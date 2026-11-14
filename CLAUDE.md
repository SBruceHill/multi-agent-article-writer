# Working in this repo

Portfolio project: a multi-agent system (OpenAI Agents SDK) where an orchestrator coordinates a research agent, an image agent, and two writer agents chosen by handoff, with Pydantic-typed handoffs, guardrails, traces, and LLM-judge evals.

This repo is private until Bruce decides to publish it. Do not push, change visibility, or create remotes unless asked.

## Writing rules (README, docs, comments, commit messages)
- Never use em dashes, or hyphens and en dashes as punctuation. Use commas, colons, parentheses, or a new sentence.
- Plain, specific language. No hype words ("robust", "seamless", "cutting-edge", "leverage").
- State real results only. If a number or claim is not backed by code or an eval in this repo, leave a TODO for Bruce.

## README structure (keep this order)
1. Title and one-line tagline
2. The problem
3. The solution
4. In action (screenshots, demo link)
5. Architecture, written in system design interview order:
   - Requirements (functional, then non-functional)
   - API and interfaces (actual endpoints or entry points, with inputs and outputs)
   - High-level design (Mermaid diagram; RAG systems show ingestion and query as separate pipelines)
   - Evals (what is measured, how, results table)
   - Trade-offs and design decisions (table: decision, alternatives, why)
6. Tech stack (table with a "Why" column)
7. Quick start
8. Project structure (annotated tree)
9. Deploying this at a customer (owners, integrations, data access, pilot, human in the loop)
10. Roadmap (built vs. proposed, kept separate)

## Product brief
`docs/product-brief.md` follows Product, Persona, Journey, Steps, Outcome, Fail line. Do not invent product facts. Mark anything Bruce has not confirmed as `Status: Draft`.

## Manual vs. AI-assisted work
Some work here is deliberately hand-coded so Bruce learns it for interviews. If a request says "manual", or a file or function is marked `# MANUAL`, explain, review, and answer questions, but do not write the implementation.

## Conventions
- Python 3.11+. Lint with `ruff check .`; test with `pytest`.
- Secrets live only in `.env` (gitignored). When adding a variable, add it to `.env.example`.
- Commit notebooks with outputs cleared.
