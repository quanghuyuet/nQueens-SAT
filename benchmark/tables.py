"""Print benchmark tables, including the median over repeated runs."""

import statistics


OK_STATUSES = ("SAT", "UNSAT")  # finished and answer checked


def _number(value):
    return "--" if value is None else f"{value:,}"


def _seconds(value):
    return "--" if value is None else f"{value:.4f}"


def _megabytes(value):
    return "--" if value is None else f"{value:,.0f}"


def print_header(title, timeout, include_counts=False, threads=None):
    extra = f" | threads: {threads}" if threads else ""
    print(f"{title} | timeout: {timeout:g} s/test{extra}", flush=True)
    print("Build = model/CNF construction; Solve = solve API call (including presolve).")
    print("Total includes startup, imports, solver setup, CNF loading and communication.")
    print("Mem = peak memory of worker + child processes, sampled (MB).")
    print("Status: SAT/UNSAT (answer checked), INVALID (answer failed the check), "
          "TIMEOUT, MEMOUT, ERROR.")
    if not include_counts:
        print("CP solve includes model serialization and CP Optimizer process startup.")
    print("-- = stage not reached/unfinished; times are in seconds.\n", flush=True)
    counts = f" {'Vars':>9} {'Clauses':>11}" if include_counts else ""
    header = (f"{'Encoding' if include_counts else 'Solver':<25} {'N':>5}{counts} "
              f"{'Build':>9} {'Solve':>9} {'Total':>9} {'Mem(MB)':>8} {'Status':<7}")
    print(header)
    print("-" * len(header), flush=True)


def print_result(result, include_counts=False):
    counts = (f" {_number(result['variables']):>9} {_number(result['clauses']):>11}"
              if include_counts else "")
    print(
        f"{result['name']:<25} {result['n']:>5}{counts} "
        f"{_seconds(result['build_seconds']):>9} "
        f"{_seconds(result['solve_seconds']):>9} "
        f"{_seconds(result['total_seconds']):>9} "
        f"{_megabytes(result.get('peak_memory_mb')):>8} {result['status']:<7}",
        flush=True,
    )
    if "error" in result:
        print(f"  {result['error']}", flush=True)


def group_by_test(results):
    """Group results by (name, N), keeping the order they first appeared in."""
    groups = {}
    for result in results:
        groups.setdefault((result["name"], result["n"]), []).append(result)
    return groups


def _median(rows, key):
    values = [row[key] for row in rows if row.get(key) is not None]
    return statistics.median(values) if values else None


def median_build_solve(rows):
    """Median of Build + Solve over the successful runs, or None."""
    totals = [row["build_seconds"] + row["solve_seconds"] for row in rows
              if row["status"] in OK_STATUSES
              and row["build_seconds"] is not None and row["solve_seconds"] is not None]
    return statistics.median(totals) if totals else None


def print_median_table(results):
    """Median over repeated runs. Times use only runs that finished (SAT/UNSAT)."""
    print("\nMedian over repeated runs (times from finished runs only)")
    header = (f"{'Solver':<25} {'N':>5} {'Ok/Runs':>8} {'Build':>9} {'Solve':>9} "
              f"{'Total':>9} {'Mem(MB)':>8}  Other statuses")
    print(header)
    print("-" * len(header))
    for (name, n), rows in group_by_test(results).items():
        done = [row for row in rows if row["status"] in OK_STATUSES]
        others = {}
        for row in rows:
            if row["status"] not in OK_STATUSES:
                others[row["status"]] = others.get(row["status"], 0) + 1
        other_text = ", ".join(f"{status} x{count}" for status, count in others.items())
        print(f"{name:<25} {n:>5} {f'{len(done)}/{len(rows)}':>8} "
              f"{_seconds(_median(done, 'build_seconds')):>9} "
              f"{_seconds(_median(done, 'solve_seconds')):>9} "
              f"{_seconds(_median(done, 'total_seconds')):>9} "
              f"{_megabytes(_median(rows, 'peak_memory_mb')):>8}  {other_text}")
    print(flush=True)
