---
name: brief-review-v2
description: Single-pass adversarial review of a feature's brief.md — the upstream source-of-truth. Refuses artifacts in `Status: needs-user-input` state (the partial-draft mid-cycle state written by `/brief-author`). Stage 0 is a Structural Shape Check (replaces /plan-lint at the brief layer — required sections, banned-content patterns, frontmatter shape). Four phases follow: Round Memory loads reviewer state and consults the brief-author sidecar at `~/.claude/cache/author-state/<feature>__brief.json` to skip re-prosecuting author-verified claims; Stage 1 grounds the brief in spec.md / CLAUDE.md / project-memory / decisions.md (NO repo grep — briefs don't cite paths or identifiers); Stage 2 runs persona prosecution in parallel (product + ai-development + project-manager by default; +architecture when the brief proposes significant arch shape); Stage 3 applies fixes, runs post-fix premise verification + SAME-ROUND focused re-prosecution on diff hunks (≤1 re-pass; bounded, never an inner loop), runs decisions-log-first carry-forward, classifies remaining, renders verdict. Sister to /engineering-plan-review-v2 (engineering-plan layer) and /plan-review-v2 (chunk-plan layer).
user-invocable: true
---

# Brief Review v2 — Staged Single-Pass

The brief is the highest-leverage artifact in the feature lifecycle: every downstream artifact (engineering plan, chunk plans, code) descends from it. A brief that contradicts its own Goals, invents a user population, or smuggles a Non-goal-violating Goal will cascade five rounds of review machinery to surface — and the surface itself doesn't repair the brief, only the descendants. This skill prosecutes briefs through a Structural Shape gate plus three stages, with bounded same-round verification on orchestrator-rewritten prose. Never a multi-round inner loop — survivors of the bounded same-round re-pass land in the verdict and the user re-invokes.

This is the brief layer. Sister skills `/engineering-plan-review-v2` (engineering-plan layer) and `/plan-review-v2` (chunk-plan layer) review downstream artifacts. If the user asks for review of an engineering plan or chunk plan, redirect.

## Shared scaffolding

- `~/.claude/skills/_review-common/principles.md` — stance, banned rationalizations, severity/tier, plan style rules
- `~/.claude/skills/_review-common/agent-prompt.md` — persona-agent prompt template
- `~/.claude/skills/_review-common/critical-pairs.md` — active subset for brief review: `P-CLASS-SCOPE, P-FULL-FILE` (universal) plus the brief-specific pairs defined in this skill (P-BRIEF-WHAT-NOT-HOW, P-BRIEF-GOAL-VERIFIABILITY, P-BRIEF-NON-GOAL-REALITY, P-BRIEF-PROBLEM-CONCRETENESS, P-BRIEF-OPEN-QUESTION-FORM, P-BRIEF-COHORT-CITATION)
- `~/.claude/skills/_review-common/blocker-classes.md` — blocker registry + verdict gate

## Tribunal stance (brief-specific)

**SPEC IS CANONICAL, PROJECT MEMORY IS LAW.** Two upstream sources bound this review:

1. **`spec.md` and `context/specs/*.md`** are the product master-spec; brief Goals must trace to spec capabilities; brief Non-goals must not contradict spec promises.
2. **`CLAUDE.md` and project memory** (`~/.claude/projects/<project>/memory/`) carry the project's bound invariants — "no non-Latin person names", "no existing users yet", "linking has to be right or not done at all", category architecture rules, etc. A brief that contradicts an invariant is solving a phantom problem; the prosecution surfaces this as a `FIX_INTRODUCED_PREMISE_INVERSION`-class finding even when it appears in the original draft (the "fix" was the brief author's act of writing the contradicting prose).

There is no equivalent of "REPO IS LAW" at the brief layer — briefs don't cite path:line or identifiers, so there's no on-disk code to ground claims against. Stage 1's verification target is the upstream documents (spec, CLAUDE, memory, decisions log), not the running codebase.

## Active critical-pair policies (brief layer)

These resolve oscillation hazards specific to brief review. The hosting skill applies them silently in Stage 3; persona findings that contradict an active policy are retracted, not relitigated.

**P-BRIEF-WHAT-NOT-HOW — Brief describes WHAT, engineering plan describes HOW.** The Solution / Goals / User-facing changes sections name product-visible shape and behavior, not architecture, file paths, schema changes, or implementation tactics. A finding demanding architecture detail / implementation specifics in the brief is invalid; a finding flagging implementation creep into the brief (e.g., file paths, function names, schema columns appearing in Solution) is valid.

**P-BRIEF-GOAL-VERIFIABILITY — Each Goal must have a verifiable success criterion.** "Better discoverability" is invalid; "the home screen shows a 'recently ranked by friends' row above the watchlist" is valid. A finding requesting more specific *implementation* of a Goal is invalid (that's engineering-plan territory); a finding requesting a verifiable success criterion for a vague Goal is valid.

**P-BRIEF-NON-GOAL-REALITY — Non-goals must be plausible scope kills, not platitudes.** "We won't break existing things" is a platitude (no feature plans to break things). "We won't change the friend-graph data model" is a real scope kill if the feature could plausibly require such a change. A finding flagging platitude Non-goals is valid; a finding demanding more Non-goals when the existing list already covers the plausible scope-creep surface is invalid.

**P-BRIEF-PROBLEM-CONCRETENESS — Problem statement names a user-visible failure with quantified cohort or observable behavior.** "Users want better X" is invalid (no quantification, no cohort). "~400 prolific authors are missing from search results because the TMDB ingest does not hydrate their canonical IDs" is valid. A finding requesting concreteness on a vague problem is valid; a finding demanding implementation detail in the problem statement is invalid (Problem describes the failure, not the fix).

**P-BRIEF-OPEN-QUESTION-FORM — Open questions are questions, not statements.** "We need to decide whether X" is a statement (re-cast as Goal or Non-goal); "How do we handle X when Y?" is a question. A finding flagging statement-as-question form is valid; a finding demanding answers to legitimately open questions is invalid (the user resolves outside the brief; that's not a brief defect).

**P-BRIEF-COHORT-CITATION — Cohort counts cite a verifiable source.** "~400-450 prolific authors" is valid only if traceable to a database query, migration, or memory entry. "Many users complain" without a citation is invalid. A finding flagging an uncited cohort claim is valid; a finding demanding *exact* counts when the brief honestly says "approximately N" with citation is invalid (briefs do not need to re-execute queries — they cite the most recent verifiable measurement).

## Active blocker classes

From `~/.claude/skills/_review-common/blocker-classes.md`:

- `STRUCTURAL_SHAPE_FAILED` — brief-layer equivalent of `STRUCTURAL_LINT_FAILED`. Stage 0 short-circuited the review because required sections are missing, banned content categories appeared, or frontmatter is malformed. The brief is unprosecutable until shape is fixed.
- `STABLE_DISAGREEMENT` — two personas filed contradictory fixes on the same brief span.
- `OPEN_QUESTION` — a finding the orchestrator cannot auto-resolve (typically: a brief Goal contradicts spec.md, and the user must arbitrate "amend the brief or amend the spec?").
- `FIX_INTRODUCED_PREMISE_INVERSION` — orchestrator's applied fix rewrote brief prose that asserts a claim about the spec, project memory, or category invariants, but the claim does not survive verification. Working tree dirty.
- `POLISH_PLATEAU` — Tier-2 weight non-zero but ≤ floor (4). Non-blocking.
- `REPO_STATE_DRIFT` — `git rev-parse HEAD` changed mid-review. User re-runs.

`STRUCTURAL_SHAPE_FAILED` is the brief-layer-only class. Briefs don't run through `/plan-lint`, so the shape check lives inline in Stage 0 and emits this class on failure. The class is registered in `_review-common/blocker-classes.md` under §Brief-only.

## Usage

```
/brief-review-v2 <brief-path-or-feature> [--personas <p1> <p2> ...]
```

**Examples:**

```
# Feature shorthand — resolves to features/<feature>/brief.md
/brief-review-v2 author-tmdb-hydration

# Explicit path
/brief-review-v2 features/author-tmdb-hydration/brief.md

# Explicit personas (overrides default)
/brief-review-v2 author-tmdb-hydration --personas product architecture

# No arguments → enumerate features/*/brief.md, list with Status, ask which
/brief-review-v2
```

## Argument parsing

Split `$ARGUMENTS` on whitespace. Classify each token:

- `--personas` → all subsequent non-path tokens are persona names.
- Token contains `/` or ends with `.md` → brief path.
- Token matches a directory name under `features/` → resolves to `features/<token>/brief.md`.
- Otherwise → treated as a feature name; if `features/<token>/brief.md` doesn't exist, stop and report.

No arguments → enumerate `features/*/brief.md` and list with feature name + brief's `Status:` field. Ask which to review.

## Persona resolution

### Default tribunal (no `--personas`)

Three personas in parallel:

- **`product.md`** — Goals/Non-goals coherence, scope creep, contradicted spec, banned project assumptions ("existing users"), problem-statement cohort grounding.
- **`ai-development.md`** — plan-quality at the brief layer (Goal verifiability, Open-question form, drift toward engineering-plan detail), banned content categories (addendum, review attribution, historical comparison).
- **`project-manager.md`** — Non-goal discipline (platitudes vs real scope kills), Open-questions completeness (every named gap has a resolution path), brief-to-engineering-plan readiness (does the brief give a downstream engineering-plan author enough to chunk?).

If the brief proposes a significant architectural shape — i.e., the Solution section names cross-cutting infrastructure, new external dependencies, schema-level invariants, or threading/concurrency posture changes — swap or add **`architecture.md`**. Justify the swap in the verdict output.

### Explicit personas

Load each from `personas/{name}.md`. Reviewed by every listed persona in parallel. Missing persona file → stop and report.

`ai-development.md` is referenced as supplementary context for every Stage 2 agent — even non-`ai-development` personas should know the plan-style rules.

---

## Workflow

```
Status-frontmatter check         (deterministic, hard short-circuit, runs first)
   ↓ Status: needs-user-input → REFUSE, point user back at /brief-author; stop
Stage 0: Structural Shape Check  (deterministic, hard short-circuit)
   ↓ verifies required sections, banned-pattern absence, frontmatter shape;
   ↓ FAIL → emit STRUCTURAL_SHAPE_FAILED, stop
Round Memory Pass                (deterministic, no LLM judgment)
   ↓ loads ~/.claude/cache/review-state/<feature>__brief.json;
   ↓ consults the brief-author sidecar at
   ↓ ~/.claude/cache/author-state/<feature>__brief.json and records counts of
   ↓ author-verified claims for Stage 2 to skip;
   ↓ computes round_number, prior_blockers, recently_resolved_blockers
Stage 1: Ground truth pass       (deterministic, mostly mechanical;
                                  Stage 1d carve-out is light LLM judgment)
   ↓ produces audit_report grounding brief claims in spec / CLAUDE / memory /
   ↓ decisions log; NO repo grep (briefs don't cite paths or identifiers)
Stage 2: Persona prosecution     (LLM judgment, M parallel agents)
   ↓ when sidecar present, prepends a directive listing author-verified claims
   ↓ so personas skip re-prosecuting them;
   ↓ produces fix_lists per persona
Stage 3: Orchestrator decision   (deterministic + judgment)
   ↓ applies fixes (with cross-file fix scope to decisions.md when fixes carry
   ↓ forward-binding markers), runs post-fix premise verification on rewritten
   ↓ prose, runs SAME-ROUND focused re-prosecution on diff hunks (≤1 re-pass),
   ↓ runs carry-forward consultation: decisions.md FIRST, then state-file cache,
   ↓ classifies remaining, renders verdict, persists state with per-round metrics
```

There is no inner loop. If blockers remain, the user resolves them and re-invokes. Round memory and `decisions.md` ensure the next run does not re-prosecute already-arbitrated questions.

---

## Status-frontmatter check (MANDATORY, HARD SHORT-CIRCUIT, RUNS FIRST)

`Read` the brief's YAML frontmatter. Extract the `Status:` value.

`Status:` is a binary mid-cycle signal: `needs-user-input` (mid-cycle) or absent (ready). All other lifecycle signals (post-merge, archived, in-progress) come from git/PR state, not frontmatter.

- **`Status: needs-user-input`** → stop. Do NOT spawn Stage 0 or anything after. The brief is mid-cycle by design (the partial draft was written by `/brief-author`'s NEEDS_USER_INPUT path with a `## Pending blockers` section appended; the user is between resolving blockers and re-invoking the author skill). Emit:

  ```
  BRIEF: <brief-path>
  STATUS: REFUSED (artifact in mid-cycle authoring state)

  This brief has frontmatter `Status: needs-user-input`. The author skill (`/brief-author`)
  wrote it as a partial draft with unresolved blockers listed in the `## Pending blockers`
  section at the end of the file. Reviewing a partial draft would re-prosecute issues the
  author already surfaced.

  Resolve the blockers listed in `## Pending blockers`, then re-invoke
  `/brief-author --rewrite <feature>`. The author skill removes the `Status:` frontmatter
  on a successful APPROVED emission; re-invoke `/brief-review-v2` once the brief is back
  to no-Status-field state.
  ```

- **No `Status:` field, OR any other value** → proceed normally. The Round Memory Pass below consults the brief-author sidecar at `~/.claude/cache/author-state/<feature>__brief.json`; if `authoring_mode: "draft"` is set there (the brief was written via `/brief-author --draft`, skipping ground-truth and self-prosecution), the verdict surfaces a draft warning. Persona prosecution still runs.

The check is deterministic and runs before any LLM judgment.

## Stage 0 — Structural Shape Check (MANDATORY, HARD SHORT-CIRCUIT)

Briefs don't run through `/plan-lint` (which is plan-shaped). The shape check lives inline.

### Required sections (in order)

The template at `features/_template/brief.md` is the source of truth. Apply these checks:

1. **Frontmatter** — `Created:` and `Last updated:` dates present (YYYY-MM-DD). `Status:` field is OPTIONAL — present only when the brief is mid-cycle (`Status: needs-user-input`); absent on an APPROVED brief. Frontmatter that has any other `Status:` value is a SOFT MEDIUM finding (the author skill should have removed it on APPROVED emission).
2. **`## Problem`** — section heading present; body non-empty.
3. **`## Solution`** — section heading present; body non-empty.
4. **`## Goals`** — section heading present; ≥1 bullet.
5. **`## Non-goals`** — section heading present; ≥1 bullet (or explicit "None — every plausibly-adjacent scope expansion is in scope" justification, which Stage 2 will then prosecute).
6. **`## User-facing changes`** — section heading present; body non-empty (may be "ships a database snapshot, no live UX changes" for backfill features).
7. **`## Open questions`** — section heading present; body is `None.` OR ≥1 question (in question form per P-BRIEF-OPEN-QUESTION-FORM, judged by Stage 2).

Each missing/empty section is `[HARD: missing required section]`.

### Forbidden patterns (regex-detectable)

Each pattern below is a Python `re` regex applied case-insensitively where `(?i)` appears. The patterns are listed in a fenced code block to keep nested backticks (used in character classes for backtick-or-quote matchers) lexically intact — a markdown-inline-code wrapper would close prematurely on the inner backtick.

```
# Addendum sections → HARD per occurrence
(?i)^##+\s*(addendum|appendix|review notes|round-\d+ findings)\b

# Review attribution → HARD per occurrence
(?i)\b(architecture review|product review|round[- ]?\d+ tribunal|reviewer A/B)\b found\b

# Historical comparison → HARD per occurrence
(?i)\b(the original brief|previously the brief|the brief used to|in the prior version)\b

# Persona-attribution headers → HARD per occurrence
(?i)^##+\s+(architecture|product|backend|frontend|testing|security)(?:'s|s')\s+(view|notes|take|opinion)\b

# Conflict-resolution metadata → HARD per occurrence
(?i)\b(conflict resolved by|consensus reached|decision pending arbitration)\b
```

Plus these prose-detected (non-regex) patterns:

- **Hedging future tense** — `we will likely`, `this brief aims to`, `the team should consider` → SOFT MEDIUM per occurrence
- **Meta-commentary** — `this section`, `below we'll cover`, `in the next section` → SOFT MEDIUM per occurrence
- **Emojis, exclamation marks** in section bodies → SOFT LOW

### Implementation-creep patterns (regex-detectable; HARD)

These signal the brief drifted into engineering-plan territory. Same fenced-block convention to preserve nested backticks:

```
# Path:line citations → HARD per occurrence
# Alternation is longest-first per the global longest-first rule (matters for `.tsx` vs `.ts`).
[a-z_/]+\.(tsx|prisma|toml|yaml|json|md|ts|js|sql)(:[0-9]+)?

# Function/identifier signatures → HARD per occurrence
\w+\(.*\)\s*(:|=>)\s*\w+

# Schema column names → HARD per occurrence
# Character class accepts either double-quote or backtick around the identifier.
(column|field|enum)\s+["`]\w+["`]

# SQL fragments → HARD per occurrence
(SELECT|INSERT|UPDATE|DELETE|CREATE TABLE)\s+\w+
```

Cohort references like "the `tmdbId` field" in Problem/Solution prose context are NOT matches — the schema-column regex requires the literal noun (`column` / `field` / `enum`) to precede the quoted identifier, so prose mentions of "the `tmdbId` field" in a Problem statement don't fire (no `column` or `enum` precedes the quoted token there).

The path-citation regex is applied to brief prose with backtick-fenced spans excluded. A reference like `` `backend/src/lib/tmdb.ts` `` inside a sentence is fine; an unfenced `backend/src/lib/tmdb.ts:42` is HARD.

### Behavior

- **All checks pass** → record `shape_clean=true` and proceed to Round Memory Pass.
- **Any HARD failure** → stop. Emit:

  ```
  BRIEF: <brief-path>
  STATUS: NEEDS USER INPUT (blocker: STRUCTURAL_SHAPE_FAILED)

  Stage 0 found N structural defects in this brief. Persona prosecution is not run
  because LLM judgment on top of a structurally-broken brief produces noise.

  - [HARD: missing required section] §Goals heading absent.
  - [HARD: implementation creep] line 42: "see backend/src/lib/tmdb.ts:120-150" — briefs do not cite paths.
  - [HARD: addendum section] §Round-2 findings — findings integrate into the section they correct.

  Fix the structural defects above and re-invoke /brief-review-v2.
  ```

  No further stages run. SOFT findings are deferred to Stage 1's audit report (they don't block the gate but appear in the verdict's structural-lint summary).

- **SOFT-only failures** → record findings; proceed to Round Memory Pass. Stage 1e mechanical fixes will resolve them inline.

Why short-circuit: a persona reviewing a brief with a missing Goals section produces findings that assume the section exists — wasted reasoning budget. The gate is the sieve.

---

## Round Memory Pass (MANDATORY, NO LLM JUDGMENT)

Same purpose as the sister skills: break the thrash patterns of (1) re-prosecution of resolved blockers and (2) orchestrator-introduced premise inversions.

The brief layer has a unique additional carry-forward source: the brief-author's sidecar at `~/.claude/cache/author-state/<feature>__brief.json`. The author skill already verified claims and applied self-prosecution; the reviewer must consult the sidecar to skip re-prosecuting what the author already arbitrated.

### State file location

Reviewer state at `~/.claude/cache/review-state/<feature>__brief.json` (NOT in the project; survives worktrees; never committed). Slug derivation: `<feature>__brief` from `features/<feature>/brief.md`.

Create the parent directory with `mkdir -p ~/.claude/cache/review-state` if missing.

### State file schema

```json
{
  "brief_slug": "<feature>__brief",
  "brief_path": "features/<feature>/brief.md",
  "last_review_at": "<ISO 8601 UTC>",
  "last_verdict": "APPROVED | NEEDS_USER_INPUT",
  "last_brief_sha256": "<hex>",
  "round_number": <integer, 1-indexed>,
  "prior_blockers": [
    {
      "blocker_class": "STABLE_DISAGREEMENT | OPEN_QUESTION | FIX_INTRODUCED_PREMISE_INVERSION | STRUCTURAL_SHAPE_FAILED",
      "path_or_section": "<brief section heading or quoted phrase>",
      "summary": "<one-line>",
      "raised_in_round": <integer>,
      "current_reclassification_justification": "<one-sentence repo-state justification when re-raised after prior resolution; absent on first appearance>"
    }
  ],
  "recently_resolved_blockers": [
    {
      "blocker_class_when_resolved": "<class | RESOLVED>",
      "path_or_section": "<brief section heading or quoted phrase>",
      "summary": "<one-line>",
      "resolved_in_round": <integer>,
      "user_decision": "<one-sentence rationale; capture priority below>",
      "carry_forward_until_round": <integer; defaults to resolved_in_round + 2>
    }
  ],
  "author_sidecar_consulted": {
    "sidecar_path": "<path or null>",
    "sidecar_present": <boolean>,
    "claims_verified_skipped": <integer>,
    "self_prosecution_findings_skipped": <integer>
  },
  "per_round_metrics": {
    "round_<N>": {
      "stage_3_fixes_applied": <integer>,
      "cross_file_edits": [
        { "file": "<path relative to repo root>", "summary": "<one-line>" }
      ],
      "re_pass_ran": <boolean>,
      "re_pass_diff_hunks_reviewed": <integer>,
      "re_pass_additional_fixes_applied": <integer>,
      "re_pass_findings_persisted_to_blockers": <integer>,
      "decisions_md_consultation": {
        "entries_matched": <integer>,
        "findings_dropped": <integer>
      }
    }
  }
}
```

Treat absence of `prior_blockers`, `recently_resolved_blockers`, and `per_round_metrics` as `[]` / `{}` when reading.

### Author sidecar consultation (brief-layer-unique)

Read `~/.claude/cache/author-state/<feature>__brief.json` if it exists. Extract:

- `claims_verified` count and `ground_truth_log` entries with outcome `verified` / `verified_softened` / `corrected`. These are claims the brief-author already grounded; Stage 2 personas MUST NOT re-prosecute them as hallucinations.
- `self_prosecution_findings` — findings the author skill already filed and resolved at write time. Stage 2 personas MUST NOT re-file them.
- `authoring_residual` — LOW residuals under the polish floor that the author skill explicitly accepted. These are not blockers; surface in the verdict as informational only.

If sidecar is absent (the brief was hand-written, not authored through `/brief-author`), record `author_sidecar_consulted.sidecar_present: false` and proceed; Stage 2 personas have full prosecution latitude.

If sidecar's `last_brief_sha256` differs from the current brief's SHA, the user edited the brief manually after authoring. Treat the sidecar's `claims_verified` as a *hint* (the author verified these against the prior version), not a binding skip-list — Stage 2 may re-prosecute spans where the user-edit overlaps an author-verified claim.

### Load prior state

`Read` the reviewer state file. Cases:

1. **File does not exist** → cold start. `round_number = 1`, `prior_blockers = []`, `recently_resolved_blockers = []`.
2. **File exists, brief SHA matches `last_brief_sha256`** → user re-invoked without modifying the brief. `round_number = stored + 1`. Carry `prior_blockers` and `recently_resolved_blockers` forward (drop entries where `carry_forward_until_round < new round_number`).
3. **File exists, brief SHA differs** → user modified the brief between rounds. `round_number = stored + 1`. The brief diff IS the user's response to prior-round blockers; carry forward but expect persona prosecution to file fewer findings against modified spans.

### Capture priority for `user_decision`

Same as plan-review-v2 (priority order: invocation `$ARGUMENTS` → brief diff → commit message body → commit message subject → `"No rationale recorded"`). Cap at ~200 chars.

### Persist on exit

After Stage 3 verdict rendering, update the state file:

- `last_review_at` ← current UTC timestamp
- `last_verdict` ← rendered verdict
- `last_brief_sha256` ← sha256 of post-fix brief
- `round_number` ← incremented
- `prior_blockers` ← rebuilt from current verdict's blockers
- `recently_resolved_blockers` ← extended per the standard pattern
- `author_sidecar_consulted` ← record of what was consulted this round
- `per_round_metrics["round_<N>"]` ← appended (append-only across rounds)

If verdict is `APPROVED`, leave the state file in place for future re-invocation.

---

## Stage 1 — Ground truth pass (MANDATORY, MOSTLY MECHANICAL)

Produces an `audit_report` per brief. Stage 2 personas MUST NOT re-prosecute facts already verified here.

**LLM-judgment carve-out.** Sub-passes 1a-1c are fully mechanical (file Reads, regex matches, substring overlaps). Sub-pass 1d (brief style supplements) makes two lightweight LLM judgment calls (Goal verifiability, Non-goal reality) that no regex can capture. These are bounded — the questions are "is this Goal observable?" / "is this Non-goal a real scope kill?" — and each finding is filed at SOFT MEDIUM under the corresponding P-BRIEF-* policy. The orchestrator does not auto-fix; the user arbitrates at Stage 3 if disputed. The sister skills' Stage 1 sub-passes stay fully mechanical because the chunk/engineering-plan layer has `/plan-lint` to handle structural concerns; the brief layer has no equivalent, so 1d picks up the slack.

The brief layer has NO repo grep — briefs don't cite path:line or identifiers (Stage 0 already enforced no implementation creep). Stage 1's verification target is upstream documents only.

### 1a. Spec trace (mechanical)

Open `spec.md` (project root) and any `context/specs/*.md` whose subject matches the feature.

For each Goal in the brief, search the spec(s) for an anchor:

- **Strong anchor** — spec section explicitly names the same capability (e.g., brief Goal "5-item ranking threshold" → spec.md §"Score-locking threshold").
- **Implicit anchor** — spec section implies the capability (e.g., brief Goal "watchlist auto-remove" → spec.md §"Ranking flow" mentions "ranking removes from watchlist atomically").
- **No anchor** — Goal has no trace in any spec. Either the brief invented capability the spec doesn't authorize (HARD: out-of-spec Goal) OR the spec is missing a section the brief assumes (SOFT: spec amendment may be needed; surface as `OPEN_QUESTION` if the user must arbitrate).

For each Non-goal in the brief, check whether it contradicts a spec capability:

- **Spec promises X, brief Non-goals X** → HARD: brief contradicts spec. The user must resolve (amend brief or amend spec).

Output a `Spec Trace` block:

```
### Spec Trace
Goals listed: <count>
Goals → spec anchors:
- "<verbatim Goal>" → strong anchor: spec.md §<heading>
- "<verbatim Goal>" → implicit anchor: spec.md §<heading> ("<verbatim phrase>")
- "<verbatim Goal>" → ❌ NO ANCHOR  [HARD: out-of-spec Goal]

Non-goals listed: <count>
Non-goals → spec contradiction check:
- "<verbatim Non-goal>" → no contradiction
- "<verbatim Non-goal>" → ❌ contradicts spec.md §<heading>: "<verbatim spec phrase>"  [HARD: contradicts spec]
```

### 1b. CLAUDE.md and project memory consistency (mechanical)

Read `CLAUDE.md` and every memory file under `~/.claude/projects/<project>/memory/` whose `description` field hints at relevance (substring match against the feature name, the brief's Solution paragraph keywords, or the brief's section bodies).

For each memory entry that may bear on the brief:

- **Brief honors the invariant** → no finding.
- **Brief contradicts the invariant** → HARD: contradicts project memory. Cite verbatim. Examples:
  - Memory says "no existing users yet" + brief says "existing users will need migration" → contradiction.
  - Memory says "no non-Latin person names" + brief Goal says "support Cyrillic author names" → contradiction.
  - CLAUDE.md says "5-item threshold; scores locked until 5 rankings" + brief Goal says "scores update from the first ranking" → contradiction.
- **Brief silent on the invariant** → no finding (silence is not contradiction).

Output a `Project Memory Consistency` block:

```
### Project Memory Consistency
Memory entries consulted: <count>
Contradictions:
- Memory entry: "<verbatim claim from MEMORY/<file>.md>"
  Brief claim: "<verbatim from brief>"  [HARD: contradicts project memory]
- ...

Honored invariants:
- "<one-line invariant>" — brief explicitly honors via §<section>
```

### 1c. Decisions log consistency (mechanical)

Read `features/<feature>/decisions.md` if it exists. For each dated entry:

- **Strong match** — entry's Decision subject substring-matches a brief Goal / Non-goal / User-facing change verbatim.
- **Topical match** — entry's Decision title or Why paragraph names a concept the brief discusses.

For each match:

- **Brief honors the bound decision** → record as `verified: bound_in_decisions_log`.
- **Brief contradicts the bound decision** → HARD: brief contradicts decisions.md.

Output a `Decisions Log Consistency` block:

```
### Decisions Log Consistency
decisions.md present: <bool>
Bound entries consulted: <count>
Contradictions:
- decisions.md entry "<title>" (<date>): "<verbatim Decision sentence>"
  Brief claim: "<verbatim from brief>"  [HARD: contradicts decisions.md]
- ...

Honored bound decisions:
- "<entry title>" (<date>) — brief honors via §<section>
```

### 1d. Brief style supplements Stage 0

Stage 0 covered the deterministic floor. Stage 1d covers brief-style hygiene the gate doesn't:

- Each Goal has a verifiable success criterion (lightweight LLM check; if truly vague, file SOFT MEDIUM under P-BRIEF-GOAL-VERIFIABILITY).
- Each Non-goal is a real scope kill (lightweight LLM check; platitudes flagged SOFT MEDIUM under P-BRIEF-NON-GOAL-REALITY).
- Open questions are in question form (regex check: must contain `?` per bullet; statements flagged SOFT MEDIUM under P-BRIEF-OPEN-QUESTION-FORM).
- Cohort claims cite a source (Problem section: regex `~?\d+(-\d+)?\s+(authors?|users?|movies?|books?|TV shows?|persons?)` — every match must be followed within 3 lines by a citation marker `(per `<file>` / `<query>`)` / "verified by" / "as of <date>"; uncited matches flagged SOFT MEDIUM under P-BRIEF-COHORT-CITATION).

### 1e. Stage 1 mechanical fixes

Apply unambiguous fixes immediately:

- Forbidden style-class patterns (tense, banned phrases, emojis from Stage 0 SOFT findings) → fix in place.
- Stale dates (Last-updated more than 30 days old AND brief content edited since) → update Last-updated.
- Trivial Open-question form fixes (statement → question) when the conversion is unambiguous.

Emit `Stage 1 fixes applied:` bullet list.

Findings that survive Stage 1 (HARDs that can't be auto-fixed) are passed to Stage 2 as `pre_resolved_hard_findings`.

### Stage 1 output (audit_report)

Bulleted facts list (not verbose YAML). Include:

- brief_path, HEAD sha
- spec_trace: goals_anchored, non_goals_contradiction, hard_findings
- project_memory_consistency: entries_consulted, contradictions, honored_invariants
- decisions_log_consistency: entries_consulted, contradictions, honored_bound_decisions
- brief_style: goal_verifiability_findings, non_goal_reality_findings, open_question_form_findings, cohort_citation_findings
- stage_1_fixes_applied
- pre_resolved_hard_findings
- author_sidecar_consulted: claims_verified_skipped, self_prosecution_findings_skipped

---

## Stage 2 — Persona prosecution (parallel agents, fix-list output)

Read `personas/ai-development.md` once for context (referenced as a path in agent prompts; agents Read on demand).

Resolve personas (auto or explicit). Launch one Agent per persona, **all in parallel in a single message**. M agents.

### Spawn agents

Use the template in `~/.claude/skills/_review-common/agent-prompt.md`. Substitute:

- `{persona_name}` — the persona being prosecuted as
- `{audit_report_bullets}` — Stage 1 audit (compact bullets)
- `{pre_resolved_hard_findings}` — anything Stage 1 already raised
- `{active_critical_pair_subset}` — `P-CLASS-SCOPE, P-FULL-FILE, P-BRIEF-WHAT-NOT-HOW, P-BRIEF-GOAL-VERIFIABILITY, P-BRIEF-NON-GOAL-REALITY, P-BRIEF-PROBLEM-CONCRETENESS, P-BRIEF-OPEN-QUESTION-FORM, P-BRIEF-COHORT-CITATION`
- `{target_locator}` — the brief path
- `{how_to_get_it}` — `Read <brief_path>`; agents Read source-of-truth files (spec.md, CLAUDE.md, project memory, decisions.md, persona files) on demand
- `{pr_description_or_brief_mapping}` — N/A (the brief IS the artifact under review; there's no upstream brief mapping)
- `{skill_specific_extensions}` — *Imagine you are the engineering-plan author who must turn this brief into a chunk DAG. Where does the brief leave you guessing? Where does it under-constrain a Goal so badly that two engineering-plan authors would chunk it differently? Where does a Non-goal feel like a platitude that won't actually stop scope creep? Where does the Solution describe a "what" that secretly imports an architectural commitment? Where would a downstream chunk plan have to invent product policy because the brief ducked the question?*
- `{skill_specific_preamble}` — none (the author-side `premise_interrogation: passed/failed` doesn't run at review time; Stage 1's three trace blocks are the equivalent ground-truth substitute)
- `{skill_specific_resets_block}` — none (RESETs are an engineering-plan-only mechanism; briefs don't have an environment-vs-plan separation)

The brief content is small enough to pass inline (typically <200 lines). The orchestrator does NOT inline source-of-truth file contents — agents Read on demand.

### Author-sidecar consultation in agent prompts

When the brief-author sidecar is present, prepend this directive to every Stage 2 agent prompt:

> **Author-side ground-truth (verified at write time — do NOT re-prosecute):**
>
> The brief was written through `/brief-author`, which already ran ground-truth verification on each cross-document claim and self-prosecution against this brief. The following claims are settled and MUST NOT be re-prosecuted as hallucinations:
> - `claims_verified`: <count> claims verified against spec.md / CLAUDE.md / project memory / external API client.
> - `self_prosecution_findings`: <count> findings the author skill already filed and resolved at write time.
>
> If you believe an author-verified claim is now wrong, you MUST cite a *specific change* in the upstream source (spec.md / CLAUDE.md / memory) since `last_brief_sha256` was computed. Without that citation, the finding is auto-retracted.
>
> Sidecar path: `~/.claude/cache/author-state/<feature>__brief.json`. Read on demand if needed.

When the sidecar is absent, omit the directive.

---

## Stage 3 — Orchestrator decision

Stage 3 runs in the main thread.

### 3a. Apply Stage 1 mechanical fixes

Already done at end of Stage 1. Confirm the brief matches the post-fix state.

### 3b. Filter Stage 2 fix lists against critical-pair policies

For each finding from each persona:

- Contradicts an active critical-pair policy (P-BRIEF-WHAT-NOT-HOW, P-BRIEF-GOAL-VERIFIABILITY, P-BRIEF-NON-GOAL-REALITY, P-BRIEF-PROBLEM-CONCRETENESS, P-BRIEF-OPEN-QUESTION-FORM, P-BRIEF-COHORT-CITATION, P-CLASS-SCOPE, P-FULL-FILE) → retract. Note in verdict.
- Duplicates a Stage 1 hard finding already mechanically fixed → retract.
- Re-prosecutes an author-sidecar-verified claim without naming a concrete upstream change → retract.
- Otherwise → keep.

### 3c. Detect cross-persona disagreement

For each brief span, collect surviving findings.

- Two personas propose contradictory fixes for the same span → label `STABLE_DISAGREEMENT`. Do not auto-apply.

### 3d. Consolidate non-conflicting fixes

Deduplicate (same finding flagged by multiple → merge, attribute to all). Group by section. Apply in a single editing pass to the brief file, ordered by severity (CRITICAL → HIGH → MEDIUM → LOW).

**Cross-file fix scope (brief layer).** A persona's fix may have substance that binds beyond the brief itself. Detect by scanning the fix prose for cross-file scope markers — literal mentions of `spec.md`, `decisions.md`, `CLAUDE.md`, project-memory paths (any path under `~/.claude/projects/`, `MEMORY.md`, or `memory/`), OR phrases that signal forward-binding scope: `binds for all`, `cross-cutting effect`, `for all future readers`, `negative decision`, `arbitrate`, `bound across briefs`, `bound across features`. When a fix carries any of these markers:

- **Mention of `spec.md`** → DO NOT auto-edit. Spec amendments are a stop-the-world decision. Surface as `OPEN_QUESTION`: "fix would amend spec.md — user arbitrates whether the spec needs updating or the brief should be re-scoped."
- **Mention of `decisions.md`** → write the dated entry to `features/<feature>/decisions.md` per the standard pattern (today's date, current `round_number`, bound decision in one sentence, rationale 1-3 sentences, cross-link from the brief).
- **Mention of `CLAUDE.md`** → DO NOT auto-edit. CLAUDE.md is the project's bound-invariant ledger; amendments are user-only. Surface as `OPEN_QUESTION`: "fix would amend CLAUDE.md — user arbitrates."
- **Mention of project-memory paths** (`~/.claude/projects/<project>/memory/<file>.md`, `MEMORY.md`, or any path under `memory/`) → DO NOT auto-edit. Memory files carry the same bound-invariant authority as CLAUDE.md. Surface as `OPEN_QUESTION`: "fix would amend project memory at `<path>` — user arbitrates."

Record cross-file edits in `cross_file_edits[]` for the per-round metrics. The four upstream-invariant sources (spec, CLAUDE, memory, decisions) all sit above the brief in the authority order; only `decisions.md` is feature-scoped enough that this skill auto-writes it. The other three are project-wide and require explicit user action.

**Authority order when artifacts disagree** (highest to lowest):

1. `spec.md` / `context/specs/*.md` — product master-spec; the brief inherits, never overrides.
2. `CLAUDE.md` and project memory — bound-invariant ledger; the brief inherits, never overrides.
3. `features/<feature>/decisions.md` — durable arbitration record at the feature scope.
4. The brief under review.

When a finding's substance reveals contradiction across these files, the brief aligns to the upstream sources. Contradiction *between* spec.md and CLAUDE.md / project memory escalates as `OPEN_QUESTION` (user arbitrates which is canonical).

**Forbidden fixes:**

- Weakening the brief (removing Goals, dropping Non-goals to bypass enforcement, softening verifiability) → escalate as `OPEN_QUESTION`.
- Auto-editing spec.md or CLAUDE.md → escalate as `OPEN_QUESTION`.
- "Leaving details for engineering plan" — if the brief is unclear now, the engineering-plan author will hallucinate.
- Adding implementation detail to fix a Goal-verifiability finding (P-BRIEF-WHAT-NOT-HOW retracts this; the right fix is to add an *observable* success criterion, not a how).

### Post-fix premise verification

Runs in the main thread. Same procedure as the sister skills, scoped to the brief's verifiable claims:

1. **Identify added or rewritten prose** in the post-fix brief.
2. **Identify verifiable claims** using LLM judgment:
   - **Spec reference**: "spec.md §X authorizes Y"
   - **Memory reference**: "project memory says Z"
   - **Cohort claim**: "~N users / books / authors"
   - **Decisions reference**: "decisions.md entry W bound this"
3. **Verify each claim** with the cheapest falsifying check: `Read` the cited file and grep for the verbatim phrase.
4. **File falsified claims** as `FIX_INTRODUCED_PREMISE_INVERSION` blockers.

Verification stats are recorded for the verdict template.

### Same-round focused re-prosecution on rewritten prose

Runs once after Post-fix premise verification, before classification. **Bounded: exactly one re-pass; never an inner loop.**

Procedure mirrors `/plan-review-v2`:

1. **Identify diff hunks** the orchestrator wrote in 3a, 3d, and Post-fix premise verification's claim-correction edits. Capture (file, before-text, after-text) tuples. Cross-file edits to `decisions.md` are included.
2. **Spawn one focused agent per persona** that reviewed the brief in Stage 2. Use the `_review-common/agent-prompt.md` template with the same substitutions Stage 2 used, except override:
   - `{target_locator}` — the brief path plus the diff-hunk list inline as before/after blocks (and any cross-file diff hunks to `decisions.md`).
   - `{skill_specific_extensions}` — *Review ONLY the diff hunks listed below. The whole-brief version was prosecuted in Stage 2; this pass exists to catch defects introduced by the round-N orchestrator edits themselves. File findings on the rewritten prose's: (a) internal consistency with the unchanged sections, (b) cross-reference correctness with decisions.md / spec.md / CLAUDE.md, (c) any verifiable claim that is unverified, (d) re-introduced contradictions where an earlier fix accidentally undid a downstream consistency. Filter findings to severity HIGH and MEDIUM only — LOW polish on freshly-written prose is round-N+1 territory.*
3. **Filter re-pass fix lists through Stage 3b** (critical-pair retraction).
4. **Detect cross-persona disagreement on diff-hunk spans** (Stage 3c).
5. **Apply surviving re-pass findings** as additional Stage 3d edits.
6. **Re-run Post-fix premise verification** on the re-pass edits.
7. **No further re-pass.** Findings that survive become Stage 3e blockers.

**Skip conditions.** The re-pass is skipped (recorded as `re_pass_ran=false`) when ALL of:

- Stage 3d applied zero fixes.
- Post-fix premise verification filed zero falsified claims.
- Cross-file edits applied = 0.

Re-pass stats persisted to `per_round_metrics`.

### 3e. Classify remaining unresolved findings

Active classes for brief review: `STRUCTURAL_SHAPE_FAILED`, `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `FIX_INTRODUCED_PREMISE_INVERSION`, `POLISH_PLATEAU`, `REPO_STATE_DRIFT`.

**Carry-forward consultation (decisions-log-first, then ephemeral cache).**

Same two-priority pattern as the sister skills.

**Priority 1 — `decisions.md` lookup** (durable arbitration; persists across rounds). Read `features/<feature>/decisions.md`. Search for entries whose Decision subject substring-matches the finding's surface.

- **Strong match** — entry quotes the same identifier or phrase the finding cites verbatim.
- **Topical match** — entry's title or Why paragraph names the same concept (cohort threshold, scope kill, user-facing change, etc.).

If a strong or topical match exists AND the entry is dated AND bound:

- **Finding contradicts the bound decision** → drop the finding. Record in verdict as `[CARRY-FORWARD via decisions.md] {finding} — bound by decisions.md entry "<title>" (<date>): "<verbatim summary>"`. Increment `decisions_md_consultation.findings_dropped`.
- **Finding consistent with bound decision but flags a new dimension** → keep the finding but surface the bound decision in the blocker line.

**Priority 2 — `recently_resolved_blockers` ephemeral cache** (state-file). Apply only to findings that survived Priority 1.

Check entries where `carry_forward_until_round >= round_number` AND the entry's `path_or_section` overlaps the finding's section heading or quoted phrase. (At the brief layer, `path_or_section` is always a section heading or quoted phrase from brief prose — briefs don't cite path:line, so the overlap heuristic stays in section-name space. Don't import the file:line overlap behavior from `/plan-review-v2` and `/review-pr-v2` where chunks and PRs do cite path:line.) If a match exists:

- **Downgrade to `OPEN_QUESTION`** with the prior `user_decision` surfaced verbatim.
- The persona's claim survives only if `current_reclassification_justification` was filed in `prior_blockers`.

Record both consultations in `decisions_md_consultation` and the existing carry-forward stats.

### 3f. Render verdict

Verdict gate logic (brief layer):

- **APPROVED** when ALL of:
  - Stage 0 Structural Shape Check exited clean
  - Tier-1 weight = 0
  - Tier-2 weight ≤ 4
  - No `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `FIX_INTRODUCED_PREMISE_INVERSION`, `STRUCTURAL_SHAPE_FAILED`, `REPO_STATE_DRIFT`
- **NEEDS USER INPUT** otherwise.

Compute Tier-1 weight (CRITICAL=8, HIGH=4, MEDIUM=2, LOW=1) and Tier-2 weight after fix application.

### 3g. Output

```
## Brief Review v2 Complete: {brief_path}

**Round:** {round_number} {| `(round 1 — no prior state)` | `(loaded from cache: {round_number-1} → {round_number})` | `(state file missing; cold start)`}
**State source:** {`Loaded from ~/.claude/cache/review-state/<feature>__brief.json` | `Round 1 (no prior state)`}
**Author sidecar:** {`consulted; N claims verified skipped; M self-prosecution findings skipped` | `absent (brief was hand-written)` | `present but SHA differs (treated as hint)`}
**Authoring mode warning:** {`none` | `sidecar reports authoring_mode: "draft" — /brief-author --draft skipped ground-truth and self-prosecution; reviewer-side feedback runs but the artifact was not verified at write time`}
**Personas:** {names}
**Stage 0 shape check:** PASS / N hard findings (sections / forbidden patterns / implementation creep)
**Stage 1 audit:** spec_trace PASS / N hard; project_memory PASS / N hard; decisions_log PASS / N hard
**Stage 1 mechanical fixes applied:** {count}
**Stage 2 personas:** {N} agents in parallel
**Stage 3 fixes applied:** {count} (HARD: {n}, SOFT: {n})
**Stage 3 retractions (critical-pair policy):** {count}
**Cross-file edits applied:** {count}
  - {file path}: {one-line summary}
  ... (one bullet per cross-file edit; omit when count = 0)
**Carry-forward consultation:**
  - decisions.md matches: {n}; findings dropped via decisions: {n}
  - state-file matches: {n}; downgraded to OPEN_QUESTION: {n}; survived with current_reclassification_justification: {n}
**Post-fix premise verification:** verification_attempts={n}; verified={n}; falsified={n}; new_blockers_filed={n}
**Same-round re-prosecution:** ran={bool}; diff_hunks_reviewed={n}; additional_fixes_applied={n}; findings_persisted_to_blockers={n}
**Final Tier 1 weight:** {n}
**Final Tier 2 weight:** {n} (floor: 4)

### Changes Made
- {bullets of significant edits, including any cross-file edits to decisions.md}

### Retractions
- {finding} → retracted because {critical-pair policy / pre-resolved by Stage 1 / superseded / re-prosecuted author-verified claim without justification}

### Blockers (if any)
- [STRUCTURAL_SHAPE_FAILED] {finding} — fix and re-invoke.
- [STABLE_DISAGREEMENT] {finding} — Persona A: {fix A}; Persona B: {fix B}. Pick one.
- [OPEN_QUESTION] {finding} — {question}.
- [FIX_INTRODUCED_PREMISE_INVERSION] {section}: orchestrator-applied fix asserts "{verbatim claim}"; verification: {what was run}; actual: "{contradicting evidence}". Working tree dirty.
- [POLISH_PLATEAU] {finding} — non-blocking; ship is acceptable.
- [REPO_STATE_DRIFT] HEAD changed from {sha} to {sha}. Re-run.

### Brief Status: APPROVED / NEEDS USER INPUT
```

If `NEEDS USER INPUT`: user resolves blockers and re-invokes. The next run is fresh — round memory carries forward, prior_blockers reload.

---

## Hard rules

- **Status-frontmatter check is mandatory and runs first.** A brief with frontmatter `Status: needs-user-input` is mid-cycle authoring state; skill refuses to run against it and points the user back at `/brief-author`. The check is deterministic and runs before Stage 0.
- **Stage 0 Structural Shape Check is mandatory.** A brief with missing required sections or implementation creep is unprosecutable; LLM judgment on a structurally-broken brief produces noise.
- **Stage 1 is mandatory.** Stage 2 personas reading the brief without the audit report will re-prosecute spec / memory / decisions facts.
- **Round Memory Pass is mandatory.** Skipping it disables carry-forward consultation. State file lives at `~/.claude/cache/review-state/<feature>__brief.json` (NOT in the project repo).
- **Author sidecar consultation is mandatory when the sidecar exists.** The brief-author already verified claims and self-prosecuted; re-prosecuting author-verified claims without a concrete upstream-change citation is a forbidden finding. The sidecar at `~/.claude/cache/author-state/<feature>__brief.json` is the brief-layer's analog of Stage 1's pre-resolved findings.
- **Orchestrator verifies its own edits.** Post-fix premise verification runs after Stage 3d, before classification.
- **Carry-forward consultation is mandatory and decisions-log-first.** Before emitting any blocker, consult `features/<feature>/decisions.md` (durable arbitration) FIRST, then `recently_resolved_blockers` (ephemeral cache). Findings contradicting a bound `decisions.md` entry are dropped (not OPEN_QUESTION).
- **Cross-file fix scope is mandatory when triggered.** A persona's fix mentioning `decisions.md` (or carrying forward-binding markers) MUST receive a corresponding decisions.md edit in the same Stage 3d application. Mentions of `spec.md` or `CLAUDE.md` escalate as `OPEN_QUESTION` — the brief skill never auto-edits the project's bound-invariant ledger.
- **Same-round focused re-prosecution is mandatory** when ANY of: Stage 3d brief fixes > 0, cross-file edits > 0, or Post-fix premise verification falsified-claim count > 0. Bounded: exactly one re-pass; never an inner loop. Skipped only when ALL three are zero.
- **Stage 2 agents return fix lists; never edit files.** All edits applied by orchestrator in Stage 3.
- **Stage 3 applies critical-pair policies before applying fixes.** Findings contradicting a policy are retracted.
- **Never** mark APPROVED while any blocker class is non-empty.
- **Never** weaken the brief to resolve a finding (drop Goals, soften verifiability, remove Non-goals). That's `OPEN_QUESTION`.
- **Always** quote verbatim from brief, spec, memory, or audit_report when justifying a finding.
- **Always** label remaining findings with their blocker class.
- **No multi-round inner loop.** The same-round re-prosecution is exactly one pass over diff hunks.

## Compliance self-check (before rendering verdict)

- [ ] Status-frontmatter check ran first; not bypassed.
- [ ] Stage 0 Structural Shape Check ran; required sections verified; banned patterns absent.
- [ ] Round Memory Pass ran; reviewer state loaded; author sidecar consulted (or marked absent).
- [ ] Stage 1 ran in full: spec trace, project memory consistency, decisions log consistency, brief style supplements.
- [ ] Stage 2 spawned all M persona agents in parallel.
- [ ] Stage 3 applied critical-pair retractions before applying fixes.
- [ ] Post-fix premise verification ran on orchestrator-rewritten prose.
- [ ] Same-round re-prosecution ran (or skip conditions met and recorded).
- [ ] Carry-forward consultation: Priority 1 (decisions.md) ran first, Priority 2 (state-file) ran second; both metrics recorded.
- [ ] Verdict template includes all metric lines, even when count = 0.
- [ ] Cross-file fix scope checked: `decisions.md` edits applied; mentions of `spec.md` / `CLAUDE.md` / project-memory paths escalated as `OPEN_QUESTION`.
- [ ] State file persisted with new round entry appended.

## Edge cases

- **Brief file not found:** report and exit; no state-file changes.
- **Persona file not found:** auto-resolution falls back to next default persona; explicit personas stop and ask.
- **`spec.md` missing:** Skill warns but proceeds. Spec trace marked `N/A — no spec to anchor against`. The brief layer requires spec.md for full prosecution; persona findings about spec contradiction are downgraded to `OPEN_QUESTION` (user resolves whether to create spec.md or accept the brief as the upstream).
- **Project memory absent:** warn and proceed. CLAUDE.md is the minimum upstream invariant source. Memory entries marked `0 consulted` in Stage 1.
- **Brief authored via `/brief-author --draft`** (sidecar `authoring_mode: "draft"`): proceed with full prosecution; warn in verdict that the artifact is unhardened. The user invoked `--draft` deliberately and wants reviewer-side feedback before promoting to a hardened brief.
- **Author sidecar SHA differs from brief SHA:** user edited the brief manually after `/brief-author` emitted. Treat sidecar's `claims_verified` as a hint, not a binding skip-list. Stage 2 may re-prosecute spans where user-edits overlap author-verified claims.
- **State file missing for a brief that has clearly been reviewed before** (user wiped `~/.claude/cache/`): cold start at round 1. The ephemeral `recently_resolved_blockers` cache is lost, but `decisions.md` is still consulted via Priority 1 carry-forward, so user-bound decisions survive the cache wipe.
- **Brief path changed between invocations** (feature renamed): slug derivation produces a different state file path; this is a cold start under the new slug. User can manually copy the old state file if continuity is desired.
- **HEAD changes mid-review:** emit `REPO_STATE_DRIFT`. User re-runs.
- **Brief proposes amendments to spec.md or CLAUDE.md:** Forbidden auto-edit. Surface as `OPEN_QUESTION`; user arbitrates whether the amendment is correct and commits to running the project's spec/CLAUDE amendment process out-of-band.
- **Multi-feature briefs (rare):** Refuse. The brief skill operates on one `features/<feature>/brief.md` at a time. If the user has a multi-feature umbrella brief, ask them to split it into per-feature briefs first.

---

## Relationship to sister skills

- **`/brief-author`** writes the brief and the author sidecar this skill consults. The author runs ground-truth verification and self-prosecution at write time; this skill (the reviewer) consults the sidecar to skip re-prosecuting author-arbitrated claims and prosecutes only what the author missed or what the user introduced via manual edits since.
- **`/engineering-plan-review-v2`** prosecutes the brief at the engineering-plan layer (premise interrogation §brief-environment sub-pass). Findings raised there belong upstream — feeding back into the next `/brief-author` invocation's State-load stage via warm-mode carry-forward, OR triggering a `/brief-review-v2` re-invocation for an external audit.
- **`/plan-review-v2`** indirectly consumes the brief (via the engineering plan). Brief edits cascade through the engineering-plan-review's BRIEF_AMENDMENT_NEEDED class.

**No Imagined-Implementer phase.** `/engineering-plan-review-v2` runs an Imagined-Implementer dry-run between Persona Prosecution and Orchestrator Decision because the engineering plan has *multiple* downstream artifacts (the chunk plans) and the dry-run surfaces undecided cross-chunk decisions before any chunk is written. The brief layer's downstream is a *single* artifact (`engineering-plan.md`) authored by a single skill (`/engineering-plan-author`); the imagined-downstream-author lens folds into Stage 2's `{skill_specific_extensions}` prompt instead of running as a separate phase. If the brief's downstream were ever to fan out (e.g., a future `/api-contract-author` consuming the brief's contracts directly), this skill would gain an Imagined-Implementer phase.

The brief is the highest-leverage artifact; this skill exists to give it the same adversarial review surface the engineering plan and chunk plans already enjoy.
