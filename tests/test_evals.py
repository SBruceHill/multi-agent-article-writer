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
        return f"brief for {topic}"

    monkeypatch.setattr(run_evals, "run_research", fake_research)
    monkeypatch.setattr(run_evals, "judge", lambda brief: "FALSE")
    topics = ["a", "bad", "c", "d", "e"]
    monkeypatch.setattr(run_evals, "TOPICS", topics)

    rows = asyncio.run(run_evals.evaluate_all(topics, workers=2))

    assert [r["topic"] for r in rows] == topics
    assert [r["failure"] for r in rows] == ["FALSE", "ERROR", "FALSE", "FALSE", "FALSE"]
    assert "boom" in rows[1]["brief"]
    assert peak == 2


def test_failure_rate_counts_only_scored_runs():
    df = pd.DataFrame({"failure": ["TRUE", "FALSE", "FALSE", "ERROR", "INVALID: 'x'"]})
    assert run_evals.failure_rate(df) == 1 / 3
    assert run_evals.failure_rate(pd.DataFrame({"failure": ["ERROR"]})) is None
