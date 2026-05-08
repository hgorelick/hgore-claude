---
name: plan-lint
description: Deterministic structural lint for engineering plans and per-chunk implementation plans. Catches the structural defects that cause ill-factored, divergent code — DAG cycles, "and"-chunks, vague exit criteria, premature abstractions, position-encoded slugs — by parsing plan markdown and applying mechanical checks. No LLM judgment, runs in milliseconds. Invoke after authoring or editing any plan, before handoff. Pairs with `/engineering-plan-review-v2` and `/plan-review-v2` (which run the LLM-judgment review on top); plan-lint is the deterministic floor those skills assume has already passed.
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

If you only want one bar to clear: pass `/plan-lint` first, then run the v2 review skills. The two together close both the structural-defect and judgment-defect axes.

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

- A **feature directory** (`features/<name>/`): lints the engineering plan + every per-chunk plan under `implementation/`, and warns on indexed chunks that have no per-chunk plan yet.
- An **engineering plan file** (`features/<name>/engineering-plan.md`): lints just the engineering plan.
- A **per-chunk plan file** (`features/<name>/implementation/<slug>.md`): lints just that chunk.
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
| `slug-position-encoded` | FAIL | Slug matches `phase-N-*`, `step-N-*`, `wave-N-*`, `chunk-NN`, `NN-*`, or `*-Na`/`*-Nb` (encodes position-in-graph instead of concern). |
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

### Engineering-plan rules

| Rule | Severity | Trigger |
|---|---|---|
| `chunk-index-missing` | FAIL | No Chunk Index section / table. |
| `slug-shape` / `slug-position-encoded` | FAIL | Same as per-chunk; applied to every slug in the index. |
| `decisions-closure-missing` | WARN | No Decisions Closure section (warning, not fail — confirm there are no cross-chunk decisions to bind). |
| `decision-unresolved` | FAIL | A Decisions Closure row has a resolution that is empty, "TBD", or "figure out later". |
| `dep-unknown` | FAIL | A Code-deps cell references a slug not in the Chunk Index. |
| `dep-cycle` | FAIL | Dependency graph has a cycle. |

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
