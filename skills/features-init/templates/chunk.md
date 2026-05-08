# Chunk: `<slug>` — <Chunk Name>

**Slug:** `<slug>` (kebab-case, 2–4 words; matches the engineering plan's chunk-index row and this file's basename)
**Feature:** <feature-name>
**Status:** proposed | approved | in-progress | merged | verified
**PR:** <link once opened>
**Depends on:** <chunk slugs, or "—">
**Brief:** [`../brief.md`](../brief.md) · **Engineering plan:** [`../engineering-plan.md`](../engineering-plan.md)

> This plan is derived from the engineering plan, which is derived from the brief. If you can't restate this chunk's purpose in terms of a brief Goal or User-facing change, stop and re-read both before continuing.
>
> Status fields above are mutable on this file as the chunk progresses (proposed → merged → verified). The engineering plan's chunk index never tracks status — that is this file's job.

## Goal

<One sentence. What this chunk delivers when merged. MUST NOT contain " and " — if it does, split the chunk into two slugs. The Factoring Contract below enforces single-concern; this Goal sentence is the human-readable form of that constraint.>

## Brief link

Which brief items this chunk serves. Pulled from the engineering plan's Brief Mapping section.

- **Goal:** <verbatim from brief>
- **User-facing change:** <verbatim from brief, if applicable>
- **Non-goal honored:** <if this chunk specifically enforces a non-goal — e.g., a CI gate that blocks the non-goal capability>

## Context pack

Files, prior PRs, and design docs Claude must read before starting. The point: skip the rediscovery phase next session.

**Read first:**
- `path/to/file.ts` — <why this matters>
- `path/to/other.ts` — <why this matters>

**Reference:**
- `features/<feature>/brief.md`
- `features/<feature>/engineering-plan.md`
- <prior PR link, design doc link>

**Conventions / patterns to follow:**
- <e.g. "All new API routes use the project's auth middleware wrapper.">

## Factoring Contract

Machine-checkable structural contract for this chunk. `/plan-lint` parses these fields and rejects the plan if any rule is violated.

**Owns (writes)** — exact paths this chunk creates or modifies. Each entry: `path` — <what changes>. No file may appear in two chunks' Owns sets across the feature.

- `path/to/existing.ts` — <what changes>
- `path/to/new.ts` — <purpose; mark NEW>

**Reads (no writes)** — files this chunk depends on but does not modify. Every path here MUST already exist when this chunk starts: either in a prior chunk's Owns set (declared by slug below) or pre-existing in the repo at HEAD before the feature began.

- `path/to/dep.ts` — pre-existing
- `path/to/from-prior.ts` — owned by `<prior-slug>`

**Forbidden** — paths explicitly off-limits to this chunk. Use this when a sibling or later chunk owns a file that an inattentive implementer might wander into. Empty bullet list when no risk exists.

- `path/to/sibling-owned.ts` — owned by `<sibling-slug>`; do not touch

**Single concern** — one sentence. MUST NOT contain " and " (case-insensitive). If you can't compress this chunk's deliverable into one " and "-free sentence, split the chunk.

> <One sentence.>

**No scaffolding** — assertion: every file in Owns is referenced by code that runs when this chunk is merged. No stubs, dead helpers, or "framework for chunk N+1." If any file in Owns has no live consumer in this chunk, either delete it or move it into the chunk that consumes it.

- [ ] Confirmed: every Owns file has a live consumer in this chunk's diff.

**Abstraction earns its place** — if this chunk introduces an abstraction (base class, helper module, framework, factory, generic interface with one consumer), name **≥2 already-merged consumers** that will use it. If <2 consumers exist yet, defer the abstraction to the chunk that produces the second consumer.

- [ ] N/A — no new abstraction introduced.

OR

- Abstraction: `<name>` in `<file>`
- Consumer 1 (already merged): `<chunk-slug>` — `<file:symbol>`
- Consumer 2 (already merged): `<chunk-slug>` — `<file:symbol>`

## Contracts / types changed

API shapes, DB schema changes, prop signatures, anything other code depends on.

- <e.g. "Add `recoveryEligibleUntil: DateTime?` to `User` model.">
- <e.g. "New endpoint `POST /api/streak/recover` — returns `{ recovered: boolean, newStreak: number }`.">

## Tests to add

Specific cases, not "test the thing."

**Unit:**
- <case>

**Integration:**
- <case>

**E2E:**
- <flow>

## Acceptance criteria

Observable, testable conditions. User-visible where possible. Each item MUST name one of: a command that exits 0, a test that passes by name, a file that exists with a named symbol, a gate (lint/typecheck/test) that is green, or a user-visible behavior verifiable by manual click. `/plan-lint` rejects items containing the bare verbs **implement**, **complete**, **works**, **ensure**, or **handle** without a measurable predicate after them — those are scope discretion in disguise.

- [ ] <e.g. "Eligible user sees the 'Recover streak' card on home screen the day after a miss.">
- [ ] <e.g. "Tapping the card navigates to `/streak/recover` and shows the make-up session.">
- [ ] <e.g. "Completing the make-up session restores the streak count to its pre-miss value.">
- [ ] <e.g. "`<typecheck command>` exits 0.">
- [ ] <e.g. "Test `<path>/<file>.test.ts::<named_test_case>` passes.">
- [ ] <e.g. "File `<path>/<file>.ts` exports symbol `<symbolName>`.">
- [ ] <e.g. "CI gate `<lint job name>` is green on the chunk's PR.">
- [ ] <e.g. "E2E flow `<path>/<flow>.<ext>` passes locally.">
- [ ] <e.g. "Manual: <observable user-visible step the human verifies>.">

These are the canonical exit-criterion shapes. Any item not matching one of these patterns is too vague to verify and will fail `/plan-lint`.

## Review checklist

What you eyeball before approving the PR. The QA-with-myself contract.

- [ ] <e.g. "Run the recovery flow end-to-end on the target platform.">
- [ ] <e.g. "Confirm push notification fires at 6pm in dev settings.">
- [ ] <e.g. "Check screenshot of new home-screen card matches design.">
- [ ] <e.g. "Verify no regression on existing streak display for users with active streaks.">

## Out of scope

What this chunk will *not* touch. Deferred to later chunks or to non-goals.

- <item>
