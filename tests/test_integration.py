"""Integration tests, run against StudioNet.

    pip install genlayer-py==0.18.0
    GENLAYER_STUDIO=1 pytest tests/test_integration.py -v

They are opt in. Without GENLAYER_STUDIO set they skip, so `pytest tests/ -q`
stays clean and offline on a reviewer's machine whatever is installed there,
and an unreachable network can never be mistaken for a broken contract.

They exercise the deterministic half on a real runtime, where the simulator is
weakest: the sender is derived from a signature rather than set by a test, the
bounty is real value attached to a real transaction, and the free refusals
before any fetch are shown to cost no inference. An answer itself costs a
fetch of every source and inference on every validator and is on the record
from scripts/demo.py.
"""

import os
import pathlib
import sys

import pytest

if not os.environ.get("GENLAYER_STUDIO"):
    pytest.skip("integration tests run against StudioNet and are opt in: set GENLAYER_STUDIO=1. "
                "Everything else runs offline with pytest tests/ -q", allow_module_level=True)

pytest.importorskip("genlayer_py", reason="pip install genlayer-py==0.18.0")

sys.path.insert(0, str(pathlib.Path(__file__).absolute().parent.parent / "scripts"))
from studio import Studio                                     # noqa: E402

CODE = (pathlib.Path(__file__).absolute().parent.parent / "contracts" / "crosscheck.py").read_text(encoding="utf-8")
QUESTION = "Crosscheck integration run: which year is named?"
SOURCES = "https://example.com/one\nhttps://example.org/two"
BOUNTY = 10 ** 13


@pytest.fixture(scope="module")
def world():
    s = Studio()
    funder = s.account("funder", gen=1)
    solver = s.account("solver")
    address = s.deploy(funder, CODE, [])
    s.write(funder, address, "open", [QUESTION, SOURCES, 2, 3600], value=BOUNTY, step="open a question")
    return s, address, funder, solver


def test_a_question_opens_with_the_signer_as_funder_and_the_bounty_held(world):
    s, address, funder, _ = world
    q = s.read(address, "question", [0])
    assert q["status"] == "open" and q["funder"].lower() == funder.address.lower()
    assert q["bounty"] == str(BOUNTY) and int(s.read(address, "held_total")) == BOUNTY
    assert q["sources"] == SOURCES.split("\n") and q["quorum"] == 2


def test_the_funder_cannot_answer(world):
    s, address, funder, _ = world
    row = s.write(funder, address, "answer", [0, "It was 1931."], step="the funder answers", expect="refused")
    assert "the funder cannot answer its own question" in row["refusal"]


def test_a_settle_while_the_question_is_open_is_refused(world):
    s, address, _, solver = world
    row = s.write(solver, address, "settle", [0], step="settle too early", expect="refused")
    assert "the question is open until" in row["refusal"]


def test_an_unknown_question_is_a_refusal_not_the_newest_row(world):
    s, address, _, solver = world
    row = s.write(solver, address, "settle", [99], step="settle a question that does not exist", expect="refused")
    assert "no such question" in row["refusal"]
