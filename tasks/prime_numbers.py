"""Prime numbers: each letter replaced by the prime in its alphabet position."""

from PIL import Image

from tasks import UnsuitableWord, register_task
from lib.render import render_text, with_instruction

_ENGLISH_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_RUSSIAN_ALPHABET = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"


def _first_primes(count: int) -> list[int]:
    """Sieve just enough primes; 33 covers the longest (Russian) alphabet."""
    primes = [2]
    candidate = 3
    while len(primes) < count:
        if all(candidate % p for p in primes if p * p <= candidate):
            primes.append(candidate)
        candidate += 2
    return primes


_PRIMES = _first_primes(max(len(_ENGLISH_ALPHABET), len(_RUSSIAN_ALPHABET)))


def _letter_prime(ch: str) -> int:
    upper = ch.upper()
    if upper in _ENGLISH_ALPHABET:
        return _PRIMES[_ENGLISH_ALPHABET.index(upper)]
    if upper in _RUSSIAN_ALPHABET:
        return _PRIMES[_RUSSIAN_ALPHABET.index(upper)]
    raise UnsuitableWord(f"character {ch!r} is not in the English or Russian alphabet")


@register_task(
    name="Prime numbers",
    type="math",
    description=(
        "Each letter is replaced by a prime number: take the letter's order "
        "number in the alphabet and then the prime with that same order "
        "number in the prime sequence starting with 2 (A=2, B=3, C=5, and so "
        "on). The participant needs to know what a prime number is and "
        "calculate the sequence or look it up to recover the word. The "
        "difficulty depends on the word's length and on the letters: X, Y, Z "
        "sit far down the alphabet and their primes take real work."
    ),
    hints=[
        "Each number hides a letter",
        "These are not random numbers — they are prime",
        "A is the 1st prime, B the 2nd, C the 3rd: 2, 3, 5, 7, 11...",
    ],
    min_len=3,
)
def prime_numbers(word: str) -> Image.Image:
    parts = word.strip().split()
    if not parts or sum(len(p) for p in parts) < 3:
        raise UnsuitableWord("word is too short")
    encoded_words = []
    for part in parts:
        encoded_words.append("-".join(str(_letter_prime(ch)) for ch in part))
    content = render_text("   /   ".join(encoded_words))
    return with_instruction(
        content, "Prime suspects — what word is behind them?"
    )
