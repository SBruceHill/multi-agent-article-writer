import re

import pytest

from article_writer import config
from article_writer.prompts import render

NAMES = ["research", "image", "journalist", "storyteller", "orchestrator"]


@pytest.mark.parametrize("name", NAMES)
def test_prompt_renders_with_no_leftover_braces(name):
    text = render(name)
    assert text.strip()
    assert "{" not in text and "}" not in text


def test_research_prompt_uses_config_values():
    text = render("research")
    assert f"under {config.MIN_SOURCE_CHARS} characters" in text
    assert f"read {config.REQUIRED_SOURCES}" in text


def test_image_prompt_names_the_image_model():
    assert f"craft a detailed {config.IMAGE_MODEL} prompt" in render("image")


def test_placeholders_follow_config_changes(monkeypatch):
    monkeypatch.setattr(config, "REQUIRED_SOURCES", 7)
    assert "successfully read 7" in render("research")


def test_every_placeholder_in_the_files_is_known():
    from importlib import resources

    for name in NAMES:
        raw = resources.files("article_writer.prompts").joinpath(f"{name}.md").read_text("utf-8")
        for placeholder in re.findall(r"\{([^}]*)\}", raw):
            assert placeholder in {"REQUIRED_SOURCES", "MIN_SOURCE_CHARS", "IMAGE_MODEL"}
