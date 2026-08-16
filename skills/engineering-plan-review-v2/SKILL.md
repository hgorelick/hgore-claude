---
name: engineering-plan-review-v2
description: Adversarial single-pass review of a feature's `engineering-plan.md` — the chunk-DAG layer between the brief and per-chunk plans. Applies fixes directly and returns CLOSED, APPROVED, or NEEDS USER INPUT with labeled blockers. Use after `/engineering-plan-author` lands a clean draft, before chunk plans are written. Sister to `/plan-review-v2` (chunk-plan layer) and `/brief-review-v2` (brief layer).
user-invocable: true
---

# Engineering Plan Review v2 — Staged Single-Pass

Engineering plans sit between the product brief and the per-chunk implementation plans. A bad engineering plan poisons every chunk plan downstream. This skill prosecutes through a Structural Lint gate plus four named phases, no inner loop. If the verdict is `NEEDS USER INPUT`, the user resolves the labeled blockers and re-invokes — that re-invocation is the equivalent of the next round, with explicit human input between passes (the IEEE 1028 review model).

This is the engineering-plan layer. Sister skill `/plan-review-v2` reviews chunk plans. If the user asks for review of a chunk plan, redirect.

## Shared scaffolding

- `~/.claude/skills/_review-common/principles.md` — stance, banned rationalizations, severity/tier, plan style rules
- `~/.claude/skills/_review-common/round-memory.md` — state file, load, capture priority, persist
- `~/.claude/skills/_review-common/orchestrator.md` — the shared Stage 3 spine
- `~/.claude/skills/_review-common/agent-prompt.md` — persona-agent prompt template
- `~/.claude/skills/_review-common/class-sweep.md` — seeded sibling-enumeration stage (expands a found class)
- `~/.claude/skills/_review-common/structural-sweep.md` — unseeded matrix-completion stage (discovers unfiled classes)
- `~/.claude/skills/_review-common/repo-reality-sweep.md` — codebase-derived stage (checks the plan's premises about code by reading the code)
- `~/.claude/skills/_review-common/critical-pairs.md` — active subset for engineering plan review: `P-CLASS-SCOPE, P-FULL-FILE, P-EP-IMPL-DETAIL, P-EP-BRIEF-GOALS, P-EP-VERIFIED-BY, P-EP-RISK-DEPTH, P-EP-DECISION-LOC, P-EP-SIBLING-CODELIVERY`
- `~/.claude/skills/_review-common/blocker-classes.md` — blocker registry + verdict gate (three-state verdict: CLOSED / APPROVED / NEEDS USER INPUT)
- `~/.claude/skills/_plan-common/layout.md` — flat vs tracked feature layout, plan-root resolution, state-slug derivation. **Read before resolving any argument** — a feature may have more than one engineering plan.

## Tribunal stance (engineering-plan-specific)

**BRIEF IS CANONICAL (when its premises hold), REPO IS LAW.** Two sources of truth bound this review, with one carve-out:

1. **The brief** (`features/<feature>/brief.md`) is the contract for *what* this feature delivers. Every chunk in the engineering plan must trace back to a Goal, User-facing change, or Supporting infrastructure entry in the Brief Mapping. A chunk that doesn't trace is either evidence of a missing Goal (update the brief) or an unjustified chunk (drop it).

   **Carve-out — brief premises are NOT canonical.** The brief's `## Problem` (or equivalent) section makes load-bearing claims about the operating environment (live users, concurrency, monitoring, SLAs, deployment posture). When those environmental claims contradict project memory / `CLAUDE.md` / source-of-truth files, the brief is solving a phantom problem and the plan inherits the phantom. The brief-environment premise check inside Persona Prosecution interrogates these claims and may file a `brief-environment` RESET that short-circuits the review — see Persona Prosecution below.
2. **The repo** is the contract for *how* the plan can be executed. Architecture claims, file paths, existing patterns, CI workflows, and chunk dependencies must match the branch the plan executes on.

**Sibling tracks are one feature.** When this feature has more than one engineering plan, the plan under review is one track of a co-delivered whole (`~/.claude/skills/_plan-common/layout.md`) — nothing goes live on a merge, so the feature ships only through a deliberate whole-feature deploy. Do not review the track as independently shippable. A track delivering no brief Goal on its own, a chunk consumed only by a sibling track, and cross-track wiring left to the sibling's own cycle are the feature's structure, not orphan / integration / go-live / undelivered-Goal defects — file none of them (`~/.claude/skills/_review-common/principles.md` § Sibling-plan co-delivery, `_review-common/critical-pairs.md` § P-EP-SIBLING-CODELIVERY). Coverage still binds: a Goal **no** sibling track delivers is a real gap, and a cross-track shared contract whose export and import have drifted is a real finding.

## Usage

```
/engineering-plan-review-v2 <plan-path> [--personas <p1> <p2> ...]
/engineering-plan-review-v2 <feature-name>           # flat layout; tracked → lists tracks, asks
/engineering-plan-review-v2 <feature-name>/<track>   # one specific plan of a tracked feature
/engineering-plan-review-v2                          # search features/ for active engineering plans, ask which
```

**Examples:**

```
/engineering-plan-review-v2 user-profile-sync
/engineering-plan-review-v2 team-chat/chat-core
/engineering-plan-review-v2 features/team-chat/plans/chat-core/engineering-plan.md
/engineering-plan-review-v2 user-profile-sync --personas architecture ai-development product
/engineering-plan-review-v2
```

## Argument parsing

Split `$ARGUMENTS` on whitespace. Classify each token, in this order:

- `--personas` → all subsequent non-path tokens are persona names.
- `<feature>/<track>` where `features/<feature>/plans/<track>/engineering-plan.md` exists → that plan root. **Test this before the path rule** — a track reference contains a `/` but is not a filesystem path.
- Token ends with `.md`, or starts with `./` / `/` / `features/` → plan path.
- Token matches a directory name under `features/` → resolve its plan roots per `_plan-common/layout.md`. Exactly one → review it. Two or more → list the tracks with each plan's `Status:` field and ask which; do NOT pick one.
- Otherwise → treated as a feature name; if it resolves to no plan root, stop and report.

No arguments → enumerate `features/*/engineering-plan.md` **and** `features/*/plans/*/engineering-plan.md`, list with feature name (plus track, where tracked) and the brief's `Status:` field. Ask which to review.

Throughout the rest of this skill, **`<plan-root>`** means the directory holding the resolved `engineering-plan.md` — `features/<feature>/` under the flat layout, `features/<feature>/plans/<track>/` under the tracked one. `brief.md` and `decisions.md` always live at `features/<feature>/`, never in the plan root.

## Persona resolution

### Explicit personas
Load each from `personas/{name}.md`, resolved relative to the **project root (cwd — the repository being reviewed)**, NOT the skill directory. The persona files are project-specific and live at the repo root (`./personas/*.md`); do not look under `~/.claude/skills/engineering-plan-review-v2/`. Reviewed by every listed persona in parallel. If a listed persona file is genuinely absent from the project root → stop and report; do NOT silently fall back to uncalibrated inline archetype lenses (that produces an under-calibrated verdict indistinguishable from a real one).

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
  ↓ loads ~/.claude/cache/review-state/<feature>[__<track>]__engineering-plan.json; computes
  ↓ plan_growth_flag and section_diff_report for round_number > 1
  ↓ runs the Remediation-completeness pass over the prior round's prior_blockers —
  ↓   closed? swept into every coupled site? arbitration recorded in decisions.md?
  ↓   files REMEDIATION_INCOMPLETE / DECISIONS_PROVENANCE_GAP as pre_resolved_hard_findings.
  ↓   This is the between-round counterpart to post-fix verification, which sees only
  ↓   the orchestrator's own edits and is structurally blind to user remediation.
Ground Truth Pass               (deterministic, no LLM judgment)
  ↓ produces audit_report (incl. decision-closure audit with
  ↓ prior-classification consistency check against decisions.md)
Brief-conformance Audit         (Stage 1.5; parallel subagent batch, HARD findings)
  ↓ spawns 1 Brief-conformance Prosecutor + 1 Scope-fidelity Adversary per at-risk Goal
  ↓   (isolated, one Goal each; see _review-common/brief-conformance-prosecutor.md)
  ↓ files BRIEF_NONGOAL_TRESPASS + BRIEF_GOAL_UNDELIVERED (prosecutor) + SURFACE_PARITY_GAP (adversaries)
  ↓ merges all findings; enters Stage 2 as pre_resolved_hard_findings
  ↓ exempt from decisions-log-first carry-forward retraction (Class A per principles.md)
Persona Prosecution             (LLM judgment, M parallel agents)
  ↓ produces fix_lists; each persona runs premise interrogation
  ↓ (repo-state + brief-environment sub-passes) + standard prosecution.
  ↓ Round > 1: section_diff + plan_growth gates injected into prompts.
Imagined-Implementer Dry Run    (LLM judgment, 1 agent)
  ↓ produces undecided_decisions (with severity_test) +
  ↓ needed_identifiers + scope_reduction_candidates
  ↓ (chunk selected by cross-chunk-contract density, NOT dep-order)
Structural Sweep                (UNSEEDED matrix completion, 1 agent per universe)
  ↓ Universe L — every gate × every condition: is every failing state exitable?
  ↓ Universe P — every destructive path × every protection the plan itself requires
  ↓ runs even when the round produced ZERO findings: it discovers classes nobody
  ↓   filed, which the seed-driven Class Sweep structurally cannot reach
  ↓   (_review-common/structural-sweep.md); GAPs become same-round findings
Repo Reality Sweep              (CODEBASE-derived, 1 agent per chunk, all 3 questions)
  ↓ Universe R — what each chunk REPLACES: is the divergence from the incumbent stated?
  ↓ Universe C — what CALLS what the chunk touches: is every caller accounted for?
  ↓ Universe D — what the chunk newly IMPORTS: does the plan's use survive the
  ↓   dependency's real guarantee, at the plan's scale?
  ↓ every other stage enumerates from the ARTIFACT; this one enumerates from the REPO,
  ↓   so it reaches claims the plan omits rather than claims it makes
  ↓   (_review-common/repo-reality-sweep.md); GAPs file REPO_PREMISE_GAP
Orchestrator Decision           (deterministic + judgment)
  ↓ evaluates RESET corroboration (subclass-aware),
  ↓ runs Class Sweep — one agent per distinct recurring category walks the
  ↓   peer-set (every chunk row / Goal / Non-goal / closure row) for siblings,
  ↓   promoting them to same-round findings (_review-common/class-sweep.md);
  ↓   each agent first WIDENS the handed peer-set to the bare invariant's
  ↓   supertype, so a narrowly-declared class does not narrow the sweep,
  ↓ applies fixes,
  ↓ auto-retracts unchanged-section findings without (a)+(b) justification,
  ↓ downgrades regression_risk: yes findings, applies cross-file edits to
  ↓ decisions.md / brief.md / engineering plan in class-aware authority order
  ↓ (Class A: brief.md > decisions.md > plan; Class B: decisions.md > plan;
  ↓  see _review-common/principles.md § Cross-artifact authority order),
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
  `/engineering-plan-author <feature>`. The author skill removes the `Status:`
  frontmatter on a successful CLOSED or APPROVED emission; re-invoke
  `/engineering-plan-review-v2` once the plan is back to no-Status-field state.
  ```

- **No `Status:` field, OR any other value** → proceed normally. The Round Memory Pass consults the engineering-plan-author sidecar at `~/.claude/cache/author-state/<feature>__engineering-plan.json`; if `authoring_mode: "draft"` is set there (the plan was written via `/engineering-plan-author --draft`, skipping Plan-lint, Concern-lint, Ground-truth, Self-prosecution, and Imagined-Implementer), the verdict surfaces a draft warning. Persona prosecution still runs.

The check is deterministic and runs before any LLM judgment or shell invocation. A `Status: needs-user-input` artifact never reaches the Structural Lint Gate.

Also `Read` the upstream brief (`features/<feature>/brief.md`) and apply the same check: a `Status: needs-user-input` brief means the upstream is mid-cycle, and the engineering plan derived from it cannot be reviewed cleanly until the brief is hardened. Refuse with the same template, redirected at `/brief-author <feature>`.

## Structural Lint Gate (MANDATORY, HARD SHORT-CIRCUIT)

```bash
python3 ~/.claude/skills/plan-lint/lint.py <plan-root>
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

## Round Memory Pass (no LLM judgment)

Mechanism, schema, load, capture priority, and persist rules: `~/.claude/skills/_review-common/round-memory.md`. Read it. This section names what the engineering-plan layer adds — the plan-growth and section-diff gates, which exist because this layer's artifact *grows* each round as the user binds flagged decisions, and the next round would otherwise prosecute the remediation itself.

### State file

**Slug** — `<feature>__engineering-plan` under the flat layout, `<feature>__<track>__engineering-plan` under the tracked one.

**Legacy-slug migration.** This skill historically wrote a bare `<feature>.json` with no layer suffix, which no author skill ever read — `/brief-author`, `/engineering-plan-author`, and `/plan-author` all consult `<feature>__engineering-plan.json` for warm carry-forward, so that channel was silently dead. On load: read the canonical slug first; if absent, fall back to `<feature>.json` and treat it as this plan's prior state. On persist: always write the canonical slug, and delete the legacy file once the canonical one is written. Report the migration on the verdict's `State source` line.

### Non-convergence tripwire (Feature-surface gate)

After loading state, evaluate the tripwire from `~/.claude/skills/_review-common/feature-surface-gate.md` § Non-convergence tripwire: `round_number >= 5` AND (open-blocker count not strictly decreasing over the last 3 entries of `open_blocker_history`, OR current `open_question_count >= 8`; cold-history fallback when the array is absent: `prior_blockers` length ≥ 8). Fired → file `FEATURE_NONCONVERGENCE` (HIGH), spawn the split-proposal agent (`model: "sonnet"`) per the gate file, and render the proposal as a director decision in the verdict — never auto-apply a split. On EVERY verdict, append `{round, open_blocker_count, open_question_count}` to `open_blocker_history` in the state file. A bound size-acceptance row re-arms the trigger at acceptance-round + 5; it never silences it. Additionally, Structural Lint recomputes the Feature-surface estimator (`chunk_count` / `dag_depth` / `cross_chunk_contract_total` / `open_decision_count` per the gate file) — breach files `FEATURE_SURFACE_EXCESS`; disagreement with the author sidecar's `feature_surface` field files `AUTHOR_GATE_DRIFT`, same convention as the chunk-surface cross-check.

**Extra fields** on top of the shared schema:

- `last_plan_word_count` — feeds the plan-growth check below.
- `section_hashes` — `{ "<section heading>": "<sha256 of the section body, excluding the heading line>" }`, feeds the section-diff.
- `track` — the track name, or `null` under the flat layout.
- `remediation_completeness` — the per-blocker result of the Remediation-completeness pass (schema in that sub-pass). One entry per prior-round blocker, never sampled. Carried forward only as evidence for the next round's pass; never used to retract a finding.
- `chunks_simulated` — `[{chunk_slug, round, verdict, row_hash}]`. Feeds the Imagined-Implementer's cross-round rotation: a chunk that returned `implementable` and whose chunk-index row hash is unchanged is excluded from selection, so successive rounds probe successively less-dense chunks instead of re-probing one forever. A changed row re-admits the chunk.
- `repo_reality_sweep` — the per-chunk matrix summary (schema in `_review-common/repo-reality-sweep.md` § State recording). Carried forward on the **repo**, not the artifact: a clean chunk may be `inherited_clean` only when its chunk-index row hash is unchanged AND every path in its recorded `incumbent_files_blob_shas` still resolves to the same blob at HEAD. Copying the Structural Sweep's `section_hashes` key here would be a bug — it cannot see the code moving under the plan.
- `structural_sweep` — the per-universe matrix summary (schema in `_review-common/structural-sweep.md` § State recording). Carried forward across rounds: a universe that returned all-clean may be recorded `inherited_clean` next round **only** when `section_hashes` is unchanged for every section that universe reads. A universe whose inputs moved is always re-run — that carry-forward is what keeps the stage's steady-state cost near zero on a stable plan.

**Blocker classes seen here** — `BRIEF_AMENDMENT_NEEDED`, `IMPLEMENTABILITY_GAP`, `UNCORROBORATED_RESET`, `CHUNK_SURFACE_EXCESS`, `FEATURE_SURFACE_EXCESS`, `FEATURE_NONCONVERGENCE`, `AUTHOR_GATE_DRIFT`, plus the universal three.

**Legacy field.** `prior_blockers_resolved_by_user`, if present, migrates on first read into `recently_resolved_blockers`: preserve `summary` and `resolved_in_round`; default `blocker_class_when_resolved` to the migrated `blocker_class`, `path_or_section` to `"(legacy entry — no path recorded)"`, `user_decision` to `"No rationale recorded (legacy entry)"`, and `carry_forward_until_round` to `resolved_in_round + 2`. Drop the legacy field after migrating.

On a cold start, skip the plan-growth and section-diff sub-passes and proceed to Ground Truth.

### Plan-growth check (gate for Persona Prosecution)

Compute current plan word count (`wc -w <plan-root>/engineering-plan.md`). Compare to `last_plan_word_count`.

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

### Remediation-completeness pass (round_number > 1, MANDATORY)

Post-fix premise verification and the same-round focused re-prosecution both cover **orchestrator-applied** fixes, inside the round that applied them. Neither can see the remediation the *user* writes **between** rounds, which is the larger surface: a `NEEDS USER INPUT` verdict hands back N blockers, the user edits the plan, and the next round meets that new text with nothing but ordinary prosecution latitude. The recurring failure is not a bad fix — it is a fix that lands in the one or two sections that motivated the blocker and never reaches the sites coupled to them, so the blocker reads as closed while its consequences are unbuilt. `prior_blockers` and `recently_resolved_blockers` are consulted only to *retract* re-prosecution; nothing verifies *completion*. This pass is that check, and it runs before Persona Prosecution so its findings enter Stage 2 as `pre_resolved_hard_findings`.

For **every** entry in the prior round's `prior_blockers`, answer three questions and record the answer. Do not sample.

1. **Closed?** Locate the text that closes it. Quote it. If nothing in the plan addresses the blocker, it is still open — carry it forward at its original class and severity rather than letting the round-counter launder it into a fresh finding.

2. **Swept?** A remediation names a mechanism, a marker, an actor, a terminal action, or a contract. Enumerate the sites that mechanism *must* reach — every gate table that governs an operator flag, every protection enumeration, every rule that quantifies over the set it joined, every count or ordinal claim over a set it changed the size of, every Owns/Reads declaration for a file it touches, every sibling-plan span the Supersession sweep rule covers. Check each. A remediation present in its motivating section and absent from its coupled sites files `REMEDIATION_INCOMPLETE` (HARD, severity inherited from the original blocker). This is the pass's highest-yield question — a newly-added terminal action, chunk, or marker is the archetype, because it changes the size of sets that other sections state as fixed numbers.

3. **Recorded?** An arbitration the user made to close a blocker belongs in `decisions.md`. Search for a bound Active-section entry covering it. A plan span that *cites* a `decisions.md` entry which does not exist is a `DECISIONS_PROVENANCE_GAP` (HARD, HIGH) — resolve every citation the round's modified sections introduced, by heading, not by date alone. An unrecorded arbitration cannot be retracted by Priority-1 carry-forward next round, so the same ground is re-prosecuted indefinitely; this question is what keeps the durable layer durable.

Record the result as `remediation_completeness` in the state file: `{blocker, closed: yes|no, closing_quote, coupled_sites_checked: [...], sites_missed: [...], decisions_entry: "<heading>" | "none — <class>"}`. A blocker whose `coupled_sites_checked` is empty was not checked; re-run it.

### Persist on exit

Per the shared file, plus `last_plan_word_count` ← current word count and `section_hashes` ← rebuilt from the current plan. On `CLOSED`, leave the file in place: a later invocation after a brief amendment needs the round count to apply these gates correctly.

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
- "<verbatim Goal>" → chunks {`slug-a`, `slug-b`, ...}, verified by {`acceptance-slug` / "Manual review — <reason>"}
- "<...>" → ❌ NO CHUNKS LISTED  [HARD: undelivered Goal]
- "<...>" → ❌ NO `Verified by` PROOF  [HARD: GOAL_VERIFICATION_GAP]

User-facing change → chunks + verifier:
- "<verbatim change>" → delivered by {`slug-a`}, verified by {`slug-x` / "Manual review"}
- "<...>" → ❌ MISSING `Verified by` ENTRY  [HARD: untraced user-facing change]

Chunks in chunk index: <count> [verbatim list]
Chunks appearing in Brief Mapping (Goals, User-facing, or Supporting infrastructure):
- `schema-migration`, `cascade-rewrite`, ... ✓
- `legacy-shim-cleanup` ❌ NO MAPPING  [HARD: unjustified chunk]

Brief Non-goals → enforcement + classification check:
- "<verbatim non-goal>" → kind: testable-absence, test owned by {`acceptance-slug`} ✓
- "<verbatim non-goal>" → kind: scope-boundary, reason: "<...>" ✓
- "<...>" → ❌ testable-absence but NO owning test  [HARD: GOAL_VERIFICATION_GAP]
- "<...>" → ❌ marked scope-boundary but the exclusion is observably assertable  [HARD: GOAL_VERIFICATION_GAP]

Acceptance chunk check:
- Dedicated acceptance chunk `<slug>`: present ✓ / ❌ ABSENT  [HARD: GOAL_VERIFICATION_GAP]
- Is DAG sink (no chunk depends on it) AND Code-deps cover every delivering chunk: ✓ / ❌ [HARD: GOAL_VERIFICATION_GAP]

Drift detected:
- Plan claims user-facing behavior X. Brief does not list X.  [SOFT: HIGH — scope creep or missing brief Goal]
- Brief lists Goal Y. Plan does not deliver Y.                [HARD: undelivered Goal]
```

**Tracked layout — trace against the union.** When the feature has sibling engineering plans, a brief Goal, user-facing change, or Non-goal this plan does not deliver may be delivered by a **sibling track**. Before filing any `undelivered Goal` / untraced-change finding, read the sibling plans' Brief Mapping and mark the Goal *covered* if a sibling delivers it — its acceptance-chunk and `Verified by` proofs are then satisfied by the delivering track's chunk. Only a Goal **no** sibling track delivers is `[HARD: undelivered Goal]`. This is the coverage-union rule of `~/.claude/skills/_review-common/principles.md` § Sibling-plan co-delivery; the orphan/integration half of that principle retires cross-track shipping findings entirely.

**Goal-verification audit (mechanical + light judgment).** The blocks above ground three facts: (1) a dedicated **acceptance chunk** exists as a DAG sink whose Code-deps cover every delivering chunk; (2) every brief Goal carries a `Verified by` proof naming that chunk (or `Manual review — <reason>` — and a Goal whose outcome is observably automatable but left to manual check is a gap, not an exemption; the mechanical trace flags the blank/`Manual review` cells and the `product`/`testing` personas judge automatability); (3) every Non-goal is classified `testable-absence` (→ an assert-absence test owned by the acceptance chunk) or `scope-boundary` (→ `not test-assertable — <reason>`), and a `scope-boundary` mark on an observably-assertable exclusion is a gap. Each failure files `GOAL_VERIFICATION_GAP` — **Class A** (brief Goal/Non-goal honoring; exempt from decisions-log-first carry-forward per `_review-common/principles.md` § Cross-artifact authority order). This is distinct from `BRIEF_GOAL_UNDELIVERED` (no chunk delivers the Goal) and `SURFACE_PARITY_GAP` (delivered short of its domain): `GOAL_VERIFICATION_GAP` fires when the Goal may be delivered fine but nothing *proves* it, so a later refactor can break the contract with no failing test.

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
3. Invariants *(required; may carry the no-invariants disclaimer)*
4. Threat model *(required; may carry the no-surface disclaimer)*
5. Other domain contracts *(optional)*
6. Chunk index
7. Manual gates *(optional)*
8. Dependency graph
9. Risks / unknowns
10. Rollout plan *(conditionally required: prod state changes / migrations / flags)*
11. Out of scope

**Required headers:**
- Header with `**Brief:**` link (and `**Decisions:**` link when `decisions.md` exists)
- Brief Mapping has `### Goals`, `### User-facing changes`, `### Scope enforcement` subsections
- User-facing changes table has a `Verified by` column
- Goals table has a `Verified by` column; Scope enforcement table has a `Kind` column (`testable-absence` | `scope-boundary` | `deferred-tracked`). A missing column → `[HARD: GOAL_VERIFICATION_GAP]` (the acceptance-proof mapping cannot be graded without it).

**Invariants and Threat model (both required sections):**
- Each carries content OR its explicit disclaimer (`No cross-chunk invariants — <reason>.` / `No threat-model surface — <reason>.`). Present-but-empty is `[HARD]` — an empty section and a missing one read identically, and neither is a decision.
- Every invariant carries `**Form:**` (`test` | `assert` | `gate` | `doc`) and `**Falsifier:**`. Missing either is `[HARD]`. `Form: doc` on an invariant in a high-risk class (auth, score math, data integrity) is `[SOFT MEDIUM]` — it is unenforced by construction.
- **The threat-model trigger is yours to judge, and `/plan-lint` cannot do it.** The disclaimer is `[HARD]` when the feature touches authentication, session or token lifetime, follow/block/mutual-unfollow, writes to user-owned data, a public-vs-locked exposure boundary, external-data ingestion, or an LLM-mediated path. Read the Architecture summary and the chunk index for those surfaces rather than trusting the disclaimer's reasoning — an unjustified disclaimer is the failure mode the required section exists to catch, and it is the one check no regex reaches.
- A populated Threat model whose detections cite invariants, alongside a `No cross-chunk invariants` disclaimer, is `[HARD]` — the two contradict.
- **Legacy tolerance.** A plan with no Invariants section, no Threat model section, or invariants carrying neither field predates the convention. File ONE `[SOFT LOW]` per missing convention recommending migration on the next substantive edit; do not file per-entry findings and do not treat it as a structural defect.

**Chunk index column rules:**
- Columns are EXACTLY `Slug | Chunk | Intent | Code deps`. Any of `#`, `Status`, `PR`, `Mode`, `Owner`, `Last-updated` is `[HARD]`. A missing `Intent` column on a plan that predates the convention is `[SOFT LOW]` (migrate on next touch), not `[HARD]`.
- `Intent` is one of `Foundation`, `Behavior`, `Hardening`, `Migration`. Any other value is `[HARD]`.
- A `Foundation` chunk that no other chunk depends on is `[HARD]` — it changes no behavior and has no consumer, so it ships dead scaffolding. **Tracked layout:** "no consumer" means no consumer **in this plan** — a Foundation chunk consumed only by a sibling track is not orphaned (`~/.claude/skills/_review-common/principles.md` § Sibling-plan co-delivery).
- A `Migration` chunk that does not depend on the chunk making the runtime forward-compatible is `[SOFT MEDIUM: expand-then-contract inverted]`.
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

### Chunk-surface estimator (mechanical, mirrors `/engineering-plan-author`'s gate)

The author skill runs a Chunk-surface estimator gate that catches chunks whose aggregate surface is feature-sized rather than chunk-sized — independently of self-disclosure patterns and not subject to Concern-lint carry-forward. The reviewer mirrors the gate to catch hand-edited plans that bypassed the author skill and to verify the author's gate fired correctly on the current shape.

For each chunk-index row, compute (same algorithm as the author skill — see `engineering-plan-author/SKILL.md` § Chunk-surface estimator gate for definitions):

- `concern_count` — top-level "+"-separated noun phrases in the row description (split on `+`, `;`, ` AND `, ` plus ` at the outermost paren level; nested parentheticals count as one outer concern).
- `introduced_identifier_count` — distinct identifiers the row's prose names that the chunk *creates* (functions, types, constants, CLI subcommands, schema columns, file paths created).
- `cross_chunk_contract_count` — distinct cross-chunk forward-binding contracts the row binds (heuristic: "every chunk that…", "downstream chunks…", "forward-binding", "cross-chunk", "future-chunk", explicit cross-chunk-contracts sub-sections).

File `CHUNK_SURFACE_EXCESS` as a HARD blocker when ANY of: `concern_count >= 5`, `introduced_identifier_count >= 8`, `cross_chunk_contract_count >= 2`.

**Author state cross-check.** Read `~/.claude/cache/author-state/<feature>__engineering-plan.json`. If `chunk_surface_estimator` is absent, OR if any row's `verdict` recorded there is `passed` but the reviewer's recomputation says `excess`, OR if the author state's recorded counts disagree with the reviewer's recomputation, file the resulting `CHUNK_SURFACE_EXCESS` blocker AND a separate `AUTHOR_GATE_DRIFT` finding noting the author state did not run or recorded different counts (helps the user notice when a hand-edit bypassed `/engineering-plan-author`).

**Carry-forward exemption.** `CHUNK_SURFACE_EXCESS` is NOT subject to decisions-log-first carry-forward consultation. Surface excess is a structural property of the row, not an arbitration question; a `decisions.md` row binding *what* the chunk does cannot bind *how much*. Only a `decisions.md` row whose Resolution column explicitly acknowledges the aggregate surface as intentional (containing language like "surface acknowledged", "feature-sized chunk accepted", "atomic landing surface arbitrated") retracts the blocker. Bare keyword matches against component concerns of the row do NOT retract.

The blocker's actionable resolutions match the author skill's: split the row into N sibling chunks with explicit dependency edges; extract a foundational sub-chunk that other siblings depend on; or cite a `decisions.md` row that arbitrates aggregate surface (per the language above).

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
- **`cross-track-codelivery`** — names a **sibling track's** consumption of an **already-defined** export of this track, or wiring the sibling performs as part of its own implementation (repointing a seam onto this core, importing a shared contract whose shape is defined here). This is not a deferred decision; it is the feature's structure, done and verified in the sibling's own cycle (`~/.claude/skills/_review-common/principles.md` § Sibling-plan co-delivery). No finding. **But** a deferral that leaves the **shape** of a shared cross-track contract undecided (its type, column, event payload, or predicate defined in neither this plan nor the owning track) is `cross-chunk-wiring`, not co-delivery — co-delivery covers *who consumes* and *when*, never *what the shared shape is*.
- **`brief-layer`** — names a residual gap, accepted user-facing tradeoff, scoped non-goal, scope expansion, or product-shape decision. Belongs in `brief.md`.
- **`unclear`** — topic cannot be classified mechanically with confidence.

**Prior-classification consistency check (MANDATORY).**

Before emitting findings, `Read` `features/<feature>/decisions.md` if it exists. For every deferral classified `cross-chunk-wiring` or `brief-layer` in the previous step, search `decisions.md` for prior entries naming the same surface (heuristics: matching identifier name, matching section heading, matching verbatim phrase fragment ≥4 words).

If a prior `decisions.md` entry is found AND it bound the surface to a different classification (e.g., previously declared `chunk-internal` and now being flagged `cross-chunk-wiring`, or vice-versa), the current classification is a **reclassification** — only an Active bound entry (one in the `## Active (bound)` section with `Status: bound`) counts as the binding prior classification; a `superseded`/`obsolete` entry in the `## Archived (superseded / obsolete)` tail is not a live binding (per `~/.claude/skills/_review-common/principles.md` § What counts as a bound entry).

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
- `cross-track-codelivery` → no finding (the feature's structure, not a deferred decision — `principles.md` § Sibling-plan co-delivery).
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
- goal_verification: acceptance_chunk_present, acceptance_chunk_is_sink, goals_with_proof / goals_total, non_goals_classified / non_goals_total, hard_findings (GOAL_VERIFICATION_GAP: missing acceptance chunk / unproven Goal / unproven-or-misclassified Non-goal)
- repo_reality: architecture_claims (claim + status + evidence), ci_claims, code_deps, false_parallelism, hard_findings
- structural_lint: sections_present, column_check, forbidden_pattern_hits, hard_findings, soft_findings
- decision_closure: deferrals_total, cross_chunk_wiring, brief_layer, chunk_internal, unclear, hard_findings
- mechanical_fixes_applied
- pre_resolved_hard_findings

---

## Brief-conformance Audit (Stage 1.5 — MANDATORY, HARD findings exempt from carry-forward)

Per `_review-common/principles.md` § Cross-artifact authority order, brief Goals and Non-goals are Class A — `brief.md > decisions.md > engineering plan`. This stage prosecutes Class A contradictions BEFORE persona prosecution, so its findings enter Stage 2 as `pre_resolved_hard_findings` exempt from decisions-log-first retraction.

The audit is a parallel batch of subagents: one Brief-conformance Prosecutor (trespass + delivery + verifiability, over the whole brief) plus one Scope-fidelity Adversary per at-risk Goal (scope/authority/timing parity, one Goal each, in isolation). Pattern matching and keyword extraction were tried in an earlier draft and rejected: trespasses surface under arbitrary vocabulary (a Non-goal forbidding "resumability infrastructure" trespassed by a chunk called `checkpointConvention` shares zero keywords), and keyword scans produce false positives on plan sections that mention a Non-goal noun in order to *honor* the Non-goal. Behavioral reasoning is the only honest gate — and for parity specifically, reasoning done in ISOLATION per Goal, because the same reasoning batched across many items goes charitable and misses narrowings (validated this way).

### Procedure

1. **Spawn both roles in one parallel batch** (Agent tool, `general-purpose`, default subagent type), using the two prompts in `~/.claude/skills/_review-common/brief-conformance-prosecutor.md`. **Every agent in this batch takes an explicit off-model `model` override** per that file's § Model pin (default `sonnet`; `opus` if the session is already Sonnet) — never inherit the session model, since a judge sharing the authoring model's priors is the bias this gate exists to remove. Record the pinned model as `brief_conformance_report.conformance_gate_model`.

   **(a) One Brief-conformance Prosecutor** (trespass + delivery + verifiability), substituting:
   - `{brief_path}` = `features/<feature>/brief.md`
   - `{plan_path}` = `<plan-root>/engineering-plan.md`
   - `{sibling_plan_paths}` = every OTHER track's `engineering-plan.md` when the feature is tracked, else "none". Required — see `_review-common/brief-conformance-prosecutor.md` § Substitutions common to all layers. Omitting it on a tracked feature makes each declared hand-off read as a narrowing and floods the round with false `SURFACE_PARITY_GAP`s.
   - `{decisions_path}` = `features/<feature>/decisions.md` (or "none" if absent)
   - `{plan_layer}` = `engineering-plan`
   - `{additional_examples}` = the calibration examples accumulated in the state file's `brief_conformance_calibration_examples` (empty on first invocation; grows as the user resolves false positives by binding explicit `## Decisions closure` arbitration entries)

   **(b) One Scope-fidelity Adversary per at-risk Goal**, each with the second prompt and exactly ONE Goal. First enumerate the brief's Goals and select the **at-risk subset** — a Goal that carries a domain quantifier ("every", "across", "all", "any", "going forward", "at every surface") OR names an authoritative signal/basis the outcome must be judged on. Single-surface concrete Goals are not at-risk and get no adversary. For each selected Goal, substitute `{goal_under_review}` = that Goal verbatim; the other four substitutions are identical to (a). **NEVER batch multiple Goals into one adversary** — isolation is the load-bearing, validated separation (a shortfall an isolated judgment catches is missed when many items share one attention window). Record which Goals were selected and which were skipped-as-not-at-risk in the `brief_conformance_report` (below) so coverage is auditable and not silently truncated. When unsure whether a Goal is at-risk, spawn the adversary.

2. **Receive every role's JSON output and merge the `findings` arrays into one list** (schemas are identical). Parse `brief_conformance_check`, `rationale`, and `findings` from each. If any single role's output is malformed (missing required fields, severity outside the allowed set, finding without both verbatim quotes), surface as an internal error and re-spawn ONLY that role once — do NOT silently file malformed findings and do NOT re-spawn the whole batch.

3. **Pass merged findings into Stage 2.** Each finding becomes a `pre_resolved_hard_findings` entry visible to every persona's prompt. Personas may file ADDITIONAL findings but cannot retract Stage 1.5 ones — the orchestrator drops persona findings whose substance contradicts a Stage 1.5 finding's evidence (with note `retracted: contradicts pre-resolved Stage 1.5 finding {id}`).

4. **Build the `brief_conformance_report` for verdict rendering:**
   ```
   brief_conformance_report:
     prosecutor_verdict: "passed" | "findings_filed"      # aggregated across all roles
     findings_total: <int>
     findings_high_hard: <int>
     findings_medium_hard: <int>
     bound_decisions_trespassing: <int>     # findings whose evidence_source cites decisions.md
     plan_sections_trespassing: <int>       # findings whose evidence_source cites the plan body
     goals_undelivered: <int>
     surface_parity_gaps: <int>             # SURFACE_PARITY_GAP findings — Goal delivered over a subset of its domain, on a proxy basis, or via a premature/irreversible action
     scope_adversaries_spawned: <int>       # one per at-risk Goal
     goals_at_risk: [<Goal verbatim>, ...]  # Goals that got an adversary
     goals_skipped_not_at_risk: [<Goal verbatim>, ...]   # concrete single-surface Goals; no adversary
     rationale: "<prosecutor's rationale paragraph + one line per adversary that flagged>"
   ```

   Pass into Stage 3 for verdict rendering; the verdict's Blockers section lists each finding with the role's reasoning, evidence, and resolution_paths verbatim so the user can act without re-reading the subagent output.

### Calibration loop

The prosecutor is judgment-class; calibration will drift. Two guard mechanisms:

- **False-positive escape.** When the user resolves a `BRIEF_NONGOAL_TRESPASS` blocker by adding an explicit `## Decisions closure` entry that arbitrates the contradiction (with `bound` status, citing why the prosecutor's reading was wrong), record the resolution in the state file's `recently_resolved_blockers` AND append the (brief_quote, contradicting_evidence, user's arbitration sentence) triple to `brief_conformance_calibration_examples`. Subsequent invocations pass these resolutions as `{additional_examples}` negative cases so the prosecutor learns the user's calibration over time.

- **False-negative escape.** If a reviewer-stage persona files a Class A trespass that Stage 1.5 missed, the orchestrator promotes it to a pre-resolved Stage 1.5 equivalent (severity HIGH HARD, class `BRIEF_NONGOAL_TRESPASS`) rather than treating it as a normal persona finding subject to carry-forward. The verdict notes `stage_1_5_miss_recovered_by_persona: <persona_name>` so calibration drift is visible.

---

## Persona Prosecution (parallel agents, fix-list output)

Resolve personas (auto or explicit). Launch one Agent per persona **in parallel in a single message**, each with `model: "sonnet"` per `_review-common/agent-prompt.md` § Model pin — never inherit the session model; record `persona_model` in the review state.

### Spawn agents

Use the template in `~/.claude/skills/_review-common/agent-prompt.md`. Substitute:

- `{persona_name}` — the persona being prosecuted as
- `{audit_report_bullets}` — Ground Truth audit (compact bullets)
- `{pre_resolved_hard_findings}` — anything Ground Truth already raised
- `{active_critical_pair_subset}` — `P-CLASS-SCOPE, P-FULL-FILE, P-EP-IMPL-DETAIL, P-EP-BRIEF-GOALS, P-EP-VERIFIED-BY, P-EP-RISK-DEPTH, P-EP-DECISION-LOC`
- `{target_locator}` — engineering plan path
- `{how_to_get_it}` — `Read <plan-root>/engineering-plan.md`, `Read features/<feature>/brief.md`, `Read features/<feature>/decisions.md` (if exists). Under the tracked layout, also name the sibling tracks' plans as context-only reads: a chunk this plan does not own may still be the counterpart of a seam it registers.
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
> - CRITICAL: plan will fail mid-execution, leave a half-shipped feature (of **this plan's own** chunks — the window between sibling tracks landing is not half-shipped; nothing deploys on a merge, per `principles.md` § Sibling-plan co-delivery), or corrupt prod state.
> - HIGH: significant correctness or rollout-safety risk.

---

## Imagined-Implementer Dry Run

Convergence-forces the plan into a state where it is *implementable as written*. Runs after Persona Prosecution by spawning one foreground Agent with `model: "sonnet"` (per `_review-common/principles.md` § Station model policy — it simulates the *execution-tier* implementer, so running it on the execution-tier model makes the simulation more faithful, not less). Output gates the `CLOSED` verdict.

The premise: the engineering plan is a contract for an implementer who will read only this plan plus the brief and start writing a chunk plan from a cold start. If after reading those two documents the implementer has to make cross-chunk-wiring decisions herself, the engineering plan is incomplete. The chunk simulated is the **most contract-dense** unshipped one, not the next dep-free one — see the selection rule in the agent prompt for why.

### Agent prompt

> You are simulating an implementer about to write the per-chunk plan for the chunk named by the selection rule below (the unshipped chunk binding the most cross-chunk contracts — **not** the next dep-free one). You have read **only** this engineering plan and its brief. You have NOT read prior reviews, decisions logs, or this conversation's history. You will not write the per-chunk plan now — only enumerate what the engineering plan provides and what it leaves you to decide yourself.
>
> Read `features/<feature>/brief.md` and `<plan-root>/engineering-plan.md`.
>
> **Pick the unshipped chunk that binds the MOST cross-chunk contracts** — not the first dep-free one. Count, per unshipped chunk-index row: shared identifiers it reads or writes, gate conditions it must satisfy or produce, markers / columns / events another chunk depends on, and forward-binding obligations it carries. Take the maximum; break ties toward the chunk that becomes dep-ready soonest. State the count in your rationale.
>
> **Rotation across rounds — do not re-simulate a chunk that already cleared.** You are handed `{chunks_already_simulated}`: chunks simulated in earlier rounds that returned `implementable` and whose chunk-index row has not changed since. Exclude those and take the densest of what remains. Only when every chunk above the median contract count has been simulated-and-cleared do you fall back to re-simulating the densest. A single fixed selection rule would otherwise probe one chunk forever and leave every other chunk permanently unexamined — which is the old rule's failure mode with a different chunk on the pedestal, and it bites hardest on exactly the large plans where more than one chunk is independently risky.
>
> This rule is deliberate and **replaces an earlier "next dep-free chunk" rule that systematically selected the safest chunk in the plan.** Dep-free chunks are foundations — small, isolated, carrying few cross-chunk contracts — so simulating one reliably returns `implementable` while the cross-chunk decisions that actually break parallel implementation sit in later, contract-dense chunks the simulation never opened. In a real round this rule picked a single-value enum migration and cleared the plan while two CRITICAL defects sat in gate machinery it never read. Your purpose is gap detection, not chronological realism: a cold-read implementer can simulate any chunk, so simulate the one where an unbound contract would do the most damage.
>
> Imagine starting that chunk's per-chunk plan now, from a cold read.
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
> cross_chunk_contract_count: {integer — the count that selected it}
> contract_counts_considered: {slug: count, ...}   # every unshipped chunk, so the selection is auditable
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

## Structural Sweep (MANDATORY, UNSEEDED — runs even on a zero-finding round)

Per `~/.claude/skills/_review-common/structural-sweep.md` — read it for the mechanism, agent template, merge, and state/verdict schema. This section fills the per-layer slots.

**Why this stage exists at this layer.** Every other discovery path here is either mechanical claim-verification (Ground Truth) or judgment recall (personas). The Class Sweep multiplies the second — it is a finding-*expansion* pass, seeded from surviving findings, and explicitly barred from discovering a new class. So a defect class **no persona filed** is invisible to the whole pipeline, and no compliance check fires, because there was no seed to be incomplete about. This stage is the unseeded counterpart. It runs regardless of the round's finding count; a clean round is exactly when it earns its cost.

**Universes to run at this layer:**

- **Universe L — gate liveness.** Members: every `## Manual gates` row × every condition it asserts, plus every scripted gate (post-`--apply` hard gates, post-run audit checks, coverage gates), every CI gate the plan names, and every condition in a capture-time re-verification set. Under the tracked layout, run it over **both** plans' gates in one pass — a cross-plan gate chain is where an absorbing state hides best. The fixed question: *is there a reachable state in which this condition can never be satisfied, no matter how many re-runs, with no specified remedy?* Closure requires a named terminating path — a re-run that genuinely differs because the cause was transient, an operator action, an exempting marker, or a **disclosed** accepted residual. "The operator would work something out" is a GAP. Weight CRITICAL when the gate blocks an irreversible or one-shot step.
- **Universe P — protection parity.** Members: every protection the plan *itself* treats as required for a dangerous action × every path reaching that effect (destructive row writes, column nulls, cascade-child deletes, irreversible operator flags). Derive the protection list **inductively from the plan**, never from a generic checklist — the plan's own invariants are the obligation. Mark HAS (quote it) / N/A (structurally inapplicable, say why) / GAP. "The operator would not do that" is a GAP, not N/A. Protection parity is judged **within a plan's own execution** — the gap between sibling tracks landing is not an unprotected state, since nothing deploys on a merge (`~/.claude/skills/_review-common/principles.md` § Sibling-plan co-delivery).

**`{known_good_reference}`** — when one path or gate already solves the question correctly, name it in the prompt. A sweep with a reference produces fixes that mirror an in-plan precedent instead of inventing a mechanism, which is what keeps a GAP's remedy cheap to bind.

**Skip rule.** Universe L is skipped only when the plan gates nothing irreversible; Universe P only when the plan defines a single path to each dangerous effect. Record every skip with its reason in `structural_sweep.universes_skipped` — never skip silently.

**Concurrency.** Both universes are unseeded, so they may be spawned in the same message as Persona Prosecution rather than after it; they need only Ground Truth's verified facts, not findings. The pipeline shows them sequentially for clarity.

**Merge.** Every GAP becomes a same-round finding at the sweep-judged severity, routed through the same critical-pair retraction and the same class-aware authority order as a persona finding. A GAP requiring an upper-authority amendment is a director blocker, not an auto-fix — a structural gap is frequently a contract or scope decision. `UNDETERMINED` cells never vanish: each is either resolved by a cheap orchestrator check or recorded as a `POLISH_PLATEAU` note naming what would settle it.

---

## Repo Reality Sweep (MANDATORY — runs even on a zero-finding round)

Per `~/.claude/skills/_review-common/repo-reality-sweep.md` — read it for the mechanism, agent template, merge, and state/verdict schema. This section fills the per-layer slots.

**Why this stage exists, and why it is not a Structural Sweep universe.** Every stage above enumerates its universe from **the artifact** — gate rows, chunk rows, Goals, declared contracts, section headings. Ground Truth reads code, but only to verify claims the plan already made. The defects that survive to implementation are the claims the plan **omits**, and silence is not falsifiable, so nothing fires. This stage enumerates from the **repository** instead. It is a sibling rather than a fourth universe because the Structural Sweep's carry-forward hashes artifact sections, which is the wrong key entirely for a universe whose inputs are source files — a plan verified against a since-changed incumbent is exactly this stage's target.

**Universes to run at this layer** — one agent per selected chunk, carrying all three questions (they are answered by reading the same files; batching the reading does not loosen the questions):

- **Universe R — incumbent divergence.** For each chunk, grep for the shipped code doing its job today, by the *behavior* described rather than by the plan's file citations, which are what may be stale. Read its **secondary** writes — cache timestamps, audit rows, provenance columns, cleanups — since the plan describes only the primary job and a dropped side effect is invisible on the page. Question: where the design differs, is the difference deliberate and stated?
- **Universe C — caller closure.** Every existing caller of every symbol, file, table, column or route the chunk changes, tests and scripts included. Question: does the plan account for it? A symbol already enumerated against one invariant but not the plan's others is the common shape and reads as coverage.
- **Universe D — dependency guarantee.** Every primitive the chunk **newly makes load-bearing**. Open it, establish what it actually guarantees, and judge the plan's use **at the plan's stated scale**. Run hardest wherever a chunk widens a population, drops a filter, or raises a fallback to primary. Neither R nor C can reach this axis: the plan adopts the dependency rather than diverging from it, and the dependency is a callee rather than a caller.

**Under the tracked layout, sweep across both plans' chunk sets** — sibling plans share a codebase and most of the same incumbents, so covering both costs barely more than one, and a cross-plan chunk pair writing the same column is exactly where a divergence hides. But a symbol or export whose only consumer is a **sibling track's** chunk is accounted-for by that track, not an orphan — file no Universe-C/R gap for "nothing calls this" across the track boundary (`~/.claude/skills/_review-common/principles.md` § Sibling-plan co-delivery). A genuine cross-track **contract drift** (the two tracks disagree on a shared type/column shape) remains a real finding.

**Chunk selection and the cap.** Sweep every chunk on round 1; afterwards, chunks whose chunk-index row hash changed plus chunks whose recorded incumbents changed at HEAD. Cap 6 agents per round, taken in dependency order (earliest wave first — a wrong premise in an early chunk propagates through everything downstream). Record deferrals in `repo_reality_sweep.chunks_deferred` with the round they are owed; a silent cap reads as coverage.

**Skip rule.** This stage is skipped only when the plan names no code at all, which at this layer means it has no chunks. Record the skip and its reason.

**Concurrency.** Unseeded, so it may be spawned in the same message as Persona Prosecution and the Structural Sweep; it needs the repo and the chunk index, not findings.

**Merge.** Every GAP becomes a same-round `REPO_PREMISE_GAP` finding at the swept severity, through the same retraction and authority order as any other. Universe-D gaps are usually director decisions — strengthen the use, narrow the population, or disclose the shortfall with the population sized — not auto-fixes.

**Re-run the three questions on any fix this round applies.** A remedy is new design against the same codebase, and the specific failure is authoring a check the repo already implements next to what you just read. Before emitting a fix that adds a check, filter, or fallback: grep for an existing implementation and prefer importing it to redefining it. This is not hypothetical — in this stage's validation run the first proposed remedy for a Universe-D gap wrote off 47% of the affected population by stopping at two corroborating signals, while a third sat in an adjacent shipped helper one grep away.

---

## Orchestrator Decision

Runs in the main thread. Sub-passes in order: RESET Corroboration Check, Apply Mechanical-Fix Carry-Over, Filter Against Round-Memory Tags, Filter Against Critical-Pair Policies, Fold In Implementability Findings, Class Sweep, Detect Cross-Persona Disagreement, Consolidate Non-Conflicting Fixes, Post-fix premise verification, Same-round focused re-prosecution, Classify Remaining Findings, Render Verdict. The Class Sweep runs *after* the RESET short-circuit gate (a short-circuited round pays for no sweep) and after the finding-thinning filters, but *before* consolidation — so swept siblings are fixed alongside their seeds.

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

### Class Sweep

Runs after Fold In Implementability Findings (all findings collected + thinned by the round-memory and critical-pair filters), before Detect Cross-Persona Disagreement and Consolidate — a swept sibling must be able to become a `STABLE_DISAGREEMENT` like any seed, which it cannot if the sweep runs after disagreement detection. Skipped entirely if a RESET short-circuit fired above (the round already stopped). Per `~/.claude/skills/_review-common/class-sweep.md` — read it for the mechanism, sweep-agent template, merge, and state/verdict schema. Engineering-plan personas file one instance of a recurring class per round (one chunk-index row with an "and", one Goal missing a Brief-mapping, one closure row left `unclear`, one Non-goal contradicted); this fan-out closes the whole class in-round.

**Procedure (per the shared file), with these engineering-plan slots:**

- **Seed grouping.** Group surviving findings (persona + implementability) by `class`. Every distinct `recurring_category` (and any `propagated_identity` with a >1 peer-set) gets one sweep agent, `model: "sonnet"`; genuine singletons (`class_notion` absent / one-location peer-set) are recorded `singleton: true` with no agent.
- **`{peer_set_definition}`** — the engineering-plan repeated units: every chunk-index row, every Brief-mapping entry, every `## Goals` / `## Non-goals` / `## User-facing changes` entry, every Decisions-closure row, every Risks entry, every section body. For `propagated_identity` classes (a cross-chunk identifier / column / flag), the token's callsites across the plan and the repo. Name the specific unit the seed's `peer_set` points at.
- **`{artifact_access}`** — `Read <plan-root>/engineering-plan.md`, `features/<feature>/brief.md`, `features/<feature>/decisions.md`; under the tracked layout, the sibling tracks' plans (a class can recur across tracks). Grep the repo only for `propagated_identity` token sweeps.
- **`{layer_notes}`** — respect `P-EP-IMPL-DETAIL` (a chunk-internal-detail sibling is out of scope at this layer) and `P-EP-BRIEF-GOALS` (an infrastructure chunk without a dedicated Goal is not a `BRIEF_GOAL_UNDELIVERED` sibling). Brief-conformance / `SURFACE_PARITY_GAP` siblings are Class A — they inherit the Class A carry-forward exemption and route to the user, not an auto-fix.
- **Merge.** Dedup siblings against the finding pool by `(class, path_or_section)`; route new siblings through the Filter-Against-Critical-Pair-Policies retraction (same filter the seeds got), then carry the merged set into Detect Cross-Persona Disagreement. Record the `class_sweep` block in the per-round metrics.

### Detect Cross-Persona Disagreement

For each plan span (section / chunk / line range), collect surviving findings — seeds and swept siblings alike. Two personas propose contradictory fixes for the same span → label `STABLE_DISAGREEMENT`.

### Consolidate Non-Conflicting Fixes

Deduplicate findings across personas (merge, attribute to all). Group by target file (engineering plan, brief, decisions log). Apply in a single editing pass per file, ordered by severity (CRITICAL → HIGH → MEDIUM → LOW). Within a severity, document order.

**Forbidden fixes:**
- Weakening the plan (dropping rollback, lowering quality gates) → `OPEN_QUESTION`.
- Editing the brief just to make a chunk fit → `BRIEF_AMENDMENT_NEEDED`.
- "Will be cleaned up later" — if it's not in the plan now, it won't happen.

`IMPLEMENTABILITY_GAP` findings are NOT auto-fixable. The decision requires user judgment about which mechanism to bind to. Carry forward to verdict; they gate `CLOSED` but do not gate `APPROVED`.

### Post-fix premise verification

Per `~/.claude/skills/_review-common/orchestrator.md` § Post-fix premise verification, across the engineering plan, the brief, and `decisions.md`. Use the `section_diff_report` (sections marked `modified` or `added`) as the starting set, then narrow to lines this round's fixes actually wrote.

This layer's claims are behavioral and structural: "the resolver returns X under condition Y", "chunk N writes only to files matching `<glob>`", "this column is NOT NULL", "matches the existing pattern in `<file>`". Distinct from Ground Truth's path-existence checks — this verifies that *behavior at those paths matches the claim*. Render each falsified claim as:

```
[FIX_INTRODUCED_PREMISE_INVERSION] {plan_section}: orchestrator-applied fix asserts "{verbatim claim}". Verification: {what was run}. Actual: "{verbatim contradicting evidence}". Working tree left dirty.
```

### Same-round focused re-prosecution on rewritten prose

Per `~/.claude/skills/_review-common/orchestrator.md` § Same-round focused re-prosecution — one pass, bounded. Engineering-plan reviews thrash hardest here: premise verification catches *false claims* in fix prose, but not the *new persona-class defects* that prose introduces — a decisions-closure remediation an architecture persona would flag as cross-chunk wiring, a Brief Mapping addendum a product persona would flag as scope creep.

Layer specifics:

- **Fan-out** — one focused agent per **(artifact, persona)** pair from the Stage 2 panel, not one per persona. This layer writes three artifacts (engineering plan, brief, `decisions.md`); collapsing to one agent per persona under-covers the cross-file edits.
- **Diff hunks** — `git diff --unified=3 <pre-orchestrator-tree-ish>..HEAD -- features/<feature>/`, capturing added-line spans across the engineering plan, brief, and decisions log.
- **Prompt overrides** — `{audit_report_bullets}` gains a "Diff hunks under review" block listing each (path, line range, verbatim added text); `{skill_specific_preamble}` is `re_pass: focused_diff_hunks; round_number: <N>; original_pass_completed: yes`; the HIGH/MEDIUM filter adds "Do not file premise-inversion RESETs — those are an entry-point-only mechanism, and premise inversions on rewritten prose are caught by post-fix verification, not this pass."
- **Authority on multi-file findings** — class-aware per `principles.md` § Cross-artifact authority order: Class A follows `brief.md > decisions.md > engineering plan`; Class B follows `decisions.md > engineering plan`.
- **Metrics** — agents spawned, findings raised, findings retracted, disagreement spans, fixes applied, falsified claims from the second verification pass.

### Classify Remaining Unresolved Findings

See `~/.claude/skills/_review-common/blocker-classes.md`. Active for engineering plan review: `STRUCTURAL_LINT_FAILED`, `GOAL_VERIFICATION_GAP`, `BRIEF_AMENDMENT_NEEDED`, `CHUNK_SURFACE_EXCESS`, `AUTHOR_GATE_DRIFT`, `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `IMPLEMENTABILITY_GAP`, `UNCORROBORATED_RESET`, `FIX_INTRODUCED_PREMISE_INVERSION`, `REMEDIATION_INCOMPLETE`, `DECISIONS_PROVENANCE_GAP`, `POLISH_PLATEAU`, `REPO_STATE_DRIFT`. `REMEDIATION_INCOMPLETE` and `DECISIONS_PROVENANCE_GAP` are filed by the Round Memory pass's Remediation-completeness sub-pass and are **exempt from Priority-2 carry-forward** — each is an assertion about the completeness of the carry-forward record itself, so retracting it against that record is circular. `DECISIONS_PROVENANCE_GAP` is additionally exempt from Priority 1: a citation to a `decisions.md` entry that does not exist cannot be retracted by `decisions.md`. `GOAL_VERIFICATION_GAP` is **Class A** — skip Priority 1 decisions-log retraction (a bound entry cannot drop it), exactly as `BRIEF_GOAL_UNDELIVERED` / `SURFACE_PARITY_GAP`. `CHUNK_SURFACE_EXCESS` and `AUTHOR_GATE_DRIFT` are HARD blockers gating CLOSED and APPROVED (matching `CONCERN_GATE_FAILED`'s precedent in the author skill); `CHUNK_SURFACE_EXCESS` is exempt from decisions-log-first carry-forward unless the cited `decisions.md` row explicitly arbitrates aggregate surface area (not just one component concern).

**Carry-forward consultation.** Two priorities, applied in order. Priority 1 is the *durable* arbitration record; Priority 2 is the *ephemeral* round-cache. Both are consulted; whichever drops the finding first wins.

**Priority 1 — Decisions log (durable record), class-aware.** `Read` `features/<feature>/decisions.md` if it exists. The retraction logic is split by finding class per `_review-common/principles.md` § Cross-artifact authority order.

**Class-A exemption (mandatory, runs first).** Classify each surviving finding's class before applying retraction:
- Finding's `evidence` field contains a verbatim quote from `brief.md` § Goals / Non-goals / User-facing changes, OR the finding's class is `BRIEF_NONGOAL_TRESPASS` / `BRIEF_GOAL_UNDELIVERED` / `SURFACE_PARITY_GAP` (filed by Stage 1.5 Brief-conformance audit) / `GOAL_VERIFICATION_GAP` (filed by the Ground-Truth Goal-verification audit) → **Class A**. **Skip Priority 1 retraction entirely.** Class A findings are NEVER dropped by decisions-log carry-forward, even when the contradicting evidence is itself a bound `decisions.md` entry. The class-A exemption is the whole point of Stage 1.5; without it, the accumulation pattern (bound decisions trespassing brief Non-goals across rounds) resumes.
- Finding cites a cross-chunk identifier (file path, schema column, module ownership, transaction boundary) → **Class B**. Proceed with Priority 1 retraction below.
- Finding cites a chunk-internal target only → **Class C**. Proceed with Priority 1 retraction below.
- Ambiguous (cites both brief Non-goal AND wiring identifier) → **Class A** (stricter wins). Skip retraction.

Record the class on every finding before applying carry-forward. The verdict template's `decisions_md_consultation` block reports `findings_dropped_class_B: <n>; findings_dropped_class_C: <n>; class_A_exempt: <n>` so a verdict can be audited for whether the exemption fired correctly.

**For Class B and C findings only**, scan decisions.md for entries where ALL of:
- The entry's `Decision:` subject substring-matches the finding's `path_or_section` (matching identifier, section heading, or quoted phrase fragment ≥4 words).
- The entry's `Status:` is `bound` (case-insensitive) and the entry is in the `## Active (bound)` section — an entry marked `superseded by "<title>" (<date>)` or `obsolete` in the `## Archived (superseded / obsolete)` tail never binds or retracts (per `~/.claude/skills/_review-common/principles.md` § What counts as a bound entry).
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

**Final line — verdict banner.** After the output block below and any Scope-Reduction-Candidates block, run the shared verdict-banner script and emit its output verbatim (`~/.claude/skills/_review-common/blocker-classes.md` § Verdict banner) as the **very last** thing in your response, so the CLOSED / APPROVED / NEEDS USER INPUT status is visible without scrolling.

### Output

```
## Engineering Plan Review v2 Complete: <plan-root>/engineering-plan.md

**Round:** {round_number} {(plan_growth: +N% / unchanged-section gate active) | (round 1 — no prior state)}
**State source:** {`Loaded from ~/.claude/cache/review-state/<slug>.json (round N → N+1)` | `Migrated from legacy ~/.claude/cache/review-state/<feature>.json → <slug>.json (round N → N+1)` | `Round 1 (no prior state)` | `Reconstructed from decisions.md (state file missing; round_number reset to 1; recently_resolved_blockers seeded from decisions log)`}
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
**Class sweep:** {skipped (no sweep-eligible categories) | ran with {n} agents; siblings_found: {n}; siblings_after_critical_pair_filter: {n}; peer-sets widened: {n}/{total}}
**Structural sweep (unseeded):** {ran with {n} agents over {universes}; members: {n}; gaps: {n} ({severities}); undetermined: {n} | universes skipped: {universe} ({reason})}
**Final Tier 1 weight:** {n}
**Final Tier 2 weight:** {n} (floor: 4)

### Structural sweep (unseeded)
Always rendered when the plan has a qualifying universe — an all-clean sweep is the evidence the universe was covered, and it is what makes a `CLOSED` verdict mean more than "no reviewer noticed anything".
- Universe: {name} — {members_enumerated} members: {closed} closed, {gap} gap, {na} n/a, {undetermined} undetermined
- Skipped: {universe} ({reason})
- Gaps promoted to findings: {n} ({severities})

### Class sweep audit
For each class swept (omit block entirely when class_sweep.ran=false):
- Class: {name} ({class_notion}) — bare invariant: {bare_invariant}
- Peer-set: handed {peer_set_handed} → walked {peer_set_walked} {(widened — {justification}) | (confirmed widest)}; swept clean: {n}
- Instances: {seeds} seed + {siblings_found} sibling ({siblings_after_critical_pair_filter} survived critical-pair filter); resolution: all fixed this round | {n} escalated as {blocker class}
- Singleton classes recorded (no peer-set): {list, or none}

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
- [BRIEF_NONGOAL_TRESPASS] {plan section or bound decisions.md entry} — brief Non-goal: "{verbatim quote}"; trespassing evidence: "{verbatim quote}"; reasoning: {prosecutor reasoning paragraph}. Resolution paths: {amend_brief / drop_section / unbind_decision}.
- [BRIEF_GOAL_UNDELIVERED] {brief Goal} — Goal: "{verbatim quote}"; the engineering plan's Brief Mapping table lists chunks {x, y, z} but none non-trivially delivers it (supporting-infrastructure routing alone does not count). Resolution paths: {add_delivering_chunk / amend_brief_drop_goal}.
- [SURFACE_PARITY_GAP] {brief Goal} — Goal: "{verbatim quote}"; intended outcome + domain + authoritative signal: {reconstructed maximal_scope}; narrowing axis: {subset-of-domain | weaker-substitute-basis | premature-action-before-basis}; the shortfall: {the specific consumer/surface/input/stage delivered by a weaker proxy, not at all, or acted on irreversibly before its basis exists — chunks {x, y}}. {deferred path: why the residual is required-work, not a launch-acceptable cut}. {mechanism-phrased Goal: note it needs outcome-rephrasing upstream}. Resolution paths: {extend_coverage / scope_down_brief}.
- [GOAL_VERIFICATION_GAP] {brief Goal / Non-goal, verbatim} — {missing acceptance chunk | Goal has no `Verified by` proof | testable-absence Non-goal has no owning test | Non-goal mis-classified scope-boundary}. The Goal may be delivered, but nothing proves it, so a later refactor can break the contract with no failing test. Resolution paths: {add_acceptance_chunk / add_verified_by_proof / reclassify_and_add_absence_test / keep_manual_review_with_reason}. (Class A — not retracted by a bound decision.)
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
- **Round Memory pass is mandatory.** Skipping it disables the plan-growth gate and section-diff gate, returning the skill to its pre-fix thrash mode. State file lives at `~/.claude/cache/review-state/<feature>[__<track>]__engineering-plan.json` (NOT in the project repo).
- **Decision-Closure Audit is mandatory, including the prior-classification consistency check.** Skipping the consistency check lets the same decision flip between `cross-chunk-wiring` and `chunk-internal` across rounds, forcing the user to add then delete the same binding.
- **Persona Prosecution agents return fix lists; never edit files.** All edits applied by orchestrator.
- **Premise interrogation pass is mandatory.** Both the repo-state and brief-environment sub-passes MUST run. A persona producing zero RESETs must explicitly state `premise_interrogation: passed` (covering both sub-passes). Skipping the brief-environment sub-pass is a workflow bug — it lets brief premises that contradict project memory poison every downstream chunk.
- **Imagined-Implementer Dry Run is mandatory.** Skipping removes the convergence forcing-function and lets `IMPLEMENTABILITY_GAP`s slip through.
- **RESET corroboration gate.** Single-persona RESET reclassified to CRITICAL HARD, not auto-escalated. Two-of-three on the same span is the only short-circuit signal.
- **Orchestrator applies critical-pair policies before applying fixes.** Findings contradicting a policy are retracted, not relitigated.
- **Never** mark CLOSED while any blocker class (`BRIEF_NONGOAL_TRESPASS`, `BRIEF_GOAL_UNDELIVERED`, `SURFACE_PARITY_GAP`, `BRIEF_AMENDMENT_NEEDED`, `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `IMPLEMENTABILITY_GAP`, `UNCORROBORATED_RESET`, `REPO_STATE_DRIFT`) is non-empty.
- **Never** mark APPROVED while a non-`IMPLEMENTABILITY_GAP` blocker is present (including `BRIEF_NONGOAL_TRESPASS` / `BRIEF_GOAL_UNDELIVERED` / `SURFACE_PARITY_GAP` — Class A blockers fail APPROVED as well as CLOSED, because a plan that trespasses the brief or delivers a Goal over a subset of its domain is not shape-correct).
- **APPROVED does not unblock per-chunk plan writing.** Only CLOSED does. Communicate clearly.
- **Never** edit the brief just to make a chunk fit. That's `BRIEF_AMENDMENT_NEEDED`.
- **Never** weaken the plan to resolve a finding. That's `OPEN_QUESTION`.
- **Never** auto-fix an `IMPLEMENTABILITY_GAP`. The decision requires user judgment.
- **Orchestrator verifies its own edits.** Post-fix premise verification runs after Consolidate Non-Conflicting Fixes, before Classify Remaining Findings. Skipping it allows the orchestrator's own prose-rewrite fixes to introduce premise inversions that cascade into the next round.
- **Class Sweep is mandatory** whenever a surviving finding declares `class_notion: recurring_category` (or a `propagated_identity` with a >1 peer-set). It runs as an orchestrator sub-pass after the RESET short-circuit gate and the finding-thinning filters, before Consolidate: one sweep agent per distinct such category walks the peer-set (chunk rows / Goals / Non-goals / closure rows / sibling tracks) and promotes every sibling to a same-round finding, routed through the critical-pair filter. Per `~/.claude/skills/_review-common/class-sweep.md`. Closes a defect class in the round it was found instead of leaking one sibling per round. Skipped only when zero sweep-eligible categories exist or a RESET short-circuit already fired. **Each sweep agent must perform the Method-step-1 peer-set challenge** — restate the class as its bare invariant and widen the handed peer-set to that invariant's widest applicable set before walking. A faithfully-walked *narrow* peer-set reports clean while leaving the class open, and that failure is invisible in the instance counts.
- **Structural Sweep is mandatory and is NOT contingent on the round producing findings.** Per `~/.claude/skills/_review-common/structural-sweep.md`: one unseeded agent per applicable universe (Universe L — every gate × every condition, is every failing state exitable; Universe P — every destructive path × every protection the plan itself requires), run over both plans under the tracked layout. It exists because the Class Sweep is seeded and therefore structurally blind to a class no persona filed — the pipeline's only unseeded exhaustive pass otherwise covers brief Goals alone. A round with zero persona findings still runs it; a verdict reporting no structural sweep on a gated plan is incomplete no matter how clean the rest of the round looked. Skipped per-universe only on the stated skip rule, and every skip records its reason.
- **Same-round focused re-prosecution is mandatory** when ANY of: orchestrator engineering-plan fix count > 0, cross-file fix count (brief / decisions log) > 0, premise verification falsified-claim count > 0. Skipping it lets persona-class defects in orchestrator-rewritten prose bake in and surface as fresh blockers next round. Bounded: exactly one re-pass on the diff hunks Stage 3 wrote.
- **The Remediation-completeness pass is mandatory on every `round_number > 1`**, and covers what the two verification stages above structurally cannot: post-fix premise verification and the same-round re-pass both scope to the orchestrator's *own* edits, while the majority of text entering a round is remediation the **user** wrote between rounds to clear the last verdict's blockers. Every prior blocker gets all three questions — closed, swept into every coupled site, arbitration recorded in `decisions.md` — with no sampling. The swept question carries the yield: a remediation that adds a terminal action, a chunk, a marker, or a gate changes the size of sets that other sections state as fixed counts and that other tables enumerate as complete, and landing it only in its motivating section is the dominant defect shape at this layer. Skipping the pass makes a `NEEDS USER INPUT` → re-invoke cycle non-convergent by construction: each round's fix silently seeds the next round's findings, and the blocker count stops falling for reasons no stage attributes.
- **Carry-forward consultation is mandatory and uses two priorities in order.** Priority 1: consult `features/<feature>/decisions.md` for findings contradicting bound entries — drop them with citation. Priority 2: consult `recently_resolved_blockers` for ephemeral round-cache matches — downgrade to `OPEN_QUESTION` unless `current_reclassification_justification` is filed. Authority order: `decisions.md` > `engineering-plan.md` > prior round's verdict text.
- **Compliance self-check.** Before emitting the verdict, confirm: (1) post-fix premise verification ran with non-empty stats; (2) same-round re-prosecution ran when any of the three triggering conditions held, and recorded re-pass agent counts; (3) Priority 1 carry-forward (decisions.md) fired when the file exists, even on round 1; (4) Priority 2 carry-forward fired when `recently_resolved_blockers` had matching entries; (5) if state was reconstructed from `decisions.md`, the verdict's State source line reflects it; (6) **Stage 1.5 Brief-conformance audit ran in full** — the Brief-conformance Prosecutor was spawned AND one Scope-fidelity Adversary was spawned per at-risk Goal (`brief_conformance_report.scope_adversaries_spawned` equals the length of `goals_at_risk`, and every at-risk Goal — domain-quantified or authoritative-signal — is in `goals_at_risk` or justified in `goals_skipped_not_at_risk`); `brief_conformance_report` is non-empty in Stage 3 input; and any filed `BRIEF_NONGOAL_TRESPASS` / `BRIEF_GOAL_UNDELIVERED` / `SURFACE_PARITY_GAP` findings appear in the verdict. If no adversary was spawned but at-risk Goals exist, the audit is incomplete — re-run Stage 1.5's step (b) before posting; (7) **Class-A exemption fired correctly** — if `brief_conformance_report.findings_high_hard > 0` AND `decisions_md_consultation.class_A_exempt < findings_high_hard`, some Class A findings were dropped by carry-forward; re-classify and restore them before posting; (8) **Class Sweep ran for every recurring category** — `class_sweep.sweep_agents_spawned` equals the count of distinct sweep-eligible (non-singleton) seed categories after grouping, every spawned agent recorded a `peer_set_size` and non-empty `swept_clean` (instances with empty `swept_clean` on a multi-member peer-set = the set was not walked; re-run that agent), and every surviving sibling appears in the consolidated fix set or a blocker. A round with `class_notion: recurring_category` seeds but `sweep_agents_spawned: 0` skipped the stage — run it before posting; (9) **Goal-verification audit ran** — `audit_report.goal_verification` is populated: the acceptance chunk was confirmed present + DAG-sink, `goals_with_proof == goals_total`, `non_goals_classified == non_goals_total`, and any `GOAL_VERIFICATION_GAP` filed appears in the verdict and was NOT dropped by carry-forward (it is Class A). A verdict with `goal_verification` absent skipped the audit — run it before posting; (10) **Structural Sweep ran every applicable universe** — `structural_sweep.ran` is true whenever the plan has a qualifying universe, `universes_run` plus `universes_skipped` accounts for every universe this layer declares with a reason per skip, each universe recorded `members_enumerated` and a non-empty `cells` list, and every GAP appears in the consolidated fix set or a blocker. **This check is independent of the round's finding count** — a zero-finding round that skipped the stage is non-compliant, which is precisely the case the stage was added for; (11) **Repo Reality Sweep ran** — `repo_reality_sweep.ran` is true whenever the plan has chunks; `chunks_swept` + `chunks_deferred` + `chunks_inherited_clean` accounts for every chunk across both plans under the tracked layout, with a reason per deferral and a `from_round` per inheritance; every swept chunk records a non-empty `incumbent_files_read` and an `enumeration_query` per universe (a universe with no query was not run, whatever its cells say); every `inherited_clean` chunk has stored `incumbent_files_blob_shas` that still match HEAD; and every GAP appears in the consolidated fix set or a `REPO_PREMISE_GAP` blocker. **Independent of the round's finding count** — a clean round that skipped this stage is non-compliant, which is the case it was added for; (12) **every Class-Sweep agent performed the peer-set challenge** — each category recorded a `bare_invariant`, both `peer_set_handed` and `peer_set_walked`, and an explicit `peer_set_widened` flag with a justification when true. A `peer_set_walked` copied from `peer_set_handed` with no evidence the supertype question was asked did not run Method step 1; re-run that agent; (13) **Remediation-completeness ran on every prior blocker** — on `round_number > 1`, `remediation_completeness` has one entry per entry in the prior round's `prior_blockers`, each with a non-empty `coupled_sites_checked` and an explicit `decisions_entry` (a heading, or `none` with its class). An entry with `closed: yes` and an empty `coupled_sites_checked` answered only the first of three questions; re-run it. Any `REMEDIATION_INCOMPLETE` / `DECISIONS_PROVENANCE_GAP` filed must appear in the verdict — neither is retractable by Priority-2 carry-forward, since both are assertions *about* the carry-forward record rather than findings subject to it.
- **Always** quote verbatim from plan, brief, repo, or audit_report when justifying a finding.
- **Always** label remaining findings with their blocker class.
- **No re-review loop within a single invocation.** Escalate; let the user re-invoke.
- **Do not re-run `/engineering-plan-author` to clear a completed review.** When the verdict is `NEEDS USER INPUT` (or `APPROVED` with open cross-chunk decisions), the next step is targeted edits that clear the listed blockers / bind the open decisions, then re-invoking `/engineering-plan-review-v2` (optionally triaged through `/explain-blockers` or `/solve-blockers`). Re-running `/engineering-plan-author` re-enters the full authoring pipeline over the whole engineering plan — wrong tool for clearing ordinary blockers (`OPEN_QUESTION`, `STABLE_DISAGREEMENT`, `IMPLEMENTABILITY_GAP`, `BRIEF_AMENDMENT_NEEDED`, and the like). Re-run the author skill only in two cases: the mid-cycle `Status: needs-user-input` refuse path (the artifact is already a partial draft and the author resumes it in warm mode); or the rare case where the plan is fundamentally broken and must be re-authored wholesale (ask in plain language). The author-gate blockers (`AUTHOR_GATE_DRIFT`, `CONCERN_GATE_FAILED`) are NOT re-author cases — the reviewer already recomputes those gates, so they are cleared by the same targeted agent edits as every other blocker (decompose / rewrite the row / cite an arbitration) plus reconciling the stale author-state field. Re-running the author to clear them desyncs the in-flight review state (`section_hashes`, `round_number`, blocker carry-forward) for no benefit.

## Compliance self-check (before rendering verdict)

Run the checklist in `~/.claude/skills/_review-common/orchestrator.md` § Compliance self-check and state each result in the verdict. A failed check is reported, never silently skipped. Add one layer-specific line: whether the RESET corroboration check ran, and on how many single-persona RESET claims.

## Edge cases

- **No brief found** at `features/<feature>/brief.md` → CRITICAL. Engineering plan cannot exist without a brief; stop and escalate.
- **Plan in old monolithic format** (e.g., `context/plans/049_*.md`) → confirm with user whether to review-and-port or stop. This skill assumes the new structure.
- **Brief and plan disagree on a Goal** → `BRIEF_AMENDMENT_NEEDED`. Brief is canonical; user signs off on amendment or plan changes.
- **Chunk plans don't yet exist for proposed chunks** → expected. Ground Truth Repo Reality is limited to architecture-level claims for those chunks.
- **Chunk plan exists in `implementation/`** → Ground Truth spot-checks consistency with engineering-plan chunk-index row. Doesn't full-review (that's `/plan-review-v2`'s job).
- **Multiple engineering plans across features in one invocation** → out of scope. Run once per feature.
- **Decisions log missing** (`features/<feature>/decisions.md`) → `OPEN_QUESTION` only if the plan has a non-obvious architectural choice without a `Why:` paragraph; otherwise no finding.
- **State file missing but `decisions.md` exists** → reconstruct partial state. Round number resets to 1. Seed `recently_resolved_blockers` from `decisions.md` entries (Active bound entries only — skip the `## Archived (superseded / obsolete)` tail; per `~/.claude/skills/_review-common/principles.md` § What counts as a bound entry) (each entry's `Decision:` line becomes a row with `blocker_class_when_resolved: RESOLVED`, `path_or_section` from the entry's subject, `user_decision` from the entry's `Why:` paragraph capped at ~200 chars, `carry_forward_until_round = 2`). Section hashes recompute clean (no diff vs prior, full prosecution latitude). Verdict's State source records `Reconstructed from decisions.md`. Warn the user that round-counter reset means plan-growth and section-diff gates are dormant for this invocation.
- **State file missing AND no `decisions.md`** → cold start. Round 1, empty `prior_blockers`, empty `recently_resolved_blockers`. No reconstruction; full re-prosecution latitude. This matches the legacy behavior.
- **HEAD changes mid-review** → `REPO_STATE_DRIFT`. User re-runs.
