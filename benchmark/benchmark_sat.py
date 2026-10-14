"""Compare N-Queens SAT encodings, all solved with Glucose3."""

import argparse
import importlib
import multiprocessing
import random
import sys
from pathlib import Path
from time import perf_counter


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmark.common import TIMEOUT_SECONDS, add_run_arguments, measure_time, run_process
from benchmark.csv_log import CsvLog, default_output_path
from benchmark.tables import (
    OK_STATUSES, group_by_test, median_build_solve, print_header,
    print_median_table, print_result,
)
from benchmark.verify import classify_board


ENCODINGS = ("binomial", "binary", "commander", "product", "sequential")
SAT_SOLVER = "Glucose3"


def benchmark_encoding(encoding, n, shuffle_seed, connection, include_counts=True):
    """Build the encoding (CNF generation + loading into Glucose3) and time the solve call.

    If shuffle_seed is not None the clause order is shuffled with that seed
    (not timed) so repeated runs explore different search paths. The model
    returned by the solver is turned into a board and checked outside the
    timed section.
    """
    module = importlib.import_module(f"solvers.sat.{encoding}")
    from pysat.solvers import Glucose3

    # Build = generate CNF + load it into the SAT solver (comparable to the
    # MIP/CP solvers, whose Build includes passing the model to the solver).
    started = perf_counter()
    try:
        variables = module.generate_variables(n)
        clauses = module.generate_clauses(n, variables)
    finally:
        generate_seconds = perf_counter() - started
        connection.send({"build_seconds": generate_seconds})
    if shuffle_seed is not None:
        random.Random(shuffle_seed).shuffle(clauses)  # not timed
    if include_counts:
        connection.send({"clauses": len(clauses)})
        connection.send({
            "variables": len({abs(literal) for clause in clauses for literal in clause})
        })
    started = perf_counter()
    try:
        solver = Glucose3(bootstrap_with=clauses)
    finally:
        connection.send({"build_seconds": generate_seconds + perf_counter() - started})
    with solver:
        with measure_time(connection, "solve_seconds"):
            satisfiable = solver.solve()
        board = None
        if satisfiable:
            positive = {literal for literal in solver.get_model() if literal > 0}
            board = [[int(variable in positive) for variable in row]
                     for row in variables]
    status, error = classify_board(n, board)
    message = {"status": status}
    if error:
        message["error"] = error
    connection.send(message)


def run_test(encoding, n, timeout=TIMEOUT_SECONDS, run=1, shuffle=False,
             memory_limit_mb=None):
    if encoding not in ENCODINGS:
        raise ValueError(f"Unknown SAT encoding: {encoding}")
    shuffle_seed = run if shuffle else None
    result = run_process(benchmark_encoding, encoding, n, timeout,
                         worker_args=(shuffle_seed,), memory_limit_mb=memory_limit_mb)
    # Preserve the result names used by the previous SAT-only benchmark.
    result.update(encoding=encoding, cnf_seconds=result["build_seconds"],
                  solver="sat", sat_solver=SAT_SOLVER, run=run, threads=1,
                  shuffle_seed=shuffle_seed)
    return result


def recommend_encoding(results, sizes):
    """Rank only encodings whose every run finished for every requested N.

    Score = sum over N of the median Build + Solve time (excluding process
    startup and diagnostic counting overhead). A recommendation applies only
    to this measured sample.
    """
    scores = {}
    for encoding in ENCODINGS:
        groups = {n: rows for (name, n), rows in group_by_test(results).items()
                  if name == encoding}
        if set(groups) != set(sizes) or any(
                row["status"] not in OK_STATUSES for rows in groups.values() for row in rows):
            continue
        scores[encoding] = sum(median_build_solve(rows) for rows in groups.values())
    return min(scores, key=scores.get) if scores else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_run_arguments(parser, threads=False)
    parser.add_argument("--encodings", nargs="+", choices=ENCODINGS, default=ENCODINGS)
    parser.add_argument("--shuffle", action="store_true",
                        help="shuffle clause order, seed = run number (1, 2, ...); "
                             "gives different search paths for --repeats > 1")
    args = parser.parse_args()

    output = args.output or default_output_path("sat_encodings")
    log = CsvLog(output, "sat_encodings")
    print_header(f"SAT encoding benchmark ({SAT_SOLVER})", args.timeout, include_counts=True)
    print(f"Saving results to: {output}\n", flush=True)
    results = []
    try:
        for encoding in args.encodings:
            for n in args.sizes:
                for run in range(1, args.repeats + 1):
                    suffix = f", run {run}/{args.repeats}" if args.repeats > 1 else ""
                    print(f"Running {encoding}, N={n}{suffix} ...", flush=True)
                    result = run_test(encoding, n, args.timeout, run, args.shuffle,
                                      args.memory_limit_mb)
                    results.append(result)
                    print_result(result, include_counts=True)
                    log.write(result)
    except KeyboardInterrupt:
        print(f"\nBenchmark interrupted. Results so far are in {output}", flush=True)
        return 130

    if args.repeats > 1:
        print_median_table(results)
    best = recommend_encoding(results, args.sizes)
    if best:
        print(f"\nRecommended SAT encoding for this run: {best} (lowest summed Build + Solve).")
        print(f"Use: python -m benchmark.benchmark_solvers --sat-encoding {best}", flush=True)
    else:
        print("\nNo encoding completed every requested size; no recommendation.", flush=True)
    print(f"Results saved to: {output}", flush=True)
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())