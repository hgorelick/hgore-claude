# <Feature Name> — Engineering Plan

**Brief:** [`brief.md`](./brief.md) · **Decisions:** [`decisions.md`](./decisions.md)

<!--
==========================================================================
HOW TO WRITE THIS DOC — read before editing.
==========================================================================

This is a contract, not a narrative. Frozen on approval. Edits only when
the brief changes. Tracker state (which chunks are merged, in flight, blocked)
lives in `git log`, the PR list, and the per-chunk plans. NEVER add it here.

ARCHITECTURE LEVEL ONLY. The engineering plan describes the architecture and
the chunk graph. It does NOT specify chunk-internal implementation. Per-chunk
plans (`features/<feature>/implementation/<slug>.md`) are written just before
each chunk starts, because earlier chunks change the codebase and invalidate
later assumptions. Baking implementation detail into the engineering plan
makes the plan stale by the time the implementer reads it.

  Forbidden in the engineering plan, allowed in the per-chunk plan:
  - Specific test names, action keys, e2e flow IDs (e.g. "TEST 4 covers …").
  - Internal phase splits inside one chunk ("Phase 1 does X, Phase 2 does Y").
  - Function-by-function file lists ("touches `personHydration.ts:hydrateCredits`").
  - Acceptance criteria, review checklists, files-to-create/touch lists.
  - SQL queries, regex patterns, exact log lines.

  Allowed in the engineering plan:
  - The chunk's name and one-line scope (the chunk index row).
  - Architecture-level contracts the chunk must honor (invariants, field
    precedence rules, rate-limit budgets, rollback paths).
  - Explicit cross-chunk dependencies (code deps, manual gates).

SECTION ORDER IS FIXED. Do not reorder, rename, or merge sections. Skip the
optional sections only when truly inapplicable; do not invent new sections
without first amending `features/README.md`.

  1. Brief mapping
  2. Architecture summary
  3. Decisions closure             (cross-chunk decisions resolved before chunks start)
  4. Invariants                    (optional)
  5. <Other domain contracts>      (optional, e.g. Field Precedence, Cost & Capacity)
  6. Chunk index
  7. Manual gates                  (optional)
  8. Dependency graph
  9. Risks / unknowns
 10. Rollout plan                  (optional)
 11. Out of scope

File-level ownership is NOT declared at the engineering-plan layer. Each
per-chunk plan declares its own Owns / Reads / Forbidden Factoring Contract
at the moment it is written (just-in-time). Pinning filenames at engineering-
plan time forces premature naming; chunk-plan authors discover them from the
repo when they actually have context.

CHUNK IDENTIFIERS — slugs, not numbers:
  - Every chunk has a stable `slug`: kebab-case, 2–4 words, descriptive of
    the chunk's CONCERN — what it does, not where it sits.
    Good: `schema-migration`, `wikidata-qid-backfill`, `cascade-direction-neutral`.
    Bad:  `phase-2-cascade`, `step-3`, `chunk-01`, `01a-cascade`, `wave-2-llm`.
  - Slugs are immutable once the plan is approved. Renames break PR links,
    decision-log references, chunk-plan filenames, and audit traces.
  - Forbidden slug shapes (all are numbered identifiers in disguise):
      `phase-N-*`, `step-N-*`, `wave-N-*`, `chunk-NN`, `NN-*`, `*-Na`/`*-Nb`.
    If you find yourself reaching for any of these, the slug is encoding
    position-in-graph instead of concern; rename it.
  - If a chunk grows, split it into two new concern-named slugs
    (`cascade-rewrite` + `callsite-migration`) — never introduce a sub-letter
    (`cascade-rewrite-a/b/c`) or a phase suffix.
  - Slugs are also the filename of the per-chunk plan:
    `features/<feature>/implementation/<slug>.md`.

FORBIDDEN PATTERNS — do NOT do any of these:
  - Status / PR / Mode / Owner / Last-updated columns or fields. Frozen plans
    do not track. Your only columns in the chunk index are:
    Slug | Chunk | Code deps.
  - Numbered chunk identifiers (`01`, `27a`, `Phase 2.b`). Use slugs.
  - Implementation detail (test names, file artifacts, internal phases,
    function names beyond architecture-level contracts). See "ARCHITECTURE
    LEVEL ONLY" above.
  - Meta-commentary about the doc itself ("this is the first place implementation
    detail enters the feature docs", "the section above…", "below we'll cover…").
    Delete it. Just write the content.
  - Hedging future tense ("we will likely", "this plan aims to", "we plan to",
    "the team should consider"). The plan IS the contract. Use declarative
    present tense.
  - Restating the brief or the README. Reference; do not repeat.
  - "Open questions" sections. Open questions belong in the brief and must be
    resolved before this plan is approved.
  - Trailing summary paragraphs that restate the section.
  - Tribunal/round-N findings or change-log notes inside the plan body. Decisions
    go in `decisions.md`. Lineage from older plans does not belong here.
  - Vague nouns ("the new system", "a helper", "some scripts") when the concrete
    name exists. Use the function name, table name, file path.

CROSS-REFERENCE FORMAT:
  - Chunks: `chunk schema-migration`, `chunks cascade-rewrite + callsite-migration`.
    Never "chunk 05", "Ch5", "Phase 2.b".
  - Other features: "features/<name>/engineering-plan.md".
  - Source files: backticked path, e.g. `src/lib/runId.ts`.
  - This plan's other sections: by section title, not "above" / "below".

TONE:
  - Declarative present tense.
  - Short paragraphs, ≤4 lines each. One idea per paragraph.
  - Concrete names, not generic descriptors.
  - No emojis. No exclamation marks.
==========================================================================
-->

> The brief is the input to this plan. Every chunk traces to a Goal, User-facing change, or Non-goal in the brief — see Brief Mapping below. If the brief changes, re-walk the mapping before amending the plan.

## Brief mapping

<!--
The load-bearing link between brief and plan. Tables only.
- One row per Goal / Change verbatim from the brief (left cell).
- Right cell: chunk numbers that deliver it. Empty right cell = planning gap; fix
  the brief or fix the chunks.
- "Verified by" column on the User-facing changes table names the chunk that ships
  the test (e2e, integration, manual checklist) — or "Manual review" if no automated check.
- "Supporting infrastructure" subsection only if some chunks don't directly deliver
  a brief Goal/Change but exist to unblock ones that do. Each bullet names the
  chunk(s) and which goal-bearing chunk(s) they unblock.
- "Non-goals enforcement" subsection: one bullet per brief Non-goal, naming how the
  plan keeps it out (a specific chunk's CI gate, a test that asserts absence, or
  "no chunk introduces capability X").
-->

### Goals

| Brief Goal | Delivered by chunks |
|---|---|
| <verbatim from brief> | <chunk slugs> |
| <verbatim from brief> | <chunk slugs> |

### User-facing changes

| Brief change | Delivered by chunks | Verified by |
|---|---|---|
| <verbatim from brief> | <chunk slugs> | <chunk slug or "Manual review"> |
| <verbatim from brief> | <chunk slugs> | <chunk slug or "Manual review"> |

### Supporting infrastructure

<!-- Drop this subsection entirely if every chunk maps to a Goal or Change above. -->

- **<chunk slug(s)>** — <what they do, in one line>. <Which goal-bearing chunk(s) they unblock.>

### Non-goals enforcement

- **<non-goal verbatim from brief>** — <how the plan ensures it stays out of scope.>
- **<non-goal verbatim from brief>** — <how the plan ensures it stays out of scope.>

## Architecture summary

<!--
One to two short paragraphs. Declarative, concrete.
- Name the technical core (function, table, library) in the first sentence.
- Around it: the systems and chunks that ring the core.
- No meta-commentary. No "this section". Just describe the architecture.
- If a foundation chunk delivers schema or infrastructure that the rest depends
  on, name it explicitly with the artifact (column, table, helper, flag).
-->

<Paragraph 1: the core. Concrete names. What replaces what, what flows where.>

<Paragraph 2 (optional): the supporting systems. Same style.>

## Decisions closure

<!--
Cross-chunk decisions resolved at the engineering-plan level, before any chunk
starts. This section exists to prevent decisions from being deferred into
chunks where they get re-litigated or quietly diverge across chunks.

A decision is "cross-chunk" if more than one chunk depends on a consistent
answer to it. Examples:
  - Naming convention for new tables, columns, or types.
  - Error-handling style (throw vs return Result, error code vocabulary).
  - Transaction boundary (per-row vs per-batch).
  - Logging shape (structured vs unstructured, which fields).
  - Idempotency / retry semantics.
  - Field precedence rules (which source wins on conflict).
  - Auth pattern (which middleware, which guard).

Each row: the decision, its resolution, and the chunks that must honor it.
A bound resolution is concrete and unambiguous — no "TBD", no "we'll figure
out later", no "depends on chunk X". If you can't bind it now, the chunk that
introduces it must own it (note that in the row's "Owned by" column instead).

If a decision affects exactly ONE chunk, drop it from this section — it belongs
in that chunk's per-chunk plan, not here.

Rows with status "deferred to <slug>" are ALLOWED only when that chunk is
genuinely the right place to decide; `/plan-lint` flags any row whose
resolution is "TBD" or hand-wavy.
-->

| Decision | Resolution | Chunks bound by it |
|---|---|---|
| <e.g. "Error code for already-blocked"> | <e.g. "Throw `CONFLICT` with message `'already_blocked'`"> | `block-mutation`, `block-profile-action` |
| <e.g. "Transaction boundary for cascade"> | <e.g. "One transaction per source row; failures isolate"> | `cascade-rewrite`, `callsite-migration` |

If any decision is genuinely owned by a single chunk and not yet decided, list it instead under that chunk's per-chunk plan — not here. This section is for **closure**, not deferral.

## Invariants

<!--
Optional. Include only if the feature has cross-chunk rules that any chunk
writing to the affected tables MUST preserve. Otherwise delete this section.

Each invariant gets one ### subsection:
- One-paragraph rule statement.
- "Enforced by:" bullet list naming the chunks and what they do to enforce.
- Hard SQL gates / test assertions go inline in fenced blocks where they're
  load-bearing for the contract.
-->

### <Invariant name>

<One-paragraph rule statement, declarative, no hedging.>

Enforced by:
- `<chunk-slug>` — <how it enforces>.
- `<chunk-slug>` — <how it enforces>.

## <Other domain contracts>

<!--
Optional. Include separate ## sections only when the feature has cross-chunk
contracts beyond invariants. Examples: "Field Precedence", "Cost & Capacity",
"SLA targets", "Quality gates". Same declarative style. Same forbidden patterns.

Delete this entire block (heading + comment) if the feature doesn't need it.
Do not leave a placeholder header.
-->

## Chunk index

<!--
List of every PR-sized unit of work, identified by slug. Columns are EXACTLY:
  | Slug | Chunk | Code deps |
No status, no PR, no owner, no mode, no last-updated, no number column.

Slug rules (also enforced in the top-of-file guidance):
  - kebab-case, 2–4 words, descriptive of the chunk's concern.
  - Immutable once the plan is approved. Renames break PR links, decision-log
    references, and chunk-plan filenames.
  - The slug is also the per-chunk plan's filename:
    `features/<feature>/implementation/<slug>.md`.

Chunk-name rules (the prose label that appears beside the slug):
  - 6–10 words. Plain English. Imperative-noun ("Schema migration", "Cache-bust
    pubsub backend infra") or descriptive ("Backfill Wikidata Q-IDs"). Pick one
    style and stay consistent across the index.
  - No "Phase N" / "Step N" prefixes — chunks aren't sub-steps of one process,
    they're independent PRs.
  - No "(WIP)", "(stretch)", "(if time)". A chunk is in or it isn't.

Code-deps cell:
  - Comma-separated chunk slugs (`schema-migration, llm-circuit-breaker`) or
    "—" for none.
  - Lists code dependencies only — i.e. chunks whose code this chunk imports or
    extends. Manual-gate dependencies (e.g. "after the audit --apply runs") live
    in the Manual gates section, not here.
-->

| Slug | Chunk | Code deps |
|------|-------|-----------|
| `<slug-a>` | <chunk name> | — |
| `<slug-b>` | <chunk name> | `<slug-a>` |
| `<slug-c>` | <chunk name> | `<slug-a>` |
| `<slug-d>` | <chunk name> | `<slug-b>`, `<slug-c>` |

## Manual gates

<!--
Optional. Include only when the plan has non-PR steps (operator dry-runs,
`--apply` invocations, snapshot captures) that block downstream chunks.
Each row: a gate name, what blocks it, and an optional "Requires" clause for
prerequisites that aren't simple chunk-merge dependencies.

Drop the section entirely if all blocking is chunk-to-chunk.
-->

| Gate | Blocks on |
|---|---|
| <gate name> | <chunk slugs and/or prior gate> |

Each `--apply` requires:
- <prerequisite, e.g. calibration evidence reviewed>
- <prerequisite, e.g. budget ballpark from --dry-run>
- <prerequisite, e.g. database snapshot captured>

## Dependency graph

<!--
ASCII DAG. Always include, even when linear — make the parallelism (or lack
of it) explicit. Two valid forms below; pick one.

If wave-numbered, also include the cross-wave gating rule.
-->

```
Wave 1:    schema-migration ‖ llm-tier-and-runid ‖ orphan-cleanup-hardening
Wave 2:    cascade-rewrite (← llm-tier-and-runid, schema-migration)
```

**Cross-wave rule:** don't start wave N+1 until wave N's PRs are all merged (or `--apply`s complete, for manual waves).

Or linear:
```
schema-migration → wikidata-qid-backfill → cascade-rewrite → callsite-migration
```

## Risks / unknowns

<!--
Bullet form. One bullet per risk. Each bullet:
  **<short risk title>.** <Impact in one sentence.> <Mitigation, owner, or
  explicit acceptance.>

No vague hedges. If a risk has no mitigation, say so and accept it.
-->

- **<risk title>.** <impact>. <mitigation or owner>.
- **<risk title>.** <impact>. <mitigation or owner>.

## Rollout plan

<!--
Optional. Skip the entire section if no flag, no migration, no monitoring.
Bulleted; only include lines that apply.
-->

- **Feature flag:** <name, default state, who flips it and when>
- **Schema migrations:** <which chunk, ordering relative to others>
- **Production data writes:** <which gates control them>
- **Monitoring:** <log paths, dashboards, alerts>
- **Rollback:** <strategy per chunk; last-resort recovery>

## Out of scope

<!--
Bullets. Mirror the brief's Non-goals plus any technical deferrals.
For technical deferrals, append a one-line reason. Brief-non-goal bullets are
verbatim and need no reason — the brief already explained.
-->

- <brief non-goal verbatim>
- <technical deferral> — <one-line reason>

---

Per-chunk implementation plans live in [`implementation/`](./implementation/) and are written just before each chunk starts (see `features/README.md`).
