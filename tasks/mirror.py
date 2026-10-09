"""Mirror: the clue-word randomly flipped horizontally or vertically, rendered as an image."""

import random

from PIL import Image

from tasks import register_task
from utils.render import render_text, with_instruction

_FLIPS = (Image.Transpose.FLIP_LEFT_RIGHT, Image.Transpose.FLIP_TOP_BOTTOM)


@register_task(
    name="Mirror",
    type="text",
    description=(
        "The clue-word is flipped at random, either horizontally or "
        "vertically, never both at once. The participant needs a mirror to "
        "read it. Choose words with letters that are symmetrical if "
        "possible, so it is hard to decide what is up or down, like 'E' or "
        "'D'. The difficulty also depends on the length of the word: the "
        "longer the word, the harder the task."
    ),
    hints=[
        "The word is mirrored",
        "Try holding it up to a mirror",
        "It is flipped in only one direction",
    ],
    min_len=3,
    no_spaces=True,
)
def mirror(word: str) -> Image.Image:
    content = render_text(word.strip(), uppercase=True).transpose(
        random.choice(_FLIPS)
    )
    return with_instruction(
        content, "Don't believe your eyes. What word is it really?"
    )
