---
name: brief-review-v2
description: Adversarial single-pass review of a feature's `brief.md` — the upstream source-of-truth the engineering plan and chunk plans descend from. Applies fixes directly and returns APPROVED or NEEDS USER INPUT with labeled blockers. Use after `/brief-author` lands a clean draft. Sister to `/engineering-plan-review-v2` and `/plan-review-v2`.
user-invocable: true
---

# Brief Review v2 — Staged Single-Pass

The brief is the highest-leverage artifact in the feature lifecycle: every downstream artifact (engineering plan, chunk plans, code) descends from it. A brief that contradicts its own Goals, invents a user population, or smuggles a Non-goal-violating Goal will cascade five rounds of review machinery to surface — and the surface itself doesn't repair the brief, only the descendants. This skill prosecutes briefs through a Structural Shape gate plus three stages, with bounded same-round verification on orchestrator-rewritten prose. Never a multi-round inner loop — survivors of the bounded same-round re-pass land in the verdict and the user re-invokes.

This is the brief layer. Sister skills `/engineering-plan-review-v2` (engineering-plan layer) and `/plan-review-v2` (chunk-plan layer) review downstream artifacts. If the user asks for review of an engineering plan or chunk plan, redirect.

## Shared scaffolding

- `~/.claude/skills/_review-common/principles.md` — stance, banned rationalizations, severity/tier, plan style rules
- `~/.claude/skills/_review-common/round-memory.md` — state file, load, capture priority, persist
- `~/.claude/skills/_review-common/orchestrator.md` — the shared Stage 3 spine
- `~/.claude/skills/_review-common/agent-prompt.md` — persona-agent prompt template
- `~/.claude/skills/_review-common/critical-pairs.md` — active subset for brief review: `P-CLASS-SCOPE, P-FULL-FILE` (universal) plus the brief-specific pairs defined in this skill (P-BRIEF-WHAT-NOT-HOW, P-BRIEF-GOAL-VERIFIABILITY, P-BRIEF-GOAL-OUTCOME-SCOPE, P-BRIEF-NON-GOAL-REALITY, P-BRIEF-PROBLEM-CONCRETENESS, P-BRIEF-OPEN-QUESTION-FORM, P-BRIEF-COHORT-CITATION)
- `~/.claude/skills/_review-common/blocker-classes.md` — blocker registry + verdict gate

## Tribunal stance (brief-specific)

**SPEC IS CANONICAL, PROJECT MEMORY IS LAW.** Two upstream sources bound this review:

1. **`spec.md` and `context/specs/*.md`** are the product master-spec; brief Goals must trace to spec capabilities; brief Non-goals must not contradict spec promises.
2. **`CLAUDE.md` and project memory** (`~/.claude/projects/<project>/memory/`) carry the project's bound invariants — "no test accounts in production data", "no existing users yet", "records must resolve correctly or not at all", domain-model architecture rules, etc. A brief that contradicts an invariant is solving a phantom problem; the prosecution surfaces this as a `FIX_INTRODUCED_PREMISE_INVERSION`-class finding even when it appears in the original draft (the "fix" was the brief author's act of writing the contradicting prose).

There is no equivalent of "REPO IS LAW" at the brief layer — briefs don't cite path:line or identifiers, so there's no on-disk code to ground claims against. Stage 1's verification target is the upstream documents (spec, CLAUDE, memory, decisions log), not the running codebase.

## Active critical-pair policies (brief layer)

These resolve oscillation hazards specific to brief review. The hosting skill applies them silently in Stage 3; persona findings that contradict an active policy are retracted, not relitigated.

**P-BRIEF-WHAT-NOT-HOW — Brief describes WHAT, engineering plan describes HOW.** The Solution / Goals / User-facing changes sections name product-visible shape and behavior, not architecture, file paths, schema changes, or implementation tactics. A finding demanding architecture detail / implementation specifics in the brief is invalid; a finding flagging implementation creep into the brief (e.g., file paths, function names, schema columns appearing in Solution) is valid.

**P-BRIEF-GOAL-VERIFIABILITY — Each Goal must have a verifiable success criterion.** "Better discoverability" is invalid; "the home screen shows a 'recently active teammates' row above the task list" is valid. A finding requesting more specific *implementation* of a Goal is invalid (that's engineering-plan territory); a finding requesting a verifiable success criterion for a vague Goal is valid.

**P-BRIEF-GOAL-OUTCOME-SCOPE — Goals state outcomes, name their domain, and name their authoritative signal.** Three failure shapes, all valid findings (see `principles.md` § Outcome-scope parity). (1) A Goal phrased as a bare mechanism — "using an allowlist/ML approach", "via a dedupe step", "with an LLM pass" — is a finding: the technique is satisfiable on one surface while the outcome ships on none whole. The fix is to rewrite the Goal as the observable result, NOT to demand more implementation detail (that would contradict P-BRIEF-WHAT-NOT-HOW; the mechanism moves to the engineering plan, it does not get expanded in the brief). This rule is the *durable* fix and is load-bearing: the engineering-plan-layer Scope-fidelity Adversary is defeated by a mechanism-phrased Goal — a reader taking the mechanism words literally-disjunctively acquits a plan that ran one technique on one surface and another on another. The downstream parity check only becomes reliable once the Goal is outcome-phrased, so this is a finding to hold firm on, not a stylistic nicety. (2) A Goal carrying a domain quantifier ("every", "across", "all", "any", "going forward", "at every surface") that does not name the domain it ranges over — which surfaces, media types, call paths, cohorts — is a finding: an unnamed domain cannot be checked for coverage downstream, so a subset delivery passes review and the gap surfaces only at PR review or as a half-shipped feature. (3) A Goal whose outcome must be judged on a distinguished signal — "the same junk verdict that governs the purge", "judged on the work itself", "on the restored author links" — that does not name that authoritative signal is a finding: without it named, the downstream adversary cannot detect delivery on a weaker-substitute proxy or an irreversible action taken before the signal exists. A finding demanding the domain or signal be named is valid; a finding demanding an exact enumeration the brief author cannot know yet (e.g., every file path) is invalid — the domain and signal are product-level (surfaces, cohorts, media types, "the confident classifier verdict"), not implementation-level.

**P-BRIEF-GOAL-MEASURE — Each Goal names the check that proves it shipped whole.** The `Measured by:` clause is a query, a named test, a CI gate, or a counted set — the thing you would run to answer *"did this ship whole, or on a subset?"* A Goal with no such clause is a valid finding, because completeness that cannot be checked cannot be defended: the engineering plan narrows the domain, every conformance gate passes, and the gap surfaces at PR review or in production. This is the direct upstream fix for the outcome-scope parity failure in `principles.md`. Two invalid finding shapes: demanding an adoption or usage percentage (this project is pre-launch with no users, so those thresholds are unfalsifiable — the honest threshold is a *domain plus a check*), and demanding the clause name the delivering chunk (that is the engineering plan's `Verified by` column; this names the check, not the chunk).

**P-BRIEF-SCOPE-BUCKETS — Each scope exclusion sits in the bucket that matches its actual commitment.** The four buckets encode three different states a single Non-goals list collapses. Valid findings: an item in `Intentionally deferred` with no destination (an undestined deferral is indistinguishable from a silent narrowing — the promise has no address, so nothing will ever notice it was not kept); an item in `Not planned` that the brief or `decisions.md` elsewhere treats as committed-later; an item in `Intentionally deferred` that nothing has actually committed to, which manufactures a promise to make a cut look softer than it is. Invalid: demanding items be moved between the two non-committal buckets on taste, or demanding every bucket be non-empty. The bucket is load-bearing downstream — a narrowing landing in `Intentionally deferred` with a destination is an *approved cut* the Scope-fidelity Adversary will not flag — so mis-filing an item either manufactures noise or launders a real narrowing.

**P-BRIEF-NON-GOAL-REALITY — Non-goals must be plausible scope kills, not platitudes.** ("Non-goal" throughout this skill means any entry in the three exclusion buckets — `Intentionally deferred`, `Not in scope (this release)`, `Not planned` — or, on a legacy brief, the bare `## Non-goals` list.) "We won't break existing things" is a platitude (no feature plans to break things). "We won't change the friend-graph data model" is a real scope kill if the feature could plausibly require such a change. A finding flagging platitude Non-goals is valid; a finding demanding more Non-goals when the existing list already covers the plausible scope-creep surface is invalid.

**P-BRIEF-PROBLEM-CONCRETENESS — Problem statement names a user-visible failure with quantified cohort or observable behavior.** "Users want better X" is invalid (no quantification, no cohort). "~400 active vendors are missing from search results because the upstream ingest does not hydrate their canonical IDs" is valid. A finding requesting concreteness on a vague problem is valid; a finding demanding implementation detail in the problem statement is invalid (Problem describes the failure, not the fix).

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
/brief-review-v2 user-profile-sync

# Explicit path
/brief-review-v2 features/user-profile-sync/brief.md

# Explicit personas (overrides default)
/brief-review-v2 user-profile-sync --personas product architecture

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
   ↓ 3b retracts against round-memory tags + critical-pair policies, THEN
   ↓ 3b.5 Class Sweep             (one agent per distinct recurring category)
   ↓   walks the brief's peer-set (every Goal / Non-goal / User-facing change /
   ↓   section) for siblings of each surviving seed class; NO repo grep — the
   ↓   brief document is the peer-set; promotes siblings before 3c and 3d
   ↓   (_review-common/class-sweep.md)
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
  `/brief-author <feature>` (warm mode is automatic). The author skill removes the `Status:` frontmatter
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
4. **`## Goals`** — section heading present; ≥1 bullet. Every bullet carries a `Measured by:` clause (P-BRIEF-GOAL-MEASURE); a bullet without one is `[HARD: Goal has no completeness check]`.
5. **`## Scope`** — section heading present, with the four `###` buckets: `In scope`, `Intentionally deferred`, `Not in scope (this release)`, `Not planned`. A bucket may be empty; the heading may not be missing, because an absent bucket and a deliberately-empty one read identically. Every `Intentionally deferred` bullet names a destination (`#NNN` or a follow-on feature slug) — a bullet without one is `[HARD: undestined deferral]` per P-BRIEF-SCOPE-BUCKETS.
   **Legacy shape.** A brief carrying a bare `## Non-goals` section instead predates the four-bucket convention. Treat it as the `Not planned` bucket and file ONE SOFT LOW finding recommending migration on the next substantive edit — do not file per-bullet findings, and do not sort the bullets into buckets as an auto-fix. Which bucket a settled exclusion belongs in is a product call per item; guessing it silently re-decides scope, which is the failure this whole section exists to prevent. If the correct bucket for an item is genuinely load-bearing to this review, raise it as `OPEN_QUESTION`.
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

Cohort references like "the `externalId` field" in Problem/Solution prose context are NOT matches — the schema-column regex requires the literal noun (`column` / `field` / `enum`) to precede the quoted identifier, so prose mentions of "the `externalId` field" in a Problem statement don't fire (no `column` or `enum` precedes the quoted token there).

The path-citation regex is applied to brief prose with backtick-fenced spans excluded. A reference like `` `src/lib/externalApi.ts` `` inside a sentence is fine; an unfenced `src/lib/externalApi.ts:42` is HARD.

### Behavior

- **All checks pass** → record `shape_clean=true` and proceed to Round Memory Pass.
- **Any HARD failure** → stop. Emit:

  ```
  BRIEF: <brief-path>
  STATUS: NEEDS USER INPUT (blocker: STRUCTURAL_SHAPE_FAILED)

  Stage 0 found N structural defects in this brief. Persona prosecution is not run
  because LLM judgment on top of a structurally-broken brief produces noise.

  - [HARD: missing required section] §Goals heading absent.
  - [HARD: implementation creep] line 42: "see src/lib/externalApi.ts:120-150" — briefs do not cite paths.
  - [HARD: addendum section] §Round-2 findings — findings integrate into the section they correct.

  Fix the structural defects above and re-invoke /brief-review-v2.
  ```

  No further stages run. SOFT findings are deferred to Stage 1's audit report (they don't block the gate but appear in the verdict's structural-lint summary).

- **SOFT-only failures** → record findings; proceed to Round Memory Pass. Stage 1e mechanical fixes will resolve them inline.

Why short-circuit: a persona reviewing a brief with a missing Goals section produces findings that assume the section exists — wasted reasoning budget. The gate is the sieve.

---

## Round Memory Pass (no LLM judgment)

Same purpose as the sister skills, same mechanism — `~/.claude/skills/_review-common/round-memory.md`.

The brief layer has a unique additional carry-forward source: the brief-author's sidecar at `~/.claude/cache/author-state/<feature>__brief.json`. The author skill already verified claims and applied self-prosecution; the reviewer must consult the sidecar to skip re-prosecuting what the author already arbitrated.

**Non-convergence tripwire (Feature-surface gate).** After loading state, evaluate the tripwire from `~/.claude/skills/_review-common/feature-surface-gate.md` § Non-convergence tripwire: `round_number >= 5` AND (open-blocker count not strictly decreasing over the last 3 entries of `open_blocker_history`, OR current `open_question_count >= 8`; cold-history fallback: `prior_blockers` length ≥ 8). Fired → file `FEATURE_NONCONVERGENCE` (HIGH), spawn the split-proposal agent (`model: "sonnet"`) per the gate file, render the proposal as a director decision in the verdict. On EVERY verdict, append `{round, open_blocker_count, open_question_count}` to `open_blocker_history` in the state file. Additionally: Stage 2 runs the Goal-cohesion check (trigger filter + adversary per the gate file's § Goal-cohesion check, spawned with the persona batch), filing `BRIEF_SCOPE_BUNDLE` — suppressed only by a bound size-acceptance row.

### State file

Location, schema, load rules, capture priority, and persist rules: `~/.claude/skills/_review-common/round-memory.md`. Read it. The brief layer adds:

- **Slug** — `<feature>__brief`, from `features/<feature>/brief.md`.
- **Extra field** — `author_sidecar_consulted: { sidecar_path, sidecar_present, claims_verified_skipped, self_prosecution_findings_skipped }`, written every round per the consultation below.
- **Blocker classes seen here** — `STRUCTURAL_SHAPE_FAILED`, `BRIEF_SCOPE_BUNDLE`, `FEATURE_NONCONVERGENCE`, `REMEDIATION_INCOMPLETE`, `DECISIONS_PROVENANCE_GAP`, plus the universal `STABLE_DISAGREEMENT` / `OPEN_QUESTION` / `FIX_INTRODUCED_PREMISE_INVERSION`. The last two are filed by the Remediation-completeness sub-pass below and are **exempt from `recently_resolved_blockers` carry-forward** — each is an assertion about the completeness of the carry-forward record itself, so retracting it against that record is circular. `DECISIONS_PROVENANCE_GAP` is additionally exempt from decisions-log-first retraction.
- **Extra field** — `remediation_completeness`, the per-blocker result of the sub-pass below. One entry per prior-round blocker, never sampled.

### Author sidecar consultation (brief-layer-unique)

Read `~/.claude/cache/author-state/<feature>__brief.json` if it exists. Extract:

- `claims_verified` count and `ground_truth_log` entries with outcome `verified` / `verified_softened` / `corrected`. These are claims the brief-author already grounded; Stage 2 personas MUST NOT re-prosecute them as hallucinations.
- `self_prosecution_findings` — findings the author skill already filed and resolved at write time. Stage 2 personas MUST NOT re-file them.
- `authoring_residual` — LOW residuals under the polish floor that the author skill explicitly accepted. These are not blockers; surface in the verdict as informational only.

If sidecar is absent (the brief was hand-written, not authored through `/brief-author`), record `author_sidecar_consulted.sidecar_present: false` and proceed; Stage 2 personas have full prosecution latitude.

If sidecar's `last_brief_sha256` differs from the current brief's SHA, the user edited the brief manually after authoring. Treat the sidecar's `claims_verified` as a *hint* (the author verified these against the prior version), not a binding skip-list — Stage 2 may re-prosecute spans where the user-edit overlaps an author-verified claim.

### Remediation-completeness pass (round_number > 1, MANDATORY)

Stage 3's same-round re-prosecution and its post-fix premise verification both scope to the **orchestrator's own** edits, inside the round that made them. Neither can see the remediation the *user* writes **between** rounds, which is the larger surface: a `NEEDS USER INPUT` verdict hands back N blockers, the user edits the brief, and the next round meets that new text with ordinary prosecution latitude and nothing else. The recurring failure is not a bad fix — it is a fix that lands in the Goal that motivated the blocker and never reaches what is coupled to it, so the blocker reads as closed while its consequences are unbuilt. `prior_blockers` and `recently_resolved_blockers` are consulted only to *retract* re-prosecution; nothing verifies *completion*. This pass is that check, and it runs before Stage 2 so its findings enter as `pre_resolved_hard_findings`.

For **every** entry in the prior round's `prior_blockers`, answer three questions and record the answer. Do not sample.

1. **Closed?** Locate the text that closes it and quote it. Nothing addressing the blocker means it is still open — carry it forward at its original class and severity rather than letting the round-counter launder it into a fresh finding.

2. **Swept?** This is the layer where the swept question bites hardest, because the brief's coupled sites are **downstream artifacts, not other paragraphs**. A brief amendment that widens a Goal, adds a Non-goal, accepts a residual, or narrows a domain must reach: the brief's own §Goals / §Non-goals / §User-facing changes (a residual accepted in a Goal and absent from §User-facing changes is disclosed to no reader who reads the second), **every `engineering-plan.md` that traces to this brief** — flat at `features/<feature>/engineering-plan.md`, or every track under `features/<feature>/plans/*/` per `~/.claude/skills/_plan-common/layout.md` — and their Brief-mapping Goals / Non-goals-enforcement tables, plus any chunk plan already written against the amended Goal. An amendment landing in the brief alone leaves every downstream plan delivering the superseded contract while both artifacts review clean in isolation; file `REMEDIATION_INCOMPLETE` (HARD, severity inherited). Under the tracked layout check **every** track — an amendment swept into one plan and not its sibling is the same defect with a narrower blast radius.

3. **Recorded?** An arbitration the user made to close a blocker belongs in `decisions.md`. Search for a bound Active-section entry covering it. A brief span that *cites* a `decisions.md` entry which does not exist is a `DECISIONS_PROVENANCE_GAP` (HARD, HIGH) — resolve every citation this round's modified sections introduced, by heading, not by date alone. An unrecorded arbitration cannot be retracted by decisions-log-first carry-forward next round, so the same ground is re-prosecuted indefinitely.

Record as `remediation_completeness` in the state file: `{blocker, closed: yes|no, closing_quote, coupled_sites_checked: [...], sites_missed: [...], decisions_entry: "<heading>" | "none — <class>"}`. An entry with an empty `coupled_sites_checked` answered only the first question; re-run it.

### Persist on exit

Per the shared file, plus `author_sidecar_consulted` ← what was consulted this round, and `remediation_completeness` ← this round's per-blocker result.

---

## Stage 1 — Ground truth pass (MANDATORY, MOSTLY MECHANICAL)

Produces an `audit_report` per brief. Stage 2 personas MUST NOT re-prosecute facts already verified here.

**LLM-judgment carve-out.** Sub-passes 1a-1c are fully mechanical (file Reads, regex matches, substring overlaps). Sub-pass 1d (brief style supplements) makes two lightweight LLM judgment calls (Goal verifiability, Non-goal reality) that no regex can capture. These are bounded — the questions are "is this Goal observable?" / "is this Non-goal a real scope kill?" — and each finding is filed at SOFT MEDIUM under the corresponding P-BRIEF-* policy. The orchestrator does not auto-fix; the user arbitrates at Stage 3 if disputed. The sister skills' Stage 1 sub-passes stay fully mechanical because the chunk/engineering-plan layer has `/plan-lint` to handle structural concerns; the brief layer has no equivalent, so 1d picks up the slack.

The brief layer has NO repo grep — briefs don't cite path:line or identifiers (Stage 0 already enforced no implementation creep). Stage 1's verification target is upstream documents only.

### 1a. Spec trace (mechanical)

Open `spec.md` (project root) and any `context/specs/*.md` whose subject matches the feature.

For each Goal in the brief, search the spec(s) for an anchor:

- **Strong anchor** — spec section explicitly names the same capability (e.g., brief Goal "5-review activation threshold" → spec.md §"Activation-threshold rule").
- **Implicit anchor** — spec section implies the capability (e.g., brief Goal "cart auto-clear" → spec.md §"Checkout flow" mentions "checkout removes items from the cart atomically").
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
  - Memory says "usernames are ASCII-only" + brief Goal says "support emoji usernames" → contradiction.
  - CLAUDE.md says "sessions expire after 30 minutes idle" + brief Goal says "sessions never expire" → contradiction.
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

Read `features/<feature>/decisions.md` if it exists. For each dated entry (only Active bound entries are consulted — skip the `## Archived (superseded / obsolete)` tail; per `~/.claude/skills/_review-common/principles.md` § What counts as a bound entry):

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
- Each Goal's `Measured by:` clause is actually a check — something runnable or countable — and not a restatement of the Goal in other words. A clause that reads "the feature works correctly" is a missing clause wearing a colon; file SOFT MEDIUM under P-BRIEF-GOAL-MEASURE.
- Each `Intentionally deferred` bullet's destination resolves: a `#NNN` that plausibly exists, or a feature slug that is a real or clearly-named future feature. File SOFT MEDIUM under P-BRIEF-SCOPE-BUCKETS on a bare "later" or "TBD".
- Each Non-goal is a real scope kill (lightweight LLM check; platitudes flagged SOFT MEDIUM under P-BRIEF-NON-GOAL-REALITY).
- Open questions are in question form (regex check: must contain `?` per bullet; statements flagged SOFT MEDIUM under P-BRIEF-OPEN-QUESTION-FORM).
- Cohort claims cite a source (Problem section: regex `~?\d+(-\d+)?\s+(users?|customers?|accounts?|records?)` — every match must be followed within 3 lines by a citation marker `(per `<file>` / `<query>`)` / "verified by" / "as of <date>"; uncited matches flagged SOFT MEDIUM under P-BRIEF-COHORT-CITATION).

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

Resolve personas (auto or explicit). Launch one Agent per persona, **all in parallel in a single message**, each with `model: "sonnet"` per `_review-common/agent-prompt.md` § Model pin — never inherit the session model; record `persona_model` in the review state. M agents.

### Spawn agents

Use the template in `~/.claude/skills/_review-common/agent-prompt.md`. Substitute:

- `{persona_name}` — the persona being prosecuted as
- `{audit_report_bullets}` — Stage 1 audit (compact bullets)
- `{pre_resolved_hard_findings}` — anything Stage 1 already raised
- `{active_critical_pair_subset}` — `P-CLASS-SCOPE, P-FULL-FILE, P-BRIEF-WHAT-NOT-HOW, P-BRIEF-GOAL-VERIFIABILITY, P-BRIEF-GOAL-OUTCOME-SCOPE, P-BRIEF-NON-GOAL-REALITY, P-BRIEF-PROBLEM-CONCRETENESS, P-BRIEF-OPEN-QUESTION-FORM, P-BRIEF-COHORT-CITATION`
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
> Two grounds let you file against a settled claim anyway. Both demand evidence you observed **this run**, quoted with `path:line`:
>
> 1. **Drift** — cite a *specific change* in the upstream source (spec.md / CLAUDE.md / memory) since `last_brief_sha256` was computed. The claim was true when verified and is not now.
> 2. **Never held** — cite the upstream span the claim asserts, showing it does not say what the author recorded. The verification itself was wrong.
>
> For either, set `exclusion_challenge: true` and populate `challenged_entry` (verbatim, from the sidecar) and `challenge_evidence` (`path:line` + verbatim quote). Without that anchoring the finding is malformed and discarded.
>
> Do NOT go hunting — a challenge is a byproduct of prosecution you were doing anyway, never a systematic re-audit of the author's log. And do NOT challenge on suspicion: "the author may not have checked carefully" is a banned rationalization, not evidence.
>
> The orchestrator re-verifies every challenge itself and logs the outcome either way. A rejected challenge costs you nothing.
>
> Sidecar path: `~/.claude/cache/author-state/<feature>__brief.json`. Read on demand if needed.

When the sidecar is absent, omit the directive.

**Orchestrator handling.** In Stage 3, partition findings on `exclusion_challenge: true` before the carry-forward pass. Discard as `malformed` any challenge missing anchored `challenge_evidence`. Re-verify each remaining challenge with one targeted Read against the cited span: upheld → the finding proceeds normally and the reviewer state records the author's log as wrong on that entry; rejected → retract with note `RETRACTED: exclusion challenge rejected; "<entry>" re-verified at <path:line>`. Log every challenge — upheld, rejected, malformed — into the reviewer state's `exclusion_challenges` array using the schema in `~/.claude/skills/_author-common/self-prosecution-protocol.md` § `sidecar.exclusion_challenges`.

This does not loosen the consultation rule: an unsupported re-prosecution is still auto-retracted, exactly as before. It only makes the retraction *visible*. The accumulated upheld/rejected rate is the evidence base for deciding whether mandatory author-sidecar trust is calibrated — a question that must be settled from this log, not from intuition.

**Not challengeable by this mechanism:** bound `decisions.md` entries and in-force `recently_resolved_blockers`. Those are user arbitrations, not author self-attestation. An `exclusion_challenge` flag set against one is stripped and the finding falls through to normal carry-forward retraction.

---

## Class Sweep (dedicated sibling-enumeration fan-out; runs as Stage 3b.5)

Runs after Stage 3b retracts findings against critical-pair policies, before Stage 3d applies anything — a category whose only seed just died at 3b must not be swept, and swept siblings must be fixed in the same editing pass as their seeds. Per `~/.claude/skills/_review-common/class-sweep.md` — read it for the mechanism, sweep-agent template, merge, and state/verdict schema. Brief personas file one instance of a recurring class per round (one non-verifiable Goal, one non-goal that isn't a real scope kill, one section carrying implementation creep, one banned-tense phrase) and the siblings leak out one per round otherwise.

**Procedure (per the shared file), with these brief-layer slots:**

- **Seed grouping.** Group the **3b survivors** by `class`. Every distinct `recurring_category` gets one sweep agent, `model: "sonnet"`; genuine singletons (`class_notion` absent / one-location peer-set — "the single Problem statement is wrong") are recorded `singleton: true` with no agent.
- **`{peer_set_definition}`** — the brief's repeated units: every `## Goals` bullet, every `## Non-goals` bullet, every `## User-facing changes` entry, every `## Open questions` item, every section body. Name the specific unit the seed's `peer_set` points at.
- **`{artifact_access}`** — `Read features/<feature>/brief.md` in full. **NO repo grep and no `propagated_identity` token-sweep** — briefs don't cite paths or identifiers (Stage 0 enforces no implementation creep), so every brief class is `recurring_category` and the brief document itself is the entire peer-set. The sweep may Read the upstream spec / CLAUDE.md / project-memory / decisions.md as *context* (to judge whether a sibling Goal is verifiable or a sibling Non-goal is real) but never as a peer-set to expand into.
- **`{layer_notes}`** — the brief-layer critical pairs bound the sweep: a "sibling" that P-BRIEF-WHAT-NOT-HOW would retract (an implementation-detail fix dressed as a verifiability sibling) is not a sibling. Findings whose evidence quotes an upstream spec/CLAUDE/memory invariant are Class A — siblings inherit the Class A exemption.
- **Merge.** Dedup siblings against the Stage 2 pool by `(class, section)`; route the new siblings through **Stage 3b critical-pair retraction** (same filter the seeds get) before folding them into Stage 3d consolidation. Record the `class_sweep` block in `per_round_metrics`.

Skip the stage (record `class_sweep.ran=false`) only when zero sweep-eligible categories exist among the surviving Stage 2 findings.

---

## Stage 3 — Orchestrator decision

Stage 3 runs in the main thread.

### 3a. Apply Stage 1 mechanical fixes

Already done at end of Stage 1. Confirm the brief matches the post-fix state.

### 3b. Filter Stage 2 fix lists against critical-pair policies

This layer runs no section-diff gate, so it emits no round-memory tags and the shared tag filter does not apply here. For each finding from each persona:

- Contradicts an active critical-pair policy (P-BRIEF-WHAT-NOT-HOW, P-BRIEF-GOAL-VERIFIABILITY, P-BRIEF-GOAL-OUTCOME-SCOPE, P-BRIEF-NON-GOAL-REALITY, P-BRIEF-PROBLEM-CONCRETENESS, P-BRIEF-OPEN-QUESTION-FORM, P-BRIEF-COHORT-CITATION, P-CLASS-SCOPE, P-FULL-FILE) → retract. Note in verdict.
- Duplicates a Stage 1 hard finding already mechanically fixed → retract.
- Re-prosecutes an author-sidecar-verified claim without naming a concrete upstream change → retract.
- Otherwise → keep.

### 3b.5 Class Sweep

Runs here — see "Class Sweep" above for the full procedure. Group the 3b survivors by class, sweep, then carry the merged finding set into 3c.

### 3c. Detect cross-persona disagreement

For each brief span, collect surviving findings.

- Two personas propose contradictory fixes for the same span → label `STABLE_DISAGREEMENT`. Do not auto-apply.

### 3d. Consolidate non-conflicting fixes

Deduplicate (same finding flagged by multiple → merge, attribute to all). Group by section. Apply in a single editing pass to the brief file, ordered by severity (CRITICAL → HIGH → MEDIUM → LOW).

**Cross-file fix scope (brief layer).** A persona's fix may have substance that binds beyond the brief itself. Detect by scanning the fix prose for cross-file scope markers — literal mentions of `spec.md`, `decisions.md`, `CLAUDE.md`, project-memory paths (any path under `~/.claude/projects/`, `MEMORY.md`, or `memory/`), OR phrases that signal forward-binding scope: `binds for all`, `cross-cutting effect`, `for all future readers`, `negative decision`, `arbitrate`, `bound across briefs`, `bound across features`. When a fix carries any of these markers:

- **Mention of `spec.md`** → DO NOT auto-edit. Spec amendments are a stop-the-world decision. Surface as `OPEN_QUESTION`: "fix would amend spec.md — user arbitrates whether the spec needs updating or the brief should be re-scoped."
- **Mention of `decisions.md`** → write the dated entry to `features/<feature>/decisions.md` per the template (today's date, current `round_number`, bound decision in one sentence, a `**Status:** bound` line, rationale 1-3 sentences, cross-link from the brief). Append it under the `## Active (bound)` heading. If the new decision *replaces* an existing Active bound entry on the same surface, in the SAME edit flip that older entry to `**Status:** superseded by "<new title>" (<today's date>)` and move it to the `## Archived (superseded / obsolete)` section — a superseded entry left reading `bound` would silently override the new decision (per `~/.claude/skills/_review-common/principles.md` § What counts as a bound entry).
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

Per `~/.claude/skills/_review-common/orchestrator.md` § Post-fix premise verification. The claims that matter at this layer are references, not behaviors: "spec.md §X authorizes Y", "project memory says Z", "decisions.md entry W bound this", and cohort claims ("~N users / accounts / records"). Verify by reading the cited file and grepping for the verbatim phrase.

### Same-round focused re-prosecution on rewritten prose

Per `~/.claude/skills/_review-common/orchestrator.md` § Same-round focused re-prosecution — one pass, bounded. Include cross-file edits to `decisions.md` in the diff-hunk set. The brief-layer defect to look for in fix prose: a fix that resolves one section's contradiction while re-introducing it against an unchanged section.

### 3e. Classify remaining unresolved findings

Active classes for brief review: `STRUCTURAL_SHAPE_FAILED`, `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `FIX_INTRODUCED_PREMISE_INVERSION`, `BRIEF_SCOPE_BUNDLE`, `FEATURE_NONCONVERGENCE`, `POLISH_PLATEAU`, `REPO_STATE_DRIFT`.

**Carry-forward consultation (decisions-log-first, then ephemeral cache).**

Same two-priority pattern as the sister skills.

**Priority 1 — `decisions.md` lookup** (durable arbitration; persists across rounds). Read `features/<feature>/decisions.md`. Search for entries whose Decision subject substring-matches the finding's surface.

- **Strong match** — entry quotes the same identifier or phrase the finding cites verbatim.
- **Topical match** — entry's title or Why paragraph names the same concept (cohort threshold, scope kill, user-facing change, etc.).

If a strong or topical match exists AND the entry is dated AND bound (in the `## Active (bound)` section with `Status: bound` — not `superseded`/`obsolete` in the `## Archived (superseded / obsolete)` tail; per `~/.claude/skills/_review-common/principles.md` § What counts as a bound entry):

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
  - No `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `FIX_INTRODUCED_PREMISE_INVERSION`, `STRUCTURAL_SHAPE_FAILED`, `BRIEF_SCOPE_BUNDLE`, `FEATURE_NONCONVERGENCE`, `REPO_STATE_DRIFT`
- **NEEDS USER INPUT** otherwise.

Compute Tier-1 weight (CRITICAL=8, HIGH=4, MEDIUM=2, LOW=1) and Tier-2 weight after fix application.

**Final line — verdict banner.** After the output block below, run the shared verdict-banner script and emit its output verbatim (`~/.claude/skills/_review-common/blocker-classes.md` § Verdict banner) as the **very last** thing in your response, so the verdict is visible without scrolling.

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
**Class sweep:** ran={bool}; sweep_agents={n}; siblings_found={n}; siblings_after_filter={n}
**Final Tier 1 weight:** {n}
**Final Tier 2 weight:** {n} (floor: 4)

### Class sweep audit
For each class swept (omit block entirely when class_sweep.ran=false):
- Class: {name} (recurring_category) — bare invariant: {bare_invariant}
- Peer-set: handed {peer_set_handed} → walked {peer_set_walked} {(widened — {widening_justification}) | (confirmed widest)}; {n} members; swept clean: {n}
- Instances: {seeds} seed + {siblings_found} sibling ({siblings_after_filter} survived critical-pair filter); resolution: all fixed this round | {n} escalated as {blocker class}
- Singleton classes recorded (no peer-set): {list, or none}

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

If `NEEDS USER INPUT`: the next step is **targeted edits to clear the listed blockers**, then re-invoke `/brief-review-v2` (optionally triage first with `/explain-blockers` or `/solve-blockers`). Do **not** re-run `/brief-author` to clear a handful of blockers — see the hard rule below. The next run is fresh — round memory carries forward, prior_blockers reload.

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
- **Class Sweep is mandatory** whenever a surviving Stage 2 finding declares `class_notion: recurring_category`. One sweep agent per distinct such category walks the brief's peer-set (every Goal / Non-goal / User-facing change / section) for siblings and promotes them to same-round findings at Stage 3b.5 — after 3b retraction, before 3c and 3d — so siblings and seeds pass through the same critical-pair filter and the same disagreement detection. NO repo grep — the brief document is the entire peer-set. Per `~/.claude/skills/_review-common/class-sweep.md`. Closes a defect class in the round it was found instead of leaking one sibling per round. Skipped only when zero sweep-eligible categories exist.
- **Same-round focused re-prosecution is mandatory** when ANY of: Stage 3d brief fixes > 0, cross-file edits > 0, or Post-fix premise verification falsified-claim count > 0. Bounded: exactly one re-pass; never an inner loop. Skipped only when ALL three are zero.
- **The Remediation-completeness pass is mandatory on every `round_number > 1`** (Round Memory Pass), and covers what the two verification stages above structurally cannot: both scope to the orchestrator's *own* edits, while the majority of text entering a round is remediation the **user** wrote between rounds to clear the last verdict's blockers. Every prior blocker gets all three questions — closed, swept into every coupled site, arbitration recorded in `decisions.md` — with no sampling. This layer's swept question is the sharpest in the suite, because a brief's coupled sites are **downstream artifacts rather than sibling paragraphs**: an amendment that lands in the brief alone leaves every engineering plan tracing to it delivering the superseded contract, and both artifacts review clean in isolation. Check every plan root the feature resolves to, not just one. Skipping the pass makes a `NEEDS USER INPUT` → re-invoke cycle non-convergent by construction.
- **Stage 2 agents return fix lists; never edit files.** All edits applied by orchestrator in Stage 3.
- **Stage 3 applies critical-pair policies before applying fixes.** Findings contradicting a policy are retracted.
- **Never** mark APPROVED while any blocker class is non-empty.
- **Never** weaken the brief to resolve a finding (drop Goals, soften verifiability, remove Non-goals). That's `OPEN_QUESTION`.
- **Always** quote verbatim from brief, spec, memory, or audit_report when justifying a finding.
- **Always** label remaining findings with their blocker class.
- **No multi-round inner loop.** The same-round re-prosecution is exactly one pass over diff hunks.
- **Do not re-run `/brief-author` to clear a completed review.** When the verdict is `NEEDS USER INPUT`, the next step is targeted edits that clear the listed blockers, then re-invoking `/brief-review-v2` (optionally triaged through `/explain-blockers` or `/solve-blockers`). Re-running `/brief-author` re-enters the full authoring pipeline over the whole brief — wrong tool for clearing a handful of blockers. Re-run the author skill only for the mid-cycle `Status: needs-user-input` refuse path (the artifact is already a partial draft and the author resumes it in warm mode), or the rare case where the brief is fundamentally broken and must be re-authored wholesale (ask in plain language).

## Compliance self-check (before rendering verdict)

- [ ] Status-frontmatter check ran first; not bypassed.
- [ ] Stage 0 Structural Shape Check ran; required sections verified; banned patterns absent.
- [ ] Round Memory Pass ran; reviewer state loaded; author sidecar consulted (or marked absent).
- [ ] **Remediation-completeness ran on every prior blocker** (`round_number > 1`): `remediation_completeness` holds one entry per entry in the prior round's `prior_blockers`, each with a non-empty `coupled_sites_checked` and an explicit `decisions_entry`. Every downstream plan root the feature resolves to was checked, not just one — an amendment swept into the brief alone leaves every engineering plan delivering the superseded contract, and both artifacts review clean in isolation. Any `REMEDIATION_INCOMPLETE` / `DECISIONS_PROVENANCE_GAP` filed appears in the verdict and was not dropped by carry-forward.
- [ ] Stage 1 ran in full: spec trace, project memory consistency, decisions log consistency, brief style supplements.
- [ ] Stage 2 spawned all M persona agents in parallel.
- [ ] Stage 3 applied critical-pair retractions before applying fixes.
- [ ] Class Sweep ran for every distinct recurring category among surviving Stage 2 findings — `class_sweep.sweep_agents_spawned` equals the count of distinct sweep-eligible categories, every agent recorded a `peer_set_size` + non-empty `swept_clean`, every surviving sibling appears in the fix set or a blocker (or `class_sweep.ran=false` recorded because zero sweep-eligible categories existed).
- [ ] Every sweep agent performed the **peer-set challenge** (`class-sweep.md` § The sweep, Method step 1) — each category records a non-empty `bare_invariant`, both `peer_set_handed` and `peer_set_walked`, and an explicit `peer_set_widened` flag with a justification when true. A `bare_invariant` that merely restates the seed's wording, or a `peer_set_walked` copied from `peer_set_handed` with no evidence the supertype question was asked, means step 1 did not run — re-run that agent. A faithfully-walked *narrow* peer-set reports clean while leaving the class open, and that failure is invisible in the instance counts, so it has to be checked on these fields directly.
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

**No Imagined-Implementer phase.** `/engineering-plan-review-v2` runs an Imagined-Implementer dry-run between Persona Prosecution and Orchestrator Decision because the engineering plan has *multiple* downstream artifacts (the chunk plans) and the dry-run surfaces undecided cross-chunk decisions before any chunk is written. The brief layer's downstream is normally a *single* artifact (`engineering-plan.md`) authored by a single skill (`/engineering-plan-author`); the imagined-downstream-author lens folds into Stage 2's `{skill_specific_extensions}` prompt instead of running as a separate phase.

**Exception — tracked features.** A feature whose delivery splits across tracks has one engineering plan per track under `features/<feature>/plans/<track>/` (see `~/.claude/skills/_plan-common/layout.md`), so the brief's downstream *does* fan out. The consequence the fan-out creates is Goal-clause ownership: when two plans both trace to one Goal, a clause of that Goal can fall between them and be delivered by neither. Until this skill grows a proper Imagined-Implementer phase, Stage 2's `{skill_specific_extensions}` prompt for a tracked feature MUST additionally ask: *for each Goal traced by more than one plan, is every clause claimed by exactly one plan?* An unclaimed clause is `BRIEF_GOAL_UNDELIVERED`; a clause claimed by two is an `OPEN_QUESTION` on ownership.

The brief is the highest-leverage artifact; this skill exists to give it the same adversarial review surface the engineering plan and chunk plans already enjoy.
