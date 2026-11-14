# Multi-Agent Article Writer

An orchestrator agent researches a topic, picks the right writer for it, and produces a sourced article with a generated hero image.

> Status: notebook prototype being packaged into a command line tool.

## The problem
TODO: why a single prompt produces thin, poorly sourced articles, and why one writing style does not fit every topic.

## The solution
TODO: research agent with web search and page extraction, image agent, journalist and storyteller writer agents selected by a typed handoff, guardrails, and LLM-judge evals on source breadth.

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
- TODO

## About
Built by S. Bruce Hill. Product brief: [docs/product-brief.md](docs/product-brief.md).
