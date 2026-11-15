import base64
from pathlib import Path

from conftest import invoke_tool

from article_writer.tools import image


def test_save_image_decodes_and_names_file(tmp_path):
    path = image.save_image(base64.b64encode(b"jpeg-bytes").decode(), tmp_path / "images")
    assert path.startswith((tmp_path / "images").as_posix() + "/hero_")
    assert path.endswith(".jpg")
    assert Path(path).read_bytes() == b"jpeg-bytes"


def test_tool_wiring_success(monkeypatch, tmp_path):
    monkeypatch.setattr(image, "request_image", lambda prompt: base64.b64encode(b"x").decode())
    monkeypatch.setattr(image, "IMAGE_DIR", tmp_path)
    output = invoke_tool(image.generate_image, prompt="a quiet harbor at dawn")
    assert output.startswith("Image generated successfully: ")
    assert output.endswith(".jpg")


def test_tool_wiring_failure_message(monkeypatch):
    def boom(prompt):
        raise RuntimeError("no quota")

    monkeypatch.setattr(image, "request_image", boom)
    assert invoke_tool(image.generate_image, prompt="p") == "Image generation failed: no quota"
