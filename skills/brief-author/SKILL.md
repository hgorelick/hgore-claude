---
name: brief-author
description: Authoring-side sister to `/brief-review-v2`. Produces or rewrites a feature's `brief.md` (the upstream source-of-truth that the engineering plan and chunk plans descend from) with ground-truth verification and self-prosecution applied at write time, not review time. Catches brief-layer hallucinations (invented user populations, contradicted Goals, scope creep, banned non-goal patterns) before they cascade downstream. Persists a sidecar at `~/.claude/cache/author-state/<feature>__brief.json` recording every claim verified/dropped/softened. On HIGH+ residuals the partial draft is written to disk with frontmatter `Status: needs-user-input` plus a `## Pending blockers` section; the user resolves and re-invokes with the partial draft as warm-mode anchor so re-generation cost is paid once. Surfaces blockers as OPEN_QUESTION. Sister to `/engineering-plan-author` (engineering-plan layer) and `/plan-author` (chunk-plan layer).
---

# Brief author

Produces or rewrites `features/<feature>/brief.md` with the same prosecution rigor `/plan-review-v2` applies, but front-loaded at write time.

The brief is the highest-leverage artifact in the feature lifecycle: every downstream artifact (engineering plan, chunk plans, code) descends from it. A brief that contradicts its own Goals, invents a user population, or smuggles a Non-goal-violating Goal will cascade five rounds of review machinery to surface — and the surface itself doesn't repair the brief, only the descendants.

## Inputs

- `$ARGUMENTS` (optional):
  - `<feature>` — the feature directory under `features/`. If absent, infer from the current working directory or ask the user.
  - `--draft` — quick-exploration mode; skip ground-truth and self-prosecution; emit a sidecar marked `authoring_mode: "draft"` for the user to harden later.
  - `--rewrite` — assume `features/<feature>/brief.md` exists and you are rewriting it; warm-mode carry-forward applies.

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
  ├─ Read review-state at ~/.claude/cache/review-state/<feature>__engineering-plan.json (if exists — warm carry-forward at brief layer)
  └─ Determine cold vs warm mode

Source ingest (deterministic; ~30 seconds)
  ├─ Read spec.md
  ├─ Read context/specs/*.md (category specs that bear on this feature)
  ├─ Read CLAUDE.md
  ├─ Read MEMORY.md + relevant project memory files
  ├─ Read existing brief.md (if --rewrite or warm mode)
  └─ Extract project invariants the brief MUST honor (no non-Latin names, no existing-users assumptions, etc.)

Draft (LLM judgment; main thread)
  ├─ Mirror section template: Problem / Solution / Goals / Non-goals / User-facing changes / Open questions
  ├─ Mark each Goal with "Verified by:" pointing at the metric or sub-feature that proves it ships
  ├─ Surface every "Open questions" entry the upstream artifacts left unresolved
  └─ Emit first draft to in-memory buffer (NOT yet written to disk)

Ground-truth audit  (`_author-common/ground-truth-protocol.md`; skipped in --draft mode)
  ├─ Tokenize draft for V1-V5 claims
  │   (V1 anchors mostly absent at brief layer; V4 cross-doc + V5 external-API dominate)
  ├─ Verify each claim against spec.md / project memory / category-spec / external API client
  ├─ Apply outcomes (verified / softened / corrected / dropped / restructured)
  └─ Write sidecar audit log

Self-prosecution and emission  (`_author-common/self-prosecution-protocol.md`; skipped in --draft mode)
  ├─ Spawn product + ai-development persona agents in parallel
  │   (each runs the premise-interrogation sub-pass + the standard-prosecution sub-pass)
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
  "introduced_identifiers": [],
  "ground_truth_log": [...],
  "self_prosecution_findings": [...],
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

The `prior_blockers` / `recently_resolved_blockers` shape mirrors the reviewer state schema in `~/.claude/cache/review-state/`. This intentional uniformity lets `/explain-blockers` parse author-state with the same parser. Only HIGH+ self-prosecution residuals land in `prior_blockers` — LOW residuals under the polish floor stay in `authoring_residual` and are never surfaced as blockers.

If `last_brief_sha256` matches the SHA of `features/<feature>/brief.md` on disk and the file's mtime is recent, the brief has not changed since the last invocation; the sidecar's `ground_truth_log` is still authoritative. If the SHA differs (the user edited the brief manually) or the file is older than the sidecar implies, treat as a fresh authoring round (cold w.r.t. ground-truth, warm w.r.t. carry-forward).

Also read the engineering-plan reviewer's state at `~/.claude/cache/review-state/<feature>__engineering-plan.json` if it exists. The engineering-plan reviewer's `recently_resolved_blockers` list may include brief-layer items the user already arbitrated (BRIEF_AMENDMENT_NEEDED). These are warm-mode carry-forward at the brief layer: re-introducing a Goal/Non-goal the user already removed is the worst thrash form.

---

## Source ingest

Read in this order. Read once into context; do not re-read in later stages.

1. `spec.md` (project root) — the product master spec. Brief Goals must trace to spec sections; brief Non-goals must not contradict spec capabilities.
2. `context/specs/*.md` — category-specific specs. For book features, read `context/specs/clean-book-database-spec.md` if present.
3. `CLAUDE.md` — project conventions, banned patterns, business rules. Pay attention to: the 5-item threshold, score-rounding rule, watchlist auto-remove, block-mutual-unfollow, public-rankings invariant, multi-category architecture rules.
4. `MEMORY.md` + every memory file under `~/.claude/projects/-Users-hgorelick-Documents-ozzi-app/memory/` whose `description` field hints at relevance to this feature.
5. Existing `features/<feature>/brief.md` (warm/rewrite modes only) + `features/<feature>/decisions.md` (every dated entry; brief-layer decisions live there). The brief.md may be in `Status: needs-user-input` state from a previous invocation — that partial draft (with the `## Pending blockers` section appended) IS the canonical warm-mode anchor; the next Draft stage starts from the partial body and only re-emits sections affected by the user's blocker resolutions.

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

**Created:** <YYYY-MM-DD>
**Last updated:** <YYYY-MM-DD>

## Problem

<One or more paragraphs. State the user-visible failure mode this feature exists to fix. Quantify cohorts where possible (the "~400-450 prolific authors" pattern). Tie to spec.md sections that already named the problem.>

## Solution

<One or more paragraphs. The shape of the fix at the user-visible level — not the implementation. Name the cohorts/populations the solution operates on. End with the load-bearing tradeoff (e.g., "Linking has to be right or not done at all").>

## Goals

- **<Goal name>.** <Verifiable success criterion. Each Goal is something a downstream chunk can claim "Verified by" against.>
- ...

## Non-goals

- **<Non-goal>.** <Why this isn't being done. Explicit, not implied. Each Non-goal is a bound to scope creep.>
- ...

## User-facing changes

<What the user sees post-feature. May be "ships a database snapshot, no live UX changes" for backfill features. Concrete and present-tense.>

## Open questions

None. | <list of unresolved questions in question form, NOT statements>
```

### Drafting rules

- **Each Goal is verifiable.** "Disambiguation primitive shared across the codebase" is verifiable; "great UX" is not. The Goal's verifiability is the foundation for the engineering plan's `Verified by` column.
- **Each Non-goal is real, not aspirational.** "No paid tier" is a real Non-goal if the feature could plausibly include one. "No ML-driven recommendation" is a real Non-goal if the feature could plausibly include it. Don't pad with implausible Non-goals.
- **Open questions are questions.** "How do we handle X?" is an open question. "We need to figure out X" is a statement and should be either a Goal (if it's required to ship) or a Non-goal (if it's deferred).
- **Mirror existing briefs in the same feature family.** Read `features/*/brief.md` and copy section ordering, tone, and density. Do not invent a new brief shape.
- **No persona-attribution headers.** The brief is one document with one voice (per `_review-common/principles.md` plan-style rules).
- **No review attributions.** No "Architecture review found…" — those belong in `decisions.md`.
- **No historical comparisons.** No "the original brief said X but actually Y" — describe the current state only.

---

## Ground-truth audit

Apply `_author-common/ground-truth-protocol.md`. At the brief layer, the dominant claim classes are:

- **V4 (Cross-document)** — every reference to spec.md, category-spec, project memory, decisions.md, or CLAUDE.md.
- **V5 (External-API)** — claims about what TMDB / Open Library / Google Books / Anthropic SDK *can do at the API level* (not implementation detail). Verify against the project's wrapper code.
- **V3 (Constraint)** — claims about cohort counts ("~400-450 prolific authors"), database state ("~841 already-pre-hydrated film/TV Persons"). Verify against the most recent migration / seed data / database query the project supports.

V1 (path:line) and V2 (identifier) claims are RARE at the brief layer. If the draft has them, the brief has drifted into engineering-plan territory — file as a self-prosecution finding (drift class).

After verification, emit the sidecar audit log even if the draft is rejected at the Self-prosecution stage; the user benefits from seeing what was verified vs dropped.

---

## Self-prosecution and emission

Spawn two persona agents in parallel using the template in `_author-common/self-prosecution-protocol.md`:

- **product** — prosecutes Goals/Non-goals coherence, scope creep, contradicted spec, banned project assumptions ("existing users").
- **ai-development** — prosecutes plan-quality at the brief layer (verifiability of Goals, banned patterns, drift toward engineering-plan detail).

Active critical pairs: universal pairs from `_review-common/critical-pairs.md` only. PR/chunk/engineering-plan-specific pairs do not apply at the brief layer.

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
- **APPROVED** → write `features/<feature>/brief.md` with NO `Status:` frontmatter (the binary-Status convention reserves `Status:` for the mid-cycle signal only); persist sidecar; print verdict. If the prior on-disk file had `Status: needs-user-input` from a previous invocation, this emission removes that line along with the `## Pending blockers` section.
- **NEEDS_USER_INPUT** → write `features/<feature>/brief.md` with frontmatter `Status: needs-user-input` AND an inline `## Pending blockers` section listing each unresolved finding verbatim from the verdict; persist sidecar with `verdict: "NEEDS_USER_INPUT"`; print verdict including the unresolved blockers. The next `--rewrite` invocation reads the partially-improved draft as warm-mode source-of-truth (re-generation cost is paid once, not on every iteration). Downstream skills (`/engineering-plan-author`, `/engineering-plan-review-v2`, `/brief-review-v2`) hard-refuse against `Status: needs-user-input` briefs — the upstream is mid-cycle by design.
- **DRAFT_EMITTED** → write `features/<feature>/brief.md` with NO `Status:` frontmatter; persist sidecar with `verdict: "DRAFT_EMITTED"` AND `authoring_mode: "draft"` (the load-bearing draft signal); print verdict noting the draft is hardened-pending and instructing the user to re-invoke without `--draft` once the prose stabilizes. Reviewer skills consult the sidecar's `authoring_mode` field to detect draft mode and warn in their verdicts; `/execute-plan` consults it and refuses (implementing a draft plan ships hallucinations).

### Pending-blockers section (NEEDS_USER_INPUT mode)

On NEEDS_USER_INPUT, the on-disk brief gets two additions beyond the partial draft body:

1. **Frontmatter `Status: needs-user-input`** is added (or replaces a prior Status value if any). The APPROVED-emission convention is no `Status:` field; the NEEDS_USER_INPUT path adds the field as the only valid Status value.
2. **`## Pending blockers` section appended at the end of the file**, with verbatim bullets from the verdict's `### Blockers` block:

   ```markdown
   ## Pending blockers

   <!-- This section is auto-managed by /brief-author. Resolve each blocker below, then re-invoke `/brief-author --rewrite <feature>`. The next Draft stage reads this file as warm-mode source-of-truth and only re-emits prose affected by your resolutions; the unaffected sections stay byte-stable. Downstream skills (`/engineering-plan-author`, `/engineering-plan-review-v2`) refuse to run against this brief until it lands at APPROVED. -->

   - [<BLOCKER_CLASS>] <span / section> — <one-line summary>; <actionable resolution path>.
   - ...
   ```

On the subsequent `--rewrite` invocation that lands at APPROVED, the entire `## Pending blockers` section AND its HTML comment are removed, AND the `Status: needs-user-input` line is removed (the APPROVED emission convention is no `Status:` field). If the next invocation is still NEEDS_USER_INPUT, the `## Pending blockers` section is rewritten with the new blocker set (replaced, not appended to — stale blockers don't accumulate); the `Status: needs-user-input` line stays.

---

## Hard rules

- **Stage order is fixed.** Source ingest before Draft. Ground-truth audit before Self-prosecution and emission. No stage can be skipped except Ground-truth audit and Self-prosecution in `--draft` mode.
- **In `ship` mode, the draft is written to disk after Self-prosecution and emission closes regardless of verdict; the on-disk frontmatter `Status:` field gates downstream skills via the binary mid-cycle convention.** APPROVED writes with NO `Status:` field (downstream skills consume the brief normally). NEEDS_USER_INPUT writes the partially-improved draft with `Status: needs-user-input` and an inline `## Pending blockers` section — downstream skills (`/brief-review-v2`, `/engineering-plan-author`, `/engineering-plan-review-v2`) hard-refuse against `Status: needs-user-input` briefs because the upstream is mid-cycle by design; the next `--rewrite` invocation reads the partial draft as warm-mode source-of-truth and only re-emits sections affected by the user's blocker resolutions. In `--draft` mode the user has explicitly opted out of the safety net by passing the flag; the draft IS written to disk with NO `Status:` field, the sidecar records `authoring_mode: "draft"` AND `verdict: "DRAFT_EMITTED"`, and reviewers consult the sidecar to detect draft mode and warn (rather than refuse). Re-invoking without `--draft` runs Ground-truth audit and Self-prosecution against the on-disk draft to harden it.
- **Sidecar is always written.** Even on NEEDS_USER_INPUT verdicts, the sidecar persists so the next invocation has full context. (In NEEDS_USER_INPUT, the brief on disk does not change; only the sidecar.)
- **Banned content categories** (per `_review-common/principles.md` plan style rules + `_author-common/principles.md` banned authoring rationalizations):
  - Addendum sections, review attribution, historical comparison, persona-attribution headers, conflict-resolution metadata.
  - "Should exist" / "probably exists" / "the spec implies" without a verbatim quote.
  - Goal/Non-goal pairs that contradict each other or contradict spec.md.
  - Cohort counts without a verifiable source.
- **Carry-forward respect.** Warm mode: a brief edit that re-introduces a Goal/Non-goal/user-cohort the user removed in a prior invocation is `FIX_INTRODUCED_PREMISE_INVERSION` against the brief itself. Surface to the user; do not emit.
- **Self-prosecution is mandatory for `ship` mode.** `--draft` skips it; `ship` does not.
- **Source ingest before draft.** A draft written without reading the upstream spec / memory / existing brief is not a brief — it's fan fiction. The Source-ingest stage is hard-blocking.

---

## Edge cases

**Sidecar absent, brief.md absent (cold start, fresh feature):** Skill is in cold mode. State load returns empty. Source ingest reads spec/memory/CLAUDE only. Draft writes from scratch. Ground-truth audit and Self-prosecution run normally.

**Sidecar absent, brief.md present (manual edit since last invocation, OR first invocation):** Read brief.md as the warm-mode source-of-truth. Treat its current content as the "before" state for the rewrite. No carry-forward (no sidecar history); but the current brief is itself a constraint.

**Sidecar present, brief.md absent (someone deleted the brief):** Treat as cold start at the disk level; consult sidecar's history for what the user had previously arbitrated, but write a fresh draft. Surface in the verdict that the prior brief was deleted.

**Sidecar present, brief.md present, SHA matches:** No-op invocation if `$ARGUMENTS` doesn't include `--rewrite` or new constraint; print "no changes; brief is in the last APPROVED state" and exit.

**Sidecar present, brief.md present, SHA differs (manual edit):** The user's manual edit takes precedence. Reset the sidecar's `ground_truth_log` to empty; re-run from Source ingest. Carry-forward of `recently_resolved_blockers` still applies.

**`--draft` mode:** Ground-truth audit and Self-prosecution are skipped. Sidecar is written with `authoring_mode: "draft"` and `verdict: "DRAFT_EMITTED"`. The brief IS written to disk with NO `Status:` frontmatter so the user can iterate on the file directly. The sidecar's `authoring_mode: "draft"` field is the load-bearing signal that downstream skills consult — `/brief-review-v2` proceeds with full prosecution but surfaces a draft warning in its verdict; `/engineering-plan-author` and `/engineering-plan-review-v2` warn-not-block when the upstream brief's sidecar reports draft mode. The verdict prose surfaces the hardening-pending state and instructs the user to re-invoke without `--draft` once the prose stabilizes.

**Engineering-plan-review state has BRIEF_AMENDMENT_NEEDED unresolved:** Warm-mode carry-forward surfaces this; the brief author MUST address the amendment in the new draft, not just touch surrounding prose. If the amendment isn't addressable from this skill's vantage (requires user decision), surface as `OPEN_QUESTION`.

**Spec.md missing:** Refuse to run. The brief is the bridge between spec.md and engineering-plan.md; without a spec, the brief has no anchor. Print: "spec.md not found; the brief layer requires a spec source-of-truth. Create spec.md or invoke from the project root."

**Project memory absent (no `~/.claude/projects/<project>/memory/MEMORY.md`):** Run with degraded ground-truth coverage. Print warning. The product persona's prosecution will be weaker (fewer invariants to enforce), but the Ground-truth audit still runs against spec/CLAUDE.

---

## Relationship to sister skills

- **`/engineering-plan-author`** consumes the brief written here. The engineering-plan-author's Source-ingest stage reads `features/<feature>/brief.md` and the brief-author's sidecar (introduced_identifiers, authoring_residual). The engineering-plan-author's product-persona prosecution sub-pass cross-checks the engineering plan's chunks against the brief Goals.
- **`/plan-author`** indirectly consumes the brief (via the engineering plan). Brief edits cascade through the engineering-plan-review's BRIEF_AMENDMENT_NEEDED class.
- **`/engineering-plan-review-v2`** prosecutes the brief at the engineering-plan layer (premise interrogation §brief-environment sub-pass). Findings raised there belong upstream — feeding back into the next `/brief-author` invocation's State-load stage via the warm-mode carry-forward.

The brief is the highest-leverage artifact; this skill exists to make it the cleanest.
