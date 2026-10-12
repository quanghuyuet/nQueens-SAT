"""Solve N-Queens as a binary ILP (install with: python -m pip install gurobipy).

A working Gurobi license is required. The bundled license supports small models;
larger boards may require a full license.
"""

import gurobipy as gp
from gurobipy import GRB


def build_model(n, model):
    """Populate an existing Gurobi model; return its binary queen variables."""
    # queens[row, column] = 1 exactly when that cell contains a queen.
    queens = model.addVars(n, n, vtype=GRB.BINARY, name="queen")

    # Exactly one queen in each row and each column.
    for row in range(n):
        model.addConstr(
            gp.quicksum(queens[row, column] for column in range(n)) == 1,
            name=f"row_{row}",
        )
    for column in range(n):
        model.addConstr(
            gp.quicksum(queens[row, column] for row in range(n)) == 1,
            name=f"column_{column}",
        )

    # Cells on a descending diagonal share row - column.
    for difference in range(1 - n, n):
        model.addConstr(
            gp.quicksum(queens[row, row - difference]
                        for row in range(n) if 0 <= row - difference < n) <= 1,
            name=f"diagonal_difference_{difference}",
        )

    # Cells on an ascending diagonal share row + column.
    for total in range(2 * n - 1):
        model.addConstr(
            gp.quicksum(queens[row, total - row]
                        for row in range(n) if 0 <= total - row < n) <= 1,
            name=f"diagonal_sum_{total}",
        )

    # This is a feasibility problem: any valid placement is sufficient.
    model.setObjective(0, GRB.MINIMIZE)
    return queens


def solve_n_queens(n):
    """Return an n x n board of 0/1 cells, or None if proven infeasible.

    n must be a positive integer. Each call creates and closes its own Gurobi
    environment and model. License/solver errors propagate to the caller;
    they are not treated as an infeasible board.
    """
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an integer")
    if n < 1:
        raise ValueError("n must be positive")

    # Configure logging before starting the environment to keep calls quiet.
    with gp.Env(empty=True) as env:
        env.setParam("OutputFlag", 0)
        env.start()
        with gp.Model("n_queens", env=env) as model:
            queens = build_model(n, model)
            model.optimize()

            if model.Status == GRB.INFEASIBLE:
                return None
            if model.SolCount == 0:
                raise RuntimeError(
                    f"Gurobi did not find a solution (status {model.Status})"
                )

            # Convert floating-point solver values to integer 0/1 cells.
            return [[int(queens[row, column].X > 0.5) for column in range(n)]
                    for row in range(n)]


def print_solution(solution):
    """Print a board using Q for queens and . for empty cells."""
    if solution is None:
        print("No solution found.")
    else:
        for row in solution:
            print(" ".join("Q" if cell else "." for cell in row))


if __name__ == "__main__":
    print_solution(solve_n_queens(8))
