"""Pairwise (binomial) AMO: với mỗi cặp biến thêm một clause (¬a ∨ ¬b)."""

from solvers.sat import common
from solvers.sat.common import generate_variables, print_solution  # noqa: F401


def binomial_AMO(clauses, variables):
    for i in range(len(variables)):
        for j in range(i + 1, len(variables)):
            clauses.append([-variables[i], -variables[j]])


def at_most_one(clauses, variables, next_variable=None):
    binomial_AMO(clauses, variables)


def generate_clauses(n, variables):
    return common.generate_clauses(n, variables, at_most_one)


def solve_n_queens(n):
    """Return an n x n board of 0/1 cells, or None if no solution exists."""
    return common.solve_n_queens(n, generate_clauses)


if __name__ == "__main__":
    print_solution(solve_n_queens(8))