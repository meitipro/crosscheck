# Crosscheck - a fact bounty paid only when the funder's own sources agree with the answer

A GenLayer Intelligent Contract for fact bounties, with the bounty paid in
before the first answer. A funder opens a question, names the **two to five
public sources that will settle it** (frozen at that moment), says how many of
them must back an answer (the quorum), and pays the bounty in. Anyone but the
funder answers once, with a short claim. In the same transaction the contract
**fetches every source itself** with `gl.nondet.web.render`, and the validators
judge each page on its own: does this page state the claim, contradict it, or
say nothing. The contract then counts. At least `quorum` sources must state it
and **none may contradict it**; then the solver is paid at once. Otherwise the
answer is recorded with its tally and the question stays open for the next
solver, and after the deadline the bounty returns to the funder.

- **Contract:** [`contracts/crosscheck.py`](contracts/crosscheck.py)
- **Tests:** `pip install pytest && pytest tests/ -q` - nothing else to install
- **Deployed:** see [It is live](#it-is-live-and-every-path-is-on-chain) below, and [`deployments/studionet.json`](deployments/studionet.json)
- **Run the demo yourself:** [DEPLOY.md](DEPLOY.md)
- **Verify a deployment:** `python scripts/verify_deployment.py 0x...` - compares the on-chain source with this file and lints it
- **Decisions:** [DECISIONS.md](DECISIONS.md)
- **License:** MIT

---

## It is live, and every path is on chain

<!-- measured:deployment:start -->
Run `python scripts/demo.py`, then `python scripts/measure.py --write`.
<!-- measured:deployment:end -->

## The problem

A fact bounty has to be paid on evidence, and the usual shapes are both easy
to game.

- **Trust one page.** The bounty goes to whoever finds one page that says what
  they need. A single page can be wrong, stale or planted.
- **Trust the solver's description of the sources.** "I checked three sites and
  they agree" is a claim the contract cannot check, so it is paying for fiction.

Crosscheck takes the choice of evidence out of the solver's hands. **The
funder names the sources before anyone answers**, so a solver cannot add a
friendly page and cannot drop an unfriendly one. And no single source decides:
each page is judged **alone**, never shown the other pages or what the model
said about them, and the contract's own arithmetic combines the verdicts.

## How consensus is used

### Before any page is fetched, and before any model

The contract refuses for free what no answer could change: an answer from the
funder, a second answer from the same solver, an answer after the deadline, an
answer on a question that already paid, an answer once the question has taken
as many as it will (8), and a claim outside 3 to 300 characters.

### One fetch per source, one verdict per page

The block fetches each source with `gl.nondet.web.render`, independently on the
leader and on each validator, then asks the model about **that one page** and
nothing else. Three options, written by the contract and labelled `[0]` `[1]`
`[2]` inside an `<options>` block: `states`, `contradicts`, `silent`. The model
is not shown any other source, anyone's verdict on another source, how many
sources there are, the quorum, the solver, the funder, the bounty, or the URL.

A page that cannot be read is its own value, `unreadable`: it counts for
nothing and against nothing, and is never put to the model.

### Both orders

Each page is asked twice: in the order `states, contradicts, silent`, and then
fully reversed and renumbered. Each answer is read back through the order it was
asked in. The same label both ways stands; **anything else is `silent`**. A page
has to say the same thing both ways to count for a claim or against it, and a
model that always answers "0" states nothing at all.

### The validator, in two layers

1. **Structural, and free.** Exactly one known label per source. A payload that
   fails this is refused before the validator spends a single prompt.
2. **Exact agreement**, after the validator has fetched every page and asked
   both orders itself, source by source.

A model answer that is unusable is retried once inside the block and then raised
as `[LLM_ERROR]`, which no validator agrees with: a broken model can never pay a
bounty and never uses up a solver's one answer.

## What the contract decides, not the model

The model judges one page against one claim. Everything after that is the
contract's own arithmetic, done once every model call has returned:

| | |
|---|---|
| accepted | `stated >= quorum` **and** `contradicts == 0` |
| paid | the whole bounty, to the solver, at once |
| rejected | the answer and its per-source labels are recorded; nothing moves |
| refunded | after the deadline, the whole bounty to the funder |

One page that says the opposite **vetoes** an answer the others state. That is
deliberate: a bounty that pays on a majority is paid on a lie that happens to be
repeated.

## The state machine and its clock

```
open --(accepted answer)--> paid
open --(deadline passes, nobody paid, settle())--> refunded
```

`deadline = open + window`. After it `answer()` refuses for free, before any
fetch, and `settle()` is open to anyone.

## Who may write

| Method | Who | Why |
|---|---|---|
| `open(text, sources, quorum, window)` payable | anyone | the caller is the funder; the bounty is theirs |
| `answer(id, claim)` | anyone but the funder, once each | the caller is the solver; paid if accepted |
| `settle(id)` | anyone | a refund goes to the recorded funder whoever asks, only after the deadline; it reads no page and no model |

## The API

```
open(text: str, sources: str, quorum: u256, window: u256)   payable; sources one per line
answer(question_id: u256, claim: str)
settle(question_id: u256)

count() -> u256
held_total() -> u256
status(question_id) -> "open" | "paid" | "refunded"
question(question_id) -> {text, funder, bounty, sources[], quorum, status, attempts, deadline, winner, ...}
attempts_of(question_id) -> every answer with its per-source labels and the contract's count
```

## Running the tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -q
python scripts/mutate.py          # break every defence, one at a time
GENLAYER_STUDIO=1 pytest tests/test_integration.py -v     # opt in, hits StudioNet
```

<!-- measured:tests:start -->
Run `python scripts/measure.py --write`.
<!-- measured:tests:end -->

The suite runs the real contract file in `tests/glsim.py`, a small GenVM
stand-in that gives the leader and each validator **their own pages and their
own model answers**, rolls storage and transfers back when a call raises, and
refuses what GenVM refuses (a collection inside a storage dataclass, a `bool`
or `int` in a block's return value).

### The tests have teeth

<!-- measured:mutations:start -->
Run `python scripts/measure.py --write`.
<!-- measured:mutations:end -->

## Design rules applied

- **The coarsest answer that carries the judgment.** One label per page from a closed set; only labels cross consensus. The reason sentence is display only.
- **Uncertainty goes in the value.** Disagreement between the orders is `silent`; a page that cannot be read is `unreadable`. Neither is ever compared with a tolerance.
- **Both presentation orders** for every page.
- **Every write is bound to an address**, and a test fails when a write is added without being classified.
- **Untrusted text is fenced** at the prompt boundary (replace, never delete), and a test fails when a prompt value is not.
- **The contract counts, not the model:** the quorum and the veto are arithmetic over labels.
- **The deployed bytes are the repository's bytes:** `scripts/verify_deployment.py`.

## Further reading in this repository

- [`lib/crosscheck_consensus.py`](lib/crosscheck_consensus.py) - the answer rules lifted out to copy; generated by `scripts/lift.py`, compared function by function with the contract by a test.
- [`DECISIONS.md`](DECISIONS.md) - what was chosen and what was rejected.
- [`SUBMISSION.md`](SUBMISSION.md) - the submission text.

## Known limits

- The model reads the first 6,000 characters of each page. A claim that is only settled further down reads as `silent`.
- A page that changes between the leader's fetch and a validator's can make the validators disagree; the answer then fails without being recorded, and the solver may try again.
- The sources are the funder's choice. Crosscheck guarantees the solver cannot choose them, not that the funder chose well.
- The demo's two small source pages are fixtures committed to this repository; the almanac page is deliberately wrong.
