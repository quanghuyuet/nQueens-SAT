"""Write benchmark results to a CSV file, one row per finished test."""

import csv
from datetime import datetime
from pathlib import Path


RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"

CSV_FIELDS = (
    "timestamp", "benchmark", "solver", "encoding", "sat_solver", "n", "run",
    "threads", "shuffle_seed", "variables", "clauses", "build_seconds",
    "solve_seconds", "total_seconds", "peak_memory_mb", "status", "error",
)


def default_output_path(prefix):
    return RESULTS_DIR / f"{prefix}_{datetime.now():%Y%m%d_%H%M%S}.csv"


class CsvLog:
    """Append one row per finished test and flush immediately, so a crash or
    Ctrl+C never loses earlier results."""

    def __init__(self, path, benchmark):
        self.path = Path(path)
        self.benchmark = benchmark
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, result):
        row = {field: result.get(field) for field in CSV_FIELDS}
        row["benchmark"] = self.benchmark
        row["timestamp"] = datetime.now().isoformat(timespec="seconds")
        for field in ("build_seconds", "solve_seconds", "total_seconds", "peak_memory_mb"):
            if row[field] is not None:
                row[field] = round(row[field], 6)
        new_file = not self.path.exists() or self.path.stat().st_size == 0
        with open(self.path, "a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            if new_file:
                writer.writeheader()
            writer.writerow(row)
