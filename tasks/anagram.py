"""Anagram: the letters of the clue-word in random order, rendered as an image."""

import random

from PIL import Image

from tasks import UnsuitableWord, register_task
from lib.render import render_text, with_instruction


@register_task(
    name="Anagram",
    type="text",
    description=(
        "A generalization of the reversed-word task: the letters of the "
        "clue-word are shuffled in random order. All letters of the word "
        "are used, nothing is added or removed. The participant needs to "
        "rearrange the letters to recover the word. The younger the participants, the "
        "shorter the word should be."
    ),
    hints=[
        "Try rearranging the letters",
        "All letters of the word are there, just mixed up",
        "Write the letters on separate slips and shuffle them",
    ],
    min_len=3,
    max_len=8,
    no_spaces=True,
)
def anagram(word: str) -> Image.Image:
    letters = list(word.strip())
    if len(set(letters)) < 2:
        raise UnsuitableWord("word has no letters to shuffle")
    original = "".join(letters)
    for _ in range(10):
        shuffled = "".join(random.sample(letters, len(letters)))
        if shuffled != original:
            break
    else:
        raise UnsuitableWord("could not shuffle word into a different order")
    content = render_text(shuffled, uppercase=True)
    return with_instruction(content, "Rearrange the letters to form the word.")
