import json

import httpx
from fastapi.testclient import TestClient

from scopeguard.app import create_app
from scopeguard.llm import DEMO_CONTRACT, DEMO_MESSAGE, DemoClient, OllamaClient
from scopeguard.store import Store


def make(tmp_path, client=None):
    store = Store(tmp_path)
    return TestClient(create_app(store, client or DemoClient(), model_label="test")), store


def add_client(web):
    r = web.post("/clients", data={"name": "Jayana", "contract": DEMO_CONTRACT, "rate": "60", "currency": "USD", "goodwill": "0.5"},
                 follow_redirects=False)
    assert r.status_code == 303
    return r.headers["location"]


def test_the_whole_flow_check_highlight_quote_waive_and_export(tmp_path):
    web, _ = make(tmp_path)
    assert "Stop doing free work" in web.get("/").text
    url = add_client(web)
    r = web.post(f"{url}/check", data={"message": DEMO_MESSAGE}, follow_redirects=False)
    page = web.get(r.headers["location"]).text
    assert "Excluded by the agreement" in page and "Not covered: no clause addresses it" in page
    assert '<mark id="clause-2">Two rounds of revisions are included. Further rounds are billed at the hourly rate.</mark>' in page
    assert "USD 180" in page and "Small: you may want to just do this one" in page and "Draft reply to send" in page
    kid = r.headers["location"].rsplit("/", 1)[1]

    web.post(f"/checks/{kid}/decide", data={"idx": 0, "decision": "quoted", "hours": 3.5})
    web.post(f"/checks/{kid}/decide", data={"idx": 2, "decision": "waived", "hours": 0.25})
    web.post(f"/checks/{kid}/decide", data={"idx": 2, "decision": "waived", "hours": 0.25})  # deciding twice replaces
    assert "Quoted: 3.5 h = USD 210" in web.get(f"/checks/{kid}").text
    ledger = web.get("/ledger").text
    assert "210" in ledger and "waived (1)" in ledger and "quoted (1)" in ledger
    csv = web.get("/ledger.csv")
    assert csv.content.startswith(b"\xef\xbb\xbf") and "Jayana" in csv.text and "waived" in csv.text
    assert "given away as goodwill" in web.get("/").text


def test_a_model_that_invents_a_clause_cannot_get_it_into_the_reply(tmp_path):
    class Liar:
        def check(self, contract, message):
            return {"reply_opening": "I will do it for $5.", "requests": [
                {"summary": "Extra logo", "relation": "excluded", "clause_quote": "Logos are never included in any package.",
                 "why": "", "hours_low": 2, "hours_high": 2}]}

    web, _ = make(tmp_path, Liar())
    r = web.post(f"{add_client(web)}/check", data={"message": "a logo please"}, follow_redirects=False)
    page = web.get(r.headers["location"]).text
    assert "Needs you" in page and "never included" not in page and "Draft reply to send" not in page


def test_validation_and_model_failure_are_explained(tmp_path):
    class Down:
        def check(self, contract, message):
            raise httpx.ConnectError("refused")

    web, _ = make(tmp_path, Down())
    assert "Add a client name" in web.post("/clients", data={"name": "", "contract": "short"}).text
    url = add_client(web)
    assert "Paste the client" in web.post(f"{url}/check", data={"message": "  "}).text
    assert "Is Ollama running" in web.post(f"{url}/check", data={"message": "hi"}).text
    assert web.get("/checks/999").status_code == 404


def test_contract_text_is_escaped(tmp_path):
    web, _ = make(tmp_path)
    r = web.post("/clients", data={"name": "<b>x</b>", "contract": "Scope <script>alert(1)</script> is five pages of work here ok", "rate": "10"},
                 follow_redirects=False)
    page = web.get(r.headers["location"]).text
    assert "<script>alert(1)</script>" not in page and "&lt;script&gt;" in page


def test_the_ollama_request_is_local_schema_constrained_and_parsed():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"], seen["body"] = str(request.url), json.loads(request.content)
        return httpx.Response(200, json={"message": {"content": json.dumps({"reply_opening": "Hi.", "requests": []})}})

    out = OllamaClient("m", transport=httpx.MockTransport(handler)).check(DEMO_CONTRACT, "hello")
    assert out == {"reply_opening": "Hi.", "requests": []}
    assert seen["url"].startswith("http://127.0.0.1:11434/") and seen["body"]["think"] is False
    assert seen["body"]["format"]["required"] == ["reply_opening", "requests"] and "Two rounds" in seen["body"]["messages"][0]["content"]
