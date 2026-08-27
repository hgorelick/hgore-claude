#!/usr/bin/env python3
"""Deterministic reviewer verdict banner.

Single source of truth for the verdict/round banner every review skill
(`/brief-review-v2`, `/engineering-plan-review-v2`, `/plan-review-v2`,
`/review-pr-v2`, `/spec-review`, `/vision-review`) and the triage pair
(`/explain-blockers`, `/solve-blockers`) prints as the last thing in its
response.
Same inputs -> byte-identical output, for every skill and every run.

Usage:
    python3 verdict_banner.py <STATUS> <ROUND> [<BLOCKERS>] --skill /<skill> [--next "<text>"]

    STATUS    reviewer statuses: APPROVED | CLOSED | NEEDS USER INPUT
              (quote it; it has spaces). CLOSED comes from the three-state
              reviewers: /engineering-plan-review-v2 and /vision-review.
              Triage statuses: RESOLVED | DECISIONS PENDING
              (RESOLVED = fixes applied, source skill must revalidate;
              DECISIONS PENDING = the calls are rendered and sit with the user).
    ROUND     round number for this verdict (1 on a cold start). Triage skills
              pass the SOURCE verdict's round; "?" when the source carried none.
    BLOCKERS  count: open blockers (NEEDS USER INPUT), blockers covered by the
              applied fixes (RESOLVED), or decisions awaiting the user
              (DECISIONS PENDING); omit/0 when clean
    --skill   for reviewer statuses: the invoking reviewer, e.g. /plan-review-v2.
              For triage statuses: the SOURCE skill to re-invoke, e.g. /spec-review.
              Used by the canned Next lines.
    --next    one-line next-action text; honored ONLY on APPROVED / CLOSED.
              NEEDS USER INPUT, RESOLVED, and DECISIONS PENDING render a canned
              Next line from --skill and ignore --next, so their wording never
              varies.

Output is a fenced markdown code block, fences included. Emit stdout verbatim;
do not reformat, and never add or strip a fence around it.
"""
import argparse

BAR = "═" * 44
FENCE = "```"
VALID = {"APPROVED", "CLOSED", "NEEDS USER INPUT", "RESOLVED", "DECISIONS PENDING"}


def render(status: str, round_: str, blockers: int, skill: str, nxt: str) -> str:
    status = " ".join(status.strip().upper().split())
    unit = "decision" if status == "DECISIONS PENDING" else "blocker"
    verdict = f"VERDICT: {status}"
    if blockers > 0:
        verdict += f" — {blockers} {unit}{'' if blockers == 1 else 's'}"
    target = skill.strip() if skill.strip() else "the source skill"
    if status == "NEEDS USER INPUT":
        target = skill.strip() if skill.strip() else "the reviewer"
        nxt = f"resolve the blockers above (or /explain-blockers), then re-invoke {target}"
    elif status == "RESOLVED":
        nxt = f"re-invoke {target} to validate the resolutions"
    elif status == "DECISIONS PENDING":
        nxt = f"make the calls above, then re-invoke {target}"
    lines = [FENCE + "text", BAR, verdict, f"Round: {round_}"]
    if nxt.strip():
        lines.append(f"Next: {nxt.strip()}")
    lines.append(BAR)
    lines.append(FENCE)
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument("status")
    p.add_argument("round")
    p.add_argument("blockers", nargs="?", default="0")
    p.add_argument("--skill", dest="skill", default="")
    p.add_argument("--next", dest="nxt", default="")
    a = p.parse_args()

    status = " ".join(a.status.strip().upper().split())
    if status not in VALID:
        p.error(f"STATUS must be one of {sorted(VALID)}; got {a.status!r}")
    try:
        blockers = max(0, int(a.blockers))
    except ValueError:
        p.error(f"BLOCKERS must be an integer; got {a.blockers!r}")

    print(render(status, a.round, blockers, a.skill, a.nxt))


if __name__ == "__main__":
    main()
