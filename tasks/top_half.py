"""Top half: only the upper half of the clue-word is shown, rendered as an image."""

from PIL import Image

from tasks import register_task
from lib.render import render_text


@register_task(
    name="Top half",
    description=(
        "The clue-word is cut by a strictly horizontal line through the "
        "middle, so only the upper half is left. The participant needs to "
        "recognize the letters by their tops. Choose words with letters "
        "that stay readable above the middle horizontal line; the longer "
        "the word, the harder the task."
    ),
    hints=[
        "Only the top half of the word is shown",
        "Imagine the missing bottom of each letter",
        "Half letters are enough to read the word",
    ],
    min_len=5,
    no_spaces=True,
)
def top_half(word: str) -> Image.Image:
    img = render_text(word.strip(), uppercase=True)
    return img.crop((0, 0, img.width, img.height // 2))
