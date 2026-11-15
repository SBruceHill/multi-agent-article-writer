"""Typed payloads passed between agents."""

from pydantic import BaseModel


class WriterSelectionInfo(BaseModel):
    """The orchestrator's choice of writer, passed along with the handoff."""

    which_writer: str
    reason: str
