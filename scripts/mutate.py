"""Mutation pass: break every defence on purpose, confirm a test notices.

Passing tests prove nothing on their own. Each entry below is a small edit to
the contract that removes a defence. The suite must fail for every one of them,
and this script records WHICH test caught it, so the table in the README is
measured rather than claimed.

    python scripts/mutate.py            # run them all, print what caught what
    python scripts/mutate.py --md       # emit the markdown table for the README

An escaping mutation is a finding, not a nuisance: either a missing test, or a
later defence strict enough that an earlier test can no longer fail. The script
exits non-zero if anything escapes, and refuses to run on a red baseline.

Three rules keep the harness honest:

  * the unmutated suite must be green before anything is mutated;
  * a find string that is missing, or matches more than once, is a failure of
    the harness, never a skip, so refactoring cannot quietly turn a row off;
  * scripts/lift.py runs inside every mutated copy before the suite, so the lib
    parity test can never stand in for the behavioural test a mutation deserves.
"""

import argparse
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).absolute().parent.parent
TARGET = "crosscheck.py"

FENCE = '    return str(raw).replace("<", "(").replace(">", ")").replace("[", "(").replace("]", ")")'

MUTATIONS = [
    # -- reading the answer
    ("an option past the list is accepted", "    if k < 0 or k >= n:\n        return \"\"", "    if k < 0:\n        return \"\""),
    ("an answer in words is read as a number",
     '    if s == "" or any(ch not in "0123456789" for ch in s) or len(s) > 2:', '    if s == "":'),

    # -- the two orders, per page
    ("the second pass is asked in the forward order",
     "        rev, _ = ask(question, claim, page, REVERSED)", "        rev, _ = ask(question, claim, page, FORWARD)"),
    ("the reversed order is not reversed", "REVERSED = [SILENT, CONTRADICTS, STATES]", "REVERSED = [STATES, CONTRADICTS, SILENT]"),
    ("a disagreement between the orders keeps the forward label",
     "    return forward if forward == reverse else SILENT", "    return forward"),
    ("a disagreement between the orders states the claim",
     "    return forward if forward == reverse else SILENT", "    return forward if forward == reverse else STATES"),
    ("a disagreement between the orders contradicts the claim",
     "    return forward if forward == reverse else SILENT", "    return forward if forward == reverse else CONTRADICTS"),
    ("an answer is not read back through its order", "    return order[int(choice)]", "    return FORWARD[int(choice)]"),

    # -- reading the model
    ("an unusable answer is not retried",
     "    for _ in range(2):\n        raw = gl.nondet.exec_prompt(", "    for _ in range(1):\n        raw = gl.nondet.exec_prompt("),
    ("an unusable answer is read as stating the claim",
     '    raise gl.vm.UserError(f"{ERR_LLM} the model named no option")', '    return STATES, ""'),
    ("an answer that is not an object crashes the block",
     "        if isinstance(raw, dict):\n            choice", "        if True:\n            choice"),

    # -- the fetch, source by source
    ("an unreadable source is shown to the model as an error text",
     '    except Exception:\n        return ""\n    body = str(text)', '    except Exception:\n        text = "x" * MIN_PAGE\n    body = str(text)'),
    ("a short or empty page is still judged", "    if len(body.strip()) < MIN_PAGE:", "    if False:"),
    ("a source is never actually fetched", "        text = gl.nondet.web.render(url)", "        text = url"),
    ("an unreadable source is still put to the model",
     "            labels.append(UNREADABLE)\n            continue", "            labels.append(UNREADABLE)"),
    ("the sources are read in another order than the funder listed them",
     "    for u in urls:\n        page = fetch(u)", "    for u in reversed(urls):\n        page = fetch(u)"),
    ("an unreadable source counts as a source that states the claim",
     "    return parts.count(STATES), parts.count(CONTRADICTS), parts.count(UNREADABLE)",
     "    return parts.count(STATES) + parts.count(UNREADABLE), parts.count(CONTRADICTS), parts.count(UNREADABLE)"),
    ("a source that contradicts is counted as one that states",
     "    return parts.count(STATES), parts.count(CONTRADICTS), parts.count(UNREADABLE)",
     "    return parts.count(STATES) + parts.count(CONTRADICTS), parts.count(CONTRADICTS), parts.count(UNREADABLE)"),

    # -- the validator
    ("the validator agrees with an error", "                return False\n            theirs", "                return True\n            theirs"),
    ("the validator skips the structural check",
     "            if not labels_sound(proposed, n):\n                return False", "            if False:\n                return False"),
    ("the validator agrees with anything sound", '            return crosscheck_agrees(mine["labels"], proposed, n)', "            return True"),
    ("the validator agrees when its own fetch or model fails",
     "            except gl.vm.UserError:\n                return False", "            except gl.vm.UserError:\n                return True"),
    ("agreement ignores soundness",
     "    return labels_sound(mine, n) and labels_sound(theirs, n) and str(mine) == str(theirs)", "    return str(mine) == str(theirs)"),
    ("a label string of the wrong length is sound", "    if len(parts) != n:\n        return False", "    if False:\n        return False"),
    ("a label the contract does not know is sound", "    return all(p in LABELS for p in parts)", "    return True"),

    # -- the deterministic half
    ("the agreed labels are not checked again",
     "        if not labels_sound(labels, n):\n            raise", "        if False:\n            raise"),
    ("one source is enough whatever the quorum", "    return stated >= quorum and contradicts == 0", "    return stated >= 1 and contradicts == 0"),
    ("a contradicting source does not veto", "    return stated >= quorum and contradicts == 0", "    return stated >= quorum"),
    ("the quorum has to be exceeded", "    return stated >= quorum and contradicts == 0", "    return stated > quorum and contradicts == 0"),
    ("an accepted answer pays nobody", "            self._send(sender, int(q.bounty))", "            pass"),
    ("a rejected answer pays the solver too", "        if ok:\n            q.status = PAID", "        if True:\n            q.status = PAID"),
    ("the winner is not recorded", "            q.winner = sender", "            pass"),
    ("the accepted claim is not recorded", "            q.accepted_claim = text", "            pass"),
    ("every attempt is recorded as accepted", '            verdict="accepted" if ok else "rejected",', '            verdict="accepted",'),
    ("the count of sources that state it is recorded wrongly",
     "            stated=u256(stated), contradicts=u256(contradicts), unreadable=u256(unreadable),",
     "            stated=u256(contradicts), contradicts=u256(stated), unreadable=u256(unreadable),"),
    ("attempts are not linked", "            self.attempts[int(q.last_attempt)].next = u256(aid)", "            pass"),
    ("the attempt count is not raised", "        q.n_attempts = u256(int(q.n_attempts) + 1)", "        pass"),
    ("the solver is not recorded as having answered", "        self.tried[key] = u256(aid + 1)", "        pass"),
    ("the settlement time is not recorded", "            q.settled_at = u256(self._now())", "            pass"),
    ("a leader's reason is stored as sent",
     "why=sanitise_reason(res.get(\"because\", \"\")),", "why=str(res.get(\"because\", \"\")),"),
    ("a leader's reason is stored uncapped",
     '    return " ".join("".join(out).split())[:limit]', '    return " ".join("".join(out).split())'),

    # -- the free refusals
    ("the funder may answer its own question",
     "        if sender == q.funder:\n            raise", "        if False:\n            raise"),
    ("an answer is taken on a question that is not open",
     '        if str(q.status) != OPEN:\n            raise gl.vm.UserError(f"{ERR_EXPECTED} this question is {q.status}; only an open one takes an answer")',
     '        if False:\n            raise gl.vm.UserError(f"{ERR_EXPECTED} this question is {q.status}; only an open one takes an answer")'),
    ("answers never close", "        if self._now() > int(q.deadline):", "        if False:"),
    ("a solver may answer twice", "        if int(self.tried.get(key, u256(0))) > 0:", "        if False:"),
    ("a question takes any number of answers", "        if int(q.n_attempts) >= MAX_ATTEMPTS:", "        if False:"),
    ("a claim of any length is accepted", "        if not bounded(text, MIN_CLAIM, MAX_CLAIM):", "        if False:"),

    # -- settle
    ("a question settles while it can still be answered",
     "        if now <= int(q.deadline):\n            raise", "        if False:\n            raise"),
    ("a paid or refunded question settles again",
     '        if str(q.status) != OPEN:\n            raise gl.vm.UserError(f"{ERR_EXPECTED} this question is {q.status}; nothing to settle")',
     '        if False:\n            raise gl.vm.UserError(f"{ERR_EXPECTED} this question is {q.status}; nothing to settle")'),
    ("settle returns less than the bounty", "        self._send(q.funder, int(q.bounty))", "        self._send(q.funder, int(q.bounty) - 1)"),

    # -- money
    ("a bounty of nothing is accepted", "        if bounty < 1 or bounty > MAX_AMOUNT:", "        if bounty > MAX_AMOUNT:"),
    ("the held counter is not raised", "        self.held = u256(int(self.held) + bounty)", "        pass"),
    ("a payout beyond what is held is sent", "        if amount > int(self.held):", "        if False:"),
    ("the held counter is not lowered", "        self.held = u256(int(self.held) - amount)", "        pass"),

    # -- opening
    ("the window is unbounded", "        if w < MIN_WINDOW or w > MAX_WINDOW:", "        if False:"),
    ("the window does not set the clock", "deadline=u256(now + w)", "deadline=u256(now + MAX_WINDOW)"),
    ("the question is unbounded", "        if not bounded(t, MIN_QUESTION, MAX_QUESTION):", "        if False:"),
    ("the sources are not checked", '        if problem != "":', "        if False:"),
    ("the quorum is unbounded", "        if k < 1 or k > len(urls):", "        if False:"),
    ("the quorum is not stored", "quorum=u256(k), status=OPEN,", "quorum=u256(1), status=OPEN,"),
    ("the sources are stored in another order", 'sources="\\n".join(urls)', 'sources="\\n".join(sorted(urls))'),

    # -- what counts as a source
    ("a source with angle brackets is accepted", '    if rest == "" or any(ch in s for ch in " <>\\"\'`\\\\"):', '    if rest == "":'),
    ("a source may be named twice", '        if k in seen:\n            return "a source is named twice"', '        if False:\n            return "a source is named twice"'),
    ("any number of sources is accepted", "    if len(urls) < MIN_SOURCES or len(urls) > MAX_SOURCES:", "    if False:"),
    ("a host without a dot is accepted", '    return "." in host and not host.startswith(".") and not host.endswith(".")', "    return True"),
    ("a source is not tested for being http at all", '    if s.startswith("https://"):\n        rest = s[8:]\n    elif s.startswith("http://"):\n        rest = s[7:]\n    else:\n        return False', '    rest = s.split("://")[-1]'),

    # -- the prompt boundary
    ("the fence is removed", FENCE, "    return str(raw)"),
    ("the fence leaves square brackets", FENCE, '    return str(raw).replace("<", "(").replace(">", ")")'),
    ("the fetched page reaches the prompt unfenced", "{fence(page[:MAX_PAGE_SHOWN])}", "{page[:MAX_PAGE_SHOWN]}"),
    ("the claim reaches the prompt unfenced", "{fence(claim)}", "{claim}"),
    ("the question reaches the prompt unfenced", "{fence(question)}", "{question}"),
    ("a whole page, however long, reaches the prompt", "fence(page[:MAX_PAGE_SHOWN])", "fence(page)"),
    ("the prompt lets the model use what it already knows",
     "Do not use what you already know about the subject: a page\nthat does not say it is silent, even if the claim is true.",
     "Use what you already know about the subject."),
    ("control characters are stored", '            out.append(" ")\n        else:', "            out.append(ch)\n        else:"),
]

PYTEST = [sys.executable, "-m", "pytest", "tests/", "-x", "-q", "--no-header", "-p", "no:cacheprovider"]


def copy_repo(tmp):
    dst = pathlib.Path(tmp) / "repo"
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(
        "__pycache__", ".pytest_cache", ".git", "artifacts", "*.pyc"))
    return dst


def run_one(label, find, replace):
    with tempfile.TemporaryDirectory() as tmp:
        dst = copy_repo(tmp)
        target = dst / "contracts" / TARGET
        src = target.read_text(encoding="utf-8")
        hits = src.count(find)
        if hits == 0:
            return "PATTERN NOT FOUND", None
        if hits > 1:
            return "PATTERN NOT UNIQUE", None
        target.write_text(src.replace(find, replace, 1), encoding="utf-8", newline="\n")
        subprocess.run([sys.executable, "scripts/lift.py"], cwd=dst, capture_output=True)
        proc = subprocess.run(PYTEST, cwd=dst, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
        if proc.returncode == 0:
            return "ESCAPED", None
        text = proc.stdout + proc.stderr
        m = re.search(r"^(?:FAILED|ERROR) (\S+?)::(\S+?)(?:\[|\s|$)", text, re.M)
        if m:
            return "caught", m.group(2).split("::")[-1]
        m = re.search(r"^E\s+(\w*(?:Error|Exception))", text, re.M)
        if m:
            return "caught", m.group(1) + " at import"
        return "caught", "unnamed failure"


def baseline_is_green():
    with tempfile.TemporaryDirectory() as tmp:
        dst = copy_repo(tmp)
        proc = subprocess.run(PYTEST, cwd=dst, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
        return proc.returncode == 0, (proc.stdout + proc.stderr)[-2000:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", action="store_true", help="emit the README table")
    args = ap.parse_args()

    green, tail = baseline_is_green()
    if not green:
        print("the unmutated suite is not green; every mutation would look caught:\n" + tail, file=sys.stderr)
        return 2

    rows, escaped = [], []
    for label, find, replace in MUTATIONS:
        status, test = run_one(label, find, replace)
        if status == "caught":
            rows.append((label, test))
            if not args.md:
                print("  caught   %-70s %s" % (label, test), flush=True)
        else:
            escaped.append((label, status))
            print("  %-8s %s" % (status, label), file=sys.stderr, flush=True)

    if args.md:
        print("| Mutation | Caught by |")
        print("|---|---|")
        for label, test in rows:
            print("| %s | `%s` |" % (label, test))
    else:
        print()
        print("  %d mutations, %d caught, %d escaped" % (len(MUTATIONS), len(rows), len(escaped)))
    return 1 if escaped else 0


if __name__ == "__main__":
    sys.exit(main())
