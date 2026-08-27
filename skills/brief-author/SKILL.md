---
name: brief-author
description: Writes or rewrites a feature's `brief.md` — the upstream source-of-truth the engineering plan and chunk plans descend from — applying ground-truth verification and self-prosecution at write time rather than review time. Run once per cycle, then `/brief-review-v2`. Sister to `/engineering-plan-author` and `/plan-author`.
user-invocable: true
---

# Brief author

Produces or rewrites `features/<feature>/brief.md` with the same prosecution rigor `/plan-review-v2` applies, but front-loaded at write time.

The brief is the highest-leverage artifact in the feature lifecycle: every downstream artifact (engineering plan, chunk plans, code) descends from it. A brief that contradicts its own Goals, invents a user population, or smuggles a Non-goal-violating Goal will cascade five rounds of review machinery to surface — and the surface itself doesn't repair the brief, only the descendants.

## Inputs

- `$ARGUMENTS` (optional):
  - `<feature>` — the feature directory under `features/`. If absent, infer from the current working directory or ask the user.
  - `--spec <slug>` — the parent spec this feature's brief descends from, resolving to `specs/<slug>/spec.md`. The override for a project whose `specs/` tree holds several spec folders; Source ingest § Parent-spec resolution defines the full order and the single-root-`spec.md` path that needs no argument.
  - `--draft` — quick-exploration mode; skip ground-truth and self-prosecution; emit a sidecar marked `authoring_mode: "draft"` (unhardened by choice; downstream reviewers warn rather than refuse).
  - `--no-worktree` — (when your project provides a worktree bootstrap script) skip **Brief-worktree provisioning** and author in the current checkout. Use when you deliberately want the brief written in place — e.g. you are already set up in the tree you want it to land in, or you are consciously not using a per-brief branch.

**The author runs once per cycle.** It produces the first draft; the next step in the cycle is to run `/brief-review-v2`, and the session agent then applies its findings — plus your blocker resolutions — directly to `brief.md`. The author is not re-invoked to apply changes. There is no `--rewrite` flag. When `features/<feature>/brief.md` already exists or its author sidecar is present, invoke `/brief-author <feature>` again only for an explicit clean-slate re-author (ask in plain language); that fresh run treats the existing brief and any prior review state as carry-forward constraints — a Goal/Non-goal the user already removed is not re-introduced.

## Sidecar location

`~/.claude/cache/author-state/<feature>__brief.json`. Same directory as `~/.claude/cache/review-state/`'s sibling pattern. The reviewer skills (engineering-plan-review-v2 reading the brief upstream of the engineering plan it reviews) consult this sidecar to skip re-prosecuting claims the author already verified.

---

## Workflow

```
State load (deterministic; ~5 seconds)
  ├─ mkdir -p ~/.claude/cache/author-state (the directory may not exist on the
  │   first author-skill invocation; Write does NOT auto-create parents and the
  │   reviewer-side machinery only creates ~/.claude/cache/review-state)
  ├─ Read sidecar at ~/.claude/cache/author-state/<feature>__brief.json (if exists)
  ├─ Read review-state at ~/.claude/cache/review-state/<feature>[__<track>]__engineering-plan.json
  │   (every track of a tracked feature; warm carry-forward at brief layer)
  └─ Determine cold vs warm mode

Brief-worktree provisioning (when a bootstrap script exists; deterministic; plain `git worktree add` off origin/main — the script itself is NOT used)
  ├─ No-op (author in place) when: --no-worktree, already inside a linked worktree, or no worktree bootstrap script
  ├─ WT_NAME = BRANCH = <feature>-brief; reuse .worktrees/<feature>-brief if it exists on branch <feature>-brief; else create off origin/main
  │   (git fetch origin main; git branch <feature>-brief origin/main; git worktree add .worktrees/<feature>-brief <feature>-brief)
  ├─ Re-anchor cwd to the worktree — every repo read below (the parent spec + its decisions log, category specs, CLAUDE.md, existing brief/decisions)
  │   and the brief write resolve inside it
  └─ Cold-create fallback: an existing brief.md / decisions.md not yet on origin/main is read from the
      invocation checkout by absolute path; the new draft still lands in the worktree

Source ingest (deterministic; ~30 seconds — runs inside the brief worktree when provisioned)
  ├─ Resolve the parent spec by file presence (specs/<slug>/spec.md or root spec.md) and read it
  ├─ Read its `## Decomposition` scope stub for this feature, looked up by the feature directory name
  │   (no section → proceed without one; section but no row for this slug → one OPEN_QUESTION)
  ├─ Read its decisions logs nearest-first (specs/<slug>/decisions.md, then specs/decisions.md) — `## Active (bound)` entries only
  ├─ Read context/specs/*.md (category specs that bear on this feature)
  ├─ Read CLAUDE.md
  ├─ Read MEMORY.md + relevant project memory files
  ├─ Read existing brief.md (warm mode — when the file or sidecar already exists)
  └─ Extract project invariants the brief MUST honor (no non-Latin names, no existing-users assumptions, etc.)

Draft (LLM judgment; main thread)
  ├─ Mirror section template: Problem / Solution / Goals / Scope / User-facing changes / Open questions
  ├─ Draft Goals from the stub's outcomes owed; derive each inherited exclusion's bucket from its source (Non-goal or seam)
  ├─ Give each Goal a "Measured by:" clause — the check that proves it shipped whole
  ├─ Sort every remaining scope exclusion into one of the four buckets; deferrals name a destination
  ├─ Surface every "Open questions" entry the upstream artifacts left unresolved
  └─ Emit first draft to in-memory buffer (NOT yet written to disk)

Ground-truth audit  (`_author-common/ground-truth-protocol.md`; skipped in --draft mode)
  ├─ Tokenize draft for V1-V5 claims
  │   (V1 anchors mostly absent at brief layer; V4 cross-doc + V5 external-API dominate)
  ├─ Verify each claim against the parent spec / its stub + Coverage table / project memory / category-spec / external API client
  ├─ Apply outcomes (verified / softened / corrected / dropped / restructured)
  └─ Write sidecar audit log

Self-prosecution and emission  (`_author-common/self-prosecution-protocol.md`; skipped in --draft mode)
  ├─ Spawn product + ai-development persona agents in parallel
  │   (each runs the premise-interrogation sub-pass + the standard-prosecution sub-pass)
  ├─ Run the no-annexation check against the parent spec's Coverage table
  ├─ Consolidate findings; apply auto-fixable
  ├─ Run post-fix premise verification on orchestrator-rewritten prose
  ├─ Classify residuals (STABLE_DISAGREEMENT, OPEN_QUESTION, FIX_INTRODUCED_PREMISE_INVERSION)
  └─ Decide emission:
      ├─ APPROVED: write brief.md with NO `Status:` frontmatter (the binary mid-cycle convention) + persist sidecar + render verdict
      └─ NEEDS_USER_INPUT: write partial draft with `Status: needs-user-input` and inline `## Pending blockers` + persist sidecar + render verdict
```

In `--draft` mode the Ground-truth audit and Self-prosecution stages are skipped; the draft is emitted directly with `verdict: "DRAFT_EMITTED"` per the rule under Edge cases.

---

## State load

Read the sidecar if it exists. Schema:

```json
{
  "feature": "<feature>",
  "artifact_path": "features/<feature>/brief.md",
  "parent_spec": "specs/<slug>/spec.md | spec.md",
  "decomposition_stub": "ingested | absent",
  "brief_worktree": {
    "action": "created | reused | in-place",
    "path": "<.worktrees/<feature>-brief or null when in-place>",
    "branch": "<<feature>-brief or null when in-place>",
    "in_place_reason": "--no-worktree | already-in-linked-worktree | no-bootstrap-script | null",
    "upstream_from": "worktree | invocation-checkout (cold-create fallback)"
  },
  "authoring_mode": "ship | draft",
  "ground_truth_at": "<ISO 8601 UTC>",
  "self_prosecution_at": "<ISO 8601 UTC>",
  "invocation_number": <int>,
  "last_brief_sha256": "<hex>",
  "claims_total": <int>,
  "claims_verified": <int>,
  "claims_verified_softened": <int>,
  "claims_corrected": <int>,
  "claims_dropped": <int>,
  "claims_restructured": <int>,
  "claims_skipped_carveout": <int>,
  "no_annexation": "not_applicable | clean | <N> claims",
  "goal_cohesion": "not_at_risk | cohesive | bundle",
  "introduced_identifiers": [],
  "ground_truth_log": [...],
  "self_prosecution_findings": [...],
  "exclusion_challenges": [...],
  "authoring_residual": [...],
  "prior_blockers": [
    {
      "blocker_class": "<class>",
      "path_or_section": "<verbatim>",
      "summary": "<verbatim>",
      "raised_in_round": <int>,
      "current_reclassification_justification": "<optional, when re-prosecuted across rounds>"
    }
  ],
  "recently_resolved_blockers": [
    {
      "blocker_class_when_resolved": "<class>",
      "path_or_section": "<verbatim>",
      "summary": "<verbatim>",
      "resolved_in_round": <int>,
      "user_decision": "<verbatim>",
      "carry_forward_until_round": <int>
    }
  ],
  "verdict": "APPROVED | NEEDS_USER_INPUT | DRAFT_EMITTED"
}
```

`DRAFT_EMITTED` is the verdict written when the user invokes with `--draft` — the Ground-truth audit and Self-prosecution stages are skipped, so no APPROVED/NEEDS_USER_INPUT determination is possible. The reviewer skills and `/explain-blockers` both treat `DRAFT_EMITTED` as "intentionally unhardened" — `/explain-blockers` skips it (no blockers to triage), and `/engineering-plan-review-v2` warns when reviewing an engineering plan whose upstream brief is `DRAFT_EMITTED`.

`no_annexation` and `goal_cohesion` carry the two Self-prosecution-stage gate results, and both are written on every `ship` run — including the clean case, since "the check ran and found nothing" and "the check never ran" are the two states a reviewer consulting this sidecar has to tell apart.

The `prior_blockers` / `recently_resolved_blockers` shape mirrors the reviewer state schema in `~/.claude/cache/review-state/`. This intentional uniformity lets `/explain-blockers` parse author-state with the same parser. Only HIGH+ self-prosecution residuals land in `prior_blockers` — LOW residuals under the polish floor stay in `authoring_residual` and are never surfaced as blockers.

If `last_brief_sha256` matches the SHA of `features/<feature>/brief.md` on disk and the file's mtime is recent, the brief has not changed since the last invocation; the sidecar's `ground_truth_log` is still authoritative. If the SHA differs (the user edited the brief manually) or the file is older than the sidecar implies, treat as a fresh authoring round (cold w.r.t. ground-truth, warm w.r.t. carry-forward).

Also read the engineering-plan reviewer's state at `~/.claude/cache/review-state/<feature>__engineering-plan.json` if it exists — and for a **tracked** feature (per `~/.claude/skills/_plan-common/layout.md`), every `<feature>__<track>__engineering-plan.json` instead, since one brief has one engineering plan per track and any of them can raise a brief-layer blocker. If neither exists, fall back to the legacy bare `<feature>.json` (see that doc's Migration note). The engineering-plan reviewer's `recently_resolved_blockers` list may include brief-layer items the user already arbitrated (BRIEF_AMENDMENT_NEEDED). These are warm-mode carry-forward at the brief layer: re-introducing a Goal/Non-goal the user already removed is the worst thrash form.

---

## Brief-worktree provisioning (when your project provides a worktree bootstrap script; runs after State load, before Source ingest)

When your project provides a worktree bootstrap script, the brief is authored inside a **lightweight, per-brief worktree** off `origin/main`, not in the primary checkout — the same convention `/plan-author` applies at the chunk layer. Brief authoring only ever writes markdown, so the worktree is a plain `git worktree add` — it does **NOT** use the bootstrap script and provisions **no** dev-services stack, dependencies, or seed data (that heavy path is `/execute-plan`'s, for code that runs tests). This keeps the primary checkout clean and lets parallel authoring sessions run without racing on the shared tree.

The provisioning happens after State load (which only touches the global `~/.claude/cache` sidecars) and before Source ingest, because Source ingest reads repo files (the parent spec and its decisions log, `context/specs/*.md`, `CLAUDE.md`, any existing `brief.md` / `decisions.md`) and must resolve them inside the worktree when they are on `main`, or from the invocation checkout when they are not yet merged (see the cold-create fallback).

### When it runs

Provisioning runs unless ANY of the following holds, in which case this stage is a no-op and authoring proceeds **in place** (record the reason in the sidecar and verdict):

- **`--no-worktree` was passed.**
- **Already inside a linked worktree** — `git rev-parse --git-dir` differs from `git rev-parse --git-common-dir`. The session is already isolated in some `.worktrees/<name>`; write the brief there rather than nesting a worktree in a worktree.
- **No worktree bootstrap script** — no executable bootstrap script exists at the repo root (`git rev-parse --show-toplevel`). This skill is global; the whole stage is a no-op elsewhere.

### Worktree identity

Deterministic, per-feature. Let `MAIN_ROOT` = `git rev-parse --show-toplevel`.

- `WT_NAME` = `BRANCH` = `<feature>-brief`.
- `WT_PATH` = `$MAIN_ROOT/.worktrees/$WT_NAME`.

The `-brief` suffix names the artifact layer: it keeps this worktree distinct from `/plan-author`'s `<chunk-slug>-plan` worktrees and `/execute-plan`'s `<chunk-slug>` implementation worktrees, and keeps `/cleanup-worktree`'s `-plan`-specific next-step hint (the ready-to-paste `/execute-plan` command) from firing on a brief branch.

### Steps

1. **Reuse guard.** If `$WT_PATH` already exists:
   - its checked-out branch is `$BRANCH` (`<feature>-brief`) → **adopt it**: re-anchor to `$WT_PATH`, skip creation. This is a re-author of the same feature's brief.
   - any other branch → REFUSE `BRIEF_WORKTREE_COLLISION` (something else owns that path; the user resolves it — e.g. `/cleanup-worktree <WT_NAME>`).
2. **Sync + pin the base (fresh create only).** `git -C "$MAIN_ROOT" fetch origin main`. Pin the branch to `origin/main` explicitly rather than forking off the shared checkout's current HEAD (the shared-tree branch-creation race): `git -C "$MAIN_ROOT" branch "$BRANCH" origin/main`. If `$BRANCH` already exists with no worktree (a leftover from an aborted run), reuse it; otherwise the branch is live elsewhere → REFUSE `BRIEF_BRANCH_EXISTS`.
3. **Create the worktree.** `git -C "$MAIN_ROOT" worktree add "$WT_PATH" "$BRANCH"`. Plain and fast — no bootstrap script, no DB/deps.
4. **Re-anchor.** Set the working directory to `$WT_PATH` for Source ingest and every stage below. All repo reads (the parent spec and its decisions log, `context/specs/*.md`, `CLAUDE.md`, existing `brief.md` / `decisions.md`, sibling `features/*/brief.md` shape references) and the final brief write resolve inside `$WT_PATH`. The sidecar (`~/.claude/cache/author-state/<feature>__brief.json`), review-state reads, and project-memory reads keep their absolute paths — they are outside the repo and unaffected.

### Upstream presence (cold-create fallback)

A per-brief worktree is a fresh branch off `origin/main`, so it carries an existing `brief.md` / `decisions.md` only when they are already merged to `main`. When they are not (e.g. a prior in-place authoring round left an uncommitted brief in the primary checkout), do NOT treat the warm-mode source as missing: read it from the **invocation checkout** by absolute path, still write the new draft into the worktree, and surface a SOFT note in the verdict — the brief should land on `main` via this branch's PR so downstream skills review against the real upstream. Record `brief_worktree.upstream_from: "invocation-checkout (cold-create fallback)"`.

---

## Source ingest

### Parent-spec resolution

Every brief descends from exactly one spec, resolved by **file presence**, in this order:

1. `--spec <slug>` → `specs/<slug>/spec.md`. Refuse when that file is absent; the user named a spec that is not there.
2. The `**Spec:**` header line of an existing `features/<feature>/brief.md`, when re-authoring.
3. `specs/<slug>/spec.md` when a `specs/` tree exists and holds exactly one spec folder.
4. Root `spec.md` when the `specs/` tree is absent **or holds no spec folders**. An empty or scaffold-only `specs/` directory is the same evidence as no directory at all — a tree that names no spec cannot name this brief's parent, and treating its mere existence as a signal refuses every brief in a project that created the folder ahead of its first spec.

**There is exactly one sanctioned ask, and this is it:** a `specs/` tree holding several spec folders, with no `--spec` and no `Spec:` header to read. Presence has no answer with several candidates, so list the slugs and ask which one this feature belongs to. Every other case resolves from the disk without a question, and the answer to this one is written into the draft's `**Spec:**` header so it is asked once per feature rather than once per invocation. A project with a single root `spec.md` and no `specs/` tree resolves at step 4 and is fully supported — every stage below reads whatever that spec carries and behaves identically.

The resolved path is what the draft's `**Spec:**` header names and what the sidecar's `parent_spec` records, so a re-author lands on the same spec without re-asking.

### Read order

Read in this order. Read once into context; do not re-read in later stages.

1. **The parent spec** resolved above — the product master spec for this feature's domain. Brief Goals must trace to spec sections; brief Non-goals must not contradict spec capabilities.
2. **The parent spec's `## Decomposition` scope stub for this feature** — the block naming this brief's *outcomes owed*, *exclusions inherited*, and *spec units claimed*, plus the Coverage table rows dispositioning those units. The stub is looked up by slug, and the slug is this feature's directory name under `features/` — the same string that names its row in the spec's Briefs table (`~/.claude/skills/_spec-common/spec-format.md` § The Decomposition section). The stub is the slice of the spec this brief is authored against, and the Draft stage consumes it directly rather than re-deriving the slice. Two absences, two behaviors: a spec carrying **no `## Decomposition` section at all** yields no stub and no Coverage table, and Goals derive from the spec body (the degradation under Edge cases). A spec that **has** a decomposition but carries no row for this slug is a gap upstream — file one `OPEN_QUESTION` and emit a partial draft, per the Edge case below.
3. **The parent spec's decisions logs** — two of them, read **nearest first**: `specs/<slug>/decisions.md` beside a per-system spec (root `decisions.md` beside a root spec), then the shared `specs/decisions.md` holding calls that range across specs. Only `## Active (bound)` entries bind, in either log; a `superseded` / `obsolete` entry binds nothing. Where the two disagree, the nearer one wins — a call made for this spec is more specific than a call made for the tree. A call about which briefs exist or where a boundary sits lives in the spec's log; a call inside one feature's scope lives in the feature's log. Boundary calls are constraints on this draft rather than ground to re-litigate. A missing log is not an error — read what is there and carry on.
   **Boundary-binding force is gated on the parent spec carrying `## Decomposition`.** A spec with no decomposition never cut a boundary, so the log beside it binds content the ordinary way and settles no brief boundary — there is none to settle. This gate is on the section, not the path: a root `spec.md` that *does* carry `## Decomposition` has a boundary-binding root `decisions.md`.
4. `context/specs/*.md` — category-specific specs. For book features, read `context/specs/clean-book-database-spec.md` if present.
5. `CLAUDE.md` — project conventions, banned patterns, business rules. Pay attention to: the 5-item threshold, score-rounding rule, watchlist auto-remove, block-mutual-unfollow, public-rankings invariant, multi-category architecture rules.
6. `MEMORY.md` + every memory file under `~/.claude/projects/<project>/memory/` whose `description` field hints at relevance to this feature.
7. Existing `features/<feature>/brief.md` (when re-authoring an existing brief) + `features/<feature>/decisions.md` (every dated entry). The logs split by subject: a call about which briefs exist or where a boundary sits lives in the spec's log; a call inside one feature's scope lives in the feature's log (step 3 read the spec side). When re-authoring, the current brief content is a carry-forward constraint. A mid-cycle `Status: needs-user-input` brief is resolved by the session agent applying blocker resolutions directly, not by re-running this skill.

After reading, build an "invariants ledger" — a short list of facts the brief MUST honor. Examples for this project:
- "No non-Latin-script person names" (`feedback_*` memory)
- "No existing users yet" (`MEMORY.md`)
- "App is a social-media ranking app for movies/TV/books — expanding to more categories" (CLAUDE.md)
- "Linking has to be right or not done at all; correctness over coverage" (existing brief patterns)

The ledger is the prosecution target for the Self-prosecution stage's product persona.

---

## Draft

Mirror this section template (matches the shape of existing briefs in the repo):

```markdown
# <Feature Name> — Product Brief

<!-- Status frontmatter is OPTIONAL and binary. Set to `needs-user-input` ONLY when the brief is mid-cycle (auto-managed by /brief-author NEEDS_USER_INPUT path). Otherwise omit entirely. Lifecycle states (Frozen / Archived) are derived from git state, not frontmatter. -->
<!-- Status: needs-user-input -->  <!-- only when mid-cycle -->

**Spec:** <the resolved parent spec — `specs/<slug>/spec.md`, or `spec.md` in a single-root-spec project>
**Created:** <YYYY-MM-DD>
**Last updated:** <YYYY-MM-DD>

## Problem

<One or more paragraphs. State the user-visible failure mode this feature exists to fix. Quantify cohorts where possible (the "~400-450 prolific authors" pattern). Tie to the parent spec's sections that already named the problem.>

## Solution

<One or more paragraphs. The shape of the fix at the user-visible level — not the implementation. Name the cohorts/populations the solution operates on. End with the load-bearing tradeoff (e.g., "Linking has to be right or not done at all").>

## Goals

- **<Goal name>.** <Observable outcome, with the domain it ranges over named explicitly.>
  **Measured by:** <the check that answers "did this ship whole?" — a query, a named test, a gate, a counted set.>
- ...

## Scope

### In scope

- <what this feature delivers; each item testable against a Goal>

### Intentionally deferred

- <item> — <destination: `#NNN` or a follow-on feature slug>

### Not in scope (this release)

- <outside this commitment, no committed future ship, still a candidate>

### Not planned

- <decided against> — <why>

## User-facing changes

<What the user sees post-feature. May be "ships a database snapshot, no live UX changes" for backfill features. Concrete and present-tense.>

## Open questions

None. | <list of unresolved questions in question form, NOT statements>
```

### Drafting rules

- **The stub's outcomes owed are the Goal source.** Where the parent spec's Decomposition carries a scope stub for this feature, each outcome owed becomes a Goal — restated in the brief's own user-facing voice, none dropped, none merged into another. The stub already decided *what this brief is for*; re-deriving that from the whole spec is the step this ingest exists to remove. A Goal with no outcome owed behind it is either surface the Coverage table assigns elsewhere (see the no-annexation check) or an amendment the spec owes — never a quiet addition. With no stub, Goals derive from the spec body as usual.
- **An inherited exclusion's bucket is derived from its source, not read off a label.** The stub's *exclusions inherited* carry no bucket field — spec-format defines none — so waiting for one stalls the draft forever. Derive it from where the exclusion came from:
  - **Sourced from the spec's Non-goals** → `Not planned`, carrying the spec's own reason. The spec decided against it; the brief restates that decision rather than re-opening it.
  - **Sourced from a named seam** → the seam already says who owns the unit, and the owner picks the bucket. A sibling brief in this spec's decomposition, or a named follow-on pass, makes it `Intentionally deferred` with that slug as the destination. A unit another spec owns, with nothing committing when it ships, makes it `Not in scope (this release)`.

  The derivation is mechanical in both directions, so two authors reading the same stub land the same exclusion in the same bucket. Where the source is genuinely ambiguous — an exclusion the stub inherits with no Non-goal and no seam behind it — that is an `OPEN_QUESTION` for the user, not a guess: the bucket is load-bearing downstream, because a narrowing in `Intentionally deferred` with a destination is an approved cut the Scope-fidelity Adversary will not flag.
- **Each Goal is verifiable, and says how.** "Disambiguation primitive shared across the codebase" is verifiable; "great UX" is not. The Goal's verifiability is the foundation for the engineering plan's `Verified by` column.
- **Each Goal carries a `Measured by:` clause.** The check that answers *"did this ship whole?"* — a query, a named test, a CI gate, a counted set. It names the **check**, not the chunk; the engineering plan's Brief-mapping table already has a `Verified by` column for the chunk that ships the proof. A Goal whose completeness cannot be checked is one whose narrowing cannot be caught, and that narrowing is this project's most-repeated failure. `/plan-lint` warns on a Goal with no clause.
  **A check against an authored artifact counts.** At the brief layer the clause may name a check a reader runs over authored content — "all six pair cells name both layers", "the catalog holds two compatible expressions against every legally reachable body" — as well as a query, a test, or an executable gate. What the clause owes is a domain and a countable answer over it, not an automated runner; a brief whose Goals produce authored surface has nothing to gate in CI and still has everything to count.
  The project is pre-launch with no users, so adoption-percentage thresholds ("30% of users…") are unfalsifiable and banned. The threshold that works here is a **domain plus a check**: "every profile page reachable from search", "0 rows fail this query", "p95 under the budget".
- **Each Goal states an outcome, not a mechanism.** A Goal names what the user (or the data, or the system) observably ends up with — never the technique that gets there. "Junk can't silently return at any surface a user reaches" is an outcome; "junk is kept out using an allowlist/ML approach" is a mechanism. Mechanism-phrased Goals ("using/via X", "an allowlist/ML approach", "a dedupe step", "an LLM pass") are satisfiable by performing the technique *somewhere*, which lets the engineering plan partition one technique onto one surface and another onto another while the user-visible outcome ships nowhere whole. If a Goal names a technique, rewrite it as the observable result; the technique belongs in the engineering plan. This is the *durable* fix, and it is load-bearing: the engineering-plan layer's Scope-fidelity Adversary is defeated by a mechanism-phrased Goal — a reader taking "allowlist/ML approach" literally acquits a plan that ran the allowlist on one surface and the ML on another. The downstream parity check only becomes reliable once the Goal is an outcome; do not rely on the reviewer to catch what an outcome-phrased Goal would have prevented here.
- **Name the domain when a Goal quantifies over one.** When a Goal carries a quantifier — "every", "across the catalog", "all", "any", "going forward", "at every surface" — state the concrete domain it ranges over: which surfaces (search, person pages, ingestion, live read-render), which media types, which call paths (live + offline, read + write), which cohorts. "Authorship is restored across the catalog (books *and* series)" beats "authorship is restored across the catalog." The named domain is what the engineering plan's outcome-scope-parity check measures chunk coverage against (per `_review-common/principles.md` § Outcome-scope parity); an unnamed domain cannot be checked, so a subset delivery ships silently.
- **Each scope exclusion is real, not aspirational.** "No paid tier" belongs in a bucket if the feature could plausibly include one. Don't pad any bucket with implausible entries.
- **Scope has four buckets, and the bucket is a claim.** A single Non-goals list collapses committed-later, not-this-release, and decided-against into one shape, and the downstream scope adversary then has to re-derive which is which — it guesses, and it guesses charitably. Sort each exclusion deliberately:
  - *Intentionally deferred* is a promise. **Every item names a destination** — a GitHub issue number or a follow-on feature slug. `/plan-lint` FAILs an undestined deferral, because it is indistinguishable from a silent narrowing. If you cannot name where the work goes, it is not deferred.
  - *Not in scope (this release)* is "no committed future ship, still a candidate."
  - *Not planned* is a decision, and it states its reason.
  The payoff is downstream: a narrowing that lands in *Intentionally deferred* with a destination **is** an approved cut, and the Scope-fidelity Adversary treats it as legitimate rather than flagging it. Sorting carefully here buys quieter reviews later.
- **Migrating an older brief.** A brief on the bare `## Non-goals` shape converts to `## Scope` only when you are already rewriting it. Sorting settled items into buckets is a product call per item, not a transformation — if the right bucket for an item isn't obvious from the brief or `decisions.md`, that's an `OPEN_QUESTION`, not a guess.
- **Open questions are questions.** "How do we handle X?" is an open question. "We need to figure out X" is a statement and should be either a Goal (if it's required to ship) or a Non-goal (if it's deferred).
- **Advisory size ceiling: 15KB.** A brief past that is almost always re-narrating itself — Solution restating Goals, Scope restating both — or carrying detail that belongs in `decisions.md` or the engineering plan. State each fact once, in the section that owns it: Problem the failure, Solution the shape, Goals the commitments and checks, Scope one line per item. `/plan-lint` warns (`brief-oversize`) past the ceiling; the fix is cutting repetition and narration, never commitments or `Measured by:` checks.
- **Mirror existing briefs in the same feature family.** Read `features/*/brief.md` and copy section ordering, tone, and density. Do not invent a new brief shape.
- **No persona-attribution headers.** The brief is one document with one voice (per `_review-common/principles.md` plan-style rules).
- **No review attributions.** No "Architecture review found…" — those belong in `decisions.md`.
- **No historical comparisons.** No "the original brief said X but actually Y" — describe the current state only.

---

## Ground-truth audit

Apply `_author-common/ground-truth-protocol.md`. At the brief layer, the dominant claim classes are:

- **V4 (Cross-document)** — every reference to the parent spec (its body, its `## Decomposition` stub, its Coverage table), a category-spec, project memory, either decisions log, or CLAUDE.md. A Goal citing an outcome owed the stub does not carry, or a scope bucket citing an exclusion the stub does not inherit, is a false claim about a real file.
- **V5 (External-API)** — claims about what an upstream API or an LLM API *can do at the API level* (not implementation detail). Verify against the project's wrapper code.
- **V3 (Constraint)** — claims about cohort counts ("~400-450 prolific authors"), database state ("~841 already-pre-hydrated film/TV Persons"). Verify against the most recent migration / seed data / database query the project supports.

V1 (path:line) and V2 (identifier) claims are RARE at the brief layer. If the draft has them, the brief has drifted into engineering-plan territory — file as a self-prosecution finding (drift class).

After verification, emit the sidecar audit log even if the draft is rejected at the Self-prosecution stage; the user benefits from seeing what was verified vs dropped.

---

## Self-prosecution and emission

Spawn two persona agents in parallel using the template in `_author-common/self-prosecution-protocol.md`:

- **product** — prosecutes Goals/Non-goals coherence, scope creep, contradicted spec, banned project assumptions ("existing users").
- **ai-development** — prosecutes plan-quality at the brief layer (verifiability of Goals, banned patterns, drift toward engineering-plan detail).

Active critical pairs: universal pairs from `_review-common/critical-pairs.md` only. PR/chunk/engineering-plan-specific pairs do not apply at the brief layer.

**Goal-cohesion check (Feature-surface gate).** Alongside the persona batch, run the trigger filter from `~/.claude/skills/_review-common/feature-surface-gate.md` § Goal-cohesion check (≥ 4 Goals, OR ≥ 3 distinct surfaces in Goals, OR ≥ 3 product areas in User-facing changes). At-risk → spawn the Goal-cohesion Adversary (`model: "sonnet"`, isolated, in the same parallel message as the personas) with the halved-feature mandate from the gate file. A reported partition files `BRIEF_SCOPE_BUNDLE` (HIGH) → partial-draft with the split proposal rendered per the gate file's § Split proposal; suppressed only by a bound size-acceptance row per § Acceptance. Record `goal_cohesion: not_at_risk | cohesive | bundle` in the sidecar either way.

**No-annexation check.** Where the parent spec carries a `## Decomposition` Coverage table, test every drafted Goal against it. A Goal claiming a spec unit the table assigns to a **sibling brief slug**, or excludes by a **named seam**, files `OPEN_QUESTION` (HIGH) naming three things: the unit, the slug or seam the table dispositions it to, and the Goal that reached for it. Do not widen the brief to the unit and do not drop the Goal — which of the two is right is the director's call, and it is the one finding no reviewer downstream can make: the annexing brief traces its Goal to a real spec unit, the annexed brief still traces its own, and both review clean while the unit ships twice or nowhere. A spec with no Coverage table skips the check. Record `no_annexation: not_applicable | clean | <N> claims` in the sidecar either way.

After consolidation, run post-fix premise verification on any orchestrator-rewritten prose. Classify residuals.

### Verdict template

```markdown
# Brief authoring verdict — features/<feature>/brief.md

**Mode:** cold | warm
**Authoring mode:** ship | draft
**Round:** <invocation_number>
**Last brief sha:** <hex>

## Ground-truth audit
**Claims total:** <N>
**Verified:** <V>  **Softened:** <S>  **Corrected:** <C>  **Dropped:** <D>  **Restructured:** <R>  **Skipped (carve-out):** <K>

## Self-prosecution
**Personas:** product, ai-development
**Premise interrogation:** <product=passed/failed>, <ai-development=passed/failed>
**Standard findings:** <N total>; <by tier+severity>
**Post-fix premise verification:** <P claims rewritten; Q falsified> → <FIX_INTRODUCED_PREMISE_INVERSION count>
**Carry-forward consultation:** <skipped because cold mode | M recently-resolved blockers cross-checked, R re-prosecutions auto-retracted>

## Verdict
**APPROVED** | **NEEDS_USER_INPUT** | **DRAFT_EMITTED**

### Blockers (if NEEDS_USER_INPUT)
- [STABLE_DISAGREEMENT] <span> — <one-line>
- [OPEN_QUESTION] <span> — <one-line>
- [FIX_INTRODUCED_PREMISE_INVERSION] <span> — <one-line>

### Authoring residuals (LOW, under polish floor)
- ...
```

### Verdict gates

- **APPROVED** when ALL of:
  - Authoring mode is `ship` (not `--draft`).
  - Ground-truth complete (no V1-V5 class left unverified outside carve-out).
  - All HIGH+CRITICAL self-prosecution findings resolved.
  - Tier-2 weight ≤ 4 (polish floor).
  - No `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `FIX_INTRODUCED_PREMISE_INVERSION`.
- **NEEDS_USER_INPUT** when authoring mode is `ship` AND any of the above APPROVED conditions fails.
- **DRAFT_EMITTED** when authoring mode is `--draft`. By construction the Ground-truth audit and Self-prosecution stages are skipped, so APPROVED/NEEDS_USER_INPUT cannot be determined; the user has explicitly opted out of the safety net.

Disk-write semantics:
- **APPROVED** → write `features/<feature>/brief.md` with NO `Status:` frontmatter (the binary-Status convention reserves `Status:` for the mid-cycle signal only); persist sidecar; print verdict. If the on-disk file still carries `Status: needs-user-input` and a `## Pending blockers` section, this emission removes that line along with the section. **Next step:** run `/brief-review-v2` to prosecute the draft.
- **NEEDS_USER_INPUT** → write `features/<feature>/brief.md` with frontmatter `Status: needs-user-input` AND an inline `## Pending blockers` section listing each unresolved finding verbatim from the verdict; persist sidecar with `verdict: "NEEDS_USER_INPUT"`; print verdict including the unresolved blockers. The session agent then applies your blocker resolutions directly to `brief.md` and removes the `Status:` line + `## Pending blockers` section once the blockers clear — the author is not re-invoked. Downstream skills (`/engineering-plan-author`, `/engineering-plan-review-v2`, `/brief-review-v2`) hard-refuse against `Status: needs-user-input` briefs — the upstream is mid-cycle by design.
- **DRAFT_EMITTED** → write `features/<feature>/brief.md` with NO `Status:` frontmatter; persist sidecar with `verdict: "DRAFT_EMITTED"` AND `authoring_mode: "draft"` (the load-bearing draft signal); print verdict noting the draft is unhardened by choice (`--draft` skipped Ground-truth audit and Self-prosecution). Reviewer skills consult the sidecar's `authoring_mode` field to detect draft mode and warn in their verdicts; `/execute-plan` consults it and refuses (implementing a draft plan ships hallucinations).

### Pending-blockers section (NEEDS_USER_INPUT mode)

On NEEDS_USER_INPUT, the on-disk brief gets two additions beyond the partial draft body:

1. **Frontmatter `Status: needs-user-input`** is added (or replaces a prior Status value if any). The APPROVED-emission convention is no `Status:` field; the NEEDS_USER_INPUT path adds the field as the only valid Status value.
2. **`## Pending blockers` section appended at the end of the file**, with verbatim bullets from the verdict's `### Blockers` block:

   ```markdown
   ## Pending blockers

   <!-- This section is auto-managed by /brief-author. Resolve each blocker below; the session agent then applies your resolutions directly to this file and removes this section along with the `Status: needs-user-input` line — the author skill is not re-run. Downstream skills (`/engineering-plan-author`, `/engineering-plan-review-v2`) refuse to run against this brief until the blockers clear. -->

   - [<BLOCKER_CLASS>] <span / section> — <one-line summary>; <actionable resolution path>.
   - ...
   ```

Once the session agent has applied every resolution, it removes the entire `## Pending blockers` section AND its HTML comment, AND the `Status: needs-user-input` line (a resolved brief carries no `Status:` field). While any blocker remains unresolved, the `## Pending blockers` section keeps only the still-open blockers (resolved ones drop out as they land — stale blockers don't accumulate) and the `Status: needs-user-input` line stays.

---

## Hard rules

- **Stage order is fixed.** State load, then Brief-worktree provisioning (a no-op only under its own listed conditions), then Source ingest, then Draft. Ground-truth audit before Self-prosecution and emission. No stage can be skipped except Ground-truth audit and Self-prosecution in `--draft` mode.
- **In `ship` mode, the draft is written to disk after Self-prosecution and emission closes regardless of verdict; the on-disk frontmatter `Status:` field gates downstream skills via the binary mid-cycle convention.** APPROVED writes with NO `Status:` field (downstream skills consume the brief normally). NEEDS_USER_INPUT writes the partially-improved draft with `Status: needs-user-input` and an inline `## Pending blockers` section — downstream skills (`/brief-review-v2`, `/engineering-plan-author`, `/engineering-plan-review-v2`) hard-refuse against `Status: needs-user-input` briefs because the upstream is mid-cycle by design; the session agent applies the user's blocker resolutions directly to the brief and clears the `Status:` line once they land — the author is not re-invoked. In `--draft` mode the user has explicitly opted out of the safety net by passing the flag; the draft IS written to disk with NO `Status:` field, the sidecar records `authoring_mode: "draft"` AND `verdict: "DRAFT_EMITTED"`, and reviewers consult the sidecar to detect draft mode and warn (rather than refuse). Authoring without `--draft` runs Ground-truth audit and Self-prosecution to produce a hardened draft; the author is not re-run to harden an existing `--draft` artifact.
- **Sidecar is always written.** Even on NEEDS_USER_INPUT verdicts, the sidecar persists so downstream skills and any later clean-slate re-author have full context.
- **Banned content categories** (per `_review-common/principles.md` plan style rules + `_author-common/principles.md` banned authoring rationalizations):
  - Addendum sections, review attribution, historical comparison, persona-attribution headers, conflict-resolution metadata.
  - "Should exist" / "probably exists" / "the spec implies" without a verbatim quote.
  - Goal/scope-exclusion pairs that contradict each other or contradict the parent spec.
  - Cohort counts without a verifiable source.
  - Goals with no `Measured by:` clause, or with a quantifier whose domain is unnamed.
  - Goals claiming a spec unit the parent spec's Coverage table assigns to a sibling brief or excludes by a named seam.
  - `Intentionally deferred` items with no destination.
- **The parent spec's bound decisions are constraints.** An Active `Status: bound` entry in the spec's decisions log settles which briefs exist and where the boundary between two of them sits. A draft that moves such a boundary is surfaced as an `OPEN_QUESTION` for the user, never re-cut in the brief — re-cutting is `/spec-author`'s Seam alignment, and it supersedes the bound entry in the log the usual two-step way.
- **Carry-forward respect.** Warm mode: a brief edit that re-introduces a Goal/Non-goal/user-cohort the user removed in a prior invocation is `FIX_INTRODUCED_PREMISE_INVERSION` against the brief itself. Surface to the user; do not emit.
- **Self-prosecution is mandatory for `ship` mode.** `--draft` skips it; `ship` does not.
- **Source ingest before draft.** A draft written without reading the upstream spec / memory / existing brief is not a brief — it's fan fiction. The Source-ingest stage is hard-blocking.

---

## Edge cases

**Sidecar absent, brief.md absent (cold start, fresh feature):** Skill is in cold mode. State load returns empty. Source ingest reads spec/memory/CLAUDE only. Draft writes from scratch. Ground-truth audit and Self-prosecution run normally.

**Sidecar absent, brief.md present (manual edit since last invocation, OR first invocation):** Read brief.md as the warm-mode source-of-truth. Treat its current content as the "before" state for the rewrite. No carry-forward (no sidecar history); but the current brief is itself a constraint.

**Sidecar present, brief.md absent (someone deleted the brief):** Treat as cold start at the disk level; consult sidecar's history for what the user had previously arbitrated, but write a fresh draft. Surface in the verdict that the prior brief was deleted.

**Sidecar present, brief.md present, SHA matches:** No-op invocation when the request adds no new constraint or instruction; print "no changes; brief is in the last APPROVED state" and exit. (A plain-language ask to rewrite or change the brief IS a new instruction and proceeds in warm mode.)

**Sidecar present, brief.md present, SHA differs (manual edit):** The user's manual edit takes precedence. Reset the sidecar's `ground_truth_log` to empty; re-run from Source ingest. Carry-forward of `recently_resolved_blockers` still applies.

**`--draft` mode:** Ground-truth audit and Self-prosecution are skipped. Sidecar is written with `authoring_mode: "draft"` and `verdict: "DRAFT_EMITTED"`. The brief IS written to disk with NO `Status:` frontmatter so the user can iterate on the file directly. The sidecar's `authoring_mode: "draft"` field is the load-bearing signal that downstream skills consult — `/brief-review-v2` proceeds with full prosecution but surfaces a draft warning in its verdict; `/engineering-plan-author` and `/engineering-plan-review-v2` warn-not-block when the upstream brief's sidecar reports draft mode. The verdict prose surfaces the unhardened-by-choice state (`--draft` skipped Ground-truth audit and Self-prosecution).

**Engineering-plan-review state has BRIEF_AMENDMENT_NEEDED unresolved:** Warm-mode carry-forward surfaces this; the brief author MUST address the amendment in the new draft, not just touch surrounding prose. If the amendment isn't addressable from this skill's vantage (requires user decision), surface as `OPEN_QUESTION`.

**No parent spec resolves:** Refuse to run. The brief is the bridge between its spec and `engineering-plan.md`; with no spec, the brief has no anchor. Print: "no spec found at `specs/<slug>/spec.md` or `spec.md`; the brief layer requires a spec source-of-truth. Create the spec, pass `--spec <slug>`, or invoke from the project root." Refuse only when *nothing* resolves — a project on a `specs/` tree has no root `spec.md`, and refusing on that absence alone would block every brief in it.

**Several spec folders, no `--spec`, no `Spec:` header:** Do not guess and do not fall back to a root `spec.md`. List the spec slugs under `specs/` and ask which one this feature belongs to, then proceed from the answer. Record the answer in the draft's `**Spec:**` header so the question is asked once per feature, not once per invocation.

**Parent spec carries no `## Decomposition` section:** Proceed with no stub. Goals derive from the spec body, exclusions are sorted into the four buckets by the ordinary drafting rules, and the no-annexation check is `not_applicable` because there is no Coverage table to test against. This is the whole of the degradation — in that layout the spec body is the Goal source, and every other stage runs unchanged.

**Parent spec carries a `## Decomposition`, but its Coverage table has no row for this slug:** File exactly ONE `OPEN_QUESTION` naming the missing row, and emit a partial draft. One question, never one per Goal — the whole slice is missing, so N per-Goal blockers say the same thing N times and bury the single upstream fix. Do not fall back to tracing against the whole spec and do not proceed as though the spec had no decomposition: a spec that cut briefs and did not cut this one is telling you something, and either the brief names the wrong parent or the decomposition never cut it. `/spec-author` answers both. Record `decomposition_stub: "absent"` and `no_annexation: not_applicable`.

**Parent spec's Decomposition names this slug but its stub is empty:** Treat as a spec-layer gap, not a licence to invent. The stub exists to say what the brief owes; an empty one answers nothing. File `OPEN_QUESTION` naming the slug and emit a partial draft — `/spec-author` fills the stub, and re-authoring picks it up.

**Parent spec's state carries an open `IMPLEMENTABILITY_GAP` for this slug:** Refuse to run, the same way this skill refuses against a `Status: needs-user-input` upstream. The spec layer's imagined-brief-author dry run already found this brief unauthorable from its stub, so drafting anyway produces exactly the brief that finding predicted. Print the gap's question and name `/spec-author` as the resolution path. Read the gap from the parent spec's author-state and review-state sidecars (`~/.claude/cache/author-state/` and `~/.claude/cache/review-state/`). **Check both spec keyings**, because `vision.md`'s presence decides which one exists: `<project>__<spec-slug>__spec.json` where a `vision.md` slugs the specs, and `<project>__spec.json` where there is none. Reading only the slugged form makes the refusal silently dead in every project without a vision map — including the single-root-`spec.md` projects step 4 of the resolution ladder serves. Absence of either file is normal and is not a refusal, and a gap keyed to any *other* slug is not this brief's business and never blocks it.

**Project memory absent (no `~/.claude/projects/<project>/memory/MEMORY.md`):** Run with degraded ground-truth coverage. Print warning. The product persona's prosecution will be weaker (fewer invariants to enforce), but the Ground-truth audit still runs against spec/CLAUDE.

---

## Relationship to sister skills

- **`/spec-author`** writes the parent spec whose `## Decomposition` cuts this brief out of it: the scope stub is this skill's Goal source, the Coverage table is what the no-annexation check tests against, and the spec's decisions log holds the bound seam calls this skill treats as constraints. A boundary this brief cannot honor goes back there, not into the brief.
- **`/brief-review-v2`** prosecutes the brief written here and consults this skill's sidecar to skip re-prosecuting author-arbitrated claims. It is the immediate next step after this author's first clean draft.
- **`/engineering-plan-author`** consumes the brief written here. The engineering-plan-author's Source-ingest stage reads `features/<feature>/brief.md` and the brief-author's sidecar (introduced_identifiers, authoring_residual). The engineering-plan-author's product-persona prosecution sub-pass cross-checks the engineering plan's chunks against the brief Goals.
- **`/plan-author`** indirectly consumes the brief (via the engineering plan). Brief edits cascade through the engineering-plan-review's BRIEF_AMENDMENT_NEEDED class.
- **`/engineering-plan-review-v2`** prosecutes the brief at the engineering-plan layer (premise interrogation §brief-environment sub-pass). Findings raised there belong upstream — the session agent applies them to `brief.md` directly; a later clean-slate re-author still respects them via the state file's carry-forward.

The brief is the highest-leverage artifact; this skill exists to make it the cleanest.
