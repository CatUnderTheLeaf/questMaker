"""Reverse word: the clue-word spelled backwards, rendered as an image."""

from PIL import Image

from tasks import register_task
from utils.render import render_text, with_instruction


def _difficulty(word: str) -> int:
    return 1 if len(word.strip()) <= 4 else 2


@register_task(
    name="Reverse word",
    type="text",
    description=(
        "A simple task: the clue-word is written backwards. The participant "
        "needs to read confidently and reverse the letter order to recover "
        "the word. Suitable for readers; the younger the participants, the "
        "shorter the word should be."
    ),
    hints=[
        "Try reading it from the end",
        "Read the letters right to left",
        "The last letter is actually the first",
    ],
    difficulty=_difficulty,
    min_len=3,
)
def reverse_word(word: str) -> Image.Image:
    content = render_text(word.strip()[::-1], uppercase=True)
    return with_instruction(content, "Can you spot the secret word?")
