# Multi-Agent Article Writer

An orchestrator agent researches a topic, picks the right writer for it, and produces a sourced article with a generated hero image.

> Status: notebook prototype being packaged into a command line tool.

## The problem
TODO: why a single prompt produces thin, poorly sourced articles, and why one writing style does not fit every topic.

## The solution
TODO: research agent with web search and page extraction, image agent, journalist and storyteller writer agents selected by a typed handoff, and LLM-judge evals on source breadth.

## In action
TODO: screenshots or a short GIF, plus the demo link.

## Architecture

### Requirements
**Functional**
- TODO

**Non-functional**
- TODO (latency, cost per run, reliability, privacy)

### API and interfaces
| Endpoint or entry point | Input | Output |
|---|---|---|
| TODO | TODO | TODO |

### High-level design
```mermaid
flowchart LR
    A[TODO] --> B[TODO]
```

### Evals
TODO: what is measured, how it is measured, and a results table.

### Trade-offs and design decisions
| Decision | Alternatives considered | Why |
|---|---|---|
| TODO | TODO | TODO |

## Tech stack
| Tool | Role | Why |
|---|---|---|
| TODO | TODO | TODO |

## Quick start
```bash
git clone TODO
cd TODO
python -m venv .venv
# Windows: .venv\Scripts\activate   macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # then add your keys
```

## Project structure
TODO: annotated tree.

## Deploying this at a customer
TODO: who owns what, integrations, data access, pilot plan, where a human stays in the loop.

## Roadmap
**Built**
- TODO

**Proposed**
- Input and output guardrails
- Source judging: two research designs to compare. The current design (A) runs the research agent twice and the orchestrator keeps the better brief. It judges the finished text, not the sources behind it, and the second call repeats the first instead of filling gaps. The alternative (B) moves evaluation into the research step: the agent reads more than the required number of candidate sources, an evaluator keeps the best ones (for example by credibility, relevance, and variety of domains), and one brief is written from only those. The hypothesis is that B produces better sourced articles at similar or lower cost, because it spends effort on the sources and writes one brief instead of two. This is untested. A fair comparison runs the same topics through both designs and scores the briefs with the source breadth judge plus a second judge for article quality, since breadth alone only shows whether a design reaches enough sources. The evaluator would need explicit criteria and a typed output (the chosen URLs and a reason for each).

## About
Built by S. Bruce Hill. Product brief: [docs/product-brief.md](docs/product-brief.md).
