---
name: plan-author
description: Authoring-side sister to `/plan-review-v2`. Produces or rewrites a per-chunk implementation plan at `features/<feature>/implementation/<chunk-slug>.md` (or `.scratch/<name>.md`) with deterministic structural lint, ground-truth verification, and self-prosecution applied at write time, not review time. The Concern gate auto-refuses self-disclosed bundling; the ai-development persona's halved-work test catches the rest semantically. Persists a sidecar at `~/.claude/cache/author-state/<feature>__<chunk-slug>.json`. On HIGH+ residuals or gate failures the partial draft is written to disk with frontmatter `Status: needs-user-input` plus a `## Pending blockers` section; the user resolves and re-invokes with the partial draft as warm-mode anchor so re-generation cost is paid once. Surfaces blockers as CONCERN_GATE_FAILED / STRUCTURAL_LINT_FAILED / OPEN_QUESTION. Sister to `/brief-author` (brief layer) and `/engineering-plan-author` (engineering-plan layer).
---

# Chunk plan author

Produces or rewrites a per-chunk implementation plan. This is the layer where `/plan-review-v2` thrash concentrates: 28 findings in a single round, 5 user decisions and 13 orchestrator batches, 563-line plan files. Front-loading verification and self-prosecution at write time is supposed to land the plan at `/plan-review-v2` with single-digit findings, not five rounds of arbitration.

## Inputs

- `$ARGUMENTS`:
  - `<feature>/<chunk-slug>` — the chunk plan to author. Path resolves to `features/<feature>/implementation/<chunk-slug>.md`. Required (unless free-standing path is given).
  - OR `<absolute-or-relative-path>.md` — for `.scratch/` plans or other locations.
  - `--draft` — quick-exploration mode; skip Plan-lint, Ground-truth audit, and Self-prosecution. The Concern gate STILL runs in `--draft` mode (self-disclosed multi-concern bundling is a fatal scope error).
  - `--rewrite` — file exists; warm-mode carry-forward applies.

## Sidecar location

`~/.claude/cache/author-state/<feature>__<chunk-slug>.json` for chunks under `features/`. Slug derivation: replace the `/` separator in `<feature>/<chunk-slug>` with `__` (e.g., `author-tmdb-hydration/orphan-cleanup-hardening` → `author-tmdb-hydration__orphan-cleanup-hardening.json`).

For free-standing `.scratch/<name>.md` plans, slug is `scratch__<name>` where `<name>` is the path basename without the `.md` extension (e.g., `.scratch/orphan-bug.md` → `scratch__orphan-bug.json`). For other free-standing paths, slug is `scratch__<sanitized-name>` where `<sanitized-name>` replaces path separators with `__` and strips the `.md` extension.

Same derivation rule as `/plan-review-v2`'s state file, by design — both skills read/write the same slug for the same artifact.

The reviewer skill `/plan-review-v2` consults this sidecar to skip re-prosecuting verified claims and to read `introduced_identifiers`.

---

## Workflow

```
State load (deterministic; ~5 seconds)
  ├─ mkdir -p ~/.claude/cache/author-state (Write does NOT auto-create parents;
  │   the reviewer-side machinery only creates ~/.claude/cache/review-state)
  ├─ Read author sidecar at ~/.claude/cache/author-state/<slug>.json
  ├─ Read review state at ~/.claude/cache/review-state/<slug>.json (warm carry-forward)
  ├─ Read engineering-plan-author sidecar at ~/.claude/cache/author-state/<feature>__engineering-plan.json
  │   (must exist — engineering plan must be CLOSED before chunk authoring; see Hard rules)
  ├─ Read engineering-plan reviewer state at ~/.claude/cache/review-state/<feature>__engineering-plan.json
  │   (consulted by the Concern gate's carry-forward consultation if a refusal pattern matches)
  └─ Determine cold vs warm mode

Source ingest (deterministic; ~60 seconds)
  ├─ Read brief.md (HARD-blocking)
  ├─ Read engineering-plan.md (HARD-blocking, AND must be at CLOSED status — author skill refuses
  │   to run if engineering-plan-author sidecar shows last verdict was APPROVED or NEEDS_USER_INPUT)
  ├─ Locate THIS chunk's row in the chunk index; extract description and row index
  ├─ Read decisions.md (every entry; chunk plans cite decisions, never inline rationale)
  ├─ Read existing chunk plan (warm/rewrite mode)
  ├─ Read every file the chunk's "Read first" list cites (the chunk's read-set)
  ├─ Read CLAUDE.md, MEMORY.md, project memory
  ├─ Read schema.prisma, operations.graphql, sibling chunk plans for shape consistency
  └─ Build invariants ledger, identifier ledger, decisions ledger

Concern gate (deterministic — HARD-blocking unless carry-forward applies)
  ├─ Extract chunk description from the engineering-plan chunk index row located in Source ingest
  ├─ Apply ONE structural check against the description:
  │     - Self-disclosure: /\b\d+-concern\b|\bN-concern\b|\bbundle\b|\bbundling\b/i
  ├─ No match → concern_gate_status = "passed"; proceed to Draft. Semantic concern judgment
  │   happens in Self-prosecution (the ai-development persona's halved-work test); the
  │   deterministic gate intentionally does NOT pattern-match conjunctions, comma lists, or
  │   multi-clause descriptions, which fire false-positives on legitimate prose
  │   (e.g., "extract helper used in 12 sites and migrate callsites" is one concern but
  │   contains " and "; "add fieldA, fieldB, fieldC to User model" is one schema change).
  ├─ Match → consult carry-forward (see "Concern-gate carry-forward consultation" below)
  │   BEFORE refusing. If carry-forward applies, set concern_gate_status = "carried_forward",
  │   log the source, and proceed.
  └─ Match AND no carry-forward applies → REFUSE with class CONCERN_GATE_FAILED + the
      three actionable resolution paths (chunk-index rewrite preferred, decisions-closure row,
      reviewer re-run). The verdict surfaces them; the user picks one.

Draft (LLM judgment; main thread)
  ├─ Mirror Factoring Contract template (sections: Goal, Brief link, Context pack, Conventions,
  │   Factoring Contract — Owns / Contracts changed / Tests to add / Acceptance criteria,
  │   Review checklist, Out of scope)
  ├─ §Owns enumerates files the chunk owns; every owned file has a one-line description
  ├─ §Contracts changed lists new types/functions/schema-fields/operations the chunk introduces
  ├─ §Tests to add describes test cases by behavior + assertion shape (NEVER pre-commit to test paths
  │   per `P-CHUNK-TEST-PATHS`)
  ├─ §Acceptance criteria is verifiable (npm test passes, npm run typecheck passes, specific commands)
  ├─ §Review checklist is short — calls out the load-bearing things a reviewer must verify
  ├─ §Out of scope cites decisions.md entries that defer adjacent work
  └─ Emit first draft to in-memory buffer (NOT yet written to disk)

Plan-lint gate (deterministic, HARD-blocking)
  ├─ Write in-memory draft to /tmp/<slug>-draft-<timestamp>.md
  ├─ Bash: `python3 ~/.claude/skills/plan-lint/lint.py /tmp/<slug>-draft-<timestamp>.md`
  ├─ Capture stdout + exit code into sidecar
  ├─ Failures HARD-blocking — fix locally and re-lint up to 2x; structural failures surface
  │   as STRUCTURAL_LINT_FAILED
  └─ Delete temp file

Ground-truth audit (`_author-common/ground-truth-protocol.md`)
  ├─ Tokenize draft for V1-V5 claims (V1 anchors are heavy at chunk-plan layer)
  ├─ V1 — every path:line, every §heading anchor, every line range
  ├─ V2 — every helper, type, constant, schema field, GraphQL operation, test pattern reference;
  │   classify each as carve-out (introduced by THIS chunk) or anchor (must verify)
  ├─ V3 — counts, ordering, presence of constraints
  ├─ V4 — brief Goal quotes, decisions.md citations, engineering-plan §heading citations,
  │   CLAUDE.md / project-memory rule citations
  ├─ V5 — external API shape claims (rare at chunk-plan layer; usually project-wrapper level)
  └─ Apply outcomes; write sidecar audit log

Self-prosecution (`_author-common/self-prosecution-protocol.md`)
  ├─ Spawn 5 persona agents in parallel:
  │     - backend OR frontend (depending on chunk's Owns set: backend/ vs mobile/ heavy)
  │     - architecture
  │     - testing
  │     - security
  │     - ai-development
  ├─ Each runs the premise-interrogation sub-pass (against the chunk's premises) +
  │   the standard-prosecution sub-pass
  ├─ Consolidate findings; apply auto-fixable
  ├─ Run post-fix premise verification on orchestrator-rewritten prose
  ├─ Classify residuals
  └─ Decide emission via two-state verdict:
      ├─ APPROVED: write chunk plan with NO `Status:` frontmatter (the binary mid-cycle convention) + persist sidecar + render verdict
      └─ NEEDS_USER_INPUT: write partial draft with `Status: needs-user-input` and inline `## Pending blockers` + persist sidecar + render verdict
```

In `--draft` mode the Plan-lint, Ground-truth audit, and Self-prosecution stages are skipped. The Concern gate STILL runs even in `--draft` (self-disclosed multi-concern bundling is a fatal scope error that does not get to defer behind the flag).

---

## State load

Read the author sidecar. Schema:

```json
{
  "feature": "<feature>",
  "chunk_slug": "<slug>",
  "artifact_path": "features/<feature>/implementation/<chunk-slug>.md",
  "authoring_mode": "ship | draft",
  "ground_truth_at": "<ISO 8601 UTC>",
  "self_prosecution_at": "<ISO 8601 UTC>",
  "invocation_number": <int>,
  "last_plan_sha256": "<hex>",
  "concern_gate_status": "passed | refused | skipped | carried_forward",
  "concern_gate_carry_forward_source": {
    "source": "review_state | author_state | decisions_closure",
    "source_path": "<verbatim path or `## Decisions closure` row>",
    "source_blocker_id": "<id or null when source is decisions_closure>",
    "carry_forward_until_round": <int>,
    "user_decision": "<verbatim>"
  },
  "plan_lint_status": "PASS | FAIL",
  "plan_lint_log": "<verbatim>",
  "claims_total": <int>,
  "claims_verified": <int>,
  "claims_verified_softened": <int>,
  "claims_corrected": <int>,
  "claims_dropped": <int>,
  "claims_restructured": <int>,
  "claims_skipped_carveout": <int>,
  "introduced_identifiers": [...],
  "ground_truth_log": [...],
  "self_prosecution_findings": [...],
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
  "verdict": "APPROVED | NEEDS_USER_INPUT | DRAFT_EMITTED"
}
```

`prior_blockers` / `recently_resolved_blockers` mirror the reviewer state schema in `~/.claude/cache/review-state/` so `/explain-blockers` parses author-state with the same parser. `CONCERN_GATE_FAILED` blockers land in `prior_blockers` alongside the universal classes (`STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `FIX_INTRODUCED_PREMISE_INVERSION`, `STRUCTURAL_LINT_FAILED`, `REPO_STATE_DRIFT`). Only HIGH+ findings land here; LOW findings under the polish floor stay in `authoring_residual`. `DRAFT_EMITTED` is set when `--draft` is passed; Plan-lint, Ground-truth audit, and Self-prosecution are skipped, the chunk plan IS written to disk with NO `Status:` frontmatter, the sidecar's `authoring_mode: "draft"` carries the load-bearing draft signal that downstream skills consult, and the user re-invokes without `--draft` to harden. `NEEDS_USER_INPUT` is set when one or more HIGH+ blockers remain; the partially-improved chunk plan IS written to disk with frontmatter `Status: needs-user-input` AND an inline `## Pending blockers` section listing each unresolved finding verbatim (so the user knows what to resolve and the next `--rewrite` invocation reads the partial draft as warm-mode source-of-truth instead of re-emitting from scratch).

Also read the review-state at `~/.claude/cache/review-state/<slug>.json`. Its `recently_resolved_blockers` list is warm-mode carry-forward — re-introducing a defect class the user closed is `FIX_INTRODUCED_PREMISE_INVERSION`.

Also read the engineering-plan-author sidecar `~/.claude/cache/author-state/<feature>__engineering-plan.json`. **The chunk-plan author refuses to run if the engineering-plan-author's last `verdict` is not `CLOSED`.** Per the engineering-plan-review-v2 verdict semantics, `APPROVED` means the engineering plan is shape-correct but cross-chunk decisions remain undecided — authoring chunk plans against an APPROVED engineering plan re-introduces every IMPLEMENTABILITY_GAP into the chunk, which is exactly the thrash this skill exists to prevent.

---

## Source ingest

Hard requirements:
- `features/<feature>/brief.md` exists.
- `features/<feature>/engineering-plan.md` exists.
- Engineering-plan-author sidecar `verdict == "CLOSED"` (or sidecar absent — cold mode is acceptable in early development; warn in verdict).
- The chunk's row in the engineering-plan chunk index exists, with a one-concern description.

Read in this order:

1. `features/<feature>/brief.md` — Goals/Non-goals.
2. `features/<feature>/engineering-plan.md` — focus on the chunk's row in the chunk index, the dependency graph (which sibling chunks ship before this one), the decisions-closure entries that the chunk relies on, and the invariants the chunk enforces.
3. `features/<feature>/decisions.md` — every entry the chunk plan will cite.
4. Existing chunk plan (warm/rewrite mode) — current §Owns, §Contracts, etc. become the warm-mode source-of-truth. This includes a prior `Status: needs-user-input` partial draft from a previous invocation: the partial draft is the canonical anchor, NOT the pre-rewrite version. The Draft stage starts from the partial-draft body (auto-fixes already applied to its prose) and only re-emits sections affected by the user's blocker-resolutions; the unaffected ~80% of the plan stays byte-stable, which is the cost-asymmetry fix that justifies the disk-write semantic.
5. Every file in the chunk's planned "Read first" list — the implementer's read-set is the chunk's anchor surface; the author must have read all of it.
6. `CLAUDE.md` (project conventions, business rules); `MEMORY.md` + relevant project memory.
7. `backend/prisma/schema.prisma` (if backend chunk) or `mobile/src/graphql/operations.graphql` (if frontend chunk).
8. Sibling chunk plans in `features/*/implementation/*.md` — for shape, tone, density, depth-of-prescription consistency.

Build:
- **Invariants ledger** — every brief Goal + every engineering-plan invariant the chunk enforces.
- **Identifier ledger** — every existing identifier the chunk references (functions, types, schema fields, helpers, test patterns from sibling tests). Each gets a verification source.
- **Decisions ledger** — every decisions.md entry the chunk cites.

---

## Concern gate

Deterministic check against the chunk's description, extracted from the engineering-plan chunk-index row matching this slug (located in the Source-ingest stage). The gate runs before Draft. Only ONE pattern triggers refusal — self-disclosure. Concern judgment otherwise is semantic, performed by the ai-development persona's halved-work test in Self-prosecution against the drafted Goal sentence and §Owns set.

### Refusal pattern (match invokes carry-forward consultation; absent carry-forward, the gate refuses)

**Self-disclosure of bundling.** Description matches `/\b\d+-concern\b|\bN-concern\b|\bbundle\b|\bbundling\b/i`. Example: "Orphan-cleanup hardening (4-concern bundle)". This is the author actively admitting the chunk is multi-concern; no false-positive case exists for an author writing "this is a 4-concern bundle" while meaning a single chunk.

### Patterns NOT enforced by this gate

The earlier version of this skill enforced four additional syntactic patterns as auto-refuse triggers: ` AND ` conjunctions, three+ comma-separated noun phrases, `+ <noun> + <noun>` separators, and ≥2 independent clauses. They were dropped. Each had high false-positive rates on legitimate prose:

- "Extract helper used in 12 sites and migrate callsites" is one concern (the migration is incomplete without the extraction).
- "Add fieldA, fieldB, fieldC to the User model" is one schema change with three named columns.
- "Refactor X to use Y and update its callers" is one concern (the rewrite is incomplete without the callsite migration).
- "Schema migration: drop column X; backfill column Y; add index Z" describes one mechanical change with three named ripples.

Concern judgment for these cases is semantic, not syntactic. The ai-development persona evaluates every chunk in Self-prosecution with the **halved-work test**: "if you halved the work in §Owns, would the other half still be a coherent shippable thing?" If yes → multi-concern, surface a finding. If no → one concern, proceed. The persona runs on every chunk regardless of pattern matches; explicit syntactic detection is not needed because the persona reads the actual draft and judges semantically.

### Carry-forward consultation

Run only on a self-disclosure match. The decision is deterministic: carry-forward applies, or it does not. Three sources are checked, in order; the first match wins.

1. **Engineering-plan reviewer state.** Read `~/.claude/cache/review-state/<feature>__engineering-plan.json`. In `recently_resolved_blockers`, find an entry where ALL of:
   - `path_or_section` substring-matches one of: the chunk slug; the chunk-index row's verbatim description; or `chunk-index row N` where N is the row's index position.
   - `blocker_class_when_resolved` is one of `CONCERN_GATE_FAILED`, `CHUNK_BUNDLE`, `MULTI_CONCERN`, `CONCERN_FACTORING` — OR `summary` contains both a concern-family keyword (`bundle`, `concern`, `factoring`) and a resolution-direction keyword (`accept`, `bound`, `keep`, `retain`, `reaffirm`).
   - `carry_forward_until_round >= current_invocation_number` (cross-side number-line mapping per `_author-common/self-prosecution-protocol.md`).

2. **Engineering-plan-author state.** Read `~/.claude/cache/author-state/<feature>__engineering-plan.json`. Apply the same three-condition match against ITS `recently_resolved_blockers`.

3. **Engineering-plan decisions-closure scan.** Read the engineering plan's `## Decisions closure` section (already in memory from Source ingest). A row carries forward when ALL of:
   - The `Decision` column substring-matches the chunk slug or the row's verbatim description.
   - The `Resolution` column starts with `bound` (case-insensitive).
   - The `Resolution` column contains a concern-family keyword (`bundle`, `multi-concern`, `mutually load-bearing`, `transactional invariant`, `theme-unified`).

If any source matches, set `concern_gate_status: "carried_forward"`, populate `concern_gate_carry_forward_source` with the source kind, path/citation, blocker id (when applicable), `carry_forward_until_round`, and the user's decision verbatim. Proceed to Draft.

If no source matches, refuse. Emit `CONCERN_GATE_FAILED` with:
- The exact phrase that triggered the refusal.
- The three actionable resolution paths, in preference order:
  1. Rewrite the engineering-plan chunk-index row description to single-concern phrasing citing the decision (preferred — most durable).
  2. Add an explicit `## Decisions closure` row arbitrating the bundle, with `bound` status and a concern-family keyword in the resolution.
  3. Re-run `/engineering-plan-review-v2` to record the arbitration in the reviewer state's `recently_resolved_blockers`.

---

## Draft

Mirror this section template:

```markdown
# Chunk: `<chunk-slug>` — <one-concern description>

**Slug:** `<chunk-slug>`
**Feature:** <feature>
<!-- Status frontmatter is OPTIONAL and binary. Set to `needs-user-input` ONLY when the chunk plan is mid-cycle (auto-managed by /plan-author NEEDS_USER_INPUT path). Otherwise omit entirely. Lifecycle states (in-progress, merged, verified) are derived from branch / PR / merge state, not frontmatter. -->
<!-- Status: needs-user-input -->  <!-- only when mid-cycle -->

**PR:** —
**Depends on:** `<sibling-chunk-slug>` (if applicable, from engineering-plan dependency graph)
**Brief:** [`../brief.md`](../brief.md) · **Engineering plan:** [`../engineering-plan.md`](../engineering-plan.md)

> This plan is derived from the engineering plan, which is derived from the brief. If you can't restate this chunk's purpose in terms of a brief Goal or User-facing change, stop and re-read both before continuing.

## Goal

<One-sentence statement of what this chunk ships. ONE concern. Verifiable.>

## Brief link

- **Goal:** <verbatim brief Goal quote> — <how this chunk advances it>
- **Non-goal honored:** <verbatim brief Non-goal quote> — <how this chunk respects it>

## Context pack

**Read first:**
- <every file the implementer must read; each entry has a one-line WHY>

**Reference:**
- <less-critical files the implementer may consult>

**Conventions / patterns to follow:**
- <byte-format pinned conventions; ground-truthed against existing code or explicitly chunk-introduced>

## Factoring Contract

### Owns
- `<file-path>` — <what this file does post-chunk; one line>
- ...

### Contracts changed
- <new type / new function / new schema field / new GraphQL operation / new exported constant>
- ...

### Tests to add
- `<behavior + assertion shape>` — <NEVER a literal test path; describe the test by what it asserts>
- ...

### Acceptance criteria
- [ ] <verifiable criterion>; verify with `<command>`
- ...

## Review checklist

- [ ] <load-bearing thing the reviewer must hand-verify>
- ...

## Out of scope

| Item | Where instead |
|---|---|
| <adjacent concern> | <sibling chunk slug \| decisions.md date entry \| explicit out-of-scope> |
```

### Drafting rules — chunk-plan layer

- **Goal sentence is ONE concern.** Apply the halved-work test: if you halved the work in §Owns, would the other half still be a coherent shippable thing? If yes, the chunk is multi-concern; split it. Conjunctions in the Goal sentence are NOT a refusal trigger — "extract helper used in 12 sites and migrate callsites" is one concern (the migration is incomplete without the extraction); "add field X and the test that proves X" is one concern (the test is not separate work). The halved-work test is what matters, not the surface syntax.
- **Context pack "Read first" is honest.** Every file listed is one the implementer truly must read; gratuitous additions just dilute attention.
- **Conventions are byte-format pinned OR cite an existing pattern.** Conventions like "stderr regex format `^abort: ...`" or "audit-row write inside `prisma.$transaction(async (tx) => { ... })`" are byte-pinned and testable. Conventions like "use good error handling" are useless.
- **§Owns describes file purpose, not implementation steps.** "X.ts owns the orphan-deletion script" is good. "X.ts step 1: parse args; step 2: query orphans; step 3: ..." is implementation prose that drifts as code is written. Steps go in the implementer's head, not the plan body.
- **§Contracts changed enumerates exports + schema diffs only.** New non-exported helpers don't go here.
- **§Tests describes assertion shape, not test paths.** Per `P-CHUNK-TEST-PATHS`. The test harness layout is the implementer's call.
- **§Acceptance criteria is verifiable by command.** Every box has a `verify with <command>`. The command must exist (`npm test`, `npm run typecheck`, etc.) — verified at ground-truth time.
- **§Review checklist is short.** 5-15 items. The list calls out load-bearing things; the implementer's full diff has many other lines that don't need surfacing.
- **§Out of scope cites decisions.** If the chunk explicitly does NOT do something the brief allows, cite the decisions.md entry that bound the deferral.
- **No archaeological prose.** No "the original plan said X but actually Y", no "round-3 review changed this", no "see addendum E". Per `_review-common/principles.md` plan style.
- **No persona-attribution headers.** One document, one voice.
- **No invented test infrastructure.** If the chunk's tests need a helper, either (a) the helper exists in a sibling test file (verify and cite), (b) the helper is introduced by THIS chunk (add to §Contracts changed), or (c) the test bullet describes the inline pattern verbatim (e.g., the `vi.spyOn(console, 'error')` template).
- **Diagnostic byte-formats live in §Conventions.** If the chunk's tests assert byte-exact regex on stderr, the regex template is pinned in §Conventions once, not duplicated per test bullet.
- **Proactive convention extraction (≥3 same-shape rule).** When drafting §Tests, §Owns, or §Acceptance criteria, if you find yourself writing the **same structural pattern across 3+ bullets**, extract the pattern to §Conventions before continuing. Examples of structural patterns that MUST be extracted at the third recurrence:
  - The same test setup invariant (e.g., `vi.spyOn(console, 'error').mockImplementation(...)` in 3+ test bullets) → extract as `Convention: stderr-suppression in tests using <pattern>`.
  - The same trap-row idiom in 3+ test setups (e.g., "insert a row whose deletion would violate FK constraint to assert the cleanup script aborts") → extract as `Convention: trap-row idiom for <invariant under test>`.
  - The same byte-exact diagnostic format in 3+ assertions (e.g., `expect(stderr).toMatch(/^abort: cannot proceed: <reason>/)` with shared prefix) → extract as `Convention: abort-stderr regex template`.
  - The same cleanup ordering across 3+ §Owns descriptions → extract as `Convention: cleanup ordering for <resource class>`.
  Without proactive extraction, the same pattern is restated 3+ times in the plan body — exactly the duplication that drives the "≥3 same-shape fix bullets" pattern at review time. The reviewer's convention-extraction sub-step will fold the duplications back into §Conventions as a fix; doing it at write time saves the round.
- **Drafted prose must not contradict bound decisions.** Before emitting the in-memory draft to Plan-lint, scan §Goal, §Brief link, §Conventions, §Owns, §Contracts changed, §Tests to add, §Acceptance criteria, and §Out of scope for prose that contradicts an entry in `features/<feature>/decisions.md` whose `Status:` is `bound`. The chunk plan is downstream of `decisions.md` — if a bound entry says "use approach X for cross-author dedupe", the chunk plan's §Tests cannot describe a test that would only pass under approach Y. When a contradiction is found, prefer rewriting the draft to match the bound decision; if the contradiction is itself a discovery (the bound decision is wrong given new repo state), surface as `OPEN_QUESTION` rather than silently overriding. The Self-prosecution carry-forward auto-retract handles findings the personas raise that contradict bound decisions, but that is reactive — this rule is the proactive write-side pair.

---

## Plan-lint gate

Write the in-memory draft to `/tmp/<slug>-draft-<timestamp>.md`, then invoke the lint script directly:

```bash
python3 ~/.claude/skills/plan-lint/lint.py /tmp/<slug>-draft-<timestamp>.md
```

Capture stdout + exit code into `sidecar.plan_lint_log`. Exit codes: `0` clean, `1` FAIL, `2` usage/IO error. Apply local fixes and re-run up to 2x; if structural defects remain after 2 retries, surface `STRUCTURAL_LINT_FAILED`. Delete the temp file regardless of outcome.

Same deterministic gate semantics as the engineering-plan-author's Plan-lint gate — the chunk-plan layer operates on a chunk plan instead of an engineering plan, but the script handles both layouts.

---

## Ground-truth audit

Apply `_author-common/ground-truth-protocol.md`. At the chunk-plan layer:

- **V1 (anchor) is heavy.** Every `path:line` reference, every `§heading` reference, every line-range reference. Substitute symbolic anchors (`<file>:<symbol>` or `§<heading>`) for numeric ones whenever possible — numeric lines drift, symbols don't.
- **V2 (identifier) is heavy and bimodal.** Every helper / type / constant / schema-field / GraphQL-op reference splits into:
  - Carve-out 1 — introduced by THIS chunk → record in `introduced_identifiers`, do NOT verify against existing repo (the chunk's contract is to make them exist).
  - Anchor — must already exist or come from a sibling chunk that owns it (per A-INTRODUCE-vs-RELOCATE) → verify via grep / Read.
- **V3 (constraint) catches math errors.** "N writer-fence ticks per hydration", "@@unique on X", "X happens before Y in source order". Verify by reading the cited file.
- **V4 (cross-document)** every brief/engineering-plan/decisions/CLAUDE.md citation. Verbatim quote check.
- **V5 (external API)** rare. Most chunks integrate via project wrappers (`backend/src/lib/{tmdb,openLibrary,googleBooks,llm}.ts`); claims about these wrappers are V2 against project code, not V5 against external docs.

Sidecar audit log records every claim, outcome, evidence.

The volume here is the largest of the three layers — chunk plans typically have 50-150 verifiable claims. Each costs one Read or grep. Front-load is roughly equivalent to one round of `/plan-review-v2` machinery.

---

## Self-prosecution

Spawn 5 persona agents in parallel using the template in `_author-common/self-prosecution-protocol.md`:

- **backend** OR **frontend** — depending on which directory the chunk's §Owns concentrates in. Backend chunks use the backend persona; frontend chunks use the frontend persona. Mixed-stack chunks (rare; usually a sign of multi-concern) get both.
- **architecture** — system-shape coherence, hidden dependencies, factoring, cross-chunk wiring.
- **testing** — assertion-shape rigor, test-helper hallucinations, fixture coverage, RED-state ordering, real-DB cleanup conventions. **This persona catches the highest volume of findings at the chunk layer** (per the orphan-cleanup-hardening case study, 14+ findings classed Testing).
- **security** — auth checks, input validation, secret handling, atomic rollback, P2002/P2025 scrub bindings, cascade-flip dust quantification.
- **ai-development** — chunk discipline, plan-quality, banned style, byte-format prescriptions vs proscriptions.

Active critical pairs: universal pairs + chunk-plan-specific pairs (`P-CHUNK-TEST-PATHS`, `P-CHUNK-COMMANDS`, `P-CHUNK-SINGLE-CONCERN`, `P-CHUNK-READ-FIRST`).

After consolidation, run post-fix premise verification on orchestrator-rewritten prose. Classify residuals.

### Verdict template

```markdown
# Chunk plan authoring verdict — features/<feature>/implementation/<chunk-slug>.md

**Mode:** cold | warm
**Authoring mode:** ship | draft
**Round:** <invocation_number>
**Last plan sha:** <hex>

## Concern gate
**Status:** passed | refused | carried_forward
**Refusal reason (if refused):** <triggering phrase + decomposition suggestion>
**Carry-forward source (if carried_forward):** <review_state | author_state | decisions_closure> entry <id-or-citation> until round <N>

## Plan-lint
**Status:** PASS | FAIL
**Defects:** <N>; if FAIL, list each.

## Ground-truth audit
**Claims total:** <N>
**Verified:** <V>  **Softened:** <S>  **Corrected:** <C>  **Dropped:** <D>  **Restructured:** <R>  **Skipped (carve-out):** <K>
**Introduced identifiers:** <count> (<comma-separated list, truncated>)

## Self-prosecution
**Personas:** <persona list>
**Premise interrogation:** <per-persona pass/fail>
**Standard findings:** <N total>; <by tier+severity>
**Post-fix premise verification:** <P claims rewritten; Q falsified> → <FIX_INTRODUCED_PREMISE_INVERSION count>
**Carry-forward consultation:** <skipped because cold | M recently-resolved blockers cross-checked, R re-prosecutions auto-retracted>

## Verdict
**APPROVED** | **NEEDS_USER_INPUT** | **DRAFT_EMITTED**

### Blockers (if NEEDS_USER_INPUT)
- [CONCERN_GATE_FAILED] — <triggering phrase>; decomposition required
- [STRUCTURAL_LINT_FAILED] — <plan-lint defect>
- [STABLE_DISAGREEMENT] <span> — <one-line>
- [OPEN_QUESTION] <span> — <one-line>
- [FIX_INTRODUCED_PREMISE_INVERSION] <span> — <one-line>
- [REPO_STATE_DRIFT] — git rev-parse HEAD changed mid-authoring; re-invoke

### Authoring residuals (LOW, under polish floor)
- ...
```

### Verdict gates

- **APPROVED** when ALL of:
  - Concern gate passed OR carried_forward.
  - Plan-lint PASS.
  - Ground-truth complete.
  - All HIGH+CRITICAL self-prosecution findings resolved.
  - Tier-2 weight ≤ 4 (polish floor).
  - No `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `FIX_INTRODUCED_PREMISE_INVERSION`, `CONCERN_GATE_FAILED`, `STRUCTURAL_LINT_FAILED`, `REPO_STATE_DRIFT`.
- **NEEDS_USER_INPUT** otherwise.

### Pending-blockers section (NEEDS_USER_INPUT mode)

On NEEDS_USER_INPUT, the on-disk chunk plan gets two additions beyond the partial draft body:

1. **Frontmatter `Status: needs-user-input`** is added (or replaces a prior Status value if any). The APPROVED-emission convention is no `Status:` field; the NEEDS_USER_INPUT path adds the field as the only valid Status value.
2. **`## Pending blockers` section appended at the end of the file**, with verbatim bullets from the verdict's `### Blockers` block:

   ```markdown
   ## Pending blockers

   <!-- This section is auto-managed by /plan-author. Resolve each blocker below, then re-invoke `/plan-author --rewrite <feature>/<chunk-slug>`. The next Draft stage reads this file as warm-mode source-of-truth and only re-emits prose affected by your resolutions; the unaffected sections stay byte-stable. -->

   - [<BLOCKER_CLASS>] <span / section> — <one-line summary>; <actionable resolution path>.
   - ...
   ```

On the subsequent `--rewrite` invocation that lands at APPROVED, the entire `## Pending blockers` section AND its HTML comment are removed, AND the `Status: needs-user-input` line is removed (the APPROVED emission convention is no `Status:` field). If the next invocation is still NEEDS_USER_INPUT, the `## Pending blockers` section is rewritten with the new blocker set (replaced, not appended to — stale blockers don't accumulate); the `Status: needs-user-input` line stays.

---

## Hard rules

- **Stage order is fixed.** State load → Source ingest → Concern gate → Draft → Plan-lint gate → Ground-truth audit → Self-prosecution. `--draft` skips Plan-lint, Ground-truth audit, and Self-prosecution only; the Concern gate still runs.
- **Engineering plan must be CLOSED.** If the engineering-plan-author sidecar's verdict is APPROVED (decisions still undecided) or NEEDS_USER_INPUT, the chunk plan author refuses to run. The user must bind cross-chunk decisions and re-invoke `/engineering-plan-author --rewrite <feature>` to land at CLOSED first.
- **Concern gate is HARD-blocking unless carry-forward applies.** Triggered only by self-disclosed bundling (the description literally containing `\bN-concern\b`, `\bbundle\b`, or `\bbundling\b`). A draft for a self-admitted multi-concern chunk does not reach Draft when no upstream arbitration is recorded in the engineering-plan reviewer state, the engineering-plan-author state, or the engineering plan's `## Decisions closure` section. Other concern judgments (genuine bundling that the description doesn't self-disclose) are handled semantically by the ai-development persona's halved-work test in Self-prosecution, NOT by this gate.
- **Plan-Lint is HARD-blocking.** Same as engineering-plan-author.
- **No length or files-touched gate.** A chunk plan that runs 500+ lines because its single concern's footprint is broad (e.g., a refactor that extracts one helper used in 12 sites; a callsite migration after a rename) is not refused on size. The earlier Byte-budget gate (500 lines / 40k tokens) was dropped because length is downstream of footprint breadth, not an independent measure of factoring quality. Bloat-from-overscoping (premature abstraction, dead scaffolding, restating the brief) is caught by the "Abstraction earns its place", "No scaffolding", and Self-prosecution gates, which target the actual failure mode.
- **Disk-write semantics by verdict:** APPROVED writes the chunk plan with NO `Status:` frontmatter (the binary-Status convention reserves `Status:` for the mid-cycle signal only); NEEDS_USER_INPUT writes the partially-improved in-memory draft with frontmatter `Status: needs-user-input` AND an inline `## Pending blockers` section listing each unresolved finding verbatim from the verdict (the user fixes the blockers and re-invokes; the partially-improved draft becomes the warm-mode source-of-truth so re-generation cost is paid once, not on every iteration); DRAFT_EMITTED writes with NO `Status:` frontmatter; the sidecar's `authoring_mode: "draft"` is the load-bearing draft signal that downstream skills consult. The user re-invokes without `--draft` to harden via Plan-lint, Ground-truth audit, and Self-prosecution. Sidecar persists in all cases. The reviewer skill `/plan-review-v2` refuses to run against `Status: needs-user-input` artifacts — the partial draft is mid-cycle by design and not yet a candidate for prosecution. `/execute-plan` consults the sidecar's `authoring_mode` and refuses on draft (implementing a draft plan ships hallucinations).
- **Sidecar always written.** Every invocation, every verdict.
- **Carry-forward respect.** Re-introducing a defect class the user closed in a prior invocation is `FIX_INTRODUCED_PREMISE_INVERSION`.
- **No banned content.** Same prohibited categories as `/brief-author` and `/engineering-plan-author`.
- **Banned single-file grep at write time.** Per `~/.claude/CLAUDE.md` global rules and the agent template's tool-selection note, single-file grep is the wrong tool — use Read for symbols inside a known file.
- **Proactive convention extraction (≥3-same-shape rule) is mandatory at Draft.** Before emitting the in-memory draft to Plan-lint, scan §Tests, §Owns, and §Acceptance criteria for ≥3 bullets sharing a structural pattern (test-setup invariant, trap-row idiom, byte-exact diagnostic format, cleanup ordering). Each detected ≥3-same-shape group must be extracted into a §Conventions entry before the draft proceeds. The Self-prosecution ai-development persona will catch a Draft that skipped this step; the rule exists so the gap is closed at write time, not at the next review round. The verdict template's `Ground-truth audit` block must record `convention_extractions: <count>` (with the patterns enumerated) so a "0 extractions on a 30-bullet test list" attestation is visible as a red flag.
- **Drafted prose must not contradict bound `decisions.md` entries.** Before emitting the in-memory draft to Plan-lint, scan every section for prose that contradicts an entry in `features/<feature>/decisions.md` whose `Status:` is `bound`. Contradictions are HARD-blocking unless surfaced as `OPEN_QUESTION` (the bound decision may itself be wrong given new repo state, but that is a re-arbitration, not a silent override). The verdict template's `Ground-truth audit` block records `bound_decisions_consulted: <count>; contradictions_found: <count>` so missing this step is visible. The Self-prosecution carry-forward Priority 1 auto-retract handles persona findings that contradict bound decisions reactively; this rule is the proactive write-side pair.

---

## Edge cases

**Engineering-plan sidecar absent (cold development):** Run with degraded checks; emit `WARNING: engineering plan not yet CLOSED — chunk plan may need rework after engineering-plan finalization`. Verdict mentions it. The chunk plan can still be useful in early exploration.

**Chunk slug not in engineering-plan chunk index:** Refuse to run; the chunk hasn't been declared. Suggest `/engineering-plan-author --rewrite <feature>` to add the chunk row.

**Chunk slug exists but description is multi-concern:** Concern gate fails; surface `CONCERN_GATE_FAILED` blocker with the engineering-plan amendment recommendation.

**Plan-lint fails after 2 fix attempts:** Surface `STRUCTURAL_LINT_FAILED` blocker. Common cause: vague acceptance criteria or position-encoded slugs introduced by the LLM during drafting; user fixes by hand and re-invokes.

**Sibling test patterns referenced (e.g., `vi.spyOn` from `personHydration.test.ts`):** Verify each by Read of the cited sibling file at the cited section. If the pattern actually appears, anchor the citation symbolically (`personHydration.test.ts:<test-name>`); if not, surface `INVENTED_TEST_PATTERN` finding (testing persona's class).

**Real-DB test cleanup pattern needed:** If the chunk's tests write to the real test DB AND no sibling test in the same `__tests__/` directory has a real-DB cleanup template, the chunk plan must define the template in §Conventions (BASE constants, sequence-restore, OR-predicate cleanup). Author-side: surface this as an `OPEN_QUESTION` if the user hasn't bound conventions; per the orphan-cleanup-hardening case, the user resolved this in Round 5 Batch A.

**Repository state drift mid-authoring (rare):** If the SHA of files in the chunk's read-set changes between Source-ingest read and Ground-truth-audit verification, treat as `REPO_STATE_DRIFT` and require re-invocation. The deterministic detection: capture each read file's SHA at Source ingest; re-check at Ground-truth audit entry.

**`--draft` mode:** Plan-lint, Ground-truth audit, and Self-prosecution are skipped. The Concern gate STILL runs — self-disclosed multi-concern bundling is a fatal scope error that doesn't get to defer behind `--draft`. Sidecar records `authoring_mode: "draft"`, `verdict: "DRAFT_EMITTED"`, `concern_gate_status: "passed" | "carried_forward"` (refusal still aborts in this mode). Chunk plan IS written to disk with NO `Status:` frontmatter. The sidecar's `authoring_mode: "draft"` field is the load-bearing draft signal: `/plan-review-v2` consults it and warns in its verdict (does NOT refuse — `--draft` is a user-opt-in to the unhardened state, distinct from `Status: needs-user-input` where the reviewer hard-refuses); `/execute-plan` consults it and REFUSES (implementing a draft plan ships hallucinations). User re-invokes without `--draft` to harden.

**`.scratch/<name>.md` plan (not under `features/<feature>/implementation/`):** Slug derives to `scratch__<name>`. The brief/engineering-plan reads in Source ingest are skipped (no upstream); the Concern gate still applies (regex against the chunk's H1 / Goal sentence — no chunk-index row to consult, and carry-forward sources are unavailable); Plan-lint, Ground-truth audit, and Self-prosecution run normally. Self-prosecution drops the `product` persona (no brief to map to).

---

## Relationship to sister skills

- **Upstream: `/engineering-plan-author`.** Must be at CLOSED for chunk authoring to proceed (see Hard rules).
- **Reviewer: `/plan-review-v2`.** Its `recently_resolved_blockers` are warm-mode constraints. Author-side findings share blocker classes. The author's sidecar's `introduced_identifiers` and `ground_truth_log` let `/plan-review-v2` skip re-prosecuting verified claims.
- **Indirect upstream: `/brief-author`.** Brief edits cascade through `/engineering-plan-author` re-authoring; chunk plans inherit the latest brief Goals via the engineering plan's Brief Mapping table.

The chunk-plan layer is where thrash concentrates and where this skill earns its keep. The orphan-cleanup-hardening case (Round 5: 28 findings, 5 user decisions, 13 batches, 563-line plan) is exactly what the concern gate + ground-truth + self-prosecution stack is designed to prevent at write time, not five rounds later at review time.
