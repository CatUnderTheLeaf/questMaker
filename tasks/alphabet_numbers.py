"""Alphabet numbers: each letter replaced by its position in the alphabet."""

from PIL import Image

from tasks import UnsuitableWord, register_task
from lib.render import render_text, with_instruction

_ENGLISH_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_RUSSIAN_ALPHABET = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"


def _letter_number(ch: str) -> int:
    upper = ch.upper()
    if upper in _ENGLISH_ALPHABET:
        return _ENGLISH_ALPHABET.index(upper) + 1
    if upper in _RUSSIAN_ALPHABET:
        return _RUSSIAN_ALPHABET.index(upper) + 1
    raise UnsuitableWord(f"character {ch!r} is not in the English or Russian alphabet")


@register_task(
    name="Alphabet numbers",
    type="text",
    description=(
        "A simple task: each letter is replaced by its order number in the "
        "alphabet (A=1, B=2, C=3, and so on). The participant needs to know "
        "the order of letters in the alphabet and replace each number with "
        "the matching letter to recover the word. Suitable for participants "
        "who know the alphabet confidently; the younger the participants, "
        "the shorter the word should be."
    ),
    hints=[
        "Each number hides a letter",
        "1 is A, 2 is B, 3 is C — count on",
        "Replace each number with the letter in that place in the alphabet",
    ],
    min_len=3,
)
def alphabet_numbers(word: str) -> Image.Image:
    parts = word.strip().split()
    if not parts or sum(len(p) for p in parts) < 3:
        raise UnsuitableWord("word is too short")
    encoded_words = []
    for part in parts:
        encoded_words.append("-".join(str(_letter_number(ch)) for ch in part))
    content = render_text("   /   ".join(encoded_words))
    return with_instruction(
        content, "What word did the numbers swallow?"
    )
