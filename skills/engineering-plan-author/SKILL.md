---
name: engineering-plan-author
description: Authoring-side sister to `/engineering-plan-review-v2`. Produces or rewrites a feature's `engineering-plan.md` (the chunk-DAG layer between the brief and per-chunk implementation plans) with deterministic structural lint, ground-truth verification, and self-prosecution applied at write time. The Plan-lint and Concern-lint gates catch DAG cycles, and-chunks, vague exit criteria, premature abstractions, position-encoded slugs, and self-disclosed bundling; the ai-development persona's halved-work test catches semantic concern violations. Includes an Imagined-Implementer dry-run that surfaces undecided cross-chunk decisions as IMPLEMENTABILITY_GAP. Persists a sidecar at `~/.claude/cache/author-state/<feature>__engineering-plan.json`. On HIGH+ residuals the partial draft is written to disk with frontmatter `Status: needs-user-input` plus a `## Pending blockers` section; the user resolves and re-invokes with the partial draft as warm-mode anchor. Surfaces blockers as OPEN_QUESTION / IMPLEMENTABILITY_GAP / CONCERN_GATE_FAILED. Sister to `/brief-author` (brief layer) and `/plan-author` (chunk-plan layer).
---

# Engineering plan author

Produces or rewrites `features/<feature>/engineering-plan.md`. Pre-empts the failure modes `/engineering-plan-review-v2` keeps surfacing — chunk overscoping, brief drift, decision-closure gaps, false parallelism, position-encoded slugs.

The engineering plan is the contract between the brief (what we're shipping) and the chunk plans (how each piece is built). Every defect at this layer multiplies: a 4-concern chunk row produces a 4-concern chunk plan; a missing decision-closure entry means every chunk plan re-prosecutes the same cross-chunk wiring; a brief Goal not mapped to a chunk means the feature ships incomplete.

## Inputs

- `$ARGUMENTS` (optional):
  - `<feature>` — the feature directory under `features/`. Required if not inferable from cwd.
  - `--draft` — quick-exploration mode; skip Plan-lint, Concern-lint, Ground-truth audit, and Self-prosecution.
  - `--rewrite` — assume `features/<feature>/engineering-plan.md` exists; warm-mode carry-forward applies.

## Sidecar location

`~/.claude/cache/author-state/<feature>__engineering-plan.json`.

The reviewer skill `/engineering-plan-review-v2` consults this sidecar to skip re-prosecuting claims the author already verified, and to read `introduced_identifiers` (cross-chunk contracts the engineering plan introduces — type names, table names, flag names, enum values, file paths of shared modules; chunk-internal identifiers do NOT belong in the engineering plan per `P-EP-IMPL-DETAIL`).

---

## Workflow

```
State load (deterministic; ~5 seconds)
  ├─ mkdir -p ~/.claude/cache/author-state (Write does NOT auto-create parents;
  │   the reviewer-side machinery only creates ~/.claude/cache/review-state)
  ├─ Read author sidecar at ~/.claude/cache/author-state/<feature>__engineering-plan.json
  ├─ Read review state at ~/.claude/cache/review-state/<feature>__engineering-plan.json (warm carry-forward)
  ├─ Read brief author sidecar at ~/.claude/cache/author-state/<feature>__brief.json (upstream context)
  └─ Determine cold vs warm mode

Source ingest (deterministic; ~60 seconds)
  ├─ Read brief.md (HARD-blocking — engineering plan without brief is fan fiction)
  ├─ Read decisions.md (every dated entry, especially cross-chunk wiring)
  ├─ Read existing engineering-plan.md (warm/rewrite modes)
  ├─ Read CLAUDE.md, MEMORY.md, project memory files, schema.prisma, operations.graphql
  ├─ Read sibling engineering plans (features/*/engineering-plan.md) for shape/tone consistency
  └─ Build invariants ledger and identifier ledger

Draft (LLM judgment; main thread)
  ├─ Mirror section template: Brief mapping → Architecture summary → Decisions closure
  │     → Invariants → Field Precedence → Cost & Capacity → Operator-facing budgets
  │     → Chunk index → Manual gates → Dependency graph
  ├─ Each chunk row in the chunk index = ONE concern (refuse 'N-concern' / 'bundle' framings)
  ├─ Every Goal in the brief maps to ≥1 chunk in Brief Mapping (or to Supporting infrastructure)
  ├─ Decisions-closure table covers every cross-chunk wiring decision
  └─ Emit first draft to in-memory buffer (NOT yet written to disk)

Plan-lint gate (deterministic, HARD-blocking)
  ├─ Write the in-memory draft to /tmp/<feature>__engineering-plan-draft-<timestamp>.md
  ├─ Bash: `python3 ~/.claude/skills/plan-lint/lint.py /tmp/<feature>__engineering-plan-draft-<timestamp>.md`
  │   (the Skill tool form `Skill(skill="plan-lint", args=...)` is also valid;
  │   the python script is the canonical underlying invocation, faster and
  │   easier to capture in the sidecar's plan_lint_log)
  ├─ Capture stdout + exit code into sidecar.plan_lint_log
  ├─ Exit 0: continue to Concern-lint gate
  ├─ Exit 1: apply local fixes (re-draft prose, do not change DAG); re-run lint up to 2x.
  │   If still failing after 2 retries, surface STRUCTURAL_LINT_FAILED blocker.
  ├─ Exit 2: usage/IO error — re-check temp-file path; re-emit
  └─ Delete the temp file regardless of outcome

Concern-lint gate (deterministic, HARD-blocking unless carry-forward applies)
  ├─ For each row in the in-memory draft's chunk index, apply ONE structural check
  │   against the description (mirrors the chunk-plan author's Concern gate):
  │     - Self-disclosure pattern: /\b\d+-concern\b|\bN-concern\b|\bbundle\b|\bbundling\b/i
  ├─ For each row that matches, consult carry-forward (see "Concern-lint carry-forward
  │   consultation" below) BEFORE refusing. If carry-forward applies, tag the row's
  │   lint outcome `carried_forward` and proceed.
  ├─ Rows that match AND have no applicable carry-forward → HARD-blocking. Catching
  │   self-disclosed bundling at the engineering-plan layer prevents the cascade into
  │   a multi-concern chunk plan that plan-author's own Concern gate would refuse anyway.
  ├─ On unsalvageable failure: surface CONCERN_GATE_FAILED with the offending row(s);
  │   decompose the chunk into one-concern siblings, OR (when the bundle is intentional
  │   and decided) record an explicit bundle arbitration in `## Decisions closure`
  │   citing the durable decision so future invocations carry forward deterministically.
  ├─ Other syntactic patterns (` AND ` conjunctions, comma lists, plus-separators,
  │   multi-clause descriptions) are NOT refusal triggers at this gate — they fire
  │   false-positives on legitimate prose. Concern judgment for these cases is
  │   semantic, performed by the ai-development persona's halved-work test in
  │   Self-prosecution against each chunk row.
  └─ On clean pass (no self-disclosure matches, or all matches resolved by
      carry-forward): proceed to Ground-truth audit.

Ground-truth audit (`_author-common/ground-truth-protocol.md`)
  ├─ Tokenize draft for V1-V5 claims
  ├─ V2 (identifiers): cross-chunk contract names — verify each is either (a) introduced by THIS plan
  │   (added to introduced_identifiers) or (b) verified to exist in the repo
  ├─ V4 (cross-document): every brief-Goal quote, every decisions.md citation, every CLAUDE.md rule
  ├─ V3 (constraint): chunk dependencies (claim "X depends on Y" verified against the dependency graph)
  └─ Write sidecar audit log

Self-prosecution and imagined-implementer (`_author-common/self-prosecution-protocol.md`)
  ├─ Spawn architecture, ai-development, product, backend, testing in parallel
  ├─ Each runs the premise-interrogation sub-pass + the standard-prosecution sub-pass
  ├─ THEN run Imagined-Implementer dry-run (author-side; engineering-plan layer only):
  │     - Pick the first chunk in the dependency graph that has no upstream dependency
  │     - Attempt to author its chunk plan in a single thought-experiment pass (not actually written)
  │     - Surface every cross-chunk wiring decision the imagined-implementer cannot bind
  │     - File these as IMPLEMENTABILITY_GAP — same blocker class the reviewer uses
  ├─ Consolidate findings; apply auto-fixable
  ├─ Run post-fix premise verification on orchestrator-rewritten prose
  ├─ Classify residuals (STABLE_DISAGREEMENT, OPEN_QUESTION, FIX_INTRODUCED_PREMISE_INVERSION,
  │   IMPLEMENTABILITY_GAP, BRIEF_AMENDMENT_NEEDED, UNCORROBORATED_RESET)
  └─ Decide emission via three-state verdict:
      ├─ CLOSED: write engineering plan with NO `Status:` frontmatter + persist + verdict (per-chunk authoring is unblocked)
      ├─ APPROVED: write engineering plan with NO `Status:` frontmatter + persist + verdict (shape-correct, but cross-chunk
      │           decisions still undecided — do NOT yet author per-chunk plans; IMPLEMENTABILITY_GAPs in the body)
      └─ NEEDS_USER_INPUT: write partial draft with `Status: needs-user-input` and inline `## Pending blockers`
                          + persist + render verdict
```

In `--draft` mode the Plan-lint, Concern-lint, Ground-truth, and Self-prosecution stages are all skipped; the draft is emitted directly with `verdict: "DRAFT_EMITTED"` per the rule under Edge cases.

---

## State load

Read the author sidecar. Schema (extends the brief-author sidecar with engineering-plan-specific fields):

```json
{
  "feature": "<feature>",
  "artifact_path": "features/<feature>/engineering-plan.md",
  "authoring_mode": "ship | draft",
  "ground_truth_at": "<ISO 8601 UTC>",
  "self_prosecution_at": "<ISO 8601 UTC>",
  "imagined_implementer_at": "<ISO 8601 UTC>",
  "invocation_number": <int>,
  "last_engineering_plan_sha256": "<hex>",
  "claims_total": <int>,
  "claims_verified": <int>,
  "claims_verified_softened": <int>,
  "claims_corrected": <int>,
  "claims_dropped": <int>,
  "claims_restructured": <int>,
  "claims_skipped_carveout": <int>,
  "introduced_identifiers": ["<cross-chunk contract name>", ...],
  "chunk_count": <int>,
  "chunk_dag": [{"slug": "...", "depends_on": [...]}, ...],
  "ground_truth_log": [...],
  "self_prosecution_findings": [...],
  "imagined_implementer_findings": [...],
  "authoring_residual": [...],
  "prior_blockers": [
    {
      "blocker_class": "<class>",
      "path_or_section": "<verbatim>",
      "summary": "<verbatim>",
      "raised_in_round": <int>,
      "current_reclassification_justification": "<optional>"
    }
  ],
  "recently_resolved_blockers": [
    {
      "blocker_class_when_resolved": "<class>",
      "path_or_section": "<verbatim>",
      "summary": "<verbatim>",
      "resolved_in_round": <int>,
      "user_decision": "<verbatim>",
      "carry_forward_until_round": <int>
    }
  ],
  "plan_lint_log": "<verbatim stdout from python3 ~/.claude/skills/plan-lint/lint.py>",
  "concern_lint_status": "passed | failed | carried_forward",
  "concern_lint_offending_rows": ["<chunk-index row description>", ...],
  "concern_lint_carry_forward_log": [
    {
      "row_description": "<verbatim chunk-index row description>",
      "matched_pattern": "self_disclosure",
      "source": "review_state | author_state | decisions_closure",
      "source_path": "<verbatim path or `## Decisions closure` row>",
      "source_blocker_id": "<id or null when source is decisions_closure>",
      "carry_forward_until_round": <int>,
      "user_decision": "<verbatim>"
    }
  ],
  "verdict": "CLOSED | APPROVED | NEEDS_USER_INPUT | DRAFT_EMITTED"
}
```

`prior_blockers` / `recently_resolved_blockers` mirror the reviewer state schema in `~/.claude/cache/review-state/` so `/explain-blockers` parses both with one parser. Verdict semantics differ from brief-author / plan-author: `APPROVED` means shape-correct AND one or more `IMPLEMENTABILITY_GAP` entries remain in `prior_blockers`; `CLOSED` means `prior_blockers` is empty AND every cross-chunk decision is bound. `DRAFT_EMITTED` is set when authoring_mode is `--draft` (Plan-lint, Concern-lint, Ground-truth audit, and Self-prosecution skipped); the engineering plan IS written to disk in this mode with NO `Status:` frontmatter, and the sidecar's `authoring_mode: "draft"` carries the load-bearing draft signal that downstream skills consult. `NEEDS_USER_INPUT` is set when one or more HIGH+ blockers remain (other than IMPLEMENTABILITY_GAP, which lands at APPROVED); the partially-improved engineering plan IS written to disk with frontmatter `Status: needs-user-input` AND an inline `## Pending blockers` section listing each unresolved finding verbatim — the next `--rewrite` invocation reads the partial draft as warm-mode source-of-truth and only re-emits sections affected by the user's blocker resolutions. Only HIGH+ findings land in `prior_blockers`; LOW findings under the polish floor stay in `authoring_residual`.

Also read the review-state at `~/.claude/cache/review-state/<feature>__engineering-plan.json`. Its `recently_resolved_blockers` list constrains the new draft (warm-mode carry-forward at the engineering-plan layer): re-introducing a chunk the user removed, or re-prosecuting a decision the user closed, is `FIX_INTRODUCED_PREMISE_INVERSION`.

Also read the brief-author sidecar `~/.claude/cache/author-state/<feature>__brief.json` if present. Its `introduced_identifiers` list (rare at the brief layer) and `authoring_residual` items inform the engineering-plan draft.

---

## Source ingest

Hard requirements — skill refuses to run without:
- `features/<feature>/brief.md` exists (brief is the bridge to the engineering plan).

Read in this order:

1. `features/<feature>/brief.md` — every Goal and Non-goal goes into the invariants ledger as constraints the chunk DAG must honor.
2. `features/<feature>/decisions.md` — every dated entry. Cross-chunk wiring decisions go into the decisions-closure table.
3. `features/<feature>/engineering-plan.md` (warm/rewrite mode) — current chunk DAG. This includes a prior `Status: needs-user-input` partial draft from a previous invocation: the partial draft is the canonical anchor, NOT the pre-rewrite version. The Draft stage starts from the partial-draft body (auto-fixes already applied to its prose) and only re-emits sections affected by the user's blocker-resolutions; unaffected sections stay byte-stable.
4. `CLAUDE.md` — banned patterns, business rules, schema-first / operations-first / multi-category architecture rules.
5. `MEMORY.md` + project memory.
6. `backend/prisma/schema.prisma` — current schema; the engineering plan's schema-additions section must declare every new field/table/enum AND verify no naming collisions with existing fields.
7. `mobile/src/graphql/operations.graphql` — current operations; user-facing changes naming GraphQL operations must verify the operation either exists or is an introduced_identifier.
8. Sibling engineering plans (`features/*/engineering-plan.md`) — for shape/tone consistency. Pay attention to: section ordering, decisions-closure column shape, chunk-index column shape, dependency-graph rendering style.

After reading, build:
- **Invariants ledger** — every brief Goal, every Non-goal, every project-memory-bound rule. Format as bullet list with verification source.
- **Identifier ledger** — every existing schema field, every existing GraphQL operation, every existing class/type/file path the brief or decisions.md mentions. The chunk DAG cross-references these.
- **Decisions ledger** — every dated entry from `decisions.md`, indexed by (date, key). The decisions-closure table will cite these.

---

## Draft

Mirror this section template (matches the shape of existing engineering plans):

```markdown
# <Feature Name> — Engineering Plan

**Brief:** [`./brief.md`](./brief.md)
<!-- Status frontmatter is OPTIONAL and binary. Set to `needs-user-input` ONLY when the engineering plan is mid-cycle (auto-managed by /engineering-plan-author NEEDS_USER_INPUT path). Otherwise omit entirely. Lifecycle states (Frozen, Archived) are derived from git state, not frontmatter. -->
<!-- Status: needs-user-input -->  <!-- only when mid-cycle -->

**Created:** <YYYY-MM-DD>
**Last updated:** <YYYY-MM-DD>

## Brief mapping

### Goals
| Goal | Chunks |
|---|---|
| <Goal verbatim> | <chunk-slug-1>, <chunk-slug-2>, ... |

### User-facing changes
| Change | Verified by |
|---|---|
| <change> | <chunk-slug or "Manual review"> |

### Supporting infrastructure
- **<chunk-slug>** — <one-line description, ONE CONCERN ONLY>

### Non-goals enforcement
| Non-goal | Enforcement |
|---|---|
| <non-goal> | <which chunk's plan body bounds it / "no chunk; out of scope by absence"> |

## Architecture summary

<Two or three paragraphs describing the system shape. Names cross-chunk contracts only — type names, table names, file paths of shared modules. NO chunk-internal detail. Wave structure (which chunks ship in parallel) lives in the dependency graph, not here.>

## Decisions closure

| Decision | Status | Citation |
|---|---|---|
| <decision> | bound \| open \| deferred-to-X | <decisions.md date entry or chunk slug> |

## Invariants

### <Invariant Name>
<One paragraph stating the invariant. Names which chunks enforce it.>

## Field Precedence on Linked Persons (or feature-specific equivalent)

<Table of cross-source data conflicts and resolution rules.>

## Cost & Capacity

<API quotas, rate limits, expected throughput.>

## Operator-facing budgets

<Manual-gate budgets, runtime budgets, expected operator effort.>

## Chunk index

| Slug | Description | Depends on |
|---|---|---|
| `<chunk-slug>` | <one concern, no AND, no bundle> | `<chunk-slug-or-empty>` |

## Manual gates

<Operator runbook entries — pre-apply snapshots, post-run audits, etc.>

## Dependency graph

```
<ASCII or mermaid showing wave structure>
```
```

### Drafting rules — anti-thrash discipline

- **One concern per chunk row.** Only self-disclosure (`\bN-concern\b`, `\bbundle\b`, `\bbundling\b`) auto-refuses at the deterministic Concern-lint gate. Conjunctions, comma lists, plus-separators, and multi-clause descriptions are NOT auto-refusal triggers — they fire false-positives on legitimate prose ("extract helper used in 12 sites and migrate callsites" is one concern; "add fieldA, fieldB, fieldC to User model" is one schema change). Concern judgment for these is semantic: the ai-development persona applies the halved-work test to each chunk row in Self-prosecution. Mutual load-bearing is shipping-order, not bundling.
- **Every brief Goal maps to ≥1 chunk.** No orphan Goals. Cross-cutting infrastructure (rate limiters, error helpers, observability) maps to `### Supporting infrastructure` not a brief Goal (per `P-EP-BRIEF-GOALS`).
- **No chunk-internal identifiers in the engineering plan.** Test names, single-file function names, internal phase splits, files-to-create lists, exact log strings, SQL queries, regex patterns — all chunk-internal. Per `P-EP-IMPL-DETAIL`, the engineering plan names cross-chunk contracts only.
- **Every cross-chunk decision is in Decisions-closure.** Status ∈ {bound, open, deferred-to-<chunk>}. `bound` means the decision is fully resolved; `open` means it needs user arbitration before the chunk plan can be authored; `deferred-to-<chunk>` means the listed chunk owns the decision.
- **No position-encoded slugs.** Slugs are semantic (`orphan-cleanup-hardening`), not positional (`wave-2-task-3`). Per `/plan-lint` and `_review-common/critical-pairs.md`.
- **No false parallelism.** A chunk in Wave N must have all dependencies in Waves <N. The dependency graph is the source of truth; the wave numbering descends from it, not the other way around.
- **Verified-by cells name chunk slugs.** Per `P-EP-VERIFIED-BY`. Never test files or test cases directly.
- **Risk depth is bounded.** Per `P-EP-RISK-DEPTH`. Name risks, mitigations, rollback. Don't enumerate every possible failure mode.
- **Drafted prose must not contradict bound decisions.** Before emitting the in-memory draft to Plan-lint, scan every section (Brief mapping, Architecture summary, Decisions closure, Invariants, Field Precedence, Cost & Capacity, Operator-facing budgets, Chunk index descriptions, Manual gates, Dependency graph, Risks/unknowns, Rollout plan, Out of scope) for prose that contradicts an entry in `features/<feature>/decisions.md` whose `Status:` is `bound`. The engineering plan is the source of `decisions.md` for cross-chunk wiring, but earlier-round bound entries are durable — a Round-3 chunk DAG cannot drop a column the Round-2 decisions.md committed to (without the user explicitly amending the decision). When a contradiction is found, prefer rewriting the draft to match the bound decision; if the contradiction is itself a discovery (the bound decision is wrong given new repo state or new brief Goals), surface as `OPEN_QUESTION` with the bound entry quoted verbatim — the user re-arbitrates rather than the orchestrator silently overriding. The Self-prosecution carry-forward auto-retract handles findings the personas raise that contradict bound decisions, but that is reactive — this rule is the proactive write-side pair.

---

## Plan-lint gate

Write the in-memory draft to `/tmp/<feature>__engineering-plan-draft-<timestamp>.md`, then invoke the lint script directly via Bash:

```bash
python3 ~/.claude/skills/plan-lint/lint.py /tmp/<feature>__engineering-plan-draft-<timestamp>.md
```

The Skill-tool form `Skill(skill="plan-lint", args="/tmp/...md")` is also valid; the Bash form is the canonical one because it surfaces stdout + exit code directly for capture into `sidecar.plan_lint_log`. Exit codes: `0` = clean, `1` = FAIL, `2` = usage/IO error.

If lint fails (exit 1):
- Read the failure list. For each defect, identify whether the fix is local (rewrite a line) or structural (remove a chunk, reorder dependency).
- Apply local fixes to the in-memory draft, re-run lint. Repeat up to 2x.
- If structural fixes are needed, refuse to emit; surface as `STRUCTURAL_LINT_FAILED` blocker requiring user arbitration.

If lint errors (exit 2): re-check the temp-file path and content; if the issue persists, treat as a `STRUCTURAL_LINT_FAILED` blocker with the lint stderr verbatim.

Delete the temp file regardless of outcome (no leftover drafts in `/tmp`).

The Plan-lint gate is HARD-blocking. A draft that fails plan-lint never reaches the Concern-lint gate.

---

## Concern-lint gate

For each row in the in-memory draft's chunk index, apply ONE deterministic check against the description cell (mirrors the chunk-plan author's Concern gate):

**Self-disclosure** — `/\b\d+-concern\b|\bN-concern\b|\bbundle\b|\bbundling\b/i` matches anywhere in the row description. This is the author actively admitting the row is bundled; no false-positive case exists.

On a match, run the carry-forward consultation below BEFORE refusing. If carry-forward applies for that row, mark its lint outcome `carried_forward` (per the sidecar's `concern_lint_status` and `concern_lint_carry_forward_log`) and proceed.

If a row matches AND has no applicable carry-forward, the gate is HARD-blocking for that draft. Surface a `CONCERN_GATE_FAILED` blocker naming the offending row(s); the user either decomposes into one-concern siblings (which forces an aligned update of the chunk index, dependency graph, brief-mapping table, and decisions-closure entries — partial fixes are not allowed) or records an explicit `## Decisions closure` row arbitrating the bundle, citing a `decisions.md` entry with `bound` status, so the next invocation carry-forwards deterministically.

### Patterns NOT enforced by this gate

The earlier version enforced four additional syntactic patterns as auto-refuse triggers: ` AND ` conjunctions, three+ comma-separated noun phrases, `+ <noun> + <noun>` separators, and ≥2 independent clauses. They were dropped. Each had high false-positive rates on legitimate prose:

- "Extract helper used in 12 sites and migrate callsites" is one concern (the migration is incomplete without the extraction).
- "Add fieldA, fieldB, fieldC to the User model" is one schema change with three named columns.
- "Schema migration: drop column X; backfill column Y; add index Z" describes one mechanical change with three named ripples.

Concern judgment for these cases is semantic, not syntactic. The ai-development persona evaluates every chunk-index row in Self-prosecution with the **halved-work test**: "if you halved the work this chunk row implies, would the other half still be a coherent shippable thing?" If yes → multi-concern, surface a finding. If no → one concern, proceed. The persona runs on every chunk row regardless of pattern matches; explicit syntactic detection is not needed because the persona reads the actual draft and judges semantically.

### Concern-lint carry-forward consultation

Run this only on a refusal-pattern match. It produces a deterministic decision: carry-forward applies, or it doesn't. Three sources are checked, in order; the first match wins.

1. **Engineering-plan reviewer state.** Read `~/.claude/cache/review-state/<feature>__engineering-plan.json`. In `recently_resolved_blockers`, find an entry where ALL of:
   - `path_or_section` substring-matches one of: the chunk slug; the chunk-index row's verbatim description; or `chunk-index row N` where N is the row's index position.
   - `blocker_class_when_resolved` is one of `CONCERN_GATE_FAILED`, `CHUNK_BUNDLE`, `MULTI_CONCERN`, `CONCERN_FACTORING` — OR the entry's `summary` field contains both a concern-family keyword (`bundle`, `concern`, `factoring`) and a resolution-direction keyword (`accept`, `bound`, `keep`, `retain`, `reaffirm`).
   - `carry_forward_until_round >= current_invocation_number` (cross-side number-line mapping per `_author-common/self-prosecution-protocol.md`).

2. **Engineering-plan-author state.** Read this skill's own sidecar `~/.claude/cache/author-state/<feature>__engineering-plan.json`. Apply the same three-condition match against ITS `recently_resolved_blockers`.

3. **Engineering-plan decisions-closure scan.** Read the in-memory draft's `## Decisions closure` section. A row carries forward when ALL of:
   - The `Decision` column substring-matches the chunk slug or the row's verbatim description.
   - The `Resolution` column starts with `bound` (case-insensitive).
   - The `Resolution` column contains a concern-family keyword (`bundle`, `multi-concern`, `mutually load-bearing`, `transactional invariant`, `theme-unified`).

If any source matches, set `concern_lint_status: "carried_forward"` for the row, append a `concern_lint_carry_forward_log` entry naming the source, blocker id (when applicable), `carry_forward_until_round`, and the user's decision verbatim. Proceed past the gate.

If no source matches, refuse with `CONCERN_GATE_FAILED`. The verdict surfaces the three actionable resolutions: rewrite the chunk-index row description to single-concern phrasing citing the decision (preferred); add an explicit `## Decisions closure` row arbitrating the bundle; or re-run `/engineering-plan-review-v2` to record the arbitration in the reviewer state's `recently_resolved_blockers`.

---

## Ground-truth audit

Apply `_author-common/ground-truth-protocol.md`. At the engineering-plan layer:

- **V2 (identifier) is dominant.** Every cross-chunk contract name (table, type, flag, file path of shared module) is either:
  1. Added to `introduced_identifiers` in the sidecar (the engineering plan introduces this; child chunks build it).
  2. Verified to exist in the repo (`schema.prisma`, `operations.graphql`, source code).
- **V4 (cross-document) is heavy.** Every brief-Goal quote in Brief Mapping is verified verbatim. Every decisions.md citation in Decisions-closure is verified by date + entry text. Every CLAUDE.md / project-memory rule the engineering plan invokes is verified.
- **V3 (constraint) tests the dependency graph.** Each "X depends on Y" claim must be reflected in the chunk-index `Depends on` column AND in the dependency graph.

Carve-out 1 (`introduced_identifiers`) is the dominant carve-out at this layer — engineering plans introduce more cross-chunk contract names than they reference existing ones.

Sidecar audit log includes the full claim-by-claim breakdown.

---

## Self-prosecution and imagined-implementer

### Persona prosecution

Spawn five persona agents in parallel using the template in `_author-common/self-prosecution-protocol.md`:

- **architecture** — system-shape coherence, hidden dependencies, false parallelism, factoring.
- **ai-development** — chunk discipline, plan-quality at engineering-plan layer, DAG cycles, position-encoded slugs.
- **product** — brief drift, Goal mapping, Non-goal enforcement, scope creep.
- **backend** — schema-additions correctness, GraphQL-operation introductions, decisions-closure on backend wiring.
- **testing** — `Verified by` columns, gate-test coverage, chunk-internal-detail leakage in test references.

Active critical pairs: universal pairs + engineering-plan-specific pairs (`P-EP-IMPL-DETAIL`, `P-EP-BRIEF-GOALS`, `P-EP-VERIFIED-BY`, `P-EP-RISK-DEPTH`, `P-EP-DECISION-LOC`).

### Imagined-Implementer dry-run (after personas return)

Author skills mirror the reviewer's `imagined_implementer` pass — but at write time, with stronger consequences (the verdict gate uses it).

Procedure:

1. Pick the first chunk in the chunk index whose `Depends on` is empty (or whose dependencies are all marked `bound` and shipped).
2. Attempt a thought-experiment authoring of its chunk plan WITHOUT actually writing it. The procedure follows what `/plan-author` would do: read the brief, read the engineering plan §relevant chunk, read decisions.md, build a Factoring Contract, fill §Owns / §Contracts / §Acceptance.
3. Surface every cross-chunk wiring decision the imagined-implementer would need to *bind* but the engineering plan leaves *open* or *deferred-without-citation*. Each such decision is filed as `IMPLEMENTABILITY_GAP` with:
   - The decision name.
   - Where the chunk plan would have to bind it.
   - A `severity_test` — a falsifiable scenario where leaving the decision unbound breaks the chunk plan ("if Decision X is open, the chunk's §Owns step 3 cannot be written because it depends on knowing whether Y or Z is the source-of-truth").
4. If no `IMPLEMENTABILITY_GAP` surfaces, the imagined-implementer pass returns `verdict: implementable`. Otherwise `verdict: not_implementable`.

The verdict gate uses this:

- **CLOSED** ⇔ `imagined_implementer.verdict == implementable` AND no other blockers.
- **APPROVED** ⇔ shape-correct AND `imagined_implementer.verdict == not_implementable` (one or more `IMPLEMENTABILITY_GAP`s remain — the engineering plan is fine, but per-chunk authoring is blocked until the user binds the gaps).
- **NEEDS_USER_INPUT** ⇔ anything else.

### Verdict template

```markdown
# Engineering plan authoring verdict — features/<feature>/engineering-plan.md

**Mode:** cold | warm
**Authoring mode:** ship | draft
**Round:** <invocation_number>
**Last engineering-plan sha:** <hex>

## Plan-lint
**Status:** PASS | FAIL
**Defects:** <N>; if FAIL, list each.

## Concern-lint
**Status:** PASS | FAIL | CARRIED_FORWARD
**Offending rows (if FAIL):** <quoted descriptions>
**Carried-forward rows (if CARRIED_FORWARD):** <row description> ← <source: review_state | author_state | decisions_closure> entry <id-or-citation> until round <N>

## Ground-truth audit
**Claims total:** <N>
**Verified:** <V>  **Softened:** <S>  **Corrected:** <C>  **Dropped:** <D>  **Restructured:** <R>  **Skipped (carve-out):** <K>
**Introduced identifiers:** <count> (<comma-separated list, truncated>)

## Self-prosecution
**Personas:** architecture, ai-development, product, backend, testing
**Premise interrogation:** <per-persona pass/fail>
**Standard findings:** <N total>; <by tier+severity>
**Post-fix premise verification:** <P claims rewritten; Q falsified> → <FIX_INTRODUCED_PREMISE_INVERSION count>
**Carry-forward consultation:** <skipped because cold | M recently-resolved blockers cross-checked, R re-prosecutions auto-retracted>

## Imagined-Implementer dry-run
**Chunk attempted:** `<slug>`
**Verdict:** implementable | not_implementable
**Implementability gaps:** <N> (each with decision name + severity_test)

## Verdict
**CLOSED** | **APPROVED** | **NEEDS_USER_INPUT** | **DRAFT_EMITTED**

### Blockers (if NEEDS_USER_INPUT)
- [STABLE_DISAGREEMENT] <span> — <one-line>
- [OPEN_QUESTION] <span> — <one-line>
- [FIX_INTRODUCED_PREMISE_INVERSION] <span> — <one-line>
- [STRUCTURAL_LINT_FAILED] <plan-lint defect> — <one-line>
- [CONCERN_GATE_FAILED] <chunk-index row> — <one-line; decomposition required>
- [BRIEF_AMENDMENT_NEEDED] <gap> — <one-line>
- [UNCORROBORATED_RESET] <span> — <one-line>

### Implementability gaps (if APPROVED)
- <decision name>: <severity_test>; <where it must be bound>

### Authoring residuals (LOW, under polish floor)
- ...
```

### Verdict gates

- **CLOSED** ⇔ ALL of:
  - Authoring mode is `ship` (not `--draft`).
  - Plan-lint PASS, Concern-lint PASS or CARRIED_FORWARD, Imagined-Implementer verdict `implementable`.
  - Tier-1 weight = 0; Tier-2 weight ≤ 4 (polish floor).
  - No `BRIEF_AMENDMENT_NEEDED`, `CONCERN_GATE_FAILED`, `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `IMPLEMENTABILITY_GAP`, `UNCORROBORATED_RESET`, `STRUCTURAL_LINT_FAILED`, `FIX_INTRODUCED_PREMISE_INVERSION`, `REPO_STATE_DRIFT`.

- **APPROVED** ⇔ shape-correct (Plan-lint PASS, Concern-lint PASS or CARRIED_FORWARD, no other blockers above) AND `imagined_implementer.verdict == not_implementable` AND one or more `IMPLEMENTABILITY_GAP` findings remain. Per-chunk plan authoring is **NOT** unblocked at APPROVED; the user must bind the gaps via `decisions.md` and re-invoke before authoring chunks.

- **NEEDS_USER_INPUT** ⇔ authoring mode is `ship` AND any blocker class above (other than IMPLEMENTABILITY_GAP) fires. Concern-lint failures with no applicable carry-forward fall here as `CONCERN_GATE_FAILED`.

- **DRAFT_EMITTED** ⇔ authoring mode is `--draft` (Plan-lint, Concern-lint, Ground-truth audit, and Self-prosecution skipped). Disk write proceeds with NO `Status:` frontmatter; the sidecar records `authoring_mode: "draft"` as the load-bearing draft signal. Per-chunk plan authoring is gated on the engineering plan being CLOSED, so a DRAFT_EMITTED engineering plan does NOT unblock `/plan-author` — re-invoke without `--draft` to harden first.

### Pending-blockers section (NEEDS_USER_INPUT mode)

On NEEDS_USER_INPUT, the on-disk engineering plan gets two additions beyond the partial draft body:

1. **Frontmatter `Status: needs-user-input`** is added (or replaces a prior Status value if any). The CLOSED/APPROVED-emission convention is no `Status:` field; the NEEDS_USER_INPUT path adds the field as the only valid Status value.
2. **`## Pending blockers` section appended at the end of the file**, with verbatim bullets from the verdict's `### Blockers` block:

   ```markdown
   ## Pending blockers

   <!-- This section is auto-managed by /engineering-plan-author. Resolve each blocker below, then re-invoke `/engineering-plan-author --rewrite <feature>`. The next Draft stage reads this file as warm-mode source-of-truth and only re-emits sections affected by your resolutions; the unaffected sections stay byte-stable. Per-chunk plan authoring (`/plan-author`) is also gated on this status and refuses to run until the engineering plan lands at CLOSED. -->

   - [<BLOCKER_CLASS>] <span / section> — <one-line summary>; <actionable resolution path>.
   - ...
   ```

On the subsequent `--rewrite` invocation that lands at CLOSED or APPROVED, the entire `## Pending blockers` section AND its HTML comment are removed, AND the `Status: needs-user-input` line is removed (the CLOSED/APPROVED emission convention is no `Status:` field). If the next invocation is still NEEDS_USER_INPUT, the `## Pending blockers` section is rewritten with the new blocker set (replaced, not appended to — stale blockers don't accumulate); the `Status: needs-user-input` line stays. IMPLEMENTABILITY_GAP findings, which gate CLOSED but not APPROVED, do NOT appear in `## Pending blockers` — they live in the engineering-plan body's Decisions-closure table where they belong.

---

## Hard rules

- **Stage order is fixed.** Source ingest before Draft. Plan-lint before Concern-lint. Concern-lint before Ground-truth audit. Ground-truth audit before Self-prosecution and imagined-implementer. All before emission. `--draft` skips Plan-lint, Concern-lint, Ground-truth audit, and Self-prosecution.
- **Brief is HARD-blocking.** No brief.md → skill refuses to run.
- **Plan-lint is HARD-blocking.** Failures must be fixed in-loop or surfaced as `STRUCTURAL_LINT_FAILED`; the draft cannot reach Concern-lint with structural defects.
- **Concern-lint is HARD-blocking unless carry-forward applies.** Triggered only by self-disclosed bundling in chunk-index row descriptions (`\bN-concern\b`, `\bbundle\b`, `\bbundling\b`). The draft cannot reach Ground-truth audit with unsalvaged self-disclosed bundled rows. Catching at this layer prevents the cascade into multi-concern chunk plans. Other concern judgments (genuine bundling that the row description doesn't self-disclose) are handled semantically by the ai-development persona's halved-work test in Self-prosecution, NOT by this gate.
- **Imagined-Implementer is mandatory in `ship` mode.** It is the load-bearing gate between APPROVED and CLOSED.
- **Disk-write semantics by verdict:** CLOSED and APPROVED write the engineering plan with NO `Status:` frontmatter (the binary-Status convention reserves `Status:` for the mid-cycle signal only); NEEDS_USER_INPUT writes the partially-improved in-memory draft with frontmatter `Status: needs-user-input` AND an inline `## Pending blockers` section listing each unresolved finding verbatim from the verdict (the user fixes the blockers and re-invokes; the partially-improved draft becomes the warm-mode source-of-truth so re-generation cost is paid once, not on every iteration); DRAFT_EMITTED writes with NO `Status:` frontmatter; the sidecar's `authoring_mode: "draft"` is the load-bearing draft signal that downstream skills consult. Sidecar persists in all cases. The reviewer skill `/engineering-plan-review-v2` refuses to run against `Status: needs-user-input` artifacts — the partial draft is mid-cycle by design and not yet a candidate for prosecution.
- **Sidecar always written.** Every invocation, every verdict.
- **Chunk-internal detail prohibition.** A draft that names test files, exact regex patterns, single-file function names in the engineering-plan body (outside of the sidecar's `introduced_identifiers` for cross-chunk contracts) is rejected by the architecture+ai-development persona prosecution.
- **Decisions-closure completeness.** Every cross-chunk wiring decision the chunks reference must appear in the decisions-closure table. A reference without a closure entry is `IMPLEMENTABILITY_GAP`.
- **No banned content.** Same prohibited categories as `/brief-author` (addendum, review attribution, historical comparison, persona-attribution headers).
- **Carry-forward respect.** Re-introducing a chunk the user removed in a prior invocation, or re-opening a decision the user closed, is `FIX_INTRODUCED_PREMISE_INVERSION`.
- **Drafted prose must not contradict bound `decisions.md` entries.** Before emitting the in-memory draft to Plan-lint, scan every section (Brief mapping, Architecture summary, Decisions closure, Invariants, Field Precedence, Cost & Capacity, Operator-facing budgets, Chunk-index descriptions, Manual gates, Dependency graph, Risks/unknowns, Rollout plan, Out of scope) for prose contradicting any `Status: bound` entry in `features/<feature>/decisions.md`. Earlier-round bound entries are durable — a later-round chunk DAG cannot drop a column the prior round's `decisions.md` committed to without explicit user re-arbitration. Contradictions are HARD-blocking unless surfaced as `OPEN_QUESTION` (the bound decision may itself be wrong given new repo state or new brief Goals, but that is a re-arbitration, not a silent override). The verdict template's `Ground-truth audit` block records `bound_decisions_consulted: <count>; contradictions_found: <count>` so missing this step is visible. The Self-prosecution carry-forward Priority 1 auto-retract handles persona findings reactively; this rule is the proactive write-side pair.

---

## Edge cases

**Sidecar absent, engineering-plan.md absent (cold start):** State load returns empty; Source ingest reads brief + decisions only; Draft writes from scratch. All later stages run normally.

**Sidecar absent, engineering-plan.md present:** Treat current file as warm-mode source; reset ground-truth to fresh; carry-forward unavailable.

**Sidecar present, engineering-plan.md present, SHA matches, no `--rewrite`:** No-op invocation; print "no changes; engineering plan in last-APPROVED/CLOSED state."

**Sidecar present, engineering-plan.md absent (deleted):** Treat as cold disk-state; consult sidecar history for prior arbitrations; surface in verdict that prior plan was deleted.

**Brief amended since last invocation (brief sha changed in brief-author sidecar):** Hard re-author. The chunk DAG may need restructuring to honor new Goals or honor amended Non-goals. Surface every brief-driven structural change in the verdict.

**Plan-lint surfaces a STRUCTURAL_LINT_FAILED that the orchestrator can't auto-fix in two passes:** Block emission; surface to user with the exact `/plan-lint` failure messages quoted.

**Concern-lint refusal pattern matches a row, but the user has arbitrated the bundle elsewhere:** The carry-forward consultation handles this. If a matching `recently_resolved_blockers` entry (in either the engineering-plan reviewer state or this skill's own author state) is in carry-forward window, OR an explicit `## Decisions closure` row is `bound` and contains a concern-family keyword, the row's outcome is `carried_forward`. Otherwise the gate refuses with `CONCERN_GATE_FAILED` and the verdict prose names the three resolution paths (chunk-index rewrite, decisions-closure row, reviewer re-run).

**Imagined-Implementer surfaces gaps but persona prosecution all PASS:** Verdict is APPROVED (shape-correct, decisions undecided). User binds gaps in `decisions.md` and re-invokes; the next pass should land at CLOSED.

**Persona finds an UNCORROBORATED_RESET:** Per `_review-common/blocker-classes.md`, RESET findings need 2-persona corroboration OR 1 persona + verbatim CLAUDE.md / project-memory contradiction. Single-persona uncorroborated resets are reclassified to CRITICAL HARD findings. Surface to user; do not auto-resolve.

**`--draft` mode:** Plan-lint, Concern-lint, Ground-truth audit, and Self-prosecution + Imagined-Implementer are skipped; sidecar marked `authoring_mode: "draft"` and `verdict: "DRAFT_EMITTED"`; engineering-plan written to disk with NO `Status:` frontmatter. The sidecar's `authoring_mode: "draft"` field is the load-bearing draft signal that `/engineering-plan-review-v2` consults. Per-chunk plan authoring (`/plan-author`) is gated on the engineering-plan-author sidecar's verdict being `CLOSED`, so `DRAFT_EMITTED` does NOT unblock `/plan-author` — the user must re-invoke without `--draft` to harden, run Imagined-Implementer, bind any IMPLEMENTABILITY_GAPs in `decisions.md`, and re-invoke a third time to land at CLOSED before chunk authoring.

---

## Relationship to sister skills

- **Upstream: `/brief-author`.** The engineering-plan-author reads the brief and the brief-author sidecar. A brief layer change cascades; warm-mode carry-forward includes the brief-side `recently_resolved_blockers`.
- **Downstream: `/plan-author`.** The engineering-plan-author's CLOSED verdict unblocks per-chunk plan authoring. APPROVED does NOT (per the three-state semantic).
- **Reviewer: `/engineering-plan-review-v2`.** Its `recently_resolved_blockers` are warm-mode constraints here. Author-side findings that match a reviewer-side blocker class share the class (BRIEF_AMENDMENT_NEEDED, IMPLEMENTABILITY_GAP, UNCORROBORATED_RESET, STABLE_DISAGREEMENT, OPEN_QUESTION, FIX_INTRODUCED_PREMISE_INVERSION, STRUCTURAL_LINT_FAILED, REPO_STATE_DRIFT).
