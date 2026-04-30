---
name: engineering-plan-review
description: Convene an adversarial tribunal of expert personas on a feature's engineering-plan.md. Ruthlessly attack chunk granularity, brief drift, hidden dependencies, rollout gaps, and false parallelism. Fix the plan, loop until clean. Sister skill to /plan-review (which targets per-chunk implementation plans).
user-invocable: true
---

# Engineering Plan Review — Adversarial Tribunal

Engineering plans sit between the product brief and the per-chunk implementation plans. A bad engineering plan poisons every chunk plan downstream — the implementer can't recover from a feature whose chunks aren't shippable, whose dependencies are wrong, or whose rollout has unexamined holes.

This skill is a sister to `/plan-review`. The differences:

| | `/plan-review` | `/engineering-plan-review` (this) |
|---|---|---|
| Target | One chunk's implementation plan (`features/<feature>/implementation/<slug>.md`) | One feature's engineering plan (`features/<feature>/engineering-plan.md`) |
| Repo Reality Audit scope | Every file/line/identifier the chunk plan names | Architecture-level claims + chunk-index status hygiene + cross-chunk file boundaries |
| Top failure modes | Hallucinated paths, vague TDD, oversized chunk | Brief drift, hidden cross-chunk deps, false parallelism, missing rollback, unjustified chunks, **implementation detail baked into the engineering plan** |
| Brief alignment | Inherited from engineering plan | **Load-bearing** — every chunk must trace back |

If the user asks for review of a chunk plan, redirect to `/plan-review`. This skill is for the engineering-plan layer only.

## Tribunal principles

**BRIEF IS CANONICAL, REPO IS LAW.** Two sources of truth bound this review:

1. **The brief** (`features/<feature>/brief.md`) is the contract for *what* this feature delivers. Every chunk in the engineering plan must trace back to a Goal, User-facing change, or Non-goal in the brief. A chunk that doesn't trace is either evidence of a missing Goal (update the brief) or an unjustified chunk (drop it).
2. **The repo** is the contract for *how* the plan can be executed. Architecture claims, file paths, existing patterns, CI workflows, and chunk dependencies must match the branch the plan executes on. Hallucinated architecture is a CRITICAL finding.

**Banned rationalizations:**
- "every chunk roughly maps to a goal" — every chunk maps **explicitly** in the Brief Mapping section, or it doesn't map.
- "the brief implies this" — the brief states; it doesn't imply. Update the brief or drop the chunk.
- "we'll figure out the dependency at implementation time" — declared dependencies are part of the plan's contract.
- "minor scope creep is fine" — non-goals are non-goals.
- "rollback is obvious" — rollback path is named and verified or it doesn't exist.
- "the implementer needs the test names spelled out here" — they don't, and putting them here makes them stale by the time the chunk plan is written. Test names belong in the per-chunk plan.

**Prosecute, don't collaborate.** Find the reason this plan will produce a half-shipped feature, an unmergeable PR, or a corrupt prod state mid-rollout. If you can construct a scenario where executing the plan verbatim produces one of those, it's CRITICAL.

**Fix, don't annotate.** Every finding becomes a direct edit to the engineering plan, or an edit to the brief, or an escalation to the user. No dangling "consider…" comments.

## Plan style rules (forward-looking, not archaeological)

The same forward-looking rules from `/plan-review` apply. The engineering plan is a contract for an implementer with no context about how it was produced. It MUST NOT contain:

- **Addendum sections.** Findings integrate into the section they correct.
- **Review attribution.** No "architecture review found…", "round-3 tribunal flagged…".
- **Cross-references between fix locations.** No "see addendum E", "binding per round-N finding".
- **Conflict-resolution metadata.** Pre-resolve and state the resolved instruction.
- **Historical comparisons.** No "the original plan said X but actually Y".
- **"Decisions resolved" sections** in the engineering plan itself — decisions live in `features/<feature>/decisions.md`. The engineering plan may *link* to decisions.md but does not duplicate it.

The smell test: pretend you've never seen the plan, never heard of the review, and have 10 minutes to start work on Wave N. Can you act on every section without reconstructing how the plan got into its current state?

## Usage

```
/engineering-plan-review <plan-path> [--personas <p1> <p2> ...]
/engineering-plan-review <feature-name>          # resolves to features/<feature-name>/engineering-plan.md
/engineering-plan-review                          # search features/ for active engineering plans, ask which
```

**Examples:**

```
# By feature name (most common)
/engineering-plan-review author-tmdb-hydration

# By explicit path
/engineering-plan-review features/author-tmdb-hydration/engineering-plan.md

# Multiple personas in parallel — N personas = N parallel agents on the same plan
/engineering-plan-review author-tmdb-hydration --personas architecture ai-development product

# No args — list every features/*/engineering-plan.md, ask
/engineering-plan-review
```

## Argument parsing

Split `$ARGUMENTS` on whitespace. Classify each token:

- Token is `--personas` → all subsequent non-path tokens are persona names.
- Token contains `/` or ends with `.md` → plan path.
- Token matches a directory name under `features/` → resolves to `features/<token>/engineering-plan.md`.
- Otherwise → treated as a feature name; if `features/<token>/engineering-plan.md` doesn't exist, stop and report.

No arguments → enumerate `features/*/engineering-plan.md` and list them with their feature name and the brief's `Status:` field (engineering plans themselves are unstamped — status lives in the brief). Ask which to review.

## Persona resolution

### Explicit personas

Load each from `personas/{name}.md` (same path convention as `/plan-review`). The plan is reviewed by every listed persona in parallel. M personas = M agents. Missing persona file → stop and report.

### Auto-assignment (no `--personas`)

Default tribunal for engineering-plan review is **3 personas in parallel**:
- `architecture.md` — cross-cutting design, dependency graph integrity, abstraction boundaries.
- `ai-development.md` — chunk granularity, parallel-execution map, plan structure for AI-implementer consumption.
- `product.md` — brief alignment, scope discipline, non-goals enforcement, user-facing change verification.

If the plan's content strongly skews toward one domain, swap one of these for a domain-specific persona (security, data-engineering, frontend, etc.). Justify the swap in the review output.

`ai-development.md` is loaded as supplementary context for every agent — even non-`ai-development` personas should know the chunk-discipline rules.

## Workflow

### Single-plan, single-persona

Execute the review phases inline.

### Single-plan, multiple personas (default)

- Read `personas/ai-development.md`, the brief (`features/<feature>/brief.md`), and (if exists) the decisions log (`features/<feature>/decisions.md`) once — shared context.
- Resolve personas (auto or explicit).
- **Launch one Agent per persona in parallel in a single message.** M agents.
- Wait for all to complete.
- Consolidate (below).
- Apply fixes once at the end (not per-persona) so personas don't write conflicting edits to the same line.

**Agent prompt template:**

> You are a hostile reviewer on an adversarial tribunal, reviewing an engineering plan as the **{persona_name}** persona.
>
> {persona_file_content}
>
> ## AI Development Principles (always apply)
> {ai_development_content}
>
> ## Feature Brief (canonical product contract)
> {brief_content}
>
> ## Feature Decisions Log (if exists)
> {decisions_content_or_"(no file)"}
>
> ## Engineering Plan Under Review: {plan_path}
> {plan_content}
>
> ## Your Task
>
> Prosecute this engineering plan. Assume it is broken until you prove otherwise. The brief is the contract; the plan must honor it. Repo reality is law; the plan must match it.
>
> **Execute every phase below. The Brief Trace Audit AND Repo Reality Audit are MANDATORY and BLOCKING every round.**
>
> Output your findings using the format in the SKILL doc, then propose specific edits to the engineering plan (or brief, or decisions log). Do NOT apply edits — return them as a fix list. The orchestrator applies all personas' fixes after consolidating.

---

## Review phases

### Phase 1 — Brief Trace Audit (MANDATORY, BLOCKING)

The Brief Mapping section in the engineering plan is the load-bearing link between brief and plan. If the mapping is incomplete, the plan has unjustified or undelivered work.

For each round, produce:

```
### Brief Trace Audit (Round N)

Brief Goals listed: <count>
Brief User-facing changes listed: <count>
Brief Non-goals listed: <count>

Goals delivered by chunks (per Brief Mapping):
- "<verbatim Goal from brief>" → chunks {`slug-a`, `slug-b`, ...}
- "<...>" → ❌ NO CHUNKS LISTED  [CRITICAL — undelivered Goal]

User-facing changes (per Brief Mapping):
- "<verbatim change from brief>" → delivered by {`slug-a`, `slug-b`}, verified by {`slug-x` / "Manual review"}
- "<...>" → ❌ MISSING `Verified by` ENTRY  [HIGH — user-facing change with no test trace]

Chunks in the chunk index: <count>
Chunks that appear in the Brief Mapping (Goals, User-facing changes, or Supporting infrastructure subsection):
- `schema-migration`, `cascade-rewrite`, `wikidata-qid-backfill`, ... ✓
- `legacy-shim-cleanup` ❌ NO MAPPING  [CRITICAL — unjustified chunk]

Brief Non-goals → enforcement check:
- "<verbatim non-goal>" → enforced by: <plan section / chunk> / ❌ NOT ENFORCED  [HIGH]

Brief drift:
- Plan claims user-facing behavior X. Brief does not list X.  [HIGH — scope creep or missing brief Goal]
- Brief lists Goal Y. Plan does not deliver Y.                [CRITICAL]
```

If a chunk appears nowhere in the Brief Mapping, that's a CRITICAL finding — either the brief needs a Goal or the chunk needs to be dropped. Don't silently let it slide.

### Phase 2 — Repo Reality Audit (MANDATORY, BLOCKING)

Engineering plans don't name file lines (those live in chunk plans), but they do make architecture-level claims that must be verified.

- **Tree:** `ls` repo root.
- **Existing files / patterns the architecture summary cites:** for every file path mentioned in Architecture Summary, `ls` it. For every pattern claimed (e.g., "matches existing `personFieldChange` pattern"), grep for the pattern's anchor and verify.
- **Existing CI workflows the plan extends:** `ls .github/workflows/` and read the files. If the plan claims it adds a job to an existing workflow, verify the workflow exists and the job hook fits.
- **Chunk-index hygiene:** the engineering plan is frozen post-approval and MUST NOT contain status columns, "merged" annotations, "last updated" timestamps, or PR links — that's tracker data, not plan data. Flag any of these as a structural defect (CRITICAL), but verify the plan's `Code deps` against repo reality regardless: for any chunk whose deps reference an earlier chunk, verify the earlier chunk's claimed exports / file boundaries exist on `main` (if shipped) or are coherently scoped (if not yet shipped). Status tracking lives on each per-chunk plan's `Status:` field — confirm the engineering plan does not duplicate it.
- **Chunk file boundaries (cross-chunk hidden deps):** for each pair of chunks claimed parallel in the dependency graph, infer the file set each will touch (from the chunk plan if it exists, or from the historical plan reference if not). Any file that appears in both → CRITICAL. False parallelism causes merge conflicts mid-wave.
- **Implementation-detail leak audit:** the engineering plan stays at architecture level. Scan every section for chunk-internal commitments that should live in the per-chunk plan instead: specific test names ("TEST 4 covers …"), action keys, e2e flow IDs, internal phase splits inside one chunk ("Phase 1 / Phase 2"), function-by-function file lists, files-to-create lists, acceptance checkboxes, SQL queries, regex patterns, exact log-line wording. Each leak is a HIGH finding (CRITICAL when it locks the implementer into a stale commitment, e.g. naming a test file that the chunk-plan author would name differently if free to choose). Fix: strip from the engineering plan; if the architecture-level contract still needs to be expressed, restate it as an invariant or a one-line rollback path.

Record the audit in your review output:

```
### Repo Reality Audit (Round N)

- Tree: <dirs>
- Architecture claims verified:
  - "Two thin constructors `buildTMDBClaim`, `buildOLAuthorClaim`" → file `personDisambiguation.ts` exists / does not exist; constructors absent (pre-implementation, expected) / present
  - "renamed `BioSource` → `DataSource`" → schema.prisma has `enum DataSource` ✓ / still has `BioSource` (mismatch with `schema-migration` chunk's claimed scope)
- CI workflow claims:
  - "feature flag `AUTHOR_HYDRATION_ENABLED`" → grep'd src/, present in `orchestrator-rollout` chunk's scope ✓
- Chunk-index hygiene:
  - Columns are `Slug | Chunk | Code deps` ✓ / column header is `# | Chunk | Code deps` ❌ CRITICAL (numbered identifiers; rename to slug)
  - No `Status` column ✓ / `Status` column present ❌ CRITICAL (frozen plan tracking violation)
  - No `PR` column ✓ / `PR` column present ❌ CRITICAL
  - `wikidata-qid-backfill` deps "—" → its plan section asserts it depends on shared rate-limiter abstraction in `src/lib/olRateLimiter.ts` ✓ exists on main
- False-parallelism check:
  - Wave 2 [`cascade-rewrite` ‖ `prisma-error-helpers` ‖ `ol-rate-limiter-classes` ‖ `wikidata-rate-limiter` ‖ `tmdb-client-extensions`]: `cascade-rewrite` touches `llm.ts`, `personDisambiguation.ts`; `prisma-error-helpers` touches `prismaErrors.ts`; `ol-rate-limiter-classes` touches `olRateLimiter.ts`; `wikidata-rate-limiter` touches `wikidataRateLimiter.ts`; `tmdb-client-extensions` touches `tmdb.ts`. No overlap ✓
- Implementation-detail leak audit:
  - "TEST 4 covers cascade fail-closed under LLM circuit-open" ❌ HIGH (specific test name in engineering plan; belongs in `cascade-rewrite` chunk plan)
  - "Phase 1: rename column; Phase 2: add index" ❌ HIGH (internal phase split inside `schema-migration`; belongs in chunk plan)
  - "creates `backend/scripts/auditOrphanPersons.ts`" ❌ HIGH (file-creation list; belongs in chunk plan's Files-to-create section)
```

If the audit contradicts the plan, those contradictions are the first findings of the round.

### Phase 3 — Structural Review

Engineering-plan-specific structural rules. The template at `features/_template/engineering-plan.md` is the source of truth for shape, section order, and forbidden patterns. Read it once before reviewing.

**Section order is fixed** (per template). Skip optional sections only when truly inapplicable; never reorder, rename, or merge:

1. Brief mapping
2. Architecture summary
3. Invariants                    *(optional)*
4. Other domain contracts        *(optional, e.g. Field Precedence, Cost & Capacity)*
5. Chunk index
6. Manual gates                  *(optional)*
7. Dependency graph
8. Risks / unknowns
9. Rollout plan                  *(optional)*
10. Out of scope

**Required sections (always present):**
- [ ] Header with `**Brief:**` link (and `**Decisions:**` link when `decisions.md` exists)
- [ ] Guidance callout reminding the brief is the input
- [ ] Brief mapping section, with `### Goals`, `### User-facing changes`, and `### Non-goals enforcement` subsections
- [ ] User-facing changes table includes a `Verified by` column
- [ ] Architecture summary
- [ ] Chunk index with **exactly** these columns: `# | Chunk | Code deps`. No others.
- [ ] Dependency graph (DAG, even if linear)
- [ ] Risks / unknowns
- [ ] Out of scope

**Conditionally-required sections:**
- [ ] **Rollout plan** — required if the feature has prod state changes (DB writes, flags, migrations, monitoring).
- [ ] **Manual gates** — required if the plan has any non-PR steps (operator dry-runs, `--apply` invocations, snapshot captures) that block downstream chunks. Section includes both the `Gate | Blocks on` table and an `Each --apply requires:` prerequisite list.
- [ ] **Invariants** — required if the feature has cross-chunk rules that any chunk writing to the affected tables MUST preserve. Each invariant gets one `###` subsection: rule statement plus an `Enforced by:` bullet list naming chunks.
- [ ] **Other domain contracts** — required when the feature has cross-chunk contracts beyond invariants (Field Precedence, Cost & Capacity, SLA targets, Quality gates).

Each missing required section is a finding.

**Chunk index column rules:**
- [ ] Columns are EXACTLY `Slug | Chunk | Code deps`. A `#` (number) column is a CRITICAL structural defect — chunks are identified by slug, not number. Any of `Status`, `PR`, `Mode`, `Owner`, `Last-updated` is also a CRITICAL structural defect (frozen-plan tracking violation).
- [ ] Slugs are kebab-case, 2–4 words, descriptive of the chunk's **concern**. Good: `schema-migration`, `wikidata-qid-backfill`. Forbidden shapes (all are numbered identifiers in disguise; flag each occurrence as CRITICAL): `phase-N-*`, `step-N-*`, `wave-N-*`, `chunk-NN`, `NN-*`, `*-Na`/`*-Nb`, `01a/01b`, `Phase 2.b`. A slug encodes what the chunk does, not where it sits in the graph.
- [ ] Chunk names (the prose label beside the slug) are 6–10 words, plain English. No `(WIP)` / `(stretch)` / `(if time)` markers. No `Phase N` / `Step N` prefixes.
- [ ] Chunk-name style is consistent across the index — pick imperative-noun ("Schema migration") OR descriptive ("Backfill Wikidata Q-IDs") and stay in that lane.
- [ ] `Code deps` cell is comma-separated chunk slugs (`schema-migration, llm-circuit-breaker`) or `—` for none. Manual-gate dependencies do NOT belong here — they live in the Manual gates section.

**Chunk discipline:**
- [ ] Every chunk = one PR, ≤5 files (the chunk plan enforces final file count, but the engineering plan must not bundle obvious multi-PR work into one chunk).
- [ ] Every chunk has a single concern (sniff test: can you describe the chunk in one sentence without using "and")?
- [ ] Every chunk is independently shippable — even behind a flag — without breaking `main`.

**Dependency graph:**
- [ ] DAG is explicit (text or diagram). Linear-only deps still get a graph.
- [ ] Every chunk's `Code deps` field matches the graph.
- [ ] Apply-deps (operator-execution preconditions) are separated from code-deps; conflating them is a finding.
- [ ] Operator-executed runs (`--apply`, prod runs) appear in the Manual gates section or rollout plan. They must be visible.
- [ ] Wave-numbered graphs include the cross-wave gating rule statement.

**Rollout plan (when present):**
- [ ] Feature flag named (or stated as N/A with reason).
- [ ] Migration order explicit (or N/A with reason).
- [ ] Monitoring/observability named (logs, metrics, dashboards).
- [ ] Rollback path named for every irreversible step (DB writes, schema changes, prod-config changes).
- [ ] Pre-`--apply` gates listed for every operator-executed run.

**Out of scope:**
- [ ] Brief non-goals appear verbatim, no embellishment, no reason needed (the brief explained).
- [ ] Technical deferrals append a one-line reason.

**Decision log linkage:**
- [ ] Major architectural choices (rejected alternatives, irreversible commitments) are either in `decisions.md` or have a `Why:` paragraph in the plan that the reviewer judges sufficient. If a Risk references a decision, it should link to `decisions.md` rather than restate.
- [ ] No "Decisions resolved" section in the plan body — the plan may *link* to `decisions.md` but never duplicate it.

**Forbidden patterns (each occurrence is a finding; tracker columns and numbered identifiers are CRITICAL):**
- [ ] No status / PR / mode / owner / last-updated / `#` columns or fields anywhere in the plan.
- [ ] No numbered chunk identifiers (`01`, `27a`, `chunks 22+23+24+26`). Slugs only.
- [ ] No implementation detail (chunk-internal commitments) — see the dedicated "Implementation-detail leak audit" in Phase 2. Specific test names, action keys, e2e flow IDs, internal phase splits, function-by-function file lists, files-to-create lists, acceptance checkboxes, SQL queries, regex patterns, exact log-line wording all belong in the per-chunk plan.
- [ ] No meta-commentary about the doc itself ("this section…", "below we'll cover…", "this is the first place implementation detail enters…"). Just write the content.
- [ ] No hedging future tense ("we will likely", "this plan aims to", "we plan to", "the team should consider"). Declarative present tense only — the plan IS the contract.
- [ ] No restatement of the brief or the README. Reference; do not repeat.
- [ ] No "Open questions" section. Open questions belong in the brief and must be resolved before the plan is approved.
- [ ] No legacy implementation slugs ported from older plans (`1d-cascade`, `Phase 2.b`).
- [ ] No trailing summary paragraphs that restate the section.
- [ ] No tribunal / round-N findings / change-log notes inside the plan body. Lineage from older plans goes in `decisions.md` if it goes anywhere.
- [ ] No vague nouns ("the new system", "a helper", "some scripts") when the concrete name (function, table, file path) exists.

**Cross-reference format:**
- [ ] Chunks referenced by slug: `chunk schema-migration`, `chunks cascade-rewrite + callsite-migration`. Never `chunk 05`, `Chunk 1d-cascade`, `Ch5`.
- [ ] Other features referenced as `features/<name>/engineering-plan.md`.
- [ ] Source files backticked: `` `backend/src/lib/runId.ts` ``.
- [ ] Other sections of this plan referenced by section title, not "above" / "below".

**Tone:**
- [ ] Declarative present tense throughout.
- [ ] Short paragraphs, ≤4 lines each, one idea per paragraph.
- [ ] Concrete names, not generic descriptors.
- [ ] No emojis. No exclamation marks.

Each structural failure is a finding with severity.

### Phase 4 — Persona Prosecution

Review every section through the persona's lens as a hostile expert. For each claim:

- Does the architecture summary's pattern claim match the codebase? (Cross-check Repo Reality Audit.)
- Does the Brief Mapping line up with the persona's read of the brief? (e.g., a `product` persona might catch a missing user-facing change; an `architecture` persona might catch a missing infra dependency.)
- Can you construct a scenario where executing wave N verbatim leaves wave N+1 unable to start?
- Can you construct a scenario where an operator `--apply` runs against an inconsistent state because a precondition is missing?
- Are the Risks section and the Rollback path adequate for the persona's failure-mode catalog?
- Does the plan respect project invariants in `CLAUDE.md`, `SPEC.md`, `features/README.md`, etc.? Quote the invariant when flagging a violation.

**Verify, don't infer.** If the plan says "extends existing `circuitBreaker`," open `circuitBreaker.ts` and confirm the extension points exist. If it says "reuses graphql-ws subscription transport," grep for it in `mobile/src/`.

Finding format:

```
[CRITICAL] {Section / Wave / Chunk}: {finding}
  - Evidence: {verbatim plan quote} vs {repo file:line / grep output / brief quote}
  - Impact: {concrete failure mode — half-shipped feature, mergeable PR conflict, prod state corruption, ...}
  - Fix: {specific edit to the engineering plan, brief, or decisions.md}
```

Severities:
- **CRITICAL** — plan will fail mid-execution, leave a half-shipped feature, or corrupt prod state. Includes any unjustified chunk or undelivered brief Goal.
- **HIGH** — significant correctness or rollout-safety risk.
- **MEDIUM** — real gap that weakens the plan.
- **LOW** — polish that still must be fixed before APPROVED.

**Severity does not gate fixing.** Everything gets fixed or escalated.

### Phase 5 — Consolidate

Multi-persona mode: merge structural + per-persona findings into a single deduplicated list, grouped by section. Note source persona on each finding.

Single-persona mode: skip — your findings are already consolidated.

Present the consolidated list to the user before applying fixes (single-plan inline mode) OR include in the agent's final output (multi-plan mode where the orchestrator collects).

### Phase 6 — Fix the Plan

Apply every fix to the relevant file:

- Engineering plan defects → edit `features/<feature>/engineering-plan.md`.
- Brief drift (plan delivers something the brief doesn't list, or brief Goal isn't delivered) → edit either the brief or the plan, depending on which is "right." If unclear, escalate.
- Decision rationale missing → add an entry to `features/<feature>/decisions.md` and link from the plan.
- Hallucinated architecture claim → replace with the verified pattern from the Repo Reality Audit.
- Unjustified chunk → either add the missing brief Goal to justify it, or drop the chunk and renumber.
- False parallelism → split the wave, or add a code-dep edge between conflicting chunks, or merge them into one chunk.
- Missing rollback → name the rollback path explicitly with the verified command/SQL.
- Mode-C overreach → downgrade to Mode A or split the chunk.

**Forbidden fixes:**
- Weakening the plan (dropping rollback, lowering quality gates) to resolve a finding.
- Editing the brief just to make a chunk fit (brief is canonical; if a chunk doesn't fit, drop the chunk, don't bend the brief).
- "Will be cleaned up later" — if it's not in the plan now, it won't happen.

Output a summary of edits made.

### Phase 7 — Re-review (Loop)

Re-run Brief Trace Audit, Repo Reality Audit, Structural Review, Persona Prosecution, Consolidate. Audits repeat in full — fixes can introduce new defects.

**Termination:** a round produces zero findings at any severity AND both audits pass 100%.

**Max rounds:** 3. If round 3 still has findings, escalate ALL of them to the user.

### Phase 8 — Final Report

```
## Engineering Plan Review Complete: features/<feature>/engineering-plan.md

**Personas:** {names}
**Rounds:** {N}
**Final Brief Trace Audit:** PASS / N issues remain (see below)
**Final Repo Reality Audit:** PASS / N issues remain (see below)

### Changes Made
- Plan: {bullets}
- Brief (if any): {bullets}
- Decisions log (if any): {bullets}

### Retractions from earlier rounds
- {findings dropped because audits showed they were based on wrong assumptions}

### Needs User Input (if any)
- {issues requiring human decision — state tradeoff and options}

### Plan Status: APPROVED / NEEDS USER INPUT
```

**APPROVED** = zero findings at any severity, both audits pass 100%.
**NEEDS USER INPUT** = genuinely-open design decisions or brief/plan conflicts only the user can resolve. Not lazy-deferred MEDIUM/LOW.

---

## Combined summary (multi-persona mode)

```
# Engineering Plan Review Summary: <feature>

| Persona | Rounds | Critical | High | Medium | Low | Brief Audit | Repo Audit | Status |
|---|---|---|---|---|---|---|---|---|
| architecture | 2 | 0 | 0 | 1 | 0 | PASS | PASS | NEEDS USER INPUT |
| product | 1 | 0 | 0 | 0 | 0 | PASS | PASS | APPROVED |
| ai-development | 2 | 0 | 0 | 0 | 0 | PASS | PASS | APPROVED |
| **overall** | | **0** | **0** | **1** | **0** | **PASS** | **PASS** | **NEEDS USER INPUT** |

## Needs User Input (deduplicated across personas)
- {issue} — Options: {A} vs {B} (flagged by: {personas})

## Key Changes
- {bullets}

## Retractions
- {persona / round N: dropped finding, why}
```

Expand each persona's full final report below the table, ordered NEEDS USER INPUT first.

## Hard rules

- **Never** produce a finding without tool output *this round* proving its target.
- **Never** skip the Brief Trace Audit or Repo Reality Audit.
- **Never** carry a prior-round finding forward without re-verifying.
- **Never** accept "the brief implies this," "should be obvious," "standard pattern" as evidence.
- **Never** weaken the plan, brief, or rollout to resolve a finding.
- **Never** mark APPROVED while any finding — at any severity — remains.
- **Always** quote verbatim from plan, brief, and repo when flagging a mismatch.
- **Always** retract prior-round findings explicitly when audits show they were fictional.
- **Always** apply fixes to the file; don't just annotate.
- **Always** prefer dropping an unjustified chunk over inventing a Goal to justify it.

## Edge cases

- **No brief found** at `features/<feature>/brief.md` → CRITICAL. Engineering plan cannot exist without a brief; stop and escalate.
- **Plan is in an old monolithic format** (e.g., `context/plans/049_*.md` rather than `features/<feature>/engineering-plan.md`) → confirm with user whether they want this skill to review-and-port to the new format, or stop. This skill assumes the new structure.
- **Brief and plan disagree on a Goal** → CRITICAL. The brief is canonical; either the plan changes or the user explicitly amends the brief and signs off.
- **Chunk plans don't yet exist for proposed chunks** → expected. Repo Reality Audit on those chunks is limited to architecture-level claims, not file-level. Use the historical-plan reference (if any) for additional cross-checks.
- **Plan references a chunk plan that exists in `implementation/`** → spot-check the chunk plan for consistency with the engineering plan's chunk-index row. Don't full-review it (that's `/plan-review`'s job).
- **Multiple engineering plans across features** in one invocation → out of scope. Run the skill once per feature; engineering plans are feature-scoped and rarely benefit from cross-feature batch review.
- **Decisions log missing** (`features/<feature>/decisions.md`) → MEDIUM finding if the plan has any non-obvious architectural choice without a `Why:` paragraph. The decisions log is recommended but not required by the README.
