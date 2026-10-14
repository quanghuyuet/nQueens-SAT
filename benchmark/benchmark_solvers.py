"""Compare SAT + Glucose3, CP-SAT, Gurobi, CPLEX MIP, and CPLEX CP."""

import argparse
import importlib
import multiprocessing
import sys
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmark.common import (
    DEFAULT_THREADS, TIMEOUT_SECONDS, add_run_arguments, measure_time, run_process,
)
from benchmark.csv_log import CsvLog, default_output_path
from benchmark.tables import print_header, print_median_table, print_result
from benchmark.verify import board_from_rows, classify_board
from benchmark.benchmark_sat import ENCODINGS, SAT_SOLVER, benchmark_encoding


SOLVERS = ("sat", "cp_sat", "gurobi", "cplex_mip", "cplex_cp")
# Lowest successful summed Build + Solve on N=8,16,32,64 in
# results/sat_encoding_selection.txt; this is a sample-based default.
DEFAULT_SAT_ENCODING = "commander"
SOLVER_LABELS = {
    "cp_sat": "CP-SAT", "gurobi": "Gurobi",
    "cplex_mip": "CPLEX MIP", "cplex_cp": "CPLEX CP",
}


def _worker(solver_name, n, sat_encoding, threads, connection):
    """Build and solve one model, then report a status that has been checked.

    Every branch ends with `board`: the n x n 0/1 matrix, or None when the
    solver proves there is no solution. The matrix is verified after the
    timed stages, so verification never counts towards Build or Solve.
    """
    # Import optional libraries only in their worker, so failures stay isolated.
    if solver_name == "sat":
        benchmark_encoding(sat_encoding, n, None, connection, include_counts=False)
        return

    if solver_name == "cp_sat":
        module = importlib.import_module("solvers.cp.cp_sat")
        with measure_time(connection, "build_seconds"):
            model, queens = module.build_model(n)
        solver = module.cp_model.CpSolver()
        solver.parameters.num_workers = threads
        with measure_time(connection, "solve_seconds"):
            status = solver.solve(model)
        if status == module.cp_model.INFEASIBLE:
            board = None
        elif status in (module.cp_model.OPTIMAL, module.cp_model.FEASIBLE):
            board = board_from_rows([solver.value(queen) for queen in queens])
        else:
            raise RuntimeError(f"CP-SAT returned {solver.status_name(status)}")

    elif solver_name == "gurobi":
        module = importlib.import_module("solvers.mip.gurobi")
        with module.gp.Env(empty=True) as env:
            env.setParam("OutputFlag", 0)
            env.setParam("Threads", threads)
            env.start()
            with module.gp.Model("n_queens", env=env) as model:
                with measure_time(connection, "build_seconds"):
                    queens = module.build_model(n, model)
                    model.update()
                with measure_time(connection, "solve_seconds"):
                    model.optimize()
                if model.Status == module.GRB.INFEASIBLE:
                    board = None
                elif model.SolCount > 0:
                    board = [[int(queens[row, column].X > 0.5) for column in range(n)]
                             for row in range(n)]
                else:
                    raise RuntimeError(f"Gurobi returned status {model.Status} without a solution")

    elif solver_name == "cplex_mip":
        module = importlib.import_module("solvers.mip.cplex_mip")
        with module.cplex.Cplex() as model:
            model.set_log_stream(None)
            model.set_results_stream(None)
            model.set_warning_stream(None)
            model.set_error_stream(None)
            model.set_problem_name("n_queens")
            model.parameters.threads.set(threads)
            with measure_time(connection, "build_seconds"):
                module.build_model(n, model)
            with measure_time(connection, "solve_seconds"):
                model.solve()
            if model.solution.get_status() in (
                model.solution.status.MIP_infeasible, model.solution.status.infeasible
            ):
                board = None
            elif model.solution.is_primal_feasible():
                values = model.solution.get_values()
                board = [[int(values[row * n + column] > 0.5) for column in range(n)]
                         for row in range(n)]
            else:
                raise RuntimeError(f"CPLEX returned {model.solution.get_status_string()}")

    elif solver_name == "cplex_cp":
        module = importlib.import_module("solvers.cp.cplex_cp")
        with measure_time(connection, "build_seconds"):
            model, queens = module.build_model(n)
        with measure_time(connection, "solve_seconds"):
            result = module.solve_model(model, workers=threads)
        if result.get_solve_status() == module.SOLVE_STATUS_INFEASIBLE:
            board = None
        elif result.is_solution():
            board = board_from_rows([result.get_value(queen) for queen in queens])
        else:
            raise RuntimeError(f"CP Optimizer returned {result.get_solve_status()}")
    else:
        raise ValueError(f"Unknown solver: {solver_name}")

    status, error = classify_board(n, board)
    message = {"status": status}
    if error:
        message["error"] = error
    connection.send(message)


def run_test(solver, n, timeout=TIMEOUT_SECONDS, sat_encoding=DEFAULT_SAT_ENCODING,
             threads=DEFAULT_THREADS, run=1, memory_limit_mb=None):
    if solver not in SOLVERS:
        raise ValueError(f"Unknown solver: {solver}")
    if sat_encoding not in ENCODINGS:
        raise ValueError(f"Unknown SAT encoding: {sat_encoding}")
    result = run_process(_worker, solver, n, timeout,
                         worker_args=(sat_encoding, threads),
                         memory_limit_mb=memory_limit_mb)
    result["solver"] = solver
    result["name"] = (f"SAT+{SAT_SOLVER}[{sat_encoding}]" if solver == "sat"
                      else SOLVER_LABELS[solver])
    result["run"] = run
    result["threads"] = 1 if solver == "sat" else threads
    if solver == "sat":
        result["encoding"] = sat_encoding
        result["sat_solver"] = SAT_SOLVER
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_run_arguments(parser)
    parser.add_argument("--solvers", nargs="+", choices=SOLVERS, default=SOLVERS)
    parser.add_argument("--sat-encoding", choices=ENCODINGS, default=DEFAULT_SAT_ENCODING,
                        help="SAT representative, chosen from benchmark_sat results")
    args = parser.parse_args()

    output = args.output or default_output_path("solvers")
    log = CsvLog(output, "solvers")
    print_header("Solver benchmark", args.timeout, threads=args.threads)
    print(f"SAT representative: {args.sat_encoding}")
    print(f"Saving results to: {output}\n", flush=True)
    results = []
    try:
        # Every solver receives exactly the same requested board sizes.
        for n in args.sizes:
            for solver in args.solvers:
                for run in range(1, args.repeats + 1):
                    suffix = f", run {run}/{args.repeats}" if args.repeats > 1 else ""
                    print(f"Running {solver}, N={n}{suffix} ...", flush=True)
                    result = run_test(solver, n, args.timeout, args.sat_encoding,
                                      args.threads, run, args.memory_limit_mb)
                    results.append(result)
                    print_result(result)
                    log.write(result)
    except KeyboardInterrupt:
        print(f"\nBenchmark interrupted. Results so far are in {output}", flush=True)
        return 130
    if args.repeats > 1:
        print_median_table(results)
    print(f"Results saved to: {output}", flush=True)
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
