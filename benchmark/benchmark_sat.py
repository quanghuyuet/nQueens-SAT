"""Compare N-Queens SAT encodings, all solved with Glucose3."""

import argparse
import importlib
import multiprocessing
import sys
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmark.common import (
    BOARD_SIZES, TIMEOUT_SECONDS, add_run_arguments, measure_time,
    print_header, print_result, run_process,
)


ENCODINGS = ("binomial", "binary", "commander", "product", "sequential")


def benchmark_encoding(encoding, n, connection, include_counts=True):
    """Build the unchanged encoding and time the Glucose3 solve call."""
    module = importlib.import_module(f"solvers.sat.{encoding}")
    from pysat.solvers import Glucose3

    with measure_time(connection, "build_seconds"):
        variables = module.generate_variables(n)
        clauses = module.generate_clauses(n, variables)
    if include_counts:
        connection.send({"clauses": len(clauses)})
        connection.send({
            "variables": len({abs(literal) for clause in clauses for literal in clause})
        })
    with Glucose3(bootstrap_with=clauses) as solver:
        with measure_time(connection, "solve_seconds"):
            satisfiable = solver.solve()
    connection.send({"status": "SAT" if satisfiable else "UNSAT"})


def run_test(encoding, n, timeout=TIMEOUT_SECONDS):
    if encoding not in ENCODINGS:
        raise ValueError(f"Unknown SAT encoding: {encoding}")
    result = run_process(benchmark_encoding, encoding, n, timeout)
    # Preserve the result names used by the previous SAT-only benchmark.
    result.update(encoding=encoding, cnf_seconds=result["build_seconds"])
    return result


def recommend_encoding(results, sizes):
    """Rank only encodings that completed every requested N successfully.

    Use summed Build + Solve time, excluding process startup and diagnostic
    counting overhead. A recommendation applies only to this measured sample.
    """
    scores = {}
    for encoding in ENCODINGS:
        rows = [row for row in results if row["name"] == encoding]
        if len(rows) != len(sizes) or any(row["status"] not in ("SAT", "UNSAT")
                                          for row in rows):
            continue
        scores[encoding] = sum(row["build_seconds"] + row["solve_seconds"] for row in rows)
    return min(scores, key=scores.get) if scores else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_run_arguments(parser)
    parser.add_argument("--encodings", nargs="+", choices=ENCODINGS, default=ENCODINGS)
    args = parser.parse_args()

    print_header("SAT encoding benchmark (Glucose3)", args.timeout, include_counts=True)
    results = []
    try:
        for encoding in args.encodings:
            for n in args.sizes:
                print(f"Running {encoding}, N={n} ...", flush=True)
                result = run_test(encoding, n, args.timeout)
                results.append(result)
                print_result(result, include_counts=True)
    except KeyboardInterrupt:
        print("\nBenchmark interrupted.", flush=True)
        return 130

    best = recommend_encoding(results, args.sizes)
    if best:
        print(f"\nRecommended SAT encoding for this run: {best} (lowest summed Build + Solve).")
        print(f"Use: python -m benchmark.benchmark_solvers --sat-encoding {best}", flush=True)
    else:
        print("\nNo encoding completed every requested size; no recommendation.", flush=True)
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
