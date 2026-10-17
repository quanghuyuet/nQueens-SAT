"""Commander AMO: chia nhóm, mỗi nhóm có một biến "commander"."""

import math

from solvers.sat import common
from solvers.sat.binary import binary_AMO
from solvers.sat.binomial import binomial_AMO
from solvers.sat.common import generate_variables, print_solution  # noqa: F401


def grouping_variables(variables, per_group):
    return [variables[i:i + per_group] for i in range(0, len(variables), per_group)]


def at_most_one(clauses, variables, next_variable):
    if len(variables) <= 1:
        return
    group_size = math.ceil(len(variables) / math.isqrt(len(variables)))
    groups = grouping_variables(variables, group_size)
    start = next_variable[0]
    commanders = list(range(start, start + len(groups)))
    next_variable[0] += len(groups)
    binomial_AMO(clauses, commanders)
    for group, commander in zip(groups, commanders):
        if len(group) > 4:
            binary_AMO(clauses, group, next_variable)
        else:
            binomial_AMO(clauses, group)
        clauses.append(group + [-commander])
        for variable in group:
            clauses.append([commander, -variable])


def generate_clauses(n, variables):
    return common.generate_clauses(n, variables, at_most_one)


def solve_n_queens(n):
    """Return an n x n board of 0/1 cells, or None if no solution exists."""
    return common.solve_n_queens(n, generate_clauses)


if __name__ == "__main__":
    print_solution(solve_n_queens(8))