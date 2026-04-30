---
name: plan-review
description: Convene an adversarial tribunal of expert personas on one or more implementation plans. Ruthlessly attack every claim, verify against actual repo state, fix the plans, loop until clean. N plans × M personas = N×M parallel agents.
user-invocable: true
---

# Plan Review — Adversarial Tribunal

Plans are cheap to write and expensive to execute. A hallucinated plan burns days of implementation time chasing files that don't exist and APIs that were never added. This skill convenes an **adversarial tribunal of expert personas** whose job is to prosecute the plan until every claim is grounded in the real repo or escalated to the author.

Each plan is reviewed by **every** specified persona — not round-robin. With N plans and M personas, launch N×M parallel agents.

## Tribunal principles

**REPO REALITY IS LAW.** Before any persona critiques the plan, the repo must be re-mapped. A plan that says "modify `MonitorHeader.tsx:42` to call `useSessionCache`" is worth nothing unless `MonitorHeader.tsx` exists, line 42 says what the plan claims it says, and `useSessionCache` is a real export. **Every path, every line number, every identifier, every command, every CI job, every test file named in the plan must be verified against the branch the plan will execute on.** Unverified claims are not "lower confidence" — they are defects.

**Prior-round findings are hypotheses, not facts.** If round 1 said "add a test in `__tests__/auth.spec.ts`," round 2 must still verify that `__tests__/` is the real test dir. It often isn't.

**Banned rationalizations** (any round ending in one of these is not-clean):
- "probably exists", "should exist", "standard convention", "common pattern"
- "minor", "nit", "can be fleshed out during implementation"
- "author will figure it out", "trusted author"
- "out of scope for this review"
- "accepted residual"

**Prosecute; don't collaborate.** Your goal as reviewer is to find the reason this plan will *fail*, not to polish its prose. If you can construct a scenario where executing the plan verbatim produces a broken result, that is a CRITICAL finding.

**Fix, don't annotate.** Every finding becomes either a direct edit to the plan file or an escalation to the author with a concrete question. No "consider…" comments left dangling.

## Plan Style Rules (Forward-Looking, Not Archaeological)

**A plan is a contract for an implementer with no context about how the plan was produced.** It reads as the only source of truth, not a layered archaeology of review history. An implementer (especially an AI agent starting from a cleared context) cannot reconstruct review history before they can act — every cross-reference, every "where X conflicts with Y", every "addendum N corrects addendum M" forces them to load the dependency graph before doing the work.

**These apply to original drafts, fix passes, and any consolidation pass. Violations are CRITICAL structural issues.**

Plans MUST NOT contain:

- **Addendum sections.** No "Addendum A", "Architecture-review addenda", "Backend-review addenda", "AI-development addenda" — findings integrate into the existing section they correct.
- **Review attribution.** No "Architecture review found…", "Backend persona flagged…", "Per AI-dev addendum…". The plan states facts and instructions, not who supplied them.
- **Cross-references between fix locations.** No "see addendum E", "per addendum AA", "binding per addendum N". If two parts of the plan relate, integrate them or use one named subsection.
- **Conflict-resolution metadata.** No "where X conflicts with Y, Y wins", "Backend addendum P's reasoning … requires that …, contrary to Architecture addendum E". Pre-resolve the conflict and state the resolved instruction. The implementer has no conflict — they have a plan.
- **Historical comparisons.** No "the original plan said X but actually Y", "the Mechanics section's claim is too loose because…", "previous version said…", "the plan ignores that…". Just state the correct thing.
- **"Decisions resolved" or "Decisions made in the past" sections.** Decisions bake into the contracts/instructions, not separate catalogues.
- **Persona-attribution headers** ("from a Rust backend lens", "through an architect's lens"). The plan is one document with one voice.

Plans MAY contain:

- **"Why" rationale** for non-obvious choices — preserves intent so the implementer can judge edge cases. Phrase forward-looking ("This split keeps each PR single-focus"), not retrospective ("Backend review flagged this, so we split it").
- **A short "Repo state facts" / "Verified facts" section** capturing observable facts that informed the plan (file paths, line numbers, test names, branch protection state). Forward-looking facts, not review history.

The smell test: pretend you've never seen the plan, never heard of the review, and have 10 minutes to start work. Can you act on every section without first reconstructing how the plan got into its current state? If no, the plan has archaeology — strip it.

## Usage

```
/plan-review <plan-path-1> [plan-path-2] ... [--personas <p1> <p2> ...]
```

**Examples:**

```
# Single plan, auto-assign best persona
/plan-review .scratch/wave1-F14-parametric-sweep.md

# Multiple plans, auto-assign one persona per plan
/plan-review .scratch/wave1-F9.md .scratch/wave1-F10.md

# Single plan, explicit personas — reviewed by ALL (2 parallel tribunals)
/plan-review context/plans/040_person-cross-category.md backend architecture

# Multiple plans with explicit personas — each plan reviewed by ALL listed personas
# 3 plans × 2 personas = 6 parallel tribunals
/plan-review .scratch/F12.md .scratch/F13.md .scratch/F14.md --personas frontend backend
```

## Argument parsing

Split `$ARGUMENTS` on whitespace. Classify each token:

- Token contains `/` or ends with `.md` → plan path
- Token is `--personas` → all subsequent non-path tokens are persona names
- Otherwise → persona name (backward compat: single-plan usage)

**Path resolution:**
- Starts with `/` or `./` → use as-is
- Starts with `.scratch/`, `context/`, or `features/` → resolve relative to repo root
- Looks like a chunk slug (kebab-case, no separator, no `.md`) → resolve as `features/*/implementation/<slug>.md` if exactly one match exists; ambiguous → ask which feature
- Ends with `.md`, no separator → prepend `.scratch/`

**Per-chunk plans live at `features/<feature>/implementation/<slug>.md`** (slug-named, no number prefix). The engineering plan's chunk index uses the same slug as the chunk-plan filename — they're the same identifier.

**Backward compatibility:** Exactly one plan + one or more non-path tokens without `--personas` → treat the non-paths as personas.

No arguments → search `.scratch/` for `*.md` files that look like plans (contain `## Implementation`, `## Files to`, or `**Effort:**`), list them, ask which to review.

## Persona resolution

### Explicit personas

Load each from `personas/{name}.md`. **Every plan is reviewed by every listed persona.** N plans × M personas = N×M parallel agents. If a persona file is missing, stop and report.

### Auto-assignment (no personas specified)

Scan each plan for the strongest keyword match:

| Persona | Keywords | Best for |
|---------|----------|----------|
| `frontend.md` | component, form, button, table, column, page, tab, modal, React, JSX, Tailwind | UI components, forms, page integration |
| `backend.md` | API, endpoint, query, mutation, hook, fetch, cache, queryKey | API hooks, data fetching |
| `architecture.md` | store, state, integration, route, dependency, pattern, system | Cross-cutting architecture |
| `data-visualization.md` | chart, D3, Recharts, SVG, topology, graph | Charts, viz |
| `product.md` | user flow, sweep, batch, multi-select, UX, edge case, empty state | User-facing features |
| `code-reviewer.md` | refactor, polish, consistency, error, type safety, test | Code quality |
| `ui-code-review.md` | dark mode, theme, CSS, design token, responsive, accessibility | Theming, a11y |
| `testing.md` | test, coverage, mock, integration, validation, assertion | Test strategy |
| `security.md` | auth, authz, token, secret, injection, sanitize, CSRF | Security |
| `slice-and-dice-design.md` | dice, hero, monster, boss, face, pip, textmod | Slice & Dice balance/mod design |
| `ai-development.md` | chunk, checkpoint, parallel, agent, implementation plan | Plan structure |

**Rules:**
- Pick the strongest match per plan.
- No two plans share a persona unless there are more plans than personas — fall back to second-best.
- `ai-development.md` is loaded as supplementary context for every agent but is not the assigned persona unless explicitly requested.

## Workflow

### Single-plan mode (1 plan)

Execute the review phases inline. If one persona, do it yourself; if multiple, launch one Agent per persona in parallel, then consolidate.

### Multi-plan mode (2+ plans)

- Read `personas/ai-development.md` and (if exists) `memory/plan-quality.md` once — shared context.
- Resolve personas (auto or explicit).
- **Launch one Agent per (plan, persona) pair, all in parallel in a single message.** N×M agents.
- Wait for all to complete.
- Output the combined summary (below).

**Agent prompt template:**

> You are a hostile reviewer on an adversarial tribunal, reviewing an implementation plan as the **{persona_name}** persona.
>
> {persona_file_content}
>
> ## AI Development Principles (always apply)
> {ai_development_content}
>
> ## Plan Quality Rules (if available)
> {plan_quality_content_or_"(no file)"}
>
> ## Plan Under Review: {plan_filename}
> {plan_content}
>
> ## Your Task
>
> You are not helping polish prose. You are prosecuting the plan. Assume it is broken until you prove otherwise.
>
> **Execute every phase below. The Repo Reality Audit is MANDATORY and BLOCKING every round.** Do not let a finding out the door unless you produced tool output *this round* that proves its target exists and exhibits the defect.
>
> {include full review-phase details below}

---

## Review phases

### Repo Reality Audit — MANDATORY, BLOCKING, EVERY ROUND

**This exists because tribunals that skip it prosecute imaginary defendants for 10 rounds while real defects walk free.** Round 1 without this step is round 1 of hallucination.

Before reading the plan with any critical eye, map the actual repo as it exists on the branch the plan will execute on. Use tool output, not memory:

- **Tree:** `ls` the repo root. List top-level dirs.
- **Authoritative file list:** `git ls-files | wc -l`, and spot-check with `git ls-files | head -n 100`.
- **Test infrastructure (real):** `git ls-files | grep -E '(^|/)(test|tests|spec|__tests__)(/|$)|\.(test|spec)\.[a-z]+$'`. Do not assume `__tests__/` — look. Many repos use `tests/`, `spec/`, inline `*_test.go`, or Rust `#[cfg(test)]` in-module.
- **CI (real):** `ls .github/workflows/ 2>/dev/null && cat .github/workflows/*.y*ml 2>/dev/null | head -n 200`. Also check `.gitlab-ci.yml`, `.circleci/config.yml`, `buildkite/`. Name the jobs that exist. If the plan invents a CI job, that is CRITICAL.
- **Build/test commands (real):** Read `package.json` scripts, `Cargo.toml`, `Makefile`, `pyproject.toml`, `justfile`, etc. The plan may only assume commands that this project actually defines.
- **Entry points the plan mentions:** For every file path, `ls` it. For every module/package, confirm it in the authoritative file list.
- **Identifiers the plan mentions:** For every function, type, field, flag, CLI arg, env var, route, table/column the plan names — grep for it. Record hit counts. A zero-hit identifier is CRITICAL unless the plan explicitly creates it (then verify the creation location matches project patterns).
- **Line-number claims:** For every "modify line N of path" claim, `Read` `path` around line N and verify the content matches what the plan asserts is there.

Record the audit in your review output:

```
### Repo Reality Audit (Round N)

- Tree: <dirs>
- git ls-files count: <N>
- Test layout (real): <paths>
- CI workflows (real): <files and job names, or "none">
- Build/test commands (real): <names>
- Plan claims verified:
  - `path/x.ts:42` — EXISTS / MISSING / WRONG CONTENT (plan said "<X>", actually "<Y>")
  - `fn fooBar` — 0 hits / N hits in <files>
  - CI job `foo-ci` — EXISTS in .github/workflows/foo.yml / DOES NOT EXIST
  - (etc., every claim)
```

**If the audit contradicts the plan, those contradictions are the first CRITICAL findings of the round.** If it contradicts a previous round's finding, explicitly retract that finding in this round's output.

### Structural Review

Check the plan against these rules. They are guidelines calibrated to chunked plans — adapt for XS/S plans without losing the spirit (clarity, testability, scope discipline).

- Every chunk has ≤ 5 files (count them).
- Every chunk has a single concern.
- Every chunk has a TDD section with **enumerated, specific test cases** — not file names, not "tests for this feature."
- File lists are definitive — no "or" / "depending on approach" ambiguity.
- Critical chunks have "If blocked" branches.
- Checkpoint strategy is explicit and minimal.
- Final verification names **specific data** and commands, not "verify it works."
- Each chunk lists "read first" / source-of-truth files.
- Out-of-scope items are explicit in the overview.
- Multi-chunk plans have a Parallel Execution Map.
- Parallel groups are correct — chunks depending only on the foundation are parallel, not falsely sequential.
- No hidden cross-chunk file dependencies (if chunk N writes `X` and chunk M reads `X`, they can't be parallel).
- Declared chunk dependencies match actual file dependencies.

Each structural failure is a finding with severity.

### Persona Prosecution

Read the full persona file. Review every section of the plan through that persona's lens as a *hostile expert*. For each claim in the plan:

- Does the cited file/line/API match repo reality? (Cross-check your Repo Reality Audit.)
- Does the plan upload the persona's red flags? (Missing auth checks, wrong patterns, hallucination risks, missing tests, architectural smells, security gaps, product gaps, data integrity risk, perf landmines, type-safety erosion.)
- Can you construct a scenario where executing the chunk verbatim produces an incorrect result?
- Is the TDD coverage actually sufficient to catch the failure modes the persona cares about? Or does it only test the golden path?
- Does the plan respect project invariants declared in `CLAUDE.md`, `SPEC.md`, and similar? Quote the invariant when flagging a violation.

**Verify, don't infer.** If the plan says "extends the existing `FooService`," open `FooService` and confirm it has the extension points the plan assumes. If it says "reuses the `useSessionCache` hook," grep for `useSessionCache` and read its signature.

Finding format:

```
[CRITICAL] {Chunk/Section}: {finding}
  - Evidence: {verbatim quote from plan} vs {verbatim quote from repo file:line, or grep output}
  - Impact: {concrete failure mode}
  - Fix: {specific edit to the plan}
```

Severities:
- **CRITICAL**: Plan will fail or produce wrong results as written. Includes every hallucinated path/API.
- **HIGH**: Significant correctness/quality risk.
- **MEDIUM**: Real gap that weakens the plan.
- **LOW**: Polish that still must be fixed before APPROVED.

**Severity does not gate fixing.** Everything gets fixed or escalated.

### Consolidate

Merge structural + persona findings into a single deduplicated list, grouped by section/chunk. Note the source (structural rule or persona name) for each. Present to the user before the Fix phase if running single-plan mode inline; in agent mode, include in the agent's final output.

### Fix the Plan

Apply every fix directly to the plan file:

- Hallucinated path/API → replace with the real one (from the Repo Reality Audit), or if the plan intentionally creates it, add explicit creation steps with a real parent directory that exists.
- Missing TDD case → add a specific enumerated test with an exact assertion.
- Oversized chunk → split, update the Parallel Execution Map, update the checkpoint plan, update the chunk count.
- Vague verification → replace with a specific command + expected output.
- Pattern drift → cite the existing pattern (file:line) and rewrite the plan's approach to match.
- Missing "If blocked" → add one with a real fallback path.

**Forbidden fixes:**
- Weakening the plan (removing tests, lowering coverage, dropping invariants) to resolve a finding.
- Changing the plan's goal to sidestep a hard problem — escalate instead.
- "Leaving details for implementation" — if it's unclear now, the implementer will hallucinate.

Output a summary of edits made.

### Re-review (Loop)

Re-run the Repo Reality Audit, Structural Review, Persona Prosecution, and Consolidate phases on the updated plan. The Repo Reality Audit repeats in full — do not skip it because "I already audited." Fixes can introduce new hallucinations. Previous-round findings are re-verified against current repo state; retract any that don't survive.

**Termination:** a round produces **zero findings at any severity** AND the Repo Reality Audit shows every plan claim matches repo reality. No "accepted residual."

**Max rounds:** 3. If round 3 still has findings, escalate ALL of them to the user with a recommendation (often: the plan's scope needs to be split or a design decision is genuinely open).

### Final Report

```
## Plan Review Complete: {plan_filename}

**Persona:** {name}
**Rounds:** {N}
**Final Repo Reality Audit:** all claims verified / N claims failed audit (see below)

### Changes Made
- {bullets of all significant edits}

### Retractions from earlier rounds
- {findings dropped because they were based on fictional targets — be honest}

### Needs User Input (if any)
- {issues requiring a human decision — state the tradeoff and options}

### Plan Status: APPROVED / NEEDS USER INPUT
```

**APPROVED** = zero findings at any severity, Repo Reality Audit passes 100%.
**NEEDS USER INPUT** = issues requiring genuine human judgment (design tradeoffs, conflicting constraints, ambiguous requirements) — *not* lazy-deferred MEDIUM/LOW.

---

## Combined summary (multi-plan mode)

```
# Plan Review Summary

| Plan | Persona | Rounds | Critical | High | Medium | Low | Audit | Status |
|------|---------|--------|----------|------|--------|-----|-------|--------|
| WP-F9 | frontend | 2 | 0 | 0 | 0 | 0 | PASS | APPROVED |
| WP-F9 | backend  | 3 | 0 | 0 | 0 | 0 | PASS | APPROVED |
| **WP-F9** | **overall** | | **0** | **0** | **0** | **0** | **PASS** | **APPROVED** |
| WP-F10 | frontend | 1 | 0 | 0 | 0 | 0 | PASS | APPROVED |
| WP-F10 | backend  | 2 | 0 | 0 | 0 | 1 | PASS | NEEDS USER INPUT |
| **WP-F10** | **overall** | | **0** | **0** | **0** | **1** | **PASS** | **NEEDS USER INPUT** |

## Needs User Input (deduplicated across personas)
- {plan}: {issue} — Options: {A} vs {B} (flagged by: {personas})

## Key Changes Across Plans
- {plan}: {summary}

## Retractions (findings dropped as hallucinated)
- {plan} / {persona} / round N: {dropped finding, why}

## Clean Passes
- {plans APPROVED by all personas}
```

Deduplicate findings that multiple personas flagged on the same plan — merge and note which personas caught each. Expand each agent's full final report below the table, grouped by plan, ordered NEEDS USER INPUT first.

## Hard rules

- **Never** produce a finding without tool output *this round* proving its target exists. Hallucinated findings are worse than missed ones — they erode trust.
- **Never** skip the Repo Reality Audit, even on round 2+.
- **Never** carry a prior-round finding forward without re-verifying its target.
- **Never** accept "probably exists," "should be there," "standard convention" as evidence.
- **Never** weaken the plan to resolve a finding.
- **Never** mark APPROVED while any finding — at any severity — remains unfixed and un-escalated.
- **Always** quote verbatim from both plan and repo when flagging a mismatch.
- **Always** retract prior-round findings explicitly when the current-round audit shows they were fictional.
- **Always** fix in the plan file; don't just annotate.

## Edge cases

- **Plan file not found:** report, continue on remaining plans.
- **Persona file not found:** auto-assignment falls back to next best match; explicit personas stop and ask.
- **Single plan + multiple personas:** launch one Agent per persona in parallel; no agent for single persona.
- **Large N×M (e.g., 7 × 3 = 21 agents):** expected. Launch all in parallel.
- **Plan references code that doesn't exist:** CRITICAL. The plan assumes an unmerged dependency or was written against a stale repo map.
- **Plan contradicts project rules** (`CLAUDE.md`, `AGENT_CONTRACT.md`, persona non-negotiables, textmod guide, schema): CRITICAL. Quote the rule.
- **Very large plans (>500 lines):** review fully. Do not truncate. Do not summarize to save tokens at the cost of missing defects.
