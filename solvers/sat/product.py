import math

from pysat.solvers import Glucose3


def generate_variables(n):
    return [[i * n + j + 1 for j in range(n)] for i in range(n)]


def binomial_AMO(clauses, variables):
    for i in range(len(variables)):
        for j in range(i + 1, len(variables)):
            clauses.append([-variables[i], -variables[j]])


def generate_new_variables(next_variable, length):
    count = (length - 1).bit_length()
    start = next_variable[0]
    next_variable[0] += count
    return list(range(start, start + count))


def binary_AMO(clauses, variables, next_variable):
    if len(variables) <= 1:
        return
    bits = generate_new_variables(next_variable, len(variables))
    for index, variable in enumerate(variables):
        for bit_index, bit in enumerate(bits):
            clauses.append([-variable, bit if index & (1 << bit_index) else -bit])


def generate_matrix(start, variables_length):
    p = math.isqrt(variables_length)
    if p * p < variables_length:
        p += 1
    q = (variables_length + p - 1) // p
    return [list(range(start, start + p)),
            list(range(start + p, start + p + q))]


def at_most_one(clauses, variables, next_variable):
    if len(variables) <= 1:
        return
    row, col = generate_matrix(next_variable[0], len(variables))
    next_variable[0] += len(row) + len(col)
    if len(variables) > 10:
        binary_AMO(clauses, row, next_variable)
        binary_AMO(clauses, col, next_variable)
    else:
        binomial_AMO(clauses, row)
        binomial_AMO(clauses, col)
    for index, variable in enumerate(variables):
        clauses.append([-variable, row[index // len(col)]])
        clauses.append([-variable, col[index % len(col)]])


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
