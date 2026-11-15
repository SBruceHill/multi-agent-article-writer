"""Orchestrator: gets two research briefs, picks one, makes an image, hands off to a writer."""

import logging

from agents import Agent, RunContextWrapper, handoff
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

from article_writer.agents.image import image_agent_as_tool
from article_writer.agents.research import research_agent_as_tool
from article_writer.agents.writers import journalist_agent, storyteller_agent
from article_writer.config import MODEL
from article_writer.models import WriterSelectionInfo
from article_writer.prompts import render

logger = logging.getLogger(__name__)


async def on_handoff(_ctx: RunContextWrapper, decision: WriterSelectionInfo) -> None:
    """Log which writer the orchestrator chose, and why."""
    logger.info("\N{WRITING HAND} Writer selected: %s, Reason: %s", decision.which_writer, decision.reason)


orchestrator_agent = Agent(
    name="orchestrator_agent w/ handoff and styles",
    instructions=RECOMMENDED_PROMPT_PREFIX + render("orchestrator"),
    model=MODEL,
    tools=[research_agent_as_tool, image_agent_as_tool],
    handoffs=[
        handoff(agent=journalist_agent, on_handoff=on_handoff, input_type=WriterSelectionInfo),
        handoff(agent=storyteller_agent, on_handoff=on_handoff, input_type=WriterSelectionInfo),
    ],
)
