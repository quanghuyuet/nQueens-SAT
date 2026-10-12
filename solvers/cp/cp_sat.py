"""Solve N-Queens with OR-Tools CP-SAT (install with: pip install ortools)."""

from ortools.sat.python import cp_model


def build_model(n):
    """Build the CP-SAT model and return it with its queen variables."""
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an integer")
    if n < 1:
        raise ValueError("n must be positive")

    model = cp_model.CpModel()

    # queens[column] is the row of the queen in that column (zero-based).
    # One variable per column guarantees exactly one queen in each column.
    queens = [model.new_int_var(0, n - 1, f"queen_{column}")
              for column in range(n)]

    # Distinct rows and diagonal identifiers prevent queens from attacking.
    model.add_all_different(queens)
    model.add_all_different([queens[column] + column for column in range(n)])
    model.add_all_different([queens[column] - column for column in range(n)])

    return model, queens


def solve_n_queens(n):
    """Return an n x n board of 0/1 cells, or None if no solution exists.

    n must be a positive integer. Each call creates a fresh model and solver.
    The return format matches the SAT solvers for future benchmarking.
    """
    model, queens = build_model(n)

    solver = cp_model.CpSolver()
    status = solver.solve(model)
    if status == cp_model.INFEASIBLE:
        return None
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(f"CP-SAT did not find a solution: {solver.status_name(status)}")

    board = [[0] * n for _ in range(n)]
    for column, queen in enumerate(queens):
        board[solver.value(queen)][column] = 1
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
