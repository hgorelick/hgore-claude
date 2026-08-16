---
name: spec-review
description: Adversarial single-pass review of a project's `spec.md` — the root source-of-truth every downstream artifact descends from. Grounds it internally and against the project's invariant ledger, applies fixes, returns APPROVED or NEEDS USER INPUT. Use after `/spec-author` lands a clean draft. Sister to `/brief-review-v2`, `/engineering-plan-review-v2`, `/plan-review-v2`.
user-invocable: true
---

# Spec Review — Staged Single-Pass

The spec is the root of the artifact lifecycle: every downstream artifact — every brief, engineering plan, chunk plan, and line of code — descends from it. A spec that contradicts its own invariants, invents a capability, leaves a load-bearing term undefined, or commits to a rule that contradicts the project's bound-invariant ledger will cascade through *every* feature, and the downstream review machinery repairs the descendants, never the spec itself. This skill prosecutes the spec through a Structural Shape gate plus three stages, with bounded same-round verification on orchestrator-rewritten prose. Never a multi-round inner loop — survivors of the bounded same-round re-pass land in the verdict and the user re-invokes.

This is the spec layer. Sister skills `/brief-review-v2`, `/engineering-plan-review-v2`, and `/plan-review-v2` review downstream artifacts. If the user asks for review of a brief / engineering plan / chunk plan, redirect.

## Shared scaffolding

- `~/.claude/skills/_spec-common/spec-format.md` — the canonical spec shape, drafting rules, claim emphasis, persona set (the format this skill prosecutes against)
- `~/.claude/skills/_review-common/principles.md` — stance, banned rationalizations, severity/tier, plan style rules
- `~/.claude/skills/_review-common/round-memory.md` — state file, load, capture priority, persist
- `~/.claude/skills/_review-common/orchestrator.md` — the shared Stage 3 spine
- `~/.claude/skills/_review-common/agent-prompt.md` — persona-agent prompt template
- `~/.claude/skills/_review-common/critical-pairs.md` — universal pairs (`P-CLASS-SCOPE`, `P-FULL-FILE`); the spec-specific `P-SPEC-*` pairs are defined in this skill
- `~/.claude/skills/_review-common/blocker-classes.md` — blocker registry + verdict gate (`SPEC_SHAPE_FAILED` is the spec-only class)

## Tribunal stance (spec-specific)

**THE INVARIANT LEDGER IS LAW; THE SPEC IS ITS OWN CONSISTENCY OBLIGATION.** The spec is the top of the *artifact* chain, so there is no upstream product document to trace to. Two things bind it:

1. **`CLAUDE.md` and project memory** (`~/.claude/projects/<project>/memory/`) carry the project's bound invariants and conventions. A spec that contradicts a bound invariant is committing the project to a phantom — surfaced as `OPEN_QUESTION` (the spec is amended, or the ledger is amended out-of-band; this skill never auto-edits the ledger). When the spec *deliberately* changes a rule the ledger also states, that is a real amendment, not a defect to silently fix — it routes to the user.
2. **Internal consistency.** Because nothing sits above the spec, its own sections are the only thing that can contradict it. A rule in §Invariants, a behavior in §Feature areas, and a definition in §Domain model must agree. Internal contradiction is the spec's highest-severity defect — every descendant inherits it.

There is no "REPO IS LAW" and no spec-trace at this layer — the spec doesn't cite path:line or trace to an upstream product doc. Stage 1's verification target is the spec's own internal coherence, the invariant ledger, project design docs, external-API reality, and data state.

## Active critical-pair policies (spec layer)

Applied silently in Stage 3; persona findings contradicting an active policy are retracted, not relitigated.

**P-SPEC-WHAT-NOT-HOW — Spec describes the product/system at the master level, not implementation.** §Domain model, §Invariants, §Feature areas, §Non-goals name product-visible rules and the system's conceptual structure — not file paths, schema columns, function signatures, framework choices, or chunk decomposition. A finding demanding engineering detail in the spec is invalid; a finding flagging implementation creep (path:line, schema columns, SQL, signatures, chunk plans) is valid. **Carve-out:** precision about a *product rule itself* (a score formula, a numeric threshold, a state-transition rule) is the spec's job, not implementation creep — a finding demanding such a rule be vaguer is invalid.

**P-SPEC-INVARIANT-VERIFIABILITY — Each invariant/business rule states a checkable condition.** "Notifications feel timely" is invalid; "a notification is queued until the user has been offline for 10 minutes" is valid. A finding requesting more *implementation* of an invariant is invalid; a finding requesting an observable success condition for an aspirational invariant is valid.

**P-SPEC-INTERNAL-CONSISTENCY — Sections must not contradict each other.** A finding flagging a cross-section contradiction (an invariant a feature area violates, a domain term used against its definition) is valid and HARD. A finding inventing a contradiction not present in the text is invalid.

**P-SPEC-INVARIANT-CONFORMANCE — The spec honors the CLAUDE.md / project-memory ledger.** A finding flagging a spec rule that contradicts a bound invariant is valid (routes to `OPEN_QUESTION`). A finding demanding the spec restate every ledger invariant verbatim is invalid — the spec inherits the ledger; it need not duplicate it.

**P-SPEC-DOMAIN-DEFINITION — Load-bearing terms are defined before use.** A finding flagging a load-bearing noun used in §Invariants / §Feature areas with no definition in §Domain model or §Glossary is valid. A finding demanding a definition for an ordinary-language word that carries no special domain meaning is invalid.

**P-SPEC-DOMAIN-SCOPE — Quantified invariants/feature-areas name their domain.** An invariant or feature area carrying "every", "all", "across", "any surface", "going forward" must name the concrete domain it ranges over (which surfaces, media types, cohorts, call paths) — per `principles.md` § Outcome-scope parity. A finding demanding the domain be named is valid; a finding demanding an implementation-level enumeration the spec author cannot know yet is invalid (the domain is product-level).

**P-SPEC-NON-GOAL-REALITY — Non-goals are plausible scope kills, not platitudes.** "We won't build a bad product" is a platitude; "the product does not support real-time collaboration" is a real scope kill if the product could plausibly include it. A finding flagging platitude Non-goals is valid; a finding demanding more Non-goals when the list already covers the plausible scope-creep surface is invalid.

## Active blocker classes

From `~/.claude/skills/_review-common/blocker-classes.md`:

- `SPEC_SHAPE_FAILED` — spec-layer equivalent of `STRUCTURAL_SHAPE_FAILED`. Stage 0 short-circuited the review because required sections are missing, banned content appeared, frontmatter is malformed, or implementation creep leaked into spec prose. Unprosecutable until shape is fixed.
- `STABLE_DISAGREEMENT` — two personas filed contradictory fixes on the same spec span.
- `OPEN_QUESTION` — a finding the orchestrator cannot auto-resolve: typically an internal contradiction where neither section is obviously canonical, or a spec rule that contradicts the `CLAUDE.md` / project-memory ledger (the user arbitrates "amend the spec or amend the ledger?").
- `FIX_INTRODUCED_PREMISE_INVERSION` — orchestrator's applied fix rewrote spec prose asserting a claim about the ledger, a design doc, an external API, or another spec section, but the claim does not survive verification. Working tree dirty.
- `POLISH_PLATEAU` — Tier-2 weight non-zero but ≤ floor (4). Non-blocking.
- `REPO_STATE_DRIFT` — `git rev-parse HEAD` changed mid-review. User re-runs.

`SPEC_SHAPE_FAILED` is the spec-layer-only class, registered in `_review-common/blocker-classes.md` under §Spec-only.

## Usage

```
/spec-review [<spec-path>] [--personas <p1> <p2> ...]
```

**Examples:**

```
# Default — resolves to spec.md at the repo root
/spec-review

# Explicit path
/spec-review docs/spec.md

# Explicit personas (overrides default)
/spec-review --personas product architecture
```

## Argument parsing

Split `$ARGUMENTS` on whitespace. Classify each token:

- `--personas` → all subsequent non-path tokens are persona names.
- Token contains `/` or ends with `.md` → spec path.
- Otherwise → ignored (the spec is a single project-root document; there is no feature-name shorthand).

No path argument → default to `spec.md` at the repository root (`git rev-parse --show-toplevel`), or `spec.md` in cwd when not in a git repo. If it doesn't exist, stop and report (point the user at `/spec-author` to create it).

## Persona resolution

**Persona files are project-scoped.** Resolve `personas/{name}.md` from the **root of the project the spec under review belongs to** (`git rev-parse --show-toplevel`), never the skill directory — so a review is always grounded in the reviewed project's own domain personas. A project with no `personas/` directory cannot be prosecuted until it has one: stop and report, pointing the user to author the project's personas.

### Default tribunal (no `--personas`)

Three personas in parallel:

- **`product.md`** — invariant/feature-area coherence, scope, internal contradictions, conflicts with the bound-invariant ledger, Non-goal discipline.
- **`architecture.md`** — internal consistency of the committed system, domain-model soundness, whether the invariants + feature areas form a buildable, non-self-contradictory whole.
- **`ai-development.md`** — plan-quality at the spec layer (invariant verifiability, Open-question form, drift toward engineering-plan detail), banned content categories.

### Explicit personas

Load each from `personas/{name}.md`. Reviewed by every listed persona in parallel. Missing persona file → stop and report.

`ai-development.md` is referenced as supplementary context for every Stage 2 agent — even non-`ai-development` personas should know the plan-style rules.

---

## Workflow

```
Status-frontmatter check         (deterministic, hard short-circuit, runs first)
   ↓ Status: needs-user-input → REFUSE, point user back at /spec-author; stop
Stage 0: Structural Shape Check  (deterministic, hard short-circuit)
   ↓ verifies required sections (per _spec-common/spec-format.md), banned-pattern absence,
   ↓ implementation-creep absence, frontmatter shape; FAIL → emit SPEC_SHAPE_FAILED, stop
Round Memory Pass                (deterministic, no LLM judgment)
   ↓ loads ~/.claude/cache/review-state/<project>__spec.json;
   ↓ consults the spec-author sidecar at
   ↓ ~/.claude/cache/author-state/<project>__spec.json and records counts of
   ↓ author-verified claims for Stage 2 to skip;
   ↓ computes round_number, prior_blockers, recently_resolved_blockers
Stage 1: Ground truth pass       (deterministic, mostly mechanical; 1d is light LLM judgment)
   ↓ produces audit_report grounding the spec in INTERNAL consistency + the CLAUDE.md /
   ↓ memory ledger + design docs + external-API wrappers + data state; NO upstream spec-trace
Stage 2: Persona prosecution     (LLM judgment, M parallel agents)
   ↓ when sidecar present, prepends a directive listing author-verified claims to skip;
   ↓ produces fix_lists per persona
Stage 3: Orchestrator decision   (deterministic + judgment)
   ↓ applies fixes, runs post-fix premise verification on rewritten prose, runs SAME-ROUND
   ↓ focused re-prosecution on diff hunks (≤1 re-pass), runs carry-forward consultation,
   ↓ classifies remaining, renders verdict, persists state with per-round metrics
```

There is no inner loop. If blockers remain, the user resolves them and re-invokes.

---

## Status-frontmatter check (MANDATORY, HARD SHORT-CIRCUIT, RUNS FIRST)

`Read` the spec's YAML frontmatter / leading HTML-comment block. Extract the `Status:` value.

`Status:` is a binary mid-cycle signal: `needs-user-input` (mid-cycle) or absent (ready).

- **`Status: needs-user-input`** → stop. Do NOT spawn Stage 0 or anything after. Emit:

  ```
  SPEC: <spec-path>
  STATUS: REFUSED (artifact in mid-cycle authoring state)

  This spec has `Status: needs-user-input`. The author skill (`/spec-author`) wrote it as a
  partial draft with unresolved blockers listed in `## Pending blockers`. Reviewing a partial
  draft would re-prosecute issues the author already surfaced.

  Resolve the blockers in `## Pending blockers`, then re-invoke `/spec-author` (warm mode is
  automatic). The author skill removes the `Status:` frontmatter on a successful APPROVED
  emission; re-invoke `/spec-review` once the spec is back to no-Status state.
  ```

- **No `Status:` field, OR any other value** → proceed. The Round Memory Pass consults the spec-author sidecar; if `authoring_mode: "draft"` is set there, the verdict surfaces a draft warning. Persona prosecution still runs.

Deterministic; runs before any LLM judgment.

## Stage 0 — Structural Shape Check (MANDATORY, HARD SHORT-CIRCUIT)

The required shape is defined in `~/.claude/skills/_spec-common/spec-format.md`. Apply these checks:

### Required sections (core, in order)

1. **Frontmatter** — `Created:` and `Last updated:` dates present (YYYY-MM-DD). `Status:` field OPTIONAL — present only when mid-cycle. Any other `Status:` value is a SOFT MEDIUM finding.
2. **`## Overview`** — heading present; body non-empty.
3. **`## Domain model & core concepts`** — heading present; body non-empty.
4. **`## Invariants & business rules`** — heading present; ≥1 bullet.
5. **`## Feature areas`** — heading present; ≥1 bullet.
6. **`## Non-goals & scope bounds`** — heading present; ≥1 bullet (or an explicit justified "None").
7. **`## Glossary`** — heading present; ≥1 entry (or `None.` when the Domain model fully defines the vocabulary).

Optional sections (`## Roadmap / milestones`, `## Analytics & observability`, `## External integrations`) are not required; when present they must be non-empty.

Each missing/empty core section is `[HARD: missing required section]`.

### Forbidden patterns (regex-detectable; HARD per occurrence)

Same style/attribution bans as the sister skills (the fenced block keeps nested backticks intact):

```
# Addendum sections
(?i)^##+\s*(addendum|appendix|review notes|round-\d+ findings)\b

# Review attribution
(?i)\b(architecture review|product review|round[- ]?\d+ tribunal|reviewer A/B)\b found\b

# Historical comparison
(?i)\b(the original spec|previously the spec|the spec used to|in the prior version)\b

# Persona-attribution headers
(?i)^##+\s+(architecture|product|backend|frontend|testing|security)(?:'s|s')\s+(view|notes|take|opinion)\b

# Conflict-resolution metadata
(?i)\b(conflict resolved by|consensus reached|decision pending arbitration)\b
```

Plus prose-detected: hedging future tense (`we will likely`, `this spec aims to`) → SOFT MEDIUM; meta-commentary (`this section`, `below we'll cover`) → SOFT MEDIUM; emojis / exclamation marks in section bodies → SOFT LOW.

### Implementation-creep patterns (regex-detectable; HARD)

The spec drifted into engineering territory. Same fenced-block convention:

```
# Path:line citations (longest-first alternation)
[a-z_/]+\.(tsx|prisma|toml|yaml|json|md|ts|js|sql)(:[0-9]+)?

# Function/identifier signatures
\w+\(.*\)\s*(:|=>)\s*\w+

# Schema column names
(column|field|enum)\s+["`]\w+["`]

# SQL fragments
(SELECT|INSERT|UPDATE|DELETE|CREATE TABLE)\s+\w+
```

The path-citation regex is applied to spec prose with backtick-fenced spans excluded (a `` `path` `` inside a sentence is fine; an unfenced `path:42` is HARD). Prose mentions of "the `externalId` field" do not fire the schema-column regex (it requires the literal noun `column`/`field`/`enum` to precede the quoted identifier). **Carve-out:** a precise product *rule* expressed with a formula or threshold is NOT implementation creep (P-SPEC-WHAT-NOT-HOW carve-out) — these regexes target code anchors, not product math.

### Behavior

- **All checks pass** → record `shape_clean=true`, proceed to Round Memory Pass.
- **Any HARD failure** → stop. Emit `SPEC_SHAPE_FAILED` with the defect list; no further stages run. SOFT findings defer to Stage 1's audit.
- **SOFT-only failures** → record; proceed. Stage 1e mechanical fixes resolve them.

Why short-circuit: a persona reviewing a spec with a missing Invariants section produces findings that assume the section exists — wasted budget.

---

## Round Memory Pass (no LLM judgment)

Same purpose as the sister skills, same mechanism — `~/.claude/skills/_review-common/round-memory.md`. Read it. The spec layer adds:

- **Slug** — `<project>__spec`, where `<project>` is the repo-root basename.
- **Extra field** — `author_sidecar_consulted: { sidecar_path, sidecar_present, claims_verified_skipped, self_prosecution_findings_skipped }`, written every round per the consultation below.
- **Extra metric** — `per_round_metrics.round_<N>.cross_file_escalations`, since this layer escalates cross-file findings rather than applying them.
- **Blocker classes seen here** — `SPEC_SHAPE_FAILED`, plus the universal `STABLE_DISAGREEMENT` / `OPEN_QUESTION` / `FIX_INTRODUCED_PREMISE_INVERSION`.

The spec layer's additional carry-forward source is the spec-author's sidecar at `~/.claude/cache/author-state/<project>__spec.json`. The author already verified claims and self-prosecuted; the reviewer consults the sidecar to skip re-prosecuting what the author arbitrated.

### Author sidecar consultation

Read `~/.claude/cache/author-state/<project>__spec.json` if it exists. Extract `claims_verified` count + `ground_truth_log` entries with outcome `verified` / `verified_softened` / `corrected` (Stage 2 MUST NOT re-prosecute these as hallucinations), `self_prosecution_findings` (MUST NOT re-file), and `authoring_residual` (informational only, not blockers). If the sidecar is absent (the spec was hand-written), record `sidecar_present: false`; Stage 2 has full prosecution latitude. If the sidecar's `last_spec_sha256` differs from the current spec's SHA, the user edited the spec manually — treat `claims_verified` as a hint, not a binding skip-list.

### Persist on exit

Per the shared file, plus `author_sidecar_consulted` ← what was consulted this round.

---

## Stage 1 — Ground truth pass (MANDATORY, MOSTLY MECHANICAL)

Produces an `audit_report`. Stage 2 personas MUST NOT re-prosecute facts verified here.

**There is NO spec-trace** (the spec is the root — nothing above it to trace to) and **NO repo grep for path:line** (Stage 0 enforced no implementation creep). Stage 1's targets are the spec's own internal coherence, the invariant ledger, design docs, external-API wrappers, and data state.

**LLM-judgment carve-out.** Sub-passes 1a-1c are mechanical (file Reads, regex, substring overlap). Sub-pass 1d makes lightweight LLM judgment calls (invariant verifiability, Non-goal reality) no regex captures, each filed SOFT MEDIUM under the corresponding P-SPEC-* policy.

### 1a. Internal consistency (mechanical + light judgment)

The spec's own sections must agree. For each:

- **Each load-bearing term** used in §Invariants / §Feature areas → verify it is defined in §Domain model or §Glossary. Undefined → `[HARD: undefined load-bearing term]` under P-SPEC-DOMAIN-DEFINITION.
- **Each invariant** → check no §Feature area describes behavior that violates it. Violation → `[HARD: feature area contradicts invariant]` under P-SPEC-INTERNAL-CONSISTENCY.
- **Each feature area** → check it does not assume a capability §Invariants or §Domain model contradicts.

Output an `Internal Consistency` block listing terms checked, contradictions found (verbatim both sides), and consistent cross-references.

### 1b. Invariant-ledger conformance (mechanical)

Read `CLAUDE.md` (and nested) and every memory file under `~/.claude/projects/<project>/memory/` whose `description` hints at relevance. For each bound invariant:

- **Spec honors it** → no finding.
- **Spec contradicts it** → `[HARD: contradicts invariant ledger]`. Cite verbatim (spec claim + ledger claim). Routes to `OPEN_QUESTION` (amend spec, or amend the ledger out-of-band).
- **Spec silent** → no finding (silence is not contradiction).

Output a `Ledger Conformance` block (entries consulted, contradictions verbatim, honored invariants).

### 1c. Design-doc consistency (mechanical)

Read project design docs where they exist (`docs/*`, `context/*`, architecture/decision records). For each that bears on a spec section:

- **Spec consistent with the design doc** → record as `verified: consistent_with <doc>`.
- **Spec contradicts a design doc** → `[HARD: contradicts design doc]` (cite verbatim). If two design docs contradict each other, surface as `OPEN_QUESTION` (which is canonical).

If no project design docs exist, record `design_docs_present: false` and skip. Output a `Design Doc Consistency` block.

### 1d. Spec style supplements

- Each invariant has a checkable condition (LLM check; vague → SOFT MEDIUM under P-SPEC-INVARIANT-VERIFIABILITY).
- Each Non-goal is a real scope kill (platitudes → SOFT MEDIUM under P-SPEC-NON-GOAL-REALITY).
- Quantified invariants/feature-areas name their domain (unnamed → SOFT MEDIUM under P-SPEC-DOMAIN-SCOPE).
- Open questions (if a `## Open questions` section exists) are in question form (regex: must contain `?`; statements → SOFT MEDIUM).
- Cohort/data counts cite a source (regex `~?\d+(-\d+)?\s+\w+` in Overview/Invariants; every match followed within 3 lines by a citation marker; uncited → SOFT MEDIUM).

### 1e. Stage 1 mechanical fixes

Apply unambiguous fixes immediately (forbidden style-class patterns from Stage 0 SOFT findings; stale `Last updated` when content changed; trivial statement→question conversions). Emit `Stage 1 fixes applied:`. HARDs that can't be auto-fixed pass to Stage 2 as `pre_resolved_hard_findings`.

### Stage 1 output (audit_report)

Bulleted facts: spec_path, HEAD sha; internal_consistency (terms_checked, contradictions, hard_findings); ledger_conformance (entries_consulted, contradictions, honored_invariants); design_doc_consistency (docs_consulted, contradictions); spec_style (invariant_verifiability, non_goal_reality, domain_scope, open_question_form, cohort_citation findings); stage_1_fixes_applied; pre_resolved_hard_findings; author_sidecar_consulted.

---

## Stage 2 — Persona prosecution (parallel agents, fix-list output)

Read `personas/ai-development.md` once for context. Resolve personas (auto or explicit). Launch one Agent per persona, **all in parallel in a single message**, each with `model: "sonnet"` per `_review-common/agent-prompt.md` § Model pin — never inherit the session model; record `persona_model` in the review state. M agents.

### Spawn agents

Use `~/.claude/skills/_review-common/agent-prompt.md`. Substitute:

- `{persona_name}` — the persona
- `{audit_report_bullets}` — Stage 1 audit (compact bullets)
- `{pre_resolved_hard_findings}` — Stage 1 HARDs
- `{active_critical_pair_subset}` — `P-CLASS-SCOPE, P-FULL-FILE, P-SPEC-WHAT-NOT-HOW, P-SPEC-INVARIANT-VERIFIABILITY, P-SPEC-INTERNAL-CONSISTENCY, P-SPEC-INVARIANT-CONFORMANCE, P-SPEC-DOMAIN-DEFINITION, P-SPEC-DOMAIN-SCOPE, P-SPEC-NON-GOAL-REALITY`
- `{target_locator}` — the spec path
- `{how_to_get_it}` — `Read <spec_path>`; agents Read source-of-truth files (CLAUDE.md, project memory, design docs, external-API wrappers, persona files) on demand
- `{pr_description_or_brief_mapping}` — N/A (the spec is the root artifact; there is no upstream mapping)
- `{skill_specific_extensions}` — *Imagine you are the brief author who must turn this spec into feature briefs. Where does the spec leave you guessing? Where is an invariant so unverifiable that two brief authors would commit to different success criteria? Where does a feature area secretly import an architectural commitment that belongs in an engineering plan? Where does a Non-goal feel like a platitude that won't actually stop scope creep? Where would a downstream brief have to invent product policy because the spec ducked the question? Where do two spec sections quietly contradict each other?*
- `{skill_specific_preamble}` — none (Stage 1's internal-consistency + ledger-conformance blocks are the ground-truth substitute)
- `{skill_specific_resets_block}` — none (RESETs are an engineering-plan-only mechanism)

The spec is typically larger than a brief; pass it inline if compact, else instruct agents to `Read` it in full. The orchestrator does NOT inline source-of-truth file contents — agents Read on demand.

### Author-sidecar consultation in agent prompts

When the spec-author sidecar is present, prepend the standard directive (mirroring `/brief-review-v2`): list `claims_verified` and `self_prosecution_findings` counts; instruct that author-verified claims MUST NOT be re-prosecuted as hallucinations without citing a *specific change* in `CLAUDE.md` / project memory / a design doc since `last_spec_sha256`. When absent, omit.

---

## Stage 3 — Orchestrator decision

Runs in the main thread.

### 3a–3d. Apply fixes

Confirm Stage 1 mechanical fixes are in place. Filter Stage 2 fix lists against the active critical-pair policies (retract contradicting findings; note in verdict). Retract duplicates of Stage-1 hard findings and author-sidecar-verified claims lacking a concrete upstream-change citation. Detect cross-persona disagreement on the same span → `STABLE_DISAGREEMENT` (do not auto-apply). Consolidate non-conflicting fixes, group by section, apply in a single editing pass ordered by severity.

**Cross-file fix scope (spec layer).** The spec author owns ONLY `spec.md`. A persona fix whose substance binds beyond the spec is never auto-applied to the other file:

- **Mention of `CLAUDE.md`** → DO NOT auto-edit. Surface as `OPEN_QUESTION`: "fix would amend CLAUDE.md — user arbitrates whether the ledger changes or the spec is re-scoped."
- **Mention of project-memory paths** (`~/.claude/projects/<project>/memory/<file>.md`, `MEMORY.md`, any path under `memory/`) → DO NOT auto-edit. Surface as `OPEN_QUESTION`.
- **Mention of a project design doc** (`docs/*`, `context/*`) → DO NOT auto-edit. Surface as `OPEN_QUESTION`: "fix would amend `<doc>` — user arbitrates which is canonical."

Record cross-file escalations in `cross_file_escalations[]`.

**Authority order when artifacts disagree** (highest to lowest):

1. `CLAUDE.md` and project memory — bound-invariant ledger; the spec honors it, never silently overrides.
2. Project design docs — grounding the spec stays consistent with.
3. `spec.md` under review.

When a finding reveals contradiction with an upstream source, the spec aligns to it OR the user arbitrates an explicit amendment. Contradiction *between* the ledger and a design doc escalates as `OPEN_QUESTION`.

**Forbidden fixes:**

- Weakening the spec (dropping an invariant, softening verifiability, removing a Non-goal to bypass enforcement) → escalate as `OPEN_QUESTION`.
- Auto-editing `CLAUDE.md`, project memory, or a design doc → escalate as `OPEN_QUESTION`.
- "Leaving it for the brief" — if the spec is unclear now, the brief author will hallucinate.
- Adding implementation detail to fix an invariant-verifiability finding (P-SPEC-WHAT-NOT-HOW retracts this; the right fix is an *observable* condition, not a how).

### Post-fix premise verification

Per `~/.claude/skills/_review-common/orchestrator.md` § Post-fix premise verification. The claims that matter at this layer: internal cross-section references, invariant-ledger references, design-doc references, cohort and data claims, and external-API claims.

### Same-round focused re-prosecution

Per `~/.claude/skills/_review-common/orchestrator.md` § Same-round focused re-prosecution — one pass, bounded. The third skip condition here is *cross-file escalations = 0* rather than cross-file edits, since this layer escalates rather than editing.

### 3e. Classify remaining unresolved findings

Active classes: `SPEC_SHAPE_FAILED`, `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `FIX_INTRODUCED_PREMISE_INVERSION`, `POLISH_PLATEAU`, `REPO_STATE_DRIFT`.

**Carry-forward consultation (durable-first, then ephemeral cache).**

- **Priority 1 — project decision log** (durable; if present). If the project keeps a project-level decision record (`docs/decisions.md` or `decisions.md` at root), read it and search for entries whose subject substring-matches the finding's surface. A finding contradicting a bound entry → drop, recording `[CARRY-FORWARD via <decision-log>]` (when the log uses the `## Active` / `## Archived` split, only Active-section `Status: bound` entries count — skip `superseded`/`obsolete` entries; per `~/.claude/skills/_review-common/principles.md` § What counts as a bound entry). If no project decision log exists, skip Priority 1 (the spec layer has no mandated durable arbitration file — many projects won't have one).
- **Priority 2 — `recently_resolved_blockers` ephemeral cache** (state-file). For findings surviving Priority 1: if an entry's `carry_forward_until_round >= round_number` AND its `path_or_section` overlaps the finding's section/phrase, downgrade to `OPEN_QUESTION` with the prior `user_decision` surfaced verbatim; the persona's claim survives only if `current_reclassification_justification` was filed. (`path_or_section` is always a section heading or quoted phrase — the spec doesn't cite path:line, so overlap stays in section-name space.)

### 3f. Render verdict

- **APPROVED** when ALL of:
  - Stage 0 Structural Shape Check exited clean (no `SPEC_SHAPE_FAILED`)
  - Tier-1 weight = 0
  - Tier-2 weight ≤ 4
  - No `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `FIX_INTRODUCED_PREMISE_INVERSION`, `REPO_STATE_DRIFT`
- **NEEDS USER INPUT** otherwise.

Tier-1 weights: CRITICAL=8, HIGH=4, MEDIUM=2, LOW=1. Tier-2 floor: 4.

**Final line — verdict banner.** After the output block below, run the shared verdict-banner script and emit its output verbatim (`~/.claude/skills/_review-common/blocker-classes.md` § Verdict banner) as the **very last** thing in your response, so the verdict is visible without scrolling.

### 3g. Output

```
## Spec Review Complete: {spec_path}

**Round:** {round_number} {| `(round 1 — no prior state)` | `(loaded from cache: {n-1} → {n})`}
**State source:** {`Loaded from ~/.claude/cache/review-state/<project>__spec.json` | `Round 1 (no prior state)`}
**Author sidecar:** {`consulted; N claims verified skipped; M self-prosecution findings skipped` | `absent (spec was hand-written)` | `present but SHA differs (treated as hint)`}
**Authoring mode warning:** {`none` | `sidecar reports authoring_mode: "draft" — /spec-author --draft skipped ground-truth and self-prosecution`}
**Personas:** {names}
**Stage 0 shape check:** PASS / N hard findings (sections / forbidden patterns / implementation creep)
**Stage 1 audit:** internal_consistency PASS / N hard; ledger_conformance PASS / N hard; design_doc PASS / N hard
**Stage 1 mechanical fixes applied:** {count}
**Stage 2 personas:** {N} agents in parallel
**Stage 3 fixes applied:** {count} (HARD: {n}, SOFT: {n})
**Stage 3 retractions (critical-pair policy):** {count}
**Cross-file escalations (OPEN_QUESTION):** {count}
  - {file}: {one-line} ... (omit when 0)
**Carry-forward consultation:**
  - decision-log matches: {n}; findings dropped: {n}
  - state-file matches: {n}; downgraded to OPEN_QUESTION: {n}; survived with current_reclassification_justification: {n}
**Post-fix premise verification:** attempts={n}; verified={n}; falsified={n}; new_blockers={n}
**Same-round re-prosecution:** ran={bool}; diff_hunks={n}; additional_fixes={n}; findings_persisted={n}
**Final Tier 1 weight:** {n}
**Final Tier 2 weight:** {n} (floor: 4)

### Changes Made
- {bullets of significant edits}

### Retractions
- {finding} → retracted because {policy / pre-resolved / superseded / author-verified without justification}

### Blockers (if any)
- [SPEC_SHAPE_FAILED] {finding} — fix and re-invoke.
- [STABLE_DISAGREEMENT] {finding} — Persona A: {fix A}; Persona B: {fix B}. Pick one.
- [OPEN_QUESTION] {finding} — {question} (internal contradiction the orchestrator can't resolve, or a ledger/design-doc conflict).
- [FIX_INTRODUCED_PREMISE_INVERSION] {section}: fix asserts "{claim}"; verification: {what was run}; actual: "{evidence}". Working tree dirty.
- [POLISH_PLATEAU] {finding} — non-blocking.
- [REPO_STATE_DRIFT] HEAD changed from {sha} to {sha}. Re-run.

### Spec Status: APPROVED / NEEDS USER INPUT
```

If `NEEDS USER INPUT`: the next step is **targeted edits to clear the listed blockers**, then re-invoke `/spec-review` (optionally triage with `/explain-blockers` or `/solve-blockers`). Do **not** re-run `/spec-author` to clear a handful of blockers (see the hard rule).

---

## Hard rules

- **Status-frontmatter check is mandatory and runs first.** A spec with `Status: needs-user-input` is mid-cycle; refuse and point at `/spec-author`.
- **Stage 0 Structural Shape Check is mandatory.** A spec with missing required sections or implementation creep is unprosecutable.
- **Stage 1 is mandatory** and has NO upstream spec-trace — the spec is the root. Its targets are internal consistency, the invariant ledger, design docs, external-API reality, and data state.
- **Round Memory Pass is mandatory.** State file at `~/.claude/cache/review-state/<project>__spec.json` (NOT in the repo).
- **Author sidecar consultation is mandatory when the sidecar exists.** Re-prosecuting author-verified claims without a concrete upstream-change citation is forbidden.
- **Orchestrator verifies its own edits.** Post-fix premise verification runs after Stage 3d, before classification.
- **Cross-file fix scope is mandatory when triggered.** Mentions of `CLAUDE.md` / project memory / a design doc escalate as `OPEN_QUESTION` — the spec skill never auto-edits the bound-invariant ledger or a design doc; it edits ONLY `spec.md`.
- **Same-round focused re-prosecution is mandatory** when ANY of: Stage 3d fixes > 0, cross-file escalations > 0, or post-fix premise verification falsified-claim count > 0. Bounded: exactly one re-pass.
- **Stage 2 agents return fix lists; never edit files.** All edits applied by the orchestrator in Stage 3.
- **Never** mark APPROVED while any blocker class is non-empty.
- **Never** weaken the spec to resolve a finding (drop an invariant, soften verifiability, remove a Non-goal). That's `OPEN_QUESTION`.
- **Always** quote verbatim from the spec, ledger, design doc, or audit_report when justifying a finding.
- **No multi-round inner loop.** The same-round re-prosecution is exactly one pass over diff hunks.
- **Do not re-run `/spec-author` to clear a completed review.** On `NEEDS USER INPUT`, the next step is targeted edits, then re-invoking `/spec-review`. Re-run the author skill only for the mid-cycle `Status: needs-user-input` refuse path, or a wholesale re-author (ask in plain language).

## Compliance self-check (before rendering verdict)

- [ ] Status-frontmatter check ran first.
- [ ] Stage 0 Structural Shape Check ran; required sections verified; banned + implementation-creep patterns absent.
- [ ] Round Memory Pass ran; reviewer state loaded; author sidecar consulted (or marked absent).
- [ ] Stage 1 ran in full: internal consistency, ledger conformance, design-doc consistency, spec style supplements. NO upstream spec-trace attempted.
- [ ] Stage 2 spawned all M persona agents in parallel.
- [ ] Stage 3 applied critical-pair retractions before applying fixes.
- [ ] Post-fix premise verification ran on orchestrator-rewritten prose.
- [ ] Same-round re-prosecution ran (or skip conditions met and recorded).
- [ ] Carry-forward consultation: Priority 1 (project decision log, if present) then Priority 2 (state-file).
- [ ] Verdict template includes all metric lines, even when count = 0.
- [ ] Cross-file fix scope checked: mentions of CLAUDE.md / memory / design docs escalated as `OPEN_QUESTION`.
- [ ] State file persisted with new round entry appended.

## Edge cases

- **Spec file not found:** report and exit; point at `/spec-author` to create it. No state-file changes.
- **Persona file not found:** auto-resolution falls back to the next default persona; explicit personas stop and ask.
- **`CLAUDE.md` absent:** warn and proceed. Ledger conformance marked `0 entries consulted`; internal-consistency + design-doc + external-API checks still run.
- **Project memory absent:** warn and proceed. `CLAUDE.md` is the minimum ledger source.
- **No project design docs:** `design_docs_present: false`; Stage 1c skipped. Not an error.
- **Spec authored via `/spec-author --draft`** (sidecar `authoring_mode: "draft"`): proceed with full prosecution; warn in verdict that the artifact is unhardened.
- **Author sidecar SHA differs from spec SHA:** user edited the spec manually after authoring. Treat `claims_verified` as a hint; Stage 2 may re-prosecute spans where user-edits overlap author-verified claims.
- **State file missing for a spec clearly reviewed before** (user wiped `~/.claude/cache/`): cold start at round 1; the ephemeral cache is lost, but a project decision log (if any) still feeds Priority-1 carry-forward.
- **HEAD changes mid-review:** emit `REPO_STATE_DRIFT`. User re-runs.
- **Spec proposes amendments to `CLAUDE.md` or a design doc:** Forbidden auto-edit. Surface as `OPEN_QUESTION`; the user runs the amendment out-of-band.

---

## Relationship to sister skills

- **`/spec-author`** writes the spec and the author sidecar this skill consults. The author runs ground-truth verification and self-prosecution at write time; this skill prosecutes only what the author missed or what the user introduced via manual edits since.
- **`/brief-review-v2`** consumes the spec as its upstream master: its Stage 1 traces brief Goals to spec capabilities and checks brief Non-goals against spec promises. A spec defect surfaced at the brief layer belongs upstream — feeding back into the next `/spec-author` invocation.
- **`/engineering-plan-review-v2`** and **`/plan-review-v2`** inherit the spec transitively through the brief.

**No Imagined-Implementer phase.** `/engineering-plan-review-v2` runs an Imagined-Implementer dry-run because its plan pre-decides cross-chunk wiring for *multiple* downstream chunk plans. The spec's downstream is many *independent* briefs, each authored and reviewed on its own; the spec does not pre-wire features the way an engineering plan pre-wires chunks. The imagined-downstream-author lens (the brief author who must consume this spec) folds into Stage 2's `{skill_specific_extensions}` instead of running as a separate phase.

The spec is the root artifact; this skill exists to give it the same adversarial review surface the brief, engineering plan, and chunk plans already enjoy.
