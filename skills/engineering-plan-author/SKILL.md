---
name: engineering-plan-author
description: Writes or rewrites a feature's `engineering-plan.md` — the chunk DAG between the brief and per-chunk plans — applying structural lint, brief-conformance, goal-verification, ground-truth verification, and self-prosecution at write time rather than review time. Run once per cycle, then `/engineering-plan-review-v2`. Sister to `/brief-author` and `/plan-author`.
user-invocable: true
---

# Engineering plan author

Produces or rewrites a feature's `engineering-plan.md`. Pre-empts the failure modes `/engineering-plan-review-v2` keeps surfacing — chunk overscoping, brief drift, decision-closure gaps, false parallelism, position-encoded slugs.

**Closed-plan guard.** If the resolved `engineering-plan.md` carries the `/ep-close` closure marker (`Status: closed` frontmatter), refuse: a closed plan is implementation complete and accepts no re-authoring or new chunks — new scope routes to an open sibling track, a new track, or a new feature (`~/.claude/skills/_plan-common/layout.md` § Closed engineering plans). Reopening is a director-only act.

**Plan-root resolution.** Read `~/.claude/skills/_plan-common/layout.md` before resolving the argument. A feature is either **flat** (one `engineering-plan.md` at `features/<feature>/`) or **tracked** (one per track at `features/<feature>/plans/<track>/`). Throughout this skill, **`<plan-root>`** is the directory holding the resolved `engineering-plan.md`; `brief.md` and `decisions.md` always live at the feature root `features/<feature>/`, shared by every track.

The engineering plan is the contract between the brief (what we're shipping) and the chunk plans (how each piece is built). Every defect at this layer multiplies: a 4-concern chunk row produces a 4-concern chunk plan; a missing decision-closure entry means every chunk plan re-prosecutes the same cross-chunk wiring; a brief Goal not mapped to a chunk means the feature ships incomplete.

## Inputs

- `$ARGUMENTS` (optional):
  - `<feature>` — the feature directory under `features/`. Required if not inferable from cwd. A tracked feature resolved without a track stops and asks which track (or whether a new one is intended); it does not pick one.
  - `<feature>/<track>` — one specific plan of a tracked feature. Authoring a track that does not exist yet creates `features/<feature>/plans/<track>/` — but adding a track to a flat feature is a director-level call, so confirm in plain language before migrating an existing flat plan into `plans/`.
  - `--draft` — quick-exploration mode; skip Plan-lint, Concern-lint, Ground-truth audit, and Self-prosecution.
  - `--no-worktree` — (when your project provides a worktree bootstrap script) skip **Engineering-plan-worktree provisioning** and author in the current checkout. Use when you deliberately want the plan written in place — e.g. you are already set up in the tree you want it to land in, or you are consciously not using a per-plan branch.

**The author runs once per cycle.** It produces the first draft; the next step in the cycle is to run `/engineering-plan-review-v2`, and the session agent then applies its findings — plus your blocker resolutions — directly to `engineering-plan.md`. The author is not re-invoked to apply changes. There is no `--rewrite` flag. When `<plan-root>/engineering-plan.md` already exists or its author sidecar is present, invoke `/engineering-plan-author <feature>` again only for an explicit clean-slate re-author (ask in plain language); that fresh run treats the existing plan and any prior review state as carry-forward constraints — a chunk the user removed or a decision the user closed is not re-introduced.

## Sidecar location

`~/.claude/cache/author-state/<slug>.json`, where `<slug>` is `<feature>__engineering-plan` under the flat layout and `<feature>__<track>__engineering-plan` under the tracked one, per `~/.claude/skills/_plan-common/layout.md` § State-slug derivation. The reviewer writes its own state under the **same** slug in `~/.claude/cache/review-state/`, so author and reviewer address one plan by one name.

The reviewer skill `/engineering-plan-review-v2` consults this sidecar to skip re-prosecuting claims the author already verified, and to read `introduced_identifiers` (cross-chunk contracts the engineering plan introduces — type names, table names, flag names, enum values, file paths of shared modules; chunk-internal identifiers do NOT belong in the engineering plan per `P-EP-IMPL-DETAIL`).

---

## Workflow

```
State load (deterministic; ~5 seconds)
  ├─ mkdir -p ~/.claude/cache/author-state (Write does NOT auto-create parents;
  │   the reviewer-side machinery only creates ~/.claude/cache/review-state)
  ├─ Read author sidecar at ~/.claude/cache/author-state/<slug>.json
  ├─ Read review state at ~/.claude/cache/review-state/<slug>.json (warm carry-forward;
  │   fall back to legacy bare <feature>.json — see Round-memory note)
  ├─ Read brief author sidecar at ~/.claude/cache/author-state/<feature>__brief.json (upstream context)
  └─ Determine cold vs warm mode

Engineering-plan-worktree provisioning (when a bootstrap script exists; deterministic; plain `git worktree add` off origin/main — the script itself is NOT used)
  ├─ No-op (author in place) when: --no-worktree, already inside a linked worktree, or no worktree bootstrap script
  ├─ WT_NAME = BRANCH = <feature>-ep (flat) or <feature>-<track>-ep (tracked); reuse .worktrees/<WT_NAME> on branch <WT_NAME> if present; else create off origin/main
  │   (git fetch origin main; git branch <WT_NAME> origin/main; git worktree add .worktrees/<WT_NAME> <WT_NAME>)
  ├─ Re-anchor cwd to the worktree — every repo read below (brief.md, decisions.md, existing engineering-plan.md, CLAUDE.md, schema.prisma, operations.graphql, sibling plans)
  └─ Cold-create fallback: a brief.md / decisions.md not yet on origin/main is read from the
      invocation checkout by absolute path; the new engineering-plan.md still lands in the worktree

Source ingest (deterministic; ~60 seconds — runs inside the plan worktree when provisioned)
  ├─ Read brief.md (HARD-blocking — engineering plan without brief is fan fiction)
  ├─ Resolve the parent spec from the brief's `**Spec:**` header by file presence
  │   (no header → every spec-layer step below is a no-op; a header whose path
  │    resolves to nothing → same skips, plus OPEN_QUESTION for the dangling header)
  ├─ Read the parent spec's `## Decomposition` — this brief's scope stub, the Seams, the Coverage table
  ├─ Read the parent spec's decisions logs (per-spec + `specs/decisions.md`, nearest first) — `## Active (bound)` entries only
  ├─ Resolve the brief's inherited exclusions into the spec sections they reference (targeted reads)
  ├─ Read decisions.md (every dated entry, especially cross-chunk wiring)
  ├─ Read existing engineering-plan.md (warm mode — when the file or sidecar already exists)
  ├─ Read CLAUDE.md, MEMORY.md, project memory files, schema.prisma, operations.graphql
  ├─ Read sibling engineering plans (features/*/engineering-plan.md and
  │   features/*/plans/*/engineering-plan.md) for shape/tone consistency
  └─ Build invariants ledger and identifier ledger

Draft (LLM judgment; main thread)
  ├─ Mirror section template: Brief mapping → Architecture summary → Decisions closure
  │     → Invariants → Threat model → Field Precedence → Cost & Capacity
  │     → Operator-facing budgets → Chunk index → Manual gates → Dependency graph
  ├─ Each chunk row in the chunk index = ONE concern (refuse 'N-concern' / 'bundle' framings)
  ├─ Each chunk row carries an Intent (Foundation | Behavior | Hardening | Migration)
  ├─ Invariants and Threat model are populated OR carry their explicit disclaimer
  ├─ Every Goal in the brief maps to ≥1 chunk in Brief Mapping (or to Supporting infrastructure)
  ├─ Decisions-closure table covers every cross-chunk wiring decision
  └─ Emit first draft to in-memory buffer (NOT yet written to disk)

Brief-conformance gate (mandatory, HARD-blocking; runs BEFORE Plan-lint)
  ├─ Materialize in-memory draft to ~/.claude/cache/author-state/<slug>-DRAFT.md
  ├─ Spawn parallel batch: 1 Brief-conformance Prosecutor + 1 Scope-fidelity Adversary per
  │   at-risk Goal (isolated, one Goal each; see _review-common/brief-conformance-prosecutor.md)
  ├─ Merge all findings; HIGH HARD finding → hard refusal; partial-draft written with `Status: needs-user-input`
  │   and `BRIEF_NONGOAL_TRESPASS` / `BRIEF_GOAL_UNDELIVERED` / `SURFACE_PARITY_GAP` in `## Pending blockers`
  ├─ MEDIUM HARD findings → partial-draft written; user adjudicates
  └─ all roles `brief_conformance_check: passed` → proceed to Goal-verification gate

Goal-verification gate (mandatory, HARD-blocking; runs in the author thread against the in-memory draft + brief)
  ├─ Confirm a dedicated acceptance chunk exists: exactly one chunk-index row is a DAG sink
  │   (no chunk lists it as a dep) whose Code-deps cover every delivering chunk and whose
  │   concern is the contract-level acceptance suite. Absent → GOAL_VERIFICATION_GAP.
  ├─ For each brief Goal: Brief mapping → Goals has a non-empty `Verified by` naming the
  │   acceptance chunk, OR `Manual review — <reason>` where the outcome is genuinely not
  │   observably automatable. A blank cell, or `Manual review` on an automatable outcome →
  │   GOAL_VERIFICATION_GAP.
  ├─ For each brief scope exclusion: Brief mapping → Scope enforcement classifies it
  │   `testable-absence` (→ an assert-absence test owned by the acceptance chunk),
  │   `scope-boundary` (→ `not test-assertable — <reason>`), or `deferred-tracked`
  │   (→ the brief's `Intentionally deferred` destination, repeated). An observably-
  │   assertable exclusion marked `scope-boundary`, a `testable-absence` row with no
  │   owning test, or a `deferred-tracked` row naming no destination →
  │   GOAL_VERIFICATION_GAP.
  ├─ GOAL_VERIFICATION_GAP is Class A (brief Goal/Non-goal honoring). HIGH HARD on a missing
  │   acceptance chunk or an unproven Goal; MEDIUM HARD on a mis-classified / unproven Non-goal.
  └─ All checks pass → proceed to Plan-lint. Any HIGH HARD → partial-draft with `Status: needs-user-input`
      and the gap(s) in `## Pending blockers`.

Plan-lint gate (deterministic, HARD-blocking)
  ├─ Write the in-memory draft to /tmp/<slug>-draft-<timestamp>.md
  ├─ Bash: `python3 ~/.claude/skills/plan-lint/lint.py /tmp/<slug>-draft-<timestamp>.md`
  │   (the Skill tool form `Skill(skill="plan-lint", args=...)` is also valid;
  │   the python script is the canonical underlying invocation, faster and
  │   easier to capture in the sidecar's plan_lint_log)
  ├─ Capture stdout + exit code into sidecar.plan_lint_log
  ├─ Exit 0: continue to Concern-lint gate
  ├─ Exit 1: apply local fixes (re-draft prose, do not change DAG); re-run lint up to 2x.
  │   If still failing after 2 retries, surface STRUCTURAL_LINT_FAILED blocker.
  ├─ Exit 2: usage/IO error — re-check temp-file path; re-emit
  └─ Delete the temp file regardless of outcome

Concern-lint gate (deterministic, HARD-blocking unless carry-forward applies)
  ├─ For each row in the in-memory draft's chunk index, apply ONE structural check
  │   against the description (mirrors the chunk-plan author's Concern gate):
  │     - Self-disclosure pattern: /\b\d+-concern\b|\bN-concern\b|\bbundle\b|\bbundling\b/i
  ├─ For each row that matches, consult carry-forward (see "Concern-lint carry-forward
  │   consultation" below) BEFORE refusing. If carry-forward applies, tag the row's
  │   lint outcome `carried_forward` and proceed.
  ├─ Rows that match AND have no applicable carry-forward → HARD-blocking. Catching
  │   self-disclosed bundling at the engineering-plan layer prevents the cascade into
  │   a multi-concern chunk plan that plan-author's own Concern gate would refuse anyway.
  ├─ On unsalvageable failure: surface CONCERN_GATE_FAILED with the offending row(s);
  │   decompose the chunk into one-concern siblings, OR (when the bundle is intentional
  │   and decided) record an explicit bundle arbitration in `## Decisions closure`
  │   citing the durable decision so future invocations carry forward deterministically.
  ├─ Other syntactic patterns (` AND ` conjunctions, comma lists, plus-separators,
  │   multi-clause descriptions) are NOT refusal triggers at this gate — they fire
  │   false-positives on legitimate prose. Concern judgment for these cases is
  │   semantic, performed by the ai-development persona's halved-work test in
  │   Self-prosecution against each chunk row.
  └─ On clean pass (no self-disclosure matches, or all matches resolved by
      carry-forward): proceed to Ground-truth audit.

Ground-truth audit (`_author-common/ground-truth-protocol.md`)
  ├─ Tokenize draft for V1-V5 claims
  ├─ V2 (identifiers): cross-chunk contract names — verify each is either (a) introduced by THIS plan
  │   (added to introduced_identifiers) or (b) verified to exist in the repo
  ├─ V4 (cross-document): every brief-Goal quote, every decisions.md citation, every CLAUDE.md rule
  ├─ V3 (constraint): chunk dependencies (claim "X depends on Y" verified against the dependency graph)
  └─ Write sidecar audit log

Self-prosecution and imagined-implementer (`_author-common/self-prosecution-protocol.md`)
  ├─ Spawn architecture, ai-development, product, backend, testing in parallel
  ├─ Each runs the premise-interrogation sub-pass + the standard-prosecution sub-pass
  ├─ THEN run Imagined-Implementer dry-run (author-side; engineering-plan layer only):
  │     - Pick the first chunk in the dependency graph that has no upstream dependency
  │     - Attempt to author its chunk plan in a single thought-experiment pass (not actually written)
  │     - Surface every cross-chunk wiring decision the imagined-implementer cannot bind
  │     - File these as IMPLEMENTABILITY_GAP — same blocker class the reviewer uses
  ├─ Run the no-annexation check at chunk grain against the parent spec's Coverage table
  ├─ Consolidate findings; apply auto-fixable
  ├─ Run post-fix premise verification on orchestrator-rewritten prose
  ├─ Classify residuals (STABLE_DISAGREEMENT, OPEN_QUESTION, FIX_INTRODUCED_PREMISE_INVERSION,
  │   IMPLEMENTABILITY_GAP, BRIEF_AMENDMENT_NEEDED, SPEC_AMENDMENT_NEEDED, UNCORROBORATED_RESET)
  └─ Decide emission via three-state verdict:
      ├─ CLOSED: write engineering plan with NO `Status:` frontmatter + persist + verdict (per-chunk authoring is unblocked)
      ├─ APPROVED: write engineering plan with NO `Status:` frontmatter + persist + verdict (shape-correct, but cross-chunk
      │           decisions still undecided — do NOT yet author per-chunk plans; IMPLEMENTABILITY_GAPs in the body)
      └─ NEEDS_USER_INPUT: write partial draft with `Status: needs-user-input` and inline `## Pending blockers`
                          + persist + render verdict
```

In `--draft` mode the Plan-lint, Concern-lint, Ground-truth, and Self-prosecution stages are all skipped; the draft is emitted directly with `verdict: "DRAFT_EMITTED"` per the rule under Edge cases.

---

## State load

Read the author sidecar. Schema (extends the brief-author sidecar with engineering-plan-specific fields):

```json
{
  "feature": "<feature>",
  "artifact_path": "<plan-root>/engineering-plan.md",
  "parent_spec": "specs/<slug>/spec.md | spec.md | null (the brief carries no `**Spec:**` header) | named but missing — <path> (the header names a file that is not on disk)",
  "decomposition_stub": "ingested | absent",
  "engineering_plan_worktree": {
    "provisioned": <bool>,
    "path": "<.worktrees/<WT_NAME> or null when in-place>",
    "branch": "<WT_NAME or null when in-place>",
    "in_place_reason": "--no-worktree | already-in-linked-worktree | no-bootstrap-script | null",
    "upstream_from": "worktree | invocation-checkout (cold-create fallback)"
  },
  "authoring_mode": "ship | draft",
  "ground_truth_at": "<ISO 8601 UTC>",
  "self_prosecution_at": "<ISO 8601 UTC>",
  "imagined_implementer_at": "<ISO 8601 UTC>",
  "invocation_number": <int>,
  "last_engineering_plan_sha256": "<hex>",
  "claims_total": <int>,
  "claims_verified": <int>,
  "claims_verified_softened": <int>,
  "claims_corrected": <int>,
  "claims_dropped": <int>,
  "claims_restructured": <int>,
  "claims_skipped_carveout": <int>,
  "introduced_identifiers": ["<cross-chunk contract name>", ...],
  "chunk_count": <int>,
  "chunk_dag": [{"slug": "...", "depends_on": [...]}, ...],
  "ground_truth_log": [...],
  "self_prosecution_findings": [...],
  "imagined_implementer_findings": [...],
  "no_annexation": "not_applicable | clean | <N> claims",
  "exclusion_challenges": [...],
  "conformance_gate_model": "<model pinned for the Brief-conformance gate, or null if it did not run>",
  "ground_truth_model": "<haiku unless inline>",
  "persona_model": "<sonnet per the pin>",
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
  "plan_lint_log": "<verbatim stdout from python3 ~/.claude/skills/plan-lint/lint.py>",
  "concern_lint_status": "passed | failed | carried_forward",
  "concern_lint_offending_rows": ["<chunk-index row description>", ...],
  "concern_lint_carry_forward_log": [
    {
      "row_description": "<verbatim chunk-index row description>",
      "matched_pattern": "self_disclosure",
      "source": "review_state | author_state | decisions_closure",
      "source_path": "<verbatim path or `## Decisions closure` row>",
      "source_blocker_id": "<id or null when source is decisions_closure>",
      "carry_forward_until_round": <int>,
      "user_decision": "<verbatim>"
    }
  ],
  "verdict": "CLOSED | APPROVED | NEEDS_USER_INPUT | DRAFT_EMITTED"
}
```

`prior_blockers` / `recently_resolved_blockers` mirror the reviewer state schema in `~/.claude/cache/review-state/` so `/explain-blockers` parses both with one parser. Verdict semantics differ from brief-author / plan-author: `APPROVED` means shape-correct AND one or more `IMPLEMENTABILITY_GAP` entries remain in `prior_blockers`; `CLOSED` means `prior_blockers` is empty AND every cross-chunk decision is bound. `DRAFT_EMITTED` is set when authoring_mode is `--draft` (Plan-lint, Concern-lint, Ground-truth audit, and Self-prosecution skipped); the engineering plan IS written to disk in this mode with NO `Status:` frontmatter, and the sidecar's `authoring_mode: "draft"` carries the load-bearing draft signal that downstream skills consult. `NEEDS_USER_INPUT` is set when one or more HIGH+ blockers remain (other than IMPLEMENTABILITY_GAP, which lands at APPROVED); the partially-improved engineering plan IS written to disk with frontmatter `Status: needs-user-input` AND an inline `## Pending blockers` section listing each unresolved finding verbatim — the session agent then applies the user's blocker resolutions directly to the plan and clears the `Status:` line once they land, and the author is not re-invoked. Only HIGH+ findings land in `prior_blockers`; LOW findings under the polish floor stay in `authoring_residual`.

`decomposition_stub: "absent"` is the one name for the no-decomposition degradation, and `/engineering-plan-review-v2` records the same condition as `Decomposition trace: N/A — no decomposition resolved`. One condition, one vocabulary per side. `parent_spec` carries three resolution states, not two: a path, `null` when the brief names no spec, and `named but missing — <path>` when it names one that is not on disk — the last is a finding, not a silent no-op.

Also read the review-state at `~/.claude/cache/review-state/<slug>.json` (if absent, fall back to the legacy bare `<feature>.json` the reviewer wrote before the slug rule was unified — see `_plan-common/layout.md` § Migration note). Its `recently_resolved_blockers` list constrains the new draft (warm-mode carry-forward at the engineering-plan layer): re-introducing a chunk the user removed, or re-prosecuting a decision the user closed, is `FIX_INTRODUCED_PREMISE_INVERSION`.

Also read the brief-author sidecar `~/.claude/cache/author-state/<feature>__brief.json` if present. Its `introduced_identifiers` list (rare at the brief layer) and `authoring_residual` items inform the engineering-plan draft.

---

## Engineering-plan-worktree provisioning (when your project provides a worktree bootstrap script; runs after State load, before Source ingest)

When your project provides a worktree bootstrap script, the engineering plan is authored inside a **lightweight, per-plan worktree** off `origin/main`, not in the primary checkout — the same convention `/brief-author` applies at the brief layer and `/plan-author` at the chunk layer. Engineering-plan authoring only ever writes markdown (the plan file), so the worktree is a plain `git worktree add` — it does **NOT** use the bootstrap script and provisions **no** dev-services stack, dependencies, or seed data (that heavy path is `/execute-plan`'s, for code that runs tests). This keeps the primary checkout clean and lets parallel authoring sessions run without racing on the shared tree.

The provisioning happens after State load (which only touches the global `~/.claude/cache` sidecars) and before Source ingest, because Source ingest reads repo files (`brief.md`, `decisions.md`, any existing `engineering-plan.md`, `CLAUDE.md`, `schema.prisma`, `operations.graphql`, sibling engineering plans) and must resolve them inside the worktree when they are on `main`, or from the invocation checkout when they are not yet merged (see the cold-create fallback).

### When it runs

Provisioning runs unless ANY of the following holds, in which case this stage is a no-op and authoring proceeds **in place** (record the reason in the sidecar and verdict):

- **`--no-worktree` was passed.**
- **Already inside a linked worktree** — `git rev-parse --git-dir` differs from `git rev-parse --git-common-dir`. The session is already isolated in some `.worktrees/<name>`; write the plan there rather than nesting a worktree in a worktree.
- **No worktree bootstrap script** — no executable bootstrap script exists at the repo root (`git rev-parse --show-toplevel`). This skill is global; the whole stage is a no-op elsewhere.

### Worktree identity

Deterministic, per-plan. Let `MAIN_ROOT` = `git rev-parse --show-toplevel`.

- `WT_NAME` = `BRANCH` = `<feature>-ep` under the flat layout, `<feature>-<track>-ep` under the tracked one (one worktree per engineering plan, so a tracked feature's per-track plans never collide).
- `WT_PATH` = `$MAIN_ROOT/.worktrees/$WT_NAME`.

The `-ep` suffix names the artifact layer: it keeps this worktree distinct from `/brief-author`'s `<feature>-brief` worktree, `/plan-author`'s `<chunk-slug>-plan` worktrees, and `/execute-plan`'s `<chunk-slug>` implementation worktrees, and keeps `/cleanup-worktree`'s `-plan`-specific next-step hint (the ready-to-paste `/execute-plan` command) from firing on an engineering-plan branch.

### Steps

1. **Reuse guard.** If `$WT_PATH` already exists:
   - its checked-out branch is `$BRANCH` (`<WT_NAME>`) → **adopt it**: re-anchor to `$WT_PATH`, skip creation. This is a re-author of the same feature's engineering plan.
   - any other branch → REFUSE `EP_WORKTREE_COLLISION` (something else owns that path; the user resolves it — e.g. `/cleanup-worktree <WT_NAME>`).
2. **Sync + pin the base (fresh create only).** `git -C "$MAIN_ROOT" fetch origin main`. Pin the branch to `origin/main` explicitly rather than forking off the shared checkout's current HEAD (the shared-tree branch-creation race): `git -C "$MAIN_ROOT" branch "$BRANCH" origin/main`. If `$BRANCH` already exists with no worktree (a leftover from an aborted run), reuse it; otherwise the branch is live elsewhere → REFUSE `EP_BRANCH_EXISTS`.
3. **Create the worktree.** `git -C "$MAIN_ROOT" worktree add "$WT_PATH" "$BRANCH"`. Plain and fast — no bootstrap script, no DB/deps.
4. **Re-anchor.** Set the working directory to `$WT_PATH` for Source ingest and every stage below. All repo reads (`brief.md`, `decisions.md`, existing `engineering-plan.md`, `CLAUDE.md`, `schema.prisma`, `operations.graphql`, sibling `features/*/engineering-plan.md` shape references) and the final engineering-plan write resolve inside `$WT_PATH`. The sidecars (`~/.claude/cache/author-state/`, `~/.claude/cache/review-state/`) and project-memory reads keep their absolute paths — they are outside the repo and unaffected.

### Upstream presence (cold-create fallback)

A per-plan worktree is a fresh branch off `origin/main`, so it carries `brief.md` / `decisions.md` only when they are already merged to `main`. At engineering-plan time the brief has frequently **not** merged yet — it is often still on its own `<feature>-brief` PR branch — so this fallback is a common path, not a rare one. When the worktree lacks the brief or decisions, do NOT treat the HARD-blocking source as missing: read `brief.md` / `decisions.md` from the **invocation checkout** by absolute path (so run the skill from a checkout that actually has them — the `<feature>-brief` branch, or an in-place draft), still write the new `engineering-plan.md` into the worktree, and surface a SOFT note in the verdict — the engineering plan should land on `main` via this branch's PR so downstream skills review against the real upstream. Record `engineering_plan_worktree.upstream_from: "invocation-checkout (cold-create fallback)"`. If neither the worktree nor the invocation checkout has `brief.md`, the Source-ingest HARD requirement fires and the skill refuses — an engineering plan without a brief is fan fiction.

---

## Source ingest

Hard requirements — skill refuses to run without:
- `features/<feature>/brief.md` exists (brief is the bridge to the engineering plan).

### Parent-spec resolution

The engineering plan is grounded in its brief and in nothing above it. The spec reaches this layer through exactly one channel: the brief's `**Spec:**` header, resolved by **file presence, never by asking**. The header names a path; that path resolving to a file on disk is what engages every spec-layer step below.

- **Header present and the path resolves** → that file is the parent spec. Read its `## Decomposition` and its decisions logs (step 2 and step 3 below), and record the path as `parent_spec` in the sidecar.
- **No `**Spec:**` header** → no parent spec resolves. Record `parent_spec: null`, skip steps 2–4, and author against the brief alone — every spec-layer step below is a no-op and nothing else in the run changes. Do not go looking for a spec the brief did not claim, and do not ask which one — a brief with no header is a legacy brief, not an ambiguity.
- **Header present but the path resolves to nothing** → record `parent_spec: "named but missing — <path>"`, skip steps 2–4, and file `OPEN_QUESTION` (HIGH) naming the header and the path — the same finding the reviewers file for the same shape. It is a brief claim about a real file and every spec-layer step anchors on it, so it is not the no-header case wearing different clothes: the two states are distinct and the sidecar records which one holds. Do not substitute a spec whose name looks close.
- **Parent spec resolves but carries no `## Decomposition` section** → record `decomposition_stub: "absent"`, skip steps 2 and 4, and the no-annexation check is `not_applicable`. Boundary-binding is gated on the decomposition: a spec that draws no boundaries has none to bind, so step 3's logs are not read for boundary arbitration either. This is the whole of the degradation.

Resolution is a targeted read, not a second grounding pass. The spec constrains the chunk DAG through its decomposition and its bound boundary calls; it never becomes the plan's source of Goals, which stay the brief's.

### Read order

1. `features/<feature>/brief.md` — every Goal and Non-goal goes into the invariants ledger as constraints the chunk DAG must honor.
2. **The parent spec's `## Decomposition`** — this feature's scope stub (the slice the brief was cut from), the **Seams** with their split-line predicates, and the **Coverage** table dispositioning every spec unit to a brief slug or a named seam. The chunk DAG is cut inside that slice: the Coverage table is what the no-annexation check tests chunks against, and a seam's predicate is what places a chunk whose work sits near a boundary.
3. **The parent spec's decisions logs** — `specs/<slug>/decisions.md` beside a per-system spec **and** the shared `specs/decisions.md` alongside it, read **nearest first** (the per-spec log wins where both bind the same call); root `decisions.md` beside a root spec that carries `## Decomposition`. Only `## Active (bound)` entries bind in any of them; a `superseded` / `obsolete` entry in the `## Archived` tail binds nothing. The logs split by subject: a call about which briefs exist or where a boundary sits lives in the spec's log; a call inside one feature's scope lives in the feature's log at step 5. Bound boundary and seam calls are constraints on the chunk DAG, never ground this layer re-litigates. A missing log is not an error — read what is there and carry on. A parent spec carrying no `## Decomposition` draws no boundaries, so nothing beside it is read as a parent-spec log here.
4. **The spec sections the brief's inherited exclusions reference** — one targeted read per exclusion that points at a spec section by name. The brief's scope buckets are derived from the stub's exclusions, which frequently carry the exclusion by reference ("the seam with `<neighbour>`", "§Invariants — `<rule>`"); a chunk cannot be placed against a reference nobody resolved. Read the referenced section, not the spec.
5. `features/<feature>/decisions.md` — every dated entry. Cross-chunk wiring decisions go into the decisions-closure table.
6. `<plan-root>/engineering-plan.md` (when re-authoring) — current chunk DAG, a carry-forward constraint. Under the tracked layout, also read every **sibling track's** engineering plan: chunks this plan does not own may register into seams it does, and a boundary this plan assumes must match what the sibling claims. A sibling carrying the `/ep-close` closure marker is a sealed contract — consume its shipped surface as-is, and never draft a chunk, seam change, or deferral that lands new work in it; scope that would have gone there lands in this plan or a new track (`_plan-common/layout.md` § Closed engineering plans). A mid-cycle `Status: needs-user-input` plan is resolved by the session agent applying blocker resolutions directly, not by re-running this skill.
7. `CLAUDE.md` — banned patterns, business rules, schema-first / operations-first / multi-category architecture rules.
8. `MEMORY.md` + project memory.
9. `backend/prisma/schema.prisma` — current schema; the engineering plan's schema-additions section must declare every new field/table/enum AND verify no naming collisions with existing fields.
10. `mobile/src/graphql/operations.graphql` — current operations; user-facing changes naming GraphQL operations must verify the operation either exists or is an introduced_identifier.
11. Sibling engineering plans (`features/*/engineering-plan.md` and `features/*/plans/*/engineering-plan.md`) — for shape/tone consistency. Pay attention to: section ordering, decisions-closure column shape, chunk-index column shape, dependency-graph rendering style.

After reading, build:
- **Invariants ledger** — every brief Goal, every Non-goal, every project-memory-bound rule. Format as bullet list with verification source.
- **Identifier ledger** — every existing schema field, every existing GraphQL operation, every existing class/type/file path the brief or decisions.md mentions. The chunk DAG cross-references these.
- **Decisions ledger** — every dated entry from `decisions.md`, indexed by (date, key). The decisions-closure table will cite these. The parent spec's Active bound entries enter the ledger too, marked as spec-scope and flagged as constraints: a boundary or seam call there is settled, and the ledger carries it so the Draft stage can be checked against it rather than re-deciding it.

---

## Draft

Mirror this section template (matches the shape of existing engineering plans):

```markdown
# <Feature Name> — Engineering Plan

**Brief:** [`./brief.md`](./brief.md)
<!-- Status frontmatter is OPTIONAL. `needs-user-input` ONLY when the engineering plan is mid-cycle (auto-managed by /engineering-plan-author NEEDS_USER_INPUT path); `closed` ONLY via /ep-close (implementation complete — this skill never writes it and refuses a plan carrying it). Otherwise omit entirely. Other lifecycle states (Frozen, Archived) are derived from git state, not frontmatter. -->
<!-- Status: needs-user-input -->  <!-- only when mid-cycle -->

**Created:** <YYYY-MM-DD>
**Last updated:** <YYYY-MM-DD>

## Brief mapping

### Goals
| Goal | Chunks | Verified by |
|---|---|---|
| <Goal verbatim> | <chunk-slug-1>, <chunk-slug-2>, ... | <acceptance-chunk-slug, or "Manual review — <reason>"> |

### User-facing changes
| Change | Verified by |
|---|---|
| <change> | <chunk-slug or "Manual review"> |

### Supporting infrastructure
- **<chunk-slug>** — <one-line description, ONE CONCERN ONLY>

### Scope enforcement
| Scope item | Bucket | Kind | Enforcement |
|---|---|---|---|
| <item> | Not planned | testable-absence | <acceptance chunk's assert-absence test, one line> |
| <item> | Not in scope (this release) | scope-boundary | not test-assertable — <reason>; <which chunk's plan body bounds it / "no chunk; out of scope by absence"> |
| <item> | Intentionally deferred | deferred-tracked | tracked at <#NNN or feature slug>; not enforced as absent |

## Architecture summary

<Two or three paragraphs describing the system shape. Names cross-chunk contracts only — type names, table names, file paths of shared modules. NO chunk-internal detail. Wave structure (which chunks ship in parallel) lives in the dependency graph, not here.>

## Decisions closure

| Decision | Status | Citation |
|---|---|---|
| <decision> | bound \| open \| deferred-to-X | <decisions.md date entry or chunk slug> |

## Invariants

<Required section. When the feature genuinely has no cross-chunk rule, the entire
body is one line: `No cross-chunk invariants — <reason>.` Do not manufacture filler.>

### <Invariant Name>
<One paragraph stating the invariant. Names which chunks enforce it.>

**Form:** test | assert | gate | doc
**Falsifier:** <the single check that would disprove this — a query, a named test, a gate>

## Threat model

<Required section. Populate when the feature touches authentication, session or
token handling, follow/block, writes to user-owned data, a public-vs-locked
exposure boundary, external-data ingestion, or an LLM-mediated path. Otherwise the
entire body is one line: `No threat-model surface — <reason>.`>

| Asset | Trust boundary | Threat | Mitigation | Falsifiable detection |
|---|---|---|---|---|
| <asset> | <who must trust whom> | <specific to this feature> | <what stops it> | <test/query/gate; cite the Invariants entry> |

**Residual risks:** <what remains uncovered, or "None.">

## Field Precedence on Linked Persons (or feature-specific equivalent)

<Table of cross-source data conflicts and resolution rules.>

## Cost & Capacity

<API quotas, rate limits, expected throughput.>

## Operator-facing budgets

<Manual-gate budgets, runtime budgets, expected operator effort.>

## Chunk index

| Slug | Description | Intent | Depends on |
|---|---|---|---|
| `<chunk-slug>` | <one concern, no AND, no bundle> | Foundation \| Behavior \| Hardening \| Migration | `<chunk-slug-or-empty>` |
| `<acceptance-chunk-slug>` | Acceptance suite: prove brief Goals honored, testable exclusions excluded | Hardening | `<every delivering chunk slug>` |

## Manual gates

<Operator runbook entries — pre-apply snapshots, post-run audits, etc.>

## Dependency graph

```
<ASCII or mermaid showing wave structure>
```
```

### Drafting rules — anti-thrash discipline

- **One concern per chunk row.** Only self-disclosure (`\bN-concern\b`, `\bbundle\b`, `\bbundling\b`) auto-refuses at the deterministic Concern-lint gate. Conjunctions, comma lists, plus-separators, and multi-clause descriptions are NOT auto-refusal triggers — they fire false-positives on legitimate prose ("extract helper used in 12 sites and migrate callsites" is one concern; "add fieldA, fieldB, fieldC to User model" is one schema change). Concern judgment for these is semantic: the ai-development persona applies the halved-work test to each chunk row in Self-prosecution. Mutual load-bearing is shipping-order, not bundling.
- **Every brief Goal maps to ≥1 chunk.** No orphan Goals. Cross-cutting infrastructure (rate limiters, error helpers, observability) maps to `### Supporting infrastructure` not a brief Goal (per `P-EP-BRIEF-GOALS`).
- **Chunks are cut inside the slice the spec assigned this brief.** Where a parent spec with `## Decomposition` resolves, the Coverage table already dispositioned every spec unit, and the chunk DAG inherits that cut whole: no chunk implements surface the table assigns to a **sibling brief slug** or excludes by a **named seam**. When a chunk's work sits near a boundary, place it by that seam's split-line predicate — hand the predicate the chunk's concern and take the side it returns, rather than arguing the placement from what is convenient to build together. A chunk the predicate puts on the far side belongs to the sibling brief, and reaching for it is annexation however well it factors here. A seam whose predicate cannot place the chunk — it names no side for this concern, or it returns both — is the spec layer's defect rather than this plan's: file `SPEC_AMENDMENT_NEEDED` routed to `/spec-author`, naming the seam, quoting its predicate, and naming the chunk it could not place. Do not guess the side. With no spec or no decomposition, chunks are cut against the brief alone.
- **Every chunk carries an intent, and Foundation carries an obligation.** `Foundation` (schema, types, scaffolding — no behavior change), `Behavior` (the user- or wire-visible change), `Hardening` (tests, error paths, observability), `Migration` (data/schema migration plus the runtime change safety requires). A `Foundation` chunk that no other chunk depends on ships dead code by definition — it changes no behavior and has no consumer — so either fold it into the chunk that consumes it or the label is wrong. `/plan-lint` FAILs the orphan case. A `Migration` chunk sequences *after* the runtime that makes the schema forward-compatible; a Migration chunk with no Foundation or Behavior dependency is almost always expand-then-contract inverted.
- **Invariants are required; content is not.** Write the cross-chunk rules, or the single line `No cross-chunk invariants — <reason>.` Never manufacture filler to fill the section: a fake invariant with a fake Falsifier passes `/plan-lint` and teaches the next reader that the section is decoration. Each real invariant carries `Form:` (`test` | `assert` | `gate` | `doc`) and `Falsifier:` — the one check that would disprove it. If you cannot write the Falsifier, what you have is prose; either sharpen it into a rule or drop it. `Form: doc` on a rule in a high-risk class is an unenforced invariant and reads as one.
- **Threat model is required; a disclaimer is a valid answer.** Populate it when the feature touches authentication, session or token lifetime, follow/block, writes to user-owned data, a public-vs-locked exposure boundary, external-data ingestion, or an LLM-mediated path. Otherwise state `No threat-model surface — <reason>.` The articulated decision is the deliverable — an empty table and a missing section read identically, and neither is an answer. Rows are specific to this feature; a paraphrased generic threat list is worse than the disclaimer because it looks like work. Each row's detection ties to an Invariants entry where one exists, and a threat with no falsifiable detection goes in `Residual risks:` rather than hiding in an empty cell.
- **Scope enforcement covers every brief exclusion, and the bucket carries through.** `Not planned` and `Not in scope (this release)` items get `testable-absence` or `scope-boundary` as before. `Intentionally deferred` items get `deferred-tracked` and repeat the destination — they are not enforced as absent, because the feature has committed to shipping them later. Silently promoting a deferred item to `scope-boundary` erases a commitment; silently demanding an assert-absence test for one manufactures work against something you intend to build.
- **Every EP ends with a dedicated acceptance chunk (the DAG sink).** One chunk whose concern is the contract-level acceptance suite — executable tests proving each brief Goal is honored on the assembled feature and each testable Non-goal stays excluded. Its Code-deps list every delivering chunk (so the suite runs against the whole feature) and no chunk depends on it. It is what the Goals `Verified by` and testable-Non-goal `Enforcement` cells point at. It is ONE concern regardless of how many Goals it covers — do NOT apply the halved-work / multi-concern test to it, and its per-Goal test coverage does NOT count toward `CHUNK_SURFACE_EXCESS` (its introduced identifiers are chunk-internal test names, and it owns no cross-chunk contract). It is contract-level only — it does not duplicate per-chunk TDD, which proves local behavior. A missing acceptance chunk is a `GOAL_VERIFICATION_GAP` blocker. Phrase its concern as a single noun — "the brief contract" — not "Goals and Non-goals": its chunk-index description uses a comma, not "and" ("prove brief Goals honored, testable Non-goals excluded"), so that when its per-chunk plan is authored the single-concern Goal sentence does not trip `/plan-lint`'s `goal-and` check.
- **Every Goal has a `Verified by` proof; every Non-goal is classified.** In Brief mapping → Goals, each Goal's `Verified by` names the acceptance chunk (or `Manual review — <reason>` only when the outcome is genuinely not observably automatable; a Goal that could be asserted but is left manual is a `GOAL_VERIFICATION_GAP`). In Brief mapping → Non-goals enforcement, each Non-goal is `testable-absence` (an observable exclusion — endpoint 404s, flag-off path inert, dismissed items never surface → the acceptance chunk owns an assert-absence test) or `scope-boundary` (a capability not built → `not test-assertable — <reason>`, no test). Mis-marking an observably-assertable exclusion as `scope-boundary` is a `GOAL_VERIFICATION_GAP` (a missing test hiding behind the classification).
- **No chunk-internal identifiers in the engineering plan.** Test names, single-file function names, internal phase splits, files-to-create lists, exact log strings, SQL queries, regex patterns — all chunk-internal. Per `P-EP-IMPL-DETAIL`, the engineering plan names cross-chunk contracts only.
- **Every cross-chunk decision is in Decisions-closure.** Status ∈ {bound, open, deferred-to-<chunk>}. `bound` means the decision is fully resolved; `open` means it needs user arbitration before the chunk plan can be authored; `deferred-to-<chunk>` means the listed chunk owns the decision.
- **No position-encoded slugs.** Slugs are semantic (`orphan-cleanup-hardening`), not positional (`wave-2-task-3`). Per `/plan-lint` and `_review-common/critical-pairs.md`.
- **No false parallelism.** A chunk in Wave N must have all dependencies in Waves <N. The dependency graph is the source of truth; the wave numbering descends from it, not the other way around.
- **Verified-by cells name chunk slugs.** Per `P-EP-VERIFIED-BY`. Never test files or test cases directly.
- **Risk depth is bounded.** Per `P-EP-RISK-DEPTH`. Name risks, mitigations, rollback. Don't enumerate every possible failure mode.
- **Drafted prose must not contradict bound decisions — class-aware.** Before emitting the in-memory draft to Plan-lint, scan every section (Brief mapping, Architecture summary, Decisions closure, Invariants, Field Precedence, Cost & Capacity, Operator-facing budgets, Chunk index descriptions, Manual gates, Dependency graph, Risks/unknowns, Rollout plan, Out of scope) for prose that contradicts a `Status: bound` entry in `features/<feature>/decisions.md` **or in the parent spec's decisions logs** — `specs/<slug>/decisions.md` and the shared `specs/decisions.md`, nearest first (only Active-section `bound` entries in any of them — a `superseded`/`obsolete` entry in the `## Archived` tail does not force a rewrite; per `~/.claude/skills/_review-common/principles.md` § What counts as a bound entry). Per `_review-common/principles.md` § Cross-artifact authority order, the rule is class-aware:
  - **Class B contradiction** (the draft contradicts a bound *wiring* decision — file path, schema column, module ownership, transaction boundary): bound decision wins. Rewrite the draft to match. If the contradiction is itself a discovery (new repo state invalidates the bound decision), surface as `OPEN_QUESTION` and the user re-arbitrates.
  - **Class A contradiction** (the draft asserts something a brief Goal or Non-goal forbids, even if a bound decision separately committed to it): the **brief wins**. Refuse to emit the section. Surface as `BRIEF_NONGOAL_TRESPASS` blocker — the bound decision is itself a defect that needs un-binding or brief amendment. Do not silently align with the bound decision; that resumes the accumulation pattern this rule exists to break.
  - **Boundary contradiction** (the draft's chunk placement contradicts an Active `Status: bound` entry in the **parent spec's** decisions logs — which briefs exist, where the seam between two of them sits): the bound call **wins and is never re-litigated at this layer**. Rewrite the placement to match it. Where the placement cannot be rewritten without moving the boundary itself, that is a blocker, not a draft decision: surface it as `OPEN_QUESTION` naming the bound entry and the chunk that crossed it, for `/spec-author` to re-cut. A *fix* that moves a bound boundary files `FIX_INTRODUCED_PREMISE_INVERSION` unless the director explicitly re-cut upstream first — re-cutting is `/spec-author`'s Seam alignment, and it supersedes the bound entry in the spec's log the usual two-step way.
  The Self-prosecution carry-forward auto-retract handles persona findings reactively; the proactive write-side pair runs at the Brief-conformance gate (which spawns the Brief-conformance Prosecutor against the in-memory draft) and at this rule (which scans the draft against both logs' bound decisions before emission).

---

## Brief-conformance gate (mandatory pre-draft check, runs BEFORE Plan-lint)

Authoring-side equivalent of `/engineering-plan-review-v2`'s Stage 1.5 Brief-conformance audit. Catches the failure mode where a chunk DAG trespasses a brief Non-goal or fails to deliver a brief Goal — a structural defect that no amount of Plan-lint or Concern-lint fixes.

The gate runs the same Brief-conformance Prosecutor as the reviewer side — same prompt, same subagent type, same severity discipline. The author self-prosecutes its own in-memory draft against the brief, refusing to emit any section the prosecutor flags as a trespass or undelivered Goal.

### Procedure

1. **Draft the chunk DAG in memory.** Build the chunk index, Brief Mapping, Supporting infrastructure entries, Architecture summary, Invariants, and any Decisions-closure entries the draft commits to binding. Hold the draft in memory; do NOT write the final plan to disk yet.

2. **Materialize the draft to a temp file** under `~/.claude/cache/author-state/<slug>-DRAFT.md`. The prosecutor needs to Read a file, not a prompt-embedded string. The temp file is cleared on gate exit (pass or fail).

3. **Spawn both Brief-conformance roles in one parallel batch** (Agent tool, `general-purpose`, default subagent type), using the two prompts in `~/.claude/skills/_review-common/brief-conformance-prosecutor.md`. **Every agent in this batch takes an explicit off-model `model` override** per that file's § Model pin (default `sonnet`; `opus` if the session is already Sonnet) — never inherit the session model. This gate judges the author's own in-flight draft, so a judge sharing the drafting model's priors is exactly the bias it exists to remove. Record the pinned model as `conformance_gate_model` in the sidecar.

   **(a) One Brief-conformance Prosecutor** (trespass + delivery + verifiability), substituting:
   - `{brief_path}` = `features/<feature>/brief.md`
   - `{plan_path}` = the temp draft path
   - `{sibling_plan_paths}` = every OTHER track's `engineering-plan.md` when the feature is tracked, else "none". Required — see `_review-common/brief-conformance-prosecutor.md` § Substitutions common to all layers. The draft under judgment is one track; without its siblings, every clause it hands off reads as a gap.
   - `{decisions_path}` = `features/<feature>/decisions.md` (or "none" if absent — first-round drafts will often have empty decisions logs, which is fine)
   - `{plan_layer}` = `engineering-plan`
   - `{additional_examples}` = the sidecar's accumulated `brief_conformance_calibration_examples` (false-positive resolutions from prior invocations; empty on first round)

   **(b) One Scope-fidelity Adversary per at-risk Goal**, each with the second prompt and exactly ONE Goal. Enumerate the brief's Goals, select the at-risk subset (a Goal carrying a domain quantifier — "every", "across", "all", "any", "going forward", "at every surface" — OR naming an authoritative signal/basis the outcome must be judged on; single-surface concrete Goals are not at-risk and get none), and for each selected Goal substitute `{goal_under_review}` = that Goal verbatim with the other four substitutions identical to (a). **NEVER batch multiple Goals into one adversary** — isolation is the load-bearing, validated separation. Record the selected and skipped-as-not-at-risk Goals in the sidecar block below. This is the author-side prevention pair: the draft's own chunk DAG is prosecuted for scope/authority/timing parity before it ever reaches the reviewer.

4. **Process findings.**
   - **`brief_conformance_check: passed`** → proceed to Plan-lint and Concern-lint with the in-memory draft.
   - **`findings_filed`, all severity MEDIUM HARD** → emit the partial draft to disk with `Status: needs-user-input` and a `## Pending blockers` section listing each finding's `reasoning` + `resolution_paths`. The user resolves the blockers and the session agent applies the resolutions directly to the plan — the author is not re-invoked. The MEDIUM rather than HIGH severity means the prosecutor was uncertain — the user's job is to adjudicate, not to be told the draft is wrong.
   - **`findings_filed`, any severity HIGH HARD** → hard refusal. Same partial-draft-to-disk flow, but the verdict label is `BRIEF_NONGOAL_TRESPASS`, `BRIEF_GOAL_UNDELIVERED`, or `SURFACE_PARITY_GAP` (mirroring the blocker registry classes). The user must choose a resolution_path, which the session agent then applies: for a trespass, amend brief / drop the trespassing chunk / un-bind the contradicting decisions.md entry; for a surface-parity gap, extend coverage so the authority is served at every consumer the Goal's domain touches, or scope the Goal's domain down in the brief when the residual is a genuine launch-acceptable cut.

5. **Sidecar block.** Write the gate's aggregated output (prosecutor + all adversaries) to the author sidecar at `~/.claude/cache/author-state/<slug>.json`:
   ```json
   {
     "brief_conformance_gate": {
       "brief_sha": "<sha256 of brief.md at draft time>",
       "draft_sha": "<sha256 of the temp draft>",
       "prosecutor_verdict": "passed" | "findings_filed",
       "findings_total": <int>,
       "findings_high_hard": <int>,
       "findings_medium_hard": <int>,
       "surface_parity_gaps": <int>,
       "scope_adversaries_spawned": <int>,
       "goals_at_risk": [<Goal verbatim>, ...],
       "goals_skipped_not_at_risk": [<Goal verbatim>, ...],
       "brief_conformance_calibration_examples": [<list of resolved-false-positive entries from prior rounds>],
       "blockers": [<verbatim findings from prosecutor AND adversaries, merged>]
     }
   }
   ```

   The `brief_conformance_calibration_examples` list grows across cycles: each time the user resolves a MEDIUM HARD finding by adding a Decisions-closure entry that legitimizes the prosecutor's miss, that resolution becomes a negative example passed into a later clean-slate re-author's `{additional_examples}` substitution. Calibration drifts toward the user's intent over cycles without weakening the gate.

### Why write-side prosecution matters

The reviewer's Stage 1.5 catches trespasses after the draft is on disk. The author's gate prevents them at draft time. The two gates are complementary — without the author gate, every draft pays the full review cost to surface a defect the author could have refused upfront. Without the reviewer gate, a partial-draft override (the user manually adding a chunk after the author refused) goes uncaught. The two gates share one prosecutor implementation, so calibration learned at the author layer transfers to the reviewer layer and vice versa.

---

## Plan-lint gate

Write the in-memory draft to `/tmp/<slug>-draft-<timestamp>.md`, then invoke the lint script directly via Bash:

```bash
python3 ~/.claude/skills/plan-lint/lint.py /tmp/<slug>-draft-<timestamp>.md
```

The Skill-tool form `Skill(skill="plan-lint", args="/tmp/...md")` is also valid; the Bash form is the canonical one because it surfaces stdout + exit code directly for capture into `sidecar.plan_lint_log`. Exit codes: `0` = clean, `1` = FAIL, `2` = usage/IO error.

If lint fails (exit 1):
- Read the failure list. For each defect, identify whether the fix is local (rewrite a line) or structural (remove a chunk, reorder dependency).
- Apply local fixes to the in-memory draft, re-run lint. Repeat up to 2x.
- If structural fixes are needed, refuse to emit; surface as `STRUCTURAL_LINT_FAILED` blocker requiring user arbitration.

If lint errors (exit 2): re-check the temp-file path and content; if the issue persists, treat as a `STRUCTURAL_LINT_FAILED` blocker with the lint stderr verbatim.

Delete the temp file regardless of outcome (no leftover drafts in `/tmp`).

The Plan-lint gate is HARD-blocking. A draft that fails plan-lint never reaches the Concern-lint gate.

---

## Concern-lint gate

For each row in the in-memory draft's chunk index, apply ONE deterministic check against the description cell (mirrors the chunk-plan author's Concern gate):

**Self-disclosure** — `/\b\d+-concern\b|\bN-concern\b|\bbundle\b|\bbundling\b/i` matches anywhere in the row description. This is the author actively admitting the row is bundled; no false-positive case exists.

On a match, run the carry-forward consultation below BEFORE refusing. If carry-forward applies for that row, mark its lint outcome `carried_forward` (per the sidecar's `concern_lint_status` and `concern_lint_carry_forward_log`) and proceed.

If a row matches AND has no applicable carry-forward, the gate is HARD-blocking for that draft. Surface a `CONCERN_GATE_FAILED` blocker naming the offending row(s); the user either decomposes into one-concern siblings (which forces an aligned update of the chunk index, dependency graph, brief-mapping table, and decisions-closure entries — partial fixes are not allowed) or records an explicit `## Decisions closure` row arbitrating the bundle, citing a `decisions.md` entry with `bound` status, so the arbitration carries forward deterministically.

### Patterns NOT enforced by this gate

Four syntactic patterns stay out of this gate: ` AND ` conjunctions, three+ comma-separated noun phrases, `+ <noun> + <noun>` separators, and ≥2 independent clauses. Each fires constantly on legitimate one-concern prose:

- "Extract helper used in 12 sites and migrate callsites" is one concern (the migration is incomplete without the extraction).
- "Add fieldA, fieldB, fieldC to the User model" is one schema change with three named columns.
- "Schema migration: drop column X; backfill column Y; add index Z" describes one mechanical change with three named ripples.

Concern judgment for these cases is semantic, not syntactic. The ai-development persona evaluates every chunk-index row in Self-prosecution with the **halved-work test**: "if you halved the work this chunk row implies, would the other half still be a coherent shippable thing?" If yes → multi-concern, surface a finding. If no → one concern, proceed. The persona runs on every chunk row regardless of pattern matches; explicit syntactic detection is not needed because the persona reads the actual draft and judges semantically.

### Concern-lint carry-forward consultation

Run this only on a refusal-pattern match. It produces a deterministic decision: carry-forward applies, or it doesn't. Three sources are checked, in order; the first match wins.

1. **Engineering-plan reviewer state.** Read `~/.claude/cache/review-state/<slug>.json` — `<slug>` per § Sidecar location, so a tracked feature consults its own track's state. In `recently_resolved_blockers`, find an entry where ALL of:
   - `path_or_section` substring-matches one of: the chunk slug; the chunk-index row's verbatim description; or `chunk-index row N` where N is the row's index position.
   - `blocker_class_when_resolved` is one of `CONCERN_GATE_FAILED`, `CHUNK_BUNDLE`, `MULTI_CONCERN`, `CONCERN_FACTORING` — OR the entry's `summary` field contains both a concern-family keyword (`bundle`, `concern`, `factoring`) and a resolution-direction keyword (`accept`, `bound`, `keep`, `retain`, `reaffirm`).
   - `carry_forward_until_round >= current_invocation_number` (cross-side number-line mapping per `_author-common/self-prosecution-protocol.md`).

2. **Engineering-plan-author state.** Read this skill's own sidecar `~/.claude/cache/author-state/<slug>.json` (same `<slug>`). Apply the same three-condition match against ITS `recently_resolved_blockers`.

3. **Engineering-plan decisions-closure scan.** Read the in-memory draft's `## Decisions closure` section. A row carries forward when ALL of:
   - The `Decision` column substring-matches the chunk slug or the row's verbatim description.
   - The `Resolution` column starts with `bound` (case-insensitive), AND if the row cites a `decisions.md` entry, that entry is still Active-bound — not `superseded`/`obsolete` (a stale EP row citing a since-retired decision does not carry forward; per `~/.claude/skills/_review-common/principles.md` § What counts as a bound entry).
   - The `Resolution` column contains a concern-family keyword (`bundle`, `multi-concern`, `mutually load-bearing`, `transactional invariant`, `theme-unified`).
   - **Scope coverage (HARD).** The bound decision must cover the SAME concerns the flagged row enumerates, not merely share a concern-family keyword. Identify the matched bundle's local scope: extract the parenthetical or "+"-separated list immediately containing the matched `bundle` / `bundling` / `N-concern` keyword. Tokenize that local scope into component noun phrases (split on `+`, `;`, ` AND `, ` plus `). For each component, the bound decision's `Resolution` column must name a substring match OR cite a sibling `decisions.md` entry by date that does. If any component is unmatched, source 3 does NOT carry forward — even if every other condition passes. Record `concern_lint_carry_forward_log[*].scope_coverage` with `components_matched: [...]` and `components_unmatched: [...]` so the failure path names which concerns the bound decision left uncovered.

If any source matches AND (when source 3 is the matching source) scope coverage passes, set `concern_lint_status: "carried_forward"` for the matched bundle's **local scope only**, append a `concern_lint_carry_forward_log` entry naming the source, blocker id (when applicable), `carry_forward_until_round`, the user's decision verbatim, AND the scope-coverage component list. Then run the residual-scope check below before declaring the row clean.

**Residual-scope check (MANDATORY, runs after any carry-forward).** A successful carry-forward dismisses ONLY the matched bundle's local scope, not the entire row. After recording the carry-forward, rescan the row description for additional self-disclosure pattern matches that sit OUTSIDE the matched scope. For each additional match, repeat the three-source consultation independently. The row passes only when every self-disclosure match in the row has its own carry-forward path. A row containing one bound bundle and N residual unbound concerns refuses with `CONCERN_GATE_FAILED` naming the residual concerns — a single `decisions.md` row covering one component cannot dismiss a row enumerating N components. This is the leak a keyword-only match admits: a decisions row binding "retirement-protocol bundle" carries forward only the retirement-protocol bundle, not the surrounding marker-infra + walker + registry concerns the same chunk row enumerates alongside it.

If no source matches (or residual-scope fails), refuse with `CONCERN_GATE_FAILED`. The verdict surfaces three actionable resolutions: rewrite the chunk-index row description to single-concern phrasing citing the decision (preferred); add an explicit `## Decisions closure` row arbitrating the bundle WITH scope coverage of every component; or re-run `/engineering-plan-review-v2` to record the arbitration in the reviewer state's `recently_resolved_blockers`.

---

## Feature-surface estimator gate

Runs immediately after the Chunk-surface estimator (whose per-row counts it aggregates), per `~/.claude/skills/_review-common/feature-surface-gate.md` § Feature-surface estimator. Deterministic, no LLM: compute `chunk_count`, `dag_depth`, `cross_chunk_contract_total` (sum of per-row counts), and `open_decision_count` over the whole draft. ANY breach (`chunk_count >= 10`, `dag_depth >= 5`, `cross_chunk_contract_total >= 12`, `open_decision_count >= 6`) files `FEATURE_SURFACE_EXCESS` (HIGH on ≥ 2 sub-metrics, MEDIUM on 1) → partial-draft with the split proposal (spawn the split-proposal agent, `model: "sonnet"`, per the gate file) unless a bound size-acceptance row per the gate file's § Acceptance suppresses (residual-scope: re-fires on ≥ 25% growth past accepted values or an added Goal). Record the four sub-metrics as `feature_surface` in the sidecar regardless of verdict. This is the layer-above analog of the Chunk-surface estimator: that gate asks "is this row chunk-sized"; this one asks "is this DAG feature-sized or is it several features wearing one brief."

## Chunk-surface estimator gate

Independent of self-disclosure. Runs after Concern-lint, before Ground-truth audit. Catches structural over-bundling that Concern-lint cannot reach: a chunk where every individual concern is bound by `decisions.md` but the *aggregate surface* exceeds the reviewer-convergence threshold. The Concern-lint gate verifies "each concern is intentional"; this gate verifies "the row carries a chunk-sized amount of work, not a feature-sized amount."

### Per-row counts

For each chunk-index row, compute three counts from the row description plus any inline parenthetical detail:

- `concern_count` — number of top-level "+"-separated noun phrases in the row description. Tokenize by splitting on `+`, `;`, ` AND `, ` plus ` at the outermost paren level. Nested parentheticals count as ONE concern at the outer level, even when they internally enumerate components (so the `retirement-protocol bundle (retirement comment + permanent guard test + doc-surface amendments)` counts as one outer concern with three internal components — the internal split applies only to Concern-lint scope-coverage, not to this surface count).
- `introduced_identifier_count` — number of distinct identifiers the row's prose names that the chunk *creates*: function names, type names, named constants, CLI subcommands, schema column names, file paths created. Count creation references, not consumption references (a row that says "calls `existing_helper`" does not count `existing_helper`).
- `cross_chunk_contract_count` — number of distinct cross-chunk forward-binding contracts the row binds. Heuristic phrases: "every chunk that…", "downstream chunks…", "forward-binding", "cross-chunk", "future-chunk", "every other enum-introducing chunk", and explicit cross-chunk-contracts sub-sections.

### Threshold

File `CHUNK_SURFACE_EXCESS` as a HARD blocker when ANY of:

- `concern_count >= 5`
- `introduced_identifier_count >= 8`
- `cross_chunk_contract_count >= 2`

A chunk hitting any threshold is feature-shaped rather than chunk-shaped, even when each individual concern is bound. The thresholds match the project's chunk-discipline ceiling (≤5 files, one concern, single-PR review surface).

### Blocker contents

The `CHUNK_SURFACE_EXCESS` finding names:
- The chunk-index row (slug + verbatim description).
- The computed counts (all three, even those under threshold).
- Which threshold(s) breached.
- Three actionable resolutions: (1) split the row into N sibling chunks with explicit dependency edges between them; (2) extract a foundational sub-chunk that other siblings depend on, reducing the original row's surface to just the foundation; (3) cite a `decisions.md` row that arbitrates the **aggregate surface area** explicitly (not just one of its component concerns) — the cited row must contain language acknowledging the surface size as intentional, not merely binding what the chunk does.

### Carry-forward exemption

`CHUNK_SURFACE_EXCESS` is NOT subject to Concern-lint's three-source carry-forward consultation. Surface excess is a structural property of the row, not a concern-bundling question; a `decisions.md` row binding *what* the chunk does cannot bind *how much*. Surface excess requires a dedicated arbitration row or row decomposition. The reviewer skill mirrors this carve-out — a `decisions.md` entry covering one component does not retract a `CHUNK_SURFACE_EXCESS` blocker.

### Sidecar additions

Extend the author state-file schema with:

```json
"chunk_surface_estimator": {
  "rows": [
    {
      "slug": "<chunk-slug>",
      "concern_count": <int>,
      "introduced_identifier_count": <int>,
      "cross_chunk_contract_count": <int>,
      "threshold_breached": ["concern" | "identifiers" | "contracts" | ...],
      "verdict": "passed" | "excess"
    }
  ]
}
```

Each row's verdict is `passed` or `excess`. Persist on every author invocation so the reviewer can verify the gate ran.

---

## Ground-truth audit

Apply `_author-common/ground-truth-protocol.md`. At the engineering-plan layer:

- **V2 (identifier) is dominant.** Every cross-chunk contract name (table, type, flag, file path of shared module) is either:
  1. Added to `introduced_identifiers` in the sidecar (the engineering plan introduces this; child chunks build it).
  2. Verified to exist in the repo (`schema.prisma`, `operations.graphql`, source code).
- **V4 (cross-document) is heavy.** Every brief-Goal quote in Brief Mapping is verified verbatim. Every decisions.md citation in Decisions-closure is verified by date + entry text. Every CLAUDE.md / project-memory rule the engineering plan invokes is verified. Where a parent spec resolved, its citations clear the same bar as a brief Goal's: every spec-section reference resolves to that heading in that file, every `## Decomposition` scope-stub quote matches the stub verbatim, and every spec-log citation names an entry that exists in the `## Active (bound)` section. A citation of the spec is a claim about a real file like any other, and one the draft cannot verify is dropped or softened rather than carried.
- **V3 (constraint) tests the dependency graph.** Each "X depends on Y" claim must be reflected in the chunk-index `Depends on` column AND in the dependency graph.

Carve-out 1 (`introduced_identifiers`) is the dominant carve-out at this layer — engineering plans introduce more cross-chunk contract names than they reference existing ones.

Sidecar audit log includes the full claim-by-claim breakdown.

---

## Self-prosecution and imagined-implementer

### Persona prosecution

Spawn five persona agents in parallel using the template in `_author-common/self-prosecution-protocol.md`:

- **architecture** — system-shape coherence, hidden dependencies, false parallelism, factoring.
- **ai-development** — chunk discipline, plan-quality at engineering-plan layer, DAG cycles, position-encoded slugs.
- **product** — brief drift, Goal mapping, Non-goal enforcement, scope creep.
- **backend** — schema-additions correctness, GraphQL-operation introductions, decisions-closure on backend wiring.
- **testing** — `Verified by` columns, gate-test coverage, chunk-internal-detail leakage in test references.

Active critical pairs: universal pairs + engineering-plan-specific pairs (`P-EP-IMPL-DETAIL`, `P-EP-BRIEF-GOALS`, `P-EP-VERIFIED-BY`, `P-EP-RISK-DEPTH`, `P-EP-DECISION-LOC`).

### Imagined-Implementer dry-run (after personas return)

Author skills mirror the reviewer's `imagined_implementer` pass — but at write time, with stronger consequences (the verdict gate uses it).

Procedure:

1. Pick the first chunk in the chunk index whose `Depends on` is empty (or whose dependencies are all marked `bound` and shipped).
2. Attempt a thought-experiment authoring of its chunk plan WITHOUT actually writing it. The procedure follows what `/plan-author` would do: read the brief, read the engineering plan §relevant chunk, read decisions.md, build a Factoring Contract, fill §Owns / §Contracts / §Acceptance.
3. Surface every cross-chunk wiring decision the imagined-implementer would need to *bind* but the engineering plan leaves *open* or *deferred-without-citation*. Each such decision is filed as `IMPLEMENTABILITY_GAP` with:
   - The decision name.
   - Where the chunk plan would have to bind it.
   - A `severity_test` — a falsifiable scenario where leaving the decision unbound breaks the chunk plan ("if Decision X is open, the chunk's §Owns step 3 cannot be written because it depends on knowing whether Y or Z is the source-of-truth").
4. If no `IMPLEMENTABILITY_GAP` surfaces, the imagined-implementer pass returns `verdict: implementable`. Otherwise `verdict: not_implementable`.

The verdict gate uses this:

- **CLOSED** ⇔ `imagined_implementer.verdict == implementable` AND no other blockers.
- **APPROVED** ⇔ shape-correct AND `imagined_implementer.verdict == not_implementable` (one or more `IMPLEMENTABILITY_GAP`s remain — the engineering plan is fine, but per-chunk authoring is blocked until the user binds the gaps).
- **NEEDS_USER_INPUT** ⇔ anything else.

### No-annexation check (chunk grain; runs after the dry-run, before consolidation)

Mechanical, and it runs only when a parent spec carrying `## Decomposition` resolved at Source ingest. Where the Coverage table exists, test every chunk-index row against it — the same check `/brief-author` runs one layer up, at chunk grain instead of Goal grain.

The slug the table is read against is the brief's own: the feature directory name under `features/` **is** the slug, and it matches the brief's row in the spec's Briefs table (`~/.claude/skills/_spec-common/spec-format.md` § Scope stubs). A Coverage table with **no row for that slug** stops the check rather than failing every chunk in it: file exactly one `OPEN_QUESTION` naming the slug and the missing row, record `no_annexation: not_applicable`, and cut chunks against the brief alone for this run. One missing row is one finding — never one per chunk, and never a silent proceed. Either the brief names the wrong parent or the spec's decomposition never cut this brief, and both are answered upstream.

For each chunk row, identify the spec units its work implements. Every one must be a unit the Coverage table dispositions to **this brief's slug**. A chunk implementing a unit the table assigns to a **sibling brief slug**, or excludes by a **named seam**, files `OPEN_QUESTION` (HIGH) naming three things: the unit, the slug or seam the table dispositions it to, and the chunk that reached for it. A chunk whose concern sits near a boundary is placed by that seam's split-line predicate; a chunk the predicate returns to the far side is the same finding.

Do not widen the plan to absorb the unit and do not drop the chunk — which of the two is right is the director's call, and it is the one finding no reviewer downstream can make: the annexing plan traces its chunk to a real brief Goal, the annexed brief still traces its own, and both review clean while the unit ships twice or nowhere. A spec with no Coverage table skips the check. Record `no_annexation: not_applicable | clean | <N> claims` in the sidecar either way.

### Verdict template

```markdown
# Engineering plan authoring verdict — <plan-root>/engineering-plan.md

**Mode:** cold | warm
**Authoring mode:** ship | draft
**Round:** <invocation_number>
**Last engineering-plan sha:** <hex>
**Parent spec:** <path> (from the brief's `Spec:` header) | none — brief carries no Spec header | named but missing — <path>; decomposition: ingested | absent

## Plan-lint
**Status:** PASS | FAIL
**Defects:** <N>; if FAIL, list each.

## Concern-lint
**Status:** PASS | FAIL | CARRIED_FORWARD
**Offending rows (if FAIL):** <quoted descriptions>
**Carried-forward rows (if CARRIED_FORWARD):** <row description> ← <source: review_state | author_state | decisions_closure> entry <id-or-citation> until round <N>

## Ground-truth audit
**Claims total:** <N>
**Verified:** <V>  **Softened:** <S>  **Corrected:** <C>  **Dropped:** <D>  **Restructured:** <R>  **Skipped (carve-out):** <K>
**Introduced identifiers:** <count> (<comma-separated list, truncated>)
**Bound decisions consulted:** <N> (feature log <n>, spec logs <m> — `specs/<slug>/decisions.md` + `specs/decisions.md`, or none)
**Contradictions found:** Class A <n>; Class B <n>; boundary <n>
**No-annexation:** not_applicable | clean | <N> claims

## Self-prosecution
**Personas:** architecture, ai-development, product, backend, testing
**Premise interrogation:** <per-persona pass/fail>
**Standard findings:** <N total>; <by tier+severity>
**Post-fix premise verification:** <P claims rewritten; Q falsified> → <FIX_INTRODUCED_PREMISE_INVERSION count>
**Carry-forward consultation:** <skipped because cold | M recently-resolved blockers cross-checked, R re-prosecutions auto-retracted>

## Imagined-Implementer dry-run
**Chunk attempted:** `<slug>`
**Verdict:** implementable | not_implementable
**Implementability gaps:** <N> (each with decision name + severity_test)

## Verdict
**CLOSED** | **APPROVED** | **NEEDS_USER_INPUT** | **DRAFT_EMITTED**

### Blockers (if NEEDS_USER_INPUT)
- [STABLE_DISAGREEMENT] <span> — <one-line>
- [OPEN_QUESTION] <span> — <one-line>
- [FIX_INTRODUCED_PREMISE_INVERSION] <span> — <one-line>
- [STRUCTURAL_LINT_FAILED] <plan-lint defect> — <one-line>
- [CONCERN_GATE_FAILED] <chunk-index row> — <one-line; decomposition required>
- [BRIEF_NONGOAL_TRESPASS] <chunk / section> — <one-line; brief Non-goal quoted>
- [BRIEF_GOAL_UNDELIVERED] <brief Goal> — <one-line; no chunk delivers it>
- [SURFACE_PARITY_GAP] <brief Goal> — <one-line; the narrowing axis and the shortfall>
- [GOAL_VERIFICATION_GAP] <Goal / Non-goal / acceptance chunk> — <one-line; what proves it, or does not>
- [CHUNK_SURFACE_EXCESS] <chunk-index row> — <one-line; the breached counts>
- [FEATURE_SURFACE_EXCESS] <the DAG> — <one-line; the breached sub-metrics and the split proposal>
- [BRIEF_AMENDMENT_NEEDED] <gap> — <one-line; the defect is the brief's own>
- [SPEC_AMENDMENT_NEEDED] <gap> — <one-line; the contradiction originates in the spec — routed to `/spec-author`>
- [UNCORROBORATED_RESET] <span> — <one-line>

### Implementability gaps (if APPROVED)
- <decision name>: <severity_test>; <where it must be bound>

### Authoring residuals (LOW, under polish floor)
- ...
```

### Verdict gates

- **CLOSED** ⇔ ALL of:
  - Authoring mode is `ship` (not `--draft`).
  - Plan-lint PASS, Concern-lint PASS or CARRIED_FORWARD, Chunk-surface estimator PASS for every row, Imagined-Implementer verdict `implementable`.
  - Tier-1 weight = 0; Tier-2 weight ≤ 4 (polish floor).
  - No `BRIEF_NONGOAL_TRESPASS`, `BRIEF_GOAL_UNDELIVERED`, `SURFACE_PARITY_GAP`, `GOAL_VERIFICATION_GAP`, `BRIEF_AMENDMENT_NEEDED`, `SPEC_AMENDMENT_NEEDED`, `CONCERN_GATE_FAILED`, `CHUNK_SURFACE_EXCESS`, `FEATURE_SURFACE_EXCESS`, `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `IMPLEMENTABILITY_GAP`, `UNCORROBORATED_RESET`, `STRUCTURAL_LINT_FAILED`, `FIX_INTRODUCED_PREMISE_INVERSION`, `REPO_STATE_DRIFT`.

- **APPROVED** ⇔ shape-correct (Plan-lint PASS, Concern-lint PASS or CARRIED_FORWARD, Chunk-surface estimator PASS for every row, no other blockers above) AND `imagined_implementer.verdict == not_implementable` AND one or more `IMPLEMENTABILITY_GAP` findings remain. Per-chunk plan authoring is **NOT** unblocked at APPROVED; the session agent binds the gaps via `decisions.md` and marks the plan CLOSED — the author is not re-invoked — before chunk authoring can begin.

- **NEEDS_USER_INPUT** ⇔ authoring mode is `ship` AND any blocker class above (other than IMPLEMENTABILITY_GAP) fires. Concern-lint failures with no applicable carry-forward fall here as `CONCERN_GATE_FAILED`; chunk-surface estimator threshold breaches fall here as `CHUNK_SURFACE_EXCESS` (NOT subject to concern-lint carry-forward; surface excess requires its own dedicated arbitration row or row decomposition).

- **DRAFT_EMITTED** ⇔ authoring mode is `--draft` (Plan-lint, Concern-lint, Ground-truth audit, and Self-prosecution skipped). Disk write proceeds with NO `Status:` frontmatter; the sidecar records `authoring_mode: "draft"` as the load-bearing draft signal. Per-chunk plan authoring is gated on the engineering plan being CLOSED, so a DRAFT_EMITTED engineering plan does NOT unblock `/plan-author` — authoring without `--draft` produces a hardened plan first; the author is not re-run to harden an existing `--draft` artifact.

### Pending-blockers section (NEEDS_USER_INPUT mode)

On NEEDS_USER_INPUT, the on-disk engineering plan gets two additions beyond the partial draft body:

1. **Frontmatter `Status: needs-user-input`** is added (or replaces a prior Status value if any). The CLOSED/APPROVED-emission convention is no `Status:` field; the NEEDS_USER_INPUT path adds the field as the only valid Status value.
2. **`## Pending blockers` section appended at the end of the file**, with verbatim bullets from the verdict's `### Blockers` block:

   ```markdown
   ## Pending blockers

   <!-- This section is auto-managed by /engineering-plan-author. Resolve each blocker below; the session agent then applies your resolutions directly to this file and removes this section along with the `Status: needs-user-input` line — the author skill is not re-run. Per-chunk plan authoring (`/plan-author`) is also gated on this status and refuses to run until the engineering plan lands at CLOSED. -->

   - [<BLOCKER_CLASS>] <span / section> — <one-line summary>; <actionable resolution path>.
   - ...
   ```

Once the session agent has applied every resolution, it removes the entire `## Pending blockers` section AND its HTML comment, AND the `Status: needs-user-input` line (a resolved plan carries no `Status:` field). While any blocker remains unresolved, the `## Pending blockers` section keeps only the still-open blockers (resolved ones drop out as they land — stale blockers don't accumulate) and the `Status: needs-user-input` line stays. IMPLEMENTABILITY_GAP findings, which gate CLOSED but not APPROVED, do NOT appear in `## Pending blockers` — they live in the engineering-plan body's Decisions-closure table where they belong.

---

## Hard rules

- **Stage order is fixed.** State load, then Engineering-plan-worktree provisioning (a no-op only under its own listed conditions), then Source ingest, then Draft. Plan-lint before Concern-lint. Concern-lint before Ground-truth audit. Ground-truth audit before Self-prosecution and imagined-implementer. All before emission. `--draft` skips Plan-lint, Concern-lint, Ground-truth audit, and Self-prosecution.
- **Brief is HARD-blocking.** No brief.md → skill refuses to run.
- **Plan-lint is HARD-blocking.** Failures must be fixed in-loop or surfaced as `STRUCTURAL_LINT_FAILED`; the draft cannot reach Concern-lint with structural defects.
- **Concern-lint is HARD-blocking unless carry-forward applies.** Triggered only by self-disclosed bundling in chunk-index row descriptions (`\bN-concern\b`, `\bbundle\b`, `\bbundling\b`). The draft cannot reach Ground-truth audit with unsalvaged self-disclosed bundled rows. Catching at this layer prevents the cascade into multi-concern chunk plans. Other concern judgments (genuine bundling that the row description doesn't self-disclose) are handled semantically by the ai-development persona's halved-work test in Self-prosecution, NOT by this gate.
- **Imagined-Implementer is mandatory in `ship` mode.** It is the load-bearing gate between APPROVED and CLOSED.
- **Disk-write semantics by verdict:** CLOSED and APPROVED write the engineering plan with NO `Status:` frontmatter (the binary-Status convention reserves `Status:` for the mid-cycle signal only); NEEDS_USER_INPUT writes the partially-improved in-memory draft with frontmatter `Status: needs-user-input` AND an inline `## Pending blockers` section listing each unresolved finding verbatim from the verdict (the user fixes the blockers and the session agent applies the resolutions directly, then clears the `Status:` line — the author is not re-invoked); DRAFT_EMITTED writes with NO `Status:` frontmatter; the sidecar's `authoring_mode: "draft"` is the load-bearing draft signal that downstream skills consult. Sidecar persists in all cases. The reviewer skill `/engineering-plan-review-v2` refuses to run against `Status: needs-user-input` artifacts — the partial draft is mid-cycle by design and not yet a candidate for prosecution. **After a CLOSED or APPROVED first draft, the next step is to run `/engineering-plan-review-v2`.**
- **Sidecar always written.** Every invocation, every verdict.
- **Chunk-internal detail prohibition.** A draft that names test files, exact regex patterns, single-file function names in the engineering-plan body (outside of the sidecar's `introduced_identifiers` for cross-chunk contracts) is rejected by the architecture+ai-development persona prosecution.
- **Decisions-closure completeness.** Every cross-chunk wiring decision the chunks reference must appear in the decisions-closure table. A reference without a closure entry is `IMPLEMENTABILITY_GAP`.
- **The parent spec's bound decisions bind here too.** An Active `Status: bound` entry in the parent spec's decisions logs — `specs/<slug>/decisions.md` and the shared `specs/decisions.md`, nearest first — settles which briefs exist and where the boundary between two of them sits, and it is never re-litigated at this layer. A chunk placement that contradicts one is a blocker — `OPEN_QUESTION` naming the entry and the chunk that crossed it, for `/spec-author` to re-cut — never a placement the draft argues its way into. A *fix* that moves a bound boundary is `FIX_INTRODUCED_PREMISE_INVERSION` unless the director explicitly re-cut upstream first. The check has a verdict surface: `bound_decisions_consulted` counts both logs alongside the feature's own, and the boundary-contradiction count sits with the Class A / Class B counters, so a run that skipped the read is visible. Whether the logs bind at all is decided by file presence and by the decomposition: no `**Spec:**` header resolving to a real spec, no log beside that spec, or a spec carrying no `## Decomposition`, and the rule is a no-op.
- **Amendments route upward one layer at a time.** Before filing `BRIEF_AMENDMENT_NEEDED`, ask where the contradiction actually originates. A defect that is genuinely the brief's own — a Goal it under-specifies, a Non-goal it should carry, a cohort it invented — keeps the brief class. A contradiction originating **upstream of the brief** — in the parent spec's `## Decomposition` (a seam, a Coverage assignment, a scope stub) or in the spec's prose — files `SPEC_AMENDMENT_NEEDED` routed to `/spec-author` instead, because amending the brief there papers over the layer that actually owes the change and the next brief cut from the same spec inherits the same contradiction. Never escalate past the spec: a contradiction whose root is a vision-layer rule reaches vision through the spec machinery (`/spec-author` files `VISION_AMENDMENT_NEEDED`), never from this layer.
- **No banned content.** Same prohibited categories as `/brief-author` (addendum, review attribution, historical comparison, persona-attribution headers).
- **Carry-forward respect.** Re-introducing a chunk the user removed in a prior invocation, or re-opening a decision the user closed, is `FIX_INTRODUCED_PREMISE_INVERSION`.
- **Drafted prose must not contradict bound `decisions.md` entries — class-aware.** Before emitting the in-memory draft to Plan-lint, scan every section (Brief mapping, Architecture summary, Decisions closure, Invariants, Field Precedence, Cost & Capacity, Operator-facing budgets, Chunk-index descriptions, Manual gates, Dependency graph, Risks/unknowns, Rollout plan, Out of scope) for prose contradicting any `Status: bound` entry in `features/<feature>/decisions.md` **or in the parent spec's decisions logs** — `specs/<slug>/decisions.md` and the shared `specs/decisions.md`, nearest first (only Active-section `Status: bound` entries — a `superseded`/`obsolete` entry in the `## Archived` tail does not force a rewrite; per `~/.claude/skills/_review-common/principles.md` § What counts as a bound entry). Per `_review-common/principles.md` § Cross-artifact authority order, the rule is class-aware. **Class B contradictions** (bound wiring decision contradicts the draft on a file path / schema column / module ownership / transaction boundary): bound decision wins — rewrite the draft to match, OR surface as `OPEN_QUESTION` if the contradiction is a discovery. **Class A contradictions** (the draft asserts something a brief Goal or Non-goal forbids, even if a bound decision separately committed to it): the **brief wins** — refuse to emit the section and surface as `BRIEF_NONGOAL_TRESPASS`. The bound decision itself is the defect; do not silently align with it. The verdict template's `Ground-truth audit` block records `bound_decisions_consulted` across the feature log and both spec logs, alongside the Class A, Class B, and boundary contradiction counts, so missing this step is visible. The Brief-conformance gate (which spawns the Brief-conformance Prosecutor) is the proactive write-side pair for Class A; the Self-prosecution carry-forward Priority 1 auto-retract handles persona findings reactively.

---

## Edge cases

**Sidecar absent, engineering-plan.md absent (cold start):** State load returns empty; Source ingest reads brief + decisions only; Draft writes from scratch. All later stages run normally.

**Sidecar absent, engineering-plan.md present:** Treat current file as warm-mode source; reset ground-truth to fresh; carry-forward unavailable.

**Sidecar present, engineering-plan.md present, SHA matches, request adds no new constraint or instruction:** No-op invocation; print "no changes; engineering plan in last-APPROVED/CLOSED state." (A plain-language ask to rewrite or change the plan IS a new instruction and proceeds in warm mode.)

**Sidecar present, engineering-plan.md absent (deleted):** Treat as cold disk-state; consult sidecar history for prior arbitrations; surface in verdict that prior plan was deleted.

**Brief amended since last invocation (brief sha changed in brief-author sidecar):** Hard re-author. The chunk DAG may need restructuring to honor new Goals or honor amended Non-goals. Surface every brief-driven structural change in the verdict.

**Brief carries no `**Spec:**` header:** No parent spec resolves. Record `parent_spec: null`, skip the Decomposition read, the inherited-exclusion resolution, and the spec's decisions logs; the no-annexation check records `not_applicable`. Every stage then runs against the brief alone, and nothing outside the spec-layer steps changes. Do not ask which spec the feature belongs to and do not go hunting for one — the brief owns that claim, and a brief with no header is a legacy brief rather than an ambiguity.

**The `**Spec:**` header names a file that is not on disk:** Record `parent_spec: "named but missing — <path>"`, skip the same steps, and file `OPEN_QUESTION` (HIGH) naming the header and the path. This is the dangling header, and it is not the no-header case: the brief made a claim about a real file that every spec-layer step would have anchored on, so it surfaces as a finding rather than a silent no-op.

**Parent spec resolves but carries no `## Decomposition` section:** Record `decomposition_stub: "absent"` and proceed with no stub, no Coverage table, and no seams. Chunks are cut against the brief alone and the no-annexation check records `not_applicable`. Boundary-binding is gated on the decomposition, so the spec's logs bind nothing here either: a spec that draws no boundaries has none to bind. This is the whole of the degradation.

**Parent spec's decisions logs absent:** Not an error, and not a refusal. Read whichever of `specs/<slug>/decisions.md` and `specs/decisions.md` is there and carry on; with neither, the transitive-bound-decisions rule is a no-op.

**A chunk implements a spec unit the Coverage table gives a sibling brief:** `OPEN_QUESTION` (HIGH) from the no-annexation check. Do not widen the plan to absorb the unit and do not drop the chunk — the director picks, and the pick lands as a bound entry in the spec's log via `/spec-author`, not here.

**Plan-lint surfaces a STRUCTURAL_LINT_FAILED that the orchestrator can't auto-fix in two passes:** Block emission; surface to user with the exact `/plan-lint` failure messages quoted.

**Concern-lint refusal pattern matches a row, but the user has arbitrated the bundle elsewhere:** The carry-forward consultation handles this. If a matching `recently_resolved_blockers` entry (in either the engineering-plan reviewer state or this skill's own author state) is in carry-forward window, OR an explicit `## Decisions closure` row is `bound` and contains a concern-family keyword, the row's outcome is `carried_forward`. Otherwise the gate refuses with `CONCERN_GATE_FAILED` and the verdict prose names the three resolution paths (chunk-index rewrite, decisions-closure row, reviewer re-run).

**Imagined-Implementer surfaces gaps but persona prosecution all PASS:** Verdict is APPROVED (shape-correct, decisions undecided). The session agent binds the gaps in `decisions.md` and marks the plan CLOSED once every gap is bound — the author is not re-invoked.

**Persona finds an UNCORROBORATED_RESET:** Per `_review-common/blocker-classes.md`, RESET findings need 2-persona corroboration OR 1 persona + verbatim CLAUDE.md / project-memory contradiction. Single-persona uncorroborated resets are reclassified to CRITICAL HARD findings. Surface to user; do not auto-resolve.

**`--draft` mode:** Plan-lint, Concern-lint, Ground-truth audit, and Self-prosecution + Imagined-Implementer are skipped; sidecar marked `authoring_mode: "draft"` and `verdict: "DRAFT_EMITTED"`; engineering-plan written to disk with NO `Status:` frontmatter. The sidecar's `authoring_mode: "draft"` field is the load-bearing draft signal that `/engineering-plan-review-v2` consults. Per-chunk plan authoring (`/plan-author`) is gated on the engineering-plan-author sidecar's verdict being `CLOSED`, so `DRAFT_EMITTED` does NOT unblock `/plan-author` — authoring without `--draft` produces a hardened plan (Imagined-Implementer runs and surfaces IMPLEMENTABILITY_GAPs); the session agent then binds any gaps in `decisions.md` and marks the plan CLOSED before chunk authoring. The author is not re-run to harden or to close.

---

## Relationship to sister skills

- **Upstream: `/brief-author`.** The engineering-plan-author reads the brief and the brief-author sidecar. A brief layer change cascades; warm-mode carry-forward includes the brief-side `recently_resolved_blockers`.
- **Above the brief: `/spec-author` and `/spec-review`.** They own the parent spec, its `## Decomposition`, and its decisions logs. Grounding here stays parental — the engineering plan is grounded in its brief and never reads `vision.md` — but the spec reaches this layer through the brief's `**Spec:**` header on three channels: the Coverage table the no-annexation check tests chunks against, the seam predicates that place a boundary-adjacent chunk, and the Active `Status: bound` boundary calls in its decisions logs, which bind **transitively** here and are never re-litigated. A boundary this plan cannot honor, and any contradiction originating in the spec rather than in the brief, goes back to that pair as `OPEN_QUESTION` / `SPEC_AMENDMENT_NEEDED`. This skill never edits the spec or its logs, and never routes past the spec to vision.
- **Downstream: `/plan-author`.** The engineering-plan-author's CLOSED verdict unblocks per-chunk plan authoring. APPROVED does NOT (per the three-state semantic).
- **Reviewer: `/engineering-plan-review-v2`.** The immediate next step after this author's first draft. Its `recently_resolved_blockers` are warm-mode constraints here. Author-side findings that match a reviewer-side blocker class share the class (BRIEF_NONGOAL_TRESPASS, BRIEF_GOAL_UNDELIVERED, SURFACE_PARITY_GAP, GOAL_VERIFICATION_GAP, BRIEF_AMENDMENT_NEEDED, SPEC_AMENDMENT_NEEDED, CHUNK_SURFACE_EXCESS, FEATURE_SURFACE_EXCESS, IMPLEMENTABILITY_GAP, UNCORROBORATED_RESET, STABLE_DISAGREEMENT, OPEN_QUESTION, FIX_INTRODUCED_PREMISE_INVERSION, STRUCTURAL_LINT_FAILED, REPO_STATE_DRIFT), so the two gates exclude the same set.
