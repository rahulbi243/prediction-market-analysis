"""7-step prompt template replicating the paper's LLM forecasting methodology.

Reference: Karkar & Chopra (Nov 2025), §3.1 — "Forecasting Protocol".

Two conditions:
  - raw:  no news context
  - news: news snippets appended after step 3 (reasons against)
"""

from __future__ import annotations

SYSTEM_PROMPT = """\
You are an expert forecasting analyst participating in a structured prediction exercise.
You reason carefully, quantitatively, and avoid over-weighting recent or unconfirmed information.
All probabilities must be expressed as integers from 0 to 100 (inclusive).
Follow the 7-step protocol exactly, using the XML tags shown.
"""

_STEPS = """\
<step1>Rephrase the question in your own words to confirm understanding.</step1>

<step2>List exactly 3 reasons the outcome will NOT happen (NO). \
For each reason assign a weight: Low / Medium / High.</step2>

<step3>List exactly 3 reasons the outcome WILL happen (YES). \
For each reason assign a weight: Low / Medium / High.</step3>

{news_block}

<step4>Aggregate the evidence from steps 2 and 3. \
Describe how the reasons balance against each other.</step4>

<step5>State your INITIAL probability estimate as an integer 0–100. \
Format: INITIAL_PROB: <integer></step5>

<step6>Consider: base rate for this type of event, \
time remaining until resolution, any ambiguities in the resolution criteria. \
Adjust your estimate if necessary and explain why.</step6>

<step7>State your FINAL probability as an integer 0–100, \
and a 90% confidence interval [low, high]. \
Format (one line each):
FINAL_PROB: <integer>
CI_LOW: <integer>
CI_HIGH: <integer>
</step7>
"""

_NEWS_BLOCK = """\
<news_context>
The following news snippets were published before this market opened. \
Use them as additional evidence when completing steps 4–7.

{snippets}
</news_context>
"""


def build_user_prompt(question: str, condition: str, news_snippets: list[dict] | None = None) -> str:
    """Build the user-facing 7-step prompt.

    Args:
        question:      The prediction market question text.
        condition:     "raw" (no news) or "news" (snippets injected after step 3).
        news_snippets: List of dicts with keys title, snippet, url, published_at.
    """
    if condition == "news" and news_snippets:
        snippet_text = "\n\n".join(
            f"[{i+1}] {s.get('title','')}\n{s.get('snippet','')}"
            for i, s in enumerate(news_snippets[:10])
        )
        news_block = _NEWS_BLOCK.format(snippets=snippet_text)
    else:
        news_block = ""

    steps = _STEPS.format(news_block=news_block)
    return f"QUESTION: {question}\n\n{steps}"
