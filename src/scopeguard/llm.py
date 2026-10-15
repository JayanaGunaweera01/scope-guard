"""The open model, run by Ollama on this computer. Nothing here talks to anything but localhost."""

from __future__ import annotations

import json
import os

import httpx

from scopeguard.core import SCHEMA, prompt


def host() -> str:
    h = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434").strip()
    return h if h.startswith("http") else f"http://{h}"


class OllamaClient:
    """Ollama's native API with a JSON Schema in `format`, so decoding is constrained and every reply parses."""

    def __init__(self, model: str | None = None, timeout: float | None = None, transport: httpx.BaseTransport | None = None):
        self.model = model or os.environ.get("SCOPEGUARD_MODEL", "gemma4:e4b")
        self.timeout = timeout or float(os.environ.get("SCOPEGUARD_TIMEOUT_S", "600"))
        self.transport = transport

    def check(self, contract: str, message: str) -> dict:
        body = {"model": self.model, "stream": False, "think": False, "format": SCHEMA,
                "options": {"temperature": 0.1, "num_ctx": 16384},
                "messages": [{"role": "user", "content": prompt(contract, message)}]}
        with httpx.Client(timeout=self.timeout, transport=self.transport) as c:
            r = c.post(f"{host()}/api/chat", json=body)
            r.raise_for_status()
        return json.loads(r.json()["message"]["content"])


class DemoClient:
    """Canned answers for trying the app without a model. It only recognises the demo contract's wording."""

    def check(self, contract: str, message: str) -> dict:
        m = message.casefold()
        reqs = []
        if "round" in m or "colour" in m or "color" in m:
            reqs.append({"summary": "A third round of revisions to the design", "relation": "excluded",
                         "clause_quote": "Two rounds of revisions are included. Further rounds are billed at the hourly rate.",
                         "why": "Both included rounds are used.", "hours_low": 3, "hours_high": 4})
        if "app" in m or "mobile" in m:
            reqs.append({"summary": "A mobile app version of the site", "relation": "not_mentioned", "clause_quote": "",
                         "why": "Nothing in the agreement mentions a mobile app.", "hours_low": 25, "hours_high": 40})
        if "logo" in m:
            reqs.append({"summary": "Make the logo smaller in the header", "relation": "not_mentioned", "clause_quote": "",
                         "why": "A tiny tweak the agreement does not mention.", "hours_low": 0.25, "hours_high": 0.5})
        if "pages" in m:
            reqs.append({"summary": "Build the five pages listed in the proposal", "relation": "covered",
                         "clause_quote": "The project includes five pages: Home, About, Services, Gallery and Contact.",
                         "why": "This is the agreed scope.", "hours_low": 0, "hours_high": 0})
        return {"reply_opening": "Thanks for the kind words, and glad the site is coming together.", "requests": reqs}


DEMO_CONTRACT = """WEB DESIGN AGREEMENT: Jay Creationz Photography

1. Scope. The project includes five pages: Home, About, Services, Gallery and Contact.
2. Revisions. Two rounds of revisions are included. Further rounds are billed at the hourly rate.
3. Content. The client supplies all photographs and text before design begins.
4. Hosting. Hosting and domain registration are arranged and paid for by the client.
5. Payment. 50% on signing and 50% on delivery.
"""
DEMO_MESSAGE = """Hi! The pages look great. Can we do another round on the colours, I'd like them warmer.
Also could you make a mobile app version for my clients to book from? And make the logo a bit smaller. Thanks!"""
