"""Solve N-Queens as a binary ILP using the native CPLEX Python API.

Install with: python -m pip install cplex
Community Edition allows up to 1,000 variables and 1,000 constraints.
This model has n*n variables and 6*n-2 constraints, so it supports n <= 31
with that edition. Larger boards require an unrestricted CPLEX installation.
"""

import cplex


def build_model(n, model):
    """Populate an existing CPLEX model with the binary N-Queens ILP."""
    # Cell (row, column) has variable index row * n + column.
    # A value of 1 means a queen occupies that cell.
    variable_count = n * n
    model.variables.add(
        obj=[0.0] * variable_count,
        lb=[0.0] * variable_count,
        ub=[1.0] * variable_count,
        types=[model.variables.type.binary] * variable_count,
        names=[f"queen_{row}_{column}"
               for row in range(n) for column in range(n)],
    )

    def add_constraint(indices, sense, name):
        """Add a sum of binary cells equal to / at most one."""
        model.linear_constraints.add(
            lin_expr=[cplex.SparsePair(ind=indices, val=[1.0] * len(indices))],
            senses=[sense], rhs=[1.0], names=[name],
        )

    # Exactly one queen per row and per column (E means equality).
    for row in range(n):
        add_constraint([row * n + column for column in range(n)],
                       "E", f"row_{row}")
    for column in range(n):
        add_constraint([row * n + column for row in range(n)],
                       "E", f"column_{column}")

    # At most one queen per diagonal (L means less than or equal).
    # Descending diagonals have constant row - column.
    for difference in range(1 - n, n):
        indices = [row * n + (row - difference) for row in range(n)
                   if 0 <= row - difference < n]
        add_constraint(indices, "L", f"diagonal_difference_{difference}")

    # Ascending diagonals have constant row + column.
    for total in range(2 * n - 1):
        indices = [row * n + (total - row) for row in range(n)
                   if 0 <= total - row < n]
        add_constraint(indices, "L", f"diagonal_sum_{total}")

    # A zero objective makes this a feasibility problem.
    model.objective.set_sense(model.objective.sense.minimize)


def solve_n_queens(n):
    """Return an n x n board of 0/1 cells, or None if proven infeasible.

    n must be a positive integer. Each call creates and closes its own model.
    Library, license, and solver errors propagate to the caller.
    """
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an integer")
    if n < 1:
        raise ValueError("n must be positive")

    with cplex.Cplex() as model:
        model.set_log_stream(None)
        model.set_results_stream(None)
        model.set_warning_stream(None)
        model.set_error_stream(None)
        model.set_problem_name("n_queens")

        build_model(n, model)
        model.solve()

        status = model.solution.get_status()
        if status in (model.solution.status.MIP_infeasible,
                      model.solution.status.infeasible):
            return None
        if not model.solution.is_primal_feasible():
            raise RuntimeError(
                f"CPLEX did not find a solution: {model.solution.get_status_string()}"
            )

        values = model.solution.get_values()
        return [[int(values[row * n + column] > 0.5) for column in range(n)]
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
