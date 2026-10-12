"""Compare SAT + Glucose3, CP-SAT, Gurobi, CPLEX MIP, and CPLEX CP."""

import argparse
import importlib
import multiprocessing
import sys
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmark.common import (
    TIMEOUT_SECONDS, add_run_arguments, measure_time,
    print_header, print_result, run_process,
)
from benchmark.benchmark_sat import ENCODINGS, benchmark_encoding


SOLVERS = ("sat", "cp_sat", "gurobi", "cplex_mip", "cplex_cp")
# Lowest successful summed Build + Solve on N=8,16,32,64 in
# results/sat_encoding_selection.txt; this is a sample-based default.
DEFAULT_SAT_ENCODING = "commander"
SOLVER_LABELS = {
    "cp_sat": "CP-SAT", "gurobi": "Gurobi",
    "cplex_mip": "CPLEX MIP", "cplex_cp": "CPLEX CP",
}


def _worker(solver_name, n, sat_encoding, connection):
    # Import optional libraries only in their worker, so failures stay isolated.
    if solver_name == "sat":
        benchmark_encoding(sat_encoding, n, connection, include_counts=False)
        return

    if solver_name == "cp_sat":
        module = importlib.import_module("solvers.cp.cp_sat")
        with measure_time(connection, "build_seconds"):
            model, _ = module.build_model(n)
        solver = module.cp_model.CpSolver()
        with measure_time(connection, "solve_seconds"):
            status = solver.solve(model)
        if status == module.cp_model.INFEASIBLE:
            status_name = "UNSAT"
        elif status in (module.cp_model.OPTIMAL, module.cp_model.FEASIBLE):
            status_name = "SAT"
        else:
            raise RuntimeError(f"CP-SAT returned {solver.status_name(status)}")

    elif solver_name == "gurobi":
        module = importlib.import_module("solvers.mip.gurobi")
        with module.gp.Env(empty=True) as env:
            env.setParam("OutputFlag", 0)
            env.start()
            with module.gp.Model("n_queens", env=env) as model:
                with measure_time(connection, "build_seconds"):
                    module.build_model(n, model)
                    model.update()
                with measure_time(connection, "solve_seconds"):
                    model.optimize()
                if model.Status == module.GRB.INFEASIBLE:
                    status_name = "UNSAT"
                elif model.SolCount > 0:
                    status_name = "SAT"
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
            with measure_time(connection, "build_seconds"):
                module.build_model(n, model)
            with measure_time(connection, "solve_seconds"):
                model.solve()
            if model.solution.get_status() in (
                model.solution.status.MIP_infeasible, model.solution.status.infeasible
            ):
                status_name = "UNSAT"
            elif model.solution.is_primal_feasible():
                status_name = "SAT"
            else:
                raise RuntimeError(f"CPLEX returned {model.solution.get_status_string()}")

    elif solver_name == "cplex_cp":
        module = importlib.import_module("solvers.cp.cplex_cp")
        with measure_time(connection, "build_seconds"):
            model, _ = module.build_model(n)
        with measure_time(connection, "solve_seconds"):
            result = module.solve_model(model)
        if result.get_solve_status() == module.SOLVE_STATUS_INFEASIBLE:
            status_name = "UNSAT"
        elif result.is_solution():
            status_name = "SAT"
        else:
            raise RuntimeError(f"CP Optimizer returned {result.get_solve_status()}")
    else:
        raise ValueError(f"Unknown solver: {solver_name}")

    connection.send({"status": status_name})


def run_test(solver, n, timeout=TIMEOUT_SECONDS, sat_encoding=DEFAULT_SAT_ENCODING):
    if solver not in SOLVERS:
        raise ValueError(f"Unknown solver: {solver}")
    if sat_encoding not in ENCODINGS:
        raise ValueError(f"Unknown SAT encoding: {sat_encoding}")
    result = run_process(_worker, solver, n, timeout, worker_args=(sat_encoding,))
    result["solver"] = solver
    result["name"] = (f"SAT+Glucose3[{sat_encoding}]" if solver == "sat"
                      else SOLVER_LABELS[solver])
    if solver == "sat":
        result["encoding"] = sat_encoding
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_run_arguments(parser)
    parser.add_argument("--solvers", nargs="+", choices=SOLVERS, default=SOLVERS)
    parser.add_argument("--sat-encoding", choices=ENCODINGS, default=DEFAULT_SAT_ENCODING,
                        help="SAT representative, chosen from benchmark_sat results")
    args = parser.parse_args()

    print_header("Solver benchmark", args.timeout)
    print(f"SAT representative: {args.sat_encoding}\n", flush=True)
    try:
        # Every solver receives exactly the same requested board sizes.
        for n in args.sizes:
            for solver in args.solvers:
                print(f"Running {solver}, N={n} ...", flush=True)
                print_result(run_test(solver, n, args.timeout, args.sat_encoding))
    except KeyboardInterrupt:
        print("\nBenchmark interrupted.", flush=True)
        return 130
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
