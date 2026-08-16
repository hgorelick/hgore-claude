#!/usr/bin/env python3
"""Deterministic reviewer verdict banner.

Single source of truth for the verdict/round banner every review skill
(`/brief-review-v2`, `/engineering-plan-review-v2`, `/plan-review-v2`,
`/review-pr-v2`, `/spec-review`) prints as the last thing in its response.
Same inputs -> byte-identical output, for every skill and every run.

Usage:
    python3 verdict_banner.py <STATUS> <ROUND> [<BLOCKERS>] [--next "<text>"]

    STATUS    one of: APPROVED | CLOSED | NEEDS USER INPUT  (quote it; it has spaces)
    ROUND     round number for this verdict (1 on a cold start)
    BLOCKERS  open-blocker count; pass for NEEDS USER INPUT, omit/0 when clean
    --next    optional one-line next-action text

Emit stdout verbatim; do not reformat.
"""
import argparse

BAR = "═" * 44
VALID = {"APPROVED", "CLOSED", "NEEDS USER INPUT"}


def render(status: str, round_: str, blockers: int, nxt: str) -> str:
    status = " ".join(status.strip().upper().split())
    verdict = f"VERDICT: {status}"
    if blockers > 0:
        verdict += f" — {blockers} blocker{'' if blockers == 1 else 's'}"
    lines = [BAR, verdict, f"Round: {round_}"]
    if nxt.strip():
        lines.append(f"Next: {nxt.strip()}")
    lines.append(BAR)
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument("status")
    p.add_argument("round")
    p.add_argument("blockers", nargs="?", default="0")
    p.add_argument("--next", dest="nxt", default="")
    a = p.parse_args()

    status = " ".join(a.status.strip().upper().split())
    if status not in VALID:
        p.error(f"STATUS must be one of {sorted(VALID)}; got {a.status!r}")
    try:
        blockers = max(0, int(a.blockers))
    except ValueError:
        p.error(f"BLOCKERS must be an integer; got {a.blockers!r}")

    print(render(status, a.round, blockers, a.nxt))


if __name__ == "__main__":
    main()
