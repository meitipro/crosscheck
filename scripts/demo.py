"""Deploy Crosscheck to StudioNet and put every path on the explorer.

    pip install genlayer-py==0.18.0
    python scripts/demo.py

The run deploys contracts/crosscheck.py exactly as it is in this repository,
then sends the steps in scripts/demo_data.py (STEPS), including the ones that
end in a refusal, and writes what happened to deployments/studionet.json:
every transaction hash, its sender and status, the refusal sentence where
there was one, every question and every answer as the chain holds them, and
the balance of every wallet that was paid, read before and again once every
payment had landed. Nothing in that file is typed by hand.

Four accounts: the funder, two solvers and a stranger. They are made in memory
for this run and never written to disk; the funder is funded from the
StudioNet faucet to pay the two bounties in.

The funder both pays in (at open) and may be refunded (at settle), so its
balance is snapshotted right after the last open, never from an earlier
moment.
"""

import datetime
import hashlib
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).absolute().parent))
import demo_data as D                                       # noqa: E402
from studio import EXPLORER, Studio                         # noqa: E402

ROOT = pathlib.Path(__file__).absolute().parent.parent
SOURCE = ROOT / "contracts" / "crosscheck.py"
OUT = ROOT / "deployments" / "studionet.json"

ROLES = ("funder", "solver", "solver2", "stranger")
PAID = ("funder", "solver")


def wait_for_balance(s, address, at_least, label, tries=24):
    """A payment can land a little after the transaction that sent it, so the
    balance is read until it has arrived rather than once."""
    for _ in range(tries):
        b = s.balance(address)
        if b >= at_least:
            return b
        time.sleep(5)
    print(f"  {label}: the payment had not landed after {tries * 5}s")
    return s.balance(address)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    code = SOURCE.read_text(encoding="utf-8")
    s = Studio()

    print("\naccounts (in memory, StudioNet test GEN only)")
    who = {name: s.account(name, gen=4 if name == "funder" else 0) for name in ROLES}
    before = {"solver": s.balance(who["solver"].address)}

    print("\ndeploy")
    address = s.deploy(who["funder"], code, [])

    print("\nthe demo")
    last_open = max(i for i, step in enumerate(D.STEPS) if step[1] == "open")
    for i, step in enumerate(D.STEPS):
        actor, method, spec, value, expect, label = step[:6]
        tag = next((t for t in step[6:] if t.startswith("after_close:")), None)
        if tag:
            qid = int(tag.split(":")[1])
            deadline = s.read(address, "question", [qid])["deadline"]
            target = datetime.datetime.fromisoformat(deadline.replace("Z", "+00:00")).timestamp() + 20
            left = target - time.time()
            if left > 0:
                print(f"  waiting {int(left)}s for question {qid}'s deadline")
                time.sleep(left)
        args = [who[a].address if a in who else a for a in spec]
        s.write(who[actor], address, method, args, value=value, step=label, expect=expect)
        if i == last_open:
            # Every question is open now and every bounty is paid in; nothing
            # further pays the funder back until a settle: the right point to
            # snapshot its balance.
            before["funder"] = s.balance(who["funder"].address)

    n = int(s.read(address, "count"))
    questions = [s.read(address, "question", [k]) for k in range(n)]
    attempts = [s.read(address, "attempts_of", [k]) for k in range(n)]

    owed = {"funder": 0, "solver": 0}
    for q in questions:
        if q["paid_to"] == "solver":
            owed["solver"] += int(q["bounty"])
        elif q["paid_to"] == "funder":
            owed["funder"] += int(q["bounty"])
    after = {name: wait_for_balance(s, who[name].address, before[name] + owed[name], name) for name in PAID}

    record = {
        "network": "studionet",
        "chain_id": 61999,
        "contract": address,
        "explorer": f"{EXPLORER}/address/{address}",
        "source_sha256": hashlib.sha256(SOURCE.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "constructor": {},
        "accounts": {name: a.address for name, a in who.items()},
        "balances": {f"{name}_{when}": str(v[name]) for when, v in (("before", before), ("after", after))
                     for name in PAID},
        "owed": {name: str(v) for name, v in owed.items()},
        "held_after": str(s.read(address, "held_total")),
        "steps": s.log,
        "questions": questions,
        "attempts": attempts,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8", newline="\n")

    print(f"\n  contract   {address}")
    print(f"  explorer   {EXPLORER}/address/{address}")
    for k, q in enumerate(questions):
        rows = attempts[k]["attempts"]
        print(f"  question {k}  {q['status']}  paid_to {q['paid_to'] or '-'}  answers {len(rows)}  "
              f"labels {[r['labels'] for r in rows]}")
    for name in PAID:
        print(f"  {name:<9} gained {after[name] - before[name]}  owed {owed[name]}")
    print(f"  written    {OUT.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
