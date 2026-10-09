"""Knight move: the clue-word read along a fixed knight's tour, rendered as an image."""

from PIL import Image, ImageDraw

from tasks import UnsuitableWord, register_task
from utils.render import get_font, with_instruction

# Fixed knight's tour on a 3x4 board, 1-indexed positions in visit order.
_TOUR = [
    (0, 0),  # 1
    (1, 2),  # 2
    (2, 0),  # 3
    (0, 1),  # 4
    (1, 3),  # 5
    (2, 1),  # 6
    (0, 2),  # 7
    (2, 3),  # 8
    (1, 1),  # 9
    (0, 3),  # 10
    (2, 2),  # 11
    (1, 0),  # 12
]
# Tour positions shown in the left (key) table; the rest stay blank.
_GIVEN = (1, 3, 7, 11)

_ROWS, _COLS = 3, 4
_CELL = 100
_LINE = 5
_TABLE_GAP = 60
_FONT_SIZE = 56
_PAD = 30


def _draw_grid(draw: ImageDraw.ImageDraw, x0: int, y0: int) -> None:
    tw, th = _COLS * _CELL, _ROWS * _CELL
    for i in range(_COLS + 1):
        x = x0 + i * _CELL
        if i == 0:
            draw.rectangle([x, y0, x + _LINE, y0 + th], fill="black")
        elif i == _COLS:
            draw.rectangle([x - _LINE, y0, x, y0 + th], fill="black")
        else:
            draw.rectangle([x - _LINE // 2, y0, x + _LINE // 2, y0 + th], fill="black")
    for j in range(_ROWS + 1):
        y = y0 + j * _CELL
        if j == 0:
            draw.rectangle([x0, y, x0 + tw, y + _LINE], fill="black")
        elif j == _ROWS:
            draw.rectangle([x0, y - _LINE, x0 + tw, y], fill="black")
        else:
            draw.rectangle([x0, y - _LINE // 2, x0 + tw, y + _LINE // 2], fill="black")


def _difficulty(word: str) -> int:
    return 5


@register_task(
    name="Knight move",
    type="math",
    description=(
        "Two 3x4 tables side by side. The left table holds the numbers of a "
        "knight's tour, with only 1, 3, 7 and 11 shown. The right table "
        "holds the 12 letters of the clue-word in tour order: the 1st "
        "letter where the knight starts, the 2nd where it jumps next, and "
        "so on, all 12 letters, nothing added or removed. The participant "
        "reconstructs the knight's path and reads the word along it. "
        "Suitable for those who know how the chess knight moves."
    ),
    hints=[
        "The knight visits every cell exactly once",
        "Numbers 1, 3, 7 and 11 mark the way",
        "Follow the knight's path to read the word",
    ],
    difficulty=_difficulty,
    min_len=12,
    max_len=12,
    no_spaces=True,
)
def knight_move(word: str) -> Image.Image:
    letters = word.strip().upper()
    if len(letters) != 12:
        raise UnsuitableWord("word must be exactly 12 letters long")
    table_w, table_h = _COLS * _CELL, _ROWS * _CELL
    img = Image.new(
        "RGB",
        (2 * table_w + _TABLE_GAP + 2 * _PAD, table_h + 2 * _PAD),
        "white",
    )
    draw = ImageDraw.Draw(img)
    left_x = _PAD
    right_x = _PAD + table_w + _TABLE_GAP
    _draw_grid(draw, left_x, _PAD)
    _draw_grid(draw, right_x, _PAD)
    font = get_font(_FONT_SIZE)
    for pos in _GIVEN:
        r, c = _TOUR[pos - 1]
        draw.text(
            (left_x + c * _CELL + _CELL / 2, _PAD + r * _CELL + _CELL / 2),
            str(pos),
            font=font,
            fill="black",
            anchor="mm",
        )
    for i, ch in enumerate(letters):
        r, c = _TOUR[i]
        draw.text(
            (right_x + c * _CELL + _CELL / 2, _PAD + r * _CELL + _CELL / 2),
            ch,
            font=font,
            fill="black",
            anchor="mm",
        )
    return with_instruction(
        img, "Follow the knight's path from 1 to 12 to read the word."
    )
