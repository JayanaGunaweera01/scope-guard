from scopeguard import core
from scopeguard.llm import DEMO_CONTRACT

CLAUSE = "Two rounds of revisions are included. Further rounds are billed at the hourly rate."


def req(**kw):
    base = {"summary": "x", "relation": "not_mentioned", "clause_quote": "", "why": "", "hours_low": 1, "hours_high": 2}
    return {**base, **kw}


def test_quote_is_found_despite_case_punctuation_and_line_breaks():
    messy = "two ROUNDS of revisions are included;\nfurther rounds are billed at the hourly rate"
    span = core.locate(messy, DEMO_CONTRACT)
    assert span and DEMO_CONTRACT[span[0]:span[1]] == CLAUSE


def test_a_changed_word_is_not_found():
    assert core.locate("Three rounds of revisions are included.", DEMO_CONTRACT) is None
    assert core.locate("rate", DEMO_CONTRACT) is None  # too short to count as a citation


def test_an_invented_clause_is_downgraded_and_discarded():
    raw = {"requests": [req(summary="Extra page", relation="excluded", clause_quote="No additional pages shall ever be built.")]}
    [item] = core.review(raw, DEMO_CONTRACT, 50, 0.5)
    assert item["relation"] == "unverified" and item["quote"] == "" and not item["billable"] and "not in the contract" in item["note"]


def test_a_real_clause_is_verified_and_the_exact_contract_text_is_used():
    raw = {"requests": [req(summary="Round 3", relation="excluded", clause_quote="further rounds are billed at the hourly rate")]}
    [item] = core.review(raw, DEMO_CONTRACT, 50, 0.5)
    assert item["relation"] == "excluded" and item["quote"] == "Further rounds are billed at the hourly rate." and item["billable"]


def test_silence_is_never_called_exclusion_and_a_quote_is_ignored():
    raw = {"requests": [req(summary="App", relation="not_mentioned", clause_quote="Hosting and domain registration are arranged")]}
    [item] = core.review(raw, DEMO_CONTRACT, 50, 0.5)
    assert item["relation"] == "not_mentioned" and item["quote"] == "" and "no clause addresses it" in item["verdict"]


def test_prices_are_hours_times_rate_and_hours_are_sane():
    raw = {"requests": [req(hours_low=4.1, hours_high=2.9), req(summary="y", hours_low=-5, hours_high=9999), req(summary="z", hours_low="lots")]}
    a, b, c = core.review(raw, DEMO_CONTRACT, 60, 0.5)
    assert (a["hours_low"], a["hours_high"], a["price_low"], a["price_high"]) == (3.0, 4.0, 180.0, 240.0)
    assert (b["hours_low"], b["hours_high"]) == (0.0, 200.0) and (c["hours_low"], c["hours_high"]) == (0.0, 2.0)


def test_small_requests_are_flagged_for_goodwill():
    small, big = core.review({"requests": [req(hours_low=0.25, hours_high=0.5), req(summary="b", hours_low=2, hours_high=3)]},
                             DEMO_CONTRACT, 60, 0.5)
    assert small["small"] and not big["small"]


def test_the_model_cannot_put_a_number_in_the_reply():
    assert core.clean_opening("I can do this for $500!") == core.DEFAULT_OPENING
    assert core.clean_opening("x" * 300) == core.DEFAULT_OPENING
    assert core.clean_opening("Thanks, happy to help.") == "Thanks, happy to help."


def test_change_order_only_lists_billable_items_with_the_real_clause():
    raw = {"reply_opening": "Thanks for the note.", "requests": [
        req(summary="Round 3", relation="excluded", clause_quote=CLAUSE, hours_low=3, hours_high=4),
        req(summary="Build the pages", relation="covered", clause_quote="The project includes five pages", hours_low=0, hours_high=0),
        req(summary="Mobile app", hours_low=25, hours_high=25)]}
    items = core.review(raw, DEMO_CONTRACT, 60, 0.5)
    text = core.change_order("Jayana", raw["reply_opening"], items, "USD")
    assert "Round 3: about 3\u20134 h, USD 180\u2013240" in text and "Further rounds are billed at the hourly rate." in text
    assert "Mobile app: about 25 h, USD 1,500 (no part of the agreement covers it)" in text
    assert "Build the pages" not in text and "Estimated total: USD 1,680\u20131,740." in text
    assert core.change_order("x", "", core.review({"requests": [raw["requests"][1]]}, DEMO_CONTRACT, 60, 0.5), "USD") == ""
