# <Feature Name> — Decision Log

Append-only cross-session arbitration record. Keeps us from re-litigating the same tradeoffs. Downstream skills (`/brief-review-v2`, `/engineering-plan-review-v2`, `/plan-review-v2`, `/review-pr-v2`, `/execute-plan`, and the authors) scan this file for `Status: bound` entries and treat them as authoritative.

## How to use this log

- **Append, never rewrite.** New decisions go under `## Active (bound)`, newest first.
- **Every entry carries a `Status:` line.** Legal values:
  - `bound` — authoritative; downstream plans/code must conform. Lives in `## Active (bound)`.
  - `superseded by "<title>" (<date>)` — a later bound entry now governs the same surface. Kept for history but no longer binds. Lives in `## Archived (superseded / obsolete)`.
  - `obsolete` — the decision no longer applies at all (the surface was removed, the feature dropped it). Kept for history; does not bind. Lives in `## Archived`.
- **Superseding is a two-step edit, done together:** (1) write the new `bound` entry at the top of `## Active`; (2) change the entry it replaces to `Status: superseded by "<new title>" (<new date>)` and MOVE it to `## Archived`. This is what keeps the scanners honest — a stale, narrower decision left reading `bound` silently beats the wider one that replaced it. Only `## Active` entries are ever treated as authoritative.
- Scanners read only `## Active (bound)`. A flat log with no section split is tolerated (treat any non-`bound` status as retired), but adopt the split once the log has any superseded/obsolete entry.

---

## Active (bound)

## YYYY-MM-DD — <short title>

**Decision:** <what we're doing>

**Status:** bound

**Why:** <reason — the constraint, data, or principle that drove this>

**Rejected:**
- <alternative> — <why not>
- <alternative> — <why not>

---

## Archived (superseded / obsolete)

_Entries here are kept for history and do NOT bind. A `superseded` entry names the bound entry that replaced it; an `obsolete` entry states the decision no longer applies. Nothing in this section is authoritative — scanners skip it._

## YYYY-MM-DD — <short title of a retired decision>

**Decision:** <what we were deciding>

**Status:** superseded by "<title of the entry that replaced it>" (<date>)

**Why:** <original reason, kept for history>
