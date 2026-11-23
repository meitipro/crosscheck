# Decisions

What was chosen, and what was rejected, with the reason.

## The funder names the sources, and they are frozen at open

**Rejected:** the solver supplies the URLs. A solver who picks the evidence
picks the answer: they add the one friendly page and leave out the rest.
**Chosen:** two to five sources, one per line, fixed in `open()`. Duplicates
(after lowercasing scheme and host and dropping a trailing slash or fragment)
are refused rather than quietly merged, so a funder is told when they listed
one page twice and thought it was two.

## One prompt per page, not one prompt over all pages

**Rejected:** showing the model every page and asking whether "the sources
agree". A hostile page could then steer the reading of the others, and a long
page could crowd the rest out of the model's window.
**Chosen:** each page is judged alone, in both orders (six prompts for three
sources). The model never learns how many sources there are, what the others
said, or what the quorum is, so it cannot be asked to round a result up.

## The contract counts

**Rejected:** asking the model "do enough sources agree".
**Chosen:** the model produces one label per page; `tally()` and `accepted()`
are pure functions of those labels, and the quorum and the veto live there.
That is also why they are mutation-tested: the arithmetic can be wrong in ways
a prompt cannot.

## One contradiction vetoes

**Rejected:** a simple majority. A majority pays a claim that one source
refutes, which is exactly the case the funder would want to see.
**Chosen:** `stated >= quorum and contradicts == 0`. A source that only touches
the subject is `silent` and does not veto.

## `silent` absorbs disagreement between the orders

A page that says the claim in one order and not in the other has not clearly
said it. Folding that into `silent` (not `states`, not `contradicts`) means
uncertainty can never pay a bounty and can never block one by veto either.

## `unreadable` is not an error

A source that cannot be fetched or returns almost nothing is labelled
`unreadable` inside the block, counts for nothing and against nothing, and is
never put to the model. **Rejected:** failing the whole answer. One dead mirror
should not sink an answer the other pages support. If the leader read a page and
a validator could not (or the other way round) the labels differ and the
validators do not agree, so a flaky fetch cannot move money.

## An attempt is recorded even when it is rejected

Every answer that reaches judgment is stored with its labels and the contract's
count, and the solver's one answer is spent. A rejected answer therefore shows
which page vetoed it. A failure *before* a verdict (a model that never names an
option, validators that do not agree) records nothing and spends nothing.

## Eight answers per question, one per solver

Every answer costs a fetch of every source and inference on every validator.
One per solver stops one wallet re-asking until it passes; the cap stops many
wallets doing the same.

## No tolerance anywhere

Labels are compared exactly. There is no "close enough" between two nodes'
readings, and no pair of labels that is forgiven for another.
