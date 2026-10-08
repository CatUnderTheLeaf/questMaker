"""Extra letters: the clue-word with an intruder letter inserted, rendered as an image."""

import random

from PIL import Image

from tasks import UnsuitableWord, register_task
from lib.render import render_text, with_instruction

_RUSSIAN_ALPHABET = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
_ENGLISH_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


@register_task(
    name="Extra letters",
    type="text",
    description=(
        "A random letter that is not part of the clue-word is inserted in "
        "random places, up to as many times as the word is long. All letters "
        "of the word stay in order. The participant needs to spot the "
        "intruder and cross it out to recover the word. Suitable for "
        "confident readers who can already guess that something is extra."
    ),
    hints=[
        "One letter does not belong here",
        "The same extra letter was added several times",
        "Cross out the letter that stands out",
    ],
    min_len=3,
    no_spaces=True,
)
def extra_letters(word: str) -> Image.Image:
    letters = list(word.strip().upper())
    if len(letters) < 3:
        raise UnsuitableWord("word is too short")
    if any(ch in _RUSSIAN_ALPHABET for ch in letters):
        alphabet = _RUSSIAN_ALPHABET
    else:
        alphabet = _ENGLISH_ALPHABET
    candidates = [ch for ch in alphabet if ch not in letters]
    if not candidates:
        raise UnsuitableWord("no intruder letter available")
    extra = random.choice(candidates)
    n = len(letters)
    total = random.randint((n + 1) // 2, n)
    # Guarantee the word is split from the inside and not readable at first
    # sight: at least one interior insertion, two when the total allows it.
    # Gap g sits before original letter g (gap n trails the last letter), so
    # gaps 1..n-1 are strictly inside the word.
    n_inside = min(total, 2)
    gap_counts = [0] * (n + 1)
    for gap in random.sample(range(1, n), n_inside):
        gap_counts[gap] += 1
    for _ in range(total - n_inside):
        gap_counts[random.randint(0, n)] += 1
    parts = []
    for i, ch in enumerate(letters):
        parts.append(extra * gap_counts[i])
        parts.append(ch)
    parts.append(extra * gap_counts[n])
    content = render_text("".join(parts), uppercase=True)
    return with_instruction(
        content, "Something is wrong with this word. Fix it."
    )
