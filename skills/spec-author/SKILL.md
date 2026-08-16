---
name: spec-author
description: Writes or rewrites a project's `spec.md` — the root source-of-truth every brief, engineering plan, and chunk plan descends from — applying ground-truth verification and self-prosecution at write time rather than review time. Run once per cycle, then `/spec-review`. Sister to `/brief-author`, `/engineering-plan-author`, `/plan-author`.
user-invocable: true
---

# Spec author

Produces or rewrites a project's `spec.md` with the same prosecution rigor `/spec-review` applies, but front-loaded at write time.

The spec is the **root** of the artifact lifecycle: every downstream artifact — every brief, engineering plan, chunk plan, and line of code — descends from it. A spec that contradicts its own invariants, invents a capability, leaves a load-bearing term undefined, or smuggles in a rule that contradicts the project's bound-invariant ledger will cascade through *every* feature, and the downstream review machinery repairs the descendants, never the spec itself. This skill makes the spec the cleanest artifact in the project.

The canonical spec shape and drafting rules live in `~/.claude/skills/_spec-common/spec-format.md` — read it before drafting. It is project-agnostic; this skill applies it to whatever project it is invoked in.

## Inputs

- `$ARGUMENTS` (optional):
  - `<path>` — the spec file to author. Defaults to `spec.md` at the repository root (`git rev-parse --show-toplevel`), or `spec.md` in the current working directory when not in a git repo.
  - `--draft` — quick-exploration mode; skip ground-truth and self-prosecution; emit a sidecar marked `authoring_mode: "draft"` (unhardened by choice; downstream reviewers warn rather than refuse).

**The author runs once per cycle.** It produces the first draft; the next step in the cycle is to run `/spec-review`, and the session agent then applies its findings — plus your blocker resolutions — directly to `spec.md`. The author is not re-invoked to apply changes. There is no `--rewrite` flag. When `spec.md` already exists or its author sidecar is present, invoke `/spec-author` again only for an explicit clean-slate re-author (ask in plain language); that fresh run treats the existing spec and any prior review state as carry-forward constraints — an invariant / feature area / non-goal the user already removed is not re-introduced.

**`spec.md` being absent is normal.** Unlike the downstream skills (which hard-refuse without a spec to anchor against), this skill *creates* the spec. A missing `spec.md` is the cold-start case, not an error.

## Sidecar location

`~/.claude/cache/author-state/<project>__spec.json`, where `<project>` is the basename of the repository root (or cwd when not a git repo) — e.g. `acme-app__spec.json`, `feature-factory__spec.json`. Same directory as the brief/engineering-plan/chunk author sidecars; the spec is keyed on the **project**, not a feature. `/spec-review` consults this sidecar to skip re-prosecuting claims the author already verified.

---

## Workflow

```
State load (deterministic; ~5 seconds)
  ├─ mkdir -p ~/.claude/cache/author-state (Write does NOT auto-create parents)
  ├─ Derive <project> from git toplevel (or cwd) basename
  ├─ Read sidecar at ~/.claude/cache/author-state/<project>__spec.json (if exists)
  ├─ Read review-state at ~/.claude/cache/review-state/<project>__spec.json (if exists — warm carry-forward)
  └─ Determine cold vs warm mode

Source ingest (deterministic; ~30 seconds)
  ├─ Read ~/.claude/skills/_spec-common/spec-format.md (the format being applied)
  ├─ Read CLAUDE.md (project conventions + bound invariants)
  ├─ Read MEMORY.md + relevant project memory files (bound invariants the spec must honor)
  ├─ Read existing spec.md (warm mode — when the file or sidecar already exists)
  ├─ Read project design docs (docs/*, context/*, architecture/decision records) where they exist
  ├─ Read external-API wrapper code for any third-party service the product integrates (for V5 claims)
  └─ Build the invariants ledger the spec MUST honor (the prosecution target for the product persona)

Draft (LLM judgment; main thread)
  ├─ Mirror the section template in _spec-common/spec-format.md (core + applicable optional sections)
  ├─ State each invariant as a checkable condition; define each load-bearing term before use
  ├─ Name the domain for every quantified invariant / feature area
  ├─ Surface unresolved product questions in ## Open questions (or `None.`)
  └─ Emit first draft to in-memory buffer (NOT yet written to disk)

Ground-truth audit  (_author-common/ground-truth-protocol.md; skipped in --draft mode)
  ├─ Tokenize draft for V1-V5 claims
  │   (V4 internal-cross-section + invariant-ledger conformance and V5 external-API dominate;
  │    V3 data/constraint reality; V1/V2 path/identifier are RARE → drift if present)
  ├─ Verify each claim against the invariant ledger / design docs / external-API wrappers / data state
  ├─ Apply outcomes (verified / softened / corrected / dropped / restructured)
  └─ Write sidecar audit log

Self-prosecution and emission  (_author-common/self-prosecution-protocol.md; skipped in --draft mode)
  ├─ Spawn product + architecture persona agents in parallel
  │   (each runs the premise-interrogation sub-pass + the standard-prosecution sub-pass)
  ├─ Consolidate findings; apply auto-fixable
  ├─ Run post-fix premise verification on orchestrator-rewritten prose
  ├─ Classify residuals (STABLE_DISAGREEMENT, OPEN_QUESTION, FIX_INTRODUCED_PREMISE_INVERSION)
  └─ Decide emission:
      ├─ APPROVED: write spec.md with NO `Status:` frontmatter + persist sidecar + render verdict
      └─ NEEDS_USER_INPUT: write partial draft with `Status: needs-user-input` and inline `## Pending blockers` + persist sidecar + render verdict
```

In `--draft` mode the Ground-truth audit and Self-prosecution stages are skipped; the draft is emitted directly with `verdict: "DRAFT_EMITTED"`.

---

## State load

Derive `<project>` first: `git rev-parse --show-toplevel` basename, else cwd basename.

Read the sidecar if it exists. Schema:

```json
{
  "project": "<project>",
  "artifact_path": "spec.md",
  "authoring_mode": "ship | draft",
  "ground_truth_at": "<ISO 8601 UTC>",
  "self_prosecution_at": "<ISO 8601 UTC>",
  "invocation_number": <int>,
  "last_spec_sha256": "<hex>",
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
  "exclusion_challenges": [...],
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

`DRAFT_EMITTED` is written when the user invokes with `--draft` (ground-truth + self-prosecution skipped). The reviewer (`/spec-review`) treats `DRAFT_EMITTED` as "intentionally unhardened" and warns rather than re-prosecutes.

`prior_blockers` / `recently_resolved_blockers` mirror the reviewer state schema in `~/.claude/cache/review-state/`. Only HIGH+ self-prosecution residuals land in `prior_blockers`; LOW residuals under the polish floor stay in `authoring_residual`.

If `last_spec_sha256` matches the SHA of `spec.md` on disk, the spec is unchanged since the last invocation. If it differs (the user edited the spec manually), treat as a fresh authoring round (cold w.r.t. ground-truth, warm w.r.t. carry-forward).

Also read the reviewer's state at `~/.claude/cache/review-state/<project>__spec.json` if it exists — its `recently_resolved_blockers` may include spec-layer items the user already arbitrated. Re-introducing an invariant / feature area / non-goal the user already removed is the worst thrash form.

---

## Source ingest

Read in this order. Read once into context; do not re-read in later stages.

1. `~/.claude/skills/_spec-common/spec-format.md` — the format being applied (section template, drafting rules, claim emphasis, persona set).
2. `CLAUDE.md` (project root, and any nested `CLAUDE.md`) — project conventions and bound invariants. The spec must honor these.
3. `MEMORY.md` + every memory file under `~/.claude/projects/<project>/memory/` whose `description` hints at relevance — bound invariants and project assumptions the spec must honor.
4. Existing `spec.md` (when re-authoring). The current spec content is a carry-forward constraint. A mid-cycle `Status: needs-user-input` spec is resolved by the session agent applying blocker resolutions directly, not by re-running this skill.
5. Project design docs where they exist — `docs/*`, `context/*`, architecture or decision records. Grounding the spec must stay consistent with.
6. External-API wrapper code for each third-party service the product integrates (e.g. `src/lib/<service>.ts`) — the canonical contract for V5 claims.

After reading, build an **invariants ledger** — the facts the spec MUST honor, drawn from `CLAUDE.md` + project memory. Examples vary per project (an app: business rules, banned data patterns, "no existing users yet"; an infra product: isolation guarantees, safety preconditions, autonomy boundaries). The ledger is the prosecution target for the Self-prosecution stage's product persona.

**There is no upstream spec to anchor against — the spec IS the anchor.** Unlike the brief layer (which traces Goals to spec sections), the spec's grounding is *internal* (cross-section consistency), the *invariant ledger* (CLAUDE.md + memory), *design docs*, and *external reality* (APIs, data state). Do not look for an upstream product document above the spec; there isn't one.

---

## Draft

Mirror the section template in `~/.claude/skills/_spec-common/spec-format.md` — the universal core (Overview, Domain model & core concepts, Invariants & business rules, Feature areas, Non-goals & scope bounds, Glossary) plus the optional sections (Roadmap / milestones, Analytics & observability, External integrations) that apply to this project type. Omit optional sections that do not apply; do not stub them.

### Drafting rules

Apply the drafting rules in `_spec-common/spec-format.md`. The load-bearing ones:

- **Each invariant is a checkable condition**, not an aspiration — the foundation for a brief Goal to trace to it.
- **Define each load-bearing term before use** (Domain model / Glossary).
- **WHAT, not HOW** — product rules and conceptual structure, never file paths / schema columns / function signatures / chunk decomposition. Precision about a *product rule* (a formula, a threshold) is not implementation creep; a path / identifier / SQL fragment is.
- **No internal contradiction** — §Invariants, §Feature areas, §Domain model must agree.
- **Honor the invariant ledger** — never silently override a bound `CLAUDE.md` / memory invariant.
- **Name the domain** for any quantified invariant / feature area.
- **Each Non-goal is a real scope kill**, not a platitude.
- **Mirror existing project specs in tone and density** where a prior spec exists. Do not invent a new shape.
- **One voice, forward-looking** — no addendum / review-attribution / historical-comparison / persona-attribution / conflict-resolution content (plan style rules, `_review-common/principles.md`).

---

## Ground-truth audit

Apply `_author-common/ground-truth-protocol.md`. At the spec layer the dominant claim classes are:

- **V4 (Cross-document)** in two forms:
  - **Internal cross-section consistency** — a claim in one section that references or depends on another (e.g. §Feature areas leaning on a §Invariants rule, §Invariants leaning on a §Domain model definition). Verify the referenced section says what the claim assumes.
  - **Invariant-ledger conformance** — every spec rule that restates or depends on a `CLAUDE.md` / project-memory invariant. Verify the spec does not contradict the bound invariant.
- **V5 (External-API)** — claims about what a third-party service *can do at the API level*. Verify against the project's wrapper code (canonical), provider docs (secondary).
- **V3 (Constraint/data)** — cohort counts and data-state claims ("~N books", "M existing X"). Verify against the most recent migration / seed / supported query.

V1 (path:line) and V2 (identifier) claims are RARE at the spec layer. If the draft has them, the spec has drifted into engineering-plan territory — file as a self-prosecution finding (drift class), not a verified anchor.

After verification, emit the sidecar audit log even if the draft is rejected at Self-prosecution; the user benefits from seeing what was verified vs dropped.

---

## Self-prosecution and emission

Spawn two persona agents in parallel using the template in `_author-common/self-prosecution-protocol.md`:

- **product** — prosecutes invariant/feature-area coherence, scope, internal contradictions, and conflicts with the bound-invariant ledger (CLAUDE.md / project memory).
- **architecture** — prosecutes internal consistency of the committed system, domain-model soundness, and whether the invariants + feature areas form a buildable, non-self-contradictory whole.

Active critical pairs: universal pairs from `_review-common/critical-pairs.md` only (`P-CLASS-SCOPE`, `P-FULL-FILE`). The spec-specific `P-SPEC-*` pairs are a review-stage filter, defined in `/spec-review`.

After consolidation, run post-fix premise verification on any orchestrator-rewritten prose. Classify residuals.

### Verdict template

```markdown
# Spec authoring verdict — spec.md (<project>)

**Mode:** cold | warm
**Authoring mode:** ship | draft
**Round:** <invocation_number>
**Last spec sha:** <hex>

## Ground-truth audit
**Claims total:** <N>
**Verified:** <V>  **Softened:** <S>  **Corrected:** <C>  **Dropped:** <D>  **Restructured:** <R>  **Skipped (carve-out):** <K>

## Self-prosecution
**Personas:** product, architecture
**Premise interrogation:** <product=passed/failed>, <architecture=passed/failed>
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
- **NEEDS_USER_INPUT** when authoring mode is `ship` AND any APPROVED condition fails.
- **DRAFT_EMITTED** when authoring mode is `--draft`.

Disk-write semantics:
- **APPROVED** → write `spec.md` with NO `Status:` frontmatter; persist sidecar; print verdict. If the on-disk file still carries `Status: needs-user-input` and a `## Pending blockers` section, this emission removes that line and the section. **Next step:** run `/spec-review` to prosecute the draft.
- **NEEDS_USER_INPUT** → write `spec.md` with frontmatter `Status: needs-user-input` AND an inline `## Pending blockers` section listing each unresolved finding verbatim; persist sidecar with `verdict: "NEEDS_USER_INPUT"`; print verdict including the unresolved blockers. The session agent then applies your blocker resolutions directly to `spec.md` and removes the `Status:` line + `## Pending blockers` section once the blockers clear — the author is not re-invoked. Downstream skills that anchor on the spec treat a `Status: needs-user-input` spec as mid-cycle.
- **DRAFT_EMITTED** → write `spec.md` with NO `Status:` frontmatter; persist sidecar with `verdict: "DRAFT_EMITTED"` AND `authoring_mode: "draft"`; print verdict noting the draft is unhardened by choice (`--draft` skipped Ground-truth audit and Self-prosecution).

### Pending-blockers section (NEEDS_USER_INPUT mode)

On NEEDS_USER_INPUT, the on-disk spec gets two additions beyond the partial draft body:

1. **Frontmatter `Status: needs-user-input`** (or replaces a prior Status value).
2. **`## Pending blockers` section appended at the end**, with verbatim bullets from the verdict's `### Blockers` block:

   ```markdown
   ## Pending blockers

   <!-- This section is auto-managed by /spec-author. Resolve each blocker below; the session agent
   then applies your resolutions directly to this file and removes this section along with the
   `Status: needs-user-input` line — the author skill is not re-run. -->

   - [<BLOCKER_CLASS>] <span / section> — <one-line summary>; <actionable resolution path>.
   - ...
   ```

Once the session agent has applied every resolution, it removes the entire `## Pending blockers` section AND its HTML comment, AND the `Status: needs-user-input` line. While any blocker remains unresolved, the section keeps only the still-open blockers (replaced, not appended) and the `Status: needs-user-input` line stays.

---

## Hard rules

- **Stage order is fixed.** Source ingest before Draft. Ground-truth audit before Self-prosecution and emission. No stage skipped except Ground-truth audit and Self-prosecution in `--draft` mode.
- **In `ship` mode, the draft is written to disk after Self-prosecution closes regardless of verdict; the on-disk `Status:` field gates downstream consumption via the binary mid-cycle convention.** APPROVED writes with NO `Status:` field. NEEDS_USER_INPUT writes the partial draft with `Status: needs-user-input` and `## Pending blockers`. In `--draft` mode the draft IS written with NO `Status:` field; the sidecar records `authoring_mode: "draft"` and `verdict: "DRAFT_EMITTED"`.
- **Sidecar is always written.** Even on NEEDS_USER_INPUT, the sidecar persists so downstream skills and any later clean-slate re-author have full context.
- **Never silently override the invariant ledger.** A spec claim contradicting a bound `CLAUDE.md` / project-memory invariant is surfaced as `OPEN_QUESTION` (amend the spec, or amend the ledger out-of-band) — the spec author never auto-edits `CLAUDE.md` or memory.
- **Banned content categories** (per `_review-common/principles.md` § Plan style rules + `_author-common/principles.md`): addendum sections, review attribution, historical comparison, persona-attribution headers, conflict-resolution metadata; "should exist" / "the docs imply" without a verbatim quote; invariants that contradict each other or the ledger; cohort/data counts without a verifiable source; implementation creep (path:line, schema columns, SQL fragments, function signatures).
- **Carry-forward respect.** Warm mode: a spec edit that re-introduces an invariant / feature area / non-goal the user removed in a prior invocation is `FIX_INTRODUCED_PREMISE_INVERSION` against the spec itself. Surface; do not emit.
- **Self-prosecution is mandatory for `ship` mode.** `--draft` skips it; `ship` does not.
- **Source ingest before draft.** A spec drafted without reading `CLAUDE.md` / memory / existing spec / design docs is fan fiction. Source ingest is hard-blocking.

---

## Edge cases

**Sidecar absent, spec.md absent (cold start, fresh project):** Cold mode. State load returns empty. Source ingest reads CLAUDE.md / memory / design docs (whatever exists). Draft writes from scratch. Ground-truth audit and Self-prosecution run normally. This is the expected first-invocation path — a missing spec is not an error.

**Sidecar absent, spec.md present (manual edit since last invocation, OR first invocation on a hand-written spec):** Read spec.md as the warm-mode source-of-truth. Treat its current content as the "before" state. No carry-forward (no sidecar history); the current spec is itself a constraint.

**Sidecar present, spec.md absent (someone deleted the spec):** Treat as cold start at the disk level; consult the sidecar's history for prior arbitrations, but write a fresh draft. Surface in the verdict that the prior spec was deleted.

**Sidecar present, spec.md present, SHA matches:** No-op when the request adds no new constraint or instruction; print "no changes; spec is in the last APPROVED state" and exit. A plain-language ask to rewrite or change the spec IS a new instruction and proceeds in warm mode.

**Sidecar present, spec.md present, SHA differs (manual edit):** The user's manual edit takes precedence. Reset the sidecar's `ground_truth_log` to empty; re-run from Source ingest. Carry-forward of `recently_resolved_blockers` still applies.

**`--draft` mode:** Ground-truth audit and Self-prosecution skipped. Sidecar written with `authoring_mode: "draft"` and `verdict: "DRAFT_EMITTED"`. The spec IS written to disk with NO `Status:` frontmatter. `/spec-review` proceeds with full prosecution but surfaces a draft warning.

**`CLAUDE.md` absent:** Run with degraded ground-truth coverage. Print a warning. The product persona's prosecution is weaker (fewer ledger invariants), but internal-consistency and external-API verification still run.

**Project memory absent (no `~/.claude/projects/<project>/memory/MEMORY.md`):** Run with degraded coverage. Print a warning. The invariant ledger is built from `CLAUDE.md` alone.

**Design docs contradict each other:** The spec cannot inherit from two contradictory design docs silently. Surface the contradiction as `OPEN_QUESTION` (the user picks which design doc is canonical, or the spec resolves it explicitly).

---

## Relationship to sister skills

- **`/spec-review`** prosecutes the spec written here and consults this skill's sidecar to skip re-prosecuting author-arbitrated claims. It is the adversarial review surface for the root artifact, and the immediate next step after this author's first clean draft.
- **`/brief-author`** consumes the spec downstream: its Source-ingest stage reads `spec.md` as the upstream master, traces brief Goals to spec capabilities, and checks brief Non-goals against spec promises. **Authoring `spec.md` is what unblocks the entire downstream chain** — `/brief-author`, `/engineering-plan-author`, and `/plan-author` hard-refuse without a spec to anchor against, so in a project that has no spec yet, this skill runs first.
- **`/features-init`** scaffolds the `features/` workflow folder (briefs, engineering plans, chunk plans, decision logs). It does not write `spec.md` — the spec is a project-root document above `features/`, owned by this skill.

The spec is the root artifact; this skill exists to make it the cleanest.
