# Deploying Crosscheck

Everything here runs on StudioNet. It is gasless; the only GEN needed is the
bounty of each question, and the funder gets it from the StudioNet faucet.
Nothing needs a private key in a file.

## 1 - Check the contract

```bash
pip install -r requirements-dev.txt
pytest tests/ -q
python scripts/schema_check.py contracts/crosscheck.py
GENVM_VERSION=v0.3.0-rc7 python -m genvm_linter.cli check contracts/crosscheck.py
```

`schema_check.py` runs the file through the live studionet runtime with
`gen_getContractSchemaForCode`, without deploying it. On Windows, set
`PYTHONIOENCODING=utf-8` first, or the linter dies printing its own tick.

## 2 - The demo sources

The demo has the contract fetch real pages. Two are third-party Wikipedia
articles. Two are small files committed into this repository and pushed ahead
of the demo, reachable at:

```
https://raw.githubusercontent.com/meitipro/crosscheck/master/demo/sources/gazetteer.md
https://raw.githubusercontent.com/meitipro/crosscheck/master/demo/sources/almanac_1899.md
```

`scripts/demo_data.py` points at exactly those URLs. If you fork this
repository, update `RAW` in that file first.

## 3 - Run the demo

```bash
python scripts/demo.py
```

It makes four accounts in memory: the funder, two solvers and a stranger.
The funder is funded with 4 GEN from the faucet. It deploys
`contracts/crosscheck.py` exactly as it is in this repository, then sends the
steps in [`scripts/demo_data.py`](scripts/demo_data.py); the same list drives
the demo and `tests/test_runbook.py`.

| # | Question | From | Call | Expected |
|---|---|---|---|---|
| 1 | 0 | funder | `open(q, 3 sources, 2, 1500)` | ok |
| 2 | 0 | funder | `answer(0, ...)` | refused: the funder cannot answer |
| 3 | 0 | solver | `answer(0, ...)` | ok: states, states, silent: **paid** |
| 4 | 0 | solver2 | `answer(0, ...)` | refused: the question is paid |
| 5 | 1 | funder | `open(q, 3 sources, 2, 1500)` | ok |
| 6 | 1 | solver | `answer(1, ...)` | ok: states, states, contradicts: **rejected** |
| 7 | 1 | solver | `answer(1, ...)` | refused: once per solver |
| 8 | 1 | stranger | `settle(1)` | refused: still open |
| 9 | 1 | solver2 | `answer(1, ...)` after the deadline | refused: deadline passed |
| 10 | 1 | stranger | `settle(1)` after the deadline | ok: the bounty returns to the funder |

It writes `deployments/studionet.json`: every transaction, the refusal
sentences, every question and answer as the chain holds them, and every
wallet's balance before and after.

## 4 - Measure and verify

```bash
python scripts/measure.py --write
python scripts/verify_deployment.py <address>
```
