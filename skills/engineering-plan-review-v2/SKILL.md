---
name: engineering-plan-review-v2
description: Single-pass review of a feature's engineering-plan.md. Refuses artifacts (engineering plan or upstream brief) in `Status: needs-user-input` state. Gated on `/plan-lint`. Five phases: Round Memory loads prior-round state with plan-growth and section-diff gates; Ground Truth grounds the plan in repo + brief reality and audits decision closure against decisions.md; Persona Prosecution runs personas in parallel with mandatory premise interrogation (repo-state + brief-environment sub-passes); Imagined-Implementer surfaces undecided cross-chunk decisions as IMPLEMENTABILITY_GAP; Orchestrator applies fixes with cross-file authority `decisions.md > brief.md > engineering plan`, runs post-fix premise verification + SAME-ROUND focused re-prosecution on diff hunks (≤1 re-pass; bounded), runs decisions-log-first carry-forward, classifies remaining, renders three-state verdict — CLOSED (shape-correct + decisions bound; unblocks per-chunk plans), APPROVED (shape-correct, decisions undecided), or NEEDS USER INPUT. Sister to /plan-review-v2 (chunk-plan layer).
user-invocable: true
---

# Engineering Plan Review v2 — Staged Single-Pass

Engineering plans sit between the product brief and the per-chunk implementation plans. A bad engineering plan poisons every chunk plan downstream. This skill prosecutes through a Structural Lint gate plus four named phases, no inner loop. If the verdict is `NEEDS USER INPUT`, the user resolves the labeled blockers and re-invokes — that re-invocation is the equivalent of the next round, with explicit human input between passes (the IEEE 1028 review model).

This is the engineering-plan layer. Sister skill `/plan-review-v2` reviews chunk plans. If the user asks for review of a chunk plan, redirect.

## Shared scaffolding

- `~/.claude/skills/_review-common/principles.md` — stance, banned rationalizations, severity/tier, plan style rules
- `~/.claude/skills/_review-common/agent-prompt.md` — persona-agent prompt template
- `~/.claude/skills/_review-common/critical-pairs.md` — active subset for engineering plan review: `P-CLASS-SCOPE, P-FULL-FILE, P-EP-IMPL-DETAIL, P-EP-BRIEF-GOALS, P-EP-VERIFIED-BY, P-EP-RISK-DEPTH, P-EP-DECISION-LOC`
- `~/.claude/skills/_review-common/blocker-classes.md` — blocker registry + verdict gate (three-state verdict: CLOSED / APPROVED / NEEDS USER INPUT)

## Tribunal stance (engineering-plan-specific)

**BRIEF IS CANONICAL (when its premises hold), REPO IS LAW.** Two sources of truth bound this review, with one carve-out:

1. **The brief** (`features/<feature>/brief.md`) is the contract for *what* this feature delivers. Every chunk in the engineering plan must trace back to a Goal, User-facing change, or Supporting infrastructure entry in the Brief Mapping. A chunk that doesn't trace is either evidence of a missing Goal (update the brief) or an unjustified chunk (drop it).

   **Carve-out — brief premises are NOT canonical.** The brief's `## Problem` (or equivalent) section makes load-bearing claims about the operating environment (live users, concurrency, monitoring, SLAs, deployment posture). When those environmental claims contradict project memory / `CLAUDE.md` / source-of-truth files, the brief is solving a phantom problem and the plan inherits the phantom. The brief-environment premise check inside Persona Prosecution interrogates these claims and may file a `brief-environment` RESET that short-circuits the review — see Persona Prosecution below.
2. **The repo** is the contract for *how* the plan can be executed. Architecture claims, file paths, existing patterns, CI workflows, and chunk dependencies must match the branch the plan executes on.

## Usage

```
/engineering-plan-review-v2 <plan-path> [--personas <p1> <p2> ...]
/engineering-plan-review-v2 <feature-name>          # resolves to features/<feature-name>/engineering-plan.md
/engineering-plan-review-v2                          # search features/ for active engineering plans, ask which
```

**Examples:**

```
/engineering-plan-review-v2 author-tmdb-hydration
/engineering-plan-review-v2 features/author-tmdb-hydration/engineering-plan.md
/engineering-plan-review-v2 author-tmdb-hydration --personas architecture ai-development product
/engineering-plan-review-v2
```

## Argument parsing

Split `$ARGUMENTS` on whitespace. Classify each token:

- `--personas` → all subsequent non-path tokens are persona names.
- Token contains `/` or ends with `.md` → plan path.
- Token matches a directory name under `features/` → resolves to `features/<token>/engineering-plan.md`.
- Otherwise → treated as a feature name; if `features/<token>/engineering-plan.md` doesn't exist, stop and report.

No arguments → enumerate `features/*/engineering-plan.md` and list with feature name + brief's `Status:` field. Ask which to review.

## Persona resolution

### Explicit personas
Load each from `personas/{name}.md`. Reviewed by every listed persona in parallel. Missing persona file → stop and report.

### Auto-assignment (no `--personas`)
Default tribunal is **3 personas in parallel**:
- `architecture.md` — cross-cutting design, dependency graph integrity, abstraction boundaries.
- `ai-development.md` — chunk granularity, parallel-execution map, plan structure for AI-implementer consumption.
- `product.md` — brief alignment, scope discipline, non-goals enforcement, user-facing change verification.

If the plan's content strongly skews toward one domain, swap one of these for a domain-specific persona (security, data-engineering, frontend, etc.). Justify the swap in the verdict output.

`ai-development.md` is referenced as supplementary context for every Persona Prosecution agent — even non-`ai-development` personas should know the chunk-discipline rules.

---

## Workflow

```
Status-frontmatter check        (deterministic, hard short-circuit, runs first)
  ↓ Status: needs-user-input on plan or upstream brief → REFUSE; stop
Structural Lint Gate            (deterministic, hard short-circuit)
  ↓ runs /plan-lint; FAIL → emit STRUCTURAL_LINT_FAILED, stop
Round Memory Pass               (deterministic, no LLM judgment)
  ↓ loads ~/.claude/cache/review-state/<feature>.json; computes
  ↓ plan_growth_flag and section_diff_report for round_number > 1
Ground Truth Pass               (deterministic, no LLM judgment)
  ↓ produces audit_report (incl. decision-closure audit with
  ↓ prior-classification consistency check against decisions.md)
Persona Prosecution             (LLM judgment, M parallel agents)
  ↓ produces fix_lists; each persona runs premise interrogation
  ↓ (repo-state + brief-environment sub-passes) + standard prosecution.
  ↓ Round > 1: section_diff + plan_growth gates injected into prompts.
Imagined-Implementer Dry Run    (LLM judgment, 1 agent)
  ↓ produces undecided_decisions (with severity_test) +
  ↓ needed_identifiers + scope_reduction_candidates
Orchestrator Decision           (deterministic + judgment)
  ↓ applies fixes, evaluates RESET corroboration (subclass-aware),
  ↓ auto-retracts unchanged-section findings without (a)+(b) justification,
  ↓ downgrades regression_risk: yes findings, applies cross-file edits to
  ↓ decisions.md / brief.md / engineering plan in authority order,
  ↓ runs post-fix premise verification on rewritten prose,
  ↓ runs SAME-ROUND focused re-prosecution on diff hunks (≤1 re-pass) when
  ↓   any of: orchestrator fixes > 0, cross-file edits > 0, falsified > 0,
  ↓ runs carry-forward consultation Priority 1 (decisions.md) then
  ↓   Priority 2 (recently_resolved_blockers), classifies remaining,
  ↓ renders three-state verdict + persists state file for next round
```

There is no inner loop. If the verdict is `APPROVED` (shape-correct but cross-chunk decisions remain undecided), per-chunk plan writing is NOT yet unblocked — the user resolves the open decisions in the engineering plan and re-invokes to seek `CLOSED`. Only `CLOSED` unblocks per-chunk plan writing.

---

## Status-frontmatter check (MANDATORY, HARD SHORT-CIRCUIT, RUNS BEFORE STRUCTURAL LINT)

`Read` the engineering plan's YAML frontmatter. Extract the `Status:` value.

`Status:` is a binary mid-cycle signal: `needs-user-input` (mid-cycle) or absent (ready). Lifecycle signals (Frozen, Archived) come from git/PR state, not frontmatter.

- **`Status: needs-user-input`** → stop. Do NOT spawn the Structural Lint Gate or anything after. The artifact is mid-cycle by design (the partial draft was written by `/engineering-plan-author` with a `## Pending blockers` section appended; the user is between resolving blockers and re-invoking the author skill). Emit:

  ```
  STATUS: REFUSED (artifact in mid-cycle authoring state)

  This engineering plan has frontmatter `Status: needs-user-input`. The author skill
  (`/engineering-plan-author`) wrote it as a partial draft with unresolved blockers
  listed in the `## Pending blockers` section at the end of the file. Reviewing a
  partial draft would re-prosecute issues the author already surfaced.

  Resolve the blockers listed in `## Pending blockers`, then re-invoke
  `/engineering-plan-author --rewrite <feature>`. The author skill removes the `Status:`
  frontmatter on a successful CLOSED or APPROVED emission; re-invoke
  `/engineering-plan-review-v2` once the plan is back to no-Status-field state.
  ```

- **No `Status:` field, OR any other value** → proceed normally. The Round Memory Pass consults the engineering-plan-author sidecar at `~/.claude/cache/author-state/<feature>__engineering-plan.json`; if `authoring_mode: "draft"` is set there (the plan was written via `/engineering-plan-author --draft`, skipping Plan-lint, Concern-lint, Ground-truth, Self-prosecution, and Imagined-Implementer), the verdict surfaces a draft warning. Persona prosecution still runs.

The check is deterministic and runs before any LLM judgment or shell invocation. A `Status: needs-user-input` artifact never reaches the Structural Lint Gate.

Also `Read` the upstream brief (`features/<feature>/brief.md`) and apply the same check: a `Status: needs-user-input` brief means the upstream is mid-cycle, and the engineering plan derived from it cannot be reviewed cleanly until the brief is hardened. Refuse with the same template, redirected at `/brief-author --rewrite <feature>`.

## Structural Lint Gate (MANDATORY, HARD SHORT-CIRCUIT)

```bash
python3 ~/.claude/skills/plan-lint/lint.py features/<feature>/
```

Catches dependency cycles, unknown-slug deps, "and"-chunks, vague exit criteria, premature abstractions, position-encoded slugs, and unresolved Decisions Closure rows. File-level ownership across chunks is the chunk plan's responsibility — engineering-plan-layer ownership maps were removed by design (chunks are written just-in-time when filenames are knowable).

**Behavior:**

- **Exit 0:** record `lint_clean=true` and proceed to Ground Truth Pass. Per-chunk plans are written just-in-time, so `chunk-plan-missing` WARNs are normal and do not block.
- **Exit 1 (lint FAILED):** stop. Emit:

  ```
  STATUS: NEEDS USER INPUT (blocker: STRUCTURAL_LINT_FAILED)

  /plan-lint found N structural defects. Persona prosecution is not run because
  LLM judgment on top of a structurally-broken plan produces noise.

  <verbatim /plan-lint output>

  Fix the structural defects above and re-invoke /engineering-plan-review-v2.
  ```

- **Exit 2 (usage / IO error):** stop and report.

---

## Round Memory Pass (MANDATORY, NO LLM JUDGMENT)

This pass exists to break two thrash patterns documented in prior runs:

1. **Prosecution of remediation artifacts** — the plan grows each round as the user binds previously-flagged decisions, and the next round files findings against the newly-added text.
2. **Re-litigation of unchanged sections** — personas re-read the whole plan each round and surface "new" findings on text that was reviewed and accepted in the prior round.

Both are mitigated by carrying state across invocations.

### State file location

State lives at `~/.claude/cache/review-state/<feature-slug>.json` (NOT in the project; survives worktrees; never committed). The slug is the basename of the feature directory (`features/<feature-slug>/`). Create the parent directory with `mkdir -p ~/.claude/cache/review-state` if missing.

### State file schema

```json
{
  "feature_slug": "<slug>",
  "last_review_at": "<ISO 8601 UTC>",
  "last_verdict": "CLOSED | APPROVED | NEEDS_USER_INPUT",
  "last_plan_word_count": <integer>,
  "last_plan_sha256": "<hex>",
  "section_hashes": {
    "<section heading>": "<sha256 of section body, body only excluding heading>"
  },
  "round_number": <integer, 1-indexed>,
  "prior_blockers": [
    {
      "blocker_class": "BRIEF_AMENDMENT_NEEDED | STABLE_DISAGREEMENT | OPEN_QUESTION | IMPLEMENTABILITY_GAP | UNCORROBORATED_RESET | FIX_INTRODUCED_PREMISE_INVERSION",
      "path_or_section": "<plan section heading or file:line>",
      "summary": "<one-line>",
      "raised_in_round": <integer>,
      "current_reclassification_justification": "<one-sentence repo-state justification when this blocker is being re-raised after prior resolution; absent on first appearance>"
    }
  ],
  "recently_resolved_blockers": [
    {
      "blocker_class_when_resolved": "<class | RESOLVED>",
      "path_or_section": "<plan section heading or file:line>",
      "summary": "<one-line>",
      "resolved_in_round": <integer>,
      "user_decision": "<one-sentence rationale; see capture priority below>",
      "carry_forward_until_round": <integer; defaults to resolved_in_round + 2>
    }
  ]
}
```

**Backward-compat note.** Treat absence of `prior_blockers` and `recently_resolved_blockers` as `[]` when reading. The legacy field `prior_blockers_resolved_by_user` (if present) is migrated on first read into `recently_resolved_blockers`: preserve `summary` and `resolved_in_round`; default `blocker_class_when_resolved` to the migrated `blocker_class`; default `path_or_section` to `"(legacy entry — no path recorded)"`; default `user_decision` to `"No rationale recorded (legacy entry)"`; default `carry_forward_until_round` to `resolved_in_round + 2`. Drop the legacy field after migration.

### Load prior state

`Read` the state file. If it does not exist:
- Set `round_number = 1`. No prior state. Skip the plan-growth and section-diff sub-passes; proceed to Ground Truth.
- If it exists, set `round_number = <stored> + 1`.

### Plan-growth check (gate for Persona Prosecution)

Compute current plan word count (`wc -w features/<feature>/engineering-plan.md`). Compare to `last_plan_word_count`.

- **Growth ≤ 20%** → no marker; persona prosecution proceeds normally.
- **Growth > 20%** → set `plan_growth_flag: true`. Persona Prosecution agent prompts MUST be prepended with:

  > **Plan grew {N}% since last review ({old_words} → {new_words} words).** Findings against text added since the last review are likely *responses to prior-round blockers*. Tag each finding `regression_risk: yes | no` based on whether the cited text overlaps with sections marked `<!-- round-N addition -->` or sections whose hash differs from `section_hashes` in the state file. Findings tagged `regression_risk: yes` will have severity downgraded one tier (CRITICAL → HIGH → MEDIUM → LOW) by the orchestrator unless you can name a *specific failure mode the added text creates* (not just "the added text is imprecise"). The orchestrator applies the downgrade mechanically; your job is to file the tag honestly.

### Section-diff for re-invocations (gate for Persona Prosecution)

If `round_number > 1`, build a section-level diff:

1. Parse the engineering plan into sections by `## ` and `### ` headings (level 2 and 3). For each section, hash the body (excluding the heading line).
2. Compare each current section hash to `section_hashes[heading]`:
   - **Heading present in prior, hash unchanged** → section is `unchanged`.
   - **Heading present in prior, hash differs** → section is `modified`.
   - **Heading not in prior** → section is `added`.
   - **Heading in prior but not in current** → section is `removed` (informational only; no persona action needed).
3. Emit a `section_diff_report`:

   ```
   ### Section diff (round N → N+1)
   unchanged: [<heading>, ...]
   modified: [<heading>, ...]
   added: [<heading>, ...]
   removed: [<heading>, ...]
   ```

Persona Prosecution agent prompts on `round_number > 1` MUST be prepended with:

> **This is round {N} of review. The following sections are UNCHANGED since round {N-1}:** `{unchanged headings}`. **These sections were prosecuted and accepted last round.** You may file findings against them only if you can name (a) a specific defect that prior personas missed AND (b) why the prior round's lens did not catch it (new persona type? new evidence? cross-section interaction surfaced by the modified sections?). Findings against unchanged sections without both (a) and (b) are auto-retracted by the orchestrator. Sections marked `modified` and `added` get full prosecution latitude.

This is the **diff-based prosecution gate**. It does NOT blind personas to unchanged sections — they still read them for context — but it raises the bar for filing new findings against text that previously passed review.

### Persist on exit

At the end of the Orchestrator Decision phase (after verdict rendering), update the state file with the new round's data:

- `last_review_at` ← current UTC timestamp
- `last_verdict` ← rendered verdict
- `last_plan_word_count` ← current word count
- `last_plan_sha256` ← sha256 of full plan file
- `section_hashes` ← rebuilt from current plan
- `round_number` ← incremented
- `prior_blockers` ← rebuilt from the current verdict's blockers (open at this round's exit)
- `recently_resolved_blockers` ← extended: prior round's blockers that no longer appear in the current verdict become entries, with `user_decision` populated per the capture priority below; existing entries with `carry_forward_until_round < new round_number` are dropped

Write the file. If verdict is `CLOSED`, leave the state file in place — a future invocation against the same feature (e.g., after a brief amendment) will see `round_number` as the next integer and apply the gates correctly.

### Capture priority for `user_decision`

When recording a resolved blocker, populate `user_decision` from these sources in priority order. Stop at the first one that yields a non-empty rationale:

1. **User text in the current invocation `$ARGUMENTS`** — e.g., re-invocation phrased "round 3, withdrew chunk 8 because cross-grep guard moved to chunk 6"
2. **Plan diff to the prior section** — if the section's hash changed since `last_plan_sha256` and the diff is small (≤200 chars added text), the diff IS the rationale; record it verbatim
3. **`features/<feature>/decisions.md` entry** added since `last_review_at` whose subject matches the blocker's `path_or_section` (use the entry's `Why:` paragraph)
4. **Commit message body** since `last_review_at` (use `git log <last_review_sha>..HEAD --format=%B` if commits exist between rounds)
5. **Commit message subject** as fallback
6. **`"No rationale recorded"`** if none of the above yields a rationale

Cap captured rationale at ~200 chars. Truncate with `…` if longer.

### Edge case — manual reset

If the user wants to discard prior-round memory (e.g., after a major plan rewrite), they delete `~/.claude/cache/review-state/<feature-slug>.json` manually. The skill does NOT auto-detect "the plan was rewritten" because that judgment can be wrong; explicit deletion is the safe lever.

---

## Ground Truth Pass (MANDATORY, NO LLM JUDGMENT)

Five sub-passes in order: Brief Trace, Repo Reality, Structural Lint (style), Decision-Closure Audit, Mechanical Fixes. Persona Prosecution agents MUST NOT re-prosecute facts verified here.

### Brief Trace (mechanical)

Open `features/<feature>/brief.md` and the engineering plan's Brief Mapping section. Build:

```
### Brief Trace

Brief Goals listed: <count> [verbatim list]
Brief User-facing changes listed: <count> [verbatim list]
Brief Non-goals listed: <count> [verbatim list]

Goal → chunks mapping (per Brief Mapping):
- "<verbatim Goal>" → chunks {`slug-a`, `slug-b`, ...}
- "<...>" → ❌ NO CHUNKS LISTED  [HARD: undelivered Goal]

User-facing change → chunks + verifier:
- "<verbatim change>" → delivered by {`slug-a`}, verified by {`slug-x` / "Manual review"}
- "<...>" → ❌ MISSING `Verified by` ENTRY  [HARD: untraced user-facing change]

Chunks in chunk index: <count> [verbatim list]
Chunks appearing in Brief Mapping (Goals, User-facing, or Supporting infrastructure):
- `schema-migration`, `cascade-rewrite`, ... ✓
- `legacy-shim-cleanup` ❌ NO MAPPING  [HARD: unjustified chunk]

Brief Non-goals → enforcement check:
- "<verbatim non-goal>" → enforced by: <plan section / chunk> / ❌ NOT ENFORCED  [SOFT: HIGH]

Drift detected:
- Plan claims user-facing behavior X. Brief does not list X.  [SOFT: HIGH — scope creep or missing brief Goal]
- Brief lists Goal Y. Plan does not deliver Y.                [HARD: undelivered Goal]
```

### Repo Reality (mechanical)

- **Tree:** `ls` repo root.
- **Cited file paths:** for every file path in Architecture Summary, `ls` it.
- **Pattern claims:** for every "matches existing X" / "extends Y" / "reuses Z" claim, grep for the anchor and verify.
- **CI workflows:** `ls .github/workflows/`. If the plan claims a job is added/changed, `Read` the workflow and verify.
- **Chunk-index `Code deps`:** for any chunk whose deps reference an earlier chunk, verify the earlier chunk's claimed exports/file boundaries exist on `main` (if shipped) or are coherently scoped.
- **Cross-chunk file boundaries:** for each pair of chunks claimed parallel, infer file sets from the chunk plan if it exists or from the engineering plan's chunk description if not. Any file in both → `[HARD: false parallelism]`.

Output a `Repo Reality` block with architecture claims (VERIFIED/MISSING/MISMATCH + evidence), CI workflow claims, chunk-index `Code deps` checks, false-parallelism check.

### Structural Lint (style supplements the Gate)

The template at `features/_template/engineering-plan.md` is the source of truth for shape. Apply these regex/structural checks; each failure is `[HARD: structural defect]`:

**Required sections present, in order:**
1. Brief mapping
2. Architecture summary
3. Invariants *(optional)*
4. Other domain contracts *(optional)*
5. Chunk index
6. Manual gates *(optional)*
7. Dependency graph
8. Risks / unknowns
9. Rollout plan *(conditionally required: prod state changes / migrations / flags)*
10. Out of scope

**Required headers:**
- Header with `**Brief:**` link (and `**Decisions:**` link when `decisions.md` exists)
- Brief Mapping has `### Goals`, `### User-facing changes`, `### Non-goals enforcement` subsections
- User-facing changes table has a `Verified by` column

**Chunk index column rules:**
- Columns are EXACTLY `Slug | Chunk | Code deps`. Any of `#`, `Status`, `PR`, `Mode`, `Owner`, `Last-updated` is `[HARD]`.
- Slugs are kebab-case, 2–4 words. Numbered identifiers (`phase-N-*`, `step-N-*`, `wave-N-*`, `chunk-NN`, `01a/01b`, `Phase 2.b`) are `[HARD]` per occurrence.
- Chunk names are 6–10 words, plain English. No `(WIP)` / `(stretch)` / `(if time)`.
- `Code deps` cell is comma-separated chunk slugs or `—`. Manual-gate dependencies in this cell → `[HARD]`.

**Dependency graph:**
- Explicit DAG present (text or diagram), even for linear deps.
- Every chunk's `Code deps` matches the graph.
- Operator-executed runs (`--apply`, prod runs) appear in Manual gates or rollout plan.

**Rollout plan (when present):**
- Feature flag named (or N/A with reason).
- Migration order explicit (or N/A with reason).
- Monitoring/observability named.
- Rollback path named for every irreversible step.

**Forbidden patterns:**
- Status / PR / Mode / Owner / Last-updated columns → HARD
- Numbered chunk identifiers (`01`, `27a`, `chunks 22+23+24+26`) → HARD
- "Open questions" section → HARD (open questions belong in the brief)
- "Decisions resolved" section in plan body → HARD
- Hedging future tense (`we will likely`, `this plan aims to`, `the team should consider`) → SOFT MEDIUM
- Meta-commentary (`this section…`, `below we'll cover…`) → SOFT MEDIUM
- Emojis, exclamation marks → SOFT LOW

### Decision-Closure Audit (mechanical, judgment-classified)

Engineering plans thrash when cross-chunk-wiring decisions get deferred to per-chunk plans under language like "mechanism is pinned in the orchestrator's per-chunk plan", "exact predicate is pinned at chunk-plan time", "TBD per per-chunk plan". A cross-chunk-wiring decision deferred this way is silent breakage: multiple chunk plans then need it but none can make it unilaterally.

**Enumerate deferrals.** Scan the plan body (skip Brief Mapping and Out of scope) for every occurrence of:

- `is pinned in the .* per-chunk plan`
- `pinned in .* chunk plan`
- `pinned at chunk-plan time`
- `mechanism .* (is|to be) pinned`
- `exact .* (is|to be) pinned`
- `(option|mechanism) \([A-Z]\) (or|,)` — multi-option deferrals
- `TBD\b`, `to be determined`, `to be decided`
- `deferred to .* per-chunk plan`
- `mechanism-choice deferred`

Record `{section_heading, line_range, verbatim_quote, surrounding_paragraph}` per hit.

**Classify each deferral.**

- **`cross-chunk-wiring`** — names or implicates a schema column, resolver predicate, transaction position, event name/payload shape, file path of a shared module read/written by 2+ chunks, cross-chunk interface or contract, manual-gate verification mechanism, rollback path, or feature-flag wiring. Heuristic: if the answer has to be the same across two or more chunks, it's cross-chunk-wiring.
- **`chunk-internal`** — names a test name, single-file function name, internal phase split within one chunk, files-to-create scoped to one chunk, exact log string, SQL query, regex pattern, internal organization. Legitimately deferred per critical-pair policy.
- **`brief-layer`** — names a residual gap, accepted user-facing tradeoff, scoped non-goal, scope expansion, or product-shape decision. Belongs in `brief.md`.
- **`unclear`** — topic cannot be classified mechanically with confidence.

**Prior-classification consistency check (MANDATORY).**

Before emitting findings, `Read` `features/<feature>/decisions.md` if it exists. For every deferral classified `cross-chunk-wiring` or `brief-layer` in the previous step, search `decisions.md` for prior entries naming the same surface (heuristics: matching identifier name, matching section heading, matching verbatim phrase fragment ≥4 words).

If a prior `decisions.md` entry is found AND it bound the surface to a different classification (e.g., previously declared `chunk-internal` and now being flagged `cross-chunk-wiring`, or vice-versa), the current classification is a **reclassification**.

Reclassifications must include a one-sentence justification grounded in repo state that changed since the prior entry (new file added, new dependency, schema migration, brief amendment) — NOT just "on re-reading I see this is cross-chunk." Without a justification:

- The HARD classification is **downgraded to `OPEN_QUESTION`** ("classification differs from prior round; user must arbitrate"). The user picks which classification stands.
- Record `prior_classification: <old>; current_classification: <new>; justification: <none | one sentence>` in the finding.

This step exists because round-N may classify a deferral cross-chunk-wiring (forcing the user to bind it in the engineering plan), and round-N+1 may then re-classify the same deferral chunk-internal (forcing the user to *delete* the binding they just added). The `decisions.md` log is the project's converged memory; the audit must consult it before re-prosecuting.

If `decisions.md` does not exist or contains no matching entry, no consistency check applies — proceed to emit findings normally.

**Emit findings.**

- `cross-chunk-wiring` (no prior conflicting classification) → `[HARD: cross-chunk decision deferred]`. Include verbatim quote and named cross-chunk surface.
- `cross-chunk-wiring` (reclassification without justification) → `[OPEN_QUESTION: classification differs from prior round]`. Surface the prior entry verbatim.
- `brief-layer` (no prior conflicting classification) → `[HARD: brief-layer decision in plan body]`. Include verbatim quote.
- `brief-layer` (reclassification without justification) → `[OPEN_QUESTION: classification differs from prior round]`.
- `chunk-internal` → no finding (legitimate deferral).
- `unclear` → pass to Persona Prosecution as `decision_classification_unclear`. Personas applying the classification must ALSO consult `decisions.md` and follow the same consistency rule.

Output:

```
### Decision Closure

Deferrals enumerated: <count>

Cross-chunk-wiring (HARD):
- {section}: "{verbatim_quote}" — names {cross-chunk surface}; classified cross-chunk-wiring because {reason}.

Brief-layer (HARD):
- {section}: "{verbatim_quote}" — implicates {residual gap / scope decision}; belongs in brief.md.

Chunk-internal (acceptable):
- {section}: "{verbatim_quote}" — scoped to {chunk slug}; legitimate deferral.

Unclear (passed to Persona Prosecution):
- {section}: "{verbatim_quote}" — ambiguous topic; persona judgment requested.
```

This sub-pass does not auto-fix — fixes require persona judgment about which decision the plan should actually make.

### Mechanical Fixes (auto-apply)

Apply unambiguous fixes immediately, before Persona Prosecution:
- Hallucinated path → if a verified path exists with similar name (typo, casing), replace.
- Forbidden columns in chunk index → strip them.
- Style-class regex hits → fix in place (tense, banned phrases, emojis).
- Emit a `Mechanical fixes applied:` bullet list in the audit report.

Findings that survive Mechanical Fixes (Brief Trace HARDs, Repo Reality HARDs, structural HARDs that can't auto-fix, decision-closure HARDs) are passed to Persona Prosecution as `pre_resolved_hard_findings`.

### Ground Truth output (audit_report)

Bulleted facts list (not verbose YAML):
- brief_trace: goals, user_facing_changes, non_goals, drift, hard_findings (undelivered Goals, untraced changes, unjustified chunks)
- repo_reality: architecture_claims (claim + status + evidence), ci_claims, code_deps, false_parallelism, hard_findings
- structural_lint: sections_present, column_check, forbidden_pattern_hits, hard_findings, soft_findings
- decision_closure: deferrals_total, cross_chunk_wiring, brief_layer, chunk_internal, unclear, hard_findings
- mechanical_fixes_applied
- pre_resolved_hard_findings

---

## Persona Prosecution (parallel agents, fix-list output)

Resolve personas (auto or explicit). Launch one Agent per persona **in parallel in a single message**.

### Spawn agents

Use the template in `~/.claude/skills/_review-common/agent-prompt.md`. Substitute:

- `{persona_name}` — the persona being prosecuted as
- `{audit_report_bullets}` — Ground Truth audit (compact bullets)
- `{pre_resolved_hard_findings}` — anything Ground Truth already raised
- `{active_critical_pair_subset}` — `P-CLASS-SCOPE, P-FULL-FILE, P-EP-IMPL-DETAIL, P-EP-BRIEF-GOALS, P-EP-VERIFIED-BY, P-EP-RISK-DEPTH, P-EP-DECISION-LOC`
- `{target_locator}` — engineering plan path
- `{how_to_get_it}` — `Read features/<feature>/engineering-plan.md`, `Read features/<feature>/brief.md`, `Read features/<feature>/decisions.md` (if exists)
- `{pr_description_or_brief_mapping}` — pointer to the brief; agents Read on demand
- `{skill_specific_extensions}` — see "Premise Interrogation pass" + "decision_classification_unclear handling" + "round-memory injection" below
- `{skill_specific_preamble}` — `premise_interrogation: passed | reset_findings_filed`; `round_number: <N>`
- `{skill_specific_resets_block}` — see RESET schema below

If `round_number > 1`, also prepend the section_diff_report from Round Memory and the plan-growth banner (if `plan_growth_flag: true`) to the persona's prompt body, before the `## Your task` section. These are the gate text from the Round Memory plan-growth and section-diff sub-passes verbatim — do not paraphrase. Personas must include `regression_risk: yes | no` on every finding when `plan_growth_flag` is set, and must include `targets_unchanged_section: yes | no` on every finding when `round_number > 1`. The orchestrator uses these tags to apply mechanical filters.

The plan and brief are passed by *path*; agents Read them. The persona file is referenced by path; agents Read what their persona needs.

### Skill-specific extensions (substituted into the agent prompt)

> Your work is two passes done in order: **premise interrogation** first, then standard prosecution.
>
> ### Premise interrogation (mandatory — runs before standard prosecution)
>
> Plans thrash hardest when they solve imaginary problems — when a load-bearing claim about *the current state of the system OR about the operating environment the brief assumes* is wrong. Your job in this pass is to falsify those claims before generating any other findings. The pass has two sub-passes: **repo-state premises** (in the plan) and **brief-environment premises** (in the brief).
>
> #### Repo-state premise check (engineering-plan claims)
>
> 1. Enumerate every load-bearing claim the plan makes about *current system state* — claims of the form "X currently does Y", "the existing path is Z", "today this re-fires after N seconds", "the predicate at file:line is X", "books are not yet enriched", "the resolver returns X under condition Y", "this column is currently NULL for cohort C". Skip claims about future state ("will write", "after `--apply`") and brief-Goals (interrogated in the brief-environment premise check below).
>
> 2. For each claim, run a verification: `Read` the cited file at the cited line; `rg` for the cited identifier; `git log -p` if the claim is about recent state. Ground Truth verified *paths exist*; you are verifying *behavior at those paths matches the claim*. Different checks.
>
> 3. A claim that does not survive verification is a **premise inversion** of subclass `repo-state`. File at severity **`RESET`** at the top of your output, in the `resets:` block (schema below). Mark `subclass: repo-state`.
>
> 4. Be calibrated. A premise inversion is "the plan claims `STALENESS_THRESHOLD_MS = 7d` causes re-fire on cohort Persons; the predicate I just read at the cited line in fact only re-fires when X also holds, so the claimed regression doesn't exist." It is NOT "the plan's tone is too pessimistic."
>
> #### Brief-environment premise check (the brief's stated problem)
>
> The brief is canonical for *what* the feature delivers, but the brief's `## Problem` (or equivalent problem-statement) section makes claims about the **operating environment** — claims like "users currently experience X", "the production system today does Y", "concurrent processes contend on Z", "operators need observability for W". When the operating environment described in the brief doesn't match reality, the entire engineering plan is solving the wrong problem and per-finding remediation produces a structurally-correct plan that still over-engineers a non-existent problem.
>
> 1. Read `features/<feature>/brief.md`. Locate the problem statement (typically `## Problem`, `## Background`, or `## Why`).
>
> 2. Enumerate every load-bearing **environmental claim** — claims about live users, production traffic, concurrent operators, existing monitoring, current SLAs, established workflows, deployed integrations. Skip claims about *what the feature will deliver* (those are Goals, not premises).
>
> 3. For each environmental claim, verify against ground truth available *to you in this invocation*: `CLAUDE.md` (project memory often documents real operating-environment facts like "no live users yet", "single-operator dev", "no production deploy", "no concurrent writers"), repo state (number of deployed environments, existence of monitoring config, presence of alerting wiring), and explicit project facts in the audit_report. If `CLAUDE.md` or memory contradicts a brief environmental claim, that contradiction IS the falsification.
>
> 4. A brief environmental claim that does not survive verification is a **premise inversion** of subclass `brief-environment`. File at severity **`RESET`** with `subclass: brief-environment`. The fix is not to edit the brief silently — it is to flag the mismatch so the user re-scopes both brief and plan.
>
> 5. Be calibrated. A brief-environment RESET is "the brief assumes 'live users may observe partial state during cascade rewrites, requiring atomic transactions per author' but `CLAUDE.md` records 'NO existing users yet — App has NOT been given to anyone'; the per-author atomicity machinery solves a non-existent observation hazard." It is NOT "the brief's prose is alarmist" or "the brief could be tighter." If you cannot name a specific environmental claim and a specific contradicting ground-truth source, do not file.
>
> #### RESETs block schema (both sub-passes)
>
> ```
> resets:
>   - id: r1
>     subclass: repo-state | brief-environment
>     section: {brief or plan section heading}
>     plan_claim: "{verbatim quote}"
>     verification: {what you ran — file:line read / grep query / CLAUDE.md citation}
>     actual_state: "{verbatim quote from repo or memory of what is actually true}"
>     implication: {one sentence on what the plan/feature was solving that doesn't need to be solved}
> ```
>
> 6. If after honest interrogation no premises invert, output `premise_interrogation: passed` and proceed to standard prosecution. Do not invent RESET findings.
>
> A `repo-state` RESET short-circuits the review *only* if at least two of three personas file corroborating RESET findings on the same plan span. A single-persona repo-state RESET becomes a CRITICAL HARD finding the orchestrator weighs but does not auto-escalate.
>
> A `brief-environment` RESET has a **lower corroboration bar**: a single-persona brief-environment RESET that cites a verbatim contradicting line from `CLAUDE.md` / project memory / source-of-truth file is treated as corroborated (the "second persona" is the project memory itself). One persona + one verbatim project-memory citation = corroboration. Two personas filing brief-environment RESETs on the same brief claim is also corroboration. Anything less is reclassified as `UNCORROBORATED_RESET` per the universal rule.
>
> The corroboration gates are enforced in the Orchestrator Decision phase — file your honest RESETs whether or not you expect corroboration.
>
> ### Standard prosecution
>
> Imagine implementing this plan from a cold start. What second-order issues surface during execution that the plan does not address? What scenario can you construct where executing wave N verbatim leaves wave N+1 unable to start? What `--apply` step runs against an inconsistent state because a precondition is missing?
>
> **`decision_classification_unclear` items.** Ground Truth may pass you deferral findings classified as `unclear`. You have brief and plan in scope; render judgment. If you judge a deferral cross-chunk-wiring or brief-layer, file the corresponding HARD finding. If chunk-internal, file no finding.
>
> Severity additions for engineering plans:
> - **RESET**: a load-bearing premise about current system state is false. In the `resets:` block, NOT in `findings:`.
> - CRITICAL: plan will fail mid-execution, leave a half-shipped feature, or corrupt prod state.
> - HIGH: significant correctness or rollout-safety risk.

---

## Imagined-Implementer Dry Run

Convergence-forces the plan into a state where it is *implementable as written*. Runs after Persona Prosecution by spawning one foreground Agent. Output gates the `CLOSED` verdict.

The premise: the engineering plan is a contract for an implementer who will read only this plan plus the brief and start writing the next chunk plan from a cold start. If after reading those two documents the implementer has to make cross-chunk-wiring decisions herself, the engineering plan is incomplete.

### Agent prompt

> You are simulating an implementer about to write the per-chunk plan for the next dep-free chunk in the chunk index. You have read **only** this engineering plan and its brief. You have NOT read prior reviews, decisions logs, or this conversation's history. You will not write the per-chunk plan now — only enumerate what the engineering plan provides and what it leaves you to decide yourself.
>
> Read `features/<feature>/brief.md` and `features/<feature>/engineering-plan.md`.
>
> Pick the next dep-free chunk in the chunk index that has not yet shipped (deps `—` or all deps shipped on `main`). Imagine starting its per-chunk plan now, from a cold read.
>
> Produce three lists:
>
> **List A — `needed_identifiers`**: every cross-chunk-shared identifier you would need to know to begin implementation. Includes column names, function names, file paths of shared modules, event names and payload shapes, feature-flag names, manual-gate verification mechanisms, transaction-write positions, predicate amendments to existing resolvers. For each identifier: (a) is it specified concretely in the engineering plan? (b) if not, can you infer it unambiguously from plan + brief alone? (c) if not, is it the kind of thing more than one chunk depends on getting right?
>
> **List B — `undecided_decisions`**: every cross-chunk-wiring decision you would have to make yourself because the plan does not make it. Each entry MUST satisfy two falsifiability tests, and you MUST attempt to write each test before filing — if you can't write either, the decision does not belong on this list:
>
>   - **`severity_test` (mandatory)**: a single concrete sentence describing a scenario where two chunk plans implementing this feature in *parallel* (without coordinating with each other) reach incompatible answers. Format: "If chunk `<slug-A>` implementer chooses `<answer-A>` and chunk `<slug-B>` implementer chooses `<answer-B>`, the resulting code breaks at `<specific surface>` because `<reason>`." If you can't name a parallel-implementation incompatibility, the decision is chunk-internal — do not file it here.
>   - **`affected_chunks` ≥ 2** (mandatory): the decision must be needed by 2+ chunks. A decision affecting only one chunk is chunk-internal regardless of how it sounds.
>
> Items that fail either test are reported under `informational_decisions` (not List B) and do NOT produce IMPLEMENTABILITY_GAP findings. Be calibrated. A decision genuinely chunk-internal (test names, internal phase split, log line content, single-file function organization) does not go in any list. A decision the plan makes implicitly via cross-chunk contracts (column name written in one chunk's transaction tail and read by another chunk's resolver predicate, both named in the plan) is *made*, not undecided.
>
> **List C — `scope_reduction_candidates`**: any chunk where ≥3 entries on List A (`status: undecided`) AND/OR List B point at that chunk. The interpretation: rather than binding this many decisions, the user may prefer to *drop the chunk* and re-scope the feature to not require it. For each candidate: (a) chunk slug; (b) count of undecided items pointing here; (c) one-sentence "what the feature loses if this chunk is dropped" — phrased as a tradeoff, not advocacy.
>
> ## Output
>
> ```
> next_chunk_chosen: {slug}
> next_chunk_rationale: {one sentence}
>
> needed_identifiers:
>   - identifier: {name}
>     surface: column | function | file_path | event | flag | gate | transaction_position | predicate | other
>     status: specified | inferable | undecided
>     plan_reference: {section / line, or "not present"}
>     rationale: {one sentence}
>
> undecided_decisions:
>   - decision: {one-sentence description}
>     affected_chunks: [{slug}, {slug}, ...]    # MUST have ≥2 entries
>     severity_test: "If chunk {A} implementer chooses {X} and chunk {B} implementer chooses {Y}, the resulting code breaks at {surface} because {reason}."
>     deferral_language: "{verbatim quote, or 'not addressed'}"
>     why_cross_chunk: {one sentence}
>
> informational_decisions:
>   - decision: {one-sentence description}
>     fail_reason: severity_test_unwritable | affected_chunks_<2 | chunk_internal_after_re_read
>     note: {one sentence}
>
> scope_reduction_candidates:
>   - chunk: {slug}
>     undecided_count: {integer ≥3}
>     tradeoff: "Dropping this chunk means the feature loses {capability}; the brief Goal {goal-id} is {still-met-via-X | partially-unmet | unmet}."
>
> verdict: implementable | not_implementable
> rationale: {one paragraph}
> ```
>
> Verdict rules:
> - `implementable` requires: `undecided_decisions` empty AND zero `needed_identifiers` with `status: undecided`. Items in `informational_decisions` do NOT block `implementable`.
> - `not_implementable` requires: at least one entry on `undecided_decisions` (which means it survived BOTH the `severity_test` and `affected_chunks ≥ 2` filters) OR at least one `needed_identifiers` with `status: undecided`.
>
> Be honest — surface gaps, don't perform completion theater. But also: if you cannot write a `severity_test` that names a real parallel-implementation incompatibility, do NOT file the decision as undecided just to look thorough. Honesty cuts both ways: false positives waste user rounds the same way false negatives ship broken plans.

---

## Orchestrator Decision

Runs in the main thread. Sub-passes in order: RESET Corroboration Check, Apply Mechanical-Fix Carry-Over, Filter Against Critical-Pair Policies, Fold In Implementability Findings, Detect Cross-Persona Disagreement, Consolidate Non-Conflicting Fixes, Classify Remaining Findings, Render Verdict.

### RESET Corroboration Check

Collect every `resets:` block from every Persona Prosecution agent. Group by plan span (section heading or overlapping line range) AND by `subclass`. The two subclasses have different corroboration thresholds.

#### `repo-state` subclass

- **Two or more personas filed corroborating `repo-state` RESETs on the same span** → premise-inversion short-circuit. Stop. Output `NEEDS USER INPUT: premise inversion (repo-state)`. Do NOT apply any Persona Prosecution fixes. Surface every corroborated RESET verbatim. User re-scopes the plan body for affected sections and re-invokes.
- **Single-persona `repo-state` RESET (no corroboration)** → reclassify as CRITICAL HARD `UNCORROBORATED_RESET` blocker. Note in verdict.

#### `brief-environment` subclass

This subclass has a lower corroboration bar because the second corroborating "voice" can be a project-memory or source-of-truth file rather than a second persona.

- **Single-persona `brief-environment` RESET WITH a verbatim citation from `CLAUDE.md` / project memory / source-of-truth file** that directly contradicts the brief's claim → **corroborated** (project memory acts as the second voice). Short-circuit fires. Output `NEEDS USER INPUT: premise inversion (brief-environment)` with both the persona quote and the contradicting memory/CLAUDE.md citation. The user must reframe the brief's problem statement before any chunk-level remediation is meaningful.
- **Two or more personas filed corroborating `brief-environment` RESETs on the same brief claim** → corroborated. Same short-circuit.
- **Single-persona `brief-environment` RESET WITHOUT a contradicting source-of-truth citation** → reclassify as CRITICAL HARD `UNCORROBORATED_RESET`. The persona's claim is preserved verbatim in the verdict for user judgment.

#### Zero RESETs filed

Proceed.

The corroboration gates exist because premise interrogation is a single-persona cognitive mode prone to false positives. The asymmetric bar for `brief-environment` reflects that load-bearing operating-environment facts ARE typically encoded in `CLAUDE.md` / project memory — those files are the project's already-converged second voice. The asymmetric bar for `repo-state` requires two independent personas because no single committed file is authoritative on dynamic system behavior.

If short-circuit fires, stop here.

### Apply Mechanical-Fix Carry-Over

Already done at end of Ground Truth. Confirm file matches.

### Filter Against Round-Memory Tags (round_number > 1 only)

Apply BEFORE critical-pair filtering. Findings carry two tags from Persona Prosecution:

1. **`targets_unchanged_section: yes`** — finding's `path_or_section` resolves to a section listed `unchanged` in the section_diff_report. Auto-retract UNLESS the finding's body explicitly satisfies BOTH:
   - (a) names a specific defect class the prior round's personas missed (not "the section is wrong" — names the missed class), AND
   - (b) names why the prior lens did not catch it (new persona type running this round? new evidence from a `modified` section interacting with this `unchanged` section? new ground-truth fact uncovered in audit?).

   If both (a) and (b) are present in the finding body, keep at filed severity. If either is missing, retract with note `RETRACTED: targets unchanged section without (a)+(b) justification`.

2. **`regression_risk: yes`** — finding's cited text is in a `modified` or `added` section AND `plan_growth_flag` was true. Apply mechanical severity downgrade: CRITICAL → HIGH → MEDIUM → LOW → drop. Skip the downgrade if the finding's body names a *specific failure mode the added text creates* (named scenario where executing the plan with this added text produces a broken result). Default behavior is downgrade; the persona has to earn the original severity.

Record retractions and downgrades in the verdict's `### Retractions` block with the rule that fired.

### Filter Against Critical-Pair Policies

For each finding:
- Contradicts an active critical-pair policy → retract. Note.
- Duplicates a Ground Truth hard finding already mechanically fixed → retract.
- Otherwise → keep.

### Fold In Implementability Findings

From `imagined_implementer_report`:

- Every `undecided_decisions` entry (which now requires `severity_test` AND `affected_chunks ≥ 2` to land here) → `[HARD: cross-chunk decision undecided]`, blocker class `IMPLEMENTABILITY_GAP`. Severity HIGH. Include the `severity_test` quote in the verdict rendering — it's the persona's own falsifiability statement.
- Every `needed_identifiers` entry with `status: undecided` → `[HARD: cross-chunk identifier missing]`, blocker class `IMPLEMENTABILITY_GAP`. Severity HIGH.
- `informational_decisions` entries → no finding. Surface counts in the verdict diagnostic line for visibility but do NOT translate to blockers.
- `scope_reduction_candidates` → render as a separate `### Scope Reduction Candidates` block in the verdict output (see template below). NOT a blocker; this is a *lever* surfaced for the user. The user decides whether to drop the chunk (and re-invoke with a slimmer plan) or bind the decisions.

Deduplicate against Decision-Closure Audit findings by topic (same cross-chunk surface, same section). Where a finding appears in both, attribute to Decision-Closure Audit (earliest source) and merge implementability evidence.

### Detect Cross-Persona Disagreement

For each plan span (section / chunk / line range), collect surviving findings. Two personas propose contradictory fixes for the same span → label `STABLE_DISAGREEMENT`.

### Consolidate Non-Conflicting Fixes

Deduplicate findings across personas (merge, attribute to all). Group by target file (engineering plan, brief, decisions log). Apply in a single editing pass per file, ordered by severity (CRITICAL → HIGH → MEDIUM → LOW). Within a severity, document order.

**Forbidden fixes:**
- Weakening the plan (dropping rollback, lowering quality gates) → `OPEN_QUESTION`.
- Editing the brief just to make a chunk fit → `BRIEF_AMENDMENT_NEEDED`.
- "Will be cleaned up later" — if it's not in the plan now, it won't happen.

`IMPLEMENTABILITY_GAP` findings are NOT auto-fixable. The decision requires user judgment about which mechanism to bind to. Carry forward to verdict; they gate `CLOSED` but do not gate `APPROVED`.

### Post-fix premise verification

Runs after fixes are applied to disk, before classifying remaining findings. Executes in the **main thread (LLM judgment), NOT as a sub-agent spawn** — the orchestrator owns the edits and must own the verification.

**Why this exists.** The orchestrator's fixes can rewrite prose that asserts claims about behavior — section bodies, decision-closure remediations, brief amendments, decisions.md entries. A fix that mechanically rewords "predicate at file:line is X" can flip the assertion to something verifiably wrong. The persona prosecution pass already runs premise interrogation against persona claims; this sub-pass extends the same rigor to claims the orchestrator just introduced.

**Procedure:**

1. **Identify added or rewritten prose.** Scan the post-fix engineering plan, brief, and `decisions.md` for prose lines that were added or modified by this round's fixes. Use the section_diff_report (sections marked `modified` or `added`) as the starting set; within those, focus on lines added by orchestrator fixes (not unchanged context lines).

2. **Identify verifiable claims.** Use LLM judgment to flag prose lines that assert a verifiable claim. Examples of verifiable claims:
   - **Behavior**: "the resolver returns X under condition Y"
   - **Scope**: "chunk N writes only to files matching `<glob>`"
   - **Constraint**: "this column is NOT NULL"
   - **Cross-reference**: "matches the existing pattern in `<file>`"

   Skip:
   - Section headers and structural prose
   - Stylistic edits (tense changes, punctuation)
   - Open-ended commentary ("future work may consider…")
   - Aspirational language ("aim to", "ideally")

3. **Verify each claim.** For each flagged claim, run the cheapest verification that falsifies it: `Read` the cited file at the cited line, `rg` for the cited identifier, `git log -p` for recent state. Distinct from Ground Truth's path-existence checks — this verifies *behavior at those paths matches the claim*.

4. **File falsified claims.** Each claim that does not survive verification becomes a `FIX_INTRODUCED_PREMISE_INVERSION` blocker rendered in the verdict as:

   ```
   [FIX_INTRODUCED_PREMISE_INVERSION] {plan_section}: orchestrator-applied fix asserts "{verbatim claim}". Verification: {what was run}. Actual: "{verbatim contradicting evidence}". Working tree left dirty.
   ```

5. **Leave working tree dirty.** Do NOT auto-revert the bad fix. The user inspects, decides whether to amend the prose to match reality OR amend the underlying code/structure to match the prose, then re-invokes.

Verification stats are recorded for the verdict template: `verification_attempts={n}; verified={n}; falsified={n}; new_blockers_filed={n}`.

### Same-round focused re-prosecution on rewritten prose

Engineering-plan reviews thrash hardest when round-N orchestrator fixes become round-N+1 prosecution targets. The Post-fix premise verification step above catches *false claims* introduced by orchestrator edits, but it does not catch *new persona-class defects* the rewritten prose introduces (e.g., a Decisions-closure remediation that an architecture persona would flag as cross-chunk-wiring, or a Brief Mapping addendum that a product persona would flag as scope creep). Without this pass those defects bake in and surface as fresh blockers next round.

This sub-pass closes the loop in-invocation. Bounded: exactly one re-pass on the orchestrator's own diff hunks, never recursive.

#### Skip conditions

Skip this sub-pass when ALL three are true:
1. Stage 3d applied zero fixes to the engineering plan (orchestrator-applied fix count == 0).
2. Cross-file edits applied zero fixes to `decisions.md` / brief.md.
3. Post-fix premise verification falsified-claim count == 0.

If any of the three is non-zero, the sub-pass is mandatory.

#### Procedure

1. **Identify the orchestrator's diff hunks.** Run `git diff --unified=3 <pre-orchestrator-tree-ish>..HEAD -- features/<feature>/` and capture the per-file added-line spans across the engineering plan, brief, and decisions log. These are the spans Stage 3 wrote.

2. **Spawn focused re-pass agents.** Spawn one focused agent per (artifact, persona) pair from the original Stage 2 panel, scoped to the diff hunks only. Use the same agent template (`~/.claude/skills/_review-common/agent-prompt.md`). All substitutions carry over verbatim from Persona Prosecution; the only changes are:
   - `{audit_report_bullets}` is augmented with a "Diff hunks under review" block listing each (path, line range, verbatim added text).
   - `{skill_specific_extensions}` gets a HIGH/MEDIUM filter prepended: "Filter findings to severity HIGH or MEDIUM only — LOW residuals are out of scope. Do not file premise-inversion RESETs (those are an entry-point-only mechanism). Premise inversions on rewritten prose are caught by Post-fix premise verification, not this pass."
   - `{skill_specific_preamble}` is `re_pass: focused_diff_hunks; round_number: <N>; original_pass_completed: yes`.

   **Omitting any other substitution under-constrains the persona** — the agent loses its persona file pointer, the audit report, the critical-pair subset, etc. The HIGH/MEDIUM filter is a refinement of an otherwise-complete prompt, not a replacement for it.

3. **Filter re-pass fix lists through Stage 3b critical-pair retraction.** Findings contradicting an active critical-pair policy are retracted, not applied. Same procedure as the original Stage 2 → 3b filtering.

4. **Detect cross-persona disagreement on diff-hunk spans (Stage 3c re-application).** If two re-pass personas file contradictory fixes on the same diff hunk, label `STABLE_DISAGREEMENT` and persist to blockers — do NOT auto-apply either.

5. **Apply surviving fixes as additional Stage 3d edits.** Use the same Consolidate Non-Conflicting Fixes procedure (Group by target file; apply in severity order). Authority order if the re-pass finding lands on multiple files: `decisions.md` > `brief.md` > engineering plan.

6. **Re-run Post-fix premise verification on the new edits.** The re-pass writes prose, so the same verification machinery applies.

7. **Record metrics.** Update the verdict template with: re-pass agents spawned, re-pass findings raised, re-pass findings retracted (critical-pair), re-pass STABLE_DISAGREEMENT spans, re-pass fixes applied, re-pass falsified claims (from the second premise verification).

The cost asymmetry justifies this: spawning 3 focused agents on bounded diff hunks is cheap relative to a full re-prosecution invocation that the user has to trigger by re-invoking the skill.

### Classify Remaining Unresolved Findings

See `~/.claude/skills/_review-common/blocker-classes.md`. Active for engineering plan review: `STRUCTURAL_LINT_FAILED`, `BRIEF_AMENDMENT_NEEDED`, `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `IMPLEMENTABILITY_GAP`, `UNCORROBORATED_RESET`, `FIX_INTRODUCED_PREMISE_INVERSION`, `POLISH_PLATEAU`, `REPO_STATE_DRIFT`.

**Carry-forward consultation.** Two priorities, applied in order. Priority 1 is the *durable* arbitration record; Priority 2 is the *ephemeral* round-cache. Both are consulted; whichever drops the finding first wins.

**Priority 1 — Decisions log (durable record).** `Read` `features/<feature>/decisions.md` if it exists. For each surviving finding, scan decisions.md for entries where ALL of:
- The entry's `Decision:` subject substring-matches the finding's `path_or_section` (matching identifier, section heading, or quoted phrase fragment ≥4 words).
- The entry's `Status:` is `bound` (case-insensitive).
- The finding contradicts the bound resolution (the persona is filing a fix that would *undo* the bound decision, or a fix that asserts the opposite of what was bound).

When all three match, **drop the finding** with note `RETRACTED: contradicts bound decisions.md entry "<entry subject>" (<entry date>); entry's Why: "<verbatim Why paragraph, capped at ~200 chars>"`. The verdict surfaces the retraction so the user sees their prior arbitration was honored.

This priority exists because `decisions.md` is the project's **converged memory across sessions**, surviving cache wipes, machine swaps, and round-counter resets. The Decision-Closure Audit's prior-classification consistency check (in Ground Truth) handles classification flips on decision-closure findings; this priority handles general findings that contradict bound resolutions on any subject. Authority order: `decisions.md` > `engineering-plan.md` > prior round's verdict text.

**Priority 2 — Recently resolved blockers (ephemeral cache).** Check `recently_resolved_blockers` for entries where `carry_forward_until_round >= round_number` AND `path_or_section` overlaps the finding's surface (matching section heading, identifier, or file:line range). If a match exists, the finding is being re-prosecuted on a span the user already adjudicated within the active carry-forward window:

- **Downgrade to `OPEN_QUESTION`** with the prior `user_decision` surfaced verbatim in the rendered blocker body.
- The persona's claim survives only if the current invocation supplied a `current_reclassification_justification` (filed in `prior_blockers[].current_reclassification_justification` when persona prosecution flagged it as a re-classification grounded in repo-state change).
- Without justification, the verdict's blocker entry reads: `[OPEN_QUESTION] {finding} — Prior round {N} resolved this with: "{user_decision}". No new repo-state justification was filed; user must decide whether to accept the prior resolution or arbitrate.`

This is the engineering-plan analog of the PR-review prior-blocker consistency rule. Without it, the same `IMPLEMENTABILITY_GAP` decision can be re-raised round-after-round under new framing.

**Why two priorities.** A user who binds a decision in `decisions.md` expects it to survive forever — but `recently_resolved_blockers` evicts after `carry_forward_until_round + 2`, and cache wipes restart from empty. Without Priority 1, a finding contradicting a 6-month-old `decisions.md` entry would re-fire on every cold-start review. Priority 1 makes durable arbitration durable; Priority 2 catches recent re-prosecutions before the durable layer would.

### Render Verdict

Three-state verdict from `_review-common/blocker-classes.md`. Pick exactly one: `CLOSED`, `APPROVED`, or `NEEDS USER INPUT`. Compute Tier-1 weight (CRITICAL=8, HIGH=4, MEDIUM=2, LOW=1) and Tier-2 weight after fix application.

The semantic difference: APPROVED says "the *shape* is right; remaining work is decision-making, not structure-fixing." CLOSED says "you can write the next per-chunk plan and have it cohere with the others." Only CLOSED unblocks per-chunk plan writing.

### Output

```
## Engineering Plan Review v2 Complete: features/<feature>/engineering-plan.md

**Round:** {round_number} {(plan_growth: +N% / unchanged-section gate active) | (round 1 — no prior state)}
**State source:** {`Loaded from ~/.claude/cache/review-state/<feature-slug>.json (round N → N+1)` | `Round 1 (no prior state)` | `Reconstructed from decisions.md (state file missing; round_number reset to 1; recently_resolved_blockers seeded from decisions log)`}
**Personas:** {names}
**Ground Truth audit:** brief_trace PASS / N hard findings; repo_reality PASS / N hard findings; structural_lint PASS / N findings; decision_closure: {n cross-chunk-wiring HARD, n brief-layer HARD, n reclassification → OPEN_QUESTION, n unclear → Persona Prosecution}
**Mechanical fixes applied:** {count}
**Persona Prosecution:** {N} agents in parallel
**RESETs filed:** {count} (corroborated repo-state: {n}; corroborated brief-environment: {n} [memory-corroborated: {n}]; uncorroborated reclassified to CRITICAL HARD: {n})
**Imagined-Implementer:** verdict={implementable | not_implementable}; undecided_decisions={count} (severity_test passed: {n}); informational_decisions={count} (severity_test_unwritable: {n}, affected_chunks_<2: {n}, chunk_internal_after_re_read: {n}); missing_identifiers={count}; scope_reduction_candidates={count}
**Round-memory retractions:** unchanged-section auto-retract: {n}; regression_risk severity downgrades: {n}
**Carry-forward consultation:**
  - Priority 1 (decisions.md): findings checked: {n}; retracted via bound entry: {n}
  - Priority 2 (recently_resolved_blockers): matches: {n}; downgraded to OPEN_QUESTION: {n}; survived with current_reclassification_justification: {n}
**Orchestrator fixes applied:** {count} (HARD: {n}, SOFT: {n})
**Orchestrator retractions (critical-pair policy):** {count}
**Post-fix premise verification:** verification_attempts={n}; verified={n}; falsified={n}; new_blockers_filed={n}
**Same-round focused re-prosecution:** {skipped (no orchestrator edits) | ran with {n} agents on {m} diff hunks; findings raised: {f}; retracted: {r}; STABLE_DISAGREEMENTs: {s}; fixes applied: {a}; second-pass falsified claims: {p}}
**Final Tier 1 weight:** {n}
**Final Tier 2 weight:** {n} (floor: 4)

### Changes Made
- Plan: {bullets}
- Brief: {bullets if any}
- Decisions log: {bullets if any}

### Retractions
- {finding} → retracted because {policy / pre-resolved by Ground Truth / superseded}

### RESETs (premise inversions)
- [CORROBORATED repo-state — short-circuit fired] Span: {plan section}; personas: {a, b[, c]}; claim falsified: "{...}"; actual: "{...}"
- [CORROBORATED brief-environment — short-circuit fired] Span: {brief section}; persona(s): {a [, b]}; corroborating source: {persona b | CLAUDE.md:line | memory file}; claim falsified: "{...}"; contradicting evidence: "{...}"
- [UNCORROBORATED — reclassified to CRITICAL HARD] Subclass: {repo-state | brief-environment}; Span: {section}; persona: {a}; claim: "{...}"; actual: "{...}"

### Scope Reduction Candidates (if any)
- {chunk-slug}: {undecided_count} undecided items point at this chunk. Tradeoff: {one-sentence loss}. **Lever:** drop this chunk and re-invoke, instead of binding {undecided_count} decisions.

### Blockers (if any)
- [BRIEF_AMENDMENT_NEEDED] {finding} — {what brief change is needed and why}
- [STABLE_DISAGREEMENT] {finding} — Persona A proposes {fix A}; Persona B proposes {fix B}. Pick one.
- [OPEN_QUESTION] {finding} — {question}
- [IMPLEMENTABILITY_GAP] {finding} — cross-chunk decision/identifier the engineering plan must bind. Source: {Decision-Closure Audit | Imagined-Implementer}.
- [UNCORROBORATED_RESET] {finding} — single-persona premise-inversion claim weighed as CRITICAL HARD.
- [FIX_INTRODUCED_PREMISE_INVERSION] {plan section}: orchestrator-applied fix asserts "{verbatim claim}"; verification: {what was run}; actual: "{contradicting evidence}". Working tree dirty.
- [POLISH_PLATEAU] {finding} — non-blocking; ship is acceptable.
- [REPO_STATE_DRIFT] HEAD changed mid-review from {sha} to {sha}. Re-run.

### Plan Status: CLOSED / APPROVED / NEEDS USER INPUT
```

---

## Multi-persona consolidation table

When 2+ personas run, also output:

```
| Persona | Findings raised | Findings applied | Retracted | Blocker contributions |
|---|---|---|---|---|
| architecture | 4 | 3 | 1 (impl-leak policy) | 1 STABLE_DISAGREEMENT |
| ai-development | 2 | 2 | 0 | 0 |
| product | 3 | 2 | 0 | 1 BRIEF_AMENDMENT_NEEDED |
| **overall** | **9** | **7** | **1** | **2 blockers** |
```

---

## Hard rules

- **Status-frontmatter check is mandatory and runs first.** An engineering plan with frontmatter `Status: needs-user-input` is mid-cycle authoring state (the partial draft was written by `/engineering-plan-author`'s NEEDS_USER_INPUT path with a `## Pending blockers` section appended); skill refuses to run against it. The same check applies to the upstream brief — a `Status: needs-user-input` brief means the engineering plan is descended from an unstable source and cannot be reviewed cleanly. Both checks are deterministic and run before the Structural Lint Gate.
- **Ground Truth phase is mandatory.** Persona agents reading the plan without the audit will re-prosecute facts.
- **Round Memory pass is mandatory.** Skipping it disables the plan-growth gate and section-diff gate, returning the skill to its pre-fix thrash mode. State file lives at `~/.claude/cache/review-state/<feature-slug>.json` (NOT in the project repo).
- **Decision-Closure Audit is mandatory, including the prior-classification consistency check.** Skipping the consistency check lets the same decision flip between `cross-chunk-wiring` and `chunk-internal` across rounds, forcing the user to add then delete the same binding.
- **Persona Prosecution agents return fix lists; never edit files.** All edits applied by orchestrator.
- **Premise interrogation pass is mandatory.** Both the repo-state and brief-environment sub-passes MUST run. A persona producing zero RESETs must explicitly state `premise_interrogation: passed` (covering both sub-passes). Skipping the brief-environment sub-pass is a workflow bug — it lets brief premises that contradict project memory poison every downstream chunk.
- **Imagined-Implementer Dry Run is mandatory.** Skipping removes the convergence forcing-function and lets `IMPLEMENTABILITY_GAP`s slip through.
- **RESET corroboration gate.** Single-persona RESET reclassified to CRITICAL HARD, not auto-escalated. Two-of-three on the same span is the only short-circuit signal.
- **Orchestrator applies critical-pair policies before applying fixes.** Findings contradicting a policy are retracted, not relitigated.
- **Never** mark CLOSED while any blocker class (`BRIEF_AMENDMENT_NEEDED`, `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `IMPLEMENTABILITY_GAP`, `UNCORROBORATED_RESET`, `REPO_STATE_DRIFT`) is non-empty.
- **Never** mark APPROVED while a non-`IMPLEMENTABILITY_GAP` blocker is present.
- **APPROVED does not unblock per-chunk plan writing.** Only CLOSED does. Communicate clearly.
- **Never** edit the brief just to make a chunk fit. That's `BRIEF_AMENDMENT_NEEDED`.
- **Never** weaken the plan to resolve a finding. That's `OPEN_QUESTION`.
- **Never** auto-fix an `IMPLEMENTABILITY_GAP`. The decision requires user judgment.
- **Orchestrator verifies its own edits.** Post-fix premise verification runs after Consolidate Non-Conflicting Fixes, before Classify Remaining Findings. Skipping it allows the orchestrator's own prose-rewrite fixes to introduce premise inversions that cascade into the next round.
- **Same-round focused re-prosecution is mandatory** when ANY of: orchestrator engineering-plan fix count > 0, cross-file fix count (brief / decisions log) > 0, premise verification falsified-claim count > 0. Skipping it lets persona-class defects in orchestrator-rewritten prose bake in and surface as fresh blockers next round. Bounded: exactly one re-pass on the diff hunks Stage 3 wrote.
- **Carry-forward consultation is mandatory and uses two priorities in order.** Priority 1: consult `features/<feature>/decisions.md` for findings contradicting bound entries — drop them with citation. Priority 2: consult `recently_resolved_blockers` for ephemeral round-cache matches — downgrade to `OPEN_QUESTION` unless `current_reclassification_justification` is filed. Authority order: `decisions.md` > `engineering-plan.md` > prior round's verdict text.
- **Compliance self-check.** Before emitting the verdict, confirm: (1) post-fix premise verification ran with non-empty stats; (2) same-round re-prosecution ran when any of the three triggering conditions held, and recorded re-pass agent counts; (3) Priority 1 carry-forward (decisions.md) fired when the file exists, even on round 1; (4) Priority 2 carry-forward fired when `recently_resolved_blockers` had matching entries; (5) if state was reconstructed from `decisions.md`, the verdict's State source line reflects it.
- **Always** quote verbatim from plan, brief, repo, or audit_report when justifying a finding.
- **Always** label remaining findings with their blocker class.
- **No re-review loop within a single invocation.** Escalate; let the user re-invoke.

## Edge cases

- **No brief found** at `features/<feature>/brief.md` → CRITICAL. Engineering plan cannot exist without a brief; stop and escalate.
- **Plan in old monolithic format** (e.g., `context/plans/049_*.md`) → confirm with user whether to review-and-port or stop. This skill assumes the new structure.
- **Brief and plan disagree on a Goal** → `BRIEF_AMENDMENT_NEEDED`. Brief is canonical; user signs off on amendment or plan changes.
- **Chunk plans don't yet exist for proposed chunks** → expected. Ground Truth Repo Reality is limited to architecture-level claims for those chunks.
- **Chunk plan exists in `implementation/`** → Ground Truth spot-checks consistency with engineering-plan chunk-index row. Doesn't full-review (that's `/plan-review-v2`'s job).
- **Multiple engineering plans across features in one invocation** → out of scope. Run once per feature.
- **Decisions log missing** (`features/<feature>/decisions.md`) → `OPEN_QUESTION` only if the plan has a non-obvious architectural choice without a `Why:` paragraph; otherwise no finding.
- **State file missing but `decisions.md` exists** → reconstruct partial state. Round number resets to 1. Seed `recently_resolved_blockers` from `decisions.md` entries (each entry's `Decision:` line becomes a row with `blocker_class_when_resolved: RESOLVED`, `path_or_section` from the entry's subject, `user_decision` from the entry's `Why:` paragraph capped at ~200 chars, `carry_forward_until_round = 2`). Section hashes recompute clean (no diff vs prior, full prosecution latitude). Verdict's State source records `Reconstructed from decisions.md`. Warn the user that round-counter reset means plan-growth and section-diff gates are dormant for this invocation.
- **State file missing AND no `decisions.md`** → cold start. Round 1, empty `prior_blockers`, empty `recently_resolved_blockers`. No reconstruction; full re-prosecution latitude. This matches the legacy behavior.
- **HEAD changes mid-review** → `REPO_STATE_DRIFT`. User re-runs.
