"""Typed payloads passed between agents."""

from dataclasses import dataclass, field

from pydantic import BaseModel


class WriterSelectionInfo(BaseModel):
    """The orchestrator's choice of writer, passed along with the handoff."""

    which_writer: str
    reason: str


@dataclass
class ResearchState:
    """Per research run state, passed to the tools as the SDK run context.

    Each research call gets its own, so one brief's sources never count toward another's.
    """

    read_urls: set[str] = field(default_factory=set)
