"""Binary AMO: đánh chỉ số nhị phân cho từng biến, dùng ceil(log2 k) biến phụ."""

from solvers.sat import common
from solvers.sat.common import generate_variables, print_solution  # noqa: F401


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


def at_most_one(clauses, variables, next_variable):
    binary_AMO(clauses, variables, next_variable)


def generate_clauses(n, variables):
    return common.generate_clauses(n, variables, at_most_one)


def solve_n_queens(n):
    """Return an n x n board of 0/1 cells, or None if no solution exists."""
    return common.solve_n_queens(n, generate_clauses)


if __name__ == "__main__":
    print_solution(solve_n_queens(8))