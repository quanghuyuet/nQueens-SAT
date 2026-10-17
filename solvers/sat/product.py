"""Product AMO: xếp biến vào lưới p x q, AMO trên các biến hàng và cột phụ."""

import math

from solvers.sat import common
from solvers.sat.binary import binary_AMO
from solvers.sat.binomial import binomial_AMO
from solvers.sat.common import generate_variables, print_solution  # noqa: F401


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


def generate_clauses(n, variables):
    return common.generate_clauses(n, variables, at_most_one)


def solve_n_queens(n):
    """Return an n x n board of 0/1 cells, or None if no solution exists."""
    return common.solve_n_queens(n, generate_clauses)


if __name__ == "__main__":
    print_solution(solve_n_queens(8))