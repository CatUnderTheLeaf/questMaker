"""Caesar cipher: each letter shifted by 3, rendered as an image."""

from PIL import Image

from tasks import UnsuitableWord, register_task
from utils.render import render_text, with_instruction

_SHIFT = 3

_ENGLISH_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_RUSSIAN_ALPHABET = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"


def _shift_char(ch: str) -> str:
    upper = ch.upper()
    if upper in _ENGLISH_ALPHABET:
        return _ENGLISH_ALPHABET[
            (_ENGLISH_ALPHABET.index(upper) + _SHIFT) % len(_ENGLISH_ALPHABET)
        ]
    if upper in _RUSSIAN_ALPHABET:
        return _RUSSIAN_ALPHABET[
            (_RUSSIAN_ALPHABET.index(upper) + _SHIFT) % len(_RUSSIAN_ALPHABET)
        ]
    raise UnsuitableWord(f"character {ch!r} is not in the English or Russian alphabet")


def _difficulty(word: str) -> int:
    return 4


@register_task(
    name="Caesar cipher",
    type="text",
    description=(
        "A classic task: each letter is shifted by 3 places in the alphabet "
        "(A becomes D, B becomes E, and so on, wrapping around at the end). "
        "The participant needs to know who Caesar is or how messages were "
        "encoded back then, and shift each letter back by 3 to recover the "
        "word. Suitable for participants who already know the alphabet well."
    ),
    hints=[
        "This is how Caesar encoded messages",
        "Each letter is shifted forward in the alphabet",
        "Shift every letter back by 3 to read the word",
    ],
    difficulty=_difficulty,
    min_len=5,
)
def caesar(word: str) -> Image.Image:
    text = word.strip()
    if len(text.replace(" ", "")) < 5:
        raise UnsuitableWord("word is too short")
    encoded = "".join(" " if ch == " " else _shift_char(ch) for ch in text)
    content = render_text(encoded, uppercase=True)
    return with_instruction(content, "Crack the code. What's the word?")
