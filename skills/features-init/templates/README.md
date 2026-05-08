# Features

This is the canonical home for all feature planning in this project. Every new feature follows the process below. Claude reads this on every feature task — keep it current.

## Folder layout

```
features/
  README.md                          # this file
  _template/                         # copy these when starting a new feature
    brief.md
    engineering-plan.md
    chunk.md
    decisions.md
  <feature-name>/                    # one folder per feature, kebab-case
    brief.md                         # product brief (the "why")
    engineering-plan.md              # chunk index + dependencies (the "what")
    decisions.md                     # decision log (append-only)
    implementation/
      <chunk-slug>.md                # one file per chunk, named by slug
      <other-chunk-slug>.md
      ...
  archive/
    <feature-name>/                  # shipped features move here once fully merged + verified
```

### Naming

- **Feature folder:** `kebab-case`, no number prefix (e.g. `streak-recovery`, not `042-streak-recovery`).
- **Chunk slug:** `kebab-case`, 2–4 words, descriptive of the chunk's **concern** — what it does, not where it sits in the graph. Good: `schema-migration`, `wikidata-qid-backfill`, `cascade-direction-neutral`. Bad: `phase-2-cascade`, `step-3`, `chunk-01`, `01a-cascade`, `wave-2-llm`. Slugs are immutable once the engineering plan is approved — renaming breaks PR links, decision-log references, and chunk-plan filenames.
- **Chunk file:** `<slug>.md` — exactly the slug, no number prefix, no order suffix. The slug is the stable identifier across the engineering plan, decisions log, and per-chunk plan.
- **Why no numbers (and no `phase-N`/`step-N`/`wave-N`):** these all encode **position-in-graph** rather than concern. A chunk that grows mid-plan becomes `27a/27b/27c`; reordering forces a renumber that invalidates every external reference. `phase-2-cascade` is the same anti-pattern in disguise — once `phase-1` splits into two, the suffix is wrong. Slugs are stable: a chunk that grows splits into two new concern-named slugs (`cascade-rewrite` + `callsite-migration`), each stable on its own. If you reach for a position-encoding slug, rename it after the work it does.

## The process

Every feature moves through three stages, in order. Do not start the next stage until the prior stage is approved.

### Stage 1 — Brief (`brief.md`)

High-altitude product doc. Answers *what problem* and *why now*. No implementation detail.

Required sections (see `_template/brief.md`):
- **Problem** — what's broken / missing for the user, in plain language.
- **Solution** — the proposed shape of the fix, one paragraph.
- **Goals** — what success looks like, in observable terms.
- **Non-goals** — what this feature explicitly will *not* do. Kills scope creep early.
- **User-facing changes** — screens, flows, copy, or behaviors the user will notice.
- **Open questions** — things to resolve before engineering plan.

### Stage 2 — Engineering plan (`engineering-plan.md`)

**The brief is the input. The engineering plan is derived from it.** Every chunk in the plan must trace back to a goal, a user-facing change, or a non-goal-induced constraint in the brief. If a chunk doesn't serve something in the brief, either the brief is missing a goal (update it) or the chunk shouldn't exist (drop it). The engineering plan opens with a **brief mapping** section that makes this trace explicit before any chunks are listed.

Breaks the feature into **chunks**. Each chunk = one PR. Chunks must be small enough to review in one sitting and shippable on their own (behind a flag if needed).

Required sections (see `_template/engineering-plan.md`), in order:
- **Brief mapping** — restate each Goal and User-facing change from the brief, then map it to the chunk(s) that deliver it. This is the load-bearing link between the two stages — if it's hand-wavy, re-read the brief or re-think the chunks.
- **Architecture summary** — one or two paragraphs on the approach. May introduce technical concepts the brief deliberately avoided.
- **Decisions closure** — cross-chunk decisions resolved at engineering-plan time, before any chunk starts. Prevents re-litigation and quiet divergence across chunks. Decisions affecting only one chunk belong in that chunk's plan, not here.
- **Chunk index** — list of every chunk + its code deps, identified by slug. Columns are exactly `Slug | Chunk | Code deps`. Slugs are stable references for the dependency graph and per-chunk plans.
- **Dependency graph** — explicit DAG (even if linear). States which chunks can run in parallel vs. must be sequential. `/plan-lint` enforces DAG acyclicity and resolves every dep slug against the Chunk index.
- **Risks / unknowns** — anything that might force re-planning mid-feature. Technical unknowns live here, not in the brief.
- **Rollout plan** — flags, migration order, monitoring. Where applicable.

**Once approved, the engineering plan is frozen.** It is the contract for what gets built, not a tracker of what's been built. Don't add status columns, "merged" annotations, or "last updated" timestamps — that information lives in `git log`, the PR list, and each per-chunk plan's `Status:` field. The only reason to edit a frozen plan is when the brief changes; in that case, re-walk Brief Mapping and amend whatever's affected.

#### The architecture-level rule (engineering plan vs chunk plan boundary)

The engineering plan describes the **architecture and the chunk graph**. The per-chunk plans describe the **implementation**. Mixing layers is the most common drift mode in this process — and the most damaging, because chunk-internal commitments baked into the engineering plan are stale by the time the implementer reaches them.

Forbidden in the engineering plan, allowed in the per-chunk plan:
- Specific test names, action keys, e2e flow IDs.
- Internal phase splits inside one chunk ("Phase 1 does X, Phase 2 does Y").
- Function-by-function file lists.
- Acceptance criteria, review checklists, files-to-create/touch lists.
- SQL queries, regex patterns, exact log lines.

Allowed in the engineering plan:
- The chunk's slug, name, and one-line scope (the chunk index row).
- Architecture-level contracts the chunk must honor (invariants, field precedence rules, rate-limit budgets, rollback paths).
- Explicit cross-chunk dependencies (code deps, manual gates).

**Smell test:** if you can't write the engineering-plan section without referencing the chunk's internal steps, the section belongs in the chunk plan instead — write it there, then come back and reduce the engineering-plan reference to the contract the chunk owes its neighbors.

### Stage 3 — Implementation plans (`implementation/<slug>.md`)

**The engineering plan is the input. The chunk plan is derived from it.** Each chunk plan opens with a back-reference to its row in the engineering plan's chunk index and to the brief items it serves. If you can't restate the chunk's purpose in terms of a brief Goal or User-facing change, stop and re-read both the brief and the engineering plan.

One file per chunk, named by slug (`implementation/<slug>.md` — no number prefix). Written *just before* starting that chunk, not all upfront — early chunks change the codebase and invalidate later assumptions.

Required sections (see `_template/chunk.md`):
- **Goal** — one sentence: what this chunk delivers. Must not contain " and ".
- **Brief link** — which Goal(s) and User-facing change(s) from the brief this chunk serves. One or two bullets.
- **Context pack** — exact files, prior PRs, design docs Claude must read before starting. The point is to skip the rediscovery phase next session.
- **Factoring Contract** — machine-checkable structural contract: Owns (writes), Reads (no writes), Forbidden, Single concern, No scaffolding, Abstraction earns its place. Subsumes the older "Files to touch" + "Files to create" sections — Owns carries those file-level annotations now. `/plan-lint` rejects the chunk if any field is missing or violates a structural rule.
- **Contracts / types changed** — API shapes, DB schema, prop signatures. Anything other code depends on.
- **Tests to add** — unit, integration, e2e. Specific cases, not "test the thing."
- **Acceptance criteria** — observable, testable conditions for "done." Each item must name a command, test, file+symbol, gate, or user-visible behavior — not a vague verb like "implement", "complete", or "ensure". `/plan-lint` rejects vague items.
- **Review checklist** — what the human will eyeball before approving. Screenshots, flows to click, perf numbers, etc.
- **Out of scope** — what this chunk will *not* touch (deferred to later chunks or non-goals).

After authoring or editing any plan (engineering or chunk), run `/plan-lint <path>` before handoff. The lint is deterministic — pure parsing — and catches DAG cycles, "and"-chunks, vague exit criteria, abstraction-before-consumers, and missing Factoring Contract fields in seconds. Lint failures block handoff.

## Decision log (`decisions.md`)

Append-only. Each entry: date, decision, why, alternatives rejected. Keeps us from re-litigating the same tradeoffs three weeks later.

Format:
```
## YYYY-MM-DD — <short title>
**Decision:** <what we're doing>
**Why:** <reason>
**Rejected:** <alternatives considered and why not>
```

## Lifecycle

- **Proposed** → brief drafted, not yet approved.
- **Active** → engineering plan approved; chunks in flight.
- **Shipped** → all chunks merged, feature verified end-to-end in the live app.
- **Archived** → folder moved to `features/archive/<feature-name>/`. Do this once shipped and stable for ~2 weeks; keeps `features/` scannable.

## Rules of thumb

- Briefs are for humans. Engineering plans and chunk plans are for Claude. Write them accordingly: briefs prose-y, plans structured and explicit.
- If a chunk plan can't be written without ambiguity, the engineering plan probably has the chunk wrong. Re-chunk before implementing.
- A chunk that takes more than one PR to land is a sign it should have been two chunks. Split into two slugs (`cascade-rewrite`, `callsite-migration`); never introduce a sub-letter (`cascade-rewrite-a/b/c`).
- Status tracking lives on the per-chunk plan's `Status:` field, not on the engineering plan. The engineering plan is frozen — adding a status column to it is a structural defect the review skill flags as CRITICAL.
