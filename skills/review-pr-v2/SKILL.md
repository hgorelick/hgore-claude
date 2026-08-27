---
name: review-pr-v2
description: Adversarial single-pass review of the current branch's PR, converging across re-invocations. Applies fixes, re-runs gates, commits, and posts the verdict to the PR. Use after `/open-pr`. Sister to the plan-layer reviewers (`/brief-review-v2`, `/engineering-plan-review-v2`, `/plan-review-v2`).
user-invocable: true
---

# Review PR v2 — Staged Single-Pass

Three stages (plus a feature-scoped Stage 1.5 Brief-conformance gate between Stages 1 and 2), with bounded same-round verification on orchestrator-rewritten code/prose. Never a multi-round inner loop. If blockers remain, the user resolves them and re-invokes — the next run carries forward round-memory state (touched-file hashes, prior blockers, classification history) so it does not re-prosecute code that was reviewed and accepted last time.

## Shared scaffolding (read these as needed; do not inline into agent prompts)

- `~/.claude/skills/_review-common/principles.md` — stance, banned rationalizations, severity/tier classification, plan style rules
- `~/.claude/skills/_review-common/round-memory.md` — state file, load, capture priority, persist
- `~/.claude/skills/_review-common/orchestrator.md` — the shared Stage 3 spine
- `~/.claude/skills/_review-common/agent-prompt.md` — persona-agent prompt template
- `~/.claude/skills/_review-common/critical-pairs.md` — pre-resolved rule conflicts (active subset for PR review: P-CLASS-SCOPE, P-FULL-FILE, P-PR-OWNERSHIP, P-PR-COVERAGE, P-PR-CLAIMS, P-PR-BRIEF-PARITY)
- `~/.claude/skills/_review-common/brief-conformance-prosecutor.md` — Stage 1.5 Brief-conformance Prosecutor + Scope-fidelity Adversary roles (feature-scoped PRs; see § How the hosting skills invoke → PR-review-layer)
- `~/.claude/skills/_review-common/class-sweep.md` — seeded sibling-enumeration stage (expands a found class)
- `~/.claude/skills/_review-common/structural-sweep.md` — unseeded matrix-completion stage (discovers unfiled classes)
- `~/.claude/skills/_review-common/blocker-classes.md` — blocker registry + verdict gate

## Workflow

```
Find the PR
   ↓
Stage 1: Ground truth pass     (deterministic, no LLM judgment)
   ↓   Prior-invocation intake (PR comments)
   ↓   Round Memory load — state file, file-hash diff, prior-blocker
   ↓                       consistency check
   ↓   Repo Reality Audit
   ↓   Gates baseline
   ↓   Diff intake
   ↓   Stage 1 mechanical fixes
   ↓ produces audit_report
Stage 1.5: Brief-conformance gate  (feature-scoped PRs only; parallel subagents)
   ↓   detect feature-scope; reconstruct at-risk Goals touched by this PR
   ↓   spawn 1 Brief-conformance Prosecutor + N per-Goal Scope-fidelity
   ↓     Adversaries (isolated) against the DELIVERED diff, not a plan
   ↓   BRIEF_NONGOAL_TRESPASS / BRIEF_GOAL_UNDELIVERED / SURFACE_PARITY_GAP
   ↓     = Class A HARD, exempt from decisions-log carry-forward retraction
   ↓ produces brief_conformance_findings (enter Stage 2 as pre-resolved)
Stage 2: Persona prosecution   (LLM judgment, M parallel agents)
   ↓   each persona: premise interrogation (diff-baseline +
   ↓                                        PR-description +
   ↓                                        Goal-outcome sub-passes)
   ↓                 + standard prosecution + round-memory tagging
   ↓ produces fix_lists
Stage 3: Orchestrator decision (apply Stage 1 mechanical fixes, filter by
                                 round-memory tags, filter by critical-pair
                                 policies, run Structural Sweep (UNSEEDED —
                                 one agent per universe over the diff: L
                                 guard liveness, T changed-surface tests,
                                 Z mutation authorization; runs even on a
                                 zero-finding round — _review-common/
                                 structural-sweep.md), run Class Sweep (one
                                 agent per distinct recurring category walks
                                 the diff + blast radius for siblings —
                                 _review-common/class-sweep.md), detect cross-persona
                                 disagreement, consolidate fixes, run post-fix premise
                                 verification on orchestrator-rewritten prose,
                                 run SAME-ROUND focused re-prosecution on
                                 diff hunks (≤1 re-pass) when ANY of:
                                 orchestrator-fix-count > 0, falsified > 0,
                                 HEAD-changed, run carry-forward consultation
                                 Priority 1 (features/<feature>/decisions.md
                                 when PR is feature-scoped) then Priority 2
                                 (prior_blocker classification consistency),
                                 re-run gates, commit, execute the PR
                                 `## Test plan` and tick it off (fix failures
                                 or escalate), classify remaining,
                                 persist state file, run compliance self-check,
                                 render and post verdict)
```

## Find the PR

```bash
gh pr view --json number,title,url,headRefName,baseRefName
```

If no PR exists for the current branch, tell the user to run `/open-pr` first and stop.

---

## Stage 1 — Ground truth pass (MANDATORY, NO LLM JUDGMENT)

### Prior-invocation intake

Pull every tribunal artifact on the PR (both v1 round-comments and v2 verdict comments). Read each in full.

```bash
gh pr view --json comments \
  --jq '.comments[] | select(.body | startswith("## Tribunal v2")) | {author: .author.login, createdAt, body}'

gh pr view --json reviews \
  --jq '.reviews[] | select(.body | startswith("## Tribunal")) | {author: .author.login, submittedAt, state, body}'

git log --oneline "$(gh pr view --json baseRefName --jq .baseRefName)..HEAD"
```

Derive:

- **Invocation number.** N+1 where N is the highest prior verdict invocation (v1 + v2 counted together). None → invocation 1.
- **Open blockers from prior invocations.** Anything labeled `NEEDS USER INPUT` in the most recent verdict and not resolved by a subsequent commit. Carry as `prior_blockers`, but re-verify each — do not paste prior text as proven.
- **Claimed fixes.** Findings a prior verdict declared resolved. Read the current source and confirm the fix landed *and* extended to the whole class. Claimed fix that didn't generalize re-opens.
- **Retractions.** Findings a prior invocation retracted (target was fictional, rationale wrong). Don't re-raise as novel.
- **Stale APPROVED verdicts.** Prior `APPROVED` + user invoking again → max suspicion. Either new commits arrived after the verdict (re-prosecute new commits AND re-verify prior claims) or the verdict was wrong (re-prosecute everything).

Record one short block in the audit report: `Prior-invocation intake (entering invocation N+1)` with prior verdicts/timestamps, commits since last, open blockers, claimed fixes scheduled for verification, retractions noted. Prior conclusions are **hypotheses, not evidence** — re-verify before propagating.

The PR-comment-derived `invocation_number` is cross-checked in the Round Memory load step against the state file's stored invocation number. If they diverge, the higher value wins and the audit records `state_file_resync: yes`.

### Round Memory load (mandatory, no LLM judgment)

This pass exists to break two PR-review thrash patterns observed in prior runs:

1. **Prosecution of remediation artifacts** — files touched in invocation N to fix a blocker get re-prosecuted in invocation N+1, surfacing "new" findings on user-applied fixes.
2. **Re-prosecution of unchanged code** — personas re-read the full diff each invocation and surface "new" findings on hunks that previously passed review.

Both are mitigated by carrying file-hash and prior-blocker state across invocations.

#### State file

Location, core schema, load rules, and persist rules: `~/.claude/skills/_review-common/round-memory.md`. Read it. The PR layer differs and adds as follows.

**Vocabulary.** This layer counts *invocations*, not rounds: `invocation_number`, `raised_in_invocation`, `resolved_in_invocation`, `carry_forward_until_invocation` are this layer's names for the shared `round_number`, `raised_in_round`, `resolved_in_round`, `carry_forward_until_round`. Same semantics.

**Slug** — `<owner>__<name>__pr-<N>`, with `<owner>__<name>` from `gh repo view --json nameWithOwner --jq .nameWithOwner` and `/` replaced by `__`.

**Extra fields:**

- `pr_number`, `branch` — the PR under review.
- `last_head_sha` — HEAD at the last invocation; feeds force-push detection.
- `last_diff_files` — `[{"path": "<path>", "blob_sha": "<git blob sha>"}]`; feeds the file-hash diff.

There is no `last_artifact_sha256` here — a PR's artifact is a diff, so `last_head_sha` plus `last_diff_files` play that role.

**Blocker classes seen here** — `POLISH_PLATEAU`, `FIX_INTRODUCED_REGRESSION`, `BASELINE_RED`, `SURFACE_PARITY_GAP`, `BRIEF_NONGOAL_TRESPASS`, `BRIEF_GOAL_UNDELIVERED`, `REMEDIATION_INCOMPLETE`, `DECISIONS_PROVENANCE_GAP`, plus the universal three.

- `remediation_completeness` — the per-blocker result of the two further questions asked of every `resolved` prior blocker (schema in the Prior-blocker consistency check). One entry per prior blocker, never sampled.

**Capture priority** replaces the shared list, because a PR carries evidence the plan layers don't:

1. **An explicit PR comment** naming the resolution choice ("I picked Option B because…") — use the relevant sentence verbatim.
2. **Commit message body** of the resolving commit, when it carries rationale prose.
3. **Commit message subject** of the resolving commit.
4. **`"No rationale recorded"`** when the evidence is silent.

Cap at ~200 chars.

#### Load prior state

`Read` the state file. Then cross-check against the PR-comment-derived invocation number from the Prior-invocation intake step.

- **Genuinely first invocation** (state file absent AND no prior verdicts on the PR): set `invocation_number = 1`. No prior state. Skip the remaining Round Memory sub-passes; proceed to Repo Reality Audit.

- **State present and consistent** (state file present; stored `invocation_number` agrees with PR-comment-derived count): set `invocation_number = <stored> + 1`. Proceed.

- **State file disagrees with PR comments by > 1 invocation** (cache cleared, user invoked from a different machine, comments deleted): take the higher value, tag the audit `state_file_resync: yes`. Proceed.

- **State file missing but PR has prior verdicts** (state-file loss, cache cleanup, machine swap): enter **state reconstruction**. Read the most recent v2 verdict comment body. Extract:
    - `invocation_number` from the `**Invocation:** N+1` line.
    - `last_head_sha` from the `**HEAD reviewed:** <sha>` line.
    - Open blockers from the `### Blockers (if NEEDS USER INPUT)` section, one entry per blocker line, with `blocker_class` from the bracketed tag, `path_or_section` and `summary` from the body text, and `raised_in_invocation = N` (the invocation that posted the comment).
    - `last_diff_files` is reconstructed from `git diff --name-only <pr_base>...<last_head_sha>` for the path list, then `git rev-parse <last_head_sha>:<path>` per path for the blob sha. `<pr_base>` is `gh pr view --json baseRefName --jq .baseRefName`.
    - If `last_head_sha` is no longer in local refs (force-push pruned the sha), set `last_diff_files: []` and `force_push_detected: true` defensively. Round-memory file-hash comparison degrades gracefully; personas treat the invocation with full prosecution latitude. Prior blockers are still reconstructible from verdict text and provide most of the convergence value.
    - `recently_resolved_blockers: []` — not reconstructible from verdict bodies (verdicts list open blockers, not resolved-this-invocation ones). One invocation of degraded prior-decision context; new resolutions begin populating again.

  Write the reconstructed state file before proceeding so the next invocation has full memory. Tag the audit `state_source: reconstructed_from_pr_comments`.

#### Force-push detection

Run `git merge-base --is-ancestor <last_head_sha> HEAD`. If exit is non-zero, the prior HEAD is NOT an ancestor — the user force-pushed (rebased / squashed) since the last invocation.

- Set `force_push_detected: true`. Do NOT auto-retract anything in Stage 3 — the file-hash comparison below is still valid (blob shas survive history rewrites if content is identical), but prior-blocker `path_or_section` line numbers may be stale.
- Tag prior_blockers with `line_numbers_may_be_stale: yes` so personas in Stage 2 verify line numbers against current HEAD before carrying them forward.

#### File-hash diff (gate for Persona Prosecution)

For each path in the current diff (`gh pr view --json files --jq '.files[].path'`), compute the current blob sha (`git rev-parse HEAD:<path>`). Compare to `last_diff_files[].blob_sha`:

- **Path in prior, blob_sha unchanged** → `unchanged_since_last_invocation`.
- **Path in prior, blob_sha differs** → `modified_since_last_invocation`.
- **Path not in prior** → `added_since_last_invocation`.
- **Path in prior but not in current** → `removed_since_last_invocation` (informational; no action).

Emit a `file_diff_report`:

```
### File diff (invocation N → N+1)
unchanged: [<path>, ...]
modified: [<path>, ...]
added: [<path>, ...]
removed: [<path>, ...]
```

Persona Prosecution agent prompts on `invocation_number > 1` MUST be prepended with:

> **This is invocation {N} of review. The following files in this PR are UNCHANGED since invocation {N-1}:** `{unchanged paths}`. **These files were prosecuted and accepted last invocation.** You may file findings against them only if you can name (a) a specific defect class the prior invocation's personas missed AND (b) why the prior lens did not catch it (new persona running this invocation? new evidence from a `modified` file interacting with this `unchanged` file? new ground-truth fact uncovered in this invocation's audit?). Findings against unchanged files without both (a) and (b) are auto-retracted by the orchestrator. Files marked `modified` and `added` get full prosecution latitude.

This is the **invocation-aware diff prosecution gate**. Personas still read unchanged files for context — but the bar to file new findings against text that previously passed review is raised, not zero.

#### Prior-blocker consistency check (MANDATORY)

For every prior blocker in the state file, classify against current state:

- **Path-keyed blocker** (has `path_or_section`): `Read` the file at the cited range. If the content has materially changed since `raised_in_invocation`, the user has acted on the blocker.
- **Non-path blocker** (e.g., `STABLE_DISAGREEMENT` resolved by a comment, `OPEN_QUESTION` answered in a commit message): scan PR comments and commit messages for resolution language.

Each prior blocker becomes one of:

- **`resolved`** — content addressed; no ongoing blocker.
- **`carrying_forward`** — content unchanged AND matches the prior blocker's symptom; will appear in this invocation's verdict at the same blocker class.
- **`reclassification_pending`** — content has changed but a Stage 2 finding may emerge with a *different* blocker class on overlapping span. Mark for the orchestrator to challenge in Stage 3: any new classification that differs from the prior class on overlapping span MUST include justification grounded in repo state (new commit, file change, new evidence) — without justification, the new classification is downgraded to `OPEN_QUESTION` per the prior-classification consistency rule. This mirrors `/engineering-plan-review-v2`'s Decision-Closure consistency check.

##### Remediation completeness — two further questions on every `resolved` blocker (MANDATORY)

The classification above answers **closed?** and stops there. Stage 3's same-round re-prosecution and post-fix premise verification cover only the **orchestrator's own** commits, so nothing in the pipeline asks whether the user's between-invocation fix actually *finished*. At this layer that gap is sharper than at the plan layers, because a code fix has call sites: a one-line change at exactly the line the finding cited, with every sibling call site untouched, presents as `resolved` on a content-changed check and ships the bug. Ask both questions of every blocker classified `resolved`, with no sampling.

1. **Swept?** Enumerate the sites the fix must reach and check each: every other call site of the changed symbol (`grep` the identifier repo-wide, not just within the diff), every sibling instance of the same defect class elsewhere in the diff, the **tests** covering the changed behavior (a fix with no test asserting it regresses silently on the next PR), and — where the prior blocker named a class rather than an instance — the whole class. A fix present at the cited line and absent from its coupled sites files `REMEDIATION_INCOMPLETE` (HARD, severity inherited from the original blocker), and the surviving sites feed the Class Sweep as seeds rather than waiting for a persona to rediscover them.

2. **Recorded?** On a feature-scoped PR (any path under `features/<feature>/` touched, or a commit / PR body citing a feature dir — the same detection Priority-1 carry-forward already uses), an arbitration the user made to close a blocker belongs in `features/<feature>/decisions.md`. Search for a bound Active-section entry covering it. A PR body, commit message, or plan span that *cites* a `decisions.md` entry which does not exist is a `DECISIONS_PROVENANCE_GAP` (HARD, HIGH) — resolve the citation by heading, not by date alone. An unrecorded arbitration cannot be retracted by Priority-1 carry-forward on the next invocation, so the same ground is re-prosecuted indefinitely. Non-feature-scoped PRs skip this question; record `decisions_entry: "n/a — not feature-scoped"`.

Record as `remediation_completeness` in the state file: `{blocker, closed: yes|no, closing_evidence, coupled_sites_checked: [...], sites_missed: [...], decisions_entry: "<heading>" | "none — <class>" | "n/a — not feature-scoped"}`. An entry with an empty `coupled_sites_checked` answered only the first question; re-run it. Both classes are **exempt from Priority-2 carry-forward** — each is an assertion about the completeness of the carry-forward record itself, so retracting it against that record is circular; `DECISIONS_PROVENANCE_GAP` is additionally exempt from Priority 1.

Emit a `prior_blocker_audit` block:

```
### Prior blocker audit (entering invocation N+1)
Resolved this invocation: <count>
Carrying forward (still open): <count>
  - [<class>] <path:line>: "<summary>" (raised invocation <M>)
Reclassification pending (require justification or downgrade in Stage 3): <count>
  - <path:line>: was <old_class> in invocation <M>
Re-prosecuted on a recently-resolved span (require prior decision surfacing): <count>
  - <path:line>: was resolved in invocation <M> with user_decision: "<verbatim>"
```

Persist-on-exit runs near the end of Stage 3 — see "Persist state file" (executes BEFORE the verdict is rendered, so a posted verdict always implies a written state file).

#### Edge case — manual reset

Per the shared file: the user deletes the state file to discard prior-invocation memory. Never auto-detect "the PR was rewritten" — a force-push is not a reset.

### Repo Reality Audit

Use tool output, not memory. Record `git rev-parse HEAD` once at start; if it changes mid-stage, restart.

- **Tree:** `ls` repo root. Confirm workspace structure if claimed.
- **File list:** `git ls-files | wc -l`, spot-check.
- **Test infrastructure:** `git ls-files | grep -E '(test|spec|__tests__|\.test\.|\.spec\.|tests/)'`. Look, don't assume.
- **CI:** `ls .github/workflows/`, read existing workflows. Also `.gitlab-ci.yml`, `.circleci/config.yml`, `buildkite/`. Name jobs that exist.
- **Build/test commands:** Read `package.json` scripts, `Cargo.toml`, `Makefile`, `pyproject.toml`, `justfile`.
- **Entry points the diff touches:** `ls` each.
- **Identifiers the diff introduces or touches** (functions, types, fields, flags, CLI args, env vars, route paths, queue names, tables/columns): grep each. Record hit counts. Diff the only writer, or other places reference it?
- **Line-content claims:** for every `path:line` the prior intake referenced or the diff modifies, `Read` `path` around line N and verify content.

Output a `Repo Reality Audit (HEAD: <sha>)` block with: tree summary, file count, test layout, CI workflows + job names, build/test commands, entry points (exists/missing), identifiers verified (with hit counts), line-content claims (matches/DRIFT).

### Gates baseline

Run gates once up front. Record exit codes.

```bash
<project compile cmd>             # e.g., npx tsc --noEmit, cargo check --all-targets
<project lint cmd>                # e.g., npm run lint, cargo clippy
<project test cmd>                # all tests, not a subset
<project-specific cmd>            # e.g., npm run codegen
```

Record `Gates Baseline (HEAD: <sha>)`: compile / lint / tests / project-specific (PASS or FAIL with exit code).

A baseline failure is BLOCKING. "It was red before" doesn't exonerate the PR unless `git stash && <cmd>` on `main` reproduces the same failure byte-for-byte. If the baseline is red, emit `BASELINE_RED` blocker and stop — Stage 2 cannot meaningfully prosecute against a broken baseline.

### Diff intake

```bash
gh pr diff
gh pr view --json files --jq '.files[].path'
gh pr view --json title,body
git log --oneline $(gh pr view --json baseRefName --jq .baseRefName)..HEAD
```

For Stage 2 personas, surface **paths and references** — agents Read on demand:
- Full diff (provided inline)
- Authoritative changed-paths list
- Author's PR description (to be tested)
- Commit list

The orchestrator does NOT inline full file contents into agent prompts. Personas are expected to Read changed files and source-of-truth files (`CLAUDE.md`, `SPEC.md`, schema files, persona files, callers/callees) when their findings depend on them.

### Stage 1 mechanical fixes

Apply unambiguous fixes immediately:
- **Auto-formatter drift:** if `prettier --check` / `cargo fmt --check` / `gofmt -l` reports unformatted files, run the formatter and stage.
- **Linter auto-fixable:** if `eslint --fix-dry-run` / `cargo clippy --fix --allow-staged` shows mechanical fixes, apply.

Emit a `Stage 1 fixes applied:` bullet list.

### Stage 1 output (audit_report)

A bulleted facts list (NOT verbose YAML). Include only fields that mattered:
- HEAD sha
- prior_invocation summary
- repo_reality: paths/identifiers/CI/commands verified, line-content drifts
- gates_baseline: per-gate PASS/FAIL; `baseline_red: true|false`
- diff_intake: changed_files (paths only), pr_description, commits
- stage_1_fixes_applied

If `baseline_red == true`, skip Stage 2/3 and emit:

```
## Tribunal v2 — Verdict: NEEDS USER INPUT

[BASELINE_RED] Pre-existing gate failures detected on the branch before review:
  - <gate>: <failure summary>

The tribunal cannot meaningfully prosecute against a broken baseline. Resolve
the failing gates (or carve them out with a stable rationale) and re-invoke
/review-pr-v2.
```

---

## Stage 1.5 — Brief-conformance gate (feature-scoped PRs only)

This gate promotes outcome-scope parity from an informal per-persona lens to a **dedicated check at the PR layer** — the last gate before merge, and the first point where the artifact under judgment is delivered *code*, not a plan. It reuses the shared roles in `~/.claude/skills/_review-common/brief-conformance-prosecutor.md` (the same Brief-conformance Prosecutor + per-Goal Scope-fidelity Adversary `/engineering-plan-review-v2` runs), adapted to judge the diff. **Read that file's § How the hosting skills invoke → PR-review-layer before spawning** — it defines every delivered-code substitution. Runs between Stage 1 and Stage 2; its findings enter Stage 2 as pre-resolved hard findings.

### When it runs

Only when the PR is **feature-scoped**, detected exactly as the Stage 3 Priority-1 carry-forward does:

1. Inspect the diff's changed-files list. If any path matches `features/<feature>/(brief|engineering-plan|decisions|implementation/.*)\.md`, OR any commit-message body cites `features/<feature>/`, OR the PR description links a feature directory → feature-scoped; capture `<feature>`.
2. Not feature-scoped → record `brief_conformance: n_a (not feature-scoped)` and skip to Stage 2. There is no brief to trace to.
3. Feature-scoped but `features/<feature>/brief.md` absent → record `brief_conformance: skipped (no brief.md)` and skip.

If `baseline_red == true`, Stage 1.5 does NOT run (Stage 2/3 were already skipped).

### Reconstruct the at-risk Goals this PR touches

`Read` `features/<feature>/brief.md` and enumerate its `## Goals`. Select the **at-risk** subset — a Goal carrying a domain quantifier ("every", "across", "all", "any", "going forward", "at every surface") OR naming an authoritative signal/basis the outcome must be judged/computed on. A concrete single-surface Goal is not at-risk and gets no adversary here (the Stage 2 Scope-persona lens covers it — see § Skill-specific extensions → Goal-outcome premise check).

Then intersect with what THIS PR delivers: `Read` the feature's engineering plan § Brief mapping to learn which chunks deliver each at-risk Goal, and match against the PR's changed files / description / chunk slug. The plan is at `features/<feature>/engineering-plan.md` when the feature is flat, or `features/<feature>/plans/<track>/engineering-plan.md` when tracked — per `~/.claude/skills/_plan-common/layout.md`. For a tracked feature, read **every** track's Brief mapping: the PR's chunk belongs to one track, but a Goal's remaining clauses may be another's, and only the union tells you whether this PR is meant to deliver the whole Goal or one declared clause of it. A Goal no part of this PR touches gets no adversary. Record the selection:

```
### Stage 1.5 Goal selection (feature: <feature>)
At-risk Goals: <list>
Touched by this PR (adversary spawned): <list>
Skipped — not at-risk: <list>
Skipped — not touched by this PR: <list>
```

When in doubt whether a Goal is at-risk or touched, spawn the adversary — a clean attestation is cheap; a missed narrowing is the failure this gate exists to prevent.

### Spawn the gate (parallel subagents)

Following `brief-conformance-prosecutor.md` exactly. **Both roles take an explicit off-model `model` override** per that file's § Model pin (default `sonnet`; `opus` if the session is already Sonnet) — never inherit the session model. Record the pinned model as `brief_conformance_report.conformance_gate_model`.

1. **One Brief-conformance Prosecutor** (`general-purpose` agent) with the prosecutor prompt, `{plan_path}` = the delivered diff (`gh pr diff`) + changed source files at branch HEAD, `{plan_layer}` = `pr-diff`. Files `BRIEF_NONGOAL_TRESPASS` (delivered code does what a Non-goal forbids) and `BRIEF_GOAL_UNDELIVERED` (PR claims a Goal but ships only enabling code).
2. **N Scope-fidelity Adversaries** — one per selected at-risk Goal, each given exactly ONE Goal, spawned **in isolation** (never batched — the isolation is load-bearing and validated). Each reconstructs its Goal's domain + authoritative basis and checks whether the delivered code serves the outcome across the domain slice this PR's chunk claims, on the authoritative input, before any irreversible step. Files `SURFACE_PARITY_GAP`.

Launch all in one parallel batch. `{brief_path}` = `features/<feature>/brief.md`; `{sibling_plan_paths}` = every OTHER track's `engineering-plan.md` when the feature is tracked, else "none" (required — a PR ships one track's chunk, so without the siblings the adversary judges the diff against Goal clauses another track owns); `{decisions_path}` = `features/<feature>/decisions.md` (**Active-section `Status: bound` entries only** — a `superseded`/`obsolete` entry does not confer launch-acceptable authority and cannot suppress a parity finding); `{additional_examples}` = any accumulated calibration examples from prior invocations' state.

### Route the findings

Merge every role's `findings` array (identical schema).

- **All roles `passed`** → record `brief_conformance: passed`; proceed to Stage 2 with no pre-resolved brief findings.
- **Any `findings_filed`** → each finding is **Class A** (per `principles.md` § Cross-artifact authority order) and enters Stage 2 as a `pre_resolved_hard_finding` personas inherit but **cannot retract**. Class A findings are **exempt from Stage 3's decisions-log-first carry-forward** — a `Status: bound` `decisions.md` entry does NOT drop them (only a brief amendment, or an Active bound entry that explicitly scoped the residual as launch-acceptable, resolves one). They surface in the verdict as blockers.

A parity / trespass finding is **not auto-fixed**: extending domain coverage or moving an irreversible step is a scope change, and Stage 3's Forbidden-fixes rule bars the orchestrator from silently changing the PR's intent. Escalate to the director with the finding's `resolution_paths` (extend coverage in a follow-up chunk, or scope the Goal down in the brief). Malformed output (a finding missing verbatim `brief_quote` or `contradicting_evidence`) → re-spawn only that one role once; persistent malformed output escalates as an internal error.

Record a `Stage 1.5 brief-conformance` block in the audit: feature, Goals selected/skipped, roles spawned, findings by class.

---

## Stage 2 — Persona prosecution (parallel agents, fix-list output)

### Empanel the panel

Convene multiple hostile experts. Use `personas/` files when present (`personas/code-reviewer.md`, `personas/architecture.md`, `personas/security.md`, `personas/testing.md`, project-specific). If absent, synthesize equivalent roles.

**Default panel** (every PR):

1. **Correctness** — compiles, tests pass, types honest, happy path implemented.
2. **Hallucination** — every identifier in the diff exists right now on this branch; extends Stage 1 audit to anything missed.
3. **Invariant** — project's stated invariants (CLAUDE.md, SPEC.md, persona rules, test properties): can a diff-introduced scenario violate them?
4. **Security** — auth/authz bypass, injection, secrets, unsafe blocks, deserialization, path traversal, privilege escalation.
5. **Drift** — does changed code follow existing patterns? New abstractions where existing one would serve? Parallel types alongside old? Dead code?
6. **Test** — for every behavior change: would a test catch the *old* behavior failing? Assertions weakened? Failing-and-fixed test actually testing the fix or masking it? Edge cases?
7. **Scope** — does the diff do what the PR description claims? Unrequested refactors, sneaky behavior changes, speculative features? On feature-scoped PRs, also apply the **Goal-outcome lens**: for the brief Goal(s) this PR delivers, read each Goal for its *intended outcome* (not its mechanism wording, not the PR description's restatement) and verify the delivered code achieves that outcome — performing a Goal's named mechanism on one surface does not satisfy a Goal whose outcome must hold across a domain. This is the concrete-Goal counterpart to the Stage 1.5 adversary (which covers the domain-quantified / authoritative-signal Goals); see § Skill-specific extensions → Goal-outcome premise check.
8. **Factoring** — self-pointers, orphaned clauses, helper-shaped repetition, half-finished refactors, comments paraphrasing the identifier, vestigial vocabulary.

**Per-PR additions:** UI-heavy → add `ui-code-review`. Data/schema-heavy → add `data-engineering`. Perf-sensitive → add `performance`. For small PRs, prune to 3–4 most-relevant from the default 8.

### Spawn agents

**CRITICAL: persona prompts are loaded from the template; they are NOT authored.** This is the single most common skill-compliance defect — the orchestrator drafts a "summary" of what the persona should do, omits the `{skill_specific_extensions}` block, and the entire convergence machinery silently goes dark. If you find yourself writing prose that begins "You are a hostile reviewer…" *without first having Read the template file*, stop — you are doing the wrong thing.

The construction recipe — follow exactly, no shortcuts:

1. **Read** `~/.claude/skills/_review-common/agent-prompt.md` into context.
2. Compute the substitution values listed below.
3. **Read** the persona file (`personas/<persona_name>.md`) so you know it exists and the agent will Read it on demand.
4. Construct the prompt by substituting the bracketed slots in the template verbatim. The `{skill_specific_extensions}` slot is replaced with the entire "Skill-specific extensions" block from this file (the premise interrogation + round-memory tagging text below). The `{skill_specific_preamble}` slot becomes `premise_interrogation: passed | premise_inversions_filed; invocation_number: <N>`. The `{skill_specific_resets_block}` slot is `none`.
5. If `invocation_number > 1`, prepend the `file_diff_report` and `prior_blocker_audit` blocks to the prompt body verbatim, before the `## Your task` section in the template.
6. If the PR is **feature-scoped** (Stage 1.5 ran), prepend the `Stage 1.5 Goal selection` block AND the line `feature_scoped: yes; brief_path: features/<feature>/brief.md; engineering_plan_path: <resolved plan path>` before the `## Your task` section (for a tracked feature, list every track's plan path, comma-separated, with the PR's own track marked) — this is what enables the persona Goal-outcome premise check. If the PR is not feature-scoped, prepend `feature_scoped: no` so personas skip that sub-pass. Also prepend the Stage 1.5 findings into `{pre_resolved_hard_findings}` (Class A; personas cannot retract them).
7. Send. Do not paraphrase. Do not summarize. Do not "skip the boilerplate".

Substitution values:

- `{persona_name}` — the persona being prosecuted as
- `{audit_report_bullets}` — Stage 1 audit (compact bullets, not full YAML; includes `prior_blocker_audit` and `file_diff_report` when `invocation_number > 1`)
- `{pre_resolved_hard_findings}` — anything Stage 1 already raised, **plus every Stage 1.5 brief-conformance finding** (`BRIEF_NONGOAL_TRESPASS` / `BRIEF_GOAL_UNDELIVERED` / `SURFACE_PARITY_GAP`; Class A — personas inherit these but must NOT re-litigate or retract them; a persona may add corroborating detail but the finding stands regardless)
- `{active_critical_pair_subset}` — `P-CLASS-SCOPE, P-FULL-FILE, P-PR-OWNERSHIP, P-PR-COVERAGE, P-PR-CLAIMS, P-PR-BRIEF-PARITY`
- `{target_locator}` — the PR number + branch
- `{how_to_get_it}` — `gh pr diff`, `gh pr view --json title,body`, `git ls-files`, `Read <path>` (paths from changed-files list)
- `{pr_description_or_brief_mapping}` — the PR title + body
- `{skill_specific_extensions}` — see "Premise Interrogation pass" + "Round-memory tagging" below
- `{skill_specific_preamble}` — `premise_interrogation: passed | premise_inversions_filed`; `invocation_number: <N>`
- `{skill_specific_resets_block}` — none (PR review files premise inversions as CRITICAL HARD findings in the normal `findings:` list, not as separate RESETs; there is no short-circuit corroboration tier)

Personas must include `targets_unchanged_file: yes | no` and `regression_risk: yes | no` on every finding when `invocation_number > 1`. The orchestrator uses these tags to apply mechanical filters in Stage 3.

The full diff is small enough to pass inline (gh pr diff output). Changed file *contents* are NOT inlined — agents Read them on demand. Source-of-truth files (CLAUDE.md, SPEC.md, persona files) are referenced by path; agents Read what their persona needs.

Launch all M agents in parallel in a single message, each with `model: "sonnet"` per `_review-common/agent-prompt.md` § Model pin — never inherit the session model; record `persona_model` in the review state.

#### Compliance self-check (mandatory, before launching)

Before sending the persona Agent calls, verify the constructed prompt for each agent contains all of:

- The literal string `Premise interrogation (mandatory` (or the verbatim heading from the extensions block).
- The literal string `Diff-baseline premise check`.
- The literal string `PR-description premise check`.
- If the PR is feature-scoped (Stage 1.5 ran): the literal string `Goal-outcome premise check`, the `feature_scoped: yes` line, AND the `Stage 1.5 Goal selection` block.
- If `invocation_number > 1`: the literal string `file_diff_report` AND the unchanged-file gate text.
- If `invocation_number > 1`: the literal string `prior_blocker_audit` AND the reclassification consistency text.

If any required string is missing, you authored a custom prompt instead of using the template. **Stop and reconstruct from the template.** This check is the first line of defense against the most common failure mode — the rest of the convergence machinery depends on it.

### Skill-specific extensions (substituted into the agent prompt)

> Your work is two passes done in order: **premise interrogation** first, then standard prosecution.
>
> ### Premise interrogation (mandatory — runs before standard prosecution)
>
> PR reviews thrash hardest when findings are filed against premises that don't survive verification. Your job in this pass is to falsify load-bearing premises before generating any other findings. Three sub-passes (the third only on feature-scoped PRs): **diff-baseline** (claims the diff makes about pre-existing repo state), **PR-description** (claims the PR description makes about what the diff does), and **Goal-outcome** (does the delivered code achieve the intended outcome of the brief Goal it claims, not just perform the Goal's mechanism).
>
> #### Diff-baseline premise check
>
> 1. Enumerate every load-bearing claim the diff makes about *pre-existing repo state* — claims of the form "extends the existing X", "hooks into the Y middleware", "reuses Z helper", "follows the W pattern from file:line", "the schema already has column C", "this matches behavior at file:line". Skip claims about what the diff *will* do (those are evaluated in standard prosecution); skip references to files the diff itself adds.
>
> 2. For each claim, run a verification: `Read` the cited file at the cited line; `rg` for the cited identifier; `git log` if the claim is about recent state. Stage 1 audit verified *paths exist*; you are verifying *behavior at those paths matches the claim*. Different checks.
>
> 3. A claim that does not survive verification is a **premise inversion: diff-baseline**. File as a normal finding with severity **CRITICAL HARD**, category **HALLUCINATION**, and prefix the `finding` field with `[premise inversion: diff-baseline]`. The `evidence` field MUST quote both the diff's claim and the actual repo state verbatim with `path:line` anchors.
>
> #### PR-description premise check
>
> 1. Read the PR title and body. Locate every claim about what the diff accomplishes — "fixes the N+1 query in Z", "deduplicates author hydration", "adds rate limiting to W", "removes the legacy X path".
>
> 2. For each claim, verify against the actual diff (`gh pr diff` output). Does the diff actually do what the description says, or does it do something different / partial / additional?
>
> 3. A description claim that does not survive verification is a **premise inversion: pr-description**. File as a normal finding with severity **HIGH HARD**, category **SCOPE**, and prefix the `finding` field with `[premise inversion: pr-description]`. The `evidence` field MUST quote both the description's claim and the contradicting diff hunk verbatim. (P-PR-CLAIMS critical-pair policy applies — descriptions claiming X but diffs doing Y are valid SCOPE findings; descriptions silent about benign Y are not.)
>
> 4. Be calibrated. A premise inversion is "the description says 'fixes the N+1 query in cascadeRewrite' but the diff modifies only seedTestData — the N+1 query is untouched." It is NOT "the description's wording is imprecise" or "the description omits a minor side effect."
>
> #### Goal-outcome premise check (feature-scoped PRs only)
>
> Runs only when the orchestrator marked this PR feature-scoped and passed you the brief path + the `Stage 1.5 Goal selection` block. The Stage 1.5 gate already ran the per-Goal Scope-fidelity Adversary on the *domain-quantified / authoritative-signal* Goals; this sub-pass covers the **concrete single-surface Goals** the at-risk filter excluded, and re-checks the delivered code against each Goal's *outcome* rather than its *mechanism*.
>
> 1. `Read` `features/<feature>/brief.md` § Goals. For each Goal this PR delivers (per the Goal-selection block / PR description), reconstruct the **intended outcome** — the observable user-facing or system result the Goal commits to. If the Goal is phrased as a *mechanism* ("via an allowlist", "using a dedupe step", "with an LLM pass"), do NOT treat performing that mechanism as satisfying it — reconstruct the outcome the mechanism was meant to produce and check *that*. A reader who takes mechanism words literally-disjunctively (allowlist here, ML there) wrongly acquits code that ships the outcome nowhere whole; that literal reading is the exact miss this check exists to catch.
>
> 2. Verify the delivered diff achieves the reconstructed outcome. Code that performs a Goal's mechanism while the outcome the Goal commits to does not hold is a **premise inversion: goal-outcome**. File as a normal finding with severity **HIGH HARD**, category **SCOPE**, prefix the `finding` field with `[premise inversion: goal-outcome]`, and quote both the brief Goal verbatim and the contradicting diff/code hunk verbatim with `path:line` anchors.
>
> 3. Be calibrated (P-PR-BRIEF-PARITY applies). A finding here is "Goal G commits to outcome O; the diff performs G's mechanism but O does not hold — e.g. the code the PR ships filters dismissed items from the recommendation rows but not from the cross-category sections the same Goal names." It is NOT "the outcome could be phrased better", and it is NOT a domain member a *different* chunk owns (scope to the slice this PR's chunk claims per the EP Brief-mapping). If the outcome holds for this PR's slice, file nothing here.
>
> A goal-outcome premise inversion is **Class A** — it is not retracted by a `Status: bound` `decisions.md` entry; only a brief amendment or an Active bound entry explicitly scoping the residual as launch-acceptable clears it.
>
> If after honest interrogation no premises invert, output `premise_interrogation: passed` and proceed to standard prosecution. Do not invent premise-inversion findings to look thorough — false positives waste user invocations the same way false negatives ship broken code.
>
> ### Standard prosecution
>
> Proceed with normal persona prosecution per the standard agent prompt. Premise-inversion findings filed in the premise-interrogation pass are already in your fix list at their flagged severity; standard prosecution adds non-premise findings.
>
> ### Round-memory tagging (when invocation_number > 1)
>
> If `invocation_number > 1`, the orchestrator passes a `file_diff_report` and `prior_blocker_audit` into your prompt. Every finding you file MUST include two additional fields:
>
> - **`targets_unchanged_file: yes | no`** — `yes` if the finding's `path_or_section` resolves to a file in the report's `unchanged` list.
> - **`regression_risk: yes | no`** — `yes` if the finding cites lines within hunks added since `last_head_sha` AND the prior_blocker_audit lists a now-resolved blocker on overlapping span.
>
> If `targets_unchanged_file: yes`, the finding's `finding` body MUST satisfy BOTH:
>   - **(a)** names a specific defect class the prior invocation's personas missed (not "the file is wrong" — names the missed class), AND
>   - **(b)** names why the prior lens did not catch it (new persona running this invocation? new evidence from a `modified` file interacting with this `unchanged` file? new ground-truth fact uncovered in this invocation's audit?).
>
> Findings tagging `targets_unchanged_file: yes` without (a)+(b) are auto-retracted by the orchestrator in Stage 3.
>
> If `regression_risk: yes`, the orchestrator will downgrade severity (CRITICAL → HIGH → MEDIUM → LOW → drop) unless your `finding` body names a *specific failure mode the new code creates* (named scenario where executing it produces a broken result). Default behavior is downgrade; you have to earn the original severity.
>
> ### Prior-blocker classification consistency
>
> The `prior_blocker_audit` may list `reclassification_pending` entries — paths/spans that previously had a different blocker class (e.g., previously `OPEN_QUESTION`, you might now be tempted to file `STABLE_DISAGREEMENT`). If you file a finding that produces a blocker class on a span listed in `reclassification_pending`, you MUST include in the `finding` body a one-sentence justification grounded in repo state that changed since the prior invocation (new commit, file change, new evidence). Without justification, the orchestrator downgrades the new classification to `OPEN_QUESTION` so the user arbitrates.
>
> The audit may also list **re-prosecuted-on-resolved-span** entries — spans where a prior invocation's user_decision is on record. When you file a finding on such a span, your `finding` body MUST acknowledge the prior decision and explain whether your finding challenges that decision (and on what new ground) or addresses a different dimension. Treating the prior decision as nonexistent is the documented failure mode this rule prevents. The user already arbitrated; the machinery's job is to surface their pick, not erase it.

---

## Stage 3 — Orchestrator decision

Stage 3 runs in the main thread.

### Apply Stage 1 mechanical fixes

Already done at end of Stage 1. Confirm working tree matches.

### Filter against round-memory tags (when invocation_number > 1)

Apply BEFORE critical-pair filtering. Findings carry two tags from Stage 2:

1. **`targets_unchanged_file: yes`** — finding's `path_or_section` resolves to a file in the `unchanged` list of `file_diff_report`. Auto-retract UNLESS the finding's body explicitly satisfies BOTH:
   - **(a)** names a specific defect class the prior invocation's personas missed (not "the file is wrong" — names the missed class), AND
   - **(b)** names why the prior lens did not catch it (new persona running this invocation? new evidence from a `modified` file interacting with this `unchanged` file? new ground-truth fact uncovered in this invocation's audit?).

   If both present, keep at filed severity. If either missing, retract with note `RETRACTED: targets unchanged file without (a)+(b) justification`.

2. **`regression_risk: yes`** — finding's cited lines are within hunks added since `last_head_sha` AND `prior_blocker_audit` lists a now-resolved blocker on overlapping span. Apply mechanical severity downgrade: CRITICAL → HIGH → MEDIUM → LOW → drop. Skip the downgrade if the finding's body names a *specific failure mode the new code creates* (named scenario where executing the new code produces a broken result). Default is downgrade; the persona has to earn the original severity.

Record retractions and downgrades in the verdict's `### Retractions` block with the rule that fired. If `force_push_detected: true`, do NOT auto-retract — line numbers from the prior state file are stale; treat all findings as round 1 for the purpose of round-memory filtering, but still surface the file-hash-unchanged signal as a diagnostic.

### Filter against critical-pair policies

For each finding from each persona:
- Contradicts an active critical-pair policy → retract. Note in verdict.
- Duplicates a Stage 1 hard finding already mechanically fixed → retract.
- Otherwise → keep.

### Structural Sweep (unseeded — runs even on a zero-finding invocation)

Runs after critical-pair filtering and **before the Class Sweep** (so the Class Sweep can fold an already-walked universe instead of re-walking it). Skipped when `baseline_red == true` (Stage 2/3 never ran). Per `~/.claude/skills/_review-common/structural-sweep.md` — read it for the mechanism, agent template, merge, and state/verdict schema. This section fills the PR slots.

**Why it is here.** The Class Sweep below is seeded from surviving findings and cannot discover a class nobody filed — so a defect class no persona noticed is invisible to the whole pipeline, with no compliance check firing, because there was no seed to be incomplete about. This is the last gate before merge, so an unfiled class here reaches real code. The stage runs regardless of the invocation's finding count.

**Universes at this layer** (all three bounded by PR ownership — in-diff plus blast radius; an out-of-ownership member is filed `OPEN_QUESTION`, never silently swept, exactly as the Class Sweep's ownership rule requires):

- **Universe L — guard liveness.** Members: every guard, assertion, validation check, early return, or invariant the diff adds or changes. The question: is there a reachable state in which this can never hold — a dead guard, an always-false branch, a check whose predicate is forced elsewhere? **Its mandatory trace procedure applies, over code:** resolve every term the guard references to its definition, and find every path that sets it, before judging. A guard judged by reading only its own line is not judged.
- **Universe T — changed-surface test coverage.** Members: every public surface the diff adds or changes (exported function, endpoint, resolver, mutation, hook, CLI flag, schema field). The question: does the diff include a test exercising the *changed behavior* — judged on the assertion, not on a file existing? Closures: a test in the diff asserts it; an existing named test already covers it and the diff does not change what it asserts; the surface is a pure re-export or rename with no behavior change.
- **Universe Z — mutation authorization.** Members: every mutation, write path, or state-changing operation the diff adds or changes. The question: does it perform authentication and authorization in **this project's established pattern** — read that pattern from the project's own `CLAUDE.md` and a sibling resolver, never from a generic notion of auth — before it mutates? A GAP is HIGH by default. This universe exists because auth is the canonical individually-obvious, collectively-forgotten check: a reviewer reads a new mutation, sees the surrounding pattern, and assumes it applies.

**Merge:** every GAP becomes a same-round finding at the sweep-judged severity, routed through the same round-memory and critical-pair filters and the same ownership bound as a persona finding.

### Class Sweep

Runs after the Structural Sweep and after critical-pair filtering (so a category whose only seed was retracted is not swept), before Detect cross-persona disagreement / Consolidate. Skipped when `baseline_red == true` (Stage 2/3 never ran). Pass `{structural_sweep_universes_run}` from the stage above so a widened peer-set overlapping a walked universe is folded in rather than re-walked. Per `~/.claude/skills/_review-common/class-sweep.md` — read it for the mechanism, sweep-agent template, merge, and state/verdict schema. PR personas file one instance of a recurring class per invocation (one un-updated callsite of a touched identifier, one mutation missing the guard the diff adds elsewhere, one behavior-change hunk with no test) and the siblings leak out one per re-invocation otherwise.

**Procedure (per the shared file), with these PR-layer slots:**

- **Seed grouping.** Group surviving Stage 2 findings by `class`. Every distinct `recurring_category` (and any `propagated_identity` with a >1 peer-set — a renamed/retired identifier across its callsites is the canonical PR case) gets one sweep agent, `model: "sonnet"`; genuine singletons are recorded `singleton: true` with no agent.
- **`{peer_set_definition}`** — the PR's repeated units: every changed file / hunk in the diff, every callsite of a touched identifier, every mutation or handler the diff adds or edits, every behavior-changing hunk (for the missing-test class). Name the specific unit the seed's `peer_set` points at.
- **`{artifact_access}`** — `gh pr diff` + Read the changed files at branch HEAD. For `propagated_identity`, grep the token across the repo.
- **`{layer_notes}`** — **PR ownership bounds the sweep (`P-PR-OWNERSHIP`).** Siblings are in scope only when they live in a file the PR touches OR in the **blast radius** of a touched identifier (an untouched caller of a function the diff changed that must update too). A sibling in a completely untouched file outside the blast radius is NOT this PR's burden — record it as `OPEN_QUESTION`, not a fix. Class A parity/trespass siblings (`SURFACE_PARITY_GAP` / `BRIEF_NONGOAL_TRESPASS` / `BRIEF_GOAL_UNDELIVERED`) are escalated, not auto-fixed.
- **Merge.** Dedup siblings against the Stage 2 pool by `(class, path:line)`; route new siblings through the round-memory-tag + critical-pair retraction (same filter the seeds got) before folding them into Consolidate. Record the `class_sweep` block in the state file / verdict metrics.

Skip the sub-pass (record `class_sweep.ran=false`) only when zero sweep-eligible categories exist among the surviving findings.

### Detect cross-persona disagreement

For each diff span (path + line range), collect surviving findings.
- Two personas propose contradictory fixes for the same span → label `STABLE_DISAGREEMENT`. Do not auto-apply. Surface options to user.

Common: factoring persona says "extract helper"; drift persona says "match existing inline pattern." User picks.

### Consolidate non-conflicting fixes

Deduplicate findings across personas (same defect flagged by multiple → merge, attribute to all). Group by:
- Target file
- Class (per Class > line — apply to every instance in the universe, which now includes the siblings the Class Sweep above promoted into the finding pool, not just the named line)

Apply fixes in a single editing pass across all touched files, ordered by:
1. Severity (CRITICAL → HIGH → MEDIUM → LOW)
2. Within severity: by file, then by line (ascending)

**Forbidden fixes:**
- Weakening tests, types, or assertions to make gates green → escalate as `OPEN_QUESTION`.
- Changing the PR's intent to sidestep a hard problem → escalate as `OPEN_QUESTION`.
- "Leaving details for follow-up" — fix in this PR or escalate.

### Post-fix premise verification

Refactor PRs (and any PR whose fix list rewrites comments, docstrings, schema directives, or plan prose) carry a specific failure mode: the fix itself can introduce false claims about behavior. Examples observed in prior invocations:

- A schema column comment rewritten to drop chunk-attribution that now claims "ensures single-session semantics" when no unique constraint exists.
- A carve-out kept on the basis of "this comment explains the unique constraint" — but the directive is `@@index` (non-unique).
- A docblock narrowed to drop one chunk reference and now describes a test scope different from what the test actually covers.

Gates do NOT catch these — the code compiles, the tests pass, but the prose asserts something the code doesn't do. The next invocation catches it via max-suspicion re-prosecution, costing the user a full round.

Mechanism: `~/.claude/skills/_review-common/orchestrator.md` § Post-fix premise verification. The PR layer scopes and verifies as follows.

#### What is in scope

For each file Stage 3 modified, identify the lines *added or rewritten in the prose layer* — not lines where only logic changed. Run `git diff --unified=0 <pre-stage-3-tree-ish>..HEAD -- <path>` per edited file and collect the added-line set. Keep lines sitting in:
- Inline comments (`//`, `#`, `--`, etc.)
- Block comments / docstrings (`/** */`, `"""`, `'''`, `<!-- -->`)
- Schema directive prose (Prisma `///` docs, `@@index([...])` trailing comments, SQL `COMMENT ON ...`)
- Markdown / plan-document prose (any added paragraph in `*.md`)

Pure logic, identifier renames, and JSON config edits are out of scope here.

#### How verification runs

Read each in-scope line with ~5 lines of surrounding context and ask: does this make a claim about behavior, scope, constraint, or cross-reference that a reader would expect to be true of the current repo? Judgment, not a keyword filter — a claim needs no particular verb.

- "Hero blocks share the same identifier across replicas." — behavior; verify the emission code preserves it.
- "Scope: src/ and tests/." — scope; verify the guard's actual reach.
- "See `replica_item_emitter.rs:42` for the canonical pattern." — cross-reference; read the cited line.
- "The unique constraint on (userId, categoryId) prevents duplicate active sessions." — constraint; grep the schema for it.

Skip section headers, pure stylistic edits, and commentary that asserts no current-repo fact ("this pattern is common in async Rust").

Match the check to the claim's shape: grep DDL for a constraint, trace callers/callees for a behavior, verify actual coverage for a scope claim, read the cited line for a cross-reference.

A claim that does not survive is a `FIX_INTRODUCED_PREMISE_INVERSION` blocker. **Do NOT commit** — leave the tree dirty so the user sees both the fix and the lie it introduced. Emit:

```
FIX_INTRODUCED_PREMISE_INVERSION at <path:line>:
  fix introduced: "<verbatim quote from the rewritten line>"
  claim type: constraint | behavior | scope | cross-reference
  verification failed: <which check failed and what was expected>
  repo evidence: <verbatim grep / Read output proving the lie>
```

If all claims survive verification, proceed to gate re-run. Record one attestation in the `Compliance attestations` block of the verdict:

> Post-fix premise verification: <count> in-scope lines reviewed; <count> claims identified; <count> survived; <count> filed as FIX_INTRODUCED_PREMISE_INVERSION.

This pass exists because Stage 2 personas catch premise inversions in the *input* artifact (the diff as filed) but no machinery catches premise inversions the *fix* introduces. Stage 3's own edits are the blind spot. LLM judgment over a bounded line set is cheap relative to a full re-prosecution invocation; the cost asymmetry is the justification.

### Same-round focused re-prosecution on rewritten code/prose

PR reviews thrash hardest when round-N orchestrator fixes become round-N+1 prosecution targets — the user resolves the blockers, the orchestrator applies fixes, and the next invocation's personas surface fresh defects in the orchestrator-rewritten code (a security finding on a rate-limiter helper the orchestrator just added; a test finding on assertions the orchestrator just rewrote). Post-fix premise verification above catches *false claims* the fix introduced; this sub-pass catches *new persona-class defects* the fix introduced.

Bounded: exactly one re-pass on the orchestrator's own diff hunks, never recursive.

#### Skip conditions

Skip this sub-pass when ALL three are true:
1. Stage 3 applied zero fixes (orchestrator-applied fix count == 0; only Stage 1 mechanical fixes ran).
2. Post-fix premise verification falsified-claim count == 0.
3. No new commits were created by Stage 3 (`git rev-parse HEAD` matches pre-Stage-3 sha).

If any of the three is non-zero, the sub-pass is mandatory.

#### Procedure

1. **Identify the orchestrator's diff hunks.** Run `git diff --unified=3 <pre-stage-3-tree-ish>..HEAD` and capture per-file added-line spans. These are the hunks Stage 3 wrote on top of the original PR diff.

2. **Spawn focused re-pass agents.** Spawn one focused agent per persona from the original Stage 2 panel, scoped to the diff hunks only. Use the same agent template (`~/.claude/skills/_review-common/agent-prompt.md`). All substitutions carry over verbatim from the original Stage 2 spawn; the only changes are:
   - `{audit_report_bullets}` is augmented with a "Diff hunks under review" block listing each (path, line range, verbatim added text) for the orchestrator's edits.
   - `{skill_specific_extensions}` gets a HIGH/MEDIUM filter prepended: "Filter findings to severity HIGH or MEDIUM only — LOW residuals are out of scope. Skip the premise-interrogation passes (already run on the original diff and on rewritten prose by Post-fix premise verification). Focus on persona-class defects in the orchestrator's edits: did the rate-limiter the orchestrator added introduce a security regression? Do the orchestrator's rewritten test assertions actually catch the original failure mode? Does the rewritten error-handling preserve the original control-flow contract?"
   - `{skill_specific_preamble}` is `re_pass: focused_diff_hunks; invocation_number: <N>; original_pass_completed: yes`.

   **Omitting any other substitution under-constrains the persona** — the agent loses the persona file pointer, the audit report, the round-memory tags, etc. The HIGH/MEDIUM filter is a refinement of an otherwise-complete prompt, not a replacement for it.

3. **Filter re-pass fix lists through Stage 3 round-memory tags + critical-pair retraction.** Apply the same filtering pipeline as the original Stage 2 → Stage 3: round-memory tag filtering (auto-retract findings tagging `targets_unchanged_file: yes` without (a)+(b) justification; downgrade `regression_risk: yes` findings without a named failure mode), then critical-pair policies. Same procedure, applied to the smaller diff-hunk-scoped finding set.

4. **Detect cross-persona disagreement on diff-hunk spans.** If two re-pass personas file contradictory fixes on the same diff hunk, label `STABLE_DISAGREEMENT` and persist to blockers — do NOT auto-apply either.

5. **Apply surviving fixes as additional Stage 3 edits.** Use the same Consolidate Non-Conflicting Fixes procedure (Group by class > line; apply in severity order). Re-pass fixes go on top of Stage 3's edits — the orchestrator amends the in-progress commits or adds an additional fix-the-fix commit, depending on whether Stage 3 has already committed.

6. **Re-run Post-fix premise verification on the new edits.** The re-pass writes code or prose, so the premise verification machinery applies again to anything that asserts a claim about behavior.

7. **Re-run gates.** Already on the path — Stage 3 re-runs gates next anyway. The re-pass fixes ride on the same gate run; no additional gate invocation needed.

8. **Record metrics.** Update the verdict template's compliance-attestations and Stage 3 fixes blocks with: re-pass agents spawned, re-pass findings raised, re-pass findings retracted (round-memory tags + critical-pair), re-pass STABLE_DISAGREEMENT spans, re-pass fixes applied, re-pass falsified claims (from the second premise verification).

The cost asymmetry justifies this: spawning M focused agents on bounded diff hunks is cheap relative to the next invocation's full re-prosecution that the user has to trigger by re-invoking the skill.

### Re-run gates after fix application

```bash
<project compile cmd>
<project lint cmd>
<project test cmd>
<project-specific cmd>
```

Record `Gates after fixes` per gate.

If any gate is RED:
- Identify which fix caused the regression (stash incrementally, or `git diff` working tree against pre-Stage-3 state).
- Emit `FIX_INTRODUCED_REGRESSION` blocker per failing gate, naming the offending fix.
- Do NOT commit; leave working tree dirty for user inspection.

If all GREEN: proceed to commit.

### Commit fixes in logical chunks

Group fixes into logical commits (not one megacommit):
- One commit per class addressed (e.g., "fix: rename retired identifier across user-facing paths").
- One commit per category if classes are too granular (e.g., "fix: security findings on auth middleware").

Commit message format:

```
fix: <one-line root-cause description>

<why this was wrong; reference findings from Stage 2 panel>
```

Push when all fixes for the invocation are committed and gates are green locally:

```bash
git push
```

### Execute the PR test plan and tick it off (mandatory)

The PR description's `## Test plan` is the author's own checklist of what proves the change works. A review that does not run it has verified only the project's generic gates — which routinely miss the PR-specific surface: a CLI/script the diff adds, the *other* workspace's suite (`cd mobile && npm test` when the diff is backend-only, and vice versa), a `bash -n` parse, an operator-verification exit-code check. Run **every** item against the pushed post-fix HEAD. Re-running the generic gates is NOT a substitute — green gates and an un-run test plan is a half-finished review.

1. Parse the `## Test plan` from `gh pr view --json body`. No test-plan section → record `test_plan: none` and proceed to classify.
2. Run each item's command(s) verbatim. Items overlapping the gate re-run (typecheck/lint/full test) are already satisfied — run the remaining PR-specific ones. Source `.env` when an item needs it (the run-gates-with-env-sourced rule), e.g. an item that invokes a script reading `DATABASE_URL`.
3. Disposition each item:
   - **Passes** → tick it.
   - **Fails** → a defect the review must resolve, not annotate around. Fold a fix into the Stage 3 fix set (commit it, re-run gates — the test plan then re-runs against the new HEAD), OR escalate as a blocker (`FIX_INTRODUCED_REGRESSION` if a Stage 3 fix broke it, else `OPEN_QUESTION`) and leave the box unticked.
   - **Passes but the item's stated count drifted** (e.g. "(44 pass)" but the suite now reports a different number because the PR changed the test set) → correct the count to the observed value.
4. Once every item passes against the final HEAD, update the PR body: tick each `- [ ]` → `- [x]`, correct drifted counts, annotate an item with the observed evidence where it adds signal (an exit code, a count), and append `_Test plan executed during /review-pr-v2 (invocation N, HEAD <sha>)._`. Fetch the body to a temp file (`gh pr view <N> --json body --jq .body > <tmp>`), edit the checkboxes/counts with Read/Edit, push back with `gh pr edit <N> --body-file <tmp>` — **never reconstruct the body inline** (transcription drift clobbers the author's prose).
5. Record a `Test plan` line for the verdict: items run / passed / counts corrected / failures escalated.

A test-plan item that fails is the most direct evidence a PR is not ready — weight it like a red gate. Never tick a box for an item you did not actually run, and never post the verdict with runnable test-plan items left unexecuted.

### Classify remaining unresolved findings

See `~/.claude/skills/_review-common/blocker-classes.md` for the full registry. Active for PR review: `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `POLISH_PLATEAU`, `FIX_INTRODUCED_REGRESSION`, `FIX_INTRODUCED_PREMISE_INVERSION`, `BASELINE_RED`, `REPO_STATE_DRIFT`, `REMEDIATION_INCOMPLETE`, `DECISIONS_PROVENANCE_GAP`, and (feature-scoped PRs, from Stage 1.5) `BRIEF_NONGOAL_TRESPASS`, `BRIEF_GOAL_UNDELIVERED`, `SURFACE_PARITY_GAP` — the last three are Class A and were already exempted from Priority-1 retraction above. `REMEDIATION_INCOMPLETE` and `DECISIONS_PROVENANCE_GAP` are filed by the Prior-blocker consistency check's remediation-completeness questions and are exempt from Priority-2 carry-forward (and, for the latter, from Priority 1) — see `_review-common/blocker-classes.md` § Remediation-completeness.

**Decisions-log-first carry-forward (Priority 1, when feature dir touched).** Many PRs implement chunks from a `features/<feature>/` directory; that feature's `decisions.md` is the project's durable arbitration record and outlasts PR-scoped state. Determine whether this PR is feature-scoped:

1. Determine feature-scope exactly as Stage 1.5 did (reuse its `<feature>`): any path matching `features/<feature>/(brief|engineering-plan|decisions|implementation/.*)\.md`, OR a commit-message body citing `features/<feature>/`, OR the PR description linking a feature directory.
2. For each detected `<feature>`, `Read` `features/<feature>/decisions.md` if it exists. **Read only the `## Active (bound)` section** when the log uses the Active/Archived split; in a flat log, consider only entries whose `Status:` is `bound`.
3. **Class-A findings are exempt — do NOT run them through the scan.** A Stage 1.5 brief-conformance finding (`BRIEF_NONGOAL_TRESPASS` / `BRIEF_GOAL_UNDELIVERED` / `SURFACE_PARITY_GAP`) or a persona `[premise inversion: goal-outcome]` finding is Class A per `principles.md` § Cross-artifact authority order; a `Status: bound` `decisions.md` entry cannot drop it (a bound entry that *itself* trespasses the brief is the defect, not a shield). Only the Class-B/C findings below are eligible for retraction.
4. For each surviving **Class-B/C** finding, scan the Active bound entries for ones where ALL of:
   - The entry's `Decision:` subject substring-matches the finding's `path_or_section` (matching identifier, file path, or quoted phrase fragment ≥4 words from the finding body).
   - The entry's `Status:` is `bound` (case-insensitive) — NOT `superseded`/`obsolete` (those live in `## Archived` and never arbitrate, per `principles.md` § What counts as a bound entry).
   - The finding contradicts the bound resolution (the persona is filing a fix that would *undo* the bound decision, or the finding asserts the opposite of what was bound).
5. When all three match, **drop the finding** with note `RETRACTED: contradicts bound decisions.md entry "<entry subject>" (<entry date>); entry's Why: "<verbatim Why paragraph, capped at ~200 chars>"`. The verdict's `### Retractions` block surfaces the retraction so the user sees their prior arbitration was honored.

This priority exists because `decisions.md` is the project's converged memory across sessions and survives PR rotation, cache wipes, and machine swaps — `recently_resolved_blockers` only holds for `carry_forward_until_invocation + 2` rounds and resets on every state-file loss. Authority order: `decisions.md` > `recently_resolved_blockers` > prior verdict text.

If the PR is NOT feature-scoped (no `features/<feature>/` paths touched, no feature reference in commits or PR body), skip Priority 1 and proceed directly to Priority 2 below.

**Prior-blocker classification consistency (Priority 2, mandatory for all PRs).** For every blocker class assignment, check the `prior_blocker_audit` from Round Memory:

- If the same `path_or_section` had a different blocker class in a prior invocation AND the persona did not provide a one-sentence justification grounded in repo state that changed since the prior invocation (new commit, file change, new evidence), **downgrade the new classification to `OPEN_QUESTION`**. The user arbitrates which classification stands.
- **Surface prior decision context in the rendered blocker.** When a blocker is filed on a `path_or_section` that has a matching entry in `recently_resolved_blockers` (from this invocation's state load), the rendered blocker line MUST include the prior decision inline so the user sees their prior rationale next to the new prosecution. Format:
    `[<CLASS>] <path:line> — <new finding>`
    `   prior decision (invocation <M>): <user_decision>`
    `   re-prosecuted because: <current_reclassification_justification>`
  This breaks the "user re-arbitrates the same decision blind" thrash by making the prior pick visible at decision time, not buried in summary text.
- Record `prior_classification: <old>; current_classification: <new>; justification: <none | one sentence>` in the rendered blocker line.

This rule exists because invocation-N may classify a defect `STABLE_DISAGREEMENT` (forcing the user to pick between two persona fixes), and invocation-N+1 may then re-classify the same span `OPEN_QUESTION` (forcing the user to *answer a question* about something they already picked between). The state file is the project's converged memory; the orchestrator must consult it before re-prosecuting a class flip.

### Persist state file (before rendering verdict)

State file persistence runs BEFORE the verdict comment is posted, not after. Rationale: the verdict comment is the visible artifact users see; if it gets posted but state-file write is skipped (or silently never executed), the next invocation has no memory and the convergence machinery is dark for the next round. Posting the verdict last makes it dependent on the work being done, not a polish step that gets forgotten.

Write the state file to `~/.claude/cache/review-state/<repo-slug>__pr-<N>.json` using the **Write** tool (NOT shell redirection — file I/O via dedicated tools per the global rule). If the parent directory does not exist, `mkdir -p ~/.claude/cache/review-state` first.

State file contents:

- `invocation_number` ← the invocation just completed (N+1)
- `last_review_at` ← current UTC timestamp (ISO 8601)
- `last_verdict` ← the verdict you are about to render (`APPROVED` or `NEEDS_USER_INPUT`)
- `last_head_sha` ← `git rev-parse HEAD` (post-fix-commit if any commits applied)
- `last_diff_files` ← rebuilt from current diff: each path with its current `git rev-parse HEAD:<path>` blob sha
- `prior_blockers` ← current invocation's unresolved blockers (each with `blocker_class`, `path_or_section`, `summary`, `raised_in_invocation = N+1` for newly-raised, or carried-forward `raised_in_invocation` for ones still open; and `current_reclassification_justification` if this invocation reclassified the blocker from a prior class)
- `recently_resolved_blockers` ← per the rules below

When persisting `recently_resolved_blockers` for the next invocation:

- For each blocker in this invocation's `prior_blocker_audit` marked `resolved`: write a `recently_resolved_blockers` entry with `blocker_class_when_resolved`, `path_or_section`, `summary`, `resolved_in_invocation = <this N>`, `user_decision` (extracted per the capture priority defined in the state-file schema), and `carry_forward_until_invocation = <this N> + 2`.

- Carry forward unexpired entries from the prior state's `recently_resolved_blockers`: copy each entry where `carry_forward_until_invocation >= <this N+1>`. Drop entries where it has expired.

- For new blockers raised this invocation that share `path_or_section` with a `recently_resolved_blockers` entry: this is a re-prosecution of a resolved span. The orchestrator's classify step (above) MUST surface the prior decision when rendering the blocker.

Persist regardless of verdict. APPROVED still gets written so a re-invocation after additional commits sees `invocation_number > 1` and applies round-memory gates correctly.

If the state file write fails (disk full, permission error), surface the error to the user IMMEDIATELY and stop — do NOT post the verdict. A verdict without a corresponding state file is worse than no verdict; it makes the next invocation think there's no prior history when there is.

### Compliance self-check (mandatory pre-verdict gate)

Before posting the verdict, verify the convergence machinery actually executed. The orchestrator runs through this checklist explicitly. Any "no" answer means a step was skipped — back up and run it before posting.

- [ ] **Did Round Memory load run?** Was the state file Read attempted? If `invocation_number > 1`, was the `file_diff_report` computed and emitted in the audit? Was `prior_blocker_audit` populated?
- [ ] **If state was reconstructed, did the reconstruction path fire?** When the state file was missing but PR comments implied prior verdicts, was the reconstruction path entered, were prior blockers extracted from the most recent verdict body, was `last_diff_files` rebuilt (or marked empty with `force_push_detected: true`), and was `state_source: reconstructed_from_pr_comments` recorded in the audit?
- [ ] **Did Stage 1.5 run when the PR is feature-scoped?** If any `features/<feature>/` path was touched (or a commit/PR-body cited a feature) AND `features/<feature>/brief.md` exists: was the at-risk-Goal selection recorded, was the Brief-conformance Prosecutor spawned, was one Scope-fidelity Adversary spawned per selected at-risk Goal (in isolation, never batched), and did every filed `SURFACE_PARITY_GAP` / `BRIEF_NONGOAL_TRESPASS` / `BRIEF_GOAL_UNDELIVERED` carry verbatim `brief_quote` + `contradicting_evidence`? A feature-scoped PR whose audit says `brief_conformance: passed` with zero adversaries spawned is a red flag — either no at-risk Goal was touched (state why) or the gate was skipped. If NOT feature-scoped, `brief_conformance: n_a` is correct.
- [ ] **Did persona prompts use the template?** For each persona Agent that was launched, can you point to the moment you Read `~/.claude/skills/_review-common/agent-prompt.md` and the moment you substituted the slots? If you cannot, you authored a custom prompt and the convergence machinery never reached the personas.
- [ ] **Did personas honor the premise-interrogation passes?** Each persona's output should contain either `premise_interrogation: passed` OR one or more findings prefixed `[premise inversion: diff-baseline]` / `[premise inversion: pr-description]`. If neither appears in any persona's output, the prompt did not include the extensions block.
- [ ] **Did `invocation_number > 1` trigger round-memory tagging?** Each finding from each persona should carry `targets_unchanged_file` and `regression_risk` fields when invocation > 1. Zero findings carrying these tags = personas did not receive the round-memory preamble.
- [ ] **Did the round-memory tag filter actually fire?** If `invocation_number > 1` and Round Memory reported any unchanged files, the verdict's "Round-memory retractions" line should be non-zero OR there should be an explicit explanation why none of the findings matched unchanged-file criteria.
- [ ] **Did the classification step consult prior_blocker_audit AND recently_resolved_blockers?** If any prior blocker was carrying-forward or reclassification-pending, the verdict's "Prior-classification downgrades" line should reflect it. If any new finding lands on a span that appears in `recently_resolved_blockers`, the rendered blocker line MUST include the prior `user_decision` and `current_reclassification_justification`.
- [ ] **Did post-fix premise verification run?** If Stage 3 edited any comment / docstring / schema directive / plan prose, did the orchestrator enumerate the in-scope added/rewritten lines, apply LLM-judgment claim identification (NOT a keyword pre-filter), verify each identified claim against the repo, and record `<lines reviewed>/<claims identified>/<survived>/<inverted>` for the verdict attestation? An attestation that says "0 claims identified" on a Stage 3 that rewrote multiple prose lines is a red flag — re-run with closer attention.
- [ ] **Did the Structural Sweep run every applicable universe?** `structural_sweep.ran` is true unless `baseline_red`; `universes_run` + `universes_skipped` + `universes_inherited_clean` accounts for all three PR universes (L guard liveness, T changed-surface tests, Z mutation authorization); every run universe recorded `members_enumerated`, a non-empty `cells` list, and a non-empty `sections_read`; every Universe-L cell carries a non-empty `traced` field (a cell judged on the guard's own line alone is unjudged — re-run that universe); out-of-ownership members were filed `OPEN_QUESTION` rather than silently swept; and every GAP appears in the fix set / a commit / a blocker. **This check is independent of the invocation's finding count** — a zero-finding invocation that skipped the stage is non-compliant, which is exactly the case it exists for. This is the last gate before merge, so an unfiled class here ships.
- [ ] **Did the Class Sweep run for every recurring category?** For every surviving Stage 2 finding tagged `class_notion: recurring_category` (or `propagated_identity` with a >1 peer-set), was one sweep agent spawned per distinct class, did each record a `peer_set_size` and non-empty `swept_clean` (instances with empty `swept_clean` on a multi-member peer-set = the diff/blast-radius was not walked; re-run that agent), were siblings bounded by PR ownership (in-diff or blast-radius; out-of-ownership siblings filed as `OPEN_QUESTION`, not silently swept), and does every surviving sibling appear in the fix set / a commit / a blocker? A surviving `recurring_category` seed with `sweep_agents_spawned: 0` means the sub-pass was skipped — run it before posting.
- [ ] **Did every sweep agent perform the peer-set challenge?** (`class-sweep.md` § The sweep, Method step 1.) Each category must record a non-empty `bare_invariant`, both `peer_set_handed` and `peer_set_walked`, and an explicit `peer_set_widened` flag with a justification when true. A `bare_invariant` that merely restates the seed's wording, or a `peer_set_walked` copied from `peer_set_handed` with no evidence the supertype question was asked, means step 1 did not run — re-run that agent. This matters because a faithfully-walked *narrow* peer-set reports clean while leaving the class open, and that failure is invisible in the instance counts. At this layer the widened set is still bounded by PR ownership: widen the *invariant*, then clip to in-diff plus blast radius, and file out-of-ownership members as `OPEN_QUESTION` exactly as the existing ownership rule requires.
- [ ] **Did same-round focused re-prosecution run when triggered?** If ANY of Stage-3-fix-count > 0, falsified-claim-count > 0, or HEAD-changed is true, the re-pass is mandatory: focused agents spawned on the orchestrator's diff hunks, all template substitutions inherited from Stage 2, findings filtered through round-memory tags + critical-pair, fixes applied + post-fix premise verification re-run on the new edits. The verdict's "Same-round focused re-prosecution" line should reflect agents-spawned + findings-raised + fixes-applied. A line that says "skipped" while Stage 3 wrote fixes is a red flag.
- [ ] **Did Priority 1 decisions-log-first carry-forward fire when feature-scoped?** If the diff touches `features/<feature>/`, OR commit messages cite a feature, OR the PR description links to a feature: was `features/<feature>/decisions.md` Read, were findings checked against `bound` entries, were contradicting findings dropped with verbatim citation in the verdict's `### Retractions` block? An attestation that says feature-scoped: yes but checked: 0 is a red flag — either the consultation didn't run or the feature dir has no decisions.md (in which case checked: 0 is honest, but the attestation should say so).
- [ ] **Did the PR test plan get executed and ticked off?** If the PR description has a `## Test plan`, was every item run against the final HEAD, were passing boxes ticked via `gh pr edit --body-file`, were drifted counts corrected, and were failing items either fixed in-PR or escalated as blockers? A verdict posted with runnable test-plan boxes still unchecked — or ticked without actually running the item — is a SKILL.md violation. If the PR has no test plan, record `test_plan: none`.
- [ ] **Did the remediation-completeness questions run on every `resolved` prior blocker?** The Prior-blocker consistency check answers *closed?*; the two further questions answer *swept?* and *recorded?*. On `invocation_number > 1`, `remediation_completeness` must hold one entry per prior blocker, each with a non-empty `coupled_sites_checked` and an explicit `decisions_entry` (a heading, `none` with its class, or `n/a — not feature-scoped`). An entry marked `resolved` with an empty `coupled_sites_checked` answered only the first question — a one-line fix at the cited line with every sibling call site untouched presents exactly that way — so re-run it. Every `REMEDIATION_INCOMPLETE` / `DECISIONS_PROVENANCE_GAP` filed must appear in the verdict and must NOT have been dropped by carry-forward.
- [ ] **Did Persist state file run?** Was the state file actually Written? Capture the `path` and the `sha256` (or word count + first 80 chars hash via Read after write) so the verdict template's "State persisted" attestation line is honest, not invented.
- [ ] **Will the verdict banner end the response?** The banner script runs (with `--skill /review-pr-v2`) after the PR comment posts, and its fenced stdout is the last thing in the response — nothing follows it.

If any checkbox is "no", stop. Surface to the user: "Compliance self-check failed at step <X>. Re-run the missed step or re-spawn personas with correct prompt before posting verdict." Do NOT post a verdict whose attestations would be lies.

This gate is the model's self-honesty test. SKILL.md is a request form — the only enforcement is the orchestrator's discipline. A PostToolUse hook keyed on `gh pr review --comment` would be a stronger backstop (see "Future hardening" at the end of this skill).

### Render verdict and post to PR

Verdict gate logic in `_review-common/blocker-classes.md`. Compute Tier-1 weight (CRITICAL=8, HIGH=4, MEDIUM=2, LOW=1) and Tier-2 weight after fix application.

**Final line — verdict banner.** After rendering the verdict output and posting it to the PR, run the shared verdict-banner script and emit its output verbatim (`~/.claude/skills/_review-common/blocker-classes.md` § Verdict banner) as the **very last** thing in your response, so the verdict is visible without scrolling up past the detail.

Post a single PR comment:

```bash
gh pr review --comment --body "$(cat <<'EOF'
## Tribunal v2 — Verdict: APPROVED | NEEDS USER INPUT

**Invocation:** N+1 (prior invocations: <list>; force-push detected: yes/no; state-file resync: yes/no)
**HEAD reviewed:** <sha>
**Commits since last invocation:** <m> (or "first invocation")
**Personas:** <list>

### Compliance attestations (machinery verification)
- **State source:** loaded from cache | reconstructed from PR comments (cache missing) | first invocation (no state needed)
- **State persisted:** `~/.claude/cache/review-state/<repo-slug>__pr-<N>.json` (size: <bytes>; written before this verdict was posted)
- **Persona prompt template used:** yes (loaded `~/.claude/skills/_review-common/agent-prompt.md`; substituted skill_specific_extensions verbatim)
- **Round-memory preamble injected:** yes / n_a (round 1, no prior state)
- **Prior_blocker_audit consulted before classification:** yes / n_a (no prior blockers)
- **Stage 1.5 brief-conformance:** feature-scoped: yes/no; at-risk Goals touched by this PR: <n>; Scope-fidelity Adversaries spawned (one per Goal, isolated): <n>; Brief-conformance Prosecutor: passed/filed; findings — SURFACE_PARITY_GAP: <n>, BRIEF_NONGOAL_TRESPASS: <n>, BRIEF_GOAL_UNDELIVERED: <n> | n/a (not feature-scoped / no brief.md)
- **Premise interrogation (diff-baseline + pr-description + goal-outcome) acknowledged by personas:** <n>/<N> personas (each persona either filed `premise_interrogation: passed` or one or more `[premise inversion: ...]` findings; goal-outcome sub-pass runs on feature-scoped PRs only)
- **Post-fix premise verification:** <n> in-scope lines reviewed; <n> claims identified; <n> survived; <n> filed as FIX_INTRODUCED_PREMISE_INVERSION (working tree left dirty)
- **PR test plan executed:** <n>/<n> items run against HEAD <sha> and ticked on the PR; <n> counts corrected; <n> failures escalated | n/a (PR has no `## Test plan`)

If any attestation reads "no", you posted a verdict whose convergence machinery did not run. That is a SKILL.md violation, not a verdict the user should trust.

### Gates
- Baseline: compile=PASS, lint=PASS, tests=PASS, project-specific=PASS
- After fixes: compile=PASS, lint=PASS, tests=PASS, project-specific=PASS

### Stage 1 audit
- Repo reality: <count> identifiers/paths/CI verified
- Stage 1 mechanical fixes: <count> (formatters, lint auto-fix)
- Round Memory: invocation N+1; <k> files unchanged since last invocation; <m> modified; <a> added
- Prior-blocker audit: <r> resolved; <c> carrying forward; <p> reclassification-pending

### Stage 1.5 brief-conformance (feature-scoped PRs)
- Feature: <feature> | n/a (not feature-scoped / no brief.md)
- At-risk Goals touched by this PR: <list>; Scope-fidelity Adversaries spawned: <n>; Prosecutor: passed/filed
- Findings: SURFACE_PARITY_GAP: <n>; BRIEF_NONGOAL_TRESPASS: <n>; BRIEF_GOAL_UNDELIVERED: <n>

### Stage 2 panel
- Personas run: <list>
- Premise interrogation: <p> personas filed `premise_interrogation: passed`; <i> premise inversions filed (diff-baseline: <n>, pr-description: <n>, goal-outcome: <n>)
- Total findings raised: <count> (CRITICAL: n, HIGH: n, MEDIUM: n, LOW: n)
- Findings retracted by critical-pair policy: <count>
- Round-memory retractions: unchanged-file auto-retract: <n>; regression_risk severity downgrades: <n>
- Decisions-log-first carry-forward (Priority 1): feature-scoped: yes/no [<feature> if yes]; findings checked: <n>; retracted via bound entry: <n>
- Prior-classification downgrades to OPEN_QUESTION (no justification): <n>

### Stage 3 fixes applied
- <commit sha>: <one-line description> — addressed <findings>
- <commit sha>: <one-line description> — addressed <findings>
- Class sweep: <skipped (no sweep-eligible categories) | ran with <n> agents; siblings_found: <n>; siblings_after_filter: <n>; out-of-ownership siblings → OPEN_QUESTION: <n>>
- Same-round focused re-prosecution: <skipped (no orchestrator edits) | ran with <n> agents on <m> diff hunks; findings raised: <f>; retracted: <r>; STABLE_DISAGREEMENTs: <s>; fixes applied: <a>; second-pass falsified claims: <p>>

### Structural sweep (unseeded)
Always rendered unless `baseline_red` — an all-clean sweep is the evidence the universes were covered, and it is what makes an `APPROVED` verdict mean more than "no persona noticed anything".
- Universe: <name> — <members_enumerated> members: <closed> closed, <gap> gap, <na> n/a, <undetermined> undetermined
- Skipped: <universe> (<reason>) · Inherited clean: <universe> (from invocation <n>)
- Out-of-ownership members filed as OPEN_QUESTION: <n>
- Gaps promoted to findings: <n> (<severities>)

### Class sweep audit
For each class swept (per the Stage 3 Class Sweep sub-pass; omit block when class_sweep.ran=false):
- Class: <name> (<class_notion>) — bare invariant: <bare_invariant>
- Peer-set: handed <peer_set_handed> → walked <peer_set_walked> <(widened — <widening_justification>) | (confirmed widest)>
- Peer-set walked: <n> members (diff files / callsites / blast radius); swept clean: <n>
- Instances: <seeds> seed + <siblings_found> sibling (<siblings_after_filter> survived round-memory + critical-pair filter)
- Resolutions: <every instance → fix, escalated blocker, or out-of-ownership OPEN_QUESTION>
- Singleton classes recorded (no peer-set): <list, or none>

### Retractions
- <finding> → retracted because <round-memory unchanged-file / critical-pair policy / pre-resolved by Stage 1>

### Blockers (if NEEDS USER INPUT)
- [SURFACE_PARITY_GAP] <Goal, verbatim> — delivered code serves the outcome over <slice> but the Goal's domain is <domain> (axis: subset-of-domain | weaker-substitute-basis | premature-action-before-basis). Resolution: extend coverage in <chunk/follow-up>, OR scope the Goal down in the brief. (Class A — not retracted by a bound decision.)
- [BRIEF_NONGOAL_TRESPASS] <Non-goal, verbatim> — delivered code does what the Non-goal forbids at <path:line>. Resolution: drop the trespassing code, OR amend the brief. (Class A.)
- [BRIEF_GOAL_UNDELIVERED] <Goal, verbatim> — PR claims to deliver this Goal but ships only enabling code; the outcome is produced nowhere. Resolution: deliver the outcome, OR amend the brief. (Class A.)
- [STABLE_DISAGREEMENT] <finding> — Persona A: <fix A>; Persona B: <fix B>. Pick one.
- [OPEN_QUESTION] <finding> — <question>{prior_classification: <old> if reclassified}
- [POLISH_PLATEAU] <finding> — non-blocking; ship is acceptable.
- [FIX_INTRODUCED_REGRESSION] <gate> failed after applying <fix> — working tree left dirty for inspection.
- [FIX_INTRODUCED_PREMISE_INVERSION] <path:line> — fix introduced "<rewritten prose>"; verification failed: <reason>. Working tree left dirty for inspection.
- [BASELINE_RED] <gate> was failing on branch HEAD before review — no Stage 2/3 ran.

### Final Tier 1 weight: <n>
### Final Tier 2 weight: <n> (floor: 4)
EOF
)"
```

If `NEEDS USER INPUT`: report blockers to user. The user resolves and re-invokes (next run carries forward round-memory state — file hashes, prior blockers, classification history — so it does not re-prosecute unchanged code).
If `APPROVED`: also report APPROVED status + PR URL to the user.

---

## Future hardening (out-of-band enforcement)

SKILL.md cannot enforce its own machinery — the orchestrator (Claude in main thread) follows it voluntarily, and the documented failure mode is precisely "follow-through gaps under load." The structural fix is a hook outside the skill:

- **PostToolUse hook on `gh pr review --comment`** in `~/.claude/settings.json`. After a tribunal v2 verdict is posted, the hook checks that a Write to `~/.claude/cache/review-state/<repo-slug>__pr-<N>.json` happened within the last N seconds. If not, it surfaces a warning ("Tribunal verdict posted without state-file persistence — round-memory will be cold on the next invocation").
- **PreToolUse hook on Agent calls during /review-pr-v2** that pattern-matches the prompt for the literal markers `Premise interrogation (mandatory`, `Diff-baseline premise check`, `PR-description premise check`. If any marker is missing, it surfaces a warning before the agent launches.

These hooks would convert SKILL.md compliance from "honor system" to "enforced." Run `/update-config` to wire them up.

---

## Hard rules

- **Stage 1 is mandatory.** No persona prosecutes without the audit report.
- **Round Memory load is mandatory.** Skipping it disables file-hash diff and prior-blocker consistency, returning the skill to pre-fix thrash mode. State file lives at `~/.claude/cache/review-state/<repo-slug>__pr-<N>.json` (NOT in the project repo).
- **Stage 1.5 Brief-conformance gate is mandatory on feature-scoped PRs.** When the PR touches `features/<feature>/` (or a commit/PR-body cites a feature) AND `features/<feature>/brief.md` exists, the gate runs before Stage 2: one Brief-conformance Prosecutor + one Scope-fidelity Adversary per at-risk Goal the PR touches, each adversary spawned in ISOLATION (never batched — the isolation is validated to catch narrowings a batched call misses). Judges the delivered diff, not a plan. Its `SURFACE_PARITY_GAP` / `BRIEF_NONGOAL_TRESPASS` / `BRIEF_GOAL_UNDELIVERED` findings are Class A — they enter Stage 2 as pre-resolved hard findings personas cannot retract, are exempt from Priority-1 decisions-log carry-forward, and are escalated (never auto-fixed — extending scope is a Forbidden fix). Non-feature-scoped PRs record `brief_conformance: n_a` and skip it.
- **Stage 2 premise interrogation is mandatory.** The diff-baseline and PR-description sub-passes MUST run on every PR; the goal-outcome sub-pass MUST additionally run on feature-scoped PRs (concrete single-surface Goals the Stage 1.5 at-risk filter excluded). A persona producing zero premise inversions must explicitly state `premise_interrogation: passed`.
- **Stage 2 agents return fix lists; never edit files or commit.** All edits are applied by Stage 3 in one pass.
- **Stage 3 applies round-memory tag filtering before critical-pair filtering.** Findings tagged `targets_unchanged_file: yes` without (a)+(b) justification are auto-retracted; findings tagged `regression_risk: yes` without a named failure mode are severity-downgraded.
- **Stage 3 applies critical-pair policies before applying fixes.** Findings contradicting a policy are retracted, not relitigated.
- **Stage 3 re-runs gates after applying fixes.** A fix that breaks a gate is `FIX_INTRODUCED_REGRESSION`, not a CLEAN-with-warning.
- **Stage 3 verifies its own edits.** When a Stage 3 fix rewrites a comment, docstring, schema directive, or plan-prose body, the orchestrator runs LLM-judgment claim identification over the rewritten lines and verifies each identified claim against the repo. False claims emit `FIX_INTRODUCED_PREMISE_INVERSION` and block the verdict; no commits land until resolved. Verification runs main-thread (LLM judgment), not as a sub-agent.
- **Stage 3 same-round focused re-prosecution is mandatory** when ANY of: orchestrator-applied Stage 3 fix count > 0, post-fix premise verification falsified-claim count > 0, new commits created by Stage 3 (HEAD changed). Skipping it lets persona-class defects in orchestrator-rewritten code/prose bake in and surface as fresh blockers next invocation. Bounded: exactly one re-pass on the diff hunks Stage 3 wrote.
- **Stage 3 carry-forward consultation uses two priorities in order when the PR is feature-scoped** (any path under `features/<feature>/` touched, OR commit/PR-body cites a feature dir). Priority 1: consult `features/<feature>/decisions.md` for findings contradicting bound entries — drop them with citation. Priority 2: prior-blocker classification consistency check against `prior_blocker_audit`. Authority order: `decisions.md` > `recently_resolved_blockers` > prior verdict text. Non-feature-scoped PRs skip Priority 1 and go directly to Priority 2.
- **Stage 3 enforces prior-blocker classification consistency.** A blocker class flip across invocations without justification is downgraded to `OPEN_QUESTION` so the user arbitrates.
- **Stage 3 executes the PR's `## Test plan` and ticks it off before the verdict.** Every runnable item is run against the final post-fix HEAD; passing boxes are ticked and drifted counts corrected via `gh pr edit --body-file`; a failing item is fixed in-PR or escalated as a blocker (`FIX_INTRODUCED_REGRESSION` / `OPEN_QUESTION`). Re-running the generic gates is NOT a substitute — the test plan covers PR-specific surface the gates miss (a new CLI/script, the other workspace's suite, a `bash -n` parse, an operator exit-code check). Never tick a box for an item you did not run; never post the verdict with runnable items unexecuted. PR has no `## Test plan` → record `test_plan: none`.
- **Stage 3 persists state file regardless of verdict, before posting the verdict.** APPROVED still gets written so the next invocation after additional commits applies round-memory gates correctly. State write uses the **Write** tool, not shell redirection.
- **Class > line is a Stage 2 obligation.** Personas declare class + universe at finding time; Stage 3 fixes the entire universe.
- **Never** mark APPROVED while any blocker class is non-empty.
- **Never** weaken tests, types, or assertions to make gates green.
- **Never** skip the Repo Reality Audit.
- **Never** skip the Round Memory load — it is the convergence forcing function.
- **Never** carry a finding forward from a prior invocation without re-verifying its target.
- **Never** accept "pre-existing" as a defense for a defect in a file the PR touches.
- **Always** read the full file (not just the hunk) when filing a finding that depends on file context.
- **Always** grep every identifier the diff introduces *and* every identifier it references.
- **Always** verify a prior invocation's claimed-fix at the *class* level, not the *line* level.
- **No re-review loop within a single invocation.** Escalate unresolved findings as blockers and let the user re-invoke.

## Edge cases

- **No PR exists:** tell the user to run `/open-pr` first, stop.
- **Baseline gates RED:** emit `BASELINE_RED` blocker, skip Stage 2/3.
- **Persona file not found:** synthesize the equivalent role from the persona's name and the audit report.
- **Stage 2 finds zero issues:** Stage 3 still runs (apply Stage 1 fixes if any, re-run gates, commit, post APPROVED). The gate re-run is the integrity check.
- **All Stage 2 findings retracted:** treat as zero findings; APPROVED if gates pass and no blockers.
- **Working tree has uncommitted changes at start:** stash, run review, surface to user. Do not silently include user's WIP in the tribunal's commits.
- **HEAD changes mid-review** (user pushed during review or remote landed): emit `REPO_STATE_DRIFT`, do not commit, ask user to re-invoke.
- **Very large diffs (>1000 lines):** review fully. Personas chunk their reading; orchestrator does not truncate the diff.
- **PR depends on an unmerged dependency PR:** Stage 1 catches via `HALLUCINATION` findings. Surface as `OPEN_QUESTION` — user decides whether to merge dep first or scope this PR's gates to ignore missing identifiers.
- **State file corrupted / unparseable:** if PR comments imply prior verdicts, enter state reconstruction (see Round Memory load). Otherwise treat as no prior state. Either way, surface `state_file_corrupt: <reason>` and overwrite on next persist.
- **State file missing but PR has prior verdicts:** state reconstruction fires automatically (see Round Memory load). Tag `state_source: reconstructed_from_pr_comments`. Reconstruction is partial — `last_diff_files` may be empty if `last_head_sha` isn't in local refs (force-pushed and pruned), in which case round-memory file-hash comparison degrades gracefully and personas treat the invocation with full prosecution latitude. `recently_resolved_blockers` cannot be reconstructed from verdicts — accept one invocation of degraded prior-decision context. Prior_blockers ARE reconstructible from verdict comment text and provide most of the convergence value.
- **State file disagrees with PR comments by > 1 invocation:** take the higher value, tag `state_file_resync: yes`. Common cause: cache cleared between invocations, or user invoked from a different machine.
- **Force-push between invocations:** detected by the Round Memory load force-push-detection sub-pass. Round-memory file-hash diff still applies (blob shas match across history rewrites), but line-number-keyed prior_blockers may be stale — Stage 2 personas verify line numbers fresh. Auto-retraction is suppressed when `force_push_detected: true`.
- **User wants to discard round-memory:** delete `~/.claude/cache/review-state/<repo-slug>__pr-<N>.json` manually before re-invoking. The skill does not auto-detect "the PR was rewritten" because the judgment is unreliable.
