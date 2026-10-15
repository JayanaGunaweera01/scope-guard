"""The rules. A model reads the contract and a client's message and *proposes* findings; this module decides
which of them count.

1. **A clause must be real.** Any "covered" or "excluded" verdict has to quote the contract, and the quote must
   be found in the contract text (ignoring case, punctuation and line breaks). If it is not, the verdict is
   downgraded to "unverified" and the quote is thrown away. A model cannot cite a clause that is not there.
2. **Silence is not exclusion.** If no clause speaks to the request ("not_mentioned") it is shown as exactly
   that, never as "the contract forbids it". Different footing, different wording to the client.
3. **The model never writes a number.** Hours are its estimate, shown as a range and labelled as one. Prices are
   hours times the freelancer's own rate, computed here. The model's opening line is dropped if it contains a digit.
4. **Small asks stay human.** A billable request at or under the freelancer's goodwill threshold is flagged as a
   candidate to waive, and waiving is recorded, so the goodwill given away is visible.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

RELATIONS = ("covered", "excluded", "not_mentioned")
MIN_QUOTE_WORDS = 3
MAX_HOURS = 200.0
MAX_CONTRACT_CHARS = 24000
DEFAULT_OPENING = "Thanks for this. I've had a look against what we agreed."

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "reply_opening": {"type": "string"},
        "requests": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "relation": {"type": "string", "enum": list(RELATIONS)},
                "clause_quote": {"type": "string"},
                "why": {"type": "string"},
                "hours_low": {"type": "number"},
                "hours_high": {"type": "number"},
            },
            "required": ["summary", "relation", "clause_quote", "why", "hours_low", "hours_high"],
            "additionalProperties": False}},
    },
    "required": ["reply_opening", "requests"],
    "additionalProperties": False,
}


# --- finding a clause in the contract -----------------------------------------------------------------


def _norm(token: str) -> str:
    token = unicodedata.normalize("NFKC", token).casefold()
    start, end = 0, len(token)
    while start < end and unicodedata.category(token[start])[0] in "PS":
        start += 1
    while end > start and unicodedata.category(token[end - 1])[0] in "PS":
        end -= 1
    return token[start:end]


def _tokens(text: str) -> list[tuple[str, int, int]]:
    out = []
    for m in re.finditer(r"\S+", text):
        n = _norm(m.group())
        if n:
            out.append((n, m.start(), m.end()))
    return out


def locate(quote: str, contract: str) -> tuple[int, int] | None:
    """Where `quote` sits in `contract` as (start, end) characters, or None. Whitespace, case and
    punctuation differences are ignored; a different word is not."""
    q = [t[0] for t in _tokens(quote or "")]
    if len(q) < MIN_QUOTE_WORDS:
        return None
    c = _tokens(contract)
    words = [t[0] for t in c]
    for i in range(len(words) - len(q) + 1):
        if words[i:i + len(q)] == q:
            return c[i][1], c[i + len(q) - 1][2]
    return None


# --- turning a model reply into verified findings -----------------------------------------------------


def _hours(raw: Any) -> float:
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return 0.0
    return min(max(v, 0.0), MAX_HOURS)


def _q(h: float) -> float:
    return round(h * 4) / 4  # quarter hours: nobody quotes 1.37 hours


def money(x: float) -> str:
    return f"{x:,.0f}" if abs(x - round(x)) < 0.005 else f"{x:,.2f}"


VERDICT = {"covered": "Covered by the agreement",
           "excluded": "Excluded by the agreement",
           "not_mentioned": "Not covered: no clause addresses it",
           "unverified": "Needs you: the model's cited clause could not be found"}


def review(raw: dict, contract: str, rate: float, goodwill_hours: float) -> list[dict]:
    items = []
    for r in (raw.get("requests") or [])[:12]:
        if not isinstance(r, dict) or not str(r.get("summary") or "").strip():
            continue
        relation = r.get("relation") if r.get("relation") in RELATIONS else "unverified"
        quote, span, note = "", None, ""
        if relation in ("covered", "excluded"):
            span = locate(str(r.get("clause_quote") or ""), contract)
            if span:
                quote = contract[span[0]:span[1]]
            else:
                note = "The model claimed a clause but quoted text that is not in the contract, so the claim was dropped."
                relation = "unverified"
        lo, hi = sorted((_q(_hours(r.get("hours_low"))), _q(_hours(r.get("hours_high")))))
        billable = relation in ("excluded", "not_mentioned")
        items.append({
            "summary": " ".join(str(r["summary"]).split())[:200], "why": " ".join(str(r.get("why") or "").split())[:400],
            "relation": relation, "verdict": VERDICT[relation], "quote": quote, "span": span, "note": note,
            "hours_low": lo, "hours_high": hi, "price_low": round(lo * rate, 2), "price_high": round(hi * rate, 2),
            "billable": billable, "small": billable and hi <= goodwill_hours})
    return items


def clean_opening(text: Any) -> str:
    text = " ".join(str(text or "").split())
    return text if text and len(text) <= 200 and not re.search(r"\d", text) else DEFAULT_OPENING


def _range(lo: float, hi: float, fmt) -> str:
    return fmt(hi) if lo == hi else f"{fmt(lo)}\u2013{fmt(hi)}"


def change_order(name: str, opening: str, items: list[dict], currency: str) -> str:
    """The client-facing message, assembled from verified parts only."""
    todo = [i for i in items if i["billable"]]
    if not todo:
        return ""
    lines = [f"Hi {name or 'there'},", "", clean_opening(opening), "",
             "These items are outside what we agreed, so I'd like to quote them separately:", ""]
    for i in todo:
        hours = _range(i["hours_low"], i["hours_high"], lambda h: f"{h:g}") + " h"
        price = f"{currency} " + _range(i["price_low"], i["price_high"], money)
        basis = f"the agreement says: \u201c{i['quote']}\u201d" if i["relation"] == "excluded" else "no part of the agreement covers it"
        lines.append(f"- {i['summary']}: about {hours}, {price} ({basis})")
    lo, hi = sum(i["price_low"] for i in todo), sum(i["price_high"] for i in todo)
    lines += ["", f"Estimated total: {currency} {_range(lo, hi, money)}. Happy to start as soon as you confirm.", ""]
    return "\n".join(lines)


def prompt(contract: str, message: str) -> str:
    return f"""You are checking a freelancer's client message against the freelancer's signed agreement.

Split the client's message into separate requests for work. For each request decide:
- "covered": the agreement clearly includes it. Quote the clause.
- "excluded": the agreement clearly excludes or limits it (revision rounds used up, a different deliverable). Quote the clause.
- "not_mentioned": no clause speaks to it either way. Leave clause_quote empty.

Rules:
- "clause_quote" must be copied word for word from the agreement below, a sentence or part of a sentence. Never paraphrase it and never invent one.
- Questions, thanks and small talk are not requests. Leave them out.
- "hours_low" and "hours_high": your honest estimate of the hours a competent freelancer needs.
- "why": one short sentence for the freelancer.
- "reply_opening": one warm, neutral sentence to start a reply to the client. No numbers, no prices, no promises.

AGREEMENT
{contract[:MAX_CONTRACT_CHARS]}

CLIENT MESSAGE
{message}

Reply with only the JSON object."""


def ledger_summary(entries: list[dict]) -> dict:
    """What the freelancer has quoted, and what they have given away. Both in hours and money."""
    out = {"quoted_hours": 0.0, "quoted_amount": 0.0, "waived_hours": 0.0, "waived_amount": 0.0, "quoted": 0, "waived": 0}
    for e in entries:
        k = "quoted" if e["decision"] == "quoted" else "waived"
        out[f"{k}_hours"] += e["hours"]
        out[f"{k}_amount"] += e["amount"]
        out[k] += 1
    return out
