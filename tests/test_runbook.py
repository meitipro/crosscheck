"""
The demo, replayed offline.

scripts/demo.py puts the demo on StudioNet from scripts/demo_data.py (STEPS).
This file replays the same steps against the real contract in the simulator,
mocking the fetch of the four sources so the pure logic is checked before a
single transaction is spent on it. The two Wikipedia articles are mocked with
short stand-ins here; the live demo fetches the real pages.

When deployments/studionet.json exists, the replay goes further: it feeds the
simulator the labels the validators actually agreed on, source by source, and
checks that the contract in this repository pays exactly what the deployed
one did, and refuses exactly where it refused.

    pytest tests/test_runbook.py -v
"""

import collections
import hashlib
import importlib.util
import json
import pathlib

import pytest

import glsim as S

CONTRACT_PATH = "contracts/crosscheck.py"
M = S.load_contract(CONTRACT_PATH)
RECORD = pathlib.Path("deployments/studionet.json")

_spec = importlib.util.spec_from_file_location("demo_data", "scripts/demo_data.py")
D = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(D)

WHO = {"funder": "0x" + "a1" * 20, "solver": "0x" + "b2" * 20, "solver2": "0x" + "c3" * 20,
       "stranger": "0x" + "f6" * 20}
T0 = 1_790_000_000

PAGES = {
    D.EN: "MARK-EN The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris. "
          "Constructed from 1887 to 1889 as the entrance arch to the 1889 World's Fair.",
    D.FR: "MARK-FR La tour Eiffel est une tour de fer de 330 metres, achevee en 1889, "
          "situee a Paris sur le Champ-de-Mars.",
    D.GAZETTEER: pathlib.Path("demo/sources/gazetteer.md").read_text(encoding="utf-8"),
    D.ALMANAC: pathlib.Path("demo/sources/almanac_1899.md").read_text(encoding="utf-8"),
}
MARK = {D.EN: "MARK-EN", D.FR: "MARK-FR", D.GAZETTEER: "Gazetteer of Paris", D.ALMANAC: "Almanac of Monuments"}


def model(label_of):
    def answer(prompt):
        for url, mark in MARK.items():
            if mark in prompt and url in label_of:
                order = M.FORWARD if "[0] states:" in prompt else M.REVERSED
                return {"option": str(order.index(label_of[url])), "because": "replayed"}
        raise S.UserError("a prompt about a page this replay never wrote")
    return answer


def replay(labels, who=WHO):
    """Run STEPS. `labels` are what the ok answers come back with, in order:
    one label per source, in the order the funder listed them."""
    S.reset_transfers()
    c = S.deploy(CONTRACT_PATH)
    queue = [list(x) for x in labels]
    outcomes = []
    clock = T0
    for step in D.STEPS:
        actor, method, spec, value, expect, label = step[:6]
        clock += 30
        tag = next((t for t in step[6:] if t.startswith("after_close:")), None)
        if tag:
            qid = int(tag.split(":")[1])
            clock = max(clock, M.seconds(c.question(qid)["deadline"]) + 20)
        S.set_time(M.iso(clock))
        S.set_mocks()
        if method == "answer" and expect == "ok":
            urls = c.question(spec[0])["sources"]
            want = queue.pop(0)
            S.set_mocks(leader_pages=dict(PAGES), leader_prompts={"<options>": model(dict(zip(urls, want)))})
        S.set_sender(who[actor])
        args = [who[a] if a in who else a for a in spec]
        try:
            S.call(c, method, *args, value=value)
            outcomes.append(("ok", ""))
        except S.UserError as e:
            outcomes.append(("refused", e.message))
    return c, outcomes


def received():
    out = collections.Counter()
    for to, v in S.transfers():
        out[str(to).lower()] += v
    return out


class TestDemoData:
    def test_every_value_the_demo_sends_passes_the_bounds(self):
        assert M.MIN_QUESTION <= len(D.QUESTION) <= M.MAX_QUESTION
        assert M.MIN_CLAIM <= len(D.CLAIM) <= M.MAX_CLAIM
        assert 1 <= D.BOUNTY <= M.MAX_AMOUNT and M.MIN_WINDOW <= D.WINDOW <= M.MAX_WINDOW
        for sources in (D.SOURCES_0, D.SOURCES_1):
            assert M.sources_problem(M.split_sources(sources)) == ""
            assert 1 <= D.QUORUM <= len(M.split_sources(sources))

    def test_the_two_small_pages_are_real_files_in_this_repository(self):
        for url in (D.GAZETTEER, D.ALMANAC):
            assert len(PAGES[url].strip()) >= M.MIN_PAGE
        assert "1889" not in PAGES[D.GAZETTEER] and "1899" in PAGES[D.ALMANAC]

    def test_the_demo_urls_point_at_those_files(self):
        assert D.GAZETTEER.endswith("/demo/sources/gazetteer.md") and D.ALMANAC.endswith("/demo/sources/almanac_1899.md")

    def test_the_window_outlasts_the_steps_meant_to_land_inside_it(self):
        """Three answers (each fetches three pages and asks six questions, up
        to 180 s) and three other transactions (up to 60 s) land before
        question 1's window closes."""
        assert D.WINDOW >= 3 * 180 + 3 * 60 + 120


class TestReplay:
    def test_the_demo_succeeds_and_refuses_exactly_where_it_says(self):
        _, outcomes = replay(D.EXPECTED_LABELS)
        assert [o for o, _ in outcomes] == [s[4] for s in D.STEPS]

    def test_the_refusals_say_why(self):
        _, outcomes = replay(D.EXPECTED_LABELS)
        msgs = [m for o, m in outcomes if o == "refused"]
        wants = ["the funder cannot answer its own question", "this question is paid", "a solver answers once",
                 "the question is open until", "deadline passed"]
        assert len(msgs) == len(wants)
        for msg, want in zip(msgs, wants):
            assert want in msg, (want, msg)

    def test_the_first_question_pays_and_the_second_is_vetoed_and_refunded(self):
        c, _ = replay(D.EXPECTED_LABELS)
        q0, q1 = c.question(0), c.question(1)
        assert (q0["status"], q0["paid_to"], q0["winner"]) == ("paid", "solver", WHO["solver"])
        assert (q1["status"], q1["paid_to"], q1["winner"]) == ("refunded", "funder", "")
        a0, a1 = c.attempts_of(0)["attempts"], c.attempts_of(1)["attempts"]
        assert [(a["labels"], a["verdict"]) for a in a0] == [(["states", "states", "silent"], "accepted")]
        assert [(a["labels"], a["verdict"]) for a in a1] == [(["states", "states", "contradicts"], "rejected")]
        got = received()
        assert got[WHO["solver"]] == D.BOUNTY and got[WHO["funder"]] == D.BOUNTY and c.held_total() == 0


@pytest.mark.skipif(not RECORD.exists(), reason="no deployment recorded yet: python scripts/demo.py")
class TestTheRecord:
    """The live run, checked against this repository."""

    def _record(self):
        return json.loads(RECORD.read_text(encoding="utf-8"))

    def _labels(self, rec):
        rows = [a for q in rec["attempts"] for a in q["attempts"]]
        return [a["labels"] for a in sorted(rows, key=lambda a: a["id"])]

    def test_the_record_is_of_this_source(self):
        here = hashlib.sha256(pathlib.Path(CONTRACT_PATH).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        assert self._record()["source_sha256"] == here, "the deployed contract is not this file; redeploy"

    def test_every_step_on_chain_did_what_the_demo_expected(self):
        steps = [s for s in self._record()["steps"] if s["step"] != "deploy"]
        assert [("ok" if s["ok"] else "refused") for s in steps] == [s[4] for s in D.STEPS]

    def test_this_contract_pays_what_the_deployed_one_paid(self):
        rec = self._record()
        c, outcomes = replay(self._labels(rec), who=rec["accounts"])
        assert [o for o, _ in outcomes] == [s[4] for s in D.STEPS]
        for k, theirs in enumerate(rec["questions"]):
            mine = c.question(k)
            for field in ("status", "paid_to", "attempts"):
                assert str(mine[field]) == str(theirs[field]), (k, field)
            assert [(a["labels"], a["verdict"], a["stated"], a["contradicts"]) for a in c.attempts_of(k)["attempts"]] == \
                [(a["labels"], a["verdict"], a["stated"], a["contradicts"]) for a in rec["attempts"][k]["attempts"]]

    def test_every_wallet_received_on_chain_exactly_what_the_contract_sent(self):
        rec = self._record()
        replay(self._labels(rec), who=rec["accounts"])
        got = received()
        b = rec["balances"]
        for name in rec["owed"]:
            gained = int(b[f"{name}_after"]) - int(b[f"{name}_before"])
            assert gained == got[rec["accounts"][name].lower()] == int(rec["owed"][name]), name
        assert rec["held_after"] == "0"
