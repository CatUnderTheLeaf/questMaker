"""Queens: the clue-word on the cells of a unique N-queens solution, rendered as an image."""

import itertools
import random

from PIL import Image, ImageDraw

from tasks import UnsuitableWord, register_task
from lib.render import get_font

_SOLUTIONS: dict[int, list[frozenset[tuple[int, int]]]] = {}

_RUSSIAN_ALPHABET = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
_ENGLISH_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

_TABLE_GAP = 60
_PAD = 30


def _all_solutions(n: int) -> list[frozenset[tuple[int, int]]]:
    if n not in _SOLUTIONS:
        sols: list[frozenset[tuple[int, int]]] = []

        def bt(r: int, cols: list[int], d1: set[int], d2: set[int]) -> None:
            if r == n:
                sols.append(frozenset((rr, c) for rr, c in enumerate(cols)))
                return
            for c in range(n):
                if c in cols or (r - c) in d1 or (r + c) in d2:
                    continue
                cols.append(c)
                d1.add(r - c)
                d2.add(r + c)
                bt(r + 1, cols, d1, d2)
                cols.pop()
                d1.discard(r - c)
                d2.discard(r + c)

        bt(0, [], set(), set())
        _SOLUTIONS[n] = sols
    return _SOLUTIONS[n]


def _minimal_clues(
    solution: frozenset[tuple[int, int]],
    others: list[frozenset[tuple[int, int]]],
) -> set[tuple[int, int]]:
    """Smallest subset of the solution completed by no other solution."""
    cells = list(solution)
    random.shuffle(cells)
    for m in range(1, len(cells) + 1):
        subs = list(itertools.combinations(cells, m))
        random.shuffle(subs)
        for sub in subs:
            forcing = frozenset(sub)
            if sum(1 for o in others if forcing <= o) == 1:
                return set(sub)
    raise AssertionError("unreachable: the full solution always forces itself")


def _decoy_letters(letters: str, count: int) -> list[str]:
    """Filler letters, never from the word, repeats kept to a minimum."""
    if any(ch in _RUSSIAN_ALPHABET for ch in letters):
        alphabet = _RUSSIAN_ALPHABET
    else:
        alphabet = _ENGLISH_ALPHABET
    pool = [ch for ch in alphabet if ch not in set(letters)] or list(alphabet)
    random.shuffle(pool)
    return [pool[i % len(pool)] for i in range(count)]


def _draw_grid(draw: ImageDraw.ImageDraw, x0: int, y0: int, n: int, cell: int, line: int) -> None:
    size = n * cell
    for i in range(n + 1):
        x = x0 + i * cell
        if i == 0:
            draw.rectangle([x, y0, x + line, y0 + size], fill="black")
        elif i == n:
            draw.rectangle([x - line, y0, x, y0 + size], fill="black")
        else:
            draw.rectangle([x - line // 2, y0, x + line // 2, y0 + size], fill="black")
    for j in range(n + 1):
        y = y0 + j * cell
        if j == 0:
            draw.rectangle([x0, y, x0 + size, y + line], fill="black")
        elif j == n:
            draw.rectangle([x0, y - line, x0 + size, y], fill="black")
        else:
            draw.rectangle([x0, y - line // 2, x0 + size, y + line // 2], fill="black")


@register_task(
    name="Queens",
    description=(
        "Two tables of word-length by word-length side by side. The left "
        "table shows only the minimal clues of the unique solution: dots "
        "mark the given queens. The right table holds the letters of the "
        "word on the cells of that solution, read row by row from the top, "
        "while all other cells get random filler letters. The participant "
        "restores the queens so none attack each other and reads the word "
        "off the queen cells. Suitable for those who know how the chess "
        "queen moves; the bigger the board, the harder the task."
    ),
    hints=[
        "Dots mark the given queens",
        "Queens must not attack each other",
        "Read the queen cells from the top row down",
    ],
    min_len=4,
    max_len=8,
    no_spaces=True,
)
def n_queens(word: str) -> Image.Image:
    letters = word.strip().upper()
    n = len(letters)
    if not 4 <= n <= 8:
        raise UnsuitableWord("word must be 4 to 8 letters long")
    solutions = _all_solutions(n)
    solution = random.choice(solutions)
    clues = _minimal_clues(solution, solutions)
    queen_col = {r: c for r, c in solution}

    others = [(r, c) for r in range(n) for c in range(n) if (r, c) not in solution]
    random.shuffle(others)
    right_letters = {(r, queen_col[r]): letters[r] for r in range(n)}
    right_letters.update(zip(others, _decoy_letters(letters, len(others))))

    cell = 400 // n
    line = max(3, round(cell / 20))
    dot = max(4, cell // 5)
    table = n * cell
    img = Image.new(
        "RGB", (2 * table + _TABLE_GAP + 2 * _PAD, table + 2 * _PAD), "white"
    )
    draw = ImageDraw.Draw(img)
    left_x = _PAD
    right_x = _PAD + table + _TABLE_GAP
    _draw_grid(draw, left_x, _PAD, n, cell, line)
    _draw_grid(draw, right_x, _PAD, n, cell, line)
    font = get_font(max(10, round(cell * 0.56)))
    for r, c in clues:
        cx, cy = left_x + c * cell + cell / 2, _PAD + r * cell + cell / 2
        draw.ellipse([cx - dot, cy - dot, cx + dot, cy + dot], fill="black")
    for (r, c), ch in right_letters.items():
        draw.text(
            (right_x + c * cell + cell / 2, _PAD + r * cell + cell / 2),
            ch,
            font=font,
            fill="black",
            anchor="mm",
        )
    return img
