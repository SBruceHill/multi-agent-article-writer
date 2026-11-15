"""Hero image generation."""

import base64
import logging
import uuid
from pathlib import Path

from agents import function_tool

from article_writer.config import IMAGE_DIR, IMAGE_MODEL, get_openai_client

logger = logging.getLogger(__name__)


def request_image(prompt: str) -> str:
    """Ask the image model for one image and return it as base64 data.

    Raises whatever the OpenAI client raises if generation fails.
    """
    response = get_openai_client().images.generate(
        model=IMAGE_MODEL,
        prompt=prompt,
        size="1536x1024",
        quality="high",
        output_format="jpeg",
        n=1,
    )
    # GPT image models return base64 data, not a URL
    return response.data[0].b64_json


def save_image(b64_data: str, image_dir: Path | None = None) -> str:
    """Save base64 JPEG data as ``hero_<id>.jpg`` in ``image_dir`` and return the file path."""
    image_dir = IMAGE_DIR if image_dir is None else image_dir
    image_dir.mkdir(parents=True, exist_ok=True)
    image_path = image_dir / f"hero_{uuid.uuid4().hex[:8]}.jpg"
    image_path.write_bytes(base64.b64decode(b64_data))
    return image_path.as_posix()


@function_tool
def generate_image(prompt: str) -> str:
    """
    Generates an image and saves it to a local file.
    The prompt should be a detailed visual description.
    Returns the file path of the saved image.
    """
    logger.info("\N{ARTIST PALETTE} Generate image: %s...", prompt[:60])
    try:
        b64_data = request_image(prompt)
    except Exception as e:  # noqa: BLE001 (any failure becomes a message or an ERROR row)
        logger.warning("\N{CROSS MARK} generate image failed: %s", e)
        return f"Image generation failed: {e}"
    image_path = save_image(b64_data)
    logger.info("\N{WHITE HEAVY CHECK MARK} generate image: Done (%s)", image_path)
    return f"Image generated successfully: {image_path}"
