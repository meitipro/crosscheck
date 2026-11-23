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
Deployed on studionet at [`0x85178f82BFE9c50C6934d0262E68863cD1Eaf63e`](https://explorer-studio.genlayer.com/address/0x85178f82BFE9c50C6934d0262E68863cD1Eaf63e) (deploy [`0x204b072f...`](https://explorer-studio.genlayer.com/tx/0x204b072f3e098e9f55f89c69d1a1ddb10aa25a73f294de8278137173a2d88b4c)). Every value below was read back from the chain by `scripts/demo.py` and written to [`deployments/studionet.json`](deployments/studionet.json); none of it is typed by hand. Two of the sources the contract fetched are real third-party pages (the English and the French Wikipedia articles on the Eiffel Tower); the other two are small files of this repository: [`gazetteer.md`](demo/sources/gazetteer.md), which gives no date, and [`almanac_1899.md`](demo/sources/almanac_1899.md), a fixture that is deliberately wrong.

| Question | Bounty | Quorum | Sources (in the funder's order) | Status | Paid to |
|---|---|---|---|---|---|
| 0: In what year was the Eiffel Tower completed? | 0.1 GEN | 2 | [`en.wikipedia.org/wiki/Eiffel_Tower`](https://en.wikipedia.org/wiki/Eiffel_Tower)<br>[`fr.wikipedia.org/wiki/Tour_Eiffel`](https://fr.wikipedia.org/wiki/Tour_Eiffel)<br>[`demo/sources/gazetteer.md`](https://raw.githubusercontent.com/meitipro/crosscheck/master/demo/sources/gazetteer.md) | paid | solver |
| 1: In what year was the Eiffel Tower completed? | 0.1 GEN | 2 | [`en.wikipedia.org/wiki/Eiffel_Tower`](https://en.wikipedia.org/wiki/Eiffel_Tower)<br>[`fr.wikipedia.org/wiki/Tour_Eiffel`](https://fr.wikipedia.org/wiki/Tour_Eiffel)<br>[`demo/sources/almanac_1899.md`](https://raw.githubusercontent.com/meitipro/crosscheck/master/demo/sources/almanac_1899.md) | refunded | funder |

What every source was judged to say, one page at a time, and what the contract's own count made of it:

| Question | Solver's claim | Source 1 | Source 2 | Source 3 | Stated | Contradicts | Verdict |
|---|---|---|---|---|---|---|---|
| 0 | The Eiffel Tower was completed in 1889. (solver) | **states** | **states** | **silent** | 2 | 0 | **accepted** |
| 1 | The Eiffel Tower was completed in 1889. (solver) | **states** | **states** | **contradicts** | 2 | 1 | **rejected** |

What the leader's model said about the first page it read (not consensus):

| Question | Reason the leader gave |
|---|---|
| 0 | The page explicitly lists the Eiffel Tower as completed on 31 March 1889. |
| 1 | The page states 'Completed 31 March 1889' and says it was built from 1887 to 1889, confirming the 1889 completion year. |

StudioNet charges a fee on every write, so a wallet's balance alone cannot show what it was paid. What each wallet received is read from the chain's own index: the transfers the contract sent it, against what the contract says it sent:

| Wallet | Received from the contract | The contract sent | Transfer |
|---|---|---|---|
| funder | 0.1 GEN | 0.1 GEN | [`0x0aff8377...`](https://explorer-studio.genlayer.com/tx/0x0aff8377020caa67218b8a146a649dcdb0c5485f68c1b5a57eb7e828858d9f0c) |
| solver | 0.1 GEN | 0.1 GEN | [`0x76a8d522...`](https://explorer-studio.genlayer.com/tx/0x76a8d522ab1ef2a1439fdb6ff7b8c5950a5b7aab366b6cf47fd9a943f9ac56b8) |

Held by the contract afterwards: 0 wei.

Every transaction, in order, refusals included, with the wallet that sent it:

| Step | From | Outcome | Transaction |
|---|---|---|---|
| question 0 opened: two Wikipedia articles and a gazetteer page, quorum 2, 0.1 GEN | funder | ok | [`0xe530a6b0...`](https://explorer-studio.genlayer.com/tx/0xe530a6b0f163fb33413c7acaf54a644d95727e36ccf4643759bf6185e30ed09c) |
| the funder answers its own question | funder | refused: the funder cannot answer its own question | [`0xf7b94258...`](https://explorer-studio.genlayer.com/tx/0xf7b94258cd9d67192bbf880a98a62d95b408cb350805202e257b42e7d73d556f) |
| question 0: three sources fetched and judged, two state it | solver | ok | [`0x05de2828...`](https://explorer-studio.genlayer.com/tx/0x05de28281a8f6d498b9c0ec9ca2db00963ef63afe95db00d7e3fe8116ecaa0ba) |
| an answer on a question that already paid | solver2 | refused: this question is paid; only an open one takes an answer | [`0xa4f6382c...`](https://explorer-studio.genlayer.com/tx/0xa4f6382c089366109a9ec57728153483d125999f1f9644a0ba355fef166d5c0a) |
| question 1 opened: the same two articles and an almanac that says 1899 | funder | ok | [`0x30fcb82d...`](https://explorer-studio.genlayer.com/tx/0x30fcb82d8b1e073cb92f906e4e079e1c8d6604cbc148c9c1c4990480daea88fe) |
| question 1: two sources state it, one contradicts it: recorded, not paid | solver | ok | [`0xdeac78a4...`](https://explorer-studio.genlayer.com/tx/0xdeac78a4e56961945f65508e80f16f638dc20ff9e3acc8b32aff04b06b5a22bc) |
| a second answer from the same solver | solver | refused: a solver answers once per question | [`0xda761e85...`](https://explorer-studio.genlayer.com/tx/0xda761e85d60b4924850aef98f9081f25f8c1e6d837469123d0996ea6ac70d4e3) |
| a settlement while question 1 is still open | stranger | refused: the question is open until 2026-11-23T21:49:20Z | [`0xdaa75b40...`](https://explorer-studio.genlayer.com/tx/0xdaa75b40b9bf735e454c64a999b50f6bc0a8e4c8529e0c0f3de03dea4c234fb9) |
| an answer after question 1's deadline | solver2 | refused: the deadline passed at 2026-11-23T21:49:20Z; a late answer is never read | [`0x62b429f2...`](https://explorer-studio.genlayer.com/tx/0x62b429f29a90f426f40e82579af6d6c7cb16beb0270f5a56bb7b6b58c9ee3540) |
| question 1 settled: nobody was paid, the bounty returns to the funder | stranger | ok | [`0x5d37c589...`](https://explorer-studio.genlayer.com/tx/0x5d37c58947cf82b3f1c3dbd60b73978c319947edac070620e6a22760cb1698d3) |

`tests/test_runbook.py::TestTheRecord` replays these labels through this repository's contract and fails unless it pays exactly what the deployed one did, and unless every wallet gained on chain exactly what the contract sent it.
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
Measured: **129 passed**, 1 skipped. The skipped tests are the opt-in StudioNet integration tests, which run with `GENLAYER_STUDIO=1`.
<!-- measured:tests:end -->

The suite runs the real contract file in `tests/glsim.py`, a small GenVM
stand-in that gives the leader and each validator **their own pages and their
own model answers**, rolls storage and transfers back when a call raises, and
refuses what GenVM refuses (a collection inside a storage dataclass, a `bool`
or `int` in a block's return value).

### The tests have teeth

<!-- measured:mutations:start -->
Measured: **74 mutations, 74 caught, 0 escaped.**

| Mutation | Caught by |
|---|---|
| an option past the list is accepted | `test_an_unusable_answer_is_an_error_and_never_a_label` |
| an answer in words is read as a number | `test_an_unusable_answer_is_an_error_and_never_a_label` |
| the second pass is asked in the forward order | `test_each_page_is_judged_alone_in_both_orders` |
| the reversed order is not reversed | `test_each_page_is_judged_alone_in_both_orders` |
| a disagreement between the orders keeps the forward label | `test_a_page_that_states_it_in_only_one_order_is_silent` |
| a disagreement between the orders states the claim | `test_a_page_that_states_it_in_only_one_order_is_silent` |
| a disagreement between the orders contradicts the claim | `test_a_page_that_states_it_in_only_one_order_is_silent` |
| an answer is not read back through its order | `test_enough_sources_that_state_it_pay_the_solver_at_once` |
| an unusable answer is not retried | `test_an_unusable_answer_is_an_error_and_never_a_label` |
| an unusable answer is read as stating the claim | `test_an_unusable_answer_is_an_error_and_never_a_label` |
| an answer that is not an object crashes the block | `test_an_unusable_answer_is_an_error_and_never_a_label` |
| an unreadable source is shown to the model as an error text | `test_a_source_that_cannot_be_read_counts_for_nothing_and_against_nothing` |
| a short or empty page is still judged | `test_too_many_unreadable_sources_leave_the_answer_below_quorum` |
| a source is never actually fetched | `test_enough_sources_that_state_it_pay_the_solver_at_once` |
| an unreadable source is still put to the model | `test_a_source_that_cannot_be_read_counts_for_nothing_and_against_nothing` |
| the sources are read in another order than the funder listed them | `test_a_source_that_cannot_be_read_counts_for_nothing_and_against_nothing` |
| an unreadable source counts as a source that states the claim | `test_too_many_unreadable_sources_leave_the_answer_below_quorum` |
| a source that contradicts is counted as one that states | `test_one_source_that_says_the_opposite_vetoes_an_answer_the_others_state` |
| the validator agrees with an error | `test_an_unusable_answer_is_an_error_and_never_a_label` |
| the validator skips the structural check | `test_a_leader_that_lies_on_the_wire_is_refused` |
| the validator agrees with anything sound | `test_nodes_that_read_the_sources_differently_do_not_agree` |
| the validator agrees when its own fetch or model fails | `test_a_validator_whose_own_model_fails_does_not_agree` |
| agreement ignores soundness | `test_agreement_is_exact_symmetric_and_source_by_source` |
| a label string of the wrong length is sound | `test_a_leader_that_lies_on_the_wire_is_refused` |
| a label the contract does not know is sound | `test_a_leader_that_lies_on_the_wire_is_refused` |
| the agreed labels are not checked again | `test_the_contract_does_not_trust_a_consensus_value_it_cannot_read` |
| one source is enough whatever the quorum | `test_fewer_sources_than_the_quorum_is_rejected_and_the_question_stays_open` |
| a contradicting source does not veto | `test_one_source_that_says_the_opposite_vetoes_an_answer_the_others_state` |
| the quorum has to be exceeded | `test_enough_sources_that_state_it_pay_the_solver_at_once` |
| an accepted answer pays nobody | `test_enough_sources_that_state_it_pay_the_solver_at_once` |
| a rejected answer pays the solver too | `test_one_source_that_says_the_opposite_vetoes_an_answer_the_others_state` |
| the winner is not recorded | `test_enough_sources_that_state_it_pay_the_solver_at_once` |
| the accepted claim is not recorded | `test_enough_sources_that_state_it_pay_the_solver_at_once` |
| every attempt is recorded as accepted | `test_one_source_that_says_the_opposite_vetoes_an_answer_the_others_state` |
| the count of sources that state it is recorded wrongly | `test_the_labels_and_the_count_are_on_the_record_source_by_source` |
| attempts are not linked | `test_a_rejected_answer_leaves_the_question_to_the_next_solver` |
| the attempt count is not raised | `test_the_labels_and_the_count_are_on_the_record_source_by_source` |
| the solver is not recorded as having answered | `test_a_solver_answers_once_per_question` |
| the settlement time is not recorded | `test_enough_sources_that_state_it_pay_the_solver_at_once` |
| a leader's reason is stored as sent | `test_a_leader_s_reason_on_the_wire_is_stored_clean_and_capped_even_if_the_validator_never_saw_it` |
| a leader's reason is stored uncapped | `test_a_leader_s_reason_on_the_wire_is_stored_clean_and_capped_even_if_the_validator_never_saw_it` |
| the funder may answer its own question | `test_the_funder_cannot_answer_its_own_question` |
| an answer is taken on a question that is not open | `test_a_question_that_paid_takes_no_more_answers` |
| answers never close | `test_nothing_is_taken_after_the_deadline` |
| a solver may answer twice | `test_a_solver_answers_once_per_question` |
| a question takes any number of answers | `test_a_question_takes_a_bounded_number_of_answers` |
| a claim of any length is accepted | `test_a_claim_is_bounded` |
| a question settles while it can still be answered | `test_nothing_settles_while_the_question_is_open_to_answers` |
| a paid or refunded question settles again | `test_a_paid_question_does_not_settle` |
| settle returns less than the bounty | `test_after_the_deadline_anyone_returns_the_bounty_to_the_funder` |
| a bounty of nothing is accepted | `test_a_bounty_must_be_paid_in` |
| the held counter is not raised | `test_a_question_opens_with_its_sources_frozen_and_the_bounty_paid_in` |
| a payout beyond what is held is sent | `test_a_payout_beyond_what_is_held_is_refused` |
| the held counter is not lowered | `test_enough_sources_that_state_it_pay_the_solver_at_once` |
| the window is unbounded | `test_the_window_is_bounded` |
| the window does not set the clock | `test_a_question_opens_with_its_sources_frozen_and_the_bounty_paid_in` |
| the question is unbounded | `test_the_question_is_bounded` |
| the sources are not checked | `test_the_sources_are_checked` |
| the quorum is unbounded | `test_the_quorum_is_one_to_the_number_of_sources` |
| the quorum is not stored | `test_a_question_opens_with_its_sources_frozen_and_the_bounty_paid_in` |
| the sources are stored in another order | `test_a_question_opens_with_its_sources_frozen_and_the_bounty_paid_in` |
| a source with angle brackets is accepted | `test_the_sources_are_checked` |
| a source may be named twice | `test_the_sources_are_checked` |
| any number of sources is accepted | `test_the_sources_are_checked` |
| a host without a dot is accepted | `test_a_source_is_a_plain_http_address` |
| a source is not tested for being http at all | `test_the_sources_are_checked` |
| the fence is removed | `test_hostile_text_in_the_claim_or_a_page_cannot_close_a_block_or_forge_an_option` |
| the fence leaves square brackets | `test_hostile_text_in_the_claim_or_a_page_cannot_close_a_block_or_forge_an_option` |
| the fetched page reaches the prompt unfenced | `test_hostile_text_in_the_claim_or_a_page_cannot_close_a_block_or_forge_an_option` |
| the claim reaches the prompt unfenced | `test_every_prompt_value_is_fenced_or_written_by_the_contract` |
| the question reaches the prompt unfenced | `test_every_prompt_value_is_fenced_or_written_by_the_contract` |
| a whole page, however long, reaches the prompt | `test_only_the_first_part_of_a_long_page_is_shown` |
| the prompt lets the model use what it already knows | `test_the_prompt_judges_one_page_by_what_it_says_and_nothing_else` |
| control characters are stored | `test_clean_text_collapses_whitespace_and_control_characters` |
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
