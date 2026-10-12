from pysat.solvers import Glucose3


def generate_variables(n):
    return [[i * n + j + 1 for j in range(n)] for i in range(n)]


def at_most_one(clauses, variables):
    for i in range(0, len(variables)):
        for j in range(i + 1, len(variables)):
            clauses.append([-variables[i], -variables[j]])
    return clauses


def exactly_one(clauses, variables):
    clauses.append(variables)
    at_most_one(clauses, variables)


def generate_clauses(n, variables):
    clauses = []

    # Exactly one queen in each row
    for i in range(n):
        exactly_one(clauses, variables[i])

    # Exactly one queen in each column
    for j in range(n):
        exactly_one(clauses, [variables[i][j] for i in range(n)])

    # At most one queen in each diagonal
    for i in range(n):
        for j in range(n):
            for k in range(1, n):
                if i + k < n and j + k < n:
                    at_most_one(clauses, [variables[i][j], variables[i + k][j + k]])
                if i + k < n and j - k >= 0:
                    at_most_one(clauses, [variables[i][j], variables[i + k][j - k]])

    return clauses


def solve_n_queens(n):
    """Return an n x n board of 0/1 cells, or None if no solution exists.

    n must be a positive integer. Each call uses its own auxiliary variables.
    """
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an integer")
    if n < 1:
        raise ValueError("n must be positive")

    variables = generate_variables(n)
    clauses = generate_clauses(n, variables)
    with Glucose3(bootstrap_with=clauses) as solver:
        if not solver.solve():
            return None
        positive_literals = {literal for literal in solver.get_model() if literal > 0}
        return [[int(variable in positive_literals) for variable in row]
                for row in variables]


def print_solution(solution):
    if solution is None:
        print("No solution found.")
    else:
        for row in solution:
            print(" ".join("Q" if cell else "." for cell in row))


if __name__ == "__main__":
    n = 8
    print_solution(solve_n_queens(n))
