
def has_solution(n):
    """N-Queens is solvable for every N except 2 and 3."""
    return n == 1 or n >= 4


def verify_board(board, n):
    """Return (True, None) for a valid n-queens board, else (False, reason)."""
    if len(board) != n or any(len(row) != n for row in board):
        return False, f"board is not {n}x{n}"
    queens = [(row, column) for row in range(n) for column in range(n)
              if board[row][column]]
    if len(queens) != n:
        return False, f"{len(queens)} queens placed, expected {n}"
    checks = (("row", lambda r, c: r), ("column", lambda r, c: c),
              ("diagonal", lambda r, c: r - c), ("anti-diagonal", lambda r, c: r + c))
    for name, key in checks:
        if len({key(r, c) for r, c in queens}) != n:
            return False, f"two queens share a {name}"
    return True, None


def classify_board(n, board):
    """Map a solver answer (board, or None for 'no solution') to a status.

    Returns (status, error). A board that fails the check, or a claim of
    'no solution' for an N that does have solutions, is reported as INVALID.
    """
    if board is None:
        if has_solution(n):
            return "INVALID", f"solver reported no solution, but N={n} has one"
        return "UNSAT", None
    ok, reason = verify_board(board, n)
    return ("SAT", None) if ok else ("INVALID", reason)


def board_from_rows(rows):
    """Board for the 'one variable per column holds that column's row' models."""
    n = len(rows)
    board = [[0] * n for _ in range(n)]
    for column, row in enumerate(rows):
        board[row][column] = 1
    return board
