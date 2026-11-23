"""The demo's data, in one place.

scripts/demo.py sends exactly these values to StudioNet, and
tests/test_runbook.py replays them offline, so the demo on the explorer and the
demo the tests check cannot drift apart.

One question, asked twice: "In what year was the Eiffel Tower completed?", and
one claim, "The Eiffel Tower was completed in 1889."

  0  the funder names three sources: the English and the French Wikipedia
     articles on the tower, and a small gazetteer page of this repository that
     describes the monument without giving a date. A solver answers 1889. The
     contract fetches all three itself and the model reads each one alone: two
     state it, one is silent. The quorum is two, so the solver is paid at once.
  1  the funder names the same two Wikipedia articles and a reprint of an old
     almanac, also a file of this repository, that says the tower was completed
     in 1899. The same solver answers the same 1889. Two pages state it and one
     contradicts it, and one page that says the opposite vetoes the answer: it
     is recorded with its tally, nothing is paid, and nobody answers again, so
     after the deadline the bounty goes back to the funder.

The two Wikipedia articles are real third-party pages. The two small pages are
real, public files committed into this repository and served from
raw.githubusercontent.com. The almanac page is a fixture: it is deliberately
wrong, to show a source the funder chose disagreeing with the others.
"""

GEN = 10 ** 18

RAW = "https://raw.githubusercontent.com/meitipro/crosscheck/master/demo/sources"
EN = "https://en.wikipedia.org/wiki/Eiffel_Tower"
FR = "https://fr.wikipedia.org/wiki/Tour_Eiffel"
GAZETTEER = f"{RAW}/gazetteer.md"
ALMANAC = f"{RAW}/almanac_1899.md"

QUESTION = "In what year was the Eiffel Tower completed?"
CLAIM = "The Eiffel Tower was completed in 1889."
SOURCES_0 = "\n".join([EN, FR, GAZETTEER])
SOURCES_1 = "\n".join([EN, FR, ALMANAC])
QUORUM = 2

BOUNTY = 10 * GEN // 100
WINDOW = 1500

# The demo, step by step, exactly as scripts/demo.py sends it and
# tests/test_runbook.py replays it: (who, method, arguments, value, expected,
# label). A step marked "after_close:N" waits until question N's deadline has
# passed.
STEPS = [
    ("funder", "open", (QUESTION, SOURCES_0, QUORUM, WINDOW), BOUNTY, "ok",
     "question 0 opened: two Wikipedia articles and a gazetteer page, quorum 2, 0.1 GEN"),
    ("funder", "answer", (0, CLAIM), 0, "refused", "the funder answers its own question"),
    ("solver", "answer", (0, CLAIM), 0, "ok", "question 0: three sources fetched and judged, two state it"),
    ("solver2", "answer", (0, CLAIM), 0, "refused", "an answer on a question that already paid"),

    ("funder", "open", (QUESTION, SOURCES_1, QUORUM, WINDOW), BOUNTY, "ok",
     "question 1 opened: the same two articles and an almanac that says 1899"),
    ("solver", "answer", (1, CLAIM), 0, "ok", "question 1: two sources state it, one contradicts it: recorded, not paid"),
    ("solver", "answer", (1, CLAIM), 0, "refused", "a second answer from the same solver"),
    ("stranger", "settle", (1,), 0, "refused", "a settlement while question 1 is still open"),
    ("solver2", "answer", (1, CLAIM), 0, "refused", "an answer after question 1's deadline", "after_close:1"),
    ("stranger", "settle", (1,), 0, "ok", "question 1 settled: nobody was paid, the bounty returns to the funder",
     "after_close:1"),
]

# What each ok answer is expected to come back with, in order: the label each
# source got, in the order the funder listed them.
EXPECTED_LABELS = [
    ["states", "states", "silent"],
    ["states", "states", "contradicts"],
]
