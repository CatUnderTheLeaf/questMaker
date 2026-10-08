"""Shopping list: an acrostic disguised as supermarket products, rendered as an image."""

import random

from PIL import Image

from tasks import UnsuitableWord, register_task
from lib.render import render_text, with_instruction

_PRODUCTS_EN = {
    "A": ["Apple", "Apricot", "Avocado", "Artichoke", "Asparagus"],
    "B": ["Banana", "Broccoli", "Beans", "Beetroot", "Butter", "Bread"],
    "C": ["Carrot", "Cucumber", "Cherry", "Cabbage", "Cheese", "Coffee"],
    "D": ["Dill", "Dates", "Daikon"],
    "E": ["Eggplant", "Eggs", "Endive"],
    "F": ["Fig", "Fennel", "Flour", "Fish"],
    "G": ["Grapes", "Garlic", "Ginger", "Grapefruit"],
    "H": ["Honey", "Hazelnut", "Honeydew", "Horseradish"],
    "I": ["Iceberg lettuce", "Ice cream"],
    "J": ["Jackfruit", "Jam", "Juice"],
    "K": ["Kiwi", "Kale", "Kohlrabi", "Ketchup"],
    "L": ["Lemon", "Lettuce", "Lime", "Leek", "Lentils"],
    "M": ["Mango", "Melon", "Mint", "Milk", "Mandarin", "Mushroom"],
    "N": ["Nectarine", "Nuts", "Noodles"],
    "O": ["Orange", "Onion", "Olives", "Oatmeal", "Oregano"],
    "P": ["Potato", "Pepper", "Pear", "Peach", "Pineapple", "Peas", "Pasta"],
    "Q": ["Quince", "Quinoa"],
    "R": ["Radish", "Raspberry", "Rice", "Raisins", "Rosemary"],
    "S": ["Strawberry", "Spinach", "Salt", "Sugar", "Squash"],
    "T": ["Tomato", "Turnip", "Tangerine", "Tea"],
    "U": ["Ugli fruit", "Udon noodles"],
    "V": ["Vanilla", "Vinegar"],
    "W": ["Watermelon", "Walnut", "Watercress"],
    "X": ["Xigua", "Xanthan gum", "Xylitol"],
    "Y": ["Yam", "Yogurt", "Yellow pepper"],
    "Z": ["Zucchini", "Zaatar", "Zwieback"],
}

_PRODUCTS_RU = {
    "А": ["Абрикос", "Ананас", "Арбуз", "Авокадо"],
    "Б": ["Банан", "Баклажан", "Брокколи", "Батон"],
    "В": ["Виноград", "Вишня"],
    "Г": ["Груша", "Гранат", "Горох", "Гречка"],
    "Д": ["Дыня", "Дайкон"],
    "Е": ["Ежевика"],
    "Ж": ["Желе", "Жвачка"],
    "З": ["Зелень", "Земляника", "Зефир"],
    "И": ["Имбирь", "Инжир"],
    "Й": ["Йогурт"],
    "К": ["Картофель", "Капуста", "Клубника", "Кофе", "Кефир"],
    "Л": ["Лук", "Лимон", "Латук", "Лайм"],
    "М": ["Морковь", "Мандарин", "Манго", "Молоко", "Малина"],
    "Н": ["Нектарин", "Нут"],
    "О": ["Огурец", "Оливки", "Орехи", "Овсянка"],
    "П": ["Помидор", "Перец", "Персик", "Печенье"],
    "Р": ["Редис", "Репа", "Рис"],
    "С": ["Свёкла", "Салат", "Смородина", "Сыр", "Слива"],
    "Т": ["Тыква", "Томат", "Творог"],
    "У": ["Укроп", "Урюк"],
    "Ф": ["Фасоль", "Финики", "Фенхель"],
    "Х": ["Хурма", "Хлеб", "Хрен"],
    "Ц": ["Цукини", "Цветная капуста"],
    "Ч": ["Чеснок", "Черешня", "Чай"],
    "Ш": ["Шампиньоны", "Шпинат", "Шоколад"],
    "Щ": ["Щавель"],
    "Э": ["Эстрагон"],
    "Ю": ["Юкола"],
    "Я": ["Яблоко"],
}

# No supermarket products start with these letters.
_NO_PRODUCT = set("ЪЫЬ")


def _product_pool_for(ch: str) -> tuple[str, list[str]]:
    upper = ch.upper()
    if upper in _PRODUCTS_EN:
        return upper, _PRODUCTS_EN[upper]
    if upper == "Ё":  # traditionally written as Е
        return "Е", _PRODUCTS_RU["Е"]
    if upper in _PRODUCTS_RU:
        return upper, _PRODUCTS_RU[upper]
    if upper in _NO_PRODUCT or not upper.isalpha():
        raise UnsuitableWord(f"no supermarket product for {ch!r}")
    raise UnsuitableWord(f"character {ch!r} is not in the English or Russian alphabet")


def _product_for(ch: str) -> str:
    _, pool = _product_pool_for(ch)
    return random.choice(pool)


@register_task(
    name="Shopping list",
    type="text",
    description=(
        "An observational task: the clue-word is hidden as the first letters "
        "of a shopping list. Each line names a supermarket product, preferably "
        "a fruit or vegetable, starting with the next letter of the word. The "
        "participant just needs to be able to read and notice the aligned first "
        "letters. For younger participants the difficulty depends on the length "
        "of the word; older ones may overthink it and see recipes or a real "
        "shopping list instead of the obvious first letters."
    ),
    hints=[
        "Is this really just a shopping list?",
        "Look at the first letters of the lines",
        "Read the first letter of each line from top to bottom",
    ],
    min_len=4,
    no_spaces=True,
)
def shopping_list(word: str) -> Image.Image:
    text = word.strip()
    if " " in text:
        raise UnsuitableWord("phrase with spaces is not supported")
    if len(text) < 4:
        raise UnsuitableWord("word is too short")
    # Group positions by product pool so repeated letters get distinct
    # products. Each pool is shuffled without replacement; only reshuffle
    # (allowing repeats) once every product has been used.
    pools: dict[str, list[str]] = {}
    indices_by_key: dict[str, list[int]] = {}
    for i, ch in enumerate(text):
        key, pool = _product_pool_for(ch)
        pools[key] = pool
        indices_by_key.setdefault(key, []).append(i)
    lines: list[str] = [""] * len(text)
    for key, indices in indices_by_key.items():
        pool = pools[key]
        remaining = list(indices)
        while remaining:
            for pos, product in zip(remaining, random.sample(pool, len(pool))):
                lines[pos] = product.upper()
            remaining = remaining[len(pool) :]
    content = render_text("\n".join(lines), 50)
    return with_instruction(
        content, "A secret ingredient is hiding in this list."
    )
