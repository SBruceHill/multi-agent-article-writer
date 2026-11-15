"""LLM judge for source breadth: does a research brief cite at least 3 distinct sources?"""

from article_writer.config import JUDGE_MODEL, get_openai_client

JUDGE_PROMPT = """
# Judge Prompt: Insufficient Source Breadth (TRUE/FALSE)

You are scoring a research agent **transcript/trace** to determine if the final **research brief** failed to reference at least 3 different sources.
Return **only** `TRUE` or `FALSE`.

## Definitions

**Research brief:** The final deliverable the agent hands back to the user. Evaluate only the brief itself, not intermediate tool calls, search results, scratch notes, or reasoning steps in the trace.

**Source:** Any identifiable external origin of information that the brief references, in any form. Formal citation is NOT required. All of the following count:
- A URL or hyperlink
- A named publication, organization, report, dataset, paper, or website (e.g., "according to the Federal Reserve's 2025 Beige Book," "Gartner estimates," "a McKinsey survey found")
- A footnote, endnote, or "Sources" list entry
- An inline mention that ties a specific claim to a specific named origin

**Distinct source:** A separate document or publication. Count each one once, no matter how many times it is referenced.
- The same article cited three times = 1 source
- Two different articles from the same outlet or domain = 2 sources
- The same report referenced by full title in one place and by short name in another = 1 source

**Does NOT count as a source:**
- Vague attributions with no identifiable origin ("studies show," "experts say," "industry data suggests," "it is widely reported")
- The user's own prompt, instructions, or files the user supplied as task input
- The agent's own analysis, reasoning, or general knowledge
- Sources that appear only in the trace (searched, fetched, or read) but are never referenced in the brief

## Insufficient breadth (label TRUE): Any of the below occurred

1. **Fewer than 3 distinct sources:** After deduplication, the brief references 2 or fewer distinct sources.
2. **Padding through repetition:** The brief appears to reference 3 or more sources, but after applying the deduplication rules above the count falls below 3.
3. **Vague attribution only:** The brief relies on unattributed claims ("research indicates...") such that fewer than 3 identifiable sources remain.
4. **Research done but not used:** The trace shows the agent consulted 3 or more sources, but the brief references fewer than 3 of them.
5. **No brief delivered:** The agent did not produce a research brief, or the deliverable is empty or truncated before any substantive content.

## Sufficient breadth (label FALSE)

The brief references **3 or more distinct, identifiable sources**, counted under the rules above. Do not penalize for citation format, citation style, missing dates, missing page numbers, or source quality. Do not attempt to verify whether a source exists or supports the claim it is attached to. This judge measures breadth only.

## Output Format

Return exactly one token: `TRUE` or `FALSE`. No explanations.
"""


def judge(brief: str) -> str:
    """Score a brief: TRUE means insufficient source breadth, FALSE means sufficient.

    Any other judge reply is returned as "INVALID: <reply>".
    """
    resp = get_openai_client().responses.create(
        model=JUDGE_MODEL,
        instructions=JUDGE_PROMPT,
        input=f"<research_brief>\n{brief}\n</research_brief>",
    )
    label = resp.output_text.strip().strip("`").upper()
    return label if label in {"TRUE", "FALSE"} else f"INVALID: {resp.output_text!r}"
