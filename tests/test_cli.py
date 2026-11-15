from pathlib import Path

import pytest

from article_writer import cli, config


def test_defaults():
    args = cli.build_parser().parse_args(["solar power"])
    assert args.topic == "solar power"
    assert args.out == config.OUTPUT_DIR
    assert args.max_turns == config.DEFAULT_MAX_TURNS
    assert args.verbose is False


def test_all_options():
    args = cli.build_parser().parse_args(["topic", "--out", "docs/out", "--max-turns", "12", "--verbose"])
    assert args.out == Path("docs/out")
    assert args.max_turns == 12
    assert args.verbose is True


def test_topic_is_required():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args([])


def test_max_turns_must_be_an_integer():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["topic", "--max-turns", "many"])


@pytest.mark.parametrize("topic, slug", [
    ("Why the sitting president's party loses seats", "why_the_sitting_president_s_party_loses_seats"),
    ("  !!!  ", "article"),
    ("a" * 100, "a" * 60),
])
def test_slugify(topic, slug):
    assert cli.slugify(topic) == slug


def test_main_writes_article_and_prints_path_and_writer(monkeypatch, tmp_path, capsys):
    async def fake_write_article(topic, max_turns):
        assert (topic, max_turns) == ("My Topic", 5)
        return "# Title\n\nBody", "storyteller_agent"

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(cli, "write_article", fake_write_article)
    assert cli.main(["My Topic", "--out", str(tmp_path), "--max-turns", "5"]) == 0
    path = tmp_path / "my_topic.md"
    assert path.read_text(encoding="utf-8") == "# Title\n\nBody"
    out = capsys.readouterr().out
    assert f"Article: {path}" in out
    assert "Writer: storyteller_agent" in out


def test_main_fails_fast_without_api_key(monkeypatch, capsys):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert cli.main(["topic"]) == 1
    assert "API Key is missing" in capsys.readouterr().err
