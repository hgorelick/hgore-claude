---
name: spec-review
description: Adversarial single-pass review of a `spec.md` — the source-of-truth every downstream artifact descends from, including the decomposition that cuts its briefs. Grounds it internally, against the project's invariant ledger, and against vision's spec map where one exists; applies fixes, returns APPROVED or NEEDS USER INPUT. Use after `/spec-author` lands a clean draft. Sister to `/vision-review`, `/brief-review-v2`, `/engineering-plan-review-v2`, `/plan-review-v2`.
user-invocable: true
---

# Spec Review — Staged Single-Pass

The spec is the source-of-truth of its own system: every downstream artifact — every brief, engineering plan, chunk plan, and line of code under that system — descends from it. A spec that contradicts its own invariants, invents a capability, leaves a load-bearing term undefined, or commits to a rule that contradicts the project's bound-invariant ledger will cascade through *every* feature, and the downstream review machinery repairs the descendants, never the spec itself. The spec also carries `## Decomposition` — the seams, the brief roster, the scope stubs, and the coverage table — so a silent narrowing there cuts a brief nobody notices is missing. This skill prosecutes both through a Structural Shape gate plus three stages, with bounded same-round verification on orchestrator-rewritten prose. Never a multi-round inner loop — survivors of the bounded same-round re-pass land in the verdict and the user re-invokes.

This is the spec layer. `/vision-review` reviews the layer above where `vision.md` exists; `/brief-review-v2`, `/engineering-plan-review-v2`, and `/plan-review-v2` review downstream artifacts. If the user asks for review of a vision / brief / engineering plan / chunk plan, redirect.

## Shared scaffolding

- `~/.claude/skills/_spec-common/spec-format.md` — the canonical spec shape, drafting rules, claim emphasis, persona set (the format this skill prosecutes against)
- `~/.claude/skills/_decompose-common/decomposition-principles.md` — split-line predicates, the coverage-map contract, and the truth-versus-state split (what `## Decomposition` is prosecuted against)
- `~/.claude/skills/_review-common/brief-conformance-prosecutor.md` — the off-model conformance-prosecutor contract and its § Model pin, used here for map conformance
- `~/.claude/skills/_review-common/principles.md` — stance, banned rationalizations, severity/tier, plan style rules
- `~/.claude/skills/_review-common/round-memory.md` — state file, load, capture priority, persist
- `~/.claude/skills/_review-common/orchestrator.md` — the shared Stage 3 spine
- `~/.claude/skills/_review-common/agent-prompt.md` — persona-agent prompt template
- `~/.claude/skills/_review-common/critical-pairs.md` — universal pairs (`P-CLASS-SCOPE`, `P-FULL-FILE`); the spec-specific `P-SPEC-*` pairs are defined in this skill
- `~/.claude/skills/_review-common/blocker-classes.md` — blocker registry + verdict gate (`SPEC_SHAPE_FAILED` is the spec-only class)

## Tribunal stance (spec-specific)

**THE INVARIANT LEDGER IS LAW; THE SPEC IS ITS OWN CONSISTENCY OBLIGATION.** Three things bind the spec:

1. **`CLAUDE.md` and project memory** (`~/.claude/projects/<project>/memory/`) carry the project's bound invariants and conventions. A spec that contradicts a bound invariant is committing the project to a phantom — surfaced as `OPEN_QUESTION` (the spec is amended, or the ledger is amended out-of-band; this skill never auto-edits the ledger). When the spec *deliberately* changes a rule the ledger also states, that is a real amendment, not a defect to silently fix — it routes to the user.
2. **Internal consistency.** A rule in §Invariants, a behavior in §Feature areas, and a definition in §Domain model must agree, and §Decomposition must agree with all three. Internal contradiction is the spec's highest-severity defect — every descendant inherits it.
3. **`vision.md`'s spec map, where `vision.md` exists.** The entry for this spec is an upstream that assigns it a surface, so it earns a trace: every surface the map assigns is present, every surface the spec defines is one the map assigns it, every vision section the entry claims to cover is covered. A map entry is a claim about a real file, which makes divergence falsifiable rather than a matter of judgment. This skill never edits `vision.md`; a needed amendment escalates.

**The vision gate is file presence at the repository root, never a question.** Where `vision.md` is absent, the spec is the root of the artifact chain, there is no upstream trace, the sidecar keys stay unslugged, and this skill behaves exactly as it does for a single-spec project.

There is no "REPO IS LAW" and no path:line grep at this layer — the spec doesn't cite them. Stage 1's verification targets are the spec's own internal coherence, its decomposition, the invariant ledger, the spec map where one exists, project design docs, external-API reality, and data state.

## Active critical-pair policies (spec layer)

Applied silently in Stage 3; persona findings contradicting an active policy are retracted, not relitigated.

**P-SPEC-WHAT-NOT-HOW — Spec describes the product/system at the master level, not implementation.** §Domain model, §Invariants, §Feature areas, §Non-goals name product-visible rules and the system's conceptual structure — not file paths, schema columns, function signatures, framework choices, or chunk decomposition. A finding demanding engineering detail in the spec is invalid; a finding flagging implementation creep (path:line, schema columns, SQL, signatures, chunk plans) is valid. **Carve-out:** precision about a *product rule itself* (a score formula, a numeric threshold, a state-transition rule) is the spec's job, not implementation creep — a finding demanding such a rule be vaguer is invalid.

**P-SPEC-INVARIANT-VERIFIABILITY — Each invariant/business rule states a checkable condition.** "The scoring feels fair" is invalid; "scores are locked until the user has 5 rankings in a category" is valid. A finding requesting more *implementation* of an invariant is invalid; a finding requesting an observable success condition for an aspirational invariant is valid.

**P-SPEC-INTERNAL-CONSISTENCY — Sections must not contradict each other.** A finding flagging a cross-section contradiction (an invariant a feature area violates, a domain term used against its definition) is valid and HARD. A finding inventing a contradiction not present in the text is invalid.

**P-SPEC-INVARIANT-CONFORMANCE — The spec honors the CLAUDE.md / project-memory ledger.** A finding flagging a spec rule that contradicts a bound invariant is valid (routes to `OPEN_QUESTION`). A finding demanding the spec restate every ledger invariant verbatim is invalid — the spec inherits the ledger; it need not duplicate it.

**P-SPEC-DOMAIN-DEFINITION — Load-bearing terms are defined before use.** A finding flagging a load-bearing noun used in §Invariants / §Feature areas with no definition in §Domain model or §Glossary is valid. A finding demanding a definition for an ordinary-language word that carries no special domain meaning is invalid.

**P-SPEC-DOMAIN-SCOPE — Quantified invariants/feature-areas name their domain.** An invariant or feature area carrying "every", "all", "across", "any surface", "going forward" must name the concrete domain it ranges over (which surfaces, media types, cohorts, call paths) — per `principles.md` § Outcome-scope parity. A finding demanding the domain be named is valid; a finding demanding an implementation-level enumeration the spec author cannot know yet is invalid (the domain is product-level).

**P-SPEC-NON-GOAL-REALITY — Non-goals are plausible scope kills, not platitudes.** "We won't build a bad product" is a platitude; "the product does not support real-time collaboration" is a real scope kill if the product could plausibly include it. A finding flagging platitude Non-goals is valid; a finding demanding more Non-goals when the list already covers the plausible scope-creep surface is invalid.

**P-SPEC-DECOMPOSITION-TRUTH — §Decomposition states the boundary, never the state of the work.** A finding flagging lifecycle words, dates, counts of what exists yet, or park/loan language in the section is valid. A finding demanding the section say which briefs exist as folders, what is in flight, or what is still owed is invalid — that lives in `features/README.md`, and a unit another domain owns renders as excluded by a named seam whether or not that domain's spec has been written.

**P-SPEC-SEAM-PREDICATE — A seam is its predicate.** A finding flagging a seam with no split-line predicate, a predicate that enumerates examples instead of stating a test, or a predicate a neighboring seam also satisfies is valid. A finding demanding a seam justify itself at greater length, or asking for a second predicate under one seam name, is invalid — a seam needing two predicates is two seams, and that is the finding to file instead.

**P-SPEC-MAP-AUTHORITY — Where `vision.md` exists, the map entry decides what this spec owns.** A finding flagging a surface the spec defines that a neighbor's entry claims, or a surface the entry assigns this spec that it never defines, is valid. A finding demanding the spec define a surface the map assigns a neighbor is invalid, and so is a finding demanding this skill rewrite `vision.md` — that escalates as `VISION_AMENDMENT_NEEDED`.

## Active blocker classes

From `~/.claude/skills/_review-common/blocker-classes.md`:

- `SPEC_SHAPE_FAILED` — spec-layer equivalent of `STRUCTURAL_SHAPE_FAILED`. Stage 0 short-circuited the review because required sections are missing, `## Decomposition` is malformed, banned content appeared, frontmatter is malformed, or implementation creep leaked into spec prose. Unprosecutable until shape is fixed.
- `STRUCTURAL_LINT_FAILED` — `/plan-lint` short-circuited Stage 0 before the shape checks ran. Lint is the deterministic floor; this class is what fires below the format check on top of it.
- `DECOMPOSITION_COVERAGE_GAP` — a spec unit neither claimed by a named brief nor excluded by a named seam, or a claimed invariant with no proof owner.
- `DECOMPOSITION_STATUS_LEAK` — churn language inside §Decomposition. The review-layer backstop for what the lint's status-token scan misses.
- `SEAM_PREDICATE_MISSING` — a seam with no split-line predicate, or one that does not decide the units the Coverage table assigns by it.
- `DECOMPOSITION_SURFACE_EXCESS` — the spec is oversized. Director decision; never auto-split.
- `SPEC_NONGOAL_TRESPASS` — a scope stub does what a Non-goal excludes or what the project's cut list cuts. Class A.
- `SPEC_AMENDMENT_NEEDED` — a brief in the decomposition has no spec unit to trace to, or a seam or stub only works if another spec section says something it does not. The amendment is the decision, and it is the director's: this skill names the section that owes the change and never writes it. `/spec-author` files the same class from Seam alignment and its conformance gate, and the engineering-plan layer routes its own upstream contradictions here.
- `SURFACE_PARITY_GAP` — a brief claims an invariant that quantifies over a domain while its stub covers part of that domain. Class A.
- `MAP_CONFORMANCE_GAP` — the spec defines a surface its map entry does not claim, or omits one the entry claims it owns. Vision-gated.
- `VISION_AMENDMENT_NEEDED` — the spec needs a rule vision does not carry, or contradicts one it does. Vision-gated; escalates as a director call, since this skill never edits `vision.md`.
- `IMPLEMENTABILITY_GAP` — recomputed from the author's dry run, keyed by brief slug. Gates neither verdict; it blocks `/brief-author` for the slug it names while the rest of the roster stays authorable.
- `AUTHOR_GATE_DRIFT` — the recomputed coverage map disagrees with the author sidecar's `decomposition_gate.coverage`, or that block is absent from a sidecar that should carry it.
- `REMEDIATION_INCOMPLETE` — a prior blocker's fix landed where it was raised and never reached the sites coupled to it.
- `DECISIONS_PROVENANCE_GAP` — an arbitration made to close a prior blocker was never written to the decisions log, or the spec cites an entry that does not exist.
- `FEATURE_NONCONVERGENCE` — the round counter climbs while the open-blocker count does not fall. At this layer it is the empirical signature of an oversized spec.
- `HOIST_INCOMPLETE` — a deferred-surface entry left `features/README.md` but its substance is not in the artifact that was to absorb it.
- `STABLE_DISAGREEMENT` — two personas filed contradictory fixes on the same spec span.
- `OPEN_QUESTION` — a finding the orchestrator cannot auto-resolve: typically an internal contradiction where neither section is obviously canonical, or a spec rule that contradicts the `CLAUDE.md` / project-memory ledger (the user arbitrates "amend the spec or amend the ledger?").
- `FIX_INTRODUCED_PREMISE_INVERSION` — orchestrator's applied fix rewrote spec prose asserting a claim about the ledger, a design doc, an external API, or another spec section, but the claim does not survive verification. Working tree dirty.
- `POLISH_PLATEAU` — Tier-2 weight non-zero but ≤ floor (4). Non-blocking.
- `REPO_STATE_DRIFT` — `git rev-parse HEAD` changed mid-review. User re-runs.

`SPEC_SHAPE_FAILED` is the spec-layer-only class, registered in `_review-common/blocker-classes.md` under §Spec-only. The decomposition classes are shared with the vision layer and registered under §Decomposition.

## Usage

```
/spec-review [<spec-slug> | <spec-path>] [--personas <p1> <p2> ...]
```

**Examples:**

```
# Default — resolves the project's one spec
/spec-review

# By slug, in a specs/ tree
/spec-review typing-system

# Explicit path
/spec-review docs/spec.md

# Explicit personas (overrides default)
/spec-review --personas product architecture
```

## Argument parsing

Split `$ARGUMENTS` on whitespace. Classify each token:

- `--personas` → all subsequent non-path tokens are persona names.
- Token contains `/` or ends with `.md` → spec path. A path naming a directory resolves to `<dir>/spec.md` (the per-spec-folder layout `specs/<slug>/spec.md`).
- Otherwise → a spec slug, resolving to `specs/<slug>/spec.md`. There is no feature-name shorthand.

No argument → resolve by file presence: the single spec folder's `spec.md` when `specs/` holds exactly one, else `spec.md` at the repository root (`git rev-parse --show-toplevel`), or `spec.md` in cwd when not in a git repo. **No argument and several spec folders is ambiguous** — list the specs and ask which, the way the engineering-plan reviewer handles tracks. If the resolved file doesn't exist, stop and report (point the user at `/spec-author` to create it).

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
   ↓ runs /plan-lint as its deterministic floor; FAIL → emit STRUCTURAL_LINT_FAILED, stop
   ↓ then verifies required sections including ## Decomposition and its four subsections
   ↓ (per _spec-common/spec-format.md), banned-pattern absence, status-token absence inside
   ↓ the decomposition, implementation-creep absence, frontmatter shape;
   ↓ FAIL → emit SPEC_SHAPE_FAILED, stop
Round Memory Pass                (deterministic, no LLM judgment)
   ↓ loads ~/.claude/cache/review-state/<slug-key>.json;
   ↓ consults the spec-author sidecar at ~/.claude/cache/author-state/<slug-key>.json
   ↓ and records counts of author-verified claims for Stage 2 to skip;
   ↓ computes round_number, prior_blockers, recently_resolved_blockers,
   ↓ open_blocker_history; runs the non-convergence tripwire
Stage 1: Ground truth pass       (deterministic, mostly mechanical; 1d is light LLM judgment)
   ↓ produces audit_report grounding the spec in INTERNAL consistency + the CLAUDE.md /
   ↓ memory ledger + design docs + external-API wrappers + data state,
   ↓ plus the three named decomposition checks, the remediation-completeness pass, and —
   ↓ where vision.md exists — the Vision trace and the off-model Map-conformance prosecutor
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

### Deterministic floor — `/plan-lint`

Runs first inside this gate, before the checks below, exactly as the sister reviewers run it:

```bash
python3 ~/.claude/skills/plan-lint/lint.py <spec-path>
```

Exit 0 → proceed to the shape checks. Exit 1 → stop and emit `STRUCTURAL_LINT_FAILED` with the lint output verbatim; no persona prosecution runs against a structurally broken spec. Exit 2 → re-check the path, then treat a persistent error the same way. A spec with **no `## Decomposition` section at all** draws a WARN rather than a FAIL here, at lint's legacy-warn severity for a document already on disk; the shape checks below still file the missing section as HARD.

### Shape checks

The required shape is defined in `~/.claude/skills/_spec-common/spec-format.md`. Apply these checks:

### Required sections (core, in order)

1. **Frontmatter** — `Created:` and `Last updated:` dates present (YYYY-MM-DD). `Status:` field OPTIONAL — present only when mid-cycle. Any other `Status:` value is a SOFT MEDIUM finding.
2. **`## Overview`** — heading present; body non-empty.
3. **`## Domain model & core concepts`** — heading present; body non-empty.
4. **`## Invariants & business rules`** — heading present; ≥1 bullet.
5. **`## Feature areas`** — heading present; ≥1 entry — a bullet or a `###` subsection; both renderings are canonical per `_spec-common/spec-format.md`.
6. **`## Non-goals & scope bounds`** — heading present; ≥1 bullet (or an explicit justified "None").
7. **`## Decomposition`** — heading present, carrying all four subsections non-empty and in order: `### Seams` (≥1 seam, each with a predicate clause), `### Briefs` (table with Slug / Scope / Intent / Depends on), `### Scope stubs` (one block per Briefs-table slug, all three fields), `### Coverage` (table with Spec unit / Brief / Proof). A missing subsection, a subsection out of order, or a Briefs-table slug with no stub is `[HARD: malformed Decomposition]`.
8. **`## Glossary`** — heading present; ≥1 entry (or `None.` when the Domain model fully defines the vocabulary).

Optional sections (`## Open questions`, `## Roadmap / milestones`, `## Analytics & observability`, `## External integrations`) are not required; when present they must be non-empty. Their order is fixed too: `## Open questions` sits directly after `## Glossary`, ahead of the other three, which hold the order above.

Each missing/empty core section is `[HARD: missing required section]`.

Shape is the only judgment here — whether the coverage table is *complete* and whether a predicate *decides* anything is Stage 1's decomposition checks, not this gate's.

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

**Status tokens inside `## Decomposition`** (HARD per occurrence; applied to that section only, since "shipped" in a Feature area may be ordinary product prose):

```
(?i)\b(shipped|next up|in flight|parked|on loan|deferred until|TODO|not yet written|awaiting)\b
(?i)\b\d{4}-\d{2}-\d{2}\b
```

The section states what is permanently true about the boundary; anything that flips as briefs ship belongs in `features/README.md`. A token match here is a shape failure; leaks the regex misses are Stage 1's `decomposition-status-leak` check.

`owed` is a vision-layer token only. At the spec layer `*Outcomes owed*` is the Scope-stub field name `_spec-common/spec-format.md` mandates, so the word carries no lifecycle claim here; `/plan-lint` splits the two lists the same way.

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

- **Slug** — `<project>__<spec-slug>__spec` where `vision.md` exists at the repository root, `<project>__spec` where it does not, per `_spec-common/spec-format.md` § Sidecar keying. `<project>` is the repo-root basename; `<spec-slug>` is the `specs/<slug>/` directory name of the spec under review. The gate is file presence, never a question, and it is the same gate `/spec-author` used to write its side.
- **Extra field** — `author_sidecar_consulted: { sidecar_path, sidecar_present, claims_verified_skipped, self_prosecution_findings_skipped, decomposition_gate_present }`, written every round per the consultation below.
- **Extra metric** — `per_round_metrics.round_<N>.cross_file_escalations`, since this layer escalates cross-file findings rather than applying them.
- **Extra metric** — `per_round_metrics.round_<N>.decomposition` ← the recomputed `units_total` / `units_claimed` / `units_excluded` / `brief_count` / `dag_depth`, so drift against the author's numbers is visible across rounds rather than only within one.
- **Blocker classes seen here** — `SPEC_SHAPE_FAILED` and the decomposition classes listed under § Active blocker classes, plus the universal `STABLE_DISAGREEMENT` / `OPEN_QUESTION` / `FIX_INTRODUCED_PREMISE_INVERSION`.

The spec layer's additional carry-forward source is the spec-author's sidecar. The author already verified claims and self-prosecuted; the reviewer consults the sidecar to skip re-prosecuting what the author arbitrated.

### Author sidecar consultation

Read `~/.claude/cache/author-state/<slug-key>.json` if it exists, resolving `<slug-key>` by the same vision gate. Extract `claims_verified` count + `ground_truth_log` entries with outcome `verified` / `verified_softened` / `corrected` (Stage 2 MUST NOT re-prosecute these as hallucinations), `self_prosecution_findings` (MUST NOT re-file), `authoring_residual` (informational only, not blockers), and `decomposition_gate` (the author's coverage counts, adversary verdicts, and dry-run gaps — Stage 1's decomposition checks recompute against these). If the sidecar is absent (the spec was hand-written), record `sidecar_present: false`; Stage 2 has full prosecution latitude and Stage 1 recomputes from scratch without filing `AUTHOR_GATE_DRIFT`. If the sidecar's `last_spec_sha256` differs from the current spec's SHA, the user edited the spec manually — treat `claims_verified` as a hint, not a binding skip-list.

**Legacy key under a newly-arrived `vision.md`.** State written before the project grew a `vision.md` sits under the unslugged key. Read it as carry-forward for the spec it describes, write forward under the slugged key, and say so in the verdict. Never merge two specs' round histories into one file.

### Non-convergence tripwire

Deterministic, runs here, and reads `open_blocker_history` — which the shared file appends every round without exception. Fires `FEATURE_NONCONVERGENCE` (HIGH) when `round_number >= 5` AND (the open-blocker count is not strictly decreasing over the last 3 rounds OR `open_question_count >= 8`; cold-history fallback: `prior_blockers` length ≥ 8).

At this layer the round counter climbing while blockers hold flat is the empirical signature of an **oversized spec** — one carrying surface that belongs to a boundary it has not admitted. The finding names the rounds and counts, and pairs with whatever `DECOMPOSITION_SURFACE_EXCESS` found: the resolution is the director's, either a split or an explicit size acceptance in a bound decisions entry. Exempt from ordinary carry-forward; a size-acceptance entry re-arms the trigger at acceptance-round + 5 rather than silencing it.

### Persist on exit

Per the shared file, plus `author_sidecar_consulted` ← what was consulted this round, and the recomputed decomposition metrics.

When Stage 3 fixes changed the decomposition or any span the author sidecar's `decomposition_gate` describes, also reconcile that sidecar — refresh `decomposition_gate.coverage` and `last_spec_sha256` to the post-fix artifact, per `blocker-classes.md` § Artifact-gate classes → `AUTHOR_GATE_DRIFT`'s resolution — so the next round's recomputation measures drift against reality instead of filing a spurious gap over the reviewer's own edits.

---

## Stage 1 — Ground truth pass (MANDATORY, MOSTLY MECHANICAL)

Produces an `audit_report`. Stage 2 personas MUST NOT re-prosecute facts verified here.

**There is NO repo grep for path:line** (Stage 0 enforced no implementation creep). **The upstream trace exists only under `vision.md`** — where it is absent, nothing sits above the spec and the Vision trace and Map conformance sub-passes do not run. Stage 1's targets are the spec's own internal coherence, its decomposition, the invariant ledger, design docs, external-API wrappers, data state, and the spec map where one exists.

**LLM-judgment carve-out.** Sub-passes 1a-1c are mechanical (file Reads, regex, substring overlap). Sub-pass 1d makes lightweight LLM judgment calls (invariant verifiability, Non-goal reality) no regex captures, each filed SOFT MEDIUM under the corresponding P-SPEC-* policy. The named decomposition checks below are mechanical except where noted; Map conformance is the one sub-pass that spawns an agent.

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

### Decomposition checks (three named checks, mechanical)

Run against `## Decomposition`, per `~/.claude/skills/_decompose-common/decomposition-principles.md`. Each is named so it can be cited in a verdict and recomputed the same way twice.

**`decomposition-coverage`.** Enumerate the spec's units **from the spec, never from the Coverage table** — every invariant under §Invariants & business rules, every §Feature areas entry, every §Non-goals entry, and every Domain-model or Glossary term owing authored content. Enumerating from the table is what makes an omission invisible. Then:

- A unit with no row, or a row whose disposition is neither a slug in the Briefs table nor an exclusion → `DECOMPOSITION_COVERAGE_GAP` (HARD). The rule that admits no third state is claimed-versus-excluded; "to be assigned" is a gap wearing a disposition's clothes. `excluded by <named seam>` is the ordinary rendering of exclusion, and the two named forms below are the same disposition written in their own columns' terms.
- A claimed invariant whose Proof cell is empty → `DECOMPOSITION_COVERAGE_GAP` (HARD). `Director review — <reason>` is exclusion in the Proof column and counts only where no authored artifact could carry the check; a Proof cell pointing at a brief absent from the Briefs table does not count at all. An invariant whose falsifier ranges over more than one brief is claimed by the conformance brief in the Brief column, and a Proof cell naming that same brief is correct rather than a pooled sink.
- A Non-goal with no Brief cell → `DECOMPOSITION_COVERAGE_GAP`; `structural — no brief could trespass it` is exclusion in the Brief column and is a valid disposition.
- Each Coverage row's unit text quotes a unit the spec actually carries, and each claiming slug appears in the Briefs table. A row citing a unit no section states is a false claim about the document it sits in → `DECOMPOSITION_COVERAGE_GAP`. This is the reverse direction of the enumeration above, and both run: one catches an omitted unit, the other a stale row.
- **A unit the director deferred is resolved by deferral, not by a HARD.** The evidence is a pair: an entry in `features/README.md`'s Deferred spec surface list, and an Active `Status: bound` entry in the decisions log naming the deferral's destination. Verify both exist and record the pair. Either half alone is the gap, filed as `DECOMPOSITION_COVERAGE_GAP` naming the missing half.
- Compare the recomputed counts against the author sidecar's `decomposition_gate.coverage`. Disagreement, or a sidecar that should carry the block and does not → `AUTHOR_GATE_DRIFT` (the gate did not run, or a hand-edit moved the spec out from under its numbers). This does not by itself mean a coverage gap; a genuine gap fires its own class.

**`decomposition-status-leak`.** Read the section for churn the Stage-0 token regex missed: lifecycle framing in prose ("until the terrain spec lands", "for now"), counts of what exists yet, folder-existence pointers, dates, and park/loan phrasing. Each occurrence → `DECOMPOSITION_STATUS_LEAK` (HARD), with the fix naming `features/README.md` as the destination. A unit another domain owns is excluded by a named seam; that is a permanent fact about the boundary and is never a leak.

**`seam-split-line`.** For every seam: it carries a predicate, and the predicate decides the units the Coverage table assigns by it. Hand the predicate each such unit and check it returns a side with no further argument. Fails → `SEAM_PREDICATE_MISSING` (HARD), naming which of the three failure shapes applies: examples instead of a test, a predicate a neighboring seam also satisfies, or a seam needing two predicates (which is two seams, and splitting it is the fix).

Then check each seam against the Active `Status: bound` entry that fixed it. A predicate that has drifted from its entry is the re-derivation failure `FIX_INTRODUCED_PREMISE_INVERSION` names — the same class `/spec-author` files when its own re-derive moves a bound boundary — and it is filed against the seam, not softened into a coverage finding.

**Structural oversize.** Also compute the structural signal that says the spec itself is too big, which files `DECOMPOSITION_SURFACE_EXCESS`: the spec carries material **on loan for more than one unwritten spec** — read from `specs/README.md` or `features/README.md`'s deferred-surface list, not from the spec, which may not say so. A spec needing two predicates against one neighbor is not this class; it is a seam that is two seams, and `seam-split-line` files it as `SEAM_PREDICATE_MISSING`.

Alongside it, recompute the author's numeric estimator (`brief_count >= 9`, `dag_depth >= 4`, `open_seam_decisions >= 4`); a breach files the same class. `dag_depth` is the longest dependency path through the Briefs table counted in edges, with the conformance sink excluded — the format mandates the sink and its depends-on-every-brief edges, so counting it would tax every spec one level for its required shape. `open_seam_decisions` is the count of seam questions surfaced at Seam alignment and not bound in either decisions log. Every form is a **director decision** — never split a spec here, and never narrow the decomposition to clear it. The finding names the breached condition and the two paths: split, or accept the size in a bound decisions entry naming what was accepted; an Active size-acceptance entry covers recomputed values at or below the ones it names, and Priority-1 carry-forward drops the finding against it.

**Hoist check.** For each entry the state sidecar says was hoisted into this spec at its authoring pass, verify the substance is present. Absent → `HOIST_INCOMPLETE`, severity inherited from the parked item.

### Vision trace (runs only when `vision.md` exists)

The spec layer's analog of the engineering-plan reviewer's Brief Trace, and the reason a map entry is binding rather than advisory. Read `vision.md` and the map entry for the spec under review. Three directions, all three required:

- **Every surface the map assigns this spec is present in it.** Missing → `MAP_CONFORMANCE_GAP` (HARD).
- **Every surface the spec defines is one the map assigns it.** A surface a neighbor's entry claims → `MAP_CONFORMANCE_GAP` (HARD). A surface no entry claims at all → `VISION_AMENDMENT_NEEDED`: vision has to grow or the spec has to drop it, and that is the director's call.
- **Every vision section the entry claims this spec covers is covered.** Uncovered → `MAP_CONFORMANCE_GAP`.

A spec that contradicts a vision rule is *amending vision*. File `VISION_AMENDMENT_NEEDED` naming the contradicted vision section verbatim and escalate; this skill never edits `vision.md`, and neither does the session agent without the director's say-so.

Output a `Vision Trace` block: entry consulted, surfaces assigned, surfaces defined, the set difference in both directions, vision sections covered.

### Map conformance prosecutor (runs only when `vision.md` exists)

The other layers run an off-model Brief-conformance Prosecutor at both author and review time; this is the spec layer's. The Vision trace above is the mechanical set comparison — this is the judgment call the set comparison cannot make: whether each split-line predicate in the entry is **honored** by the rules the spec actually writes, on concrete rules rather than in the abstract.

Spawn one agent with the prosecutor prompt in `~/.claude/skills/_review-common/brief-conformance-prosecutor.md`, substituting `vision.md` plus the map entry for the upstream artifact and the spec under review for the artifact under judgment. **The model pin is that file's § Model pin, applied verbatim** — an explicit off-model `model` override, default `sonnet`, `opus` when the session is already Sonnet, never inherited, and recorded as `conformance_gate_model` in the review state. The whole point is that the judge does not share the drafter's priors; a verdict with no recorded pin is treated as un-pinned and its independence claim does not hold.

Findings file `MAP_CONFORMANCE_GAP`. This is the backstop that keeps split lines honest — vision's map is re-tested against a real rule every time a spec is authored against it.

### Remediation completeness (mechanical)

Every other reviewer runs one; this one does too. For each entry in `prior_blockers`, check the fix reached the sites coupled to it, not only the section that raised it. Coupled sites at this layer:

- A fix to an invariant → §Feature areas and §Domain model wherever they lean on it, **and** its rows in the Coverage table and the stub of the brief claiming it.
- A fix that moved a unit across a seam → both stubs, both Coverage rows, the seam's predicate, and the `Depends on` edges either side.
- A fix that added or dropped a brief → the Briefs table, its stub, every Coverage row citing it, every `Depends on` naming it, and the conformance sink's dependency list.
- A fix that changed a boundary → the map entry's split line where `vision.md` exists (escalated, not edited).

Incomplete → `REMEDIATION_INCOMPLETE`, severity inherited from the original blocker; the surviving sites seed Stage 2 rather than waiting for a persona to rediscover them. An arbitration made to close a prior blocker with no bound entry in the spec's decisions log, or a spec citing an entry that does not exist, → `DECISIONS_PROVENANCE_GAP` (HIGH). Both are exempt from ephemeral carry-forward: each is an assertion about the completeness of the carry-forward record itself.

### Implementability recomputation (mechanical)

Read `decomposition_gate.dry_run.gaps_by_slug` from the author sidecar. For each gap, check whether the spec now answers the question. Answered → drop it and record the drop, so `/brief-author` unblocks for that slug. Still open → carry it forward as `IMPLEMENTABILITY_GAP` keyed by the same slug. Gaps do **not** gate the verdict; they gate `/brief-author` for the slug they name. Where no sidecar exists, run the dry run per `_decompose-common/decomposition-principles.md` § The imagined-downstream-author dry run rather than skipping the check.

### 1e. Stage 1 mechanical fixes

Apply unambiguous fixes immediately (forbidden style-class patterns from Stage 0 SOFT findings; stale `Last updated` when content changed; trivial statement→question conversions; a status leak whose removal changes no meaning). Emit `Stage 1 fixes applied:`. HARDs that can't be auto-fixed pass to Stage 2 as `pre_resolved_hard_findings`.

**Never fix a coverage gap by deleting the unit, narrowing a Non-goal, or widening a seam's predicate to swallow it.** Those are the shapes that make the table read clean while the narrowing survives — escalate instead.

### Stage 1 output (audit_report)

Bulleted facts: spec_path, HEAD sha; internal_consistency (terms_checked, contradictions, hard_findings); ledger_conformance (entries_consulted, contradictions, honored_invariants); design_doc_consistency (docs_consulted, contradictions); spec_style (invariant_verifiability, non_goal_reality, domain_scope, open_question_form, cohort_citation findings); decomposition (units_total, units_claimed, units_excluded, units_resolved_by_deferral, stale_coverage_rows, proof_owners_missing, seams_without_predicate, seams_drifted_from_bound_entry, status_leaks, oversize_signals, author_gate_drift); vision_trace (entry, surfaces_assigned, surfaces_defined, differences) or `vision_present: false`; map_conformance (model pinned, findings) or `not_applicable`; remediation (prior_blockers_checked, incomplete, provenance_gaps); implementability (gaps_carried, gaps_dropped); stage_1_fixes_applied; pre_resolved_hard_findings; author_sidecar_consulted.

---

## Stage 2 — Persona prosecution (parallel agents, fix-list output)

Read `personas/ai-development.md` once for context. Resolve personas (auto or explicit). Launch one Agent per persona, **all in parallel in a single message**, each with `model: "sonnet"` per `_review-common/agent-prompt.md` § Model pin — never inherit the session model; record `persona_model` in the review state. M agents.

### Spawn agents

Use `~/.claude/skills/_review-common/agent-prompt.md`. Substitute:

- `{persona_name}` — the persona
- `{audit_report_bullets}` — Stage 1 audit (compact bullets)
- `{pre_resolved_hard_findings}` — Stage 1 HARDs
- `{active_critical_pair_subset}` — `P-CLASS-SCOPE, P-FULL-FILE, P-SPEC-WHAT-NOT-HOW, P-SPEC-INVARIANT-VERIFIABILITY, P-SPEC-INTERNAL-CONSISTENCY, P-SPEC-INVARIANT-CONFORMANCE, P-SPEC-DOMAIN-DEFINITION, P-SPEC-DOMAIN-SCOPE, P-SPEC-NON-GOAL-REALITY, P-SPEC-DECOMPOSITION-TRUTH, P-SPEC-SEAM-PREDICATE, P-SPEC-MAP-AUTHORITY`
- `{target_locator}` — the spec path
- `{how_to_get_it}` — `Read <spec_path>`; agents Read source-of-truth files (CLAUDE.md, project memory, `vision.md`, the spec's decisions log, design docs, external-API wrappers, persona files) on demand. Never `handoffs/`.
- `{pr_description_or_brief_mapping}` — the spec's map entry in `vision.md` where one exists, verbatim; `N/A (no vision.md — the spec is the root artifact)` otherwise
- `{skill_specific_extensions}` — *Imagine you are the brief author who must turn one of this spec's scope stubs into a brief. Where does the stub leave you guessing? Where is an invariant so unverifiable that two brief authors would commit to different success criteria? Where does a seam's predicate fail to tell you which side the next rule lands on? Where does the Coverage table assign a unit to a brief whose stub plainly does not cover it? Where does a feature area secretly import an architectural commitment that belongs in an engineering plan? Where does a Non-goal feel like a platitude that won't actually stop scope creep? Where would a downstream brief have to invent product policy because the spec ducked the question? Where do two spec sections quietly contradict each other, or a stub contradict the section it claims?*
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

**Cross-file fix scope (spec layer).** The spec author owns ONLY the spec under review. A persona fix whose substance binds beyond it is never auto-applied to the other file:

- **Mention of `CLAUDE.md`** → DO NOT auto-edit. Surface as `OPEN_QUESTION`: "fix would amend CLAUDE.md — user arbitrates whether the ledger changes or the spec is re-scoped."
- **Mention of project-memory paths** (`~/.claude/projects/<project>/memory/<file>.md`, `MEMORY.md`, any path under `memory/`) → DO NOT auto-edit. Surface as `OPEN_QUESTION`.
- **Mention of a project design doc** (`docs/*`, `context/*`) → DO NOT auto-edit. Surface as `OPEN_QUESTION`: "fix would amend `<doc>` — user arbitrates which is canonical."
- **Mention of `vision.md` or its spec map** → DO NOT auto-edit. Surface as `VISION_AMENDMENT_NEEDED`: the boundary is a director call, and a spec that quietly rewrites the map it is judged against defeats the trace.
- **Mention of a neighboring `specs/<slug>/spec.md`** → DO NOT auto-edit. Surface as `MAP_CONFORMANCE_GAP` naming both sides; moving surface between two specs is one edit to two files and belongs in the neighbor's own authoring run.
- **Mention of `features/README.md` or `specs/README.md`** → DO NOT auto-edit, and never resolve a status leak by writing the leaked content into the sidecar yourself. Surface as `OPEN_QUESTION` naming the destination.

Record cross-file escalations in `cross_file_escalations[]`.

**Authority order when artifacts disagree** (highest to lowest):

1. `CLAUDE.md` and project memory — bound-invariant ledger; the spec honors it, never silently overrides.
2. `vision.md`'s spec map, where `vision.md` exists — what this spec owns and where its boundaries fall.
3. Active `Status: bound` entries in the spec's decisions log — the seams already arbitrated.
4. Project design docs — grounding the spec stays consistent with.
5. The spec under review.

When a finding reveals contradiction with an upstream source, the spec aligns to it OR the user arbitrates an explicit amendment. Contradiction *between* the ledger and a design doc escalates as `OPEN_QUESTION`; between the spec and vision, as `VISION_AMENDMENT_NEEDED`.

**Forbidden fixes:**

- Weakening the spec (dropping an invariant, softening verifiability, removing a Non-goal to bypass enforcement) → escalate as `OPEN_QUESTION`.
- Auto-editing `CLAUDE.md`, project memory, `vision.md`, a neighboring spec, or a design doc → escalate per the cross-file table above.
- "Leaving it for the brief" — if the spec is unclear now, the brief author will hallucinate.
- Adding implementation detail to fix an invariant-verifiability finding (P-SPEC-WHAT-NOT-HOW retracts this; the right fix is an *observable* condition, not a how).
- **Closing a coverage gap by deleting the unit, widening a seam's predicate to swallow it, or inventing a brief slug with no stub.** Each makes the table read clean while the narrowing survives, which is the exact failure the table exists to catch. Assign it, exclude it by a seam whose predicate genuinely decides it, or escalate.
- **Splitting the spec.** `DECOMPOSITION_SURFACE_EXCESS` and `FEATURE_NONCONVERGENCE` are director decisions; the orchestrator produces the finding and never applies a split.

### Post-fix premise verification

Per `~/.claude/skills/_review-common/orchestrator.md` § Post-fix premise verification. The claims that matter at this layer: internal cross-section references, invariant-ledger references, coverage-table and seam citations, map-entry references, design-doc references, cohort and data claims, and external-API claims. A fix that edits a section the Coverage table enumerates re-checks that section's rows — an invariant reworded above the table and stale inside it is a citation to a unit that no longer exists.

### Same-round focused re-prosecution

Per `~/.claude/skills/_review-common/orchestrator.md` § Same-round focused re-prosecution — one pass, bounded. The third skip condition here is *cross-file escalations = 0* rather than cross-file edits, since this layer escalates rather than editing.

### 3e. Classify remaining unresolved findings

Active classes: `SPEC_SHAPE_FAILED`, `SPEC_AMENDMENT_NEEDED`, `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `FIX_INTRODUCED_PREMISE_INVERSION`, `POLISH_PLATEAU`, `REPO_STATE_DRIFT`, plus the decomposition and vision-gated classes under § Active blocker classes.

**Class A findings** — `SPEC_NONGOAL_TRESPASS`, `SURFACE_PARITY_GAP`, `REMEDIATION_INCOMPLETE`, `DECISIONS_PROVENANCE_GAP`, `FEATURE_NONCONVERGENCE` — are exempt from the carry-forward retraction below. `principles.md` § Cross-artifact authority order places the spec above the decisions logs that arbitrate its seams, so a bound entry cannot retract a finding about the spec's contract with itself. A bound decisions entry that itself trespasses a Non-goal does not protect the finding; the bound entry is the defect.

**Carry-forward consultation (durable-first, then ephemeral cache).**

- **Priority 1 — project decision log** (durable; if present). If the project keeps a decision record (a `decisions.md` beside the spec under review — the per-spec-folder layout — or `docs/decisions.md`, or `decisions.md` at root; nearest first), read it and search for entries whose subject substring-matches the finding's surface. A finding contradicting a bound entry → drop, recording `[CARRY-FORWARD via <decision-log>]` (when the log uses the `## Active` / `## Archived` split, only Active-section `Status: bound` entries count — skip `superseded`/`obsolete` entries; per `~/.claude/skills/_review-common/principles.md` § What counts as a bound entry). If no project decision log exists, skip Priority 1 (the spec layer has no mandated durable arbitration file — many projects won't have one).
- **Priority 2 — `recently_resolved_blockers` ephemeral cache** (state-file). For findings surviving Priority 1: if an entry's `carry_forward_until_round >= round_number` AND its `path_or_section` overlaps the finding's section/phrase, downgrade to `OPEN_QUESTION` with the prior `user_decision` surfaced verbatim; the persona's claim survives only if `current_reclassification_justification` was filed. (`path_or_section` is always a section heading, a quoted phrase, or a brief slug — the spec doesn't cite path:line, so overlap stays in name space.)

**Where `vision.md` exists, the decisions log is mandatory** and Priority 1 is never skipped: read the log beside the spec and `specs/decisions.md` alongside it. Its absence is a blocker rather than a degraded run, because a seam with no bound entry to read from is a seam being re-litigated every round — file `DECISIONS_PROVENANCE_GAP` and name the log that should exist.

### 3f. Render verdict

Per `~/.claude/skills/_review-common/blocker-classes.md` § Verdict gates → Spec review, which is the registry of record:

- **APPROVED** when ALL of:
  - Stage 0 exited clean (no `STRUCTURAL_LINT_FAILED`, no `SPEC_SHAPE_FAILED`)
  - Tier-1 weight = 0
  - Tier-2 weight ≤ 4
  - No `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `FIX_INTRODUCED_PREMISE_INVERSION`, `REPO_STATE_DRIFT`, `DECOMPOSITION_COVERAGE_GAP`, `DECOMPOSITION_STATUS_LEAK`, `SEAM_PREDICATE_MISSING`, `DECOMPOSITION_SURFACE_EXCESS`, `SPEC_NONGOAL_TRESPASS`, `SPEC_AMENDMENT_NEEDED`, `SURFACE_PARITY_GAP`, `MAP_CONFORMANCE_GAP`, `VISION_AMENDMENT_NEEDED`, `AUTHOR_GATE_DRIFT`, `REMEDIATION_INCOMPLETE`, `DECISIONS_PROVENANCE_GAP`, `FEATURE_NONCONVERGENCE`, `HOIST_INCOMPLETE`
- **NEEDS USER INPUT** otherwise.

**The verdict stays two-state.** `IMPLEMENTABILITY_GAP` gates neither: the gap is per-brief, so it blocks `/brief-author` for the slug it names while the rest of the roster stays authorable, which is more precise than a whole-spec third state. An APPROVED spec carrying gaps is a normal outcome and the verdict says which slugs are held.

Tier-1 weights: CRITICAL=8, HIGH=4, MEDIUM=2, LOW=1. Tier-2 floor: 4.

**Final line — verdict banner.** After the output block below, run the shared verdict-banner script and emit its output verbatim (`~/.claude/skills/_review-common/blocker-classes.md` § Verdict banner) as the **very last** thing in your response, so the verdict is visible without scrolling.

### 3g. Output

```
## Spec Review Complete: {spec_path}

**Round:** {round_number} {| `(round 1 — no prior state)` | `(loaded from cache: {n-1} → {n})`}
**Upstream:** {`vision.md § spec map, entry `{slug}`` | `none (no vision.md — spec is the root artifact)`}
**State source:** {`Loaded from ~/.claude/cache/review-state/{slug-key}.json` | `Round 1 (no prior state)`}
**Author sidecar:** {`consulted; N claims verified skipped; M self-prosecution findings skipped; decomposition_gate {present|absent}` | `absent (spec was hand-written)` | `present but SHA differs (treated as hint)`}
**Authoring mode warning:** {`none` | `sidecar reports authoring_mode: "draft" — /spec-author --draft skipped its gates, ground-truth, and self-prosecution`}
**Personas:** {names}
**Stage 0 shape check:** PASS / N hard findings (sections / Decomposition subsections / forbidden patterns / status tokens / implementation creep)
**Stage 1 audit:** internal_consistency PASS / N hard; ledger_conformance PASS / N hard; design_doc PASS / N hard
**Decomposition:** {units_claimed} claimed + {units_excluded} excluded of {units_total} ({n} resolved by deferral); {n} stale coverage rows; {n} invariants missing a proof owner; {n} seams without a predicate; {n} seams drifted from their bound entry; {n} status leaks; author-gate drift: {yes/no}
**Structural oversize:** {`none` | `{condition breached}`}
**Vision trace:** {`not applicable` | `PASS` | `{n} surfaces assigned but absent; {n} defined but unassigned; {n} vision sections uncovered`}
**Map conformance:** {`not applicable` | `PASS / {n} findings` (model `{conformance_gate_model}`)}
**Remediation completeness:** {n} prior blockers checked; {n} incomplete; {n} provenance gaps
**Implementability gaps:** {n} carried (slugs: {list}); {n} dropped as answered
**Non-convergence tripwire:** {`not armed (round < 5)` | `clear` | `FIRED — rounds {a}→{b}, open blockers {x}→{y}`}
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
- [DECOMPOSITION_COVERAGE_GAP] {unit} — neither claimed nor excluded / no proof owner; assign it, exclude it by a named seam, or defer it in features/README.md.
- [DECOMPOSITION_STATUS_LEAK] {span} — move to features/README.md.
- [SEAM_PREDICATE_MISSING] {seam} — {which failure shape}; write the predicate, split the seam, or merge it away.
- [DECOMPOSITION_SURFACE_EXCESS] {breached condition} — split the spec, or accept the size in a bound decisions entry.
- [SPEC_NONGOAL_TRESPASS] {stub} — drop the scope, or amend the Non-goal.
- [SPEC_AMENDMENT_NEEDED] {seam / stub / brief} — §{section} owes the rule it leans on; amend that section, or drop what needs it.
- [SURFACE_PARITY_GAP] {invariant} — {which brief covers what fraction of the domain}.
- [MAP_CONFORMANCE_GAP] {surface} — rewrite the map entry, move the surface, or re-cut the boundary.
- [VISION_AMENDMENT_NEEDED] {rule} — amend the contradicted vision section, or drop the spec surface needing it.
- [AUTHOR_GATE_DRIFT] recomputed coverage {a} vs sidecar {b} — reconcile the sidecar to the recomputed values.
- [REMEDIATION_INCOMPLETE] {prior blocker} — sites still unswept: {list}.
- [DECISIONS_PROVENANCE_GAP] {arbitration} — write the missing bound entry.
- [FEATURE_NONCONVERGENCE] rounds {a}→{b} with open blockers {x}→{y} — split, or accept the size.
- [HOIST_INCOMPLETE] {parked item} — carry the substance in, or restore the sidecar entry.
- [POLISH_PLATEAU] {finding} — non-blocking.
- [REPO_STATE_DRIFT] HEAD changed from {sha} to {sha}. Re-run.

### Implementability gaps (do NOT gate the verdict)
- `{brief-slug}`: {question}; {where it must be answered}. `/brief-author {slug}` stays blocked; every other slug is authorable.

### Spec Status: APPROVED / NEEDS USER INPUT
```

If `NEEDS USER INPUT`: the next step is **targeted edits to clear the listed blockers**, then re-invoke `/spec-review` (optionally triage with `/explain-blockers` or `/solve-blockers`). Do **not** re-run `/spec-author` to clear a handful of blockers (see the hard rule).

---

## Hard rules

- **Status-frontmatter check is mandatory and runs first.** A spec with `Status: needs-user-input` is mid-cycle; refuse and point at `/spec-author`.
- **Stage 0 Structural Shape Check is mandatory.** A spec with missing required sections, a malformed `## Decomposition`, status tokens inside it, or implementation creep is unprosecutable.
- **Stage 1 is mandatory.** Its targets are internal consistency, the decomposition, the invariant ledger, design docs, external-API reality, and data state — plus the Vision trace and the Map-conformance prosecutor where `vision.md` exists. Where it does not, those two sub-passes do not run and nothing above the spec is looked for.
- **The three named decomposition checks are mandatory and enumerate from the spec, never from the Coverage table.** A universe read off the table cannot show what the table omitted.
- **Map conformance runs off-model.** The pin in `_review-common/brief-conformance-prosecutor.md` § Model pin is applied verbatim and recorded; an unrecorded pin means the independence claim does not hold.
- **Round Memory Pass is mandatory.** State file at the vision-gated key under `~/.claude/cache/review-state/` (NOT in the repo). The non-convergence tripwire runs there every round.
- **Author sidecar consultation is mandatory when the sidecar exists.** Re-prosecuting author-verified claims without a concrete upstream-change citation is forbidden. Recomputing the coverage map is not re-prosecution — it is the gate check, and disagreement files `AUTHOR_GATE_DRIFT`.
- **Orchestrator verifies its own edits.** Post-fix premise verification runs after Stage 3d, before classification.
- **Cross-file fix scope is mandatory when triggered.** Mentions of `CLAUDE.md` / project memory / a design doc escalate as `OPEN_QUESTION`; `vision.md` escalates as `VISION_AMENDMENT_NEEDED`; a neighboring spec escalates as `MAP_CONFORMANCE_GAP`. This skill edits ONLY the spec under review.
- **Never split a spec, and never resolve a decomposition finding by narrowing.** Splitting is the director's call; deleting a unit, widening a predicate to swallow it, or inventing a slug with no stub makes the table read clean while the narrowing survives.
- **Same-round focused re-prosecution is mandatory** when ANY of: Stage 3d fixes > 0, cross-file escalations > 0, or post-fix premise verification falsified-claim count > 0. Bounded: exactly one re-pass.
- **Stage 2 agents return fix lists; never edit files.** All edits applied by the orchestrator in Stage 3.
- **Never** mark APPROVED while any **gating** blocker class is non-empty — the list in § 3f, which is the registry's Spec-review gate. `IMPLEMENTABILITY_GAP` and `POLISH_PLATEAU` are outside it by construction and an APPROVED verdict carrying either is a normal outcome.
- **Never** weaken the spec to resolve a finding (drop an invariant, soften verifiability, remove a Non-goal). That's `OPEN_QUESTION`.
- **Always** quote verbatim from the spec, ledger, design doc, or audit_report when justifying a finding.
- **No multi-round inner loop.** The same-round re-prosecution is exactly one pass over diff hunks.
- **Do not re-run `/spec-author` to clear a completed review.** On `NEEDS USER INPUT`, the next step is targeted edits, then re-invoking `/spec-review`. Re-run the author skill only for the mid-cycle `Status: needs-user-input` refuse path, or a wholesale re-author (ask in plain language).

## Compliance self-check (before rendering verdict)

- [ ] Status-frontmatter check ran first.
- [ ] Stage 0 ran `/plan-lint` first, then the shape checks; required sections verified including `## Decomposition` and its four subsections; banned, status-token, and implementation-creep patterns absent.
- [ ] Round Memory Pass ran; the state key resolved by the vision gate; reviewer state loaded; author sidecar consulted (or marked absent); non-convergence tripwire evaluated.
- [ ] Stage 1 ran in full: internal consistency, ledger conformance, design-doc consistency, spec style supplements, the three named decomposition checks, structural oversize, hoist check, remediation completeness, implementability recomputation.
- [ ] Coverage units enumerated from the spec, not from the Coverage table.
- [ ] Vision trace and Map conformance ran, or `vision.md` confirmed absent and both recorded as not applicable.
- [ ] Map-conformance prosecutor ran off-model with its pin recorded.
- [ ] Stage 2 spawned all M persona agents in parallel.
- [ ] Stage 3 applied critical-pair retractions before applying fixes.
- [ ] Post-fix premise verification ran on orchestrator-rewritten prose, including coverage-table and seam citations.
- [ ] Same-round re-prosecution ran (or skip conditions met and recorded).
- [ ] Carry-forward consultation: Priority 1 (project decision log, if present) then Priority 2 (state-file); Class A findings exempted.
- [ ] Verdict template includes all metric lines, even when count = 0.
- [ ] Cross-file fix scope checked: CLAUDE.md / memory / design docs → `OPEN_QUESTION`; `vision.md` → `VISION_AMENDMENT_NEEDED`; a neighboring spec → `MAP_CONFORMANCE_GAP`.
- [ ] State file persisted with new round entry appended, `open_blocker_history` included.
- [ ] Verdict banner: the script ran (with `--skill`), its fenced stdout ends the response, nothing follows it.

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
- **No argument and several spec folders under `specs/`:** ambiguous. List the specs and ask which to review. Never guess.
- **`vision.md` absent:** every per-system behavior is off — unslugged state key, no Vision trace, no Map conformance, no mandatory decisions log, no upstream. The decomposition checks still run: a single-spec project still owes a coverage table.
- **`vision.md` present, no map entry for this spec:** `MAP_CONFORMANCE_GAP` naming the missing entry, and the Vision trace records what it could not check. Point the user at `/vision-author <slug>`.
- **`vision.md` present, no decisions log beside the spec:** `DECISIONS_PROVENANCE_GAP`. The log is mandatory at this layer; without it every seam is re-litigated each round, which is the failure the class names.
- **Spec has no `## Decomposition` section at all:** `/plan-lint` warns rather than fails, and Stage 0's shape check files the missing section as HARD `SPEC_SHAPE_FAILED`. The fix is a `/spec-author` run that adds it, not a review-side patch.
- **Author sidecar carries no `decomposition_gate` block:** `AUTHOR_GATE_DRIFT`, and Stage 1 recomputes the coverage map from scratch. The review still completes.
- **A coverage gap whose right home is a spec nobody has written:** exclude it by a named seam with its predicate — true today and after that spec lands — and let `features/README.md` carry the fact that the owner does not exist yet. Never leave the unit unassigned, and never write the absence into the spec.

---

## Relationship to sister skills

- **`/vision-review`** prosecutes the layer above where `vision.md` exists, and its map-conformance stage checks every shipped spec against its entry. This skill is where a split line is finally tested — on a concrete rule, each time a spec is authored against it — the same way the chunk-plan layer is what finally proves an engineering plan's DAG. A boundary defect found here belongs upstream, in the next `/vision-author` run.
- **`/spec-author`** writes the spec and the author sidecar this skill consults. The author runs its gates, ground-truth verification, and self-prosecution at write time; this skill prosecutes what the author missed, what the user introduced via manual edits since, and whether the author's own gate numbers still hold.
- **`/brief-author` and `/brief-review-v2`** consume the spec as their upstream master: the author reads its `## Decomposition` stub for the feature under work, and the reviewer traces brief Goals to spec capabilities and checks brief Non-goals against spec promises. `/brief-author` refuses for a slug carrying an open `IMPLEMENTABILITY_GAP`. A spec defect surfaced at the brief layer belongs upstream — feeding back into the next `/spec-author` invocation.
- **`/engineering-plan-review-v2`** and **`/plan-review-v2`** inherit the spec transitively through the brief.

**No separate Imagined-Implementer phase.** `/engineering-plan-review-v2` runs one because its plan pre-decides cross-chunk wiring for *multiple* downstream chunk plans. The spec's downstream is many *independent* briefs, each authored and reviewed on its own. The imagined-brief-author lens runs at authoring time and is recomputed in Stage 1 against the sidecar's gaps; the same lens also folds into Stage 2's `{skill_specific_extensions}` so every persona reads the spec as the brief author will.

This skill exists to give the spec — and the decomposition it carries — the same adversarial review surface the brief, engineering plan, and chunk plans already enjoy.
