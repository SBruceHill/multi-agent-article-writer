"""Agent prompts stored as Markdown files, rendered with values from config."""

import re
from functools import cache
from importlib import resources

from article_writer import config

_PLACEHOLDER = re.compile(r"\{([A-Z][A-Z_]*)\}")


def _values() -> dict[str, str]:
    return {
        "REQUIRED_SOURCES": str(config.REQUIRED_SOURCES),
        "MIN_SOURCE_CHARS": str(config.MIN_SOURCE_CHARS),
        "IMAGE_MODEL": config.IMAGE_MODEL,
    }


@cache
def _read(name: str) -> str:
    return resources.files(__package__).joinpath(f"{name}.md").read_text(encoding="utf-8")


def render(name: str) -> str:
    """Return the prompt ``name`` (a file in this package) with its {PLACEHOLDERS} filled in.

    Raises KeyError if the prompt uses a placeholder with no value.
    """
    values = _values()
    return _PLACEHOLDER.sub(lambda m: values[m.group(1)], _read(name))
