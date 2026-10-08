"""Spinning letters: each letter of the clue-word randomly rotated, rendered as an image."""

import random

from PIL import Image

from tasks import register_task
from lib.render import render_text, with_instruction

_ROTATIONS = (Image.Transpose.ROTATE_90, Image.Transpose.ROTATE_180, Image.Transpose.ROTATE_270)
_SPACING = 8


@register_task(
    name="Spinning letters",
    type="text",
    description=(
        "Each letter of the clue-word is randomly rotated by 90, 180 or 270 "
        "degrees. The participant just needs to turn the letters back "
        "upright to read the word. Suitable for beginner readers; the "
        "longer the word, the harder the task."
    ),
    hints=[
        "The letters are turned sideways",
        "Turn each letter back upright",
        "Tilt your head or turn the page",
    ],
    min_len=5,
    no_spaces=True,
)
def spinning_letters(word: str) -> Image.Image:
    tiles = [
        render_text(ch, padding=10, uppercase=True).transpose(
            random.choice(_ROTATIONS)
        )
        for ch in word.strip()
    ]
    canvas = Image.new(
        "RGB",
        (
            sum(t.width for t in tiles) + _SPACING * (len(tiles) - 1),
            max(t.height for t in tiles),
        ),
        "white",
    )
    x = 0
    for tile in tiles:
        canvas.paste(tile, (x, (canvas.height - tile.height) // 2))
        x += tile.width + _SPACING
    return with_instruction(canvas, "This word had an accident. Can you recognize it?")
