"""Task registry and auto-loader.

Each task lives in its own module inside this package and registers itself
with the ``@register_task`` decorator. Call :func:`load_tasks` once at app
startup to import all task modules; the registry is then complete.
"""

import importlib
import pkgutil
from typing import Callable, Any, Literal

from utils.types import Task
from PIL import Image

REGISTRY: dict[str, Task] = {}


class UnsuitableWord(ValueError):
    """Raised by a task's ``encode`` when the word fails a hard constraint
    (e.g. too short). The caller skips the task for that word."""


def register_task(
    *,
    name: str,
    description: str,
    hints: list[str],
    type: Literal["text", "math"] = "text",
    id: str | None = None,
    min_len: int = 1,
    max_len: int | None = None,
    no_spaces: bool = False,
    max_distinct: int | None = None,
) -> Callable[[Callable[[str], Image.Image]], Callable[[str], Image.Image]]:
    """Decorator that registers an ``encode(word) -> PIL.Image`` function.

    The task id defaults to the function name. Registering a duplicate id
    raises ``ValueError``.
    """

    def decorator(fn: Callable[[str], Image.Image]) -> Callable[[str], Image.Image]:
        task_id = id or fn.__name__
        if task_id in REGISTRY:
            raise ValueError(f"Duplicate task id: {task_id!r}")
        REGISTRY[task_id] = Task(
            id=task_id,
            name=name,
            description=description,
            hints=list(hints),
            type=type,
            min_len=min_len,
            max_len=max_len,
            no_spaces=no_spaces,
            max_distinct=max_distinct,
            encode=fn,
        )
        return fn

    return decorator


def load_tasks() -> dict[str, Task]:
    """Import every module in this package so their ``@register_task``
    decorators run. Returns the populated registry.

    A broken task module fails loud with its filename attached instead of
    being silently skipped.
    """
    package = __name__
    pkg = importutils.import_module(package)
    path: Any = getattr(pkg, "__path__", None)
    if path is None:  # pragma: no cover - defensive, always a package
        raise RuntimeError(f"{package!r} is not a package")
    for mod in pkgutil.iter_modules(path):
        if mod.name.startswith("_"):
            continue
        full_name = f"{package}.{mod.name}"
        try:
            importutils.import_module(full_name)
        except Exception as e:
            raise RuntimeError(f"Failed to load task module {full_name!r}") from e
    return REGISTRY
