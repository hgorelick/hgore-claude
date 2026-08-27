---
name: plan-lint
description: Deterministic structural lint for the whole artifact chain — vision, specs, briefs, engineering plans, and per-chunk implementation plans. Catches the structural defects that cause ill-factored, divergent code — DAG cycles, "and"-chunks, vague exit criteria, premature abstractions, position-encoded slugs, review-complexity budget overflows, undestined deferrals, invariants with no falsifier, split lines that enumerate instead of deciding, decompositions that leak status into a truth doc — by parsing markdown and applying mechanical checks. No LLM judgment, runs in milliseconds. Invoke after authoring or editing any artifact in the chain, before handoff. Pairs with `/vision-review`, `/spec-review`, `/engineering-plan-review-v2`, and `/plan-review-v2` (which run the LLM-judgment review on top); plan-lint is the deterministic floor those skills assume has already passed.
user-invocable: true
---

# /plan-lint

Deterministic structural lint for every document in the artifact chain: `vision.md` and its spec map, a `spec.md` and its `## Decomposition`, briefs, engineering plans, and per-chunk implementation plans. Pure parsing, zero LLM judgment, runs in milliseconds. Invoke after authoring or editing any of them, before declaring it done or handing it off downstream.

## What this skill catches (and what it does not)

`/plan-lint` enforces the **structural** properties that make an artifact converge by construction. It does NOT replace the review skills, which apply LLM-driven judgment on top — `/plan-lint` is the deterministic floor `/vision-review`, `/spec-review`, `/engineering-plan-review-v2`, and `/plan-review-v2` assume has already passed.

| Caught by `/plan-lint` (mechanical) | Caught by the review skills (judgment) |
|---|---|
| A split line that enumerates instead of deciding | Whether a predicate that does decide puts the next rule on the right side |
| A map entry naming a spec no entry owns, or a Depends-on with no split line against it | Whether the seam is in the right place at all |
| A status token in a decomposition section | Whether an exclusion is honest |
| A brief in the Briefs table that Coverage never names, or vice versa | Whether the proof owner's brief could actually carry the falsifier |
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

## A document in an older shape warns, it does not fail

A rule that fails every artifact written to an earlier shape trains you to ignore the lint. So each rule detects the shape it is looking at and warns when the shape itself is the finding, reserving FAIL for a structure that exists and is wrong:

- A chunk plan carrying **neither** `Kill criteria` nor `Invariant classes touched` is in the shape that has neither; one `chunk-plan-legacy-shape` WARN replaces the two FAILs, and the budget caps drop to WARN for that chunk (it may already be merged — it cannot be re-split). A plan carrying one of the two is in the current shape, and the missing one is a real FAIL.
- An `## Invariants` section where **no** entry carries `Form:` or `Falsifier:` warns once rather than failing per entry.
- A missing `## Invariants`, `## Threat model`, or `Intent` column warns. Present-but-empty fails — an articulated "none" is the deliverable, and an empty section reads exactly like a missing one.
- A `Decisions closure` table with no bound-chunks column warns when the bound slugs are named inline in the resolutions, or when each row cites `decisions.md`. The column exists so a later amendment can find what to re-sweep; both other shapes serve that purpose, less scannably.
- A `vision.md` with **no spec map at all** warns once and skips every other vision rule. A map that exists but is malformed fails.
- A `spec.md` with **no `## Decomposition` section** warns once and skips every other spec rule. A section that exists but is malformed fails.
- A `spec.md` missing one of the universal-core sections warns once and names them, and the checks that read a missing section skip.

**Ship mode overrides this.** `--strict` counts every WARN as blocking, because a document an author skill is about to ship is not in an older shape by accident. The reporting run, and `--draft`, leave WARN informational.

**Out of scope, by design.** `/plan-lint` does NOT enforce a cross-chunk file ownership map at the engineering-plan layer. File-level ownership is the chunk plan's job: each chunk plan declares its own `Owns` / `Reads` / `Forbidden` sets at the moment it is written (just-in-time), when the author knows which files actually exist or are about to be created. Pinning filenames at engineering-plan time forces premature naming that the chunk-plan author would otherwise discover from the repo, and the drift between the two layers that follows is itself the defect.

## When to invoke

- After authoring or re-seeding `vision.md`'s spec map.
- After authoring a `spec.md`'s `## Decomposition` section, or after any spec edit above it that could move what a unit is.
- After authoring a new engineering plan (`features/<name>/engineering-plan.md`).
- After authoring a new per-chunk plan (`features/<name>/implementation/<slug>.md`).
- After editing the chunk index or dependency graph of an existing engineering plan.
- After splitting or merging chunks, regardless of layer.
- As the deterministic gate inside `/vision-author` and `/spec-author`, which run it against their in-memory draft before ground truth, hard-blocking — `--strict` in ship mode, the plain reporting run under `--draft`.
- As Stage 0 of `/vision-review`, `/spec-review`, `/engineering-plan-review-v2`, and `/plan-review-v2` (those skills invoke `/plan-lint` automatically before persona prosecution; if it FAILs, persona prosecution short-circuits with a `STRUCTURAL_LINT_FAILED` blocker).

## Invocation

```
/plan-lint [--type <kind>] [--strict] <path>
```

`<path>` is one of:

- A **vision document** (`vision.md`): lints the spec map.
- A **spec** (`specs/<slug>/spec.md`, or a root `spec.md`): lints the `## Decomposition` section.
- A **repo root** or a **`specs/<slug>/` directory**: resolves to the `vision.md` or `spec.md` it holds. Only when none of the feature-layout markers are present, so a feature directory still resolves as one.
- A **feature directory** (`features/<name>/`): lints the brief, the engineering plan, and every per-chunk plan under `implementation/`, and warns on indexed chunks that have no per-chunk plan yet. A feature with a brief but no engineering plan is the Proposed lifecycle state, not a defect — the brief is linted and the missing plan warns.
- A **brief** (`features/<name>/brief.md`): lints just the brief.
- An **engineering plan file** (`features/<name>/engineering-plan.md`): lints just the engineering plan.
- A **per-chunk plan file** (`features/<name>/implementation/<NN>-<slug>.md`, or legacy `<slug>.md`): lints just that chunk. The `NN-` creation-index prefix is stripped before the slug is derived.
- A **lightweight ad-hoc plan** (`.scratch/*.md`, single-doc chunked plans): runs the chunk-plan checks on every `### Chunk: `<slug>`` block found.

`--type <kind>` forces the document kind, for a draft whose filename does not carry its identity — the shape an author skill lints its in-memory draft in. `<kind>` is one of `vision`, `spec`, `brief`, `engineering-plan`, `chunk`, and it takes a file, never a directory. Without it the kind comes from the path, exactly as above.

`--strict` counts WARN as blocking: any finding at all exits 1. It is the hook a ship-mode author gate hangs on, because the two shape WARNs (`vision-map-missing`, `spec-decomposition-missing`) are exactly what a ship-mode draft must not carry — a map-less vision or a decomposition-less spec is not shippable, however tolerable it is in a document nobody is shipping today. `/vision-author` and `/spec-author` invoke `--strict` in ship mode and the plain reporting run under `--draft`.

**Both flags precede the path**, in either order: `--type spec --strict <path>` and `--strict --type spec <path>` are the same invocation. An option after the path is a usage error (exit 2), as is an unrecognized one.

The skill runs the script at `~/.claude/skills/plan-lint/lint.py` and reports findings.

## How to invoke (for Claude)

When the user invokes `/plan-lint <path>`, run:

```bash
python3 ~/.claude/skills/plan-lint/lint.py <path>
```

For a draft whose path does not carry its identity, or for an author skill's gate:

```bash
python3 ~/.claude/skills/plan-lint/lint.py --type spec <path>            # forced kind
python3 ~/.claude/skills/plan-lint/lint.py --type spec --strict <path>   # ship-mode gate
```

Report the script's stdout to the user verbatim, then summarize:

- If exit code is 0: state "Lint clean — N WARN findings, no FAILs" and the plan is ready for handoff or `/engineering-plan-review-v2` / `/plan-review-v2`.
- If exit code is 1: state "Lint FAILED — N FAILs found" and walk through each FAIL by rule. For each, recommend the concrete fix (split chunk, add measurable predicate, etc.). Do NOT proceed to review or implementation handoff until FAILs are resolved. Under `--strict` a run with zero FAILs and one or more WARNs also exits 1, and the trailing `--strict:` line names the count that blocked it.
- If exit code is 2: usage / IO error — re-check the path argument and the flag spelling.

When `/plan-lint` is invoked as Stage 0 of a review skill (not directly by the user), behavior is:

- Lint clean → continue to Stage 1 of the review.
- Lint FAILED → emit `STRUCTURAL_LINT_FAILED` blocker with the lint output appended; do NOT spawn persona prosecution. Tell the user to fix the structural defects and re-invoke.

## Lint rules (full list)

### Vision rules — the spec map

The map is required format of `vision.md`, the way a chunk DAG is required format of an engineering plan. Detection is a path ending in `vision.md`.

| Rule | Severity | Trigger |
|---|---|---|
| `vision-map-missing` | WARN | No spec map section. A vision in a shape without one warns rather than failing, and every other vision rule is skipped. |
| `vision-map-not-last` | FAIL | Any section follows the map, numbered or not. The map appends last: inserting it mid-document renumbers every section below and orphans every `vision §N` reference across the specs, the decision logs, and `CLAUDE.md`. Mid-cycle blocker scaffolding is the one tolerated follower, and only while `Status: needs-user-input` is set. |
| `vision-map-empty` | FAIL | The map section carries no entries. An empty map and a missing one read identically. |
| `vision-map-entry-shape` | FAIL | An entry missing `Owns`, `Split line`, `Depends on`, or `Covers` — present-but-blank counts as missing. |
| `vision-slug-shape` | FAIL | A spec slug that is not concern-named kebab-case (1–4 words), or that encodes position (`phase-N-*`, `step-N-*`, `NN-*`). The heading's own case is what is checked, so `` ### `Terrain` `` fails here exactly as a capitalized brief slug fails at the spec layer. Numbering is never a naming scheme; order is read off the dependency edges. |
| `vision-slug-duplicate` | FAIL | One slug heading two map entries. Two entries under one slug make every reference to it ambiguous, and entries are read positionally so both are linted rather than the later silently replacing the earlier. |
| `vision-split-line-enumerated` | FAIL | A split line that lists instead of deciding — an itemized series or an example marker with no decisional construction anywhere in it. A list classifies only what is already assigned. |
| `vision-split-line-unpaired` | FAIL | A neighbor named in `Depends on` with no split line against it. Only declared bullets count: a slug that merely appears inside another bullet's prose is a mention, not a seam. A dependency with no seam is an unbounded claim on the neighbour's surface. |
| `vision-split-line-unbulleted` | FAIL | A paragraph-form split line naming more than one neighbor. One predicate covering several neighbours cannot be read as exactly one per neighbour in either direction — the bullet-per-neighbour form is what makes that checkable. |
| `vision-split-line-doubled` | FAIL | Two split lines against the same neighbor. A seam needing two predicates is two seams, and the entry they split is two specs. |
| `vision-dangling-slug` | FAIL | An entry naming a spec no map entry owns, in `Depends on` or as a split-line neighbor; or an entry depending on itself. |
| `vision-unowned-block-missing` | FAIL | No unowned block. Vision material no spec owns is named explicitly, so silence is never mistaken for coverage. |
| `vision-unowned-block-empty` | FAIL | The unowned block is present with nothing in it. The articulated answer is the deliverable. |
| `vision-status-token` | FAIL | A lifecycle token inside the map — `shipped`, `owed`, `next` in its lifecycle shapes, `in flight`, `parked`, `on loan`, `TODO`, `WIP`, `Status:`, or a date. The map states what is permanently true about the decomposition; where the work stands belongs in `specs/README.md`. |

**Not lintable, and left to `/vision-review`:** whether a split-line predicate puts the next rule on the right side, whether a seam is in the right place, and whether a coverage claim matches the spec on disk.

### Spec rules — the `## Decomposition` section

`## Decomposition` is required format of a `spec.md`, between `## Non-goals & scope bounds` and `## Glossary`, with four fixed subsections in order: Seams, Briefs, Scope stubs, Coverage. Detection is a path ending in `spec.md`.

| Rule | Severity | Trigger |
|---|---|---|
| `spec-required-section-missing` | WARN | One of the universal-core sections is absent: Overview, Domain model & core concepts, Invariants & business rules, Feature areas, Non-goals & scope bounds, Decomposition, Glossary. A spec in a shape that omits one warns rather than failing, and the rules that read a missing neighbour (the Decomposition placement check reads Non-goals and Glossary) skip rather than fire. The optional sections are never checked for. |
| `spec-decomposition-missing` | WARN | No `## Decomposition` section. A spec in a shape without one warns rather than failing, and every other spec rule is skipped. |
| `spec-decomposition-misplaced` | FAIL | The section precedes `## Non-goals & scope bounds` or follows `## Glossary`. Stubs name their inherited exclusions by reference, so the exclusions have to already be on the page. Each neighbour is checked only when present; which sections a spec must carry is `_spec-common/spec-format.md`'s rule, not this lint's. |
| `spec-decomposition-subsection-missing` | FAIL | One of Seams, Briefs, Scope stubs, Coverage is absent. |
| `spec-decomposition-subsection-order` | FAIL | The four are present but out of order. Map before you cut — enumerating after cutting hides an unclaimed unit behind the seam that hardened around it. |
| `spec-briefs-table-missing` | FAIL | The Briefs subsection has no rows. |
| `spec-brief-slug-shape` | FAIL | A brief slug that is not concern-named kebab-case (1–4 words), or that encodes position. |
| `spec-brief-slug-duplicate` | FAIL | One slug in two Briefs rows. |
| `spec-brief-intent-column-missing` | WARN | The Briefs table has no `Intent` column. Without it the conformance sink and the Foundation obligation are uncheckable. |
| `spec-brief-intent-invalid` | FAIL | Intent is not one of `Foundation`, `Content`, `Instrument`, `Conformance`. |
| `spec-brief-dep-unknown` | FAIL | A `Depends on` cell names a slug that is not a Briefs row. |
| `spec-brief-dep-cycle` | FAIL | The Briefs dependency graph has a cycle, or a brief depends on itself. A dependency means one brief's scope reads a rule the other binds; a cycle means neither can be authored first. A self-edge is reported as itself and then dropped from the graph, so it does not also echo as a whole-graph cycle naming every brief downstream of it. |
| `spec-foundation-brief-orphaned` | FAIL | A `Foundation` brief no other brief depends on. Foundation exists to bind what its consumers read, so with no consumer it is dead — the chunk layer's rule, one layer up. |
| `spec-conformance-sink-missing` | WARN | No brief carries the `Conformance` intent. An invariant whose falsifier ranges over more than one brief needs a sink. Suppressed when there is no `Intent` column to read. |
| `spec-conformance-sink-not-sink` | FAIL | A `Conformance` brief that another brief depends on. The conformance suite runs against the assembled surface, so nothing may read it. |
| `spec-conformance-sink-incomplete` | WARN | A delivering brief no conformance sink reaches through the dependency graph, so an invariant spanning it has no falsifier owner. |
| `spec-coverage-table-missing` | FAIL | The Coverage subsection has no rows. Coverage is a table, not prose, because silent narrowing is what it exists to prevent. |
| `spec-coverage-brief-unknown` | FAIL | A Coverage row assigns a unit to a slug that is not a Briefs row. |
| `spec-brief-uncovered` | FAIL | A Briefs row whose slug Coverage never names. A brief that covers nothing is either unnecessary or its claims were never written down. |
| `spec-stub-missing` | FAIL | A Briefs row with no Scope stub, or a `### Scope stubs` subsection that holds no recognizable stub block at all. The stub is what `/brief-author` consumes, and a section with no stub in it must not lint cleaner than one with a stub missing. |
| `spec-stub-unknown` | FAIL | A Scope stub for a slug that is not a Briefs row. |
| `spec-decomposition-status-token` | FAIL | A lifecycle token inside the section — `shipped`, `in flight`, `parked`, `on loan`, `TODO`, `WIP`, `Status:`, or a date. The date check looks past a Coverage row's unit column, which quotes a spec unit verbatim and may legitimately name a date range; the lifecycle words apply to the whole line. The section says which side of a boundary a unit sits on; where that unit is in the pipeline belongs in `features/README.md`. |

**Not lintable, and left to `/spec-review`:** whether a split-line predicate actually decides the units the table assigns by it, whether an exclusion is honest, and whether a proof owner's brief could carry the falsifier. Seam-predicate presence is the reviewer's `SEAM_PREDICATE_MISSING` check, not this lint's.

A Coverage disposition cell is two-state: a brief slug, or `excluded by <seam name>`. An exclusion names a seam rather than a brief, so it contributes no slug to the bidirectional agreement checks. `owed` is a status token at the vision layer only — at the spec layer `Outcomes owed` is a Scope-stub field name and carries no lifecycle claim.

### Parsing both decomposition layers agree on

- **`\|` inside a table cell is content, not a column break.** Both formats' own templates write alternatives that way (`Foundation \| Content \| …`, a unit named `Multiplier bounds (0.5 \| 1.0 \| 2.0)`). Splitting on it would shift every cell right of the escape, so the Intent column reads a fragment of the Scope prose and the Brief column a fragment of the unit name.
- **The no-dependency sentinel is `none`, `—`, or `n/a`, backticked or bare.** The vision entry writes `none` and the Briefs table writes `—`; the rule that backticks every slug reference puts ticks around it either way. All of those read as zero edges, never as a dependency on a spec called `none`.
- **`Depends on` harvests its edges from the list, not from the commentary.** A parenthetical saying what the dependency is for, and an em-dash clause carrying the reverse-edge assumption, both routinely name a third slug that is not itself an edge — `` `terrain` (the `cell` model it reads) `` is one dependency, not two.

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
| `chunk-plan-legacy-shape` | WARN | Neither `Kill criteria` nor `Invariant classes touched` is present. A chunk plan carrying neither warns rather than failing: it suppresses the two FAILs below and downgrades the budget caps for this chunk. |
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
| `brief-oversize` | WARN | The brief file exceeds the advisory max size (15KB). Past that a brief is almost always re-narrating itself — Solution restating Goals, Scope restating both — or carrying detail that belongs in `decisions.md` or the engineering plan. Advisory: the fix is cutting repetition and narration, never commitments or `Measured by:` checks. |
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
| `chunk-intent-column-missing` | WARN | Chunk index has no `Intent` column. A plan without the column warns rather than failing, and every other intent rule is skipped. |
| `chunk-intent-invalid` | FAIL | Intent is not one of `Foundation`, `Behavior`, `Hardening`, `Migration`. |
| `foundation-chunk-orphaned` | FAIL | A `Foundation` chunk that no other chunk depends on. Foundation changes no behavior, so with no consumer it ships dead scaffolding — the Factoring Contract's No-scaffolding rule, applied one layer up at plan time. |
| `invariants-section-missing` | WARN | No `## Invariants` section. It is required; state the rules or write `No cross-chunk invariants — <reason>.` |
| `invariants-empty` | FAIL | Section present with neither an invariant nor the disclaimer. An empty section and a missing one read identically; neither is an answer. |
| `invariants-legacy-shape` | WARN | Invariants present but none carries `Form:` or `Falsifier:`. A section where no entry carries either warns rather than failing, and the per-entry rules are skipped. |
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

The trailing summary line counts FAILs and WARNs. Exit code is 0 iff `FAIL == 0`; WARNs are informational and do not block. Under `--strict` it is 0 iff there are no findings at all, and a second trailing line names the WARN count that blocked the run.

## How to fix common failures

| Rule | Typical fix |
|---|---|
| `vision-split-line-enumerated` | Replace the list with the one sentence that hands back a side for a rule the document does not yet contain. "Cells, durations, and spread go to terrain" becomes "a rule about how a state behaves is terrain's; a rule about what that state means to a typed thing stays here." |
| `vision-split-line-doubled` | Split the entry. Two predicates against one neighbour means two seams, and writing both under one seam name does not merge them. |
| `vision-split-line-unpaired` | Write the predicate against that neighbour as its own bullet, or drop the dependency. Naming the slug inside another bullet's sentence does not pair it. |
| `vision-split-line-unbulleted` | Break the paragraph into one bullet per neighbour, each leading with that neighbour's backticked slug. If the one sentence really does cover both, it is deciding two seams at once and each needs its own predicate. |
| `vision-slug-duplicate` | Merge the two entries, or rename one after the concern it actually owns. Two entries under a slug means the map cannot say which of them a dependency on that slug refers to. |
| `spec-required-section-missing` | Add the named sections. The Decomposition rules read Non-goals and Glossary by name, so a spec missing them silently loses the placement check. |
| `vision-status-token` / `spec-decomposition-status-token` | Move the sentence to the state sidecar — `specs/README.md` at the vision layer, `features/README.md` at the spec layer. A unit another domain owns renders as `excluded by <seam name>`, which is true whether or not that domain's document has been written. |
| `vision-unowned-block-missing` | List the vision material no spec owns. If the answer is "none", write that — the coverage claim is only falsifiable once the block exists. |
| `spec-decomposition-subsection-order` | Reorder to Seams, Briefs, Scope stubs, Coverage. If the content itself was written out of order, re-derive: enumerate the units, apply the seam's predicate, assign, then write the stubs. |
| `spec-brief-uncovered` | Either the brief claims a unit nobody wrote down — add its Coverage rows — or it claims nothing and should be folded into its neighbour. A conformance brief claims the invariants whose falsifier ranges over more than one brief, so it belongs in the Brief column of those rows. |
| `spec-stub-missing` (whole section) | The Scope stubs subsection holds no block the parser recognizes. Each brief gets one headed by its backticked slug — a `**`slug`**` lead-in or an H4 — carrying outcomes owed, exclusions inherited, and spec units claimed. |
| `spec-conformance-sink-not-sink` | Whatever depends on the conformance brief is doing delivery work; move that work into a delivering brief, or the sink is really an Instrument. |
| `spec-foundation-brief-orphaned` | Fold it into the brief that consumes it, or the label is wrong and it is really Content. |
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

The decomposition layers add three more, and they hold at both of them:

9. **Every seam carries a predicate** — a split line decides, for a rule not yet written, which side it lands on. One per neighbour, no more and no fewer.
10. **Coverage is falsifiable** — every named unit resolves to a claiming artifact or a named exclusion, in both directions, so an omission is a row nobody wrote rather than a silence nobody notices.
11. **Truth and state stay separated** — a decomposition section states what is permanently true about a boundary. Nothing in it changes the day a downstream unit ships; that belongs in the state sidecar.

File-level ownership uniqueness across chunks is the chunk-plan author's responsibility, not the engineering plan's. The author of chunk N's plan reads chunks 1..N-1's plans to see what's already been written; if a path collision arises, it's resolved at that moment with full repo context, not pre-litigated at engineering-plan time on speculative filenames.

## Why this skill exists

The review skills catch structural problems *after* an artifact is written. By then the author has already committed to a decomposition; "fixes" mean re-cutting. That's exactly the kind of churn the review skills were designed to prevent on the review side — applying the same discipline on the writing side closes the loop. It is the same argument at every layer: a seam re-cut after four briefs descend from it costs what a chunk re-cut costs, one level up.

`/plan-lint` is deterministic. It cannot make a wrong judgment call because it makes no judgment calls. The rules are conservative — they will let a bad artifact through (judgment was needed) before they reject a good one (structure was fine). That's why `/plan-lint` is the floor, and the review skills are the ceiling.

See `~/.claude/skills/_decompose-common/decomposition-principles.md` for the split-line and coverage machinery the two decomposition types enforce, `~/.claude/skills/_vision-common/vision-format.md` and `~/.claude/skills/_spec-common/spec-format.md` for the canonical shapes, `personas/ai-development.md` § "Factoring Contract" for the rationale per chunk field, and `features/_template/chunk.md` + `features/_template/engineering-plan.md` for the plan-layer templates.
