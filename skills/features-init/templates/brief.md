# <Feature Name> — Product Brief

**Spec:** specs/<slug>/spec.md | spec.md
**Created:** YYYY-MM-DD
**Last updated:** YYYY-MM-DD

> `Spec:` names the parent spec this brief descends from — the one whose `## Decomposition` cut this brief out of it. A project with a single root `spec.md` and no `specs/` tree names that file.

> The brief carries no lifecycle `Status:` field. Where the brief sits between Proposed and Archived is roster state, and it lives in `features/README.md`'s Brief roster — one row per brief, one place to read them all. The only `Status:` a brief ever carries is the mid-cycle `Status: needs-user-input` flag `/brief-author` sets and clears; a brief in any other state carries no `Status:` line at all.

> Product briefs are high-altitude. Zero implementation detail. No file names, function names, schema, libraries, code paths, technical approaches, or "how." If you're tempted to explain *how* something works, that belongs in the engineering plan or a chunk plan. The brief answers *what* and *why* in language a non-engineer would understand.

## Problem

<What's broken or missing for the user? Plain language, user-facing terms only. What is the user unable to do, or doing badly, today? One or two paragraphs. No mention of code, systems, or internals.>

## Solution

<The proposed shape of the fix, described in user-facing terms. What will the user be able to do that they couldn't before? One paragraph. No "how" — no mention of services, libraries, data models, or algorithms.>

## Goals

What success looks like, in observable user-facing or business terms. Two rules per Goal:

1. **State the domain the outcome ranges over.** A Goal that quantifies — "every", "across the catalog", "all", "at every surface" — names the concrete members: which screens, which entity types, which call paths, which cohorts. An unnamed domain cannot be checked, so a subset delivery ships silently.
2. **Give it a `Measured by:` clause** — the check that answers *"did this ship whole?"* A query, a test, a gate, or a counted set. Not a chunk name; the engineering plan's Brief-mapping table names the chunk. This names the check.

State outcomes, never mechanisms. "Junk can't return at any surface a user reaches" is an outcome; "junk is filtered with an allowlist" is a mechanism, and a mechanism is satisfiable by doing the technique *somewhere* while the outcome ships nowhere whole.

- **<Goal name>.** <Observable outcome, with the domain it ranges over stated explicitly.>
  **Measured by:** <query / test / gate / counted set that proves it whole.>
- **<Goal name>.** <e.g. "A user who misses a day can recover the streak from the home screen, the streak detail screen, and the push notification.">
  **Measured by:** <e.g. "An end-to-end flow covers all three entry points; each asserts the streak count returns to its pre-miss value.">

## Scope

Four buckets. A single Non-goals list collapses three meaningfully different states — committed-later, not-this-release, decided-against — and the downstream scope check then has to guess which one an omission is. Say it once, here.

### In scope

What this feature delivers. Each item is testable against a Goal above.

- <item>

### Intentionally deferred

Committed to ship later. **Every item names its destination** — a tracking issue number or a follow-on feature slug. An item with no destination is not deferred, it is one of the two buckets below; put it there.

- <e.g. "Paid recovery — #212.">
- <e.g. "Recovery for weekly streaks — follow-on feature `weekly-streak-recovery`.">

### Not in scope (this release)

Outside this feature's commitment, with no committed future ship. Still a candidate if priorities move.

- <item>

### Not planned

Decided against. Each item states the decision and why.

- <e.g. "No retroactive recovery beyond 24 hours — it makes the streak meaningless.">

## User-facing changes

What the user will notice. Screens, flows, copy, behaviors.

- <e.g. "New 'Recover streak' card appears on home screen the day after a miss.">
- <e.g. "Push notification at 6pm local on miss day.">

## Open questions

Product-level questions to resolve before writing the engineering plan. Technical unknowns belong in the engineering plan's Risks section, not here.

- [ ] <question>
- [ ] <question>
