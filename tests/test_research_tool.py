import asyncio
from types import SimpleNamespace

from conftest import invoke_tool

from article_writer.agents import research
from article_writer.config import REQUIRED_SOURCES
from article_writer.models import ResearchState

URLS = [f"https://site{i}.com/a" for i in range(REQUIRED_SOURCES)]
GOOD_BRIEF = "# T\n\n## Sources\n" + "\n".join(f"[{i}] T - {u}" for i, u in enumerate(URLS))
STUB = "I have now read 4 sources. I will proceed to write the report."


class FakeRunner:
    """Stands in for Runner.run: replies from a script and records every call."""

    def __init__(self, replies, urls_read=()):
        self.replies = list(replies)
        self.urls_read = set(urls_read)
        self.calls = []

    async def __call__(self, agent, input, context, max_turns):
        self.calls.append({"input": input, "context": context, "max_turns": max_turns})
        context.read_urls.update(self.urls_read)
        reply = self.replies.pop(0)
        return SimpleNamespace(
            final_output=reply, to_input_list=lambda: [{"role": "assistant", "content": reply}])


def test_tool_keeps_the_name_description_and_input_schema():
    tool = research.research_agent_as_tool
    assert tool.name == "research_agent"
    assert tool.description.startswith("Researches a topic and returns a research brief in Markdown.")
    assert f"reads the full text of {REQUIRED_SOURCES} distinct sources" in tool.description
    assert list(tool.params_json_schema["properties"]) == ["input"]


def test_each_research_call_gets_its_own_state(monkeypatch):
    runner = FakeRunner([GOOD_BRIEF, GOOD_BRIEF], urls_read=URLS)
    monkeypatch.setattr(research.Runner, "run", runner)
    assert invoke_tool(research.research_agent_as_tool, input="one") == GOOD_BRIEF
    assert invoke_tool(research.research_agent_as_tool, input="two") == GOOD_BRIEF

    state_1, state_2 = (c["context"] for c in runner.calls)
    assert isinstance(state_1, ResearchState) and state_1 is not state_2
    assert runner.calls[0]["max_turns"] == research.RESEARCH_MAX_TURNS


def test_good_first_brief_needs_one_attempt(monkeypatch):
    runner = FakeRunner([GOOD_BRIEF], urls_read=URLS)
    monkeypatch.setattr(research.Runner, "run", runner)
    run = asyncio.run(research.run_research_checked("topic"))
    assert (run.attempts, run.first_problem, run.problem) == (1, None, None)
    assert len(runner.calls) == 1


def test_stub_brief_is_retried_with_the_check_feedback(monkeypatch):
    runner = FakeRunner([STUB, GOOD_BRIEF], urls_read=URLS)
    monkeypatch.setattr(research.Runner, "run", runner)
    run = asyncio.run(research.run_research_checked("topic"))

    assert run.attempts == 2
    assert run.brief == GOOD_BRIEF
    assert "no '## Sources' section" in run.first_problem
    assert run.problem is None
    first, second = runner.calls
    assert first["input"] == "topic"
    assert second["input"][-1] == {"role": "user", "content": run.first_problem}
    assert second["input"][0] == {"role": "assistant", "content": STUB}
    assert first["context"] is second["context"]  # sources read so far still count


def test_gives_up_after_the_retry_limit(monkeypatch):
    runner = FakeRunner([STUB, STUB, STUB])
    monkeypatch.setattr(research.Runner, "run", runner)
    run = asyncio.run(research.run_research_checked("topic", max_retries=2))
    assert run.attempts == 3 and run.problem is not None
    assert len(runner.calls) == 3


def test_tool_returns_an_error_message_not_a_stub_when_research_fails(monkeypatch):
    monkeypatch.setattr(research.Runner, "run", FakeRunner([STUB] * 3))
    output = invoke_tool(research.research_agent_as_tool, input="topic")
    assert output.startswith("Research failed after 3 attempts. ")
    assert STUB not in output

