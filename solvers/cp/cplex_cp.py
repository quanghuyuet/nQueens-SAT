"""Solve N-Queens using DOcplex CP and IBM CP Optimizer.

Install the modeling library with: python -m pip install docplex
A local CP Optimizer runtime is also required. Put cpoptimizer on PATH,
or set DOCPLEX_CP_EXECUTABLE to the full path of its executable.
"""

import os

from docplex.cp.model import CpoModel
from docplex.cp.solution import SOLVE_STATUS_INFEASIBLE


def build_model(n):
    """Build the CP Optimizer model and return it with its queen variables."""
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an integer")
    if n < 1:
        raise ValueError("n must be positive")

    model = CpoModel(name="n_queens")

    # queens[column] is the row of that column's queen (zero-based).
    # One variable per column guarantees exactly one queen per column.
    queens = model.integer_var_list(n, min=0, max=n - 1, name="queen")

    # Distinct rows give exactly one queen per row.
    model.add(model.all_diff(queens))

    # Diagonal identifiers are row + column and row - column.
    model.add(model.all_diff([queens[column] + column for column in range(n)]))
    model.add(model.all_diff([queens[column] - column for column in range(n)]))

    return model, queens


def solve_model(model):
    """Solve a built model using the same local runtime configuration."""

    # Use the local runtime; an explicit path can override normal discovery.
    solve_options = {"agent": "local", "LogVerbosity": "Quiet"}
    executable = os.environ.get("DOCPLEX_CP_EXECUTABLE")
    if executable:
        solve_options["execfile"] = executable
    return model.solve(**solve_options)


def solve_n_queens(n):
    """Return an n x n board of 0/1 cells, or None if proven infeasible.

    n must be a positive integer. Each call builds a fresh CP model.
    Runtime, license, and solver errors propagate to the caller.
    """
    model, queens = build_model(n)
    result = solve_model(model)

    if result.get_solve_status() == SOLVE_STATUS_INFEASIBLE:
        return None
    if not result.is_solution():
        raise RuntimeError(
            f"CP Optimizer did not find a solution: {result.get_solve_status()}"
        )

    board = [[0] * n for _ in range(n)]
    for column, queen in enumerate(queens):
        board[result.get_value(queen)][column] = 1
    return board


def print_solution(solution):
    """Print a board using Q for queens and . for empty cells."""
    if solution is None:
        print("No solution found.")
    else:
        for row in solution:
            print(" ".join("Q" if cell else "." for cell in row))


if __name__ == "__main__":
    print_solution(solve_n_queens(8))
