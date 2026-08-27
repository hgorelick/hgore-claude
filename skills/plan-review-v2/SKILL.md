---
name: plan-review-v2
description: Adversarial single-pass review of one or more chunk implementation plans, converging across re-invocations. Applies fixes directly and returns APPROVED or NEEDS USER INPUT with labeled blockers. Use after `/plan-author` lands a clean draft, before `/execute-plan`. Sister to `/engineering-plan-review-v2` (engineering-plan layer) and `/brief-review-v2` (brief layer).
user-invocable: true
---

# Plan Review v2 — Staged Single-Pass

Plans are cheap to write and expensive to execute. A hallucinated plan burns days chasing files that don't exist. This skill prosecutes chunk implementation plans through a Structural Lint gate plus three stages, with bounded same-round verification on orchestrator-rewritten prose. Never a multi-round inner loop — survivors of the bounded same-round re-pass land in the verdict and the user re-invokes.

This is the chunk-plan layer. Sister skill `/engineering-plan-review-v2` reviews engineering plans (`features/<feature>/engineering-plan.md`). If the user asks for review of an engineering plan, redirect.

## Shared scaffolding

- `~/.claude/skills/_review-common/principles.md` — stance, banned rationalizations, severity/tier, plan style rules
- `~/.claude/skills/_review-common/round-memory.md` — state file, load, capture priority, persist
- `~/.claude/skills/_review-common/orchestrator.md` — the shared Stage 3 spine
- `~/.claude/skills/_review-common/agent-prompt.md` — persona-agent prompt template
- `~/.claude/skills/_review-common/critical-pairs.md` — active subset for chunk plan review: `P-CLASS-SCOPE, P-FULL-FILE, P-CHUNK-TEST-PATHS, P-CHUNK-COMMANDS, P-CHUNK-SINGLE-CONCERN, P-CHUNK-READ-FIRST`
- `~/.claude/skills/_review-common/class-sweep.md` — seeded sibling-enumeration stage (expands a found class)
- `~/.claude/skills/_review-common/structural-sweep.md` — unseeded matrix-completion stage (discovers unfiled classes)
- `~/.claude/skills/_review-common/repo-reality-sweep.md` — codebase-derived stage (checks the plan's premises about code by reading the code)
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
/plan-review-v2 features/user-profile-sync/implementation/cascade-rewrite.md --personas backend architecture

# Multiple plans with explicit personas — N×M parallel agents
/plan-review-v2 .scratch/F12.md .scratch/F13.md .scratch/F14.md --personas frontend backend

# Chunk slug shorthand — resolves to <plan-root>/implementation/<slug>.md
/plan-review-v2 cascade-rewrite
```

## Argument parsing

Split `$ARGUMENTS` on whitespace. Classify each token:

- `--personas` → all subsequent non-path tokens are persona names.
- Token contains `/` or ends with `.md` → plan path.
- Otherwise (kebab-case, no separator, no `.md`) → chunk-slug shorthand. Resolve by globbing `features/*/implementation/{<slug>,[0-9]*-<slug>}.md` AND `features/*/plans/*/implementation/{<slug>,[0-9]*-<slug>}.md` (the `NN-` creation-index prefix `/plan-author` assigns — see its Creation index section); if exactly one combined match exists, use it; ambiguous → ask which feature, naming the track where the feature is tracked.

**Plan-root resolution.** Read `~/.claude/skills/_plan-common/layout.md`. A feature is **flat** (`implementation/` directly under `features/<feature>/`) or **tracked** (`features/<feature>/plans/<track>/implementation/`). **`<plan-root>`** below means whichever directory holds the engineering plan that indexes the chunk under review; `brief.md` and `decisions.md` always live at the feature root and are shared across tracks.

**Path resolution:**
- Starts with `/` or `./` → use as-is
- Starts with `.scratch/`, `fixes/`, `context/`, or `features/` → relative to repo root
- Ends with `.md`, no separator → prepend `.scratch/`

**Backward compatibility:** Exactly one plan + one or more non-path tokens without `--personas` → treat the non-paths as personas.

No arguments → search `.scratch/` for `*.md` files that look like plans (contain `## Implementation`, `## Files to`, or `**Effort:**`), list them, ask which to review.

## Persona resolution

### Explicit personas
Load each from `personas/{name}.md`, resolved relative to the **project root (cwd — the repository being reviewed)**, NOT the skill directory. The persona files are project-specific and live at the repo root (`./personas/*.md`); do not look under `~/.claude/skills/plan-review-v2/`. **Every plan is reviewed by every listed persona.** N plans × M personas = N×M parallel agents. If a listed persona file is genuinely absent from the project root → stop and report; do NOT silently fall back to uncalibrated inline archetype lenses (that produces an under-calibrated verdict indistinguishable from a real one).

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
     ↓ produces audit_report per plan; engineering-plan-trace also runs the
     ↓ basis-fidelity check → SURFACE_PARITY_GAP when a chunk drifts below its
     ↓ EP row's authoritative signal to a proxy (the one parity axis that reaches the chunk layer)
  Stage 1.5: Brief-conformance audit    (one subagent per plan; HARD findings exempt
     ↓                                   from carry-forward; skipped for .scratch/ plans)
     ↓ spawns Brief-conformance Prosecutor (_review-common/brief-conformance-prosecutor.md)
     ↓ files BRIEF_NONGOAL_TRESPASS + BRIEF_GOAL_UNDELIVERED as pre_resolved_hard_findings
  Stage 2: Persona prosecution          (LLM judgment, M parallel agents per plan)
     ↓ produces fix_lists per (plan, persona)
  Stage 3: Orchestrator decision        (deterministic + judgment)
     ↓ 3b retracts against round-memory tags + critical-pair policies, THEN
     ↓ 3b.4 Structural Sweep             (UNSEEDED: Universe L liveness + Universe A observability;
     ↓                                    runs even on a zero-finding round)
     ↓ 3b.5 Class Sweep                  (one agent per distinct recurring category)
     ↓   walks the peer-set (every chunk / criterion / test bullet) for siblings of
     ↓   each surviving seed class; promotes them to same-round findings before
     ↓   3c disagreement detection and 3d consolidation
     ↓   (_review-common/class-sweep.md)
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
  `/plan-author <feature>/<chunk-slug>` (warm mode is automatic). The author skill removes the `Status:`
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

## Round Memory Pass (per plan, no LLM judgment)

Mechanism, schema, load, capture priority, and persist rules: `~/.claude/skills/_review-common/round-memory.md`. Read it. This section names only what the chunk-plan layer adds.

- **Slug** — `<feature>__<chunk-slug>` (or `<feature>__<track>__<chunk-slug>`), `scratch__<name>` for `.scratch/`, `fixes__<name>` for `fixes/`. Strip the `NN-` creation-index prefix before forming the slug so it matches `/plan-author`'s sidecar key. A legacy unprefixed `<chunk-slug>.md` resolves to the same slug.
- **Extra metric** — `per_round_metrics.round_<N>.convention_extractions_applied`, the count of recurring patterns pinned into `§Conventions` this round. It should be nonzero early and fall to zero as the plan stabilizes.
- **Multi-plan invocation** — each plan carries its own state file, loaded and persisted independently. Nothing is shared across plans in one invocation except the Class Sweep's peer-set.

A third thrash pattern — **fix-cascade prosecution**, where this round's orchestrator fixes write fresh prose that next round's personas correctly file as new defects — is closed by Stage 3's same-round re-prosecution and decisions-log-first carry-forward, not by this pass. This pass loads state; Stage 3 enforces the discipline.

### Remediation-completeness pass (round_number > 1, MANDATORY)

Stage 3's same-round re-prosecution and its post-fix premise verification both scope to the **orchestrator's own** edits, inside the round that made them. Neither can see the remediation the *user* writes **between** rounds, which is the larger surface: a `NEEDS USER INPUT` verdict hands back N blockers, the user edits the chunk plan, and the next round meets that new text with ordinary prosecution latitude and nothing else. The recurring failure is not a bad fix — it is a fix that lands in the section that motivated the blocker and never reaches the sections coupled to it, so the blocker reads as closed while its consequences are unbuilt. `prior_blockers` and `recently_resolved_blockers` are consulted only to *retract* re-prosecution; nothing verifies *completion*. This pass is that check, and it runs before Stage 2 so its findings enter as `pre_resolved_hard_findings`.

For **every** entry in the prior round's `prior_blockers`, answer three questions and record the answer. Do not sample.

1. **Closed?** Locate the text that closes it and quote it. Nothing addressing the blocker means it is still open — carry it forward at its original class and severity rather than letting the round-counter launder it into a fresh finding.

2. **Swept?** A chunk-plan remediation names a file, a symbol, a test, an acceptance criterion, or a convention. Enumerate the sites it must reach and check each: the **Factoring Contract** (a remediation that adds a write to a file demands an `Owns (writes)` entry; one that drops a file demands its removal), §Files-to-touch, §Acceptance criteria, §Conventions, §Out-of-scope, the **parent engineering plan's chunk-index row** (a remediation that changes what the chunk delivers desynchronizes the row it traces to), and any sibling chunk plan sharing the contract. A remediation present in its motivating section and absent from its coupled sites files `REMEDIATION_INCOMPLETE` (HARD, severity inherited from the original blocker). The Factoring Contract is the highest-yield site here — it is the one section `/plan-lint` reads mechanically, so a remediation that skips it is invisible to the deterministic floor as well as to the personas.

3. **Recorded?** An arbitration the user made to close a blocker belongs in `decisions.md`. Search for a bound Active-section entry covering it. A plan span that *cites* a `decisions.md` entry which does not exist is a `DECISIONS_PROVENANCE_GAP` (HARD, HIGH) — resolve every citation this round's modified sections introduced, by heading, not by date alone. An unrecorded arbitration cannot be retracted by decisions-log-first carry-forward next round, so the same ground is re-prosecuted indefinitely.

Record as `remediation_completeness` in the state file: `{blocker, closed: yes|no, closing_quote, coupled_sites_checked: [...], sites_missed: [...], decisions_entry: "<heading>" | "none — <class>"}`. An entry with an empty `coupled_sites_checked` answered only the first question; re-run it.

---

## Stage 1 — Ground truth pass (MANDATORY, NO LLM JUDGMENT)

Produces an `audit_report` per plan. Stage 2 personas MUST NOT re-prosecute facts already verified here.

### 1a. Engineering-plan trace (chunk plans only)

If the plan resolves to a chunk under a feature's `implementation/` (either layout):
- Open `<plan-root>/engineering-plan.md`.
- Find the row in the chunk index whose slug matches.
- Verify: chunk name in plan matches engineering-plan row; declared `Code deps` match; chunk does not exceed scope implied by the engineering-plan's chunk description.
- **Basis fidelity (the one scope-parity axis that reaches the chunk layer).** The full three-axis scope-fidelity check runs at the engineering-plan layer, because two of its axes — subset-of-domain and premature-action/pipeline-timing — are chunk-DAG-coverage properties a single-chunk review structurally cannot see (see `_review-common/brief-conformance-prosecutor.md` § Scope-fidelity Adversary). One axis DOES reach here: **weaker-substitute-basis**. When the chunk's §Goal — or the brief Goal / EP row it delivers — names a distinguished *authoritative signal* the outcome must be computed on ("the classifier verdict", "the restored author links", "judged on the work itself"), verify the chunk's implementation actually computes the outcome on that signal, not a degraded proxy (a title-pattern heuristic standing in for a classifier verdict; a snapshot count standing in for restored links). This fires ONLY on *drift below the row*: if the EP chunk-index row, a bound `decisions.md` entry (an Active bound entry — a `superseded`/`obsolete` one in the `## Archived (superseded / obsolete)` tail does not confer this; per `~/.claude/skills/_review-common/principles.md` § What counts as a bound entry), or the chunk's own §Out-of-scope already committed the proxy and framed it as launch-acceptable, that substitution is the engineering-plan layer's call — already made — and is NOT a finding here. A chunk that silently resolves an authoritative-but-underspecified EP row *toward* the weaker proxy IS a finding: file `SURFACE_PARITY_GAP` (basis axis), applying the LEGITIMATE-vs-flag test from the adversary prompt (a stated, sound, launch-acceptable reason is not a gap; an unacknowledged downgrade is). This is the chunk-layer backstop for an engineering-plan-layer miss — a narrow deterministic assertion on the trace, not a re-run of the full parity adversary.

For freestanding plans (`.scratch/<plan>.md` with no engineering-plan parent), skip and note `engineering_plan_trace: N/A` (no brief/EP to measure basis fidelity against).

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

### 1c.1 Prose-Density gate (mechanical, mirrors `/plan-author`'s gate)

The author skill runs a Prose-Density gate after Self-prosecution that catches per-bullet defensive accretion — the failure mode where persona fixes grow existing bullets into multi-paragraph defensive prose instead of splitting them. The reviewer mirrors the gate to catch hand-edited plans that bypassed the author skill and to verify the author's gate fired correctly on the current on-disk shape.

Compute three sub-metrics over the chunk plan as it sits on disk at review time (same algorithm as the author skill — see `plan-author/SKILL.md` § Prose-Density gate for definitions):

- `bytes_per_line_avg` — total bytes in the three canonical prescriptive sections divided by line count across those three sections. Identify sections by name regardless of heading level: `Conventions / patterns to follow:` bold-label (the template emits this as a bolded sub-label under `## Context pack`), `Tests to add` heading, and `Acceptance criteria` heading. Exclude code-fence blocks and markdown table rows.
- `bullet_word_count_max` — maximum word count across all top-level bullets (a `- ` or `* ` line plus its continuation lines until the next top-level bullet or section heading).
- `parenthetical_nesting_depth_max` — maximum depth of nested parentheses / square brackets / curly braces used parenthetically in any single sentence (Markdown link syntax `[text](url)` is depth 1 by definition).

File `PROSE_DENSITY_EXCESS` as a HARD blocker when ANY of: `bytes_per_line_avg >= 200`, `bullet_word_count_max >= 400`, `parenthetical_nesting_depth_max >= 3`.

**Author state cross-check.** The reviewer ALWAYS recomputes the three sub-metrics on the on-disk plan — the author state is consulted only for drift detection, not as a substitute for the recomputation. Read `~/.claude/cache/author-state/<feature>__<chunk-slug>.json`. File a separate `AUTHOR_GATE_DRIFT` finding (alongside any `PROSE_DENSITY_EXCESS` the recomputation surfaces) when ANY of: (a) `prose_density` is absent (the author skill was bypassed by hand-edit or pre-dates the gate); (b) `prose_density.verdict == "skipped"` with a `skipped_reason` other than `"--draft"`, OR with no `skipped_reason` field (legacy author runs that skipped on the dropped ≥1-fix-applied condition — the gate fired with stale semantics and its verdict is meaningless); (c) the author state recorded `verdict: passed` but the reviewer's recomputation says `excess`; (d) the author state's recorded sub-metrics disagree with the reviewer's recomputation by more than a small tolerance (off-by-one on a word count is acceptable; a ~2x discrepancy means the author measured a different artifact than the reviewer sees on disk). The PROSE_DENSITY_EXCESS firing is independent of AUTHOR_GATE_DRIFT — the reviewer's recomputation is the source of truth for the blocker; the author state drives the cross-check finding only.

**Carry-forward exemption.** `PROSE_DENSITY_EXCESS` is NOT subject to decisions-log-first carry-forward consultation. Prose density is a structural property of the per-bullet shape, not an arbitration question; a `decisions.md` row binding *what* the chunk plans cannot, by itself, bind *how densely the prescription reads*. Only a `decisions.md` row whose Decision column substring-matches the chunk slug or chunk-index row description AND whose Resolution column explicitly contains a density-acknowledgement keyword (`prose density acknowledged`, `byte-format prescription density accepted`, `procedural verification depth required`, `regex specification accepted`) retracts the blocker. Bare keyword matches against the chunk's content do NOT retract.

The blocker's actionable resolutions match the author skill's: (a) split each overgrown bullet into peer bullets at the same indentation level; (b) promote nested parentheticals to peer bullets (three-deep nesting almost always re-flows as three siblings); (c) cite a `decisions.md` row arbitrating density per the language above.

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

## Stage 1.5 — Brief-conformance audit (chunk-plan layer; HARD findings exempt from carry-forward)

Chunk-plan-layer equivalent of `/engineering-plan-review-v2`'s Stage 1.5. Catches the case where a chunk plan implements behavior the brief excludes, even when the engineering plan or decisions.md "allows" the implementation. Per `_review-common/principles.md` § Cross-artifact authority order, brief Non-goals are Class A and the chunk plan loses to `brief.md` regardless of what's bound downstream.

### Scope guard

- Chunk plan under a feature's `implementation/` (either layout): run the audit.
- Chunk plan under `.scratch/` or `fixes/`: skip Stage 1.5 (no parent feature; no brief to conform to).
- Parent feature's `brief.md` missing: file `MISSING_BRIEF` as a HARD finding and skip the rest of Stage 1.5.

### Procedure

1. **Spawn the Brief-conformance Prosecutor.** Launch one `general-purpose` subagent (Agent tool, default subagent type) with the prompt from `~/.claude/skills/_review-common/brief-conformance-prosecutor.md`. Pass an explicit off-model `model` override per that file's § Model pin (default `sonnet`; `opus` if the session is already Sonnet) and record `conformance_gate_model` in the review state — never inherit the session model here. Substituting:
   - `{brief_path}` = `features/<feature>/brief.md` (the parent feature's brief)
   - `{plan_path}` = the chunk plan under review
   - `{decisions_path}` = `features/<feature>/decisions.md` (or "none")
   - `{sibling_plan_paths}` = every OTHER track's `engineering-plan.md` when the feature is tracked, else "none"
   - `{plan_layer}` = `chunk-plan`
   - `{additional_examples}` = chunk-plan-specific worked examples (the orchestrator appends two examples inline; see below) plus this chunk's accumulated calibration examples from the state file

2. **Pass chunk-plan-specific worked examples.** Because the chunk plan has different sections than the engineering plan (§Owns / §Acceptance / §Tests / §Out of scope / §Goal rather than Brief Mapping / Architecture / Chunk Index), the orchestrator appends two chunk-plan-specific examples to the `{additional_examples}` substitution:

   > *Positive — real trespass at chunk-plan layer:*
   >
   > > Parent feature's Non-goal: "No on-demand-path bidirectional rewrite. The hydration path users hit at runtime stays one-directional after this feature ships."
   > >
   > > Chunk plan §Owns: "Modifies `src/lib/userProfileSync.ts` to make `syncUserProfile` call `reconcileIdentities` in both directions (CRM→Directory and Directory→CRM) when invoked by the on-demand resolver."
   > >
   > > Reasoning: §Owns commits to the bidirectional rewrite on the on-demand path. The Non-goal forbids exactly this. The fact that the cascade primitive is "available" for bidirectional use does not exempt the chunk from the Non-goal — the chunk is committing to wire it into the on-demand path.
   >
   > *Negative — not a trespass at chunk-plan layer:*
   >
   > > Parent feature's Non-goal: "No filtering of which credits appear."
   > >
   > > Chunk plan §Tests to add: "Test that a Person with 50 credits returns all 50 credits in the API response, none truncated, none filtered by department or role."
   > >
   > > Reasoning: the test is *verifying* the Non-goal is honored. The chunk plan's §Tests asserting no filtering is the affirmative form of honoring "No filtering of which credits appear." This is the chunk-plan equivalent of the engineering plan's "Non-goals enforcement" section — honoring, not trespassing.

3. **§Goal verbatim-quote check.** The chunk plan's §Goal line MUST contain a verbatim quote from `brief.md` § Goals or § User-facing changes, OR explicitly cite the engineering plan's `### Supporting infrastructure` Brief-mapping entry. The prosecutor's `BRIEF_GOAL_UNDELIVERED` class covers the failure: a §Goal line that paraphrases or invents a Goal not in the brief, with no Supporting-infrastructure escape, is a trespass at the brief-grounding layer.

4. **Process findings.** Each finding becomes a `pre_resolved_hard_findings` entry visible to every persona's Stage 2 prompt. Personas may file ADDITIONAL findings but cannot retract Stage 1.5 ones. Build a `brief_conformance_report` of the same shape as the engineering-plan reviewer's:

   ```
   brief_conformance_report:
     prosecutor_verdict: "passed" | "findings_filed" | "skipped (.scratch/)"
     findings_total: <int>
     findings_high_hard: <int>
     findings_medium_hard: <int>
     bound_decisions_trespassing: <int>
     plan_sections_trespassing: <int>
     goals_undelivered: <int>
     rationale: "<prosecutor's rationale paragraph>"
   ```

   Pass into Stage 3 for verdict rendering.

### Cross-layer calibration

The author and reviewer at the chunk-plan layer share calibration with the engineering-plan layer through the prosecutor — but chunk-plan calibration examples (false-positive resolutions at the chunk-plan layer) stay scoped to chunk-plan invocations, not propagated up to engineering-plan invocations. Reason: a chunk-plan false positive often reflects layer-specific phrasing ("§Owns lists `userProfileSync.ts`, which the parent feature's Non-goal forbids touching" — but the chunk is actually touching a different function in that file). Engineering-plan false positives operate at a higher abstraction. Scope calibration per layer.

---

## Stage 2 — Persona prosecution (parallel agents, fix-list output)

Read `personas/ai-development.md` (at the **project root**, `./personas/…` relative to cwd — not the skill dir) and (if exists) `memory/plan-quality.md` once — referenced as paths in agent prompts; agents Read on demand.

Resolve personas (auto or explicit). Launch one Agent per (plan, persona) pair, **all in parallel in a single message**, each with `model: "sonnet"` per `_review-common/agent-prompt.md` § Model pin — never inherit the session model; record `persona_model` in the review state. N×M agents.

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

## Structural Sweep (unseeded matrix completion; runs as Stage 3b.4, before the Class Sweep)

Per `~/.claude/skills/_review-common/structural-sweep.md` — that file defines the mechanism, agent template, merge, and state/verdict schema. This section fills the chunk-plan slots.

**Why it is here.** The Class Sweep below is a finding-*expansion* pass: it is seeded from surviving Stage 2 findings and cannot discover a class nobody filed. So a defect class no persona noticed is invisible to the whole pipeline, and no compliance check fires, because there was no seed to be incomplete about. This stage is the unseeded counterpart and **runs even when Stage 2 produced zero findings** — a clean round is exactly when it earns its cost. It runs *before* 3b.5 so the Class Sweep can fold in an already-walked universe instead of re-walking it.

**Universes at this layer:**

- **Universe L — condition liveness.** Members: every acceptance criterion the plan states, plus every gate or check the chunk itself defines. The question: is there a reachable state in which this can never be satisfied, with no specified remedy? **Its mandatory trace procedure applies** — for each criterion, resolve every term it references to that term's definition wherever it lives, find every step that sets the term's inputs, and only then judge. A criterion judged on its own sentence alone is not judged.
- **Universe A — acceptance-criterion observability.** Members: every acceptance criterion. The question: does it name *how it is observed* — a test, a command whose output settles it, a gate, or an explicit manual check naming what the checker looks at? Distinct from L: L asks whether the criterion is satisfiable, A asks whether satisfaction is detectable. A criterion can pass L and fail A.

**Multi-plan mode:** run the universes per plan, not pooled — an acceptance criterion's satisfiability is a property of its own plan. Record one `structural_sweep` block per plan, alongside that plan's other state.

**Merge:** every GAP becomes a same-round finding at the sweep-judged severity, routed through the same 3b retraction filters and authority order as a persona finding, and folded into 3c with the Class Sweep's siblings.

## Repo Reality Sweep (codebase-derived; runs as Stage 3b.4b, alongside the Structural Sweep)

Per `~/.claude/skills/_review-common/repo-reality-sweep.md` — that file defines the mechanism, agent template, merge, and state/verdict schema. This section fills the chunk-plan slots.

**Why it is here, and why it is not another Structural Sweep universe.** Every stage above — Stage 1's trace, the personas, the Structural Sweep — enumerates its universe from **the plan**. Ground Truth reads code, but only to check claims the plan already made. What ships broken is what the plan **omits**, and silence cannot be falsified by re-reading, however carefully. This stage enumerates from the **repository** instead. It is a sibling rather than a fourth universe because the Structural Sweep's carry-forward hashes plan sections, which cannot see the code moving under a plan whose premises were verified against an older HEAD.

At this layer the plan is a single chunk, so this is **one agent**, carrying all three questions:

- **Universe R — incumbent divergence.** Grep for the shipped code doing this chunk's job today, by the behavior described rather than by the plan's file citations. Read its **secondary** writes — cache timestamps, audit rows, provenance columns, cleanups — since the plan describes the primary job and a dropped side effect is invisible on the page. Question: where the design differs, is the difference stated?
- **Universe C — caller closure.** Every existing caller of every symbol, file, table, column or route the chunk changes, tests and scripts included. Question: does the plan account for it? A symbol enumerated against one of the plan's invariants but not the rest is the common shape, and it reads as coverage.
- **Universe D — dependency guarantee.** Every primitive the chunk **newly makes load-bearing**. Open it, establish its real guarantee, and judge the plan's use **at the plan's stated scale** — hardest wherever the chunk widens a population, drops a filter, or raises a fallback to primary. Neither R nor C reaches this: the plan adopts the dependency rather than diverging from it, and it is a callee, not a caller.

At this layer the chunk plan names concrete files, so the enumeration is cheaper and sharper than at the engineering-plan layer — and this is the **last** gate before implementation, so a premise that survives here ships.

**Multi-plan mode:** one agent per plan, not pooled. Record one `repo_reality_sweep` block per plan.

**Merge:** every GAP becomes a same-round `REPO_PREMISE_GAP` finding at the swept severity, through the same 3b retraction filters and authority order, folded into 3c. Universe-D gaps are usually director decisions rather than auto-fixes.

**Re-run the three questions on any fix this round applies** — a remedy is new design against the same codebase, and the specific failure is authoring a check the repo already implements adjacent to what you just read. Grep before you specify; import rather than redefine.

## Class Sweep (dedicated sibling-enumeration fan-out; runs as Stage 3b.5)

Runs after Stage 3b retracts findings against critical-pair policies, before Stage 3d applies anything — a category whose only seed just died at 3b must not be swept, and swept siblings must be fixed in the same editing pass as their seeds. Per `~/.claude/skills/_review-common/class-sweep.md` — read it for the mechanism, the sweep-agent template, the orchestrator merge, and the state/verdict schema. This stage exists because chunk-plan personas file one instance of a recurring class per round (one vague acceptance criterion, one under-specified test bullet, one missing convention reference) and the siblings leak out one per round otherwise.

**Procedure (per the shared file), with these chunk-plan slots:**

- **Seed grouping.** Group the **3b survivors** by `class`. Drop from the sweep set any category whose only seeds are Stage-1-mechanically-fixed duplicates or obvious singletons (`class_notion` absent / peer-set is one location — "this plan has no rollback note"). Every remaining distinct `recurring_category` (and any `propagated_identity` with a >1 peer-set) gets one sweep agent, `model: "sonnet"`.
- **`{peer_set_definition}`** — the chunk-plan repeated units: every chunk under review (in multi-plan mode, sweep **across all plans in the invocation**, not just the seed's plan), every `§Acceptance criteria` bullet, every `§Tests to add` case, every `§Conventions` entry, every `§Read first` / Owns entry, every implementation-sketch claim. Name the specific unit the seed's `peer_set` points at.
- **`{artifact_access}`** — `Read <plan_path>` in full (all plans in multi-plan mode). For `propagated_identity` classes, the token grep across the plan set and any repo file the class propagates into.
- **`{layer_notes}`** — a chunk plan is single-concern; a sibling that would belong to a *different* chunk's concern is not this class's sibling (respect `P-CHUNK-SINGLE-CONCERN`). Basis-fidelity (`SURFACE_PARITY_GAP`) and brief-conformance findings are Class A — their siblings inherit the Class A carry-forward exemption.
- **Merge.** Dedup siblings against the Stage 2 pool by `(class, path_or_section)`; route the new siblings through **Stage 3b critical-pair retraction** (same filter the seeds get) before folding them into the Stage 3d consolidation. Record the `class_sweep` block in `per_round_metrics`.

Skip the stage (record `class_sweep.ran=false`) only when zero sweep-eligible categories exist among the surviving Stage 2 findings.

---

## Stage 3 — Orchestrator decision

Stage 3 runs in the main thread, per plan.

### 3a. Apply Stage 1 mechanical fixes

Already done at end of Stage 1. Confirm the file matches the post-fix state.

### 3b. Filter Stage 2 fix lists against critical-pair policies

This layer runs no section-diff gate, so it emits no round-memory tags and the shared tag filter does not apply here. For each finding from each persona on this plan:

- Contradicts an active critical-pair policy → retract. Note in verdict.
- Duplicates a Stage 1 hard finding already mechanically fixed → retract.
- Otherwise → keep.

Class A findings are exempt from decisions-log carry-forward retraction, not from these two filters.

### 3b.4 Structural Sweep

Runs here — see "Structural Sweep" above. Unseeded: spawn it regardless of how many findings survived 3b, including zero. Its GAPs join the finding pool before 3b.5 so the Class Sweep can fold an already-walked universe rather than re-walk it.

### 3b.5 Class Sweep

Runs here — see "Class Sweep" above for the full procedure. Group the 3b survivors by class, sweep, then carry the merged finding set into 3c. Pass `{structural_sweep_universes_run}` from 3b.4 so a widened peer-set that overlaps a walked universe is folded in, not re-walked.

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
2. `<plan-root>/engineering-plan.md` — chunk-DAG layer; bound invariants and decisions-closure table.
3. The chunk plan under review.

When a finding's substance reveals contradiction across artifacts, the chunk plan aligns per `_review-common/principles.md` § Cross-artifact authority order — class-aware. **Class A contradictions** (the chunk plan asserts something a brief Goal or Non-goal forbids): the chunk plan loses to `brief.md` regardless of what `decisions.md` or `engineering-plan.md` says: `brief.md > decisions.md > engineering-plan.md > chunk plan`. A bound `decisions.md` entry that itself trespasses a brief Non-goal is the defect, not protection — the finding routes to the user as `BRIEF_NONGOAL_TRESPASS` (HARD, carry-forward-exempt). **Class B contradictions** (wiring / identifier / ownership): the existing order applies: `decisions.md > engineering-plan.md > chunk plan`. Contradictions *between* `decisions.md` and `engineering-plan.md` on a Class B question escalate as `OPEN_QUESTION` (user arbitrates which is canonical) — the orchestrator does not auto-resolve cross-upstream-artifact disagreement at the wiring layer.

When writing a cross-file edit:

- **decisions.md** — append a dated entry (today's date, current `round_number`) under the `## Active (bound)` heading, with the bound decision in one sentence, a `**Status:** bound` line, and the rationale in 1–3 sentences; reference the chunk slug; cross-link from the chunk plan's relevant section. If the new decision *replaces* an existing Active bound entry on the same surface, in the SAME edit flip that older entry to `**Status:** superseded by "<new title>" (<today's date>)` and move it to `## Archived (superseded / obsolete)` — a superseded entry left reading `bound` would silently override the new one (per `_review-common/principles.md` § What counts as a bound entry).
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

Per `~/.claude/skills/_review-common/orchestrator.md` § Post-fix premise verification. The claims that matter at this layer: TDD assertion descriptions, files-touched annotations, implementation-sketch claims about existing code patterns, and verification-step expected-output strings.

### Same-round focused re-prosecution on rewritten prose

Per `~/.claude/skills/_review-common/orchestrator.md` § Same-round focused re-prosecution — one pass per plan, bounded. Include cross-file edits to `decisions.md` / `engineering-plan.md` in the diff-hunk set. Apply survivors under the Convention-extraction, Cross-file-scope, and Forbidden-fixes rules above.

The pattern this catches, from real rounds: a round adds a testing accessor and the next round finds no contract test for it; a round introduces an idiom and the next finds its shape underspecified; a round adds a convention and the next finds nothing enforcing it. The re-pass reads 2–10% of the plan and costs ≤25% of a Stage 2 round.

### 3e. Classify remaining unresolved findings

See `~/.claude/skills/_review-common/blocker-classes.md`. Active for chunk plan review: `STRUCTURAL_LINT_FAILED`, `BRIEF_NONGOAL_TRESPASS`, `BRIEF_GOAL_UNDELIVERED`, `SURFACE_PARITY_GAP` (basis axis only — filed by Stage 1 engineering-plan-trace when a chunk drifts below its EP row's authoritative signal), `PROSE_DENSITY_EXCESS`, `AUTHOR_GATE_DRIFT`, `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `FIX_INTRODUCED_PREMISE_INVERSION`, `REMEDIATION_INCOMPLETE`, `DECISIONS_PROVENANCE_GAP`, `POLISH_PLATEAU`, `REPO_STATE_DRIFT`. `REMEDIATION_INCOMPLETE` and `DECISIONS_PROVENANCE_GAP` are filed by the Round Memory Pass's Remediation-completeness sub-pass and are **exempt from `recently_resolved_blockers` carry-forward** — each is an assertion about the completeness of the carry-forward record itself, so retracting it against that record is circular. `DECISIONS_PROVENANCE_GAP` is additionally exempt from decisions-log-first retraction: a citation to a `decisions.md` entry that does not exist cannot be retracted by `decisions.md`. `PROSE_DENSITY_EXCESS` is exempt from decisions-log-first carry-forward unless the cited `decisions.md` row explicitly arbitrates density (per the keyword list in `_review-common/blocker-classes.md`); `AUTHOR_GATE_DRIFT` fires when the author state's `prose_density` field is absent or its sub-metric counts disagree with the reviewer's recomputation.

**Carry-forward consultation (decisions-log-first, then ephemeral cache).**

Before emitting any blocker, run two consultations in priority order. The decisions log is the project's durable arbitration record — what the user codified as "this question is bound; don't re-litigate." The ephemeral state-file cache is local to `~/.claude/cache/review-state/` and decays at `carry_forward_until_round`. Reading the durable record first means a finding contradicting `decisions.md 2026-05-06 "bundle ceiling extended from 5 to 6 implementation files"` is dropped automatically rather than re-litigated as an OPEN_QUESTION every round.

**Priority 1 — `decisions.md` lookup** (durable arbitration; persists across rounds; class-aware).

**Class-A exemption (mandatory, runs first).** Classify each surviving finding's class per `_review-common/principles.md` § Cross-artifact authority order before applying retraction:
- Finding's `evidence` field contains a verbatim quote from `brief.md` § Goals / Non-goals / User-facing changes, OR the finding's class is `BRIEF_NONGOAL_TRESPASS` / `BRIEF_GOAL_UNDELIVERED` (filed by Stage 1.5 Brief-conformance audit) / `SURFACE_PARITY_GAP` (basis axis, filed by Stage 1 engineering-plan-trace) → **Class A**. **Skip Priority 1 retraction entirely.** Class A findings are NEVER dropped by decisions-log carry-forward, even when the contradicting evidence is itself a bound `decisions.md` entry. A bound entry that trespasses a brief Non-goal — or that quietly downgrades a Goal's authoritative signal to a proxy — is the defect, not protection. (Exception already handled upstream: a proxy the EP row or a bound decision committed *and framed as launch-acceptable* never becomes a `SURFACE_PARITY_GAP` finding in the first place — the Stage 1 basis check only fires on unacknowledged drift, so there is no legitimate bound entry for carry-forward to protect here.)
- Finding cites a cross-chunk identifier (file path, schema column, module ownership, transaction boundary) → **Class B**. Proceed with Priority 1 retraction below.
- Finding cites a chunk-internal target only → **Class C**. Proceed with Priority 1 retraction below.
- Ambiguous (cites both brief Non-goal AND wiring identifier) → **Class A** (stricter wins). Skip retraction.

Record the class on every finding. The verdict's `decisions_md_consultation` block reports `findings_dropped_class_B: <n>; findings_dropped_class_C: <n>; class_A_exempt: <n>`.

**For Class B and C findings only**, for chunk plans under a feature's `implementation/` (either layout), `Read` `features/<feature>/decisions.md`. Search for entries whose `path_or_section` (file paths, identifier names, schema field names, decision titles) overlap the finding's surface. Match heuristic:

- **Strong match** — decisions.md entry quotes the same identifier or path the finding cites verbatim (e.g., finding cites `__concurrentGuardForTesting` and the entry titled "Co-located test-only accessor pattern" names the same identifier).
- **Topical match** — decisions.md entry's title or rationale names the same concept (writer-fence-quiescence, banner scrubbing, accessor pattern, sequence pre-pin, trap-row idiom, etc.).

If a strong or topical match exists AND the entry is dated AND the entry is bound (no `pending` / `undecided` / `open` / `superseded` / `obsolete` qualifier in the entry body, and the entry is not in the `## Archived (superseded / obsolete)` section; per `~/.claude/skills/_review-common/principles.md` § What counts as a bound entry):

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

**Final line — verdict banner.** After the per-plan output below, the multi-plan summary (if any), and any §3h auto-open or manual-open analysis, run the shared verdict-banner script and emit its output verbatim (`~/.claude/skills/_review-common/blocker-classes.md` § Verdict banner) as the **very last** thing in your response, so the verdict is visible without scrolling.

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
**Class sweep:** ran={bool}; sweep_agents={n}; siblings_found={n}; siblings_after_filter={n}
**Final Tier 1 weight:** {n}
**Final Tier 2 weight:** {n} (floor: 4)

### Structural sweep (unseeded)
Always rendered — an all-clean sweep is the evidence the universe was covered, and it is what makes an `APPROVED` verdict mean more than "no persona noticed anything".
- Universe: {name} — {members_enumerated} members: {closed} closed, {gap} gap, {na} n/a, {undetermined} undetermined
- Skipped: {universe} ({reason}) · Inherited clean: {universe} (from round {n})
- Gaps promoted to findings: {n} ({severities})

### Class sweep audit
For each class swept (omit block entirely when class_sweep.ran=false):
- Class: {name} ({class_notion}) — bare invariant: {bare_invariant}
- Peer-set: handed {peer_set_handed} → walked {peer_set_walked} {(widened — {widening_justification}) | (confirmed widest)}; {n} members; swept clean: {n}
- Instances: {seeds} seed + {siblings_found} sibling ({siblings_after_filter} survived critical-pair filter); resolution: all fixed this round | {n} escalated as {blocker class}
- Singleton classes recorded (no peer-set): {list, or none}

### Changes Made
- {bullets of significant edits, including any cross-file edits to decisions.md / engineering-plan.md / brief.md and any §Conventions extractions}

### Retractions
- {finding} → retracted because {critical-pair policy / pre-resolved by Stage 1 / superseded}

### Blockers (if any)
- [BRIEF_NONGOAL_TRESPASS] {chunk section or bound decisions.md entry} — parent-feature brief Non-goal: "{verbatim quote}"; trespassing evidence: "{verbatim quote}"; reasoning: {prosecutor reasoning paragraph}. Resolution paths: {amend_brief / drop_section / unbind_decision}.
- [BRIEF_GOAL_UNDELIVERED] {brief Goal or §Goal} — Goal: "{verbatim quote}"; the chunk's §Goal does not contain a verbatim quote from brief Goals / User-facing changes nor cite a Supporting-infrastructure mapping. Resolution paths: {rewrite_chunk_goal / cite_supporting_infrastructure / amend_brief}.
- [SURFACE_PARITY_GAP] {chunk §Goal + EP row} — Goal / EP row names authoritative signal: "{verbatim quote}"; the chunk computes the outcome on a weaker proxy instead: "{verbatim implementation evidence}"; the EP row / decisions.md did not commit this downgrade as launch-acceptable, so the chunk drifted below its row. Resolution paths: {compute_on_authoritative_signal / bind_the_proxy_upstream_as_launch_acceptable (amend EP row or decisions.md, moving the call to the engineering-plan layer where it belongs)}.
- [STABLE_DISAGREEMENT] {finding} — Persona A: {fix A}; Persona B: {fix B}. Pick one.
- [OPEN_QUESTION] {finding} — {question}
- [FIX_INTRODUCED_PREMISE_INVERSION] {chunk/section}: orchestrator-applied fix asserts "{verbatim claim}"; verification: {what was run}; actual: "{contradicting evidence}". Working tree dirty.
- [POLISH_PLATEAU] {finding} — non-blocking; ship is acceptable.
- [REPO_STATE_DRIFT] HEAD changed from {sha} to {sha}. Re-run.

### Plan Status: APPROVED / NEEDS USER INPUT
```

If `NEEDS USER INPUT`: the next step is **targeted edits to clear the listed blockers**, then re-invoke `/plan-review-v2` (optionally triage first with `/explain-blockers` or `/solve-blockers`). Do **not** regenerate the whole plan with `/plan-author` to clear a handful of blockers — see the hard rule below. The next run is fresh.

If `APPROVED` **and the prior round was not APPROVED** (first clean pass): re-invoke `/plan-review-v2` once more to confirm convergence. A second consecutive APPROVED auto-opens the plan-doc PR — see §3h.

If `APPROVED` **and the prior round was also APPROVED**: §3h has either opened the plan-doc PR or rendered its manual-open analysis; the cycle is complete unless that analysis said `RE-REVIEW`.

### 3h. Auto-open the plan-doc PR on the second consecutive APPROVED

When this round renders `APPROVED` **and** the loaded state's `last_verdict` was also `APPROVED`, the plan has converged across two consecutive clean reviews — ship the plan-doc PR **automatically, inline**. Run the `git` / `gh` steps **directly**; do **NOT** invoke the `/open-pr` skill. Going through Bash keeps this out of `~/.claude/hooks/block-self-scheduling.sh` (which guards only the `Skill` tool), so no confirm prompt fires. This is the single sanctioned auto-open — see `memory/feedback_never_open_pr_without_explicit_ask.md`.

All of these must hold, or skip the auto-open and print the manual next step instead:

- **Exactly one plan under review.** In multi-plan mode, do not auto-open; list which plans reached 2×APPROVED and let the user open each.
- **`features/`- or `fixes/`-rooted plan** — both are git-tracked, so the plan doc ships as a PR (a `fixes/` one-off's PR bundles just the plan file, or the plan file plus any review cross-file edits). A `.scratch/` plan is gitignored and has no PR flow — skip the auto-open and print the manual next step.
- **On a non-`main` branch** — `git rev-parse --abbrev-ref HEAD` is not `main` and not detached (normally the `<slug>-plan` plan worktree/branch). On `main`/detached, skip and note it.
- **This round's fixes stayed bounded.** If this round's applied fixes (Stage 1/3 plus cross-file edits) materially rewrote plan semantics — scope, exit criteria, contracts, test plans, DAG-relevant content — then the second APPROVED approved a plan the first APPROVED never saw, and auto-shipping it would skip human eyes on effectively-new content. Wording, formatting, quote-sync, and state/sidecar bookkeeping do not count against this. Skip the auto-open and run the manual-open analysis below.

Steps (follow the project's commit/PR conventions — `type: description` commits, no AI-attribution trailer, docs-only PR so **no Test plan section**, no spurious `#N`):

1. `BRANCH = git rev-parse --abbrev-ref HEAD`; confirm `BRANCH != main`.
2. **Already-open guard.** `gh pr list --head "$BRANCH" --state open --json number` — if a PR exists, `git push` the review's commits to it and report that PR; do **NOT** open a second.
3. **Commit** any dirty working tree — the plan file plus any cross-file edits the review applied (`decisions.md` / `engineering-plan.md` / `brief.md` / `lint-config.json`) — in one commit. Message: `docs(<feature>): <chunk-slug> chunk plan` for a `features/` plan; `docs(fixes): <slug> plan` for a `fixes/` one-off (no parent feature). If the tree is already clean (fixes committed earlier), skip to push.
4. **Push:** `git push -u origin "$BRANCH"`.
5. **Open the PR:** `gh pr create --base main --head "$BRANCH" --title "<same as the commit message>" --body "<one-paragraph summary of the plan and the brief/EP Goals it implements, or — for a `fixes/` plan — the GitHub issue it fixes>"`.
6. Report `**Auto-opened PR:** <url>` on its own line in the verdict.

After the PR is open the review cycle is complete. Do **NOT** chain into `/execute-plan` or `/review-pr-v2` — those still require the user to start them fresh in a clean context (`memory/feedback_never_auto_invoke_workflow_skills.md`; the hook still guards both). The auto-open is bounded to this 2×APPROVED plan-doc convergence point and nowhere else.

#### Manual-open analysis — auto-open skipped for unbounded fixes

Runs only when the bounded-fixes condition is the one that failed (single plan, git-tracked root, non-`main` branch all hold — a `.scratch/` plan or `main` checkout has no PR to analyze). One final pass, inline, deciding whether the user can open the PR now or the plan needs a third round:

1. Collect this round's full delta: `git diff HEAD` plus any commits made this round, scoped to the plan file and the cross-file edits.
2. Judge every hunk on two questions:
   - **Traceable** — it maps to a named item in this round's report (Stage 1 mechanical fix, Stage 3 fix, convention extraction, cross-file edit). An orphan hunk no finding explains fails.
   - **Re-verified** — this round's own machinery already re-checked the changed content (post-fix premise verification, same-round re-prosecution, structural lint, quote checks). A hunk none of those covered fails.
3. Every hunk passes both → render `**Manual open: COMFORTABLE** — {n} hunks, all traceable and re-verified; {one clause naming the largest change}`. The user opens the PR; never auto-open on this path and never self-invoke `/open-pr`.
4. Any hunk fails either → render `**Manual open: RE-REVIEW** — {hunk}: {which question it failed and why}`. Next step is a fresh `/plan-review-v2` round.
5. Feed the same line to the verdict banner's `--next`.

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
- **Carry-forward consultation is mandatory, decisions-log-first, and class-aware.** Before emitting any blocker, consult `decisions.md` (durable arbitration) FIRST, then `recently_resolved_blockers` (ephemeral cache). Findings contradicting a bound `decisions.md` entry are dropped — **EXCEPT** Class A findings (`BRIEF_NONGOAL_TRESPASS`, `BRIEF_GOAL_UNDELIVERED`, or any finding whose evidence quotes a brief Goal / Non-goal / User-facing change verbatim). Class A findings are NEVER dropped by carry-forward per `_review-common/principles.md` § Cross-artifact authority order; the bound entry is itself the defect. Findings re-prosecuting a span in `recently_resolved_blockers` without `current_reclassification_justification` are downgraded to `OPEN_QUESTION`.
- **Stage 1.5 Brief-conformance audit is mandatory** when the chunk plan is under a feature's `implementation/` (either layout). Skipped for `.scratch/` and `fixes/` plans (no parent feature). The audit spawns the Brief-conformance Prosecutor (`~/.claude/skills/_review-common/brief-conformance-prosecutor.md`), files `BRIEF_NONGOAL_TRESPASS` and `BRIEF_GOAL_UNDELIVERED` as `pre_resolved_hard_findings` exempt from carry-forward retraction. Personas may file additional findings but cannot retract Stage 1.5 ones.
- **Basis-fidelity check is mandatory** on the Stage 1 engineering-plan-trace for `features/`-rooted plans. When the chunk's §Goal / its EP row / the brief Goal names a distinguished authoritative signal, verify the chunk computes the outcome on that signal, not a proxy — filing `SURFACE_PARITY_GAP` (basis axis) only on unacknowledged drift below the row (a proxy the EP row or a bound decision already committed as launch-acceptable is not a finding). This is the chunk-layer half of scope-fidelity; the domain and timing axes stay at the engineering-plan layer. `.scratch/` plans skip it (no EP/brief to measure against).
- **Compliance self-check additions.** Before emitting the verdict, confirm: (a) **Stage 1.5 Brief-conformance audit ran** for `features/`-rooted plans — `brief_conformance_report` is non-empty in Stage 3 input, and any filed `BRIEF_NONGOAL_TRESPASS` / `BRIEF_GOAL_UNDELIVERED` findings appear in the verdict; (b) **Class-A exemption fired correctly** — if `brief_conformance_report.findings_high_hard > 0` AND `decisions_md_consultation.class_A_exempt < findings_high_hard`, some Class A findings were dropped by carry-forward; re-classify and restore them before posting; (c) **Stage 1 basis-fidelity check ran** — for a `features/`-rooted plan whose §Goal or EP row names an authoritative signal, the trace recorded whether the chunk computes on that signal or a proxy, and any `SURFACE_PARITY_GAP` filed appears in the verdict; (d) **Class Sweep ran for every recurring category** — `class_sweep.sweep_agents_spawned` equals the count of distinct sweep-eligible (non-singleton) Stage 2 categories, every spawned agent recorded a `peer_set_size` and non-empty `swept_clean` (an agent reporting instances with empty `swept_clean` on a multi-member peer-set did not walk it — re-run), and every surviving sibling appears in the consolidated fix set or a blocker. Seed categories tagged `class_notion: recurring_category` with `sweep_agents_spawned: 0` mean the stage was skipped — run it before posting; (e) **every sweep agent performed the peer-set challenge** (`class-sweep.md` § The sweep, Method step 1) — each category records a non-empty `bare_invariant`, both `peer_set_handed` and `peer_set_walked`, and an explicit `peer_set_widened` flag with a justification when true. A `bare_invariant` that merely restates the seed's wording, or a `peer_set_walked` copied from `peer_set_handed` with no evidence the supertype question was asked, means step 1 did not run — re-run that agent, because a faithfully-walked *narrow* peer-set reports clean while leaving the class open and that failure does not show up in the instance counts; (f) **the Structural Sweep ran every applicable universe at 3b.4** — `structural_sweep.ran` is true, `universes_run` + `universes_skipped` + `universes_inherited_clean` accounts for both Universe L and Universe A per plan, every run universe recorded `members_enumerated` + a non-empty `cells` list + a non-empty `sections_read`, every Universe-L cell carries a non-empty `traced` field, and every GAP appears in the fix set or a blocker. **This check is independent of the round's finding count** — a zero-finding round that skipped the stage is non-compliant, which is precisely the case the stage exists for. (g) **the Repo Reality Sweep ran at 3b.4b** — `repo_reality_sweep.ran` is true for any plan naming code, with a non-empty `incumbent_files_read`, an `enumeration_query` recorded per universe (a universe with no query was not run, whatever its cells say), stored `incumbent_files_blob_shas` still matching HEAD on any `inherited_clean` plan, and every GAP in the fix set or a `REPO_PREMISE_GAP` blocker. Independent of the round's finding count, for the same reason. (h) **Remediation-completeness ran on every prior blocker** — on `round_number > 1`, `remediation_completeness` has one entry per entry in the prior round's `prior_blockers`, each with a non-empty `coupled_sites_checked` and an explicit `decisions_entry` (a heading, or `none` with its class). An entry with `closed: yes` and an empty `coupled_sites_checked` answered only the first of three questions; re-run it. Any `REMEDIATION_INCOMPLETE` / `DECISIONS_PROVENANCE_GAP` filed must appear in the verdict.
- **Cross-file fix scope is mandatory when triggered.** A persona's fix prose that mentions `decisions.md` / `engineering-plan.md` / `brief.md` or carries forward-binding markers (`binds for all`, `cross-cutting effect`, `for all future readers`, `negative decision`) MUST receive a corresponding cross-file edit in the same Stage 3d application. Filing it as a TODO note in the chunk plan instead is a forbidden fix.
- **Convention extraction precedes per-bullet pinning.** Before applying ≥3 fix bullets that share a structural pattern (spy-as-timing-primitive, trap-row idiom, sequence pre-pin, fake-timer wrap, etc.), extract the pattern to `§Conventions` once and reference from each bullet. Inline duplication across bullets is a forbidden fix.
- **Structural Sweep is mandatory and is NOT contingent on the round producing findings.** Per `~/.claude/skills/_review-common/structural-sweep.md`: one unseeded agent per applicable universe at Stage 3b.4 — Universe L (condition liveness over every acceptance criterion and chunk-defined gate, with its mandatory trace procedure) and Universe A (acceptance-criterion observability), run per plan in multi-plan mode. It exists because the Class Sweep is seeded and therefore structurally blind to a class no persona filed. A round with zero Stage 2 findings still runs it; a verdict reporting no structural sweep is incomplete regardless of how clean the rest of the round looked. Skipped per-universe only on the shared file's skip rule, and every skip records its reason.
- **Class Sweep is mandatory** whenever a surviving Stage 2 finding declares `class_notion: recurring_category` (or a `propagated_identity` with a >1 peer-set). One sweep agent per distinct such category walks the peer-set (across all plans in multi-plan mode) and promotes every sibling to a same-round finding at Stage 3b.5 — after 3b retraction, before 3c and 3d — so siblings and seeds pass through the same critical-pair filter and the same disagreement detection. Per `~/.claude/skills/_review-common/class-sweep.md`. This is what closes a defect class in the round it was found instead of leaking one sibling per round. Skipped only when zero sweep-eligible categories exist.
- **Same-round focused re-prosecution is mandatory** when ANY of: Stage 3d chunk-plan fixes > 0, cross-file edits > 0, or Post-fix premise verification falsified-claim count > 0. Bounded: exactly one re-pass; never an inner loop. Skipped only when ALL three are zero (no rewritten prose to re-prosecute).
- **The Remediation-completeness pass is mandatory on every `round_number > 1`** (Round Memory Pass), and covers what the two verification stages above structurally cannot: both scope to the orchestrator's *own* edits, while the majority of text entering a round is remediation the **user** wrote between rounds to clear the last verdict's blockers. Every prior blocker gets all three questions — closed, swept into every coupled site, arbitration recorded in `decisions.md` — with no sampling. At this layer the Factoring Contract carries the yield: it is the one section `/plan-lint` reads mechanically, so a remediation that changes what the chunk writes but skips its `Owns (writes)` entry is invisible to the deterministic floor and the personas alike. Skipping the pass makes a `NEEDS USER INPUT` → re-invoke cycle non-convergent by construction.
- **Stage 2 agents return fix lists; never edit files.** All edits applied by orchestrator in Stage 3.
- **Stage 3 applies critical-pair policies before applying fixes.** Findings contradicting a policy are retracted, not relitigated.
- **Never** mark APPROVED while any blocker class is non-empty.
- **Never** weaken the plan to resolve a finding. That's `OPEN_QUESTION`.
- **Always** quote verbatim from plan, repo, or audit_report when justifying a finding.
- **Always** label remaining findings with their blocker class.
- **No multi-round inner loop.** The same-round focused re-prosecution is exactly one pass over diff hunks; survivors land in the verdict and the user re-invokes.
- **Do not re-run `/plan-author` to clear a completed review.** When the verdict is `NEEDS USER INPUT`, the next step is targeted edits that clear the listed blockers, then re-invoking `/plan-review-v2` (optionally triaged through `/explain-blockers` or `/solve-blockers`). Re-running `/plan-author` re-enters the full authoring pipeline over the whole chunk plan — wrong tool for clearing ordinary blockers (`OPEN_QUESTION`, `STABLE_DISAGREEMENT`, `IMPLEMENTABILITY_GAP`, and the like). Re-run the author skill only in two cases: the mid-cycle `Status: needs-user-input` refuse path (the artifact is already a partial draft and the author resumes it in warm mode); or the rare case where the plan is fundamentally broken and must be re-authored wholesale (ask in plain language). The author-gate blockers (`AUTHOR_GATE_DRIFT`, `PROSE_DENSITY_EXCESS`, `CONCERN_GATE_FAILED`) are NOT re-author cases — the reviewer already recomputes those gates, so they are cleared by the same targeted agent edits as every other blocker (split the overgrown bullets / decompose the chunk / cite an arbitration) plus reconciling the stale author-state field. Re-running the author to clear them desyncs the in-flight review state (`section_hashes`, `round_number`, blocker carry-forward) for no benefit.

## Compliance self-check (before rendering verdict)

Run the checklist in `~/.claude/skills/_review-common/orchestrator.md` § Compliance self-check and state each result in the verdict. A failed check is reported, never silently skipped. At this layer the check runs **per plan** — a multi-plan invocation renders one attestation block per plan.

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
