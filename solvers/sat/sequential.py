"""Sequential counter AMO (Sinz): k-1 biến phụ, 3k-4 clause."""

from solvers.sat import common
from solvers.sat.common import generate_variables, print_solution  # noqa: F401


def generate_new_variables(next_variable, length):
    start = next_variable[0]
    next_variable[0] += length - 1
    return list(range(start, start + length - 1))


def at_most_one(clauses, variables, next_variable):
    if len(variables) <= 1:
        return
    s = generate_new_variables(next_variable, len(variables))
    clauses.append([-variables[0], s[0]])
    for i in range(1, len(variables) - 1):
        clauses.append([-variables[i], s[i]])
        clauses.append([-s[i - 1], s[i]])
        clauses.append([-s[i - 1], -variables[i]])
    clauses.append([-s[-1], -variables[-1]])


def generate_clauses(n, variables):
    return common.generate_clauses(n, variables, at_most_one)


def solve_n_queens(n):
    """Return an n x n board of 0/1 cells, or None if no solution exists."""
    return common.solve_n_queens(n, generate_clauses)


if __name__ == "__main__":
    print_solution(solve_n_queens(8))