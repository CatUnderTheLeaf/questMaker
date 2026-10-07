"""Table borders: the clue-word encoded by 3x3 grid cell borders, rendered as an image."""

import random

from PIL import Image, ImageDraw

from tasks import UnsuitableWord, register_task
from lib.render import get_font

_CELL = 100
_LINE = 5
_CODE_CELL = 60
_CODE_LINE = 4
_TABLE_CODE_GAP = 40
_SYMBOL_GAP = 14
_FONT_SIZE = 56
_PAD = 30

_RUSSIAN_ALPHABET = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
_ENGLISH_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _sides(row: int, col: int) -> tuple[bool, bool, bool, bool]:
    """Which (top, right, bottom, left) sides of a cell are inner grid lines."""
    return (row > 0, col < 2, row < 2, col > 0)


def _draw_symbol(
    draw: ImageDraw.ImageDraw,
    x0: int,
    y0: int,
    size: int,
    line: int,
    sides: tuple[bool, bool, bool, bool],
) -> None:
    top, right, bottom, left = sides
    x1, y1 = x0 + size, y0 + size
    if top:
        draw.rectangle([x0, y0, x1, y0 + line], fill="black")
    if bottom:
        draw.rectangle([x0, y1 - line, x1, y1], fill="black")
    if left:
        draw.rectangle([x0, y0, x0 + line, y1], fill="black")
    if right:
        draw.rectangle([x1 - line, y0, x1, y1], fill="black")


def _decoys(letters: str, count: int) -> list[str]:
    """Random filler letters for the leftover cells; never letters of the word."""
    if any(ch in _RUSSIAN_ALPHABET for ch in letters):
        alphabet = _RUSSIAN_ALPHABET
    else:
        alphabet = _ENGLISH_ALPHABET
    candidates = [ch for ch in alphabet if ch not in set(letters)]
    return random.sample(candidates, min(count, len(candidates)))


@register_task(
    name="Table borders",
    description=(
        "A square 3x3 table shows only its inner borders, no outer frame. "
        "The different letters of the clue-word (at most 9) are randomly "
        "put into the cells, one letter per cell, and the leftover cells "
        "get random decoy letters that are not in the word. Under the "
        "table the word is encoded by the visual borders of its cells: a "
        "letter in the middle is a full square, a letter in the top-left "
        "corner is a square without the top and left sides, and so on. The "
        "participant uses the table as the key."
    ),
    hints=[
        "Each shape is a cell of the table",
        "Find the letter in the cell with these borders",
        "Letters whose shapes never appear below are decoys",
    ],
    min_len=3,
    no_spaces=True,
    max_distinct=9,
)
def table_borders(word: str) -> Image.Image:
    letters = word.strip().upper()
    if len(letters) < 3:
        raise UnsuitableWord("word is too short")
    distinct = sorted(set(letters))
    if len(distinct) < 2:
        raise UnsuitableWord("word needs at least two different letters")
    if len(distinct) > 9:
        raise UnsuitableWord("word has more than 9 different letters")
    cells = [(r, c) for r in range(3) for c in range(3)]
    placed = dict(zip(random.sample(distinct, len(distinct)), random.sample(cells, len(distinct))))
    empty = [cell for cell in cells if cell not in placed.values()]
    key_letters = placed | dict(zip(_decoys(letters, len(empty)), empty))

    table_w = 3 * _CELL
    code_w = len(letters) * _CODE_CELL + (len(letters) - 1) * _SYMBOL_GAP
    width = max(table_w, code_w)
    img = Image.new("RGB", (width, table_w + _TABLE_CODE_GAP + _CODE_CELL), "white")
    draw = ImageDraw.Draw(img)

    tx = (width - table_w) // 2
    for gx in (_CELL, 2 * _CELL):
        draw.rectangle([tx + gx - _LINE // 2, 0, tx + gx + _LINE // 2, table_w], fill="black")
    for gy in (_CELL, 2 * _CELL):
        draw.rectangle([tx, gy - _LINE // 2, tx + table_w, gy + _LINE // 2], fill="black")
    font = get_font(_FONT_SIZE)
    for ch, (r, c) in key_letters.items():
        draw.text(
            (tx + c * _CELL + _CELL / 2, r * _CELL + _CELL / 2),
            ch,
            font=font,
            fill="black",
            anchor="mm",
        )

    cx = (width - code_w) // 2
    cy = table_w + _TABLE_CODE_GAP
    for i, ch in enumerate(letters):
        _draw_symbol(
            draw,
            cx + i * (_CODE_CELL + _SYMBOL_GAP),
            cy,
            _CODE_CELL,
            _CODE_LINE,
            _sides(*placed[ch]),
        )
    padded = Image.new("RGB", (width + 2 * _PAD, img.height + 2 * _PAD), "white")
    padded.paste(img, (_PAD, _PAD))
    return padded
