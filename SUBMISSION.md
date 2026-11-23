# Submission

One submission, under **Builder -> Intelligent Contracts**. This repository is
one standalone primitive.

---

## Before you submit, in order

1. **Measure, do not estimate.**

   ```bash
   python scripts/measure.py --write
   ```

2. **Prove the address is evidence for this repository.**

   ```bash
   python scripts/verify_deployment.py <address>
   ```

3. **Open the explorer page and check it.** It must show the deploy, two paid
   opens, an answer that fetched three sources and was paid, an answer that
   fetched three sources and was vetoed by one of them, a refusal for the
   funder answering, one for a second answer, one for a settle while open, one
   for an answer past the deadline, and a settle that returns the bounty.

---

## Title

Crosscheck

## Notes

A fact bounty paid only when the funder's own sources agree with the answer. The funder names 2 to 5 public sources up front (frozen at open) and a quorum. A solver answers with one short claim. The contract fetches every source itself and the validators judge each page alone: states, contradicts or silent, asked in both orders. The contract then counts: the solver is paid only if at least the quorum of pages state it and none contradicts it. One contradicting page vetoes. A rejected answer is recorded with its labels. After the deadline the bounty returns to the funder. The solver never chooses the evidence, and no single page decides.

## Known limits

The model reads the first 6,000 characters of each page. The sources are the funder's choice; the demo's almanac page is a deliberately wrong fixture.
