"""Coordinates: the clue-word encoded by n*n table cell coordinates, rendered as an image."""

import math
import random

from PIL import Image, ImageDraw

from tasks import UnsuitableWord, register_task
from lib.render import get_font, render_text, with_instruction

_CELL = 100
_LINE = 5
_TABLE_CODE_GAP = 40
_FONT_SIZE = 56
_PAD = 30

_RUSSIAN_ALPHABET = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
_ENGLISH_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _draw_grid(draw: ImageDraw.ImageDraw, x0: int, y0: int, n: int) -> None:
    size = n * _CELL
    for i in range(n + 1):
        x = x0 + i * _CELL
        if i == 0:
            draw.rectangle([x, y0, x + _LINE, y0 + size], fill="black")
        elif i == n:
            draw.rectangle([x - _LINE, y0, x, y0 + size], fill="black")
        else:
            draw.rectangle([x - _LINE // 2, y0, x + _LINE // 2, y0 + size], fill="black")
    for j in range(n + 1):
        y = y0 + j * _CELL
        if j == 0:
            draw.rectangle([x0, y, x0 + size, y + _LINE], fill="black")
        elif j == n:
            draw.rectangle([x0, y - _LINE, x0 + size, y], fill="black")
        else:
            draw.rectangle([x0, y - _LINE // 2, x0 + size, y + _LINE // 2], fill="black")


@register_task(
    name="Coordinates",
    type="math",
    description=(
        "A square table holds the different letters of the clue-word in random "
        "cells, one letter per cell; the table is just big enough to fit them "
        "all, and the leftover cells get random decoy letters that are not in "
        "the word. Under the table the word is encoded as cell coordinates: "
        "each number is the row glued to the column, both counted from 1. The "
        "participant needs to be able to count rows and columns and read "
        "letters to recover the word."
    ),
    hints=[
        "Each number points to a cell of the table",
        "The first digit is the row, the second is the column",
        "Count rows and columns from 1 to find each letter",
    ],
    min_len=3,
    no_spaces=True,
)
def coordinates(word: str) -> Image.Image:
    letters = word.strip().upper()
    if " " in letters:
        raise UnsuitableWord("phrase with spaces is not supported")
    if len(letters) < 3:
        raise UnsuitableWord("word is too short")
    if any(ch not in _ENGLISH_ALPHABET + _RUSSIAN_ALPHABET for ch in letters):
        raise UnsuitableWord("word has characters outside the English and Russian alphabets")
    distinct = sorted(set(letters))
    if len(distinct) < 2:
        raise UnsuitableWord("word needs at least two different letters")
    # Smallest n with n*n >= x, where x is the number of distinct letters.
    n = math.ceil(math.sqrt(len(distinct)))
    cells = [(r, c) for r in range(n) for c in range(n)]
    placed = dict(zip(random.sample(distinct, len(distinct)), random.sample(cells, len(distinct))))
    if any(ch in _RUSSIAN_ALPHABET for ch in letters):
        alphabet = _RUSSIAN_ALPHABET
    else:
        alphabet = _ENGLISH_ALPHABET
    pool = [ch for ch in alphabet if ch not in set(letters)]
    if not pool:
        raise UnsuitableWord("no decoy letters available")
    grid: dict[tuple[int, int], str] = {cell: ch for ch, cell in placed.items()}
    for cell in cells:
        if cell not in grid:
            grid[cell] = random.choice(pool)
    code = "-".join(f"{placed[ch][0] + 1}{placed[ch][1] + 1}" for ch in letters)

    table_size = n * _CELL
    code_img = render_text(code)
    width = max(table_size, code_img.width)
    img = Image.new(
        "RGB",
        (width + 2 * _PAD, table_size + _TABLE_CODE_GAP + code_img.height + 2 * _PAD),
        "white",
    )
    draw = ImageDraw.Draw(img)
    tx = _PAD + (width - table_size) // 2
    _draw_grid(draw, tx, _PAD, n)
    font = get_font(_FONT_SIZE)
    for (r, c), ch in grid.items():
        draw.text(
            (tx + c * _CELL + _CELL / 2, _PAD + r * _CELL + _CELL / 2),
            ch,
            font=font,
            fill="black",
            anchor="mm",
        )
    img.paste(code_img, (_PAD + (width - code_img.width) // 2, _PAD + table_size + _TABLE_CODE_GAP))
    return with_instruction(
        img, "The table knows the word. Ask it nicely."
    )
