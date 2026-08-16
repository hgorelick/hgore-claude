---
name: plan-lint
description: Deterministic structural lint for briefs, engineering plans, and per-chunk implementation plans. Catches the structural defects that cause ill-factored, divergent code — DAG cycles, "and"-chunks, vague exit criteria, premature abstractions, position-encoded slugs, review-complexity budget overflows, undestined deferrals, invariants with no falsifier — by parsing markdown and applying mechanical checks. No LLM judgment, runs in milliseconds. Invoke after authoring or editing any plan, before handoff. Pairs with `/engineering-plan-review-v2` and `/plan-review-v2` (which run the LLM-judgment review on top); plan-lint is the deterministic floor those skills assume has already passed.
user-invocable: true
---

# /plan-lint

Deterministic structural lint for engineering plans and per-chunk implementation plans. Pure parsing, zero LLM judgment, runs in milliseconds. Invoke after authoring or editing any plan, before declaring it done or handing it off to the implementer.

## What this skill catches (and what it does not)

`/plan-lint` enforces the **structural** properties that make a plan converge by construction. It does NOT replace `/engineering-plan-review-v2` or `/plan-review-v2`, which apply LLM-driven judgment on top — `/plan-lint` is the deterministic floor those skills assume has already passed.

| Caught by `/plan-lint` (mechanical) | Caught by `/engineering-plan-review-v2` / `/plan-review-v2` (judgment) |
|---|---|
| Dependency graph has a cycle | Whether a chunk's stated scope actually serves the brief |
| Code-deps reference an unknown slug | Whether an "obvious" chunk is missing |
| Chunk Goal or Single-concern contains " and " | Whether the architecture summary is coherent |
| Acceptance criterion uses "implement" / "complete" / "ensure" with no measurable predicate | Whether two chunks would be better merged or further split |
| Slug uses position-encoded shape (`phase-2-cascade`, `step-3`) | Whether a slug name is descriptive of the chunk's concern |
| Abstraction declared with <2 already-merged consumers | Whether a chunk hides implementation detail in the engineering plan |
| Per-chunk plan Owns/Single-concern shape | Whether the brief itself has gaps |
| Decisions Closure row is "TBD" or hand-wavy | Whether resolved decisions are the right calls |
| Goals table missing `Verified by` / Scope enforcement missing `Kind` / no acceptance-chunk DAG sink (WARN) | Whether every Goal + testable scope item actually has an executable proof (the review's `GOAL_VERIFICATION_GAP` gate, which reads the brief) |
| Chunk crosses more subsystems or invariant classes than the cap allows | Whether the chunk boundary is in the right place |
| Foundation chunk that nothing depends on | Whether a chunk labelled Behavior is really Behavior |
| Invariant with no `Form:` or `Falsifier:` | Whether the stated invariant is the one that matters, or whether a needed one is missing |
| Deferred scope item with no destination | Whether the deferral is a defensible cut |
| Threat model neither populated nor disclaimed | Whether the feature actually has a threat surface (the review owns that trigger) |

If you only want one bar to clear: pass `/plan-lint` first, then run the v2 review skills. The two together close both the structural-defect and judgment-defect axes.

## Project configuration

The review-complexity budget is project-specific, so nothing about it lives in `lint.py` — this lint runs against more than one repo and a guessed subsystem map produces confident nonsense. The subsystem globs, the invariant-class vocabulary, and the thresholds load from `features/lint-config.json`, found by walking up from the artifact being linted.

**When that file is absent, every check that depends on it skips silently.** A project that has not opted into the budget gets the project-agnostic rules and nothing else.

Keys: `subsystems` (name → globs), `zero_weight` (docs; excluded entirely), `half_weight` (tests; half a file each and never counted as a subsystem, so a well-tested chunk isn't pushed over a no-exemption cap), `invariant_classes`, and `budget` (`files_target` / `files_cap` / `subsystems_target` / `subsystems_cap` / `invariant_classes_target` / `invariant_classes_cap`).

## Legacy artifacts warn, they do not fail

Conventions arrive after plans are already written. A rule that fails every pre-existing artifact trains you to ignore the lint, so each new-convention rule detects the old shape and warns instead:

- A chunk plan with **neither** `Kill criteria` nor `Invariant classes touched` predates both; one `chunk-plan-legacy-shape` WARN replaces the two FAILs, and the budget caps drop to WARN for that chunk (it may already be merged — it cannot be re-split). A plan carrying one of the two is new-shape, and the missing one is a real FAIL.
- An `## Invariants` section where **no** entry carries `Form:` or `Falsifier:` warns once rather than failing per entry.
- A missing `## Invariants`, `## Threat model`, or `Intent` column warns. Present-but-empty fails — an articulated "none" is the deliverable, and an empty section reads exactly like a missing one.
- A `Decisions closure` table with no bound-chunks column warns when the bound slugs are named inline in the resolutions, or when each row cites `decisions.md`. The column exists so a later amendment can find what to re-sweep; both older shapes serve that purpose, less scannably.

**Out of scope, by design.** `/plan-lint` does NOT enforce a cross-chunk file ownership map at the engineering-plan layer. File-level ownership is the chunk plan's job: each chunk plan declares its own `Owns` / `Reads` / `Forbidden` sets at the moment it is written (just-in-time), when the author knows which files actually exist or are about to be created. Pinning filenames at engineering-plan time forces premature naming that the chunk-plan author would otherwise discover from the repo, and the resulting drift between layers is itself a defect this skill used to catch and now no longer needs to.

## When to invoke

- After authoring a new engineering plan (`features/<name>/engineering-plan.md`).
- After authoring a new per-chunk plan (`features/<name>/implementation/<slug>.md`).
- After editing the chunk index or dependency graph of an existing engineering plan.
- After splitting or merging chunks, regardless of layer.
- As Stage 0 of `/engineering-plan-review-v2` and `/plan-review-v2` (those skills invoke `/plan-lint` automatically before persona prosecution; if it FAILs, persona prosecution short-circuits with a `STRUCTURAL_LINT_FAILED` blocker).

## Invocation

```
/plan-lint <path>
```

`<path>` is one of:

- A **feature directory** (`features/<name>/`): lints the brief, the engineering plan, and every per-chunk plan under `implementation/`, and warns on indexed chunks that have no per-chunk plan yet. A feature with a brief but no engineering plan is the Proposed lifecycle state, not a defect — the brief is linted and the missing plan warns.
- A **brief** (`features/<name>/brief.md`): lints just the brief.
- An **engineering plan file** (`features/<name>/engineering-plan.md`): lints just the engineering plan.
- A **per-chunk plan file** (`features/<name>/implementation/<NN>-<slug>.md`, or legacy `<slug>.md`): lints just that chunk. The `NN-` creation-index prefix is stripped before the slug is derived.
- A **lightweight ad-hoc plan** (`.scratch/*.md`, single-doc chunked plans): runs the chunk-plan checks on every `### Chunk: `<slug>`` block found.

The skill runs the script at `~/.claude/skills/plan-lint/lint.py` and reports findings.

## How to invoke (for Claude)

When the user invokes `/plan-lint <path>`, run:

```bash
python3 ~/.claude/skills/plan-lint/lint.py <path>
```

Report the script's stdout to the user verbatim, then summarize:

- If exit code is 0: state "Lint clean — N WARN findings, no FAILs" and the plan is ready for handoff or `/engineering-plan-review-v2` / `/plan-review-v2`.
- If exit code is 1: state "Lint FAILED — N FAILs found" and walk through each FAIL by rule. For each, recommend the concrete fix (split chunk, add measurable predicate, etc.). Do NOT proceed to review or implementation handoff until FAILs are resolved.
- If exit code is 2: usage / IO error — re-check the path argument.

When `/plan-lint` is invoked as Stage 0 of a review skill (not directly by the user), behavior is:

- Lint clean → continue to Stage 1 of the review.
- Lint FAILED → emit `STRUCTURAL_LINT_FAILED` blocker with the lint output appended; do NOT spawn persona prosecution. Tell the user to fix the structural defects and re-invoke.

## Lint rules (full list)

### Per-chunk-plan rules

| Rule | Severity | Trigger |
|---|---|---|
| `slug-shape` | FAIL | Slug is not kebab-case, 2–4 words. |
| `slug-position-encoded` | FAIL | Slug matches `phase-N-*`, `step-N-*`, `wave-N-*`, `chunk-NN`, `NN-*`, or `*-Na`/`*-Nb` (encodes position-in-graph instead of concern). The slug is the chunk's *identity* — the H1's backticked slug, or the filename stem when no H1 is present. A leading `NN-` **creation-index prefix on the filename** (e.g. `03-cascade-rewrite.md`) is stripped before this check, so it is allowed; `NN-*` here still rejects an identity slug that literally starts with a number. |
| `slug-filename-mismatch` | WARN | The filename's slug-part (after stripping any `NN-` creation-index prefix) does not match the chunk's identity slug from the H1. The file is misnamed and won't resolve when a sister skill globs `*-<slug>.md`. Suppressed for ad-hoc files outside an `implementation/` directory. |
| `goal-missing` | FAIL | No Goal section, or Goal section has no content beyond the placeholder. |
| `goal-and` | FAIL | Goal sentence contains the word "and" (case-insensitive). |
| `owns-empty` | FAIL | Factoring Contract is missing or has no paths in Owns. |
| `single-concern-missing` | FAIL | Factoring Contract has no Single concern blockquote. |
| `single-concern-and` | FAIL | Single concern blockquote contains "and". |
| `no-scaffolding-missing` | FAIL | Factoring Contract has no No-scaffolding assertion. |
| `abstraction-block-missing` | FAIL | Factoring Contract has no Abstraction-earns-its-place block (use "N/A" if no abstraction is introduced). |
| `abstraction-too-few-consumers` | FAIL | Abstraction is declared but lists fewer than 2 already-merged consumers. |
| `ac-empty` | FAIL | No acceptance criteria checkboxes. |
| `ac-vague` | FAIL | Acceptance criterion uses one of `implement`, `complete`, `works`, `ensure`, `handle`, `support` without a measurable predicate (command, test name, file+symbol, gate, or quoted value) on the same line. |
| `chunk-plan-legacy-shape` | WARN | Neither `Kill criteria` nor `Invariant classes touched` is present — the plan predates both conventions. Suppresses the two FAILs below and downgrades the budget caps for this chunk. |
| `kill-criteria-missing` | FAIL | No `Kill criteria` section. State at least one pre-stated, falsifiable condition under which the chunk stops and returns to planning. |
| `kill-criteria-empty` | FAIL | Section present but every item is an unfilled template placeholder. |
| `kill-criteria-vague` | FAIL | A kill criterion names no checkable condition — same measurable-predicate bar as acceptance criteria. A condition you can't evaluate can't stop anything. |
| `invariant-classes-missing` | FAIL | Factoring Contract has no `Invariant classes touched` field. `none` is valid; silence is not, because it makes the no-exemption cap uncheckable. |
| `invariant-class-unknown` | FAIL | Declares a class not listed in `features/lint-config.json`. |
| `invariant-classes-over-target` / `-over-cap` | WARN / FAIL | More classes than the budget allows. **The cap has no exemption** — over it, the chunk splits. |
| `budget-files-over-target` / `-over-cap` | WARN / FAIL | The weighted `Owns` count exceeds the budget. Docs weigh 0, tests weigh 0.5. |
| `budget-subsystems-over-target` / `-over-cap` | WARN / FAIL | `Owns` crosses more subsystems than the budget allows. **The cap has no exemption** — crossing this many means an undocumented cross-layer contract. |
| `owns-path-unclassified` | WARN | An `Owns` path containing a slash matches no subsystem glob and no weight rule. Either the path is wrong or the config needs the subsystem. |

Budget rules require `features/lint-config.json`; without it they skip.

### Brief rules

| Rule | Severity | Trigger |
|---|---|---|
| `goals-empty` | WARN | No Goals bullets found. |
| `goal-no-measure` | WARN | A Goal has no `Measured by:` clause. Without the check that answers "did this ship whole?", a subset delivery reviews clean — the recurring outcome-scope failure. WARN because a brief is prose and this reads it heuristically; the authoritative gate is `/brief-review-v2`. |
| `scope-section-missing` | WARN | Neither `## Scope` nor `## Non-goals`. |
| `scope-legacy-non-goals` | WARN | Uses a bare `## Non-goals` section. Read as *Not planned*; migrate to the four buckets on the next touch. |
| `deferral-no-destination` | FAIL | An `Intentionally deferred` item names no issue (`#123`) or follow-on feature slug. An undestined deferral is indistinguishable from a silent narrowing — that is what the bucket exists to prevent. If no destination exists, the item belongs in `Not in scope (this release)` or `Not planned`. |

### Engineering-plan rules

| Rule | Severity | Trigger |
|---|---|---|
| `chunk-index-missing` | FAIL | No Chunk Index section / table. |
| `slug-shape` / `slug-position-encoded` | FAIL | Same as per-chunk; applied to every slug in the index. |
| `decisions-closure-missing` | WARN | No Decisions Closure section (warning, not fail — confirm there are no cross-chunk decisions to bind). |
| `decision-unresolved` | FAIL | A Decisions Closure row has a resolution that is empty, "TBD", or "figure out later". |
| `dep-unknown` | FAIL | A Code-deps cell references a slug not in the Chunk Index. |
| `dep-cycle` | FAIL | Dependency graph has a cycle. |
| `goals-verified-by-missing` | WARN | Brief mapping → Goals table has no `Verified by` column. Every Goal needs an executable acceptance proof (or `Manual review — <reason>`). Structural presence only; coverage-vs-brief is the review's `GOAL_VERIFICATION_GAP` gate (plan-lint has no brief). |
| `non-goals-kind-missing` | WARN | Brief mapping → Scope enforcement table has no `Kind` column (`testable-absence` \| `scope-boundary` \| `deferred-tracked`). Testable scope items need an assert-absence test. |
| `decisions-closure-missing-bound-chunks` | FAIL / WARN | No `Chunks bound by it` column. Downgraded to WARN when the resolutions name their bound slugs inline, or when each row cites `decisions.md` — both older shapes still let a later amendment find the sweep list. |
| `chunk-intent-column-missing` | WARN | Chunk index has no `Intent` column. Predates the convention; migrate on the next touch. |
| `chunk-intent-invalid` | FAIL | Intent is not one of `Foundation`, `Behavior`, `Hardening`, `Migration`. |
| `foundation-chunk-orphaned` | FAIL | A `Foundation` chunk that no other chunk depends on. Foundation changes no behavior, so with no consumer it ships dead scaffolding — the Factoring Contract's No-scaffolding rule, applied one layer up at plan time. |
| `invariants-section-missing` | WARN | No `## Invariants` section. It is required; state the rules or write `No cross-chunk invariants — <reason>.` |
| `invariants-empty` | FAIL | Section present with neither an invariant nor the disclaimer. An empty section and a missing one read identically; neither is an answer. |
| `invariants-legacy-shape` | WARN | Invariants present but none carries `Form:` or `Falsifier:`. Predates the convention. |
| `invariant-form-missing` / `-invalid` | FAIL | An invariant has no `**Form:**` line, or one outside `test` \| `assert` \| `gate` \| `doc`. |
| `invariant-falsifier-missing` | FAIL | An invariant has no `**Falsifier:**` line. Without the one check that would disprove it, what is written is prose, not a rule. |
| `invariant-doc-only-high-risk` | WARN | `Form: doc` on an invariant naming a configured high-risk class. A doc-form invariant in auth, score math, or data integrity is unenforced by construction. |
| `invariants-disclaimer-contradicted` | FAIL | Declares `No cross-chunk invariants` while a populated Threat model cites invariants in its detection column. One of the two is wrong. |
| `threat-model-section-missing` | WARN | No `## Threat model` section. It is required; populate it or disclaim it. |
| `threat-model-empty` | FAIL | Section present with neither a populated row nor `No threat-model surface — <reason>.` The articulated decision is the deliverable. |
| `acceptance-chunk-missing` | WARN | No dedicated acceptance chunk found in the Chunk index — a DAG sink whose concern is proving brief Goals honored / testable Non-goals excluded. Heuristic match on the chunk name/slug (`accept` / `verif` / `conformance` / `prove … goal`); the authoritative check is the review's Goal-verification audit. |
| `acceptance-chunk-not-sink` | WARN | The acceptance chunk is depended on by another chunk. The acceptance suite must be a DAG sink so it runs against the assembled feature. |

### Cross-plan rules (when linting a feature directory)

| Rule | Severity | Trigger |
|---|---|---|
| `chunk-plan-missing` | WARN | An indexed slug has no `implementation/<slug>.md` yet (per-chunk plans are written just-in-time, not upfront — warning only). |

## How to read output

Each finding is one line:

```
SEVERITY  [rule-name]  <file>: <message>
```

The trailing summary line counts FAILs and WARNs. Exit code is 0 iff `FAIL == 0`. WARNs are informational and do not block.

## How to fix common failures

| Rule | Typical fix |
|---|---|
| `goal-and` / `single-concern-and` | Split the chunk into two slugs. The "and" is two PRs in disguise. |
| `owns-empty` | Add the explicit list of files this chunk creates or modifies, with one-line "what changes" annotations. |
| `dep-cycle` | The chunks are tangled. Find the smallest interface between them and extract it into a third chunk that both depend on. |
| `dep-unknown` | A Code-deps cell names a slug that doesn't exist in the Chunk Index. Either fix the typo or remove the dep. |
| `ac-vague` | Replace "implement X" with "test X passes" or "command Y exits 0" or "file Z contains symbol W" or "Maestro flow F passes." |
| `abstraction-too-few-consumers` | Defer the abstraction until ≥2 concrete consumers exist. Inline the duplicate code in the meantime — three similar lines is better than a premature abstraction. |
| `budget-subsystems-over-cap` | Split along the subsystem boundary. There is no exemption to argue for: the overflow says the chunk carries a cross-layer contract nobody wrote down, so find that contract and make it the seam. |
| `invariant-classes-over-cap` | Split so each chunk changes one class. Two classes moving together in one diff is where cross-domain interactions hide. |
| `budget-files-over-cap` | Usually a second concern crept in — look at the `Owns` list for the file that doesn't serve the Single concern. If the change is genuinely cohesive, that is the one axis where a considered override is defensible. |
| `foundation-chunk-orphaned` | Either fold it into the chunk that consumes it, or the label is wrong and it is really Behavior. |
| `kill-criteria-missing` | Ask: what would I learn mid-chunk that means this plan is wrong? Write that, with a threshold. |
| `invariant-falsifier-missing` | Write the one query, test, or gate that would prove the invariant violated. If you can't, the invariant is too vague to enforce — sharpen it or drop it. |
| `deferral-no-destination` | File the issue and put its number in the bullet, or move the item to `Not in scope (this release)` / `Not planned`. |
| `decision-unresolved` | Bind the decision now. If you genuinely can't, it must be owned by a single chunk; remove the row from Decisions Closure and put the decision in that chunk's per-chunk plan. |

## Invariants this skill protects

These are the structural invariants that, when satisfied across an entire feature, produce convergent code:

1. **Acyclic decomposition** — the chunk graph is a DAG (cycle-free, all deps resolve to known slugs).
2. **Single concern per chunk** — no "and" in the deliverable.
3. **No premature abstraction** — abstractions only earn their place once ≥2 concrete consumers exist.
4. **Verifiable exit criteria** — every "done" condition names a measurable artifact.
5. **No half-built scaffolding** — every Owns file has a live consumer in this chunk.
6. **Decisions closed up front** — no "TBD" survives into chunk implementation.
7. **Slug stability** — no position-encoded slug shapes that break under re-cuts.
8. **Per-chunk Factoring Contract** — every chunk plan declares Owns, Single-concern, No-scaffolding, and Abstraction-earns-its-place explicitly.

File-level ownership uniqueness across chunks is the chunk-plan author's responsibility, not the engineering plan's. The author of chunk N's plan reads chunks 1..N-1's plans to see what's already been written; if a path collision arises, it's resolved at that moment with full repo context, not pre-litigated at engineering-plan time on speculative filenames.

## Why this skill exists

The v2 review skills (`/engineering-plan-review-v2`, `/plan-review-v2`) catch structural problems *after* a plan is written. By then the plan-writer has already committed to a decomposition; "fixes" mean re-cutting chunks. That's exactly the kind of churn the v2 skills were designed to prevent on the review side — applying the same discipline on the writing side closes the loop.

`/plan-lint` is deterministic. It cannot make a wrong judgment call because it makes no judgment calls. The rules are conservative — they will let a bad plan through (judgment was needed) before they reject a good one (structure was fine). That's why `/plan-lint` is the floor, and the v2 review skills are the ceiling.

See `personas/ai-development.md` § "Factoring Contract" for the rationale per field, and `features/_template/chunk.md` + `features/_template/engineering-plan.md` for the canonical template shapes the lint expects.
