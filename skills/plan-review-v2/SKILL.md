---
name: plan-review-v2
description: Single-pass review of one or more chunk implementation plans with cross-invocation convergence. Refuses artifacts in `Status: needs-user-input` state (the partial-draft mid-cycle state written by `/plan-author`). Gated per-plan on `/plan-lint` (Factoring Contract fields, and-chunks, vague acceptance criteria, premature abstractions). Four phases follow: Round Memory loads prior-round state; Stage 1 grounds each plan in repo reality; Stage 2 runs persona prosecution in parallel (N plans × M personas = N×M parallel agents, fix-list output); Stage 3 consolidates and applies fixes with convention extraction across ≥3 shared-pattern bullets and cross-file scope to decisions.md / engineering-plan.md, runs post-fix premise verification, runs SAME-ROUND focused re-prosecution on diff hunks (≤1 re-pass; bounded, never an inner loop), runs decisions-log-first carry-forward, classifies remaining, persists state, renders verdict. Round memory and decisions.md ensure the next run does not re-prosecute already-arbitrated questions. Sister to /engineering-plan-review-v2 (engineering-plan layer).
user-invocable: true
---

# Plan Review v2 — Staged Single-Pass

Plans are cheap to write and expensive to execute. A hallucinated plan burns days chasing files that don't exist. This skill prosecutes chunk implementation plans through a Structural Lint gate plus three stages, with bounded same-round verification on orchestrator-rewritten prose. Never a multi-round inner loop — survivors of the bounded same-round re-pass land in the verdict and the user re-invokes.

This is the chunk-plan layer. Sister skill `/engineering-plan-review-v2` reviews engineering plans (`features/<feature>/engineering-plan.md`). If the user asks for review of an engineering plan, redirect.

## Shared scaffolding

- `~/.claude/skills/_review-common/principles.md` — stance, banned rationalizations, severity/tier, plan style rules
- `~/.claude/skills/_review-common/agent-prompt.md` — persona-agent prompt template
- `~/.claude/skills/_review-common/critical-pairs.md` — active subset for chunk plan review: `P-CLASS-SCOPE, P-FULL-FILE, P-CHUNK-TEST-PATHS, P-CHUNK-COMMANDS, P-CHUNK-SINGLE-CONCERN, P-CHUNK-READ-FIRST`
- `~/.claude/skills/_review-common/blocker-classes.md` — blocker registry + verdict gate

## Usage

```
/plan-review-v2 <plan-path-1> [plan-path-2] ... [--personas <p1> <p2> ...]
```

**Examples:**

```
# Single plan, auto-assign best persona
/plan-review-v2 .scratch/wave1-F14-parametric-sweep.md

# Multiple plans, auto-assign one persona per plan
/plan-review-v2 .scratch/wave1-F9.md .scratch/wave1-F10.md

# Single plan, explicit personas — reviewed by ALL (M parallel agents)
/plan-review-v2 features/author-tmdb-hydration/implementation/cascade-rewrite.md --personas backend architecture

# Multiple plans with explicit personas — N×M parallel agents
/plan-review-v2 .scratch/F12.md .scratch/F13.md .scratch/F14.md --personas frontend backend

# Chunk slug shorthand — resolves to features/<feature>/implementation/<slug>.md
/plan-review-v2 cascade-rewrite
```

## Argument parsing

Split `$ARGUMENTS` on whitespace. Classify each token:

- `--personas` → all subsequent non-path tokens are persona names.
- Token contains `/` or ends with `.md` → plan path.
- Otherwise (kebab-case, no separator, no `.md`) → chunk-slug shorthand. Resolve as `features/*/implementation/<slug>.md` if exactly one match exists; ambiguous → ask which feature.

**Path resolution:**
- Starts with `/` or `./` → use as-is
- Starts with `.scratch/`, `context/`, or `features/` → relative to repo root
- Ends with `.md`, no separator → prepend `.scratch/`

**Backward compatibility:** Exactly one plan + one or more non-path tokens without `--personas` → treat the non-paths as personas.

No arguments → search `.scratch/` for `*.md` files that look like plans (contain `## Implementation`, `## Files to`, or `**Effort:**`), list them, ask which to review.

## Persona resolution

### Explicit personas
Load each from `personas/{name}.md`. **Every plan is reviewed by every listed persona.** N plans × M personas = N×M parallel agents. Missing persona file → stop and report.

### Auto-assignment (no `--personas`)

Scan each plan for the strongest keyword match:

| Persona | Keywords | Best for |
|---|---|---|
| `frontend.md` | component, form, button, table, column, page, tab, modal, React, JSX, Tailwind | UI components |
| `backend.md` | API, endpoint, query, mutation, hook, fetch, cache, queryKey | API hooks, data fetching |
| `architecture.md` | store, state, integration, route, dependency, pattern, system | Cross-cutting architecture |
| `data-visualization.md` | chart, D3, Recharts, SVG, topology, graph | Charts, viz |
| `product.md` | user flow, sweep, batch, multi-select, UX, edge case, empty state | User-facing features |
| `code-reviewer.md` | refactor, polish, consistency, error, type safety, test | Code quality |
| `ui-code-review.md` | dark mode, theme, CSS, design token, responsive, accessibility | Theming, a11y |
| `testing.md` | test, coverage, mock, integration, validation, assertion | Test strategy |
| `security.md` | auth, authz, token, secret, injection, sanitize, CSRF | Security |
| `slice-and-dice-design.md` | dice, hero, monster, boss, face, pip, textmod | Slice & Dice balance |
| `ai-development.md` | chunk, checkpoint, parallel, agent, implementation plan | Plan structure |

**Rules:**
- Pick the strongest match per plan.
- No two plans share a persona unless there are more plans than personas — fall back to second-best.
- `ai-development.md` is loaded as supplementary context for every Stage 2 agent but is not the assigned persona unless explicitly requested.

---

## Workflow

```
Per plan (parallel across plans):
  Status-frontmatter check              (deterministic, hard short-circuit, runs first)
     ↓ Status: needs-user-input → REFUSE, point user back at /plan-author; stop
  Stage 0: Structural Lint Gate         (deterministic, hard short-circuit)
     ↓ runs /plan-lint; FAIL → emit STRUCTURAL_LINT_FAILED, stop
  Round Memory Pass                     (deterministic, no LLM judgment)
     ↓ loads ~/.claude/cache/review-state/<plan-slug>.json; computes
     ↓ round_number, prior_blockers, recently_resolved_blockers
  Stage 1: Ground truth pass            (deterministic, no LLM judgment)
     ↓ produces audit_report per plan
  Stage 2: Persona prosecution          (LLM judgment, M parallel agents per plan)
     ↓ produces fix_lists per (plan, persona)
  Stage 3: Orchestrator decision        (deterministic + judgment)
     ↓ applies fixes (with convention extraction + cross-file fix scope),
     ↓ runs post-fix premise verification on rewritten prose,
     ↓ runs SAME-ROUND focused re-prosecution on diff hunks (≤1 re-pass),
     ↓ runs carry-forward consultation: decisions.md FIRST, then state-file cache,
     ↓ classifies remaining, renders verdict, persists state with per-round metrics
```

In multi-plan mode, all plans' Stage 0 / Round Memory / Stages 1/2 may launch in parallel. Stage 3 is per-plan. A Stage 0 FAIL on plan A does not block Stages 1+ on plan B — each plan's gate is independent.

---

## Status-frontmatter check (MANDATORY, HARD SHORT-CIRCUIT, PER PLAN, RUNS BEFORE STAGE 0)

`Read` the chunk plan's YAML frontmatter. Extract the `Status:` value.

`Status:` is a binary mid-cycle signal: `needs-user-input` (mid-cycle) or absent (ready). Lifecycle signals (merged, in-progress) come from git/PR state, not frontmatter.

- **`Status: needs-user-input`** → stop processing this plan. Do NOT spawn Stage 0 or anything after. The plan is mid-cycle by design (the partial draft was written by `/plan-author` with a `## Pending blockers` section appended; the user is between resolving blockers and re-invoking the author skill). Emit:

  ```
  PLAN: <plan-path>
  STATUS: REFUSED (artifact in mid-cycle authoring state)

  This chunk plan has frontmatter `Status: needs-user-input`. The author skill (`/plan-author`)
  wrote it as a partial draft with unresolved blockers listed in the `## Pending blockers`
  section at the end of the file. Reviewing a partial draft would re-prosecute issues the
  author already surfaced.

  Resolve the blockers listed in `## Pending blockers`, then re-invoke
  `/plan-author --rewrite <feature>/<chunk-slug>`. The author skill removes the `Status:`
  frontmatter on a successful APPROVED emission; re-invoke `/plan-review-v2` once the plan
  is back to no-Status-field state.
  ```

  Other plans in the multi-plan invocation continue independently.

- **No `Status:` field, OR any other value** → proceed normally. Round Memory Pass consults the plan-author sidecar at `~/.claude/cache/author-state/<feature>__<chunk-slug>.json`; if `authoring_mode: "draft"` is set there, the verdict surfaces a draft warning. Persona prosecution still runs.

The check is deterministic and runs before any LLM judgment or shell invocation. A `Status: needs-user-input` artifact never reaches Stage 0.

## Stage 0 — Structural Lint Gate (MANDATORY, HARD SHORT-CIRCUIT, PER PLAN)

```bash
python3 ~/.claude/skills/plan-lint/lint.py <chunk-plan-path>
```

This catches structural defects that no amount of LLM judgment fixes: missing/empty Factoring Contract fields, "and"-chunks, vague acceptance criteria (`implement` / `complete` / `ensure` / `handle` / `support` without a measurable predicate), premature abstractions (< 2 already-merged consumers), position-encoded slugs (`phase-N-*`, `step-N-*`, `wave-N-*`, `chunk-NN`).

**Per-plan behavior:**

- **Exit 0:** record `lint_clean=true` and proceed to Stage 1.
- **Exit 1 (lint FAILED):** stop processing this plan. Do NOT spawn Stage 1/2. Emit:

  ```
  PLAN: <plan-path>
  STATUS: NEEDS USER INPUT (blocker: STRUCTURAL_LINT_FAILED)

  /plan-lint found N structural defects in this chunk plan. Persona prosecution
  is not run because LLM judgment on top of a structurally-broken plan produces
  noise.

  <verbatim /plan-lint output>

  Fix the structural defects above and re-invoke /plan-review-v2 on this plan.
  ```

  Other plans in the invocation continue independently.

- **Exit 2 (usage / IO error):** stop and report. Likely a path mistake.

Why short-circuit: a persona reviewing a plan with vague acceptance criteria and no Owns set produces findings that assume those gaps are recoverable, but they require the plan-author to make a decision. That wastes the persona's reasoning budget.

---

## Round Memory Pass (per plan, NO LLM JUDGMENT)

This pass exists to break two thrash patterns at the round-loading boundary:

1. **Re-prosecution of resolved blockers** — the user re-invokes after addressing prior-round findings, and personas re-file the same finding under new framing.
2. **Orchestrator-introduced premise inversions** — Stage 3 fixes rewrite chunk-plan prose in ways that flip claims about behavior; the next round prosecutes the new (false) text.

A third thrash pattern — **fix-cascade prosecution**, where round-N orchestrator fixes write fresh prose that round-N+1 personas correctly file as new defects — is broken by Stage 3's same-round focused re-prosecution and decisions-log-first carry-forward consultation, NOT by this pass. The Round Memory Pass loads state; Stage 3 enforces the discipline that closes the round-N → round-N+1 fix-cascade window.

State is carried via an external artifact under `~/.claude/cache/`, NOT mutated into the chunk plan itself. The durable arbitration record is `features/<feature>/decisions.md` (committed to the repo); the ephemeral state-file cache supplements it with recently-resolved-blocker context that decays after `carry_forward_until_round`.

### State file location

State lives at `~/.claude/cache/review-state/<plan-slug>.json` (NOT in the project; survives worktrees; never committed). Slug derivation:

- `features/<feature>/implementation/<chunk-slug>.md` → slug `<feature>__<chunk-slug>` (double underscore separator avoids collisions across features)
- `.scratch/<name>.md` → slug `scratch__<name>`
- Other paths → basename without `.md`, with `/` replaced by `__`

Create the parent directory with `mkdir -p ~/.claude/cache/review-state` if missing.

### State file schema

```json
{
  "plan_slug": "<slug>",
  "plan_path": "<original path passed at invocation>",
  "last_review_at": "<ISO 8601 UTC>",
  "last_verdict": "APPROVED | NEEDS_USER_INPUT",
  "last_plan_sha256": "<hex>",
  "round_number": <integer, 1-indexed>,
  "prior_blockers": [
    {
      "blocker_class": "STABLE_DISAGREEMENT | OPEN_QUESTION | FIX_INTRODUCED_PREMISE_INVERSION",
      "path_or_section": "<chunk slug, section heading, or file:line>",
      "summary": "<one-line>",
      "raised_in_round": <integer>,
      "current_reclassification_justification": "<one-sentence repo-state justification when re-raised after prior resolution; absent on first appearance>"
    }
  ],
  "recently_resolved_blockers": [
    {
      "blocker_class_when_resolved": "<class | RESOLVED>",
      "path_or_section": "<chunk slug, section heading, or file:line>",
      "summary": "<one-line>",
      "resolved_in_round": <integer>,
      "user_decision": "<one-sentence rationale; capture priority below>",
      "carry_forward_until_round": <integer; defaults to resolved_in_round + 2>
    }
  ],
  "per_round_metrics": {
    "round_<N>": {
      "stage_3d_fixes_applied": <integer>,
      "convention_extractions_applied": <integer>,
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

The `per_round_metrics` map persists across invocations — each round appends a new `round_<N>` entry without dropping prior rounds. Older rounds remain visible so the user (and future invocations) can see convergence trends — `re_pass_findings_persisted_to_blockers` should trend toward zero as the plan stabilizes; `convention_extractions_applied` should be nonzero in early rounds and drop to zero once recurring patterns are pinned in `§Conventions`; `decisions_md_consultation.findings_dropped` should rise once the user starts recording negative decisions in `decisions.md`.

### Load prior state

`Read` the state file. Cases:

1. **File does not exist** → cold start. `round_number = 1`, `prior_blockers = []`, `recently_resolved_blockers = []`.
2. **File exists, plan SHA matches `last_plan_sha256`** → user re-invoked without modifying the plan. `round_number = stored + 1`. Carry `prior_blockers` and `recently_resolved_blockers` forward (drop entries where `carry_forward_until_round < new round_number`).
3. **File exists, plan SHA differs** → user modified the plan between rounds. `round_number = stored + 1`. The plan diff IS the user's response to prior-round blockers; carry forward but expect persona prosecution to file fewer findings against modified spans.

### Capture priority for `user_decision`

When recording a resolved blocker, populate `user_decision` from these sources in priority order, stopping at the first that yields a non-empty rationale:

1. **User text in the current invocation `$ARGUMENTS`** — e.g., "round 2, I tightened the TDD assertions"
2. **Plan diff** since `last_plan_sha256` — if the modification is small (≤200 chars added text), the diff IS the rationale; record it verbatim
3. **Commit message body** since `last_review_at` (use `git log <last_review_sha>..HEAD --format=%B` if commits exist between rounds)
4. **Commit message subject** as fallback
5. **`"No rationale recorded"`** if none of the above yields a rationale

Cap at ~200 chars. Truncate with `…` if longer.

### Persist on exit

After Stage 3 verdict rendering, update the state file:

- `last_review_at` ← current UTC timestamp
- `last_verdict` ← rendered verdict
- `last_plan_sha256` ← sha256 of the post-fix plan file
- `round_number` ← incremented
- `prior_blockers` ← rebuilt from current verdict's blockers (open at this round's exit)
- `recently_resolved_blockers` ← extended: prior round's blockers no longer in current verdict become entries with `user_decision` populated per the capture priority above; existing entries with `carry_forward_until_round < new round_number` are dropped
- `per_round_metrics["round_<N>"]` ← appended with this round's stats: `stage_3d_fixes_applied`, `convention_extractions_applied`, `cross_file_edits[]` (one entry per file written), `re_pass_ran`, `re_pass_diff_hunks_reviewed`, `re_pass_additional_fixes_applied`, `re_pass_findings_persisted_to_blockers`, `decisions_md_consultation.entries_matched`, `decisions_md_consultation.findings_dropped`. Prior rounds' entries are NOT dropped — the map is append-only across invocations.

If verdict is `APPROVED`, leave the state file in place for future re-invocation against the same plan (e.g., after partial implementation).

### Edge cases

- **Multi-plan invocation** → each plan has its own state file, loaded independently.
- **Manual reset** → user deletes the state file. Skill does not auto-detect rewrites.

---

## Stage 1 — Ground truth pass (MANDATORY, NO LLM JUDGMENT)

Produces an `audit_report` per plan. Stage 2 personas MUST NOT re-prosecute facts already verified here.

### 1a. Engineering-plan trace (chunk plans only)

If the plan resolves to `features/<feature>/implementation/<slug>.md`:
- Open `features/<feature>/engineering-plan.md`.
- Find the row in the chunk index whose slug matches.
- Verify: chunk name in plan matches engineering-plan row; declared `Code deps` match; chunk does not exceed scope implied by the engineering-plan's chunk description.

For freestanding plans (`.scratch/<plan>.md` with no engineering-plan parent), skip and note `engineering_plan_trace: N/A`.

### 1b. Repo Reality (mechanical)

Use tool output, not memory. Record `git rev-parse HEAD` once at start; if it changes mid-stage, restart.

- **Tree:** `ls` repo root.
- **File list:** `git ls-files | wc -l`, spot-check.
- **Test infrastructure:** `git ls-files | grep -E '(^|/)(test|tests|spec|__tests__)(/|$)|\.(test|spec)\.[a-z]+$'`. Look, don't assume.
- **CI:** `ls .github/workflows/`. If the plan claims it adds/changes a CI job, verify the workflow file and job name byte-for-byte.
- **Build/test commands:** Read `package.json` scripts, `Cargo.toml`, `Makefile`, `pyproject.toml`, `justfile`. The plan may only assume commands the project actually defines.
- **Entry points:** for every file path in the plan, `ls` it.
- **Identifiers:** for every function, type, field, flag, CLI arg, env var, route, table/column the plan names — grep for it. Record hit counts. Zero-hit identifier → `[HARD: hallucination]` unless the plan explicitly creates it (then verify creation location matches project patterns).
- **Line-number claims:** for every "modify line N of path" claim, `Read` `path` around line N and verify content matches plan's assertion. Mismatch → `[HARD: line-content drift]`.

Output a `Repo Reality (HEAD: <sha>)` block: tree, file count, test layout, CI workflows, build/test commands, plan claims verified per item with hit counts and EXISTS/MISSING/WRONG-CONTENT/HARD labels.

### 1c. Structural lint (mechanical, supplements Stage 0)

Stage 0 covered the deterministic floor. Stage 1c covers plan-style hygiene the gate doesn't.

**Chunk discipline:**
- Every chunk has ≤ 5 files.
- Every chunk has a single concern (description fits one sentence without "and").
- Every chunk has a TDD section with **enumerated test cases** — behavior under test + assertion shape. Test file paths are NOT in the plan.
- File lists are definitive — no "or" / "depending on approach" ambiguity.

**Required sections present:**
- Implementation chunks listed
- TDD coverage per chunk
- Files-touched list per chunk
- Final verification (specific commands + expected outputs)
- Out-of-scope items in overview
- "Read first" / source-of-truth files per chunk

**Multi-chunk plans:**
- Parallel Execution Map present.
- Parallel groups: chunks depending only on the foundation are parallel, not falsely sequential.
- Hidden cross-chunk file dependencies (chunk N writes X, chunk M reads X → can't be parallel) → `[HARD: false parallelism]`.
- Declared chunk dependencies match actual file dependencies.

**Critical chunks have "If blocked" branches.**

**Forbidden patterns (regex-detectable; HARD for tracker fields, SOFT MEDIUM for stylistic):**
- Status / PR / Mode / Owner / Last-updated columns or fields → HARD
- Hedging future tense (`we will likely`, `this plan aims to`) → SOFT MEDIUM
- Meta-commentary (`this section…`, `below we'll cover…`) → SOFT MEDIUM
- "Open questions" section → SOFT MEDIUM
- Emojis, exclamation marks → SOFT LOW

### 1d. Stage 1 mechanical fixes

Apply unambiguous fixes immediately:
- Hallucinated path with obvious near-match (typo, casing) → replace with verified path.
- Wrong build command → replace with verified command.
- Forbidden style-class patterns (tense, banned phrases, emojis) → fix in place.
- Forbidden tracker columns → strip them.

Emit `Stage 1 fixes applied:` bullet list.

Findings that survive Stage 1 (HARDs that can't be auto-fixed) are passed to Stage 2 as `pre_resolved_hard_findings` so personas don't re-prosecute them.

### Stage 1 output (audit_report per plan)

Bulleted facts list (not verbose YAML). Include:
- plan_path, HEAD sha
- engineering_plan_trace (PASS / MISMATCH details, or N/A)
- repo_reality: paths/identifiers/CI/commands verified, line-content claims, hard findings
- structural_lint: chunk count, file counts per chunk, parallel map present, false parallelism, forbidden pattern hits, hard/soft findings
- stage_1_fixes_applied
- pre_resolved_hard_findings

---

## Stage 2 — Persona prosecution (parallel agents, fix-list output)

Read `personas/ai-development.md` and (if exists) `memory/plan-quality.md` once — referenced as paths in agent prompts; agents Read on demand.

Resolve personas (auto or explicit). Launch one Agent per (plan, persona) pair, **all in parallel in a single message**. N×M agents.

### Spawn agents

Use the template in `~/.claude/skills/_review-common/agent-prompt.md`. Substitute:

- `{persona_name}` — the persona being prosecuted as
- `{audit_report_bullets}` — Stage 1 audit (compact bullets)
- `{pre_resolved_hard_findings}` — anything Stage 1 already raised
- `{active_critical_pair_subset}` — `P-CLASS-SCOPE, P-FULL-FILE, P-CHUNK-TEST-PATHS, P-CHUNK-COMMANDS, P-CHUNK-SINGLE-CONCERN, P-CHUNK-READ-FIRST`
- `{target_locator}` — the plan path
- `{how_to_get_it}` — `Read <plan_path>`; agents Read source-of-truth files (CLAUDE.md, schema.prisma, brief.md, engineering-plan.md, persona files) on demand
- `{pr_description_or_brief_mapping}` — N/A (chunk plans don't have a PR description; if the plan is under `features/`, mention the parent feature's brief.md path)
- `{skill_specific_extensions}` — *Imagine implementing this plan from a cold start. What second-order issues surface during execution that the plan does not address? What scenario can you construct where executing the chunk verbatim produces an incorrect result? Is the TDD coverage actually sufficient to catch the failure modes the persona cares about, or only the golden path?*
- `{skill_specific_preamble}` — none
- `{skill_specific_resets_block}` — none

Plan content is small enough to pass inline (single chunk plan). The orchestrator does NOT inline source-of-truth file contents — agents Read on demand.

---

## Stage 3 — Orchestrator decision

Stage 3 runs in the main thread, per plan.

### 3a. Apply Stage 1 mechanical fixes

Already done at end of Stage 1. Confirm the file matches the post-fix state.

### 3b. Filter Stage 2 fix lists against critical-pair policies

For each finding from each persona on this plan:
- Contradicts an active critical-pair policy → retract. Note in verdict.
- Duplicates a Stage 1 hard finding already mechanically fixed → retract.
- Otherwise → keep.

### 3c. Detect cross-persona disagreement

For each plan span (chunk / section / line range), collect surviving findings.
- Two personas propose contradictory fixes for the same span → label `STABLE_DISAGREEMENT`. Do not auto-apply.

### 3d. Consolidate non-conflicting fixes

Deduplicate (same finding flagged by multiple → merge, attribute to all). Group by section. Apply in a single editing pass to the plan file, ordered by severity (CRITICAL → HIGH → MEDIUM → LOW). Within a severity, fixes are applied in document order.

**Convention extraction (de-duplicate before applying).** Before emitting per-bullet edits, scan the consolidated fix set for **structural patterns shared across ≥3 fix targets**. Common shapes: `spy-as-timing-primitive`, `spy-as-counter`, `deferred-promise mock`, `trap-row idiom`, `sequence pre-pin via setval`, `fake-timer wrap`, `BASE-range cleanup predicate`, `byte-exact regex pinning`, `namespace-import for live-binding`, `sanitization at interpolation site`. When ≥3 fix bullets describe the same structural pattern AND `§Conventions` does not already pin it, write the pattern once in `§Conventions` (or extend the existing entry) and replace the duplicated prose in each fix bullet with a one-line reference (e.g., "uses §Conventions Spy-as-timing-primitive carve-out"). The plan stays the same shape; the pattern's mechanics live in one canonical place.

Rationale: round-N personas naturally file each test-spec gap as an independent finding. Pinning the pattern inline in each bullet creates round-N+1 prosecution surface ("trap-row test #1 seed shape doesn't match trap-row test #2"). Pinning once in conventions with bullets referencing eliminates the cross-bullet drift class. Record `convention_extractions_applied` in the per-round metrics.

**Cross-file fix scope.** A persona's filed fix may have substance that binds beyond the chunk plan under review. Detect by scanning the fix prose for cross-file scope markers — literal mentions of `decisions.md`, `engineering-plan.md`, `brief.md`, OR phrases that signal forward-binding / durable-arbitration scope: `binds for all`, `cross-cutting effect`, `forward-binding`, `for all future readers`, `future-chunk planners`, `negative decision`, `arbitrate`, `bound across chunks`. When a fix carries any of these markers, the orchestrator's edit pass MUST include the corresponding cross-file edit in the same Stage 3d application — not file it as a TODO note in the chunk plan.

**Authority order when artifacts disagree** (highest to lowest):

1. `features/<feature>/decisions.md` — durable arbitration record; append-only history of bound questions.
2. `features/<feature>/engineering-plan.md` — chunk-DAG layer; bound invariants and decisions-closure table.
3. The chunk plan under review.

When a finding's substance reveals contradiction across these files, the chunk plan aligns to the upstream sources (decisions.md > engineering-plan.md), not vice versa. Contradiction *between* decisions.md and engineering-plan.md escalates as `OPEN_QUESTION` (user arbitrates which is canonical) — the orchestrator does not auto-resolve cross-upstream-artifact disagreement.

When writing a cross-file edit:

- **decisions.md** — append a dated entry (today's date, current `round_number`) under that date's heading with the bound decision in one sentence and the rationale in 1–3 sentences; reference the chunk slug; cross-link from the chunk plan's relevant section.
- **engineering-plan.md** — edit `§Invariants` / `§Decisions-closure` row matching the affected concept; add a new row if absent.
- **chunk plan** — as normal.

Record each cross-file edit in `cross_file_edits[]` for the per-round metrics so the verdict surfaces the full atomic-write surface. Working tree is left dirty across the trio; the user decides commit boundaries.

**Forbidden fixes:**
- Weakening the plan (removing tests, lowering coverage, dropping invariants) → escalate as `OPEN_QUESTION`.
- Changing the plan's goal to sidestep a hard problem → escalate as `OPEN_QUESTION`.
- "Leaving details for implementation" — if it's unclear now, the implementer will hallucinate.
- Filing a cross-file scope marker as a TODO note in the chunk plan instead of writing the cross-file edit in the same round → write the cross-file edit.
- Pinning a structural pattern inline in ≥3 bullets when `§Conventions` could carry it once → run convention extraction first.

### Post-fix premise verification

Runs in the **main thread (LLM judgment), NOT as a sub-agent spawn**. The orchestrator owns the edits and must own the verification.

**Why this exists.** Stage 3 fixes can rewrite chunk-plan prose — TDD assertion descriptions, files-touched annotations, implementation-sketch claims about existing code patterns, verification-step expected-output strings. A mechanical rewrite can flip a claim like "the existing handler at `<path>:<line>` returns Result" into something verifiably wrong.

**Procedure:**

1. **Identify added or rewritten prose** in the post-fix chunk plan. Compare to the pre-fix version held in memory (the orchestrator just made the edits; it knows what it wrote).

2. **Identify verifiable claims** using LLM judgment:
   - **Behavior**: "function X returns Y when Z"
   - **Scope**: "this chunk only modifies files matching `<glob>`"
   - **Constraint**: "the type signature is `(a: A) => B`"
   - **Cross-reference**: "matches the existing pattern in `<file>`"

   Skip stylistic edits, open commentary, aspirational language, and section headers.

3. **Verify each claim** with the cheapest falsifying check: `Read` the cited file, `rg` for the identifier, etc.

4. **File falsified claims** as `FIX_INTRODUCED_PREMISE_INVERSION` blockers; leave the working tree dirty for the user to inspect.

Verification stats are recorded for the verdict template: `verification_attempts={n}; verified={n}; falsified={n}; new_blockers_filed={n}`.

### Same-round focused re-prosecution on rewritten prose

Runs once per plan, after Post-fix premise verification, before Stage 3e classification. **Bounded: exactly one re-pass; never an inner loop.**

**Why this exists.** Stage 3d edits write new prose — test-bullet refinements, convention entries, cross-file edits, premise-corrected claims. Without a same-round re-pass the current round persists, exits, and the next round's persona prosecution finds defects in the freshly-written prose. The empirically-observed pattern: round 7 added the `__concurrentGuardForTesting` accessor → round 8 found no contract test for it; round 7 introduced the trap-row idiom → round 8 found the seed shape underspecified; round 7 added the diagnostic sanitizer convention → round 8 found zero tests covering its named interpolation sites. These are real defects in fix prose. Catching them inside the same round is cheaper than waiting for round N+1 to re-prosecute the whole plan.

**Procedure:**

1. **Identify diff hunks** the orchestrator wrote in 3a, 3d, and Post-fix premise verification's claim-correction edits. The orchestrator made the edits and knows what it wrote — capture the (file, before-text, after-text) tuples. Cross-file edits to `decisions.md` / `engineering-plan.md` are included.

2. **Spawn one focused agent per (plan, persona)** pair that reviewed the plan in Stage 2. Use the `_review-common/agent-prompt.md` template with the **same substitutions Stage 2 used**, except override these two:
   - `{target_locator}` — the plan path, plus the diff-hunk list inline as before/after blocks (and any cross-file diff hunks to `decisions.md` / `engineering-plan.md`).
   - `{skill_specific_extensions}` — *Review ONLY the diff hunks listed below. The whole-plan version was prosecuted in Stage 2; this pass exists to catch defects introduced by the round-N orchestrator edits themselves. File findings on the rewritten prose's: (a) internal consistency, (b) test-coverage gap for newly-added conventions or contracts, (c) cross-reference correctness with decisions.md or engineering-plan.md, (d) any verifiable claim that is unverified, (e) discipline gaps where a convention was added but no test/checklist row enforces it. Filter your findings to severity HIGH and MEDIUM only — LOW-severity polish on freshly-written prose is round-N+1 territory and does not warrant a same-round re-pass finding.*

   All other substitutions (`{persona_name}`, `{audit_report_bullets}`, `{pre_resolved_hard_findings}`, `{active_critical_pair_subset}`, `{how_to_get_it}`, `{pr_description_or_brief_mapping}`, `{skill_specific_preamble}`, `{skill_specific_resets_block}`) carry over verbatim from Stage 2. Omitting them produces a malformed prompt that under-constrains the persona.

3. **Filter re-pass fix lists through Stage 3b** (critical-pair policy retraction; same procedure as the original Stage 2 → 3b filtering). Findings contradicting an active critical-pair policy are retracted, not applied.

4. **Detect cross-persona disagreement on diff-hunk spans** (same procedure as Stage 3c). If two re-pass personas file contradictory fixes on the same diff hunk, label `STABLE_DISAGREEMENT` and persist to blockers — do NOT auto-apply either.

5. **Apply surviving re-pass findings** as additional Stage 3d edits, ordered by severity. The Convention-extraction, Cross-file-scope, and Forbidden-fixes rules apply identically.

6. **Re-run Post-fix premise verification** on the re-pass edits (same procedure as the original Post-fix premise verification, scoped to the re-pass diff hunks only).

7. **No further re-pass.** Findings that survive the re-pass become Stage 3e blockers as normal. The bounded one-pass cap is the natural backstop — if the re-pass produces yet more defects after fixes, those land in the verdict and the user re-invokes.

**Cost.** The re-pass agents read only the diff hunks (typically 2–10% of the plan's size) plus the source-of-truth files they re-verify against. Empirically ≤25% of a full Stage 2 round-cost.

**Skip conditions.** The re-pass is skipped (recorded as `re_pass_ran=false`) when ALL of:
- Stage 3d applied zero fixes (no rewritten prose to re-prosecute).
- Post-fix premise verification filed zero falsified claims (no claim-correction edits).
- Cross-file edits applied = 0.

In those cases, the round produced no new prose surface, so the re-pass would find nothing.

Re-pass stats are recorded for the verdict template and persisted to `per_round_metrics`: `re_pass_ran=<bool>; re_pass_diff_hunks_reviewed={n}; re_pass_additional_fixes_applied={n}; re_pass_findings_persisted_to_blockers={n}`.

### 3e. Classify remaining unresolved findings

See `~/.claude/skills/_review-common/blocker-classes.md`. Active for chunk plan review: `STRUCTURAL_LINT_FAILED`, `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `FIX_INTRODUCED_PREMISE_INVERSION`, `POLISH_PLATEAU`, `REPO_STATE_DRIFT`.

**Carry-forward consultation (decisions-log-first, then ephemeral cache).**

Before emitting any blocker, run two consultations in priority order. The decisions log is the project's durable arbitration record — what the user codified as "this question is bound; don't re-litigate." The ephemeral state-file cache is local to `~/.claude/cache/review-state/` and decays at `carry_forward_until_round`. Reading the durable record first means a finding contradicting `decisions.md 2026-05-06 "bundle ceiling extended from 5 to 6 implementation files"` is dropped automatically rather than re-litigated as an OPEN_QUESTION every round.

**Priority 1 — `decisions.md` lookup** (durable arbitration; persists across rounds).

For chunk plans under `features/<feature>/implementation/`, `Read` `features/<feature>/decisions.md`. Search for entries whose `path_or_section` (file paths, identifier names, schema field names, decision titles) overlap the finding's surface. Match heuristic:

- **Strong match** — decisions.md entry quotes the same identifier or path the finding cites verbatim (e.g., finding cites `__concurrentGuardForTesting` and the entry titled "Co-located test-only accessor pattern" names the same identifier).
- **Topical match** — decisions.md entry's title or rationale names the same concept (writer-fence-quiescence, banner scrubbing, accessor pattern, sequence pre-pin, trap-row idiom, etc.).

If a strong or topical match exists AND the entry is dated AND the entry is bound (no `pending` / `undecided` / `open` qualifier in the entry body):

- **Finding contradicts the bound decision** → drop the finding (auto-resolution); record in verdict as `[CARRY-FORWARD via decisions.md] {finding} — bound by decisions.md entry "{quoted entry title and date}": "{verbatim one-line summary}"`. Increment `decisions_md_consultation.findings_dropped`.
- **Finding is consistent with the bound decision but flags a new dimension** → keep the finding but surface the bound decision in the blocker line so the user sees the prior arbitration when reading the verdict.

For freestanding plans (`.scratch/<plan>.md` with no engineering-plan parent) or any plan path without a sibling `decisions.md`, skip Priority 1 and go directly to Priority 2.

**Priority 2 — `recently_resolved_blockers` ephemeral cache** (state-file). Apply only to findings that survived Priority 1 (no decisions.md match).

Check entries where `carry_forward_until_round >= round_number` AND `path_or_section` overlaps the finding's surface. If a match exists, the finding is being re-prosecuted on a span the user already adjudicated within the recent rounds:

- **Downgrade to `OPEN_QUESTION`** with the prior `user_decision` surfaced verbatim.
- The persona's claim survives only if `current_reclassification_justification` was filed in `prior_blockers` (i.e., the persona explicitly named a repo-state change that warrants re-prosecution).
- Without justification, the verdict reads: `[OPEN_QUESTION] {finding} — Prior round {N} resolved this with: "{user_decision}". No new repo-state justification filed; user arbitrates.`

Record both consultations in `decisions_md_consultation` and the existing carry-forward stats for the verdict template.

### 3f. Render verdict (per plan)

Verdict gate logic in `_review-common/blocker-classes.md`. Compute Tier-1 weight (CRITICAL=8, HIGH=4, MEDIUM=2, LOW=1) and Tier-2 weight after fix application.

### 3g. Output (per plan)

```
## Plan Review v2 Complete: {plan_path}

**Round:** {round_number} {| `(round 1 — no prior state)` | `(loaded from cache: {round_number-1} → {round_number})` | `(state file missing; cold start)`}
**State source:** {`Loaded from ~/.claude/cache/review-state/<plan-slug>.json` | `Round 1 (no prior state)`}
**Personas:** {names}
**Stage 1 audit:** repo_reality PASS / N hard findings; structural_lint PASS / N findings
**Stage 1 mechanical fixes applied:** {count}
**Stage 2 personas:** {N} agents in parallel
**Stage 3 fixes applied:** {count} (HARD: {n}, SOFT: {n})
**Stage 3 retractions (critical-pair policy):** {count}
**Convention extractions:** {n} pattern(s) consolidated into §Conventions; {m} test-bullet duplicate prose replaced with references
**Cross-file edits applied:** {count}
  - {file path}: {one-line summary}
  - {file path}: {one-line summary}
  ... (one bullet per cross-file edit; omit the sub-bullet list entirely when count = 0)
**Carry-forward consultation:**
  - decisions.md matches: {n}; findings dropped via decisions: {n}
  - state-file matches: {n}; downgraded to OPEN_QUESTION: {n}; survived with current_reclassification_justification: {n}
**Post-fix premise verification:** verification_attempts={n}; verified={n}; falsified={n}; new_blockers_filed={n}
**Same-round re-prosecution:** ran={bool}; diff_hunks_reviewed={n}; additional_fixes_applied={n}; findings_persisted_to_blockers={n}
**Final Tier 1 weight:** {n}
**Final Tier 2 weight:** {n} (floor: 4)

### Changes Made
- {bullets of significant edits, including any cross-file edits to decisions.md / engineering-plan.md / brief.md and any §Conventions extractions}

### Retractions
- {finding} → retracted because {critical-pair policy / pre-resolved by Stage 1 / superseded}

### Blockers (if any)
- [STABLE_DISAGREEMENT] {finding} — Persona A: {fix A}; Persona B: {fix B}. Pick one.
- [OPEN_QUESTION] {finding} — {question}
- [FIX_INTRODUCED_PREMISE_INVERSION] {chunk/section}: orchestrator-applied fix asserts "{verbatim claim}"; verification: {what was run}; actual: "{contradicting evidence}". Working tree dirty.
- [POLISH_PLATEAU] {finding} — non-blocking; ship is acceptable.
- [REPO_STATE_DRIFT] HEAD changed from {sha} to {sha}. Re-run.

### Plan Status: APPROVED / NEEDS USER INPUT
```

If `NEEDS USER INPUT`: user resolves blockers and re-invokes (next run is fresh).

---

## Multi-plan combined summary

```
# Plan Review v2 Summary

| Plan | Persona | Stage 1 | Stage 2 raised | Stage 3 applied | Retracted | Tier 1 | Tier 2 | Status |
|------|---------|---------|----------------|-----------------|-----------|--------|--------|--------|
| WP-F9 | frontend | PASS | 2 | 2 | 0 | 0 | 0 | APPROVED |
| WP-F9 | backend  | PASS | 1 | 1 | 0 | 0 | 0 | APPROVED |
| **WP-F9** | **overall** | | **3** | **3** | **0** | **0** | **0** | **APPROVED** |
| WP-F10 | frontend | PASS | 4 | 2 | 1 | 0 | 2 | APPROVED |
| WP-F10 | backend  | PASS | 3 | 1 | 0 | 0 | 4 | NEEDS USER INPUT (1 STABLE_DISAGREEMENT) |
| **WP-F10** | **overall** | | **7** | **3** | **1** | **0** | **6** | **NEEDS USER INPUT** |

## Blockers (deduplicated across personas)
- {plan}: [STABLE_DISAGREEMENT] {issue} — Options: {A} (frontend) vs {B} (backend)

## Key Changes Across Plans
- {plan}: {summary}

## Retractions (critical-pair policy)
- {plan} / {persona}: {dropped finding, policy that retracted it}

## Clean Passes
- {plans APPROVED by all personas}
```

Expand each (plan, persona) agent's full final report below the table, grouped by plan, ordered NEEDS USER INPUT first.

---

## Hard rules

- **Status-frontmatter check is mandatory and runs first.** A chunk plan with frontmatter `Status: needs-user-input` is mid-cycle authoring state (the partial draft was written by `/plan-author`'s NEEDS_USER_INPUT path with a `## Pending blockers` section appended); skill refuses to run against it and points the user back at `/plan-author`. The check is deterministic and runs before Stage 0.
- **Stage 1 is mandatory.** Stage 2 personas reading the plan without the audit report will re-prosecute facts.
- **Round Memory Pass is mandatory per plan.** Skipping it disables carry-forward consultation and lets the same OPEN_QUESTION re-litigate across rounds. State file lives at `~/.claude/cache/review-state/<plan-slug>.json` (NOT in the project repo).
- **Orchestrator verifies its own edits.** Post-fix premise verification runs after Consolidate Non-Conflicting Fixes, before Classify Remaining Findings. Skipping it allows the orchestrator's own prose-rewrite fixes to introduce premise inversions that cascade into the next round.
- **Carry-forward consultation is mandatory and decisions-log-first.** Before emitting any blocker, consult `decisions.md` (durable arbitration) FIRST, then `recently_resolved_blockers` (ephemeral cache). Findings contradicting a bound `decisions.md` entry are dropped (not OPEN_QUESTION). Findings re-prosecuting a span in `recently_resolved_blockers` without `current_reclassification_justification` are downgraded to `OPEN_QUESTION`.
- **Cross-file fix scope is mandatory when triggered.** A persona's fix prose that mentions `decisions.md` / `engineering-plan.md` / `brief.md` or carries forward-binding markers (`binds for all`, `cross-cutting effect`, `for all future readers`, `negative decision`) MUST receive a corresponding cross-file edit in the same Stage 3d application. Filing it as a TODO note in the chunk plan instead is a forbidden fix.
- **Convention extraction precedes per-bullet pinning.** Before applying ≥3 fix bullets that share a structural pattern (spy-as-timing-primitive, trap-row idiom, sequence pre-pin, fake-timer wrap, etc.), extract the pattern to `§Conventions` once and reference from each bullet. Inline duplication across bullets is a forbidden fix.
- **Same-round focused re-prosecution is mandatory** when ANY of: Stage 3d chunk-plan fixes > 0, cross-file edits > 0, or Post-fix premise verification falsified-claim count > 0. Bounded: exactly one re-pass; never an inner loop. Skipped only when ALL three are zero (no rewritten prose to re-prosecute).
- **Stage 2 agents return fix lists; never edit files.** All edits applied by orchestrator in Stage 3.
- **Stage 3 applies critical-pair policies before applying fixes.** Findings contradicting a policy are retracted, not relitigated.
- **Never** mark APPROVED while any blocker class is non-empty.
- **Never** weaken the plan to resolve a finding. That's `OPEN_QUESTION`.
- **Always** quote verbatim from plan, repo, or audit_report when justifying a finding.
- **Always** label remaining findings with their blocker class.
- **No multi-round inner loop.** The same-round focused re-prosecution is exactly one pass over diff hunks; survivors land in the verdict and the user re-invokes.

## Edge cases

- **Plan file not found:** report, continue on remaining plans.
- **Persona file not found:** auto-assignment falls back to next best match; explicit personas stop and ask.
- **Single plan + multiple personas:** launch one Agent per persona in parallel; orchestrator applies all fixes (no edit conflicts because fixes go through one writer).
- **Large N×M (e.g., 7 × 3 = 21 agents):** expected. Launch all in parallel.
- **Plan references code that doesn't exist:** Stage 1 catches; either mechanical fix (typo correction) or `[HARD: hallucination]` blocker.
- **Plan contradicts project rules** (`CLAUDE.md`, schema, persona non-negotiables): Stage 2 finding, severity CRITICAL, fixed in Stage 3 or escalated as `OPEN_QUESTION`.
- **Very large plans (>500 lines):** review fully. Do not truncate.
- **State file missing for a plan that has clearly been reviewed before** (e.g., user wiped `~/.claude/cache/`): cold start at round 1. The ephemeral `recently_resolved_blockers` cache is lost, but for chunk plans under `features/<feature>/`, the durable `decisions.md` arbitration record is still consulted via Stage 3e Priority 1 carry-forward, so user-bound decisions survive the cache wipe. Verdict's State source records `cold start (decisions.md still consulted)` for `features/`-rooted plans, or just `cold start` for freestanding `.scratch/` plans. Warn the user that recently-resolved-blocker context is lost; previously-bound decisions.md entries continue to gate findings.
- **Plan path changed between invocations** (e.g., chunk renamed, plan moved from `.scratch/` to `features/`): slug derivation will produce a different state file path; this is a cold start under the new slug. User can manually copy the old state file if continuity is desired.
- **HEAD changes mid-review:** emit `REPO_STATE_DRIFT`. User re-runs.
