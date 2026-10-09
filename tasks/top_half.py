"""Top half: only the upper half of the clue-word is shown, rendered as an image."""

from PIL import Image

from tasks import register_task
from utils.render import render_text, with_instruction


# Upper halves easily confused with each other (E/F, C/G, O/Q/D, P/R/B...).
# Cyrillic counterparts with ambiguous tops (В/Ь/Ъ, Е/Ё/Э, З/Э, Р/Ф, О/С, Ш/Щ...).
_HARD_TOPS = set("BCDEFGOPQR" + "ВЕЁЗРФОЭСШЩЪЫЬЮ")


def _difficulty(word: str) -> int:
    w = word.strip().upper()
    hard = sum(1 for ch in w if ch in _HARD_TOPS)
    if hard == 0:
        return 1
    if hard >= 3 or (len(w) > 6 and hard >= 2):
        return 3
    return 2


@register_task(
    name="Top half",
    type="text",
    description=(
        "The clue-word is cut by a strictly horizontal line through the "
        "middle, so only the upper half is left. The participant needs to "
        "recognize the letters by their tops. The difficulty depends mainly "
        "on the letters: horizontally symmetrical tops that look alike "
        "(like E and F, or O and Q) make the task much harder, while the "
        "length of the word matters less."
    ),
    hints=[
        "Only the top half of the word is shown",
        "Imagine the missing bottom of each letter",
        "Half letters are enough to read the word",
    ],
    difficulty=_difficulty,
    min_len=5,
    no_spaces=True,
)
def top_half(word: str) -> Image.Image:
    content = render_text(word.strip(), uppercase=True)
    cropped = content.crop((0, 0, content.width, content.height // 2))
    return with_instruction(
        cropped, "Guess the word from the top halves of the letters."
    )
