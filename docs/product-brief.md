# Product brief: Multi-Agent Article Writer

Status: Draft. No users yet. The Product and Personas sections are working assumptions, not validated with users. J1 is drafted from the code as it stands.

## Product
Status: Draft
- **One-sentence job:** Turn a topic into a first draft article with a hero image, written in a style chosen for the topic, from a brief that cites only web pages the system actually read.
- **Who it is for:** Small content teams (one to five people) that publish explainers or features and need every claim in a draft traceable to a source an editor can check.
- **Who pays, or who benefits in a real deployment:** The content or marketing lead who owns the budget pays. Writers and editors benefit: research, sources, and a first draft arrive together, and the editor's job becomes checking and revising, not starting from a blank page.
- **Why this instead of a general chat assistant:** A chat assistant can search and cite, but the user can't set or check its sourcing rules. Here the rule (at least 4 pages read in full, nothing cited that was not read) is enforced in code, the writing styles are fixed prompts chosen per topic with a recorded reason, and each run leaves a trace. Article quality has not been compared with chat assistants.
- **Fits the team's voice:** The team can add writer personas for its own styles (for example a house explainer voice or a product update voice). The orchestrator still chooses one writer per topic, now from a wider set. Each persona is a new prompt and a few lines of code, not a configuration setting, and only the two built in writers have been run so far.
- **Not a customer yet:** Teams that need breaking news, publish ready copy with no editor, or research from private or paywalled sources. The system reads only public web pages and produces drafts for an editor to review.

## Personas
Status: Draft
| Persona | Job they hire this for | Done looks like |
|---|---|---|
| Content lead at a small team | Get a first draft on a new topic, with sources they can check, without doing the research by hand | A Markdown draft with a hero image and a Sources list where every entry is a page the system read, ready for an editor |

## Journeys

### J1: Topic in, article out (proof journey)
Status: Draft
- **Persona:** Content lead at a small team
- **Trigger:** They have a topic to cover and no draft or research yet.
- **Steps** (actor and verb; what is true after each step):
  1. The content lead runs `article-writer "topic"`. The CLI checks for `OPENAI_API_KEY`. After: the orchestrator has the topic as its input.
  2. The orchestrator calls the research agent twice, with slightly different inputs. Each call searches the web, reads at least 4 pages of at least 2,000 characters each, and writes a brief. A brief that fails the source check (missing `## Sources`, cites pages it did not read, or cites fewer than 4 read pages) is sent back with the check's feedback, up to 2 times. After: the orchestrator holds two briefs, or an error message in place of a brief that never passed.
  3. The orchestrator picks one brief without combining them. After: one selected brief.
  4. The orchestrator calls the image agent with the topic and a short summary of the brief. After: a hero image is saved under `output/images/`, or the orchestrator has an error message instead of a path.
  5. The orchestrator hands off to the journalist or the storyteller, passing a `WriterSelectionInfo` (which writer, and why). After: the choice and reason are logged and recorded in the trace.
  6. The writer writes the article from the brief and the image path. The CLI saves it as `output/<slug>.md`, rewrites the image link so it resolves from that folder, and prints the file path and the writer used. After: the article file exists on disk.
  7. The content lead reads the draft and checks its sources before editing or publishing. After: a reviewed draft. (This step happens outside the system.)
- **Outcome** (what exists in the world when it works): A Markdown article on disk with a hero image at the top, written in the chosen style from a brief that cites only pages the research agent read, plus a trace showing both research calls, the image call, and the handoff.
- **Fail line** (where it stops, or which journey takes over): The run stops with exit code 1 if the API key is missing, and with exit code 2 and no file if the orchestrator ends without handing off to a writer. Going past `--max-turns` raises an SDK error that the CLI does not handle yet. A research call that fails the source check after its retries, or a failed image, comes back to the orchestrator as an error message; the code does not stop the run in those cases. Fact checking and publishing are not part of J1 and stay with the content lead.

## Release 1
- **Proof journey:** J1
- **Other journeys required for the proof to be true:** TODO

## Decisions
| ID | Decision | Binds to step | Status |
|---|---|---|---|
| D-001 | TODO | J1, step N | Draft |

## Parked
Future journeys or needs that are not part of Release 1.
- TODO
