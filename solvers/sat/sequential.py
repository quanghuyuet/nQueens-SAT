from pysat.solvers import Glucose3


def generate_variables(n):
    return [[i * n + j + 1 for j in range(n)] for i in range(n)]


def generate_new_variables(next_variable, length):
    start = next_variable[0]
    next_variable[0] += length - 1
    return list(range(start, start + length - 1))


def at_most_one(clauses, variables, next_variable):
    if len(variables) <= 1:
        return
    new_variables = generate_new_variables(next_variable, len(variables))
    clauses.append([-variables[0], new_variables[0]])
    for i in range(1, len(variables) - 1):
        clauses.append([-variables[i], new_variables[i]])
        clauses.append([-new_variables[i - 1], new_variables[i]])
        clauses.append([-new_variables[i - 1], -variables[i]])
    clauses.append([-new_variables[-1], -variables[-1]])


def exactly_one(clauses, variables, next_variable):
    clauses.append(variables)
    at_most_one(clauses, variables, next_variable)


def generate_clauses(n, variables):
    clauses = []
    # Mutable counter shared only by constraints for this board.
    next_variable = [n * n + 1]

    # Exactly one queen in each row
    for row in range(n):
        exactly_one(clauses, variables[row], next_variable)

    # Exactly one queen in each column
    for col in range(n):
        exactly_one(clauses, [variables[row][col] for row in range(n)], next_variable)

    # At most one queen in each diagonal
    for i in range(1, n):
        diagonal = []
        row = i
        col = 0
        while row >= 0 and col < n:
            diagonal.append(variables[row][col])
            row -= 1
            col += 1
        at_most_one(clauses, diagonal, next_variable)

    for j in range(1, n - 1):
        diagonal = []
        row = n - 1
        col = j
        while row >= 0 and col < n:
            diagonal.append(variables[row][col])
            row -= 1
            col += 1
        at_most_one(clauses, diagonal, next_variable)

    for i in range(n - 1):
        diagonal = []
        row = i
        col = 0
        while row < n and col < n:
            diagonal.append(variables[row][col])
            row += 1
            col += 1
        at_most_one(clauses, diagonal, next_variable)

    for j in range(1, n - 1):
        diagonal = []
        row = 0
        col = j
        while row < n and col < n:
            diagonal.append(variables[row][col])
            row += 1
            col += 1
        at_most_one(clauses, diagonal, next_variable)

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
