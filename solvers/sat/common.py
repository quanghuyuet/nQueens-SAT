"""Phần dùng chung của các encoding SAT cho N-Queens.

Mỗi encoding chỉ cần cung cấp hàm ``at_most_one(clauses, variables, next_variable)``;
phần còn lại (biến, ràng buộc hàng/cột/đường chéo, gọi SAT solver, in bàn cờ)
nằm ở đây.
"""

from pysat.solvers import Glucose3


def generate_variables(n):
    """Biến x[i][j] (đánh số từ 1) cho ô (i, j)."""
    return [[i * n + j + 1 for j in range(n)] for i in range(n)]


def diagonals(variables):
    """Các đường chéo có ít nhất 2 ô: trước hết đường chéo phụ (row + col
    không đổi), sau đó đường chéo chính (row - col không đổi)."""
    n = len(variables)
    # Đường chéo phụ, đi từ dưới trái lên trên phải.
    for i in range(1, n):
        yield [variables[i - k][k] for k in range(i + 1)]
    for j in range(1, n - 1):
        yield [variables[n - 1 - k][j + k] for k in range(n - j)]
    # Đường chéo chính, đi từ trên trái xuống dưới phải.
    for i in range(n - 1):
        yield [variables[i + k][k] for k in range(n - i)]
    for j in range(1, n - 1):
        yield [variables[k][j + k] for k in range(n - j)]


def generate_clauses(n, variables, at_most_one):
    """Sinh CNF: đúng 1 hậu mỗi hàng/cột, tối đa 1 hậu mỗi đường chéo.

    at_most_one(clauses, group, next_variable) thêm các clause AMO cho group;
    next_variable là list 1 phần tử chứa số biến phụ tiếp theo còn trống.
    """
    clauses = []
    next_variable = [n * n + 1]

    columns = [[variables[i][j] for i in range(n)] for j in range(n)]
    for group in list(variables) + columns:
        clauses.append(list(group))  # ALO
        at_most_one(clauses, group, next_variable)

    for group in diagonals(variables):
        at_most_one(clauses, group, next_variable)
    return clauses


def solve_n_queens(n, clause_generator):
    """Trả về bàn cờ n x n gồm 0/1, hoặc None nếu vô nghiệm.

    clause_generator(n, variables) trả về danh sách clause của một encoding.
    """
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an integer")
    if n < 1:
        raise ValueError("n must be positive")

    variables = generate_variables(n)
    clauses = clause_generator(n, variables)
    with Glucose3(bootstrap_with=clauses) as solver:
        if not solver.solve():
            return None
        positive = {literal for literal in solver.get_model() if literal > 0}
        return [[int(variable in positive) for variable in row]
                for row in variables]


def print_solution(solution):
    if solution is None:
        print("No solution found.")
    else:
        for row in solution:
            print(" ".join("Q" if cell else "." for cell in row))