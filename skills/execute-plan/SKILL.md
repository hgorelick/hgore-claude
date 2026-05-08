---
name: execute-plan
description: Implement a passed chunk plan end-to-end — TDD-first, Factoring-Contract-respecting, decisions-conformant, PR-ready. Reads the chunk plan as the contract; reads `decisions.md > engineering-plan.md > chunk plan > brief.md` in authority order. Status frontmatter is binary: refuses on `Status: needs-user-input` (mid-cycle author state) and on a plan-author sidecar reporting `authoring_mode: "draft"`; everything else proceeds. Stages run sequentially with hard gates between them: State load + authority-stack read; Context-pack ingest of every file the plan names; Pre-implementation gates (`/plan-lint` + baseline test/typecheck/lint health + HEAD record); Test-first authoring of every "Tests to add" case (confirm RED); Minimal implementation to GREEN; Acceptance-criteria observation; Pre-PR verification (typecheck / lint / test / `/plan-lint`); user invokes `/open-pr` next, then `/review-pr-v2`. Honors decisions.md / engineering-plan.md as bound — surfaces would-be amendments as `OPEN_QUESTION` rather than auto-editing. Out-of-scope is binding; pre-existing failures are zero-tolerance per CLAUDE.md. Sister to the author-side trio (`/brief-author`, `/engineering-plan-author`, `/plan-author`); pairs with `/review-pr-v2` for post-execution review.
user-invocable: true
---

# Execute Plan — TDD-First Chunk Implementation

Once a chunk plan has been authored by `/plan-author` and reviewed by `/plan-review-v2` (both APPROVED), the contract is set and the on-disk file has no `Status:` frontmatter (the author skill removes it on a successful APPROVED emission). This skill drives the implementation through TDD with the Factoring Contract enforced at every gate, and hands off to `/open-pr` + `/review-pr-v2`. Never edits the plan; never edits decisions.md without surfacing as `OPEN_QUESTION`; never weakens tests to pass.

This is the implementer-side analog of `/plan-author` (the author-side). It exists because chunk plans are written for an implementer with no context — and Claude is that implementer. The skill exists to formalize the discipline that "implement it" prompts leave implicit.

## Shared scaffolding

- `~/.claude/skills/_review-common/principles.md` — REPO REALITY IS LAW, banned rationalizations (the same stance applies at execution time)
- `personas/ai-development.md` — chunk discipline, plan-quality rules, Factoring Contract semantics
- The project's `CLAUDE.md` — TDD discipline, zero-tolerance for pre-existing failures, package-management rules, schema-first / operations-first conventions, source-of-truth files
- The project's `features/README.md` — plan-lifecycle process

## Inputs

`$ARGUMENTS` (one of):

- `<chunk-slug>` — kebab-case slug; resolved to `features/*/implementation/<slug>.md` if exactly one match exists. Ambiguous → ask which feature.
- `features/<feature>/implementation/<slug>.md` — explicit path.
- `<path>.md` — any chunk plan path; freestanding `.scratch/*.md` plans are accepted (they have no decisions.md / engineering-plan.md authority sources).
- (no argument) — list `features/*/implementation/*.md` whose frontmatter does NOT have `Status: needs-user-input` (i.e., not mid-cycle), ask which to execute.

Optional flags:

- `--no-pr` — stop before invoking `/open-pr`; leave working tree dirty for the user to inspect.
- `--no-review` — stop after `/open-pr` succeeds; do not invoke `/review-pr-v2`.
- `--resume` — explicit signal that implementation was previously started (e.g., a prior `/execute-plan` was interrupted). Skip re-running already-completed acceptance criteria; pick up where the chunk plan's checklist last marked done.

## Workflow

```
State load                   (deterministic, hard short-circuit)
  ↓ Status frontmatter check; Status: needs-user-input → REFUSE
Authority-stack read          (deterministic; reads decisions.md, engineering-plan.md, brief.md)
  ↓
Context-pack ingest           (deterministic; Reads every file the plan names)
  ↓
Pre-implementation gates      (deterministic)
  ↓ Gate 1: /plan-lint clean
  ↓ Gate 2: baseline typecheck/lint/test green (scoped by Owns set)
  ↓        baseline RED → REFUSE (zero-tolerance for pre-existing failures)
  ↓ Gate 3: HEAD recorded (re-checked at AC sweep + pre-/open-pr)
Test-first authoring          (LLM judgment, applies edits)
  ↓ writes every "Tests to add" case from the plan; runs the suite; expects new tests to FAIL (RED)
Minimal implementation        (LLM judgment, applies edits)
  ↓ smallest delta to flip new tests to GREEN; honors Factoring Contract Owns (writes) / Reads (no writes) / Forbidden
Acceptance-criteria sweep     (LLM judgment + deterministic verification)
  ↓ every AC item observed; commands run, behaviors checked, files created
  ↓ HEAD re-check on entry
Pre-PR verification           (deterministic gates)
  ↓ typecheck = 0 errors; lint = clean; full test suite = green; /plan-lint = clean
  ↓ HEAD re-check before hand-off
Hand off to /open-pr          (skill tool invocation by main-thread agent)
  ↓ unless --no-pr; /open-pr is autonomous and reads the working tree
Hand off to /review-pr-v2     (skill tool invocation by main-thread agent)
  ↓ unless --no-review; /review-pr-v2 reads the current branch's PR via gh
```

There is no inner loop within a single skill invocation. If the user discovers an issue mid-implementation that requires re-planning, the skill stops, surfaces the finding as `OPEN_QUESTION` (or `PLAN_AMENDMENT_NEEDED` when the chunk plan itself is wrong), and the user re-invokes `/plan-author --rewrite` or escalates to `/engineering-plan-author --rewrite` per the standard re-planning path.

---

## State load (MANDATORY, HARD SHORT-CIRCUIT)

`Read` the chunk plan. Extract the YAML frontmatter `Status:` value.

`Status:` is a binary mid-cycle signal: `needs-user-input` (mid-cycle) or absent (ready). Lifecycle signals (in-progress, merged, verified) come from branch / PR / merge state, not frontmatter.

- **`Status: needs-user-input`** → stop. The plan is mid-cycle authoring state (the partial draft was written by `/plan-author` with a `## Pending blockers` section; the user is between resolving blockers and re-invoking the author skill). Emit:

  ```
  PLAN: <plan-path>
  STATUS: REFUSED (artifact in mid-cycle authoring state)

  This chunk plan has frontmatter `Status: needs-user-input`. The author skill
  (`/plan-author`) wrote it as a partial draft with unresolved blockers listed in
  the `## Pending blockers` section. Implementing a partial draft would lock in
  product/architecture decisions the user is still arbitrating.

  Resolve the blockers in `## Pending blockers`, then re-invoke `/plan-author --rewrite
  <feature>/<chunk-slug>`. The author skill removes the `Status:` frontmatter on a
  successful APPROVED emission; re-invoke `/execute-plan` once the plan is back to
  no-Status-field state.
  ```

- **No `Status:` field, OR any other value** → proceed conditionally on the sidecar check below.

**Sidecar check (draft mode):** `Read` `~/.claude/cache/author-state/<feature>__<chunk-slug>.json`. If `authoring_mode: "draft"` is set, REFUSE — the plan was written via `/plan-author --draft`, which skipped Plan-lint, Ground-truth audit, and Self-prosecution. Implementing a draft plan ships hallucinations. Emit:

  ```
  PLAN: <plan-path>
  STATUS: REFUSED (plan is unhardened — author sidecar reports authoring_mode: "draft")

  The plan-author sidecar at <path> reports authoring_mode: "draft", meaning
  `/plan-author --draft` was invoked. Plan-lint, Ground-truth audit, and Self-prosecution
  were all skipped. Implementing a draft plan would ship hallucinations.

  Re-invoke `/plan-author --rewrite <feature>/<chunk-slug>` without `--draft`, then
  `/plan-review-v2`, then `/execute-plan`.
  ```

If sidecar is absent or `authoring_mode != "draft"`, proceed.

**Branch/PR state check (lifecycle):** Before proceeding, check whether the chunk has already shipped: `gh pr list --search "head:<branch> is:merged" --json number,state` (or equivalent). If a merged PR exists for the current branch AND the chunk plan slug appears in the PR title/body, surface a warning in the verdict ("this chunk appears already-merged in PR #N; proceeding only if --resume was explicitly passed"). The git history is the canonical lifecycle truth; the chunk plan does not carry it.

The Status check is deterministic and runs first.

**On `--resume` semantics.** The `--resume` flag tells `/execute-plan` to skip already-passing acceptance criteria and not re-write tests that already exist with the right assertions — useful when an earlier run was interrupted between the test-first phase and the implementation phase. It is independent of the Status check; pass `--resume` whenever you want the skill to pick up partial progress, regardless of frontmatter.

---

## Authority-stack read (MANDATORY, DETERMINISTIC)

The plan has explicit upstream authority sources. The implementer must Read them in order, top to bottom:

1. **`features/<feature>/decisions.md`** (if the chunk plan is under `features/`) — durable arbitration record. Bound entries CANNOT be contradicted by the implementation. If the chunk plan asserts something contradicting a bound decision, this is a chunk-plan defect surfaced via `PLAN_AMENDMENT_NEEDED`; stop and ask the user to re-invoke `/plan-author --rewrite`. Skip if the file does not exist (freestanding plans).
2. **`features/<feature>/engineering-plan.md`** (if the chunk plan is under `features/`) — chunk DAG, cross-chunk invariants, decisions closure. Verify:
   - The chunk's slug appears in the chunk index.
   - The chunk's `Code deps` (other slugs) are either already shipped on `main` (check git log) OR present in the working directory's prior chunks already merged. Unmet deps → stop and surface.
   - Cross-chunk invariants in the engineering plan's Invariants section apply to this chunk's implementation.
3. **`features/<feature>/brief.md`** (if the chunk plan is under `features/`) — Goals, Non-goals, User-facing changes. The chunk plan's Brief link section names the brief Goals this chunk serves; the implementation must deliver them.
4. **The chunk plan itself** — the contract.

**Authority order when artifacts disagree** (highest to lowest): `decisions.md > engineering-plan.md > chunk plan > brief.md`. The brief is the highest-leverage but least-specific source; specific bound decisions and contracts beat brief intentions.

Note that *authority order* is not the same as *read order*. The implementer reads top-down (brief first to set the "why", then the engineering plan, the chunk plan, decisions.md), but applies arbitration bottom-up: when two artifacts disagree, the lower-numbered (more authoritative) wins. This is consistent across `/brief-review-v2`, `/engineering-plan-review-v2`, `/plan-review-v2`, and this skill — every layer reads upstream context first but defers to the bound-arbitration record (`decisions.md`) when conflicts surface.

If the chunk plan asserts something contradicting an upstream source, this is a chunk-plan defect. Surface as `PLAN_AMENDMENT_NEEDED`; do NOT auto-fix. The user re-invokes `/plan-author --rewrite` to land the corrected plan.

If two upstream sources contradict each other (e.g., decisions.md says X, engineering-plan.md says Y), surface as `OPEN_QUESTION` — implementation cannot proceed without arbitration.

---

## Context-pack ingest (MANDATORY, DETERMINISTIC)

The chunk plan's "Context pack" section names every file the implementer must Read before starting. This is the section that exists to skip the rediscovery phase. Read each file in full.

If the Context pack names files that do not exist:

- **Single typo / casing mismatch** → look for a near-match file; if exactly one exists, proceed and surface in the verdict ("plan cited `<wrong-path>`; used `<correct-path>` based on case-insensitive match").
- **Multiple matches or no near-match** → stop and surface as `PLAN_AMENDMENT_NEEDED` ("Context pack cites `<path>` which does not exist; user arbitrates").

If the Context pack omits files the implementation will obviously need (e.g., the chunk modifies `backend/src/foo.ts` but the Context pack does not include it), Read them anyway but flag as a SOFT plan-quality finding for the post-implementation summary — the chunk plan should be amended to include them on the next round.

---

## Pre-implementation gates (MANDATORY, DETERMINISTIC)

Run these gates in order. Each must pass before the next runs. Any FAIL stops the skill before any implementation begins.

### Gate 1: /plan-lint

```bash
python3 ~/.claude/skills/plan-lint/lint.py <chunk-plan-path>
```

The chunk plan should have already passed `/plan-lint` at author/review time. Re-running is a defensive check — if the user edited the plan since review (legitimately fixing a typo, or illegitimately weakening a Factoring Contract field), the lint will catch it. FAIL → stop and surface `STRUCTURAL_LINT_FAILED` with the lint output.

### Gate 2: Baseline test/typecheck health (zero-tolerance for pre-existing failures)

Per `CLAUDE.md`'s zero-tolerance rule, the codebase must be green BEFORE implementation begins. Run:

```bash
cd backend && npm run typecheck
cd backend && npm run lint
cd backend && npm test
cd mobile && npm run lint
cd mobile && npm test
```

(Adjust commands per the project's actual scripts — read `package.json` first if commands differ.)

- **All green** → record baseline; proceed.
- **Any RED** → stop. Per CLAUDE.md zero-tolerance rule, "every session should leave the codebase strictly better than you found it" — accepting a RED baseline means the implementation's later RED-then-GREEN cycle cannot distinguish the new failure from the pre-existing one. Surface as `BASELINE_RED`:

  ```
  STATUS: REFUSED (baseline RED — pre-existing failures)

  Per CLAUDE.md § Pre-Existing Failures, the codebase must be green before
  implementation begins. The following gates failed on the current HEAD:

  - <command>: <one-line failure summary>
  - <command>: <one-line failure summary>

  Per zero-tolerance rule, fix the pre-existing failures FIRST (separate from
  this chunk's work — they are not "out of scope"), then re-invoke /execute-plan.
  ```

  This is the same discipline `/review-pr-v2` enforces at PR-review time, applied at execution time.

**Scoping by Owns set.** If every entry in the chunk plan's `Owns (writes)` set is under `backend/`, run only the `backend/` gates; if every entry is under `mobile/`, run only the `mobile/` gates; otherwise run both. The Pre-PR verification stage at the end of the skill always runs the full local CI equivalent regardless — Gate 2 is the cheap baseline check, Pre-PR verification is the comprehensive shipping gate.

### Gate 3: HEAD record + checkpoints

`git rev-parse HEAD` once and record. The HEAD SHA is re-checked at three later points:

- **Entry to Acceptance-criteria sweep** — the implementer is finished writing code; if HEAD has moved (a parallel worktree committed; the user pulled main), the implementation is now against a stale base.
- **Immediately before invoking `/open-pr`** — last chance to detect drift before the PR opens against the wrong base.

Drift at any checkpoint → surface `REPO_STATE_DRIFT` with both SHAs and stop. The skill does NOT auto-restart — the user re-invokes against the new HEAD after deciding whether to rebase or abort.

---

## Test-first authoring (MANDATORY, TDD DISCIPLINE)

Per `CLAUDE.md` § "Test-Driven Development (TDD) - MANDATORY" and the chunk plan's "Tests to add" section, write every test case BEFORE writing implementation.

### 1. Read the "Tests to add" section verbatim

Each enumerated case has a behavior under test + assertion shape (per `P-CHUNK-TEST-PATHS` — actual file paths come from the test layout, not the plan body).

### 2. Determine test file paths

For each test case:

- **Modifying a function** → test belongs in the existing test file for that module (find via `git ls-files | grep <module>.test.`).
- **New module** → new test file in the conventional location (`backend/src/__tests__/<module>.test.ts` or sibling `<module>.test.ts`, follow what the rest of the codebase does — Read the test layout the audit recorded).
- **Integration / e2e** → use the project's existing integration test directory (`backend/test/integration/`, `mobile/.maestro/`, etc.).

If the right test file location is genuinely ambiguous, ask the user before writing.

### 3. Write the test bodies

Per the chunk plan's "Tests to add" specification. Make each test:

- Name the behavior under test in the description (`it('returns null when the user is not authenticated', ...)`)
- Assert the exact expected output / state / side effect.
- Cover both golden path AND the edge cases the plan enumerates.
- Use existing test conventions (mocking patterns, fixture loading, setup/teardown) — DO NOT invent new patterns. Read sibling test files first.

### 4. Run the new tests; expect RED

```bash
cd backend && npm test -- <new-test-file>
# OR
cd mobile && npm test -- <new-test-file>
```

- **All new tests RED** → expected; the implementation has not been written yet. Proceed.
- **Any new test GREEN** → distinguish three cases:
  - **(i) The behavior already exists in the codebase** — the chunk plan is wrong; the test is testing existing behavior. Surface as `PLAN_AMENDMENT_NEEDED`; the chunk plan claims behavior that the codebase already provides.
  - **(ii) The test assertion is too weak** — the test passes against undefined or partially-implemented behavior. Strengthen the assertion before proceeding (a test that passes against unimplemented code is a test that won't catch regressions).
  - **(iii) The new test's name collides with an existing test** — the test name matches an existing one but the assertion is genuinely additive (more specific shape, narrower predicate, or covers an edge case the existing test missed). Rename the new test to disambiguate (`it('returns null when X AND Y', ...)` rather than `it('returns null', ...)`), then re-run. If the renamed test still passes, that's case (i) or (ii); diagnose and handle accordingly.

DO NOT proceed to implementation until every new test is RED for the right reason (the assertion is correct AND the implementation does not yet exist).

---

## Minimal implementation (MANDATORY, GREEN DISCIPLINE)

Write the smallest code change that flips every new test from RED to GREEN, while honoring the chunk plan's Factoring Contract.

### Factoring Contract enforcement

The chunk plan's Factoring Contract section enumerates:

- **Owns (writes)** — exact paths this chunk creates or modifies. Edits outside Owns are forbidden. The label matches the chunk template (`features/_template/chunk.md`) verbatim.
- **Reads (no writes)** — files this chunk depends on but does NOT modify. If implementation requires modifying a file in Reads, that's a Factoring Contract violation; surface as `PLAN_AMENDMENT_NEEDED`. The label matches the chunk template verbatim.
- **Forbidden** — files / patterns / abstractions explicitly out of bounds.
- **Single concern** — the chunk does ONE thing. If implementation requires doing two things, decompose at chunk-plan level (re-invoke `/engineering-plan-author --rewrite` to split the chunk).
- **No scaffolding** — don't create premature abstractions; the chunk has < 2 already-merged consumers means the abstraction is invalid (per `/plan-lint`).
- **Abstraction earns its place** — extract only when there's a concrete second consumer.

The Factoring Contract is machine-checked at `/plan-lint` time and re-checked at `/review-pr-v2` time. Violating it during implementation is a forbidden operation; if the implementation truly requires it, the chunk plan is wrong and the user re-invokes `/plan-author --rewrite`.

### TDD cycle

For each test case (or related cluster):

1. **RED**: confirm the new test fails for the right reason (assertion correct, implementation absent).
2. **GREEN**: write the minimum code to flip RED → GREEN. Don't add unrelated features. Don't pre-emptively handle edge cases the test doesn't enumerate.
3. **REFACTOR**: if the GREEN code introduces duplication or violates project style, refactor — but ONLY where tests still pass. Refactoring that requires test changes is forbidden (TESTS ARE SPEC per CLAUDE.md).

### Forbidden during implementation

- Modifying tests to make them pass. Tests are the spec; if a test is wrong, it's a chunk-plan defect → `PLAN_AMENDMENT_NEEDED`.
- Adding `.skip()` / `.todo()` to silence a failing test (per CLAUDE.md "Forbidden Test Modifications").
- Editing files outside the Factoring Contract's Owns set.
- Editing `decisions.md` (only `/plan-author --rewrite`, `/engineering-plan-author --rewrite`, or manual user action edits decisions.md).
- Editing `engineering-plan.md` (frozen once approved per `features/README.md`).
- Editing the chunk plan itself (the implementer never edits the contract; the user re-invokes `/plan-author --rewrite` if the plan is wrong).
- Bypassing dependency conflicts with `--legacy-peer-deps` or `--force` (per CLAUDE.md "Package Management").
- Running `prisma migrate dev` directly (per CLAUDE.md "Database Protection"; use `npm run db:migrate`).

### Allowed during implementation

- Auto-fixing pre-existing lint warnings encountered while editing a file (per CLAUDE.md "Fix pre-existing issues" rule — the codebase should be strictly better when you leave it). These fixes accompany the chunk's commit; surface in the verdict's "ancillary fixes" line.
- Auto-fixing pre-existing lint warnings in OTHER (untouched) files that the lint run surfaces during Pre-PR verification. Per CLAUDE.md zero-tolerance ("every session should leave the codebase strictly better than you found it"), encountered warnings ARE the implementer's burden to fix. Surface every such fix in the verdict's "ancillary fixes" line so the reviewer can see exactly what changed beyond the chunk's Owns set.
- Renaming variables, adding types, extracting helpers WITHIN the Owns set when it improves readability and tests still pass.
- Updating snapshots when behavior intentionally changed AND the new snapshot matches the new test assertions.
- **Trivial out-of-scope fixes (narrow carve-out):** typo / comment / dead-code fixes in files outside the Owns set — capped at ≤3 lines, no behavior change, no new test coverage need — MAY be applied as ancillary fixes when encountered. Anything beyond 3 lines, OR any behavior change, OR any new test coverage gap surfaces as `PLAN_AMENDMENT_NEEDED` (the chunk plan should grow to absorb the work, OR a separate chunk should land first). The carve-out exists because re-invoking the full plan-author + plan-review pipeline for a one-character correction is disproportionate; it does NOT exist to launder scope creep. The Pre-PR review (`/review-pr-v2`) catches misuse: any "trivial" fix that exceeds the cap is flagged as a Factoring Contract violation.

---

## Acceptance-criteria sweep (MANDATORY)

The chunk plan's "Acceptance criteria" section enumerates observable, testable conditions for "done." Each item names a command, test, file+symbol, gate, or user-visible behavior — never a vague verb (`/plan-lint` rejects vague items at plan time).

For each item:

1. **Identify the verification mechanism.** Is it a command (run it)? A test (does the test pass)? A file existence check (does it exist)? A behavior in the running app (test it)?
2. **Run the verification.** Capture the output.
3. **Compare to expected.** The plan states what "passing" looks like.
4. **Record.**

Output a per-item table:

```
### Acceptance criteria sweep

| Item | Mechanism | Result | Notes |
|---|---|---|---|
| 1. `npm run typecheck` reports 0 errors in `backend/` | typecheck | PASS | — |
| 2. New `searchAuthors` query returns ≥1 hit for "Jane Doe" | integration test | PASS | `__tests__/searchAuthors.test.ts` |
| 3. Existing watchlist test still passes | regression | PASS | full suite green |
| ... | ... | ... | ... |
```

Any FAIL → diagnose. If implementation gap → fix. If the AC is genuinely unverifiable as written → surface as `PLAN_AMENDMENT_NEEDED` (the AC was vague enough to slip past `/plan-lint`).

DO NOT mark the chunk implemented until every AC observably passes.

---

## Pre-PR verification (MANDATORY, ZERO-TOLERANCE)

Per `CLAUDE.md` § "CI Verification (Non-Negotiable)" and § "Pre-Existing Failures", before opening a PR run the full local CI equivalent:

```bash
cd mobile && npm run lint
cd backend && npm run lint && npm run typecheck && npm test
cd mobile && npm test
python3 ~/.claude/skills/plan-lint/lint.py <chunk-plan-path>
```

(Adjust commands per the project's actual scripts.)

- **All green** → proceed to /open-pr.
- **Any RED** → fix and re-run. Do NOT push code that will fail CI.

If a regression appears that the new tests don't cover (the implementation broke a pre-existing test):

1. Read the failing test.
2. Determine whether the new behavior is actually correct (the test was wrong) or wrong (the implementation broke an invariant).
3. **The test was wrong** → this is a TDD discipline failure. The new chunk's behavior change should have been captured in a NEW test, not by modifying an existing one. Surface as `PLAN_AMENDMENT_NEEDED`: the chunk plan's "Tests to add" section was incomplete.
4. **The implementation was wrong** → fix the implementation; the existing test was guarding the right invariant.

Never weaken or skip a failing pre-existing test to make implementation pass.

---

## Hand off to /open-pr

`/open-pr` is autonomous — it takes no arguments, reads the working tree, decides the commit-chunking, drafts the PR title/description from the diff content, pushes the branch, and runs `gh pr create`. `/execute-plan`'s job is to leave the working tree in a state that `/open-pr` can ship cleanly:

- Implementation complete (every Acceptance criterion observed PASS).
- Pre-PR verification green (typecheck / lint / test / `/plan-lint` all clean).
- Working tree contains ONLY the chunk's intended changes plus any ancillary fixes (per the Allowed-during-implementation rules); no stray files, no leftover debug prints, no `.scratch/` artifacts staged.

When the working tree is in that state, the next move is:

```
[Invoke the Skill tool with skill: open-pr]
```

The skill invocation pattern in Claude Code is the Skill tool, not programmatic chaining — `/execute-plan` does NOT call `/open-pr` automatically. After this skill emits its verdict, the agent in the main thread invokes `/open-pr` next. (If running in a non-Claude-Code environment, the user runs `/open-pr` manually.) Pass through any `--no-pr` flag by stopping before this hand-off; emit the no-PR verdict template (below) and the user inspects the working tree.

`--no-pr` verdict template (when `/execute-plan` was invoked with `--no-pr`):

```
## Implementation complete: <chunk-slug>

All gates green. Working tree dirty with implementation changes.

Files modified: <count>
Tests added: <count>
Acceptance criteria observed: <count>/<total>

Next step: invoke `/open-pr` (Skill tool) to commit and open the PR, or inspect
the working tree first. /execute-plan stopped before /open-pr per --no-pr flag.
```

---

## Hand off to /review-pr-v2

After `/open-pr` returns and the PR exists on GitHub, the next step is `/review-pr-v2` — the post-execution review gate that catches:

- Premise inversions in the diff (claims in code comments / docstrings that don't survive verification).
- Factoring Contract violations the implementer missed.
- Gaps in test coverage for behavior the diff introduces.
- Cross-cutting impact the chunk plan didn't anticipate.

The skill invocation pattern is the same — the agent in the main thread invokes:

```
[Invoke the Skill tool with skill: review-pr-v2]
```

after `/open-pr` succeeds. `/review-pr-v2` reads the current branch's PR via `gh pr view`, so it does not need arguments. (`/execute-plan` does NOT chain into `/review-pr-v2` programmatically.)

To detect that `/open-pr` succeeded before invoking the next skill, check the working-tree state: `git rev-parse @{u}` should report the branch is now tracking the remote, and `gh pr view --json url --jq .url` should return a non-empty URL. If `/open-pr` failed (rare; usually a `gh` auth or push issue), surface the failure and do NOT invoke `/review-pr-v2` — the user fixes the underlying issue and re-runs `/open-pr`.

If `/review-pr-v2` returns `APPROVED`, the chunk is shippable. The user can merge.

If `/review-pr-v2` returns `NEEDS USER INPUT`, the verdict surfaces blockers; subsequent fixes go through `/review-pr-v2`'s same-round re-prosecution machinery on the next invocation.

If the user passed `--no-review`, skip this step. The PR is open and unreviewed; the user runs `/review-pr-v2` later.

---

## Output (verdict template)

```
## Execute Plan Complete: <chunk-slug>

**Plan path:** <path>
**Authority sources read:**
  - decisions.md: <SHA at gate; entries consulted: N>
  - engineering-plan.md: <verified chunk slug + deps + invariants>
  - brief.md: <Goals served: N>
  - chunk plan: <ACs: N>

**Pre-implementation gates:**
  - /plan-lint: PASS
  - Baseline test/typecheck/lint: PASS (scoped to <backend / mobile / both>)
  - HEAD record: <sha at start>; checkpoints (AC-sweep entry, pre-/open-pr): <unchanged | DRIFT detected → REPO_STATE_DRIFT>

**Test-first:** <N tests added>; all RED before implementation
**Implementation:** <files modified: N>; Factoring Contract honored: <Owns-only edits: bool>
**Acceptance criteria:** <N/N items observed>

**Pre-PR verification:**
  - typecheck: PASS  - lint: PASS  - test: PASS  - /plan-lint: PASS

**Ancillary fixes (pre-existing issues fixed in passing):** <N>
  - <one-line per fix>

**PR opened:** <PR URL or "skipped (--no-pr)">
**/review-pr-v2 verdict:** <APPROVED | NEEDS USER INPUT | "skipped (--no-review)">

### Status: COMPLETE / BLOCKED

(if BLOCKED, the blocker class + actionable resolution path)
```

---

## Hard rules

- **Status check is mandatory and runs first.** `Status:` is a binary mid-cycle signal: `needs-user-input` → REFUSE; absent or anything else → proceed (subject to the sidecar draft check). The plan-author sidecar's `authoring_mode: "draft"` field is the unhardened-plan signal that also REFUSES. Lifecycle states (in-progress, merged, verified) are derived from branch / PR / merge state, not frontmatter.
- **Authority-stack read is mandatory.** Read decisions.md, engineering-plan.md, brief.md, and the chunk plan in that order. Authority order when conflicts surface (highest to lowest): `decisions.md > engineering-plan.md > chunk plan > brief.md`. The chunk plan is the contract; the upstream artifacts are the constraints.
- **Pre-implementation gates are mandatory.** `/plan-lint` re-check, baseline test/typecheck/lint health (per CLAUDE.md zero-tolerance rule), and HEAD record all pass before any test or implementation code is written.
- **HEAD record + drift checkpoints are mandatory.** HEAD is captured at Gate 3 and re-checked at the entry to Acceptance-criteria sweep AND immediately before `/open-pr` hand-off. Any drift is `REPO_STATE_DRIFT`; the skill does not auto-restart.
- **TDD is non-negotiable.** Every "Tests to add" case is written and confirmed RED before the corresponding implementation code is written. Tests are NEVER modified to fit the implementation — if a test is wrong, the chunk plan is wrong and the user re-invokes `/plan-author --rewrite`.
- **Tests-as-spec is non-negotiable.** Per CLAUDE.md § Critical Rules item 8 ("Tests are spec") and § Test Removal/Simplification Criteria, tests are not removable or weakenable to make implementation pass. Removing or weakening a test surfaces as `PLAN_AMENDMENT_NEEDED` and stops; the user must justify the removal against spec.md before any test change lands.
- **Factoring Contract is binding.** Edits outside the chunk plan's `Owns (writes)` set, additions to `Forbidden`, or expansion beyond `Single concern` are forbidden operations; surface as `PLAN_AMENDMENT_NEEDED`. The narrow trivial-fix carve-out (≤3 lines, no behavior change, no test gap) is the only exception.
- **Out of scope is binding.** The chunk plan's "Out of scope" section names work that explicitly does NOT happen in this chunk; pulling adjacent fixes in is a Factoring Contract violation (modulo the trivial-fix carve-out).
- **Decisions.md is read-only at execution time.** The implementer never edits `decisions.md`; if a finding requires amending it, surface as `OPEN_QUESTION`.
- **Engineering-plan.md is read-only at execution time.** Frozen once approved per `features/README.md`. If a finding requires amending it, surface as `OPEN_QUESTION` and the user re-invokes `/engineering-plan-author --rewrite`.
- **Pre-existing failures are zero-tolerance.** Per CLAUDE.md, "every session should leave the codebase strictly better than you found it." Pre-existing typecheck / lint / test failures are fixed BEFORE the chunk's implementation begins (Gate 2), AND any further pre-existing warnings encountered during Pre-PR verification are also fixed (in touched OR untouched files) and surfaced in the verdict's ancillary-fixes line.
- **Pre-PR verification is mandatory.** Full local CI equivalent runs before `/open-pr` is invoked.
- **Package management discipline.** Per CLAUDE.md § Package Management, NEVER use `--legacy-peer-deps` or `--force` to bypass dependency conflicts; resolve them properly. Per § Database Protection, NEVER run `prisma migrate dev`; use `npm run db:migrate`.
- **Hand-off pattern is non-programmatic.** `/execute-plan` does NOT call `/open-pr` or `/review-pr-v2` programmatically. After Pre-PR verification passes, the agent in the main thread invokes the Skill tool with `skill: open-pr`, then with `skill: review-pr-v2` after the PR opens. `--no-pr` and `--no-review` flags stop the hand-off chain at the corresponding step.
- **Always** prefer `Read` / `Edit` / `Write` over Bash for file I/O (per global CLAUDE.md tool-selection rule).
- **Never** mark the chunk implemented while any gate is RED, any AC is unobserved, or any blocker is unresolved.

## Compliance self-check (before invoking /open-pr)

- [ ] Status frontmatter check ran first; not bypassed. Refused on `Status: needs-user-input` (mid-cycle); plan-author sidecar consulted and refused on `authoring_mode: "draft"`; otherwise proceeded.
- [ ] Authority-stack read complete: decisions.md, engineering-plan.md, brief.md, chunk plan all Read in that order. Authority order applied when conflicts surfaced.
- [ ] Context-pack ingest complete: every file the plan names was Read.
- [ ] Pre-implementation gates passed: /plan-lint clean; baseline test/typecheck/lint green; HEAD recorded.
- [ ] HEAD checkpoints honored: re-checked at Acceptance-criteria entry AND before /open-pr hand-off; no drift detected (or `REPO_STATE_DRIFT` surfaced).
- [ ] Test-first: every "Tests to add" case was written and confirmed RED before any implementation. New-test-passing-immediately cases distinguished into (i)/(ii)/(iii) per the disambiguation rule.
- [ ] Implementation: edits stayed within Factoring Contract `Owns (writes)` set OR within the trivial-fix carve-out (≤3 lines, no behavior change, no test gap); no test modifications.
- [ ] Tests-as-spec: no test removed, weakened, or skipped to make implementation pass.
- [ ] Acceptance criteria: every AC item observed PASS.
- [ ] Pre-PR verification: full local CI equivalent green; ancillary fixes in untouched files (if any) recorded in the verdict.
- [ ] No edits to decisions.md, engineering-plan.md, or the chunk plan itself.
- [ ] No --legacy-peer-deps / --force / prisma migrate dev / hook-skipping.
- [ ] Hand-off pattern honored: ready to invoke `/open-pr` (Skill tool) next; not chained programmatically.

---

## Edge cases

- **Chunk plan path resolution ambiguous** (multiple `features/*/implementation/<slug>.md` matches): stop and ask which feature.
- **Chunk plan exists with no `Status:` frontmatter**: this is the canonical APPROVED state since the Status-binary cleanup. Proceed normally.
- **Engineering plan declares `Code deps` not yet shipped**: stop. Surface: "this chunk depends on `<other-slug>`, which is not yet on `main`. Implement `<other-slug>` first, OR re-invoke `/engineering-plan-author --rewrite` if the dep is incorrect."
- **Cross-chunk file conflict** (this chunk's Owns set overlaps another in-flight chunk's Owns set): stop. Surface as `OPEN_QUESTION` — the engineering plan claimed parallelism that doesn't hold.
- **Plan claims tests that already exist with the same name**: this is the "test passes immediately because behavior already exists" case under Test-first authoring step 4. Surface as `PLAN_AMENDMENT_NEEDED`.
- **TDD cycle reveals the chunk plan's "Tests to add" is incomplete** (implementation passes the listed tests but other tests fail): surface as `PLAN_AMENDMENT_NEEDED`. The chunk plan should have enumerated the regression-protection tests too.
- **Mid-implementation discovery of a needed cross-cutting change** (e.g., implementing the chunk reveals a missing helper that other code paths also need): stop. Surface as `OPEN_QUESTION`. The right move is either (a) extract to a separate chunk via engineering-plan amendment, or (b) include the helper in this chunk's Owns set via plan amendment. Either way, the user re-plans, not the implementer.
- **HEAD changes mid-execution**: emit `REPO_STATE_DRIFT`. User re-runs.
- **Worktrees**: per CLAUDE.md "Git Worktrees", each worktree has independent dependencies and database; this skill operates on whichever worktree it was invoked in. The Pre-implementation gates run in that worktree's tree; the PR opens against that worktree's branch.
- **Database migrations in the chunk's Owns set**: per CLAUDE.md "Database Protection (Non-Negotiable)", use `npm run db:migrate` (the safe wrapper). NEVER `prisma migrate dev`. Always `npm run db:snapshot` before applying. The chunk plan should have named these in the AC; if not, the chunk plan is incomplete.
- **`--no-pr` and the working tree contains existing uncommitted changes** (the user had work in progress before invoking `/execute-plan`): stop. Refuse. The skill's working-tree contract is "clean before, modifications-from-this-chunk after"; mixed-state working trees produce ambiguous diffs at PR review time.

---

## Relationship to sister skills

- **`/plan-author`** writes the chunk plan this skill consumes. The author's verification (ground-truth + self-prosecution) means this skill's State-load Status check is the only frontmatter-level gate at execution time — the author already ensured the plan is shape-correct.
- **`/plan-review-v2`** prosecutes the chunk plan AFTER the author and BEFORE this skill. By the time `/execute-plan` runs, the plan should have no `Status:` frontmatter (author skill removed it on APPROVED emission). The Status check doesn't require evidence of review (no skill writes a "reviewed" marker), so a user could in principle invoke `/execute-plan` against an unreviewed plan; this skill warns in the verdict by checking whether `~/.claude/cache/review-state/<feature>__<chunk-slug>.json` exists with a recent APPROVED verdict.
- **`/open-pr`** handles commit-chunking and PR creation. This skill writes the implementation; `/open-pr` ships it.
- **`/review-pr-v2`** is the post-execution gate. After `/open-pr` succeeds, the agent in the main thread invokes the Skill tool with `skill: review-pr-v2` (unless `--no-review` was passed). The hand-off is the agent's responsibility — `/execute-plan` does not call `/review-pr-v2` programmatically.
- **`/engineering-plan-author`** is invoked when the chunk plan reveals an engineering-plan defect (false parallelism, missing chunk, wrong invariant). The user re-invokes that skill, not this one.
- **`/brief-author`** is invoked when the chunk plan reveals a brief defect (Goal that doesn't trace, Non-goal that should have been a Goal). The user re-invokes that skill upstream, then re-runs the engineering-plan + chunk-plan + execute chain.

The five-skill chain — `/brief-author` → `/engineering-plan-author` → `/plan-author` → `/execute-plan` → `/review-pr-v2` — is the canonical feature-delivery pipeline for this project. Each skill enforces its own discipline; together they make hallucinated work, weakened tests, and Factoring Contract violations all at-author-time defects rather than at-review-time defects.
