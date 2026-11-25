"""Image agent: turns a topic and summary into one hero image prompt and generates it."""

from agents import Agent

from article_writer.config import MODEL
from article_writer.prompts import render
from article_writer.tools.image import generate_image

image_generator_agent = Agent(
    name="image_generator_agent",
    instructions=render("image"),
    model=MODEL,
    tools=[generate_image],
)

image_agent_as_tool = image_generator_agent.as_tool(
    tool_name="image_generator_agent",
    tool_description="Generates a hero image for an article based on a topic and content summary. "
                     "Supply the topic and content summary for the article.",
)
