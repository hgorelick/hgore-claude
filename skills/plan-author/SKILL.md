---
name: plan-author
description: Writes or rewrites one per-chunk implementation plan under `features/<feature>/implementation/` (or `.scratch/`), applying structural lint, brief-conformance, ground-truth verification, and self-prosecution at write time rather than review time. Run once per cycle, then `/plan-review-v2`. Sister to `/brief-author` and `/engineering-plan-author`.
user-invocable: true
---

# Chunk plan author

Produces or rewrites a per-chunk implementation plan. This is the layer where `/plan-review-v2` thrash concentrates: 28 findings in a single round, 5 user decisions and 13 orchestrator batches, 563-line plan files. Front-loading verification and self-prosecution at write time is supposed to land the plan at `/plan-review-v2` with single-digit findings, not five rounds of arbitration.

## Inputs

- `$ARGUMENTS`:
  - `<feature>/<chunk-slug>` — the chunk plan to author. Resolves to `<plan-root>/implementation/<NN>-<chunk-slug>.md` (the `<NN>-` creation-index prefix is auto-assigned — see [Creation index](#creation-index)); a bare `<chunk-slug>` matches an existing file by globbing `<chunk-slug>.md` or `[0-9]*-<chunk-slug>.md`. Required (unless free-standing path is given).
  - `<feature>/<track>/<chunk-slug>` — a chunk of a **tracked** feature (one whose engineering plans live under `features/<feature>/plans/<track>/`). See below.
  - OR `<absolute-or-relative-path>.md` — for `.scratch/` plans or other locations.
  - `--draft` — quick-exploration mode; skip Plan-lint, Ground-truth audit, and Self-prosecution. The Concern gate STILL runs in `--draft` mode (self-disclosed multi-concern bundling is a fatal scope error).
  - `--no-worktree` — (when your project provides a worktree bootstrap script) skip **Plan-worktree provisioning** and author in the current checkout. Use when you deliberately want the plan written in place — e.g. you are already set up in the tree you want it to land in, or you are consciously not using a per-plan branch.

**The author runs once per cycle.** It produces the first draft; the next step in the cycle is to run `/plan-review-v2`, and the session agent then applies its findings — plus your blocker resolutions — directly to the chunk plan. The author is not re-invoked to apply changes. There is no `--rewrite` flag. When the target chunk plan already exists on disk or its author sidecar is present, invoke `/plan-author <feature>/<chunk-slug>` again only for an explicit clean-slate re-author (ask in plain language); that fresh run treats the existing file as a carry-forward constraint (see Source ingest), reuses the creation index, and does not re-introduce a defect class the user already closed.

## Plan-root resolution

Read `~/.claude/skills/_plan-common/layout.md` before resolving the argument. A feature is **flat** (engineering plan and `implementation/` directly under `features/<feature>/`) or **tracked** (one of each per track under `features/<feature>/plans/<track>/`). Throughout this skill, **`<plan-root>`** is the directory holding the engineering plan that indexes this chunk — `features/<feature>/` when flat, `features/<feature>/plans/<track>/` when tracked. `brief.md` and `decisions.md` always live at the feature root and are shared by every track.

A two-token `<feature>/<x>` argument is a chunk reference unless `features/<feature>/plans/<x>/engineering-plan.md` exists. A bare `<chunk-slug>` globs both layouts; ambiguity across tracks is reported with the track names, never silently resolved.

**`<ep-slug>`** names the state files of the engineering plan that indexes this chunk: `<feature>__engineering-plan` when flat, `<feature>__<track>__engineering-plan` when tracked. It is the plan root's slug, not the chunk's. When reading engineering-plan **review** state, fall back to the legacy bare `<feature>.json` if the canonical name is absent (see `_plan-common/layout.md` § Migration note).

## Sidecar location

`~/.claude/cache/author-state/<slug>.json` for chunks under `features/`. Slug derivation follows `_plan-common/layout.md` § State-slug derivation — the artifact path relative to `features/`, minus the `plans/` and `implementation/` segments, `/` → `__`: `<feature>__<chunk-slug>` when flat (e.g., `user-profile-sync/stale-record-cleanup` → `user-profile-sync__stale-record-cleanup.json`), `<feature>__<track>__<chunk-slug>` when tracked (e.g., `team-chat/chat-core/chat-vocabulary` → `team-chat__chat-core__chat-vocabulary.json`).

For free-standing `.scratch/<name>.md` plans, slug is `scratch__<name>` where `<name>` is the path basename without the `.md` extension (e.g., `.scratch/orphan-bug.md` → `scratch__orphan-bug.json`). For git-tracked `fixes/<name>.md` one-off bug-fix plans, slug is `fixes__<name>` (e.g., `fixes/issue151-silent-refresh.md` → `fixes__issue151-silent-refresh.json`); `fixes/` plans are treated as brief-less exactly like `.scratch/` (no parent feature/brief). For other free-standing paths, slug is `scratch__<sanitized-name>` where `<sanitized-name>` replaces path separators with `__` and strips the `.md` extension.

Same derivation rule as `/plan-review-v2`'s state file, by design — both skills read/write the same slug for the same artifact.

The reviewer skill `/plan-review-v2` consults this sidecar to skip re-prosecuting verified claims and to read `introduced_identifiers`.

---

## Creation index

Implementation plans are written to disk with a **creation-index filename prefix** so a directory listing shows the order they were authored in at a glance:

```
<plan-root>/implementation/
  01-schema-migration.md
  02-external-id-backfill.md
  03-cascade-cleanup-ordering.md
```

- **The prefix is a glance-ordering affordance, not identity.** The slug stays prefix-free *everywhere else*: the H1 (`# Chunk: \`cascade-cleanup-ordering\``), the `**Slug:**` line, the sidecar key (`<feature>__<chunk-slug>.json`), the engineering-plan chunk-index row, every `decisions.md` citation, and the PR branch. Only the on-disk filename carries `<NN>-`. `/plan-lint` strips the prefix before deriving the slug, so the position-encoded-slug rule still rejects a number that leaks into the *identity*.
- **Format:** two-digit zero-padded, monotonically increasing per feature in authoring order — `01`, `02`, … `99`. Zero-padding keeps the lexical `ls` sort aligned with numeric order. (A feature that exceeds 99 chunks pads to three digits from the point of overflow.)
- **Assignment (new plan):** glob `<plan-root>/implementation/*.md`; the next index is `max(highest existing prefix, plan-file count) + 1`, zero-padded. The count term keeps the number sensible even when some plans in the folder are still bare (un-backfilled). Indices are **per plan root**, not per feature: two tracks of the same feature each start at `01`, because the prefix orders a directory listing and each track has its own. Record it in the sidecar's `creation_index`.
- **Reuse (re-authoring an existing plan):** the index is assigned once, at first creation, and is **stable for the life of the chunk** — never renumbered. When a plan file for this slug already exists, write back to its *current* filename (read `creation_index` from the sidecar, or take the prefix already on the file). A re-authoring run that lands NEEDS_USER_INPUT writes the partial draft back to that same filename.
- **Legacy / unprefixed files:** a plan authored before this convention keeps its bare `<chunk-slug>.md` name — re-authoring writes back to the existing filename and never renames it. Migrating old plans to the `<NN>-` convention is a separate, wholesale one-off (a backfill ordered by git history), not something this skill does lazily.
- **Scratch plans are not indexed.** `.scratch/<name>.md` plans are free-standing exploration with no feature ordering; they keep their bare `<name>.md` filename, and the sidecar omits `creation_index`.

---

## Workflow

```
State load (deterministic; ~5 seconds)
  ├─ mkdir -p ~/.claude/cache/author-state (Write does NOT auto-create parents;
  │   the reviewer-side machinery only creates ~/.claude/cache/review-state)
  ├─ Read author sidecar at ~/.claude/cache/author-state/<slug>.json
  ├─ Read review state at ~/.claude/cache/review-state/<slug>.json (warm carry-forward)
  ├─ Read engineering-plan-author sidecar at ~/.claude/cache/author-state/<ep-slug>.json
  │   (must exist — engineering plan must be CLOSED before chunk authoring; see Hard rules)
  ├─ Read engineering-plan reviewer state at ~/.claude/cache/review-state/<ep-slug>.json
  │   (consulted by the Concern gate's carry-forward consultation if a refusal pattern matches)
  └─ Determine cold vs warm mode

Plan-worktree provisioning (when your project provides a worktree bootstrap script; deterministic; plain `git worktree add` off origin/main — no project bootstrap script)
  ├─ No-op (author in place) when: --no-worktree, .scratch/ plan, already inside a linked worktree, or no worktree bootstrap script
  ├─ SLUG = the chunk's prefix-free slug; reuse .worktrees/<SLUG>-plan if it exists on branch <SLUG>-plan; else create off origin/main
  │   (git fetch origin main; git branch <SLUG>-plan origin/main; git worktree add .worktrees/<SLUG>-plan <SLUG>-plan)
  ├─ Re-anchor cwd to the worktree — every read below (authority stack, read-set, sibling plans)
  │   AND the final plan write happen there; the sidecar + temp drafts stay at their ~/.claude/cache + /tmp paths
  └─ Cold-create fallback: if the fresh worktree lacks the authority stack (brief/EP unmerged), read it from the
      invocation checkout and SOFT-note that brief/EP/decisions must land on main (or ride along in this plan's PR)

Source ingest (deterministic; ~60 seconds — runs inside the plan worktree when provisioned)
  ├─ Read brief.md (HARD-blocking)
  ├─ Read engineering-plan.md (HARD-blocking, AND must be at CLOSED status — author skill refuses
  │   to run if engineering-plan-author sidecar shows last verdict was APPROVED or NEEDS_USER_INPUT)
  ├─ Locate THIS chunk's row in the chunk index; extract description and row index
  ├─ Read decisions.md (every entry; chunk plans cite decisions, never inline rationale)
  ├─ Read existing chunk plan (warm mode)
  ├─ Read every file the chunk's "Read first" list cites (the chunk's read-set)
  ├─ Read CLAUDE.md, MEMORY.md, project memory
  ├─ Read the project's schema/data-model definitions and API operation definitions, sibling chunk plans for shape consistency
  └─ Build invariants ledger, identifier ledger, decisions ledger

Concern gate (deterministic — HARD-blocking unless carry-forward applies)
  ├─ Extract chunk description from the engineering-plan chunk index row located in Source ingest
  ├─ Apply ONE structural check against the description:
  │     - Self-disclosure: /\b\d+-concern\b|\bN-concern\b|\bbundle\b|\bbundling\b/i
  ├─ No match → concern_gate_status = "passed"; proceed to Draft. Semantic concern judgment
  │   happens in Self-prosecution (the ai-development persona's halved-work test); the
  │   deterministic gate intentionally does NOT pattern-match conjunctions, comma lists, or
  │   multi-clause descriptions, which fire false-positives on legitimate prose
  │   (e.g., "extract helper used in 12 sites and migrate callsites" is one concern but
  │   contains " and "; "add fieldA, fieldB, fieldC to User model" is one schema change).
  ├─ Match → consult carry-forward (see "Concern-gate carry-forward consultation" below)
  │   BEFORE refusing. If carry-forward applies, set concern_gate_status = "carried_forward",
  │   log the source, and proceed.
  └─ Match AND no carry-forward applies → REFUSE with class CONCERN_GATE_FAILED + the
      three actionable resolution paths (chunk-index rewrite preferred, decisions-closure row,
      reviewer re-run). The verdict surfaces them; the user picks one.

Draft (LLM judgment; main thread)
  ├─ Mirror Factoring Contract template (sections: Goal, Brief link, Context pack, Conventions,
  │   Factoring Contract — Owns / Contracts changed / Tests to add / Invariant classes touched
  │   / Acceptance criteria, Kill criteria, Review checklist, Out of scope)
  ├─ Size §Owns against the review-complexity budget BEFORE writing the rest
  ├─ §Kill criteria states ≥1 falsifiable stop condition
  ├─ §Owns enumerates files the chunk owns; every owned file has a one-line description
  ├─ §Contracts changed lists new types/functions/schema-fields/operations the chunk introduces
  ├─ §Tests to add describes test cases by behavior + assertion shape (NEVER pre-commit to test paths
  │   per `P-CHUNK-TEST-PATHS`)
  ├─ §Acceptance criteria is verifiable (npm test passes, npm run typecheck passes, specific commands)
  ├─ §Review checklist is short — calls out the load-bearing things a reviewer must verify
  ├─ §Out of scope cites decisions.md entries that defer adjacent work
  └─ Emit first draft to in-memory buffer (NOT yet written to disk)

Brief-conformance gate (mandatory when parent feature exists; HARD-blocking; runs BEFORE Plan-lint;
  │   SKIPPED for .scratch/ plans)
  ├─ Materialize in-memory draft to ~/.claude/cache/author-state/<slug>-DRAFT.md
  ├─ Spawn Brief-conformance Prosecutor (see _review-common/brief-conformance-prosecutor.md)
  ├─ HIGH HARD finding → hard refusal; partial-draft written with `Status: needs-user-input`
  ├─ MEDIUM HARD findings → partial-draft written; user adjudicates
  └─ `brief_conformance_check: passed` → proceed to Plan-lint

Plan-lint gate (deterministic, HARD-blocking)
  ├─ Write in-memory draft to /tmp/<slug>-draft-<timestamp>.md
  ├─ Bash: `python3 ~/.claude/skills/plan-lint/lint.py /tmp/<slug>-draft-<timestamp>.md`
  ├─ Capture stdout + exit code into sidecar
  ├─ Failures HARD-blocking — fix locally and re-lint up to 2x; structural failures surface
  │   as STRUCTURAL_LINT_FAILED
  └─ Delete temp file

Ground-truth audit (`_author-common/ground-truth-protocol.md`)
  ├─ Tokenize draft for V1-V5 claims (V1 anchors are heavy at chunk-plan layer)
  ├─ V1 — every path:line, every §heading anchor, every line range
  ├─ V2 — every helper, type, constant, schema field, GraphQL operation, test pattern reference;
  │   classify each as carve-out (introduced by THIS chunk) or anchor (must verify)
  ├─ V3 — counts, ordering, presence of constraints
  ├─ V4 — brief Goal quotes, decisions.md citations, engineering-plan §heading citations,
  │   CLAUDE.md / project-memory rule citations
  ├─ V5 — external API shape claims (rare at chunk-plan layer; usually project-wrapper level)
  └─ Apply outcomes; write sidecar audit log

Self-prosecution (`_author-common/self-prosecution-protocol.md`)
  ├─ Spawn 5 persona agents in parallel:
  │     - backend OR frontend (depending on chunk's Owns set: backend/ vs mobile/ heavy)
  │     - architecture
  │     - testing
  │     - security
  │     - ai-development
  ├─ Each runs the premise-interrogation sub-pass (against the chunk's premises) +
  │   the standard-prosecution sub-pass
  ├─ Consolidate findings; apply auto-fixable
  ├─ Run post-fix premise verification on orchestrator-rewritten prose
  └─ Classify residuals

Prose-Density gate (deterministic — runs unconditionally after Self-prosecution; skipped only in --draft)
  ├─ Compute three sub-metrics over the post-self-prosecution draft AS IT WILL BE WRITTEN TO DISK:
  │     - bytes_per_line_avg across §Conventions + §Tests to add + §Acceptance criteria
  │     - bullet_word_count_max anywhere in the document
  │     - parenthetical_nesting_depth_max anywhere in the document
  ├─ Any threshold breach → file PROSE_DENSITY_EXCESS (single class, sub-metric named in payload)
  ├─ Consult carry-forward (decisions.md row arbitrating density for this chunk)
  └─ Refuse with PROSE_DENSITY_EXCESS OR proceed to verdict emission

Verdict emission (two-state; the plan write lands inside the plan worktree when provisioned)
  ├─ Resolve the on-disk filename (see Creation index): if a plan file for this slug already exists,
  │   write back to its current name (prefixed or bare — never rename); else it is new — assign the
  │   next per-plan-root index → <plan-root>/implementation/<NN>-<chunk-slug>.md (scratch plans: <name>.md, no index)
  ├─ APPROVED: write chunk plan with NO `Status:` frontmatter (the binary mid-cycle convention) + persist sidecar (incl. creation_index) + render verdict
  └─ NEEDS_USER_INPUT: write partial draft with `Status: needs-user-input` and inline `## Pending blockers` + persist sidecar (incl. creation_index) + render verdict
```

In `--draft` mode the Plan-lint, Ground-truth audit, and Self-prosecution stages are skipped. The Concern gate STILL runs even in `--draft` (self-disclosed multi-concern bundling is a fatal scope error that does not get to defer behind the flag).

---

## State load

Read the author sidecar. Schema:

```json
{
  "feature": "<feature>",
  "chunk_slug": "<slug>",
  "creation_index": <int>,
  "artifact_path": "<plan-root>/implementation/<NN>-<chunk-slug>.md",
  "plan_worktree": {
    "action": "created | reused | in-place",
    "path": "<.worktrees/<SLUG>-plan or null when in-place>",
    "branch": "<<SLUG>-plan or null when in-place>",
    "in_place_reason": "--no-worktree | already-in-linked-worktree | scratch-plan | no-worktree-script | null",
    "authority_stack_from": "worktree | invocation-checkout (cold-create fallback)"
  },
  "authoring_mode": "ship | draft",
  "ground_truth_at": "<ISO 8601 UTC>",
  "self_prosecution_at": "<ISO 8601 UTC>",
  "invocation_number": <int>,
  "last_plan_sha256": "<hex>",
  "concern_gate_status": "passed | refused | skipped | carried_forward",
  "concern_gate_carry_forward_source": {
    "source": "review_state | author_state | decisions_closure",
    "source_path": "<verbatim path or `## Decisions closure` row>",
    "source_blocker_id": "<id or null when source is decisions_closure>",
    "carry_forward_until_round": <int>,
    "user_decision": "<verbatim>"
  },
  "plan_lint_status": "PASS | FAIL",
  "plan_lint_log": "<verbatim>",
  "claims_total": <int>,
  "claims_verified": <int>,
  "claims_verified_softened": <int>,
  "claims_corrected": <int>,
  "claims_dropped": <int>,
  "claims_restructured": <int>,
  "claims_skipped_carveout": <int>,
  "introduced_identifiers": [...],
  "ground_truth_model": "<model the verification batches ran on — haiku unless inline>",
  "ground_truth_log": [...],
  "persona_model": "<model the self-prosecution personas ran on — sonnet per the pin>",
  "self_prosecution_findings": [...],
  "prose_density": {
    "ran": true | false,
    "bytes_per_line_avg": <float>,
    "bullet_word_count_max": <int>,
    "parenthetical_nesting_depth_max": <int>,
    "overgrown_bullets": [
      {"section": "<Conventions|Tests to add|Acceptance criteria|...>", "bullet_anchor": "<first 8 words verbatim>", "word_count": <int>, "byte_count": <int>}
    ],
    "deeply_nested_sentences": [
      {"section": "<...>", "bullet_anchor": "<first 8 words verbatim>", "depth": <int>}
    ],
    "threshold_breached": ["bytes_per_line" | "bullet_word_count" | "nesting_depth" | ...],
    "carry_forward_source": {
      "decisions_md_row_decision_column": "<verbatim or null>",
      "resolution_column": "<verbatim or null>"
    } | null,
    "verdict": "passed" | "excess" | "carried_forward" | "skipped",
    "skipped_reason": "--draft" | null
  },
  "exclusion_challenges": [
    {
      "persona": "<persona_name>",
      "finding_id": "<f1>",
      "challenged_kind": "ground_truth_log" | "introduced_identifiers",
      "challenged_entry": "<verbatim entry the persona rebutted>",
      "challenge_evidence": "<path:line + verbatim quote the persona observed>",
      "disposition": "upheld" | "rejected" | "malformed",
      "adjudication_evidence": "<path:line the orchestrator re-verified against, or null>"
    }
  ],
  "conformance_gate_model": "<model pinned for the Brief-conformance gate, or null if the gate did not run>",
  "authoring_residual": [...],
  "prior_blockers": [
    {
      "blocker_class": "<class>",
      "path_or_section": "<verbatim>",
      "summary": "<verbatim>",
      "raised_in_round": <int>,
      "current_reclassification_justification": "<optional>"
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

`prior_blockers` / `recently_resolved_blockers` mirror the reviewer state schema in `~/.claude/cache/review-state/` so `/explain-blockers` parses author-state with the same parser. `CONCERN_GATE_FAILED` blockers land in `prior_blockers` alongside the universal classes (`STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `FIX_INTRODUCED_PREMISE_INVERSION`, `STRUCTURAL_LINT_FAILED`, `REPO_STATE_DRIFT`). Only HIGH+ findings land here; LOW findings under the polish floor stay in `authoring_residual`. `DRAFT_EMITTED` is set when `--draft` is passed; Plan-lint, Ground-truth audit, and Self-prosecution are skipped, the chunk plan IS written to disk with NO `Status:` frontmatter, the sidecar's `authoring_mode: "draft"` carries the load-bearing draft signal that downstream skills consult (authoring without `--draft` produces a hardened plan; the author is not re-run to harden). `NEEDS_USER_INPUT` is set when one or more HIGH+ blockers remain; the partially-improved chunk plan IS written to disk with frontmatter `Status: needs-user-input` AND an inline `## Pending blockers` section listing each unresolved finding verbatim (so the user knows what to resolve; the session agent then applies the resolutions directly to the plan and clears the `Status:` line — the author is not re-invoked).

Also read the review-state at `~/.claude/cache/review-state/<slug>.json`. Its `recently_resolved_blockers` list is warm-mode carry-forward — re-introducing a defect class the user closed is `FIX_INTRODUCED_PREMISE_INVERSION`.

Also read the engineering-plan-author sidecar `~/.claude/cache/author-state/<ep-slug>.json`. **The chunk-plan author refuses to run if the engineering-plan-author's last `verdict` is not `CLOSED`.** Per the engineering-plan-review-v2 verdict semantics, `APPROVED` means the engineering plan is shape-correct but cross-chunk decisions remain undecided — authoring chunk plans against an APPROVED engineering plan re-introduces every IMPLEMENTABILITY_GAP into the chunk, which is exactly the thrash this skill exists to prevent.

---

## Plan-worktree provisioning (when your project provides a worktree bootstrap script; runs after State load, before Source ingest)

When your project provides a worktree bootstrap script, the chunk plan is authored inside a **lightweight, per-plan worktree** off `origin/main`, not in the primary checkout. Plan authoring only ever writes markdown (the plan file), so the worktree is a plain `git worktree add` — it does **NOT** invoke that bootstrap script, and provisions **no** dev-stack services, dependencies, or seed data (that heavy path is `/execute-plan`'s, for code that runs tests). The worktree and its branch are named for this chunk plan's slug with a `-plan` suffix, so the authoring branch pairs with `/execute-plan`'s `<slug>` implementation branch and the two never collide. This keeps the primary checkout clean and lets parallel `/plan-author` sessions run without racing on the shared tree.

The provisioning happens after State load (which only touches the global `~/.claude/cache` sidecars) and before Source ingest, because Source ingest reads the feature's authority stack (`brief.md` / `engineering-plan.md` / `decisions.md`) and must resolve it inside the worktree when those artifacts are already on `main`, or from the invocation checkout when they are not yet merged (see the cold-create fallback).

### When it runs

Provisioning runs unless ANY of the following holds, in which case this stage is a no-op and authoring proceeds **in place** (record the reason in the sidecar and verdict):

- **`--no-worktree` was passed.**
- **The plan is a `.scratch/<name>.md` plan** — `.scratch/` is gitignored, so it has no git home to put on a branch. (`fixes/<name>.md` plans ARE git-tracked, so they DO get a plan worktree.)
- **Already inside a linked worktree** — `git rev-parse --git-dir` differs from `git rev-parse --git-common-dir`. The session is already isolated in some `.worktrees/<name>`; write the plan there rather than nesting a worktree in a worktree.
- **No worktree bootstrap script** — the repo has no executable worktree bootstrap script at its root (the project-specific tool that provisions an isolated per-chunk worktree with its own dev stack). This skill is global; the whole stage is a no-op elsewhere.

### Worktree identity

Deterministic, per-plan (one worktree per chunk plan, named for the plan's prefix-free slug — the same slug `/execute-plan` uses for its branch — plus a `-plan` suffix). Let `MAIN_ROOT` = `git rev-parse --show-toplevel`, and `SLUG` = the chunk's prefix-free slug (the H1 / `**Slug:**` slug, NOT the `NN-` filename prefix).

- **`features/<feature>/…` plan (flat or tracked):** `WT_NAME` = `BRANCH` = `<SLUG>-plan`.
- **`fixes/<name>.md` plan:** `WT_NAME` = `BRANCH` = `<name>-plan` (the plan's basename slug).
- `WT_PATH` = `$MAIN_ROOT/.worktrees/$WT_NAME`.

The `-plan` suffix keeps this worktree and branch distinct from `/execute-plan`'s implementation `<SLUG>` worktree/branch, so authoring a plan and implementing it never collide.

### Steps

1. **Reuse guard.** If `$WT_PATH` already exists:
   - its checked-out branch is `$BRANCH` (`<SLUG>-plan`) → **adopt it**: re-anchor to `$WT_PATH`, skip creation. This is a re-author of the same chunk plan.
   - any other branch → REFUSE `PLAN_WORKTREE_COLLISION` (something else owns that path; the user resolves it — e.g. `/cleanup-worktree <WT_NAME>`).
2. **Sync + pin the base (fresh create only).** `git -C "$MAIN_ROOT" fetch origin main`. Pin the branch to `origin/main` explicitly rather than forking off the shared checkout's current HEAD (the shared-tree branch-creation race): `git -C "$MAIN_ROOT" branch "$BRANCH" origin/main`. If `$BRANCH` already exists with no worktree (a leftover from an aborted run), reuse it; otherwise the branch is live elsewhere → REFUSE `PLAN_BRANCH_EXISTS`.
3. **Create the worktree.** `git -C "$MAIN_ROOT" worktree add "$WT_PATH" "$BRANCH"`. Plain and fast — no project bootstrap script, no dev-stack services or dependencies.
4. **Re-anchor.** Set the working directory to `$WT_PATH` for Source ingest and every stage below. All authority-stack reads, read-set reads, sibling-plan reads, the Brief-conformance gate's `{brief_path}`/`{decisions_path}` substitutions, and the final plan write resolve inside `$WT_PATH`. The sidecar (`~/.claude/cache/author-state/<slug>.json`), the DRAFT materialization (`~/.claude/cache/author-state/<slug>-DRAFT.md`), and the Plan-lint temp (`/tmp/<slug>-draft-<timestamp>.md`) keep their absolute paths — they are outside the repo and unaffected.

### Authority-stack presence (cold-create fallback)

A per-plan worktree is a fresh branch off `origin/main`, so it carries the authority stack only when `brief.md` / `engineering-plan.md` / `decisions.md` are already merged to `main`. When they are not (authored in place by the sister skills and not yet merged), do NOT fail the Source-ingest hard requirements: read the authority stack from the **invocation checkout** by absolute path, still write the chunk plan into the worktree, and surface a SOFT note in the verdict — brief/EP/decisions should land on `main` (or ride along in this plan's PR) so the plan is reviewable against its real upstream. Record `plan_worktree.authority_stack_from: "invocation-checkout (cold-create fallback)"`. Sibling chunk plans authored on their own `-plan` branches are visible here only once merged to `main`; an unmerged sibling this plan references is read from the invocation checkout the same way, or surfaced as a SOFT note if absent. (Mirror of `/execute-plan`'s not-yet-merged plan-file handling.)

### Sidecar `artifact_path`

`artifact_path` stays the logical, repo-relative path (`<plan-root>/implementation/<NN>-<chunk-slug>.md`) that downstream skills resolve by slug; the physical worktree location is recorded separately in `plan_worktree`.

### After authoring

`/plan-author` does NOT commit, push, or open a PR — the plan file simply lands on the `<SLUG>-plan` branch in the worktree. Run `/plan-review-v2` from inside the plan worktree (the plan and its authority stack resolve there), then commit + `/open-pr` when clean. After the plan PR merges, tear the worktree down with `/cleanup-worktree <WT_NAME>` (or `git worktree remove` — the plain worktree has no dev-stack services, so `/cleanup-worktree`'s dev-stack teardown is a guarded no-op for it).

---

## Source ingest

Hard requirements:
- `features/<feature>/brief.md` exists.
- `<plan-root>/engineering-plan.md` exists, and its chunk index contains this chunk's slug. Under the tracked layout, a slug indexed by a *different* track means the argument named the wrong track — stop and report, rather than authoring the chunk into a plan that does not sequence it.
- Engineering-plan-author sidecar `verdict == "CLOSED"` (or sidecar absent — cold mode is acceptable in early development; warn in verdict).
- The chunk's row in the engineering-plan chunk index exists, with a one-concern description.

Read in this order:

1. `features/<feature>/brief.md` — Goals/Non-goals.
2. `<plan-root>/engineering-plan.md` — focus on the chunk's row in the chunk index, the dependency graph (which sibling chunks ship before this one), the decisions-closure entries that the chunk relies on, and the invariants the chunk enforces.
3. `features/<feature>/decisions.md` — every entry the chunk plan will cite.
4. Existing chunk plan (when re-authoring) — current §Owns, §Contracts, etc. are a carry-forward constraint. A mid-cycle `Status: needs-user-input` plan is resolved by the session agent applying blocker resolutions directly, not by re-running this skill.
5. Every file in the chunk's planned "Read first" list — the implementer's read-set is the chunk's anchor surface; the author must have read all of it.
6. `CLAUDE.md` (project conventions, business rules); `MEMORY.md` + relevant project memory.
7. The project's schema/data-model definition file (if backend chunk) or its API operation definitions (if frontend chunk).
8. Sibling chunk plans in `features/*/implementation/*.md` and `features/*/plans/*/implementation/*.md` — for shape, tone, density, depth-of-prescription consistency.

Build:
- **Invariants ledger** — every brief Goal + every engineering-plan invariant the chunk enforces.
- **Identifier ledger** — every existing identifier the chunk references (functions, types, schema fields, helpers, test patterns from sibling tests). Each gets a verification source.
- **Decisions ledger** — every decisions.md entry the chunk cites.

---

## Concern gate

Deterministic check against the chunk's description, extracted from the engineering-plan chunk-index row matching this slug (located in the Source-ingest stage). The gate runs before Draft. Only ONE pattern triggers refusal — self-disclosure. Concern judgment otherwise is semantic, performed by the ai-development persona's halved-work test in Self-prosecution against the drafted Goal sentence and §Owns set.

### Refusal pattern (match invokes carry-forward consultation; absent carry-forward, the gate refuses)

**Self-disclosure of bundling.** Description matches `/\b\d+-concern\b|\bN-concern\b|\bbundle\b|\bbundling\b/i`. Example: "Orphan-cleanup hardening (4-concern bundle)". This is the author actively admitting the chunk is multi-concern; no false-positive case exists for an author writing "this is a 4-concern bundle" while meaning a single chunk.

### Patterns NOT enforced by this gate

The earlier version of this skill enforced four additional syntactic patterns as auto-refuse triggers: ` AND ` conjunctions, three+ comma-separated noun phrases, `+ <noun> + <noun>` separators, and ≥2 independent clauses. They were dropped. Each had high false-positive rates on legitimate prose:

- "Extract helper used in 12 sites and migrate callsites" is one concern (the migration is incomplete without the extraction).
- "Add fieldA, fieldB, fieldC to the User model" is one schema change with three named columns.
- "Refactor X to use Y and update its callers" is one concern (the rewrite is incomplete without the callsite migration).
- "Schema migration: drop column X; backfill column Y; add index Z" describes one mechanical change with three named ripples.

Concern judgment for these cases is semantic, not syntactic. The ai-development persona evaluates every chunk in Self-prosecution with the **halved-work test**: "if you halved the work in §Owns, would the other half still be a coherent shippable thing?" If yes → multi-concern, surface a finding. If no → one concern, proceed. The persona runs on every chunk regardless of pattern matches; explicit syntactic detection is not needed because the persona reads the actual draft and judges semantically.

### Carry-forward consultation

Run only on a self-disclosure match. The decision is deterministic: carry-forward applies, or it does not. Three sources are checked, in order; the first match wins.

1. **Engineering-plan reviewer state.** Read `~/.claude/cache/review-state/<ep-slug>.json`. In `recently_resolved_blockers`, find an entry where ALL of:
   - `path_or_section` substring-matches one of: the chunk slug; the chunk-index row's verbatim description; or `chunk-index row N` where N is the row's index position.
   - `blocker_class_when_resolved` is one of `CONCERN_GATE_FAILED`, `CHUNK_BUNDLE`, `MULTI_CONCERN`, `CONCERN_FACTORING` — OR `summary` contains both a concern-family keyword (`bundle`, `concern`, `factoring`) and a resolution-direction keyword (`accept`, `bound`, `keep`, `retain`, `reaffirm`).
   - `carry_forward_until_round >= current_invocation_number` (cross-side number-line mapping per `_author-common/self-prosecution-protocol.md`).

2. **Engineering-plan-author state.** Read `~/.claude/cache/author-state/<ep-slug>.json`. Apply the same three-condition match against ITS `recently_resolved_blockers`.

3. **Engineering-plan decisions-closure scan.** Read the engineering plan's `## Decisions closure` section (already in memory from Source ingest). A row carries forward when ALL of:
   - The `Decision` column substring-matches the chunk slug or the row's verbatim description.
   - The `Resolution` column starts with `bound` (case-insensitive), AND if the row cites a `decisions.md` entry, that entry is still Active-bound — not `superseded`/`obsolete` (a stale EP row citing a since-retired decision does not carry forward; per `~/.claude/skills/_review-common/principles.md` § What counts as a bound entry).
   - The `Resolution` column contains a concern-family keyword (`bundle`, `multi-concern`, `mutually load-bearing`, `transactional invariant`, `theme-unified`).

If any source matches, set `concern_gate_status: "carried_forward"`, populate `concern_gate_carry_forward_source` with the source kind, path/citation, blocker id (when applicable), `carry_forward_until_round`, and the user's decision verbatim. Proceed to Draft.

If no source matches, refuse. Emit `CONCERN_GATE_FAILED` with:
- The exact phrase that triggered the refusal.
- The three actionable resolution paths, in preference order:
  1. Rewrite the engineering-plan chunk-index row description to single-concern phrasing citing the decision (preferred — most durable).
  2. Add an explicit `## Decisions closure` row arbitrating the bundle, with `bound` status and a concern-family keyword in the resolution.
  3. Re-run `/engineering-plan-review-v2` to record the arbitration in the reviewer state's `recently_resolved_blockers`.

---

## Draft

Mirror this section template:

```markdown
# Chunk: `<chunk-slug>` — <one-concern description>

**Slug:** `<chunk-slug>`
**Feature:** <feature>
<!-- Status frontmatter is OPTIONAL and binary. Set to `needs-user-input` ONLY when the chunk plan is mid-cycle (auto-managed by /plan-author NEEDS_USER_INPUT path). Otherwise omit entirely. Lifecycle states (in-progress, merged, verified) are derived from branch / PR / merge state, not frontmatter. -->
<!-- Status: needs-user-input -->  <!-- only when mid-cycle -->

**PR:** —
**Depends on:** `<sibling-chunk-slug>` (if applicable, from engineering-plan dependency graph)
**Brief:** [`../brief.md`](../brief.md) · **Engineering plan:** [`../engineering-plan.md`](../engineering-plan.md)
<!-- Tracked layout: the engineering-plan link is unchanged (still one level up), but the
     brief sits two levels higher — use [`../../../brief.md`](../../../brief.md). -->


> This plan is derived from the engineering plan, which is derived from the brief. If you can't restate this chunk's purpose in terms of a brief Goal or User-facing change, stop and re-read both before continuing.

## Goal

<One-sentence statement of what this chunk ships. ONE concern. Verifiable.>

## Brief link

- **Goal:** <verbatim brief Goal quote> — <how this chunk advances it>
- **Scope exclusion honored:** <verbatim quote from the brief's Scope buckets, with its bucket named> — <how this chunk respects it>

## Context pack

**Read first:**
- <every file the implementer must read; each entry has a one-line WHY>

**Reference:**
- <less-critical files the implementer may consult>

**Conventions / patterns to follow:**
- <byte-format pinned conventions; ground-truthed against existing code or explicitly chunk-introduced>

## Factoring Contract

### Owns
- `<file-path>` — <what this file does post-chunk; one line>
- ...

### Contracts changed
- <new type / new function / new schema field / new GraphQL operation / new exported constant>
- ...

### Tests to add
- `<behavior + assertion shape>` — <NEVER a literal test path; describe the test by what it asserts>
- ...

### Invariant classes touched
<From the project's `features/lint-config.json`. `none` is valid and common; an absent
field is not — silence and `none` are different claims, and the cap is uncheckable
without one. A class counts only when this chunk adds, removes, weakens, or
strengthens an invariant in it; editing code that happens to sit in that domain
does not.>
- `none`   <!-- OR: `<class>` — <what changes about the invariant> -->

### Acceptance criteria
- [ ] <verifiable criterion>; verify with `<command>`
- ...

## Kill criteria

<Pre-stated conditions under which this chunk STOPS and returns to planning. At
least one, falsifiable, checkable before the chunk is half-built. Acceptance
criteria say when it is done; these say when it was wrong. A risk you intend to
mitigate is not a kill criterion — that belongs in the engineering plan's Risks
section, as does any condition that would abandon the whole feature.>

- [ ] <condition with a threshold, named test, gate, or command>
- ...

## Review checklist

- [ ] <load-bearing thing the reviewer must hand-verify>
- ...

## Out of scope

| Item | Where instead |
|---|---|
| <adjacent concern> | <sibling chunk slug \| decisions.md date entry \| explicit out-of-scope> |
```

### Drafting rules — chunk-plan layer

- **Goal sentence is ONE concern.** Apply the halved-work test: if you halved the work in §Owns, would the other half still be a coherent shippable thing? If yes, the chunk is multi-concern; split it. Conjunctions in the Goal sentence are NOT a refusal trigger — "extract helper used in 12 sites and migrate callsites" is one concern (the migration is incomplete without the extraction); "add field X and the test that proves X" is one concern (the test is not separate work). The halved-work test is what matters, not the surface syntax.
- **Context pack "Read first" is honest.** Every file listed is one the implementer truly must read; gratuitous additions just dilute attention.
- **Conventions are byte-format pinned OR cite an existing pattern.** Conventions like "stderr regex format `^abort: ...`" or "audit-row write inside `db.transaction(async (tx) => { ... })`" are byte-pinned and testable. Conventions like "use good error handling" are useless.
- **§Owns describes file purpose, not implementation steps.** "X.ts owns the orphan-deletion script" is good. "X.ts step 1: parse args; step 2: query orphans; step 3: ..." is implementation prose that drifts as code is written. Steps go in the implementer's head, not the plan body.
- **Compute the outcome on its authoritative signal, not a proxy (basis fidelity).** When your §Goal — or the brief Goal / engineering-plan chunk-index row it delivers — names a distinguished *authoritative signal* the outcome must be judged on ("the classifier verdict", "the restored author links", "judged on the work itself"), your §Owns / §Contracts / §Acceptance must compute it on that signal, not a degraded proxy (a title-pattern heuristic for a classifier verdict; a snapshot count for restored links). This is the write-side mirror of `/plan-review-v2`'s Stage 1 basis-fidelity check and the chunk-layer half of the engineering-plan-layer Scope-fidelity Adversary (the other two parity axes — domain coverage and pipeline timing — live at the engineering-plan layer). The one legitimate exception: the EP row, a bound `decisions.md` entry, or your §Out of scope already committed the proxy and framed it as launch-acceptable — then it is the engineering-plan layer's call, already made, and you implement it as bound. Silently resolving an authoritative-but-underspecified EP row *toward* the proxy is a `SURFACE_PARITY_GAP` the reviewer will file; catch it here instead.
- **§Contracts changed enumerates exports + schema diffs only.** New non-exported helpers don't go here.
- **§Tests describes assertion shape, not test paths.** Per `P-CHUNK-TEST-PATHS`. The test harness layout is the implementer's call.
- **§Acceptance criteria is verifiable by command.** Every box has a `verify with <command>`. The command must exist (`npm test`, `npm run typecheck`, etc.) — verified at ground-truth time.

- **Size §Owns against the review-complexity budget while drafting it, not after.** The project's `features/lint-config.json` sets three axes: weighted file count, subsystems crossed, and invariant classes changed (docs weigh 0, tests weigh 0.5 and never add a subsystem). Two of them — subsystems and invariant classes — have **no exemption path**: over the cap, the chunk splits, and no rationale changes that. Their overflow is a correctness signal rather than a capacity one. Crossing four subsystems says the chunk carries a cross-layer contract the engineering plan never wrote down, and the right response is to find that contract and make it the seam between two chunks. Carrying three invariant classes says a cross-domain interaction is about to be introduced that nobody enumerated.
  Discovering this at lint time means rewriting the plan you just wrote, so run the count while §Owns is still a list. If it overflows, the split usually already exists in the file list — group the paths by subsystem and see which group serves a different concern than §Single concern names. When the project has no `lint-config.json`, this rule does not apply; do not invent thresholds.

- **§Invariant classes touched is a claim, and `none` is the common one.** Declare a class only when this chunk changes an invariant in it — adds, removes, weakens, or strengthens. A chunk that reads an auth-guarded resolver without touching the guard declares `none`. Over-declaring is not a safe default: it burns the two-class cap on chunks that do not need it, and it trains the reader to skim the field. Under-declaring is worse, because the no-exemption cap is what stops a cross-domain interaction from shipping unreviewed. When genuinely unsure whether a change weakens an invariant, declare it and say what changes.

- **§Kill criteria is written before the work, or it is worthless.** Ask what you could learn mid-chunk that would mean this plan is wrong — not "this might be slow" but the threshold past which slow means re-planning. Each criterion is falsifiable and checkable early: a threshold, a named test, a gate, a command. The value is entirely in having pre-committed, because the moment the condition actually fires is the moment sunk cost makes it hardest to call.
  Do not restate risks here. A risk has a mitigation you intend to apply; a kill criterion has none, because it means the plan needs rewriting. A condition that would abandon the whole feature rather than this chunk belongs in the engineering plan's Risks section instead.
- **§Review checklist is short.** 5-15 items. The list calls out load-bearing things; the implementer's full diff has many other lines that don't need surfacing.
- **§Out of scope cites decisions.** If the chunk explicitly does NOT do something the brief allows, cite the decisions.md entry that bound the deferral.
- **No archaeological prose.** No "the original plan said X but actually Y", no "round-3 review changed this", no "see addendum E". Per `_review-common/principles.md` plan style.
- **No persona-attribution headers.** One document, one voice.
- **No invented test infrastructure.** If the chunk's tests need a helper, either (a) the helper exists in a sibling test file (verify and cite), (b) the helper is introduced by THIS chunk (add to §Contracts changed), or (c) the test bullet describes the inline pattern verbatim (e.g., the `vi.spyOn(console, 'error')` template).
- **Diagnostic byte-formats live in §Conventions.** If the chunk's tests assert byte-exact regex on stderr, the regex template is pinned in §Conventions once, not duplicated per test bullet.
- **Proactive convention extraction (≥3 same-shape rule).** When drafting §Tests, §Owns, or §Acceptance criteria, if you find yourself writing the **same structural pattern across 3+ bullets**, extract the pattern to §Conventions before continuing. Examples of structural patterns that MUST be extracted at the third recurrence:
  - The same test setup invariant (e.g., `vi.spyOn(console, 'error').mockImplementation(...)` in 3+ test bullets) → extract as `Convention: stderr-suppression in tests using <pattern>`.
  - The same trap-row idiom in 3+ test setups (e.g., "insert a row whose deletion would violate FK constraint to assert the cleanup script aborts") → extract as `Convention: trap-row idiom for <invariant under test>`.
  - The same byte-exact diagnostic format in 3+ assertions (e.g., `expect(stderr).toMatch(/^abort: cannot proceed: <reason>/)` with shared prefix) → extract as `Convention: abort-stderr regex template`.
  - The same cleanup ordering across 3+ §Owns descriptions → extract as `Convention: cleanup ordering for <resource class>`.
  Without proactive extraction, the same pattern is restated 3+ times in the plan body — exactly the duplication that drives the "≥3 same-shape fix bullets" pattern at review time. The reviewer's convention-extraction sub-step will fold the duplications back into §Conventions as a fix; doing it at write time saves the round.
- **Drafted prose must not contradict bound decisions — class-aware.** Before emitting the in-memory draft to Plan-lint, scan §Goal, §Brief link, §Conventions, §Owns, §Contracts changed, §Tests to add, §Acceptance criteria, and §Out of scope for prose that contradicts an entry in `features/<feature>/decisions.md` whose `Status:` is `bound` (only Active-section `bound` entries — a `superseded`/`obsolete` entry in the `## Archived` tail no longer forces a rewrite; per `~/.claude/skills/_review-common/principles.md` § What counts as a bound entry). Per `_review-common/principles.md` § Cross-artifact authority order, the rule is class-aware. **Class B contradictions** (the chunk plan contradicts a bound *wiring* decision — e.g., a bound entry says "use approach X for cross-author dedupe" and the chunk plan's §Tests describes a test that only passes under approach Y): bound decision wins; rewrite to match, OR surface as `OPEN_QUESTION` if the contradiction is a discovery. **Class A contradictions** (the chunk plan's §Owns / §Acceptance / §Tests implements behavior a parent-feature brief Non-goal forbids, even if a bound decision separately committed to it): the **brief wins**. Refuse to emit; surface as `BRIEF_NONGOAL_TRESPASS`. The bound decision is itself the defect. The Brief-conformance gate (which spawns the Brief-conformance Prosecutor against the in-memory draft) is the proactive write-side pair for Class A; the Self-prosecution carry-forward auto-retract handles persona findings reactively.

---

## Brief-conformance gate (mandatory when parent feature exists; runs BEFORE Plan-lint)

Authoring-side equivalent of `/plan-review-v2`'s Stage 1.5 Brief-conformance audit. **Skipped for `.scratch/` and `fixes/` plans** (no parent feature).

### Procedure

1. **Draft the chunk plan in memory.** Build §Goal, §Brief link, §Owns, §Contracts changed, §Tests to add, §Acceptance criteria, §Out of scope. Hold in memory.

2. **Materialize to temp file** under `~/.claude/cache/author-state/<slug>-DRAFT.md` (or `~/.claude/cache/author-state/scratch__<name>-DRAFT.md` for scratch plans — though scratch plans skip this gate entirely, the path convention is consistent).

3. **Spawn the Brief-conformance Prosecutor.** Launch one `general-purpose` subagent (Agent tool, default subagent type) with the prompt from `~/.claude/skills/_review-common/brief-conformance-prosecutor.md`. Pass an explicit off-model `model` override per that file's § Model pin (default `sonnet`; `opus` if the session is already Sonnet) and record `conformance_gate_model` in the sidecar — never inherit the session model here. Substitutions:
   - `{brief_path}` = `features/<feature>/brief.md`
   - `{plan_path}` = the temp chunk plan draft
   - `{decisions_path}` = `features/<feature>/decisions.md`
   - `{sibling_plan_paths}` = every OTHER track's `engineering-plan.md` when the feature is tracked, else "none"
   - `{plan_layer}` = `chunk-plan`
   - `{additional_examples}` = chunk-plan-specific worked examples (same two examples as `/plan-review-v2`'s Stage 1.5 — orchestrator appends them inline) plus this chunk's accumulated calibration examples from the sidecar's `brief_conformance_calibration_examples`

4. **Process findings.** Same flow as `/engineering-plan-author`'s gate:
   - `brief_conformance_check: passed` → proceed to Plan-lint and Ground-truth audit.
   - `findings_filed` with only MEDIUM HARD → partial-draft-to-disk with `Status: needs-user-input`, blockers listed verbatim in `## Pending blockers`, user adjudicates.
   - `findings_filed` with any HIGH HARD → hard refusal, same partial-draft flow with a `BRIEF_NONGOAL_TRESPASS` or `BRIEF_GOAL_UNDELIVERED` verdict label.

5. **§Out of scope auto-population from brief Non-goals — runs BEFORE the prosecutor as a courtesy step.** Before the prosecutor runs, the author identifies parent-feature Non-goals whose surface area intersects this chunk's §Owns (the chunk touches a file/resolver/script the Non-goal scopes out) and auto-populates §Out of scope with the verbatim Non-goal text. This makes the brief's scope guard locally visible to the implementer reading the chunk plan in isolation. The prosecutor then runs against the populated draft — explicit §Out of scope entries citing Non-goals will be recognized as *honoring*, per the prosecutor's calibration discipline.

   This step uses LLM reasoning to identify surface intersections, not keyword matching. The author reads the parent feature's Non-goals and asks: "is this chunk in a position where it could plausibly trespass this Non-goal, even by accident during implementation?" If yes, cite the Non-goal in §Out of scope.

6. **Sidecar block.** Write the gate's output to the author sidecar at `~/.claude/cache/author-state/<feature>__<chunk-slug>.json`:
   ```json
   {
     "brief_conformance_gate": {
       "brief_sha": "<sha256 of brief.md at draft time>",
       "engineering_plan_sha": "<sha256 of engineering-plan.md at draft time>",
       "chunk_draft_sha": "<sha256 of the temp draft>",
       "chunk_slug": "<slug>",
       "prosecutor_verdict": "passed" | "findings_filed" | "skipped (.scratch/)",
       "findings_total": <int>,
       "findings_high_hard": <int>,
       "findings_medium_hard": <int>,
       "nongoals_auto_populated_to_out_of_scope": [<verbatim Non-goal texts>],
       "brief_conformance_calibration_examples": [<list>],
       "blockers": [<verbatim prosecutor findings>]
     }
   }
   ```

   The `brief_conformance_calibration_examples` list grows over rounds — chunk-plan-layer calibration stays scoped to chunk-plan invocations (not propagated up to engineering-plan invocations) because chunk-plan false positives reflect layer-specific phrasing.

### Why write-side prosecution matters at the chunk-plan layer

A chunk plan that implements a brief Non-goal in §Owns (touching files the Non-goal scopes out) or §Acceptance (committing to outcomes the Non-goal excludes) is structurally wrong even if Plan-lint passes and Self-prosecution finds no in-scope defects. The brief Non-goal is the outermost contract, and a chunk plan implementing against it cascades: the implementer follows the plan, ships the trespass, the trespass propagates into the codebase, and the next feature inherits the precedent.

---

## Plan-lint gate

Write the in-memory draft to `/tmp/<slug>-draft-<timestamp>.md`, then invoke the lint script directly:

```bash
python3 ~/.claude/skills/plan-lint/lint.py /tmp/<slug>-draft-<timestamp>.md
```

Capture stdout + exit code into `sidecar.plan_lint_log`. Exit codes: `0` clean, `1` FAIL, `2` usage/IO error. Apply local fixes and re-run up to 2x; if structural defects remain after 2 retries, surface `STRUCTURAL_LINT_FAILED`. Delete the temp file regardless of outcome.

Same deterministic gate semantics as the engineering-plan-author's Plan-lint gate — the chunk-plan layer operates on a chunk plan instead of an engineering plan, but the script handles both layouts.

---

## Ground-truth audit

Apply `_author-common/ground-truth-protocol.md`. At the chunk-plan layer:

- **V1 (anchor) is heavy.** Every `path:line` reference, every `§heading` reference, every line-range reference. Substitute symbolic anchors (`<file>:<symbol>` or `§<heading>`) for numeric ones whenever possible — numeric lines drift, symbols don't.
- **V2 (identifier) is heavy and bimodal.** Every helper / type / constant / schema-field / GraphQL-op reference splits into:
  - Carve-out 1 — introduced by THIS chunk → record in `introduced_identifiers`, do NOT verify against existing repo (the chunk's contract is to make them exist).
  - Anchor — must already exist or come from a sibling chunk that owns it (per A-INTRODUCE-vs-RELOCATE) → verify via grep / Read.
- **V3 (constraint) catches math errors.** "N writer-fence ticks per refresh cycle", "a uniqueness constraint on X", "X happens before Y in source order". Verify by reading the cited file.
- **V4 (cross-document)** every brief/engineering-plan/decisions/CLAUDE.md citation. Verbatim quote check.
- **V5 (external API)** rare. Most chunks integrate via project wrappers (`src/lib/<api-client>.ts` per upstream API); claims about these wrappers are V2 against project code, not V5 against external docs.

Sidecar audit log records every claim, outcome, evidence.

The volume here is the largest of the three layers — chunk plans typically have 50-150 verifiable claims. Each costs one Read or grep. Front-load is roughly equivalent to one round of `/plan-review-v2` machinery.

---

## Self-prosecution

Spawn 5 persona agents in parallel using the template in `_author-common/self-prosecution-protocol.md`:

- **backend** OR **frontend** — depending on which directory the chunk's §Owns concentrates in. Backend chunks use the backend persona; frontend chunks use the frontend persona. Mixed-stack chunks (rare; usually a sign of multi-concern) get both.
- **architecture** — system-shape coherence, hidden dependencies, factoring, cross-chunk wiring.
- **testing** — assertion-shape rigor, test-helper hallucinations, fixture coverage, RED-state ordering, real-DB cleanup conventions. **This persona catches the highest volume of findings at the chunk layer** (per the stale-record-cleanup case study, 14+ findings classed Testing).
- **security** — auth checks, input validation, secret handling, atomic rollback, DB constraint-violation scrub bindings (unique/not-found), cascade-flip dust quantification.
- **ai-development** — chunk discipline, plan-quality, banned style, byte-format prescriptions vs proscriptions.

Active critical pairs: universal pairs + chunk-plan-specific pairs (`P-CHUNK-TEST-PATHS`, `P-CHUNK-COMMANDS`, `P-CHUNK-SINGLE-CONCERN`, `P-CHUNK-READ-FIRST`).

After consolidation, run post-fix premise verification on orchestrator-rewritten prose. Classify residuals.

### Verdict template

```markdown
# Chunk plan authoring verdict — <plan-root>/implementation/<NN>-<chunk-slug>.md

**Mode:** cold | warm
**Authoring mode:** ship | draft
**Plan worktree:** <`.worktrees/<SLUG>-plan` on branch `<SLUG>-plan` (created | reused) | in-place (--no-worktree | already in linked worktree | .scratch/ | no worktree bootstrap script)>
**Round:** <invocation_number>
**Last plan sha:** <hex>

## Concern gate
**Status:** passed | refused | carried_forward
**Refusal reason (if refused):** <triggering phrase + decomposition suggestion>
**Carry-forward source (if carried_forward):** <review_state | author_state | decisions_closure> entry <id-or-citation> until round <N>

## Plan-lint
**Status:** PASS | FAIL
**Defects:** <N>; if FAIL, list each.

## Ground-truth audit
**Claims total:** <N>
**Verified:** <V>  **Softened:** <S>  **Corrected:** <C>  **Dropped:** <D>  **Restructured:** <R>  **Skipped (carve-out):** <K>
**Introduced identifiers:** <count> (<comma-separated list, truncated>)

## Self-prosecution
**Personas:** <persona list>
**Premise interrogation:** <per-persona pass/fail>
**Standard findings:** <N total>; <by tier+severity>
**Fixes applied:** <int>
**Post-fix premise verification:** <P claims rewritten; Q falsified> → <FIX_INTRODUCED_PREMISE_INVERSION count>
**Carry-forward consultation:** <skipped because cold | M recently-resolved blockers cross-checked, R re-prosecutions auto-retracted>

## Prose-Density gate
**Verdict:** passed | excess | carried_forward | skipped (--draft only)
**bytes_per_line_avg:** <float> (threshold 200)
**bullet_word_count_max:** <int> (threshold 400); offending bullet anchor (if breach): <first 8 words verbatim>
**parenthetical_nesting_depth_max:** <int> (threshold 3); offending sentence anchor (if breach): <first 8 words verbatim>
**Carry-forward (if applied):** decisions.md row "<Decision column verbatim>" — Resolution: "<Resolution column verbatim>"

## Verdict
**APPROVED** | **NEEDS_USER_INPUT** | **DRAFT_EMITTED**

### Blockers (if NEEDS_USER_INPUT)
- [CONCERN_GATE_FAILED] — <triggering phrase>; decomposition required
- [STRUCTURAL_LINT_FAILED] — <plan-lint defect>
- [PROSE_DENSITY_EXCESS] — <breached sub-metric(s) + offending bullet/sentence anchor(s)>; split overgrown bullet OR promote nested clauses to peers OR cite a `decisions.md` row arbitrating density
- [STABLE_DISAGREEMENT] <span> — <one-line>
- [OPEN_QUESTION] <span> — <one-line>
- [FIX_INTRODUCED_PREMISE_INVERSION] <span> — <one-line>
- [REPO_STATE_DRIFT] — git rev-parse HEAD changed mid-authoring; re-invoke

### Authoring residuals (LOW, under polish floor)
- ...
```

### Verdict gates

- **APPROVED** when ALL of:
  - Concern gate passed OR carried_forward.
  - Plan-lint PASS.
  - Ground-truth complete.
  - All HIGH+CRITICAL self-prosecution findings resolved.
  - Prose-Density gate `passed` OR `carried_forward`. (`skipped` is reachable only in `--draft` mode, which exits via `DRAFT_EMITTED`, not APPROVED; any flow that lands `skipped` at the APPROVED gate is a bug and falls through to `NEEDS_USER_INPUT`.)
  - Tier-2 weight ≤ 4 (polish floor).
  - No `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `FIX_INTRODUCED_PREMISE_INVERSION`, `CONCERN_GATE_FAILED`, `STRUCTURAL_LINT_FAILED`, `PROSE_DENSITY_EXCESS`, `REPO_STATE_DRIFT`.
- **NEEDS_USER_INPUT** otherwise.

### Prose-Density gate (deterministic; runs after Self-prosecution; HARD-blocking when triggered)

Runs unconditionally after Self-prosecution. The only skip path is `--draft` mode (Self-prosecution itself is skipped, so the post-self-prosecution measurement point does not exist; `prose_density.verdict: "skipped"`). The gate measures the artifact-on-disk's structural quality regardless of how the bloat got there — the failure modes include (a) Self-prosecution accreting fixes into existing bullets in the current run, (b) prior bloat persisting on disk because the session agent's direct fix-edits (which don't re-run this gate) or a clean-slate re-author left it in place, (c) the first Draft writing defensively dense prose to begin with, and (d) user hand-edits. An earlier draft of this gate tied execution to `self_prosecution_fixes_applied >= 1` on the theory that bloat only accretes through fix application; that optimization was wrong because it conflated *how* the bloat arrived with *whether* it is present. The on-disk artifact is the measurement target; provenance is irrelevant. The gate catches an artifact-bloat failure mode that the dropped Byte-budget gate could not target: per-bullet defensive accretion. A chunk plan can pass Plan-lint, Ground-truth audit, and Self-prosecution while individual §Conventions / §Tests to add / §Acceptance criteria bullets balloon into multi-paragraph defensive prose. Length-as-such is downstream of footprint breadth (a 600-line plan for a 12-callsite refactor is legitimate); per-bullet density is a structural-quality property orthogonal to length.

### Sub-metrics

Compute three sub-metrics over the post-self-prosecution in-memory draft:

- `bytes_per_line_avg` — total bytes in the three canonical prescriptive sections divided by the line count across those three sections. The sections are identified by name regardless of heading level (the template uses `**Conventions / patterns to follow:**` as a bolded sub-label under `## Context pack`, and `### Tests to add` + `### Acceptance criteria` as h3 sub-headings under `## Factoring Contract`): match the `Conventions / patterns to follow:` bold-label, `Tests to add` heading, and `Acceptance criteria` heading wherever they sit. Exclude code-fence blocks (lines between ` ``` ` markers) and markdown table rows — these have legitimate density different from bullet prose.
- `bullet_word_count_max` — for each bullet (a top-level `- ` or `* ` line plus its continuation lines until the next top-level bullet or section heading), count whitespace-separated words; record the maximum across the document.
- `parenthetical_nesting_depth_max` — for each sentence in any bullet, compute the maximum depth of nested parentheses (or square brackets / curly braces used parenthetically — not Markdown link syntax `[text](url)` which is depth 1 by definition). Track the maximum across the document.

### Thresholds

File `PROSE_DENSITY_EXCESS` as a HARD blocker when ANY of:

- `bytes_per_line_avg >= 200`
- `bullet_word_count_max >= 400`
- `parenthetical_nesting_depth_max >= 3`

Rationale: a well-factored chunk-plan bullet is one short imperative sentence (~80-150 bytes, ~15-30 words, zero or one parenthetical aside). Two-hundred bytes/line averaged across the prescriptive sections means bullets are multi-sentence on average; 400+ words in any single bullet means a section's worth of prose stuffed under one bullet header; three levels of nested parentheticals means defensive accretion (each layer added to defend the layer above against a persona finding rather than splitting or restructuring).

### Blocker contents

The `PROSE_DENSITY_EXCESS` finding names:

- All three computed sub-metric values (even those under threshold).
- Which threshold(s) breached.
- The specific bullets responsible: per overgrown bullet, the section name + first-8-words anchor + word count + byte count; per deeply-nested sentence, the section name + first-8-words anchor + depth.
- Three actionable resolutions:
  1. **Split the overgrown bullet** into N peer bullets at the same `- ` indentation level. Sub-clauses with their own citations (decisions.md anchors, sibling-chunk references) are peers, not nested clauses.
  2. **Promote nested parentheticals to peers.** A parenthetical that elaborates a sub-property, defends against a defect class, or cites a decision is a peer bullet, not a nesting layer. Three-deep nesting almost always re-flows cleanly as three sibling bullets.
  3. **Cite a `decisions.md` row arbitrating density for this chunk.** The row must be `Status: bound`, its Decision column must substring-match the chunk slug or chunk-index row description, and its Resolution column must contain a density-acknowledgement keyword (`prose density acknowledged`, `byte-format prescription density accepted`, `procedural verification depth required`, `regex specification accepted`). A row binding the chunk's *content* without acknowledging the prose density does NOT carry forward (the row must explicitly cover the *prescriptive depth*, not just the prescription's subject).

### Carry-forward consultation

Run only on threshold breach. Single source — the parent feature's `decisions.md` — read in Source ingest. A row carries forward when ALL of:

- Decision column substring-matches the chunk slug OR the engineering-plan chunk-index row's verbatim description.
- `Status:` column is `bound` (case-insensitive) — only an Active-section `bound` row counts; a `superseded`/`obsolete` row does not carry forward (per `~/.claude/skills/_review-common/principles.md` § What counts as a bound entry).
- Resolution column contains a density-family keyword (the four enumerated above; the keyword list is intentionally narrow because a row binding the chunk's content does not, by itself, arbitrate density — the row must explicitly cover prescriptive depth).

On match: set `prose_density.verdict: "carried_forward"`, populate `carry_forward_source` with the row's Decision + Resolution column text verbatim, proceed to verdict emission. On no-match: refuse with `PROSE_DENSITY_EXCESS`.

The carve-out is narrow on purpose. Some chunks legitimately carry dense prescriptive prose (a regex specification, a multi-step procedural acceptance criterion, a byte-equality protocol). Those chunks need decisions.md to acknowledge the density as load-bearing, not merely the prescription's content as bound.

### Why post-Self-prosecution, not pre-Self-prosecution

Self-prosecution is one (common) accretion engine — persona findings drive fix application, and fix application without restructuring is one failure mode this gate catches. A pre-Self-prosecution gate would measure a draft that hasn't yet accreted defensive prose from this invocation's fix application; running after Self-prosecution gives the gate one shot at the artifact in its final on-disk form. The other accretion paths (prior bloat left in place by the session agent's direct edits or a clean-slate re-author, first-Draft defensive density, user hand-edits) are caught by the same final-form measurement.

The gate skips only in `--draft` mode where Self-prosecution itself is skipped — there is no post-Self-prosecution measurement point. In every other mode (ship, warm), the gate runs and the on-disk metrics are the verdict, regardless of how many fixes Self-prosecution applied this invocation (zero, fifty, or anything in between).

### Pending-blockers section (NEEDS_USER_INPUT mode)

On NEEDS_USER_INPUT, the on-disk chunk plan gets two additions beyond the partial draft body:

1. **Frontmatter `Status: needs-user-input`** is added (or replaces a prior Status value if any). The APPROVED-emission convention is no `Status:` field; the NEEDS_USER_INPUT path adds the field as the only valid Status value.
2. **`## Pending blockers` section appended at the end of the file**, with verbatim bullets from the verdict's `### Blockers` block:

   ```markdown
   ## Pending blockers

   <!-- This section is auto-managed by /plan-author. Resolve each blocker below; the session agent then applies your resolutions directly to this file and removes this section along with the `Status: needs-user-input` line — the author skill is not re-run. -->

   - [<BLOCKER_CLASS>] <span / section> — <one-line summary>; <actionable resolution path>.
   - ...
   ```

Once the session agent has applied every resolution, it removes the entire `## Pending blockers` section AND its HTML comment, AND the `Status: needs-user-input` line (a resolved plan carries no `Status:` field). While any blocker remains unresolved, the `## Pending blockers` section keeps only the still-open blockers (resolved ones drop out as they land — stale blockers don't accumulate) and the `Status: needs-user-input` line stays.

---

## Hard rules

- **Stage order is fixed.** State load → Plan-worktree provisioning → Source ingest → Concern gate → Draft → Brief-conformance gate → Plan-lint gate → Ground-truth audit → Self-prosecution → Prose-Density gate → Verdict emission. `--draft` skips Plan-lint, Ground-truth audit, Self-prosecution, and Prose-Density gate (the last because it runs *after* Self-prosecution, which is skipped — there is no post-Self-prosecution measurement point in --draft mode); the Concern gate and Brief-conformance gate still run. `--draft` does NOT skip Plan-worktree provisioning — a draft plan is still written to the `<SLUG>-plan` branch, not the primary checkout.
- **Plan-worktree provisioning is mandatory when your project provides a worktree bootstrap script** (unless a no-op condition holds). Runs after State load, before Source ingest: a plain `git worktree add` off `origin/main` (per-plan `.worktrees/<SLUG>-plan` on branch `<SLUG>-plan`, where `SLUG` is the chunk's prefix-free slug; `fixes/<name>.md` → `.worktrees/<name>-plan` on `<name>-plan`) — not the project's worktree bootstrap script, so no dev-stack services/deps/seed data. The `-plan` suffix pairs the authoring branch with `/execute-plan`'s `<SLUG>` implementation branch without colliding. Both the authority-stack reads AND the plan write re-anchor there. No-op (author in place, reason recorded in the sidecar) only when: `--no-worktree`, a `.scratch/` plan (gitignored — no branchable home), already inside a linked worktree (`--git-dir` ≠ `--git-common-dir`), or the project has no worktree bootstrap script. `/plan-author` never commits, pushes, or opens a PR from the worktree — it only writes the plan file; the user runs `/plan-review-v2` there next, then commits + `/open-pr`.
- **Engineering plan must be CLOSED.** If the engineering-plan-author sidecar's verdict is APPROVED (decisions still undecided) or NEEDS_USER_INPUT, the chunk plan author refuses to run. The session agent binds the cross-chunk decisions in `decisions.md` and marks the engineering plan CLOSED first — the engineering-plan author is not re-invoked.
- **Concern gate is HARD-blocking unless carry-forward applies.** Triggered only by self-disclosed bundling (the description literally containing `\bN-concern\b`, `\bbundle\b`, or `\bbundling\b`). A draft for a self-admitted multi-concern chunk does not reach Draft when no upstream arbitration is recorded in the engineering-plan reviewer state, the engineering-plan-author state, or the engineering plan's `## Decisions closure` section. Other concern judgments (genuine bundling that the description doesn't self-disclose) are handled semantically by the ai-development persona's halved-work test in Self-prosecution, NOT by this gate.
- **Plan-Lint is HARD-blocking.** Same as engineering-plan-author.
- **No length or files-touched gate.** A chunk plan that runs 500+ lines because its single concern's footprint is broad (e.g., a refactor that extracts one helper used in 12 sites; a callsite migration after a rename) is not refused on size. The earlier Byte-budget gate (500 lines / 40k tokens) was dropped because length is downstream of footprint breadth, not an independent measure of factoring quality. Bloat-from-overscoping (premature abstraction, dead scaffolding, restating the brief) is caught by the "Abstraction earns its place", "No scaffolding", and Self-prosecution gates, which target the actual failure mode.
- **Prose-Density gate is the per-bullet floor — distinct from length.** A 600-line plan with 100 well-factored 80-byte bullets passes. A 200-line plan with 30 bullets averaging 370 bytes/line fails. The gate's three sub-metrics — `bytes_per_line_avg`, `bullet_word_count_max`, `parenthetical_nesting_depth_max` — target per-bullet structural quality, not document length. The gate runs unconditionally after Self-prosecution (skipped only in `--draft` because Self-prosecution is skipped). The on-disk artifact is the measurement target regardless of how the bloat arrived — fix accretion this run, prior bloat left in place by the session agent's direct edits or a clean-slate re-author, first-Draft defensive density, or hand-edits.
- **Disk-write semantics by verdict:** APPROVED writes the chunk plan with NO `Status:` frontmatter (the binary-Status convention reserves `Status:` for the mid-cycle signal only); NEEDS_USER_INPUT writes the partially-improved in-memory draft with frontmatter `Status: needs-user-input` AND an inline `## Pending blockers` section listing each unresolved finding verbatim from the verdict (the user fixes the blockers and the session agent applies the resolutions directly, then clears the `Status:` line — the author is not re-invoked); DRAFT_EMITTED writes with NO `Status:` frontmatter; the sidecar's `authoring_mode: "draft"` is the load-bearing draft signal that downstream skills consult. Authoring without `--draft` runs Plan-lint, Ground-truth audit, and Self-prosecution to produce a hardened plan; the author is not re-run to harden an existing `--draft` artifact. Sidecar persists in all cases. The reviewer skill `/plan-review-v2` refuses to run against `Status: needs-user-input` artifacts — the partial draft is mid-cycle by design and not yet a candidate for prosecution. **After an APPROVED first draft, the next step is to run `/plan-review-v2`.** `/execute-plan` consults the sidecar's `authoring_mode` and refuses on draft (implementing a draft plan ships hallucinations).
- **Creation-index filename prefix.** New chunk plans are written to `<plan-root>/implementation/<NN>-<chunk-slug>.md` with a per-plan-root, authoring-order `<NN>-` prefix that is assigned once and stays stable across re-authoring (see Creation index). Only the filename carries the number; the slug — H1, `**Slug:**` line, sidecar key, chunk-index row, `decisions.md` citations, PR branch — stays prefix-free. Re-authoring writes back to a plan's existing filename and never renames it; a pre-convention bare plan keeps its bare name until a separate wholesale backfill migrates it. Scratch plans are not indexed.
- **Sidecar always written.** Every invocation, every verdict.
- **Carry-forward respect.** Re-introducing a defect class the user closed in a prior invocation is `FIX_INTRODUCED_PREMISE_INVERSION`.
- **No banned content.** Same prohibited categories as `/brief-author` and `/engineering-plan-author`.
- **Banned single-file grep at write time.** Per `~/.claude/CLAUDE.md` global rules and the agent template's tool-selection note, single-file grep is the wrong tool — use Read for symbols inside a known file.
- **Proactive convention extraction (≥3-same-shape rule) is mandatory at Draft.** Before emitting the in-memory draft to Plan-lint, scan §Tests, §Owns, and §Acceptance criteria for ≥3 bullets sharing a structural pattern (test-setup invariant, trap-row idiom, byte-exact diagnostic format, cleanup ordering). Each detected ≥3-same-shape group must be extracted into a §Conventions entry before the draft proceeds. The Self-prosecution ai-development persona will catch a Draft that skipped this step; the rule exists so the gap is closed at write time, not at the next review round. The verdict template's `Ground-truth audit` block must record `convention_extractions: <count>` (with the patterns enumerated) so a "0 extractions on a 30-bullet test list" attestation is visible as a red flag.
- **Drafted prose must not contradict bound `decisions.md` entries — class-aware.** Before emitting the in-memory draft to Plan-lint, scan every section for prose that contradicts an entry in `features/<feature>/decisions.md` whose `Status:` is `bound` (only Active-section `bound` entries — a `superseded`/`obsolete` entry in the `## Archived` tail no longer forces a rewrite; per `~/.claude/skills/_review-common/principles.md` § What counts as a bound entry). Per `_review-common/principles.md` § Cross-artifact authority order, the rule is class-aware. **Class B contradictions** (bound wiring decision contradicts the chunk plan on identifier / file path / schema column / module ownership): HARD-blocking unless surfaced as `OPEN_QUESTION` (the bound decision may itself be wrong given new repo state, but that is a re-arbitration, not a silent override). **Class A contradictions** (the chunk plan's §Owns / §Acceptance / §Tests asserts something a parent-feature brief Non-goal forbids, even if a bound decision separately committed to it): the **brief wins** — refuse to emit and surface as `BRIEF_NONGOAL_TRESPASS`. The bound decision is itself the defect. The verdict template's `Ground-truth audit` block records `bound_decisions_consulted: <count>; class_B_contradictions_found: <count>; class_A_contradictions_found: <count>` so missing this step is visible. The Brief-conformance gate is the proactive write-side pair for Class A; the Self-prosecution carry-forward Priority 1 auto-retract handles persona findings reactively.

---

## Edge cases

**Engineering-plan sidecar absent (cold development):** Run with degraded checks; emit `WARNING: engineering plan not yet CLOSED — chunk plan may need rework after engineering-plan finalization`. Verdict mentions it. The chunk plan can still be useful in early exploration.

**Chunk slug not in engineering-plan chunk index:** Refuse to run; the chunk hasn't been declared. Suggest `/engineering-plan-author <feature>` to add the chunk row.

**Chunk slug exists but description is multi-concern:** Concern gate fails; surface `CONCERN_GATE_FAILED` blocker with the engineering-plan amendment recommendation.

**Plan-lint fails after 2 fix attempts:** Surface `STRUCTURAL_LINT_FAILED` blocker. Common cause: vague acceptance criteria or position-encoded slugs introduced by the LLM during drafting; the session agent fixes them directly in the plan — the author is not re-invoked.

**Sibling test patterns referenced (e.g., `vi.spyOn` from `recordSync.test.ts`):** Verify each by Read of the cited sibling file at the cited section. If the pattern actually appears, anchor the citation symbolically (`recordSync.test.ts:<test-name>`); if not, surface `INVENTED_TEST_PATTERN` finding (testing persona's class).

**Real-DB test cleanup pattern needed:** If the chunk's tests write to the real test DB AND no sibling test in the same `__tests__/` directory has a real-DB cleanup template, the chunk plan must define the template in §Conventions (BASE constants, sequence-restore, OR-predicate cleanup). Author-side: surface this as an `OPEN_QUESTION` if the user hasn't bound conventions; per the stale-record-cleanup case, the user resolved this in Round 5 Batch A.

**Repository state drift mid-authoring (rare):** If the SHA of files in the chunk's read-set changes between Source-ingest read and Ground-truth-audit verification, treat as `REPO_STATE_DRIFT` and require re-invocation. The deterministic detection: capture each read file's SHA at Source ingest; re-check at Ground-truth audit entry.

**`--draft` mode:** Plan-lint, Ground-truth audit, and Self-prosecution are skipped. The Concern gate STILL runs — self-disclosed multi-concern bundling is a fatal scope error that doesn't get to defer behind `--draft`. Sidecar records `authoring_mode: "draft"`, `verdict: "DRAFT_EMITTED"`, `concern_gate_status: "passed" | "carried_forward"` (refusal still aborts in this mode). Chunk plan IS written to disk with NO `Status:` frontmatter. The sidecar's `authoring_mode: "draft"` field is the load-bearing draft signal: `/plan-review-v2` consults it and warns in its verdict (does NOT refuse — `--draft` is a user-opt-in to the unhardened state, distinct from `Status: needs-user-input` where the reviewer hard-refuses); `/execute-plan` consults it and REFUSES (implementing a draft plan ships hallucinations). Authoring without `--draft` produces a hardened plan; the author is not re-run to harden an existing `--draft` artifact.

**`.scratch/<name>.md` plan (not under `features/<feature>/implementation/`):** Slug derives to `scratch__<name>`. **Plan-worktree provisioning is a no-op — `.scratch/` is gitignored, so it has no branchable git home; author in place** (sidecar `plan_worktree.action: "in-place"`, `in_place_reason: "scratch-plan"`). The brief/engineering-plan reads in Source ingest are skipped (no upstream); the Concern gate still applies (regex against the chunk's H1 / Goal sentence — no chunk-index row to consult, and carry-forward sources are unavailable); Plan-lint, Ground-truth audit, and Self-prosecution run normally. Self-prosecution drops the `product` persona (no brief to map to).

**`fixes/<name>.md` plan (git-tracked one-off bug fix):** Same brief-less handling as a `.scratch/` plan above (slug `fixes__<name>`; Source-ingest brief/EP reads and the Brief-conformance gate skipped; `product` persona dropped) — EXCEPT the artifact is git-tracked, so **it DOES get a plan worktree**: `.worktrees/<name>-plan` on branch `<name>-plan`. Use `fixes/` for durable one-off fix/issue plans that should live in history; use `.scratch/` for throwaway exploration.

**Plan worktree already exists for this chunk (reuse — a re-author):** `.worktrees/<SLUG>-plan` is on branch `<SLUG>-plan` → adopt it, read the authority stack and write the plan there, skip creation. This is how a re-author of the same chunk plan lands back on its own branch.

**`.worktrees/<SLUG>-plan` exists but is NOT on branch `<SLUG>-plan`:** REFUSE `PLAN_WORKTREE_COLLISION` — something else owns the path. The user clears it (`/cleanup-worktree <SLUG>-plan`) or passes `--no-worktree` to author in place.

**`<SLUG>-plan` branch exists but is checked out elsewhere (live in another worktree/session):** REFUSE `PLAN_BRANCH_EXISTS`. A branch checked out in a live worktree cannot be checked out again; the user reuses that worktree, cleans it up, or passes `--no-worktree`.

**Fresh plan worktree lacks the authority stack (brief/EP unmerged):** Cold-create fallback — read `brief.md`/`engineering-plan.md`/`decisions.md` from the invocation checkout by absolute path, write the plan into the worktree anyway, and SOFT-note in the verdict that those artifacts should land on `main` (or ride along in this plan's PR) so the plan is reviewable against its real upstream. Record `plan_worktree.authority_stack_from: "invocation-checkout (cold-create fallback)"`.

**Already inside a linked worktree, or `--no-worktree`, or no worktree bootstrap script:** Plan-worktree provisioning is a no-op; author in place with the reason recorded in `plan_worktree.in_place_reason`.

---

## Relationship to sister skills

- **Upstream: `/engineering-plan-author`.** Must be at CLOSED for chunk authoring to proceed (see Hard rules).
- **Reviewer: `/plan-review-v2`.** The immediate next step after this author's first draft. When your project provides a worktree bootstrap script, run it from **inside the plan worktree** — that is where the plan lands (the `<SLUG>-plan` branch), and where its authority stack resolves (from `main`, or the invocation checkout under the cold-create fallback). Its `recently_resolved_blockers` are warm-mode constraints. Author-side findings share blocker classes. The author's sidecar's `introduced_identifiers` and `ground_truth_log` let `/plan-review-v2` skip re-prosecuting verified claims (the sidecar is at the global `~/.claude/cache` path, so it is shared across worktrees).
- **Indirect upstream: `/brief-author`.** Brief edits cascade through `/engineering-plan-author` re-authoring; chunk plans inherit the latest brief Goals via the engineering plan's Brief Mapping table.

The chunk-plan layer is where thrash concentrates and where this skill earns its keep. The stale-record-cleanup case (Round 5: 28 findings, 5 user decisions, 13 batches, 563-line plan) is exactly what the concern gate + ground-truth + self-prosecution stack is designed to prevent at write time, not five rounds later at review time.
