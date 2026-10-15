"""The web app, served only on this computer.

    /                    your clients, and what each has cost you in unbilled work
    /clients/<id>        the contract, paste a client's message, past checks
    /checks/<id>         the verdicts, the clause highlighted in the contract, the change order to send
    /ledger, /ledger.csv everything quoted and everything waived
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Annotated

import httpx
from anyio import to_thread
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from jinja2 import DictLoader, Environment, select_autoescape
from markupsafe import Markup, escape

from scopeguard import core
from scopeguard.store import Store
from scopeguard.templates import TEMPLATES

log = logging.getLogger(__name__)
MAX_MESSAGE = 8000


def highlighted(contract: str, spans: list[tuple[int, int]]) -> Markup:
    """The contract with each cited clause marked, so you can see exactly what the finding rests on."""
    out, pos = [], 0
    for n, (a, b) in enumerate(sorted(s for s in spans if s), start=1):
        if a < pos:
            continue
        out += [escape(contract[pos:a]), Markup(f'<mark id="clause-{n}">'), escape(contract[a:b]), Markup("</mark>")]
        pos = b
    out.append(escape(contract[pos:]))
    return Markup("").join(out)


def create_app(store: Store | None = None, client=None, *, model_label: str = "") -> FastAPI:
    store = store or Store()
    if client is None:
        from scopeguard.llm import OllamaClient

        client = OllamaClient()
    model_label = model_label or getattr(client, "model", "an open model")
    app = FastAPI(title="ScopeGuard", docs_url=None, redoc_url=None)
    app.state.store = store
    env = Environment(loader=DictLoader(TEMPLATES), autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)
    env.globals.update(money=core.money, model_label=model_label)

    def page(name: str, status: int = 200, **ctx) -> HTMLResponse:
        return HTMLResponse(env.get_template(name).render(**ctx), status_code=status)

    def totals(cid: int | None = None) -> dict:
        return core.ledger_summary(store.ledger(cid))

    @app.get("/")
    async def index(error: str = ""):
        rows = [{"c": c, "t": totals(c["id"])} for c in store.clients()]
        return page("index.html", rows=rows, error=error, t=totals())

    @app.post("/clients")
    async def add_client(name: Annotated[str, Form()] = "", contract: Annotated[str, Form()] = "", rate: Annotated[float, Form()] = 50.0,
                         currency: Annotated[str, Form()] = "USD", goodwill: Annotated[float, Form()] = 0.5):
        if not name.strip() or len(contract.split()) < 8 or rate <= 0:
            return RedirectResponse("/?error=Add a client name, a rate above zero and the agreement text.", status_code=303)
        cid = store.add_client(name=name.strip()[:80], contract=contract.strip(), rate=rate, currency=currency.strip()[:6] or "USD",
                               goodwill=max(goodwill, 0))
        return RedirectResponse(f"/clients/{cid}", status_code=303)

    @app.get("/clients/{cid}")
    async def client_page(cid: int, error: str = ""):
        c = store.client(cid)
        if c is None:
            raise HTTPException(404)
        return page("client.html", c=c, checks=store.checks(cid), t=totals(cid), error=error,
                    long=len(c["contract"]) > core.MAX_CONTRACT_CHARS)

    @app.post("/clients/{cid}/check")
    async def run_check(cid: int, message: Annotated[str, Form()] = ""):
        c = store.client(cid)
        if c is None:
            raise HTTPException(404)
        message = message.strip()[:MAX_MESSAGE]
        if not message:
            return RedirectResponse(f"/clients/{cid}?error=Paste the client's message first.", status_code=303)
        try:
            raw = await to_thread.run_sync(client.check, c["contract"], message)
        except (httpx.HTTPError, ValueError, KeyError) as e:
            log.warning("model call failed: %s", e)
            hint = "The model did not answer. Is Ollama running, and is the model pulled? Try `ollama list`."
            return RedirectResponse(f"/clients/{cid}?error={hint}", status_code=303)
        items = core.review(raw, c["contract"], c["rate"], c["goodwill"])
        kid = store.add_check(client_id=cid, message=message, items=items, opening=core.clean_opening(raw.get("reply_opening")))
        return RedirectResponse(f"/checks/{kid}", status_code=303)

    @app.get("/checks/{kid}")
    async def check_page(kid: int):
        k = store.check(kid)
        if k is None:
            raise HTTPException(404)
        c = store.client(k["client_id"])
        spans = [tuple(i["span"]) for i in k["items"] if i.get("span")]
        done = {e["idx"]: e for e in store.ledger(c["id"]) if e["check_id"] == kid}
        reply = core.change_order(c["name"], k["opening"], k["items"], c["currency"])
        return page("check.html", k=k, c=c, contract=highlighted(c["contract"], spans), reply=reply, done=done)

    @app.post("/checks/{kid}/decide")
    async def decide(kid: int, idx: Annotated[int, Form()], decision: Annotated[str, Form()], hours: Annotated[float, Form()] = 0.0):
        k = store.check(kid)
        if k is None or decision not in ("quoted", "waived"):
            raise HTTPException(404)
        c = store.client(k["client_id"])
        hours = min(max(hours, 0.0), core.MAX_HOURS)
        store.decide(kid, idx, decision, hours, round(hours * c["rate"], 2))
        return RedirectResponse(f"/checks/{kid}#item-{idx}", status_code=303)

    @app.get("/ledger")
    async def ledger_page():
        clients = {c["id"]: c for c in store.clients()}
        return page("ledger.html", entries=store.ledger()[::-1], clients=clients, t=totals())

    @app.get("/ledger.csv")
    async def ledger_csv():
        clients = {c["id"]: c for c in store.clients()}
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["date", "client", "request", "decision", "hours", "amount", "currency"])
        for e in store.ledger():
            c = clients.get(e["client_id"], {})
            w.writerow([e["at"][:10], c.get("name", ""), e["summary"], e["decision"], e["hours"], e["amount"], c.get("currency", "")])
        return Response(("\ufeff" + buf.getvalue()).encode("utf-8"), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": 'attachment; filename="scopeguard-ledger.csv"'})

    return app
