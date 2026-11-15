import asyncio

import pandas as pd

from article_writer.evals import run_evals


def test_evaluate_all_keeps_order_limits_concurrency_and_records_errors(monkeypatch):
    running = peak = 0

    async def fake_research(topic):
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.01)
        running -= 1
        if topic == "bad":
            raise RuntimeError("boom")
        return f"brief for {topic}", {"https://a.com/1"}

    monkeypatch.setattr(run_evals, "run_research", fake_research)
    monkeypatch.setattr(run_evals, "judge", lambda brief: "FALSE")
    topics = ["a", "bad", "c", "d", "e"]
    monkeypatch.setattr(run_evals, "TOPICS", topics)

    rows = asyncio.run(run_evals.evaluate_all(topics, workers=2))

    assert [r["topic"] for r in rows] == topics
    assert [r["failure"] for r in rows] == ["FALSE", "ERROR", "FALSE", "FALSE", "FALSE"]
    assert "boom" in rows[1]["brief"]
    assert peak == 2
    assert [r["check_failure"] for r in rows] == ["TRUE", "ERROR", "TRUE", "TRUE", "TRUE"]
    assert "no '## Sources' section" in rows[0]["check_detail"]


def test_source_check_passes_a_brief_citing_enough_read_sources(monkeypatch):
    urls = {f"https://site{i}.com/a" for i in range(4)}
    brief = "## Sources\n" + "\n".join(f"[{i}] T - {u}" for i, u in enumerate(sorted(urls)))

    async def fake_research(topic):
        return brief, urls

    monkeypatch.setattr(run_evals, "run_research", fake_research)
    monkeypatch.setattr(run_evals, "judge", lambda b: "FALSE")
    monkeypatch.setattr(run_evals, "TOPICS", ["t"])
    row = asyncio.run(run_evals.evaluate("t", asyncio.Semaphore(1)))
    assert (row["check_failure"], row["check_detail"]) == ("FALSE", "")


def test_source_check_fails_a_brief_citing_sources_the_agent_did_not_read(monkeypatch):
    brief = "## Sources\n[1] T - https://made-up.com/x"

    async def fake_research(topic):
        return brief, set()

    monkeypatch.setattr(run_evals, "run_research", fake_research)
    monkeypatch.setattr(run_evals, "judge", lambda b: "FALSE")
    monkeypatch.setattr(run_evals, "TOPICS", ["t"])
    row = asyncio.run(run_evals.evaluate("t", asyncio.Semaphore(1)))
    assert row["check_failure"] == "TRUE"
    assert "made-up.com/x" in row["check_detail"]


def test_failure_rate_counts_only_scored_runs():
    df = pd.DataFrame({"failure": ["TRUE", "FALSE", "FALSE", "ERROR", "INVALID: 'x'"]})
    assert run_evals.failure_rate(df) == 1 / 3
    assert run_evals.failure_rate(pd.DataFrame({"failure": ["ERROR"]})) is None
    df["check_failure"] = ["FALSE", "TRUE", "TRUE", "ERROR", "FALSE"]
    assert run_evals.failure_rate(df, "check_failure") == 0.5
