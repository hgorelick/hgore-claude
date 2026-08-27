---
name: vision-review
description: Adversarial single-pass review of a project's `vision.md` — the root source-of-truth every spec, brief, and plan descends from — prosecuting its spec map against the format, its own internal consistency, and the specs already shipped below it. Applies fixes directly and returns CLOSED, APPROVED, or NEEDS USER INPUT with labeled blockers. Use after `/vision-author` lands a clean draft. Sister to `/spec-review`, `/engineering-plan-review-v2`, `/brief-review-v2`.
user-invocable: true
---

# Vision Review — Staged Single-Pass

Vision is the root of the artifact lifecycle in a project that decomposes into per-system specs: every spec, brief, engineering plan, chunk plan, and line of code descends from it. A spec map that leaves a mechanism unowned, draws a seam nobody can apply to the next rule, or claims a spec owns a surface that spec does not define will cascade through *every* spec, and the downstream review machinery repairs the descendants, never vision itself. This skill prosecutes vision through a Structural Shape gate plus three stages, with bounded same-round verification on orchestrator-rewritten prose. Never a multi-round inner loop — survivors of the bounded same-round re-pass land in the verdict and the user re-invokes.

This is the vision layer. Sister skills `/spec-review`, `/brief-review-v2`, `/engineering-plan-review-v2`, and `/plan-review-v2` review downstream artifacts. If the user asks for review of a spec / brief / engineering plan / chunk plan, redirect.

## Compatibility gate (runs first, before anything else)

This skill applies only where **`vision.md` exists at the repository root** (`git rev-parse --show-toplevel`, or cwd when not in a git repo). Detected by file presence, never by asking.

Where it is absent, decline in one line and stop:

```
No vision.md at the repo root — this project's root artifact is spec.md. Use /spec-review.
```

## Shared scaffolding

- `~/.claude/skills/_vision-common/vision-format.md` — the canonical vision shape, the map's entry shape, the roster's shape, drafting rules, claim emphasis, persona set (the format this skill prosecutes against)
- `~/.claude/skills/_decompose-common/decomposition-principles.md` — split-line predicates, the coverage-map contract, truth versus state, the imagined-downstream-author dry run, director arbitration (read through its **Vision layer** column)
- `~/.claude/skills/_review-common/principles.md` — stance, banned rationalizations, severity/tier, plan style rules
- `~/.claude/skills/_review-common/round-memory.md` — state file, load, capture priority, persist
- `~/.claude/skills/_review-common/orchestrator.md` — the shared Stage 3 spine
- `~/.claude/skills/_review-common/agent-prompt.md` — persona-agent prompt template
- `~/.claude/skills/_review-common/critical-pairs.md` — universal pairs (`P-CLASS-SCOPE`, `P-FULL-FILE`); the vision-specific `P-VISION-*` pairs are defined in this skill
- `~/.claude/skills/_review-common/blocker-classes.md` — blocker registry + the three-state verdict gate under § Verdict gates → Vision review

## Tribunal stance (vision-specific)

**THE INVARIANT LEDGER IS LAW; THE SHIPPED SPECS ARE FACT; THE MAP IS A PROOF, NOT A LIST.** Vision is the top of the *artifact* chain, so there is no upstream trace. Three things bind it:

1. **`CLAUDE.md` and project memory** carry the project's bound invariants, conventions, and — in most projects — the vocabulary table. A vision claim contradicting a bound invariant commits the project to a phantom, surfaced as `OPEN_QUESTION` (vision is amended, or the ledger is amended out-of-band; this skill never auto-edits the ledger).
2. **Internal consistency.** Because nothing sits above vision, its own sections are the only thing that can contradict it. A mechanism section, a cut-list rank, a ledger entry, and a map entry must agree. Internal contradiction is vision's highest-severity defect — every spec inherits it.
3. **The shipped specs — downstream, but concrete.** This is the one place a reviewer legitimately reads below its own layer. A map entry is a claim about a real file, so an entry that misdescribes a shipped `specs/<slug>/spec.md` is a falsifiable defect, not a matter of judgment.

**The map is a coverage proof.** It is prosecuted by enumerating units from `vision.md` and asking the map to dispose of each, never by reading the map and asking whether it looks complete. Silence is only falsifiable in the first direction.

**The map's strongest backstop is downstream, not here.** `/spec-review`'s map-conformance check re-tests every split line each time a spec is authored against it, on a concrete rule rather than in the abstract — the same structure as the engineering-plan layer, where the chunk-plan layer is what finally proves the DAG. This review is the first gate, not the last word.

## Active critical-pair policies (vision layer)

Applied silently in Stage 3; persona findings contradicting an active policy are retracted, not relitigated.

**P-VISION-WHAT-NOT-HOW — Vision states mechanisms; a spec specifies them.** A finding demanding a spec's exhaustive tables, catalogs, or per-case rulings be pulled up into vision is invalid; a finding flagging spec-level or engineering-level detail (path:line, schema columns, signatures, chunk decomposition) inside vision is valid. **Carve-out:** precision about a *product rule* — a formula, a threshold, a figure marked as a constraint — is vision's job, not creep.

**P-VISION-SPLIT-LINE-PREDICATE — A split line is one predicate sentence that decides the next unwritten rule.** A finding flagging an enumeration wearing a predicate's clothes, a predicate two seams both satisfy, or a seam needing two predicates is valid and HARD. A finding demanding a predicate be longer, hedged, or illustrated with examples is invalid — examples are what the failure shape looks like.

**P-VISION-COVERAGE-TWO-STATE — Every unit is claimed by exactly one entry or named in the unowned block.** A finding flagging a unit with neither disposition is valid and HARD. A finding proposing a third state — deferred, pending, to-be-assigned — is invalid; the moment "unassigned" is a legal cell the map stops being a proof.

**P-VISION-NO-STATUS — The map carries no lifecycle language.** A finding flagging a status token, a date, a count of what exists yet, or park/loan phrasing inside the map is valid. A finding demanding the map record which specs are shipped, next, or owed is invalid — that is `specs/README.md`'s job, and the two read together. **Carve-out:** an entry heading's `name unsettled` marker is format, not state (`vision-format.md` § Entry shape) — a finding filing `DECOMPOSITION_STATUS_LEAK` against it is invalid.

**P-VISION-MAP-IS-CLAIM — An entry is a falsifiable claim about a shipped spec.** A finding asserting divergence between an entry and a shipped spec is valid only when it quotes both sides verbatim. A finding asserting divergence against a spec that does not exist on disk is invalid — an unwritten spec cannot falsify anything.

**P-VISION-NAMES-ARE-DIRECTOR — Names are minted only on an explicit director call.** A finding proposing a spec name, a domain term, or an element name is invalid as a fix and routes to `OPEN_QUESTION`. A finding flagging a name used in vision that the vocabulary table does not bind is valid.

**P-VISION-CYCLES-LEGAL — A dependency cycle between two specs is resolved by a stated assumption, not by deleting the edge.** A finding demanding the graph be made acyclic by dropping a real dependency is invalid; a finding flagging a cycle where neither side states the assumption it rests on is valid.

**P-VISION-SECTION-BOUND — Vision's hand-shaped prose is not the map's collateral.** The whole document is prosecuted, but a finding whose fix is a wholesale rewrite of a mechanism section in order to clear a map defect is invalid; the valid fix is the narrowest edit that closes the defect, or an `OPEN_QUESTION` naming the passage that has to change.

## Active blocker classes

From `~/.claude/skills/_review-common/blocker-classes.md`:

- `VISION_SHAPE_FAILED` — Stage 0 short-circuited the review: required sections missing, a map entry malformed, banned content present, or frontmatter malformed. Unprosecutable until shape is fixed.
- `STRUCTURAL_LINT_FAILED` — `/plan-lint` short-circuited Stage 0's deterministic floor.
- `VISION_COVERAGE_GAP` — a vision section, vocabulary term, ledger item, or cut-list item no entry owns and no unowned line names.
- `SPEC_BOUNDARY_UNBOUND` — two entries claim one surface, or the imagined-spec-author dry run left a question unanswerable. **Gates CLOSED only; does NOT gate APPROVED.**
- `MAP_CONFORMANCE_GAP` — a shipped spec defines a surface its entry does not claim, or omits one the entry claims.
- `SEAM_PREDICATE_MISSING` — a seam with no applicable split-line predicate.
- `DECOMPOSITION_STATUS_LEAK` — churn language inside the map.
- `DECOMPOSITION_SURFACE_EXCESS` — an entry holding material on loan for more than one unwritten spec. Director decision.
- `VISION_AMENDMENT_NEEDED` — an entry needs a rule vision does not carry, or contradicts one it does.
- `HOIST_INCOMPLETE` — a parked item left `specs/README.md` but its substance is not in the authored spec.
- `REMEDIATION_INCOMPLETE` / `DECISIONS_PROVENANCE_GAP` — from the between-round completeness check over the prior round's blockers.
- `AUTHOR_GATE_DRIFT` — this skill's recomputation of an author-side gate disagrees with the author sidecar's recorded values.
- `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `FIX_INTRODUCED_PREMISE_INVERSION`, `POLISH_PLATEAU`, `REPO_STATE_DRIFT` — universal.

## Usage

```
/vision-review [<vision-path>] [<spec-slug>] [--personas <p1> <p2> ...]
```

**Examples:**

```
# Default — resolves to vision.md at the repo root
/vision-review

# Scope the map-conformance and dry-run passes to one entry
/vision-review typing-system

# Explicit personas (overrides default)
/vision-review --personas product architecture game-design
```

## Argument parsing

Split `$ARGUMENTS` on whitespace. Classify each token:

- `--personas` → all subsequent non-path tokens are persona names.
- Token contains `/` or ends with `.md` → vision path.
- Bare token matching a slug in the map → scopes Stage 1's map-conformance and dry-run sub-passes to that entry. The coverage audit still runs over the whole document; a scoped run that skipped coverage could not tell whether the scoping moved a unit out of every entry.
- Otherwise → ignored.

No path argument → default to `vision.md` at the repository root. If it doesn't exist, the compatibility gate has already declined.

## Persona resolution

**Persona files are project-scoped.** Resolve `personas/{name}.md` from the **root of the project vision belongs to** (`git rev-parse --show-toplevel`), never the skill directory. Read `personas/README.md` first where the project has one — it names which domain perspective owns which question. A project with no `personas/` directory cannot be prosecuted until it has one: stop and report.

### Default tribunal (no `--personas`)

- **`product.md`** — coherence of the decomposition against the product it decomposes, scope, contradictions with the bound-invariant ledger.
- **`architecture.md`** — internal consistency, dependency-graph soundness, whether the set of specs is a buildable whole rather than a partition that reads well.
- **`ai-development.md`** — plan-quality at the vision layer: coverage falsifiability, predicate applicability, banned content, drift into spec detail.
- **the project's domain-ownership persona** — the perspective whose domain decides where a mechanism belongs (`game-design.md` in a game project). Included wherever the project has one; boundary questions at this layer are design-ownership questions.

### Explicit personas

Load each from `personas/{name}.md`. Reviewed by every listed persona in parallel. Missing persona file → stop and report.

`ai-development.md` is referenced as supplementary context for every Stage 2 agent.

---

## Workflow

```
Compatibility gate               (deterministic, runs first)
   ↓ no vision.md at repo root → decline in one line; stop
Status-frontmatter check         (deterministic, hard short-circuit)
   ↓ Status: needs-user-input → REFUSE, point user back at /vision-author; stop
Stage 0: Structural Shape Check  (deterministic, hard short-circuit)
   ↓ runs /plan-lint as its deterministic floor, then verifies required sections
   ↓ (per _vision-common/vision-format.md), map-entry shape, banned-pattern absence,
   ↓ frontmatter shape; FAIL → emit VISION_SHAPE_FAILED (or STRUCTURAL_LINT_FAILED), stop
Round Memory Pass                (deterministic, no LLM judgment)
   ↓ loads ~/.claude/cache/review-state/<project>__vision.json;
   ↓ consults the vision-author sidecar at ~/.claude/cache/author-state/<project>__vision.json;
   ↓ computes round_number, prior_blockers, recently_resolved_blockers
Stage 1: Ground truth pass       (deterministic, mostly mechanical)
   ↓ internal consistency + ledger conformance; coverage audit enumerated FROM vision;
   ↓ map conformance against shipped specs; ledger and cut-list grounding;
   ↓ imagined-spec-author recomputation; remediation completeness over prior blockers
Stage 2: Persona prosecution     (LLM judgment, M parallel agents)
   ↓ when the sidecar is present, prepends a directive listing author-verified claims to skip
Stage 3: Orchestrator decision   (deterministic + judgment)
   ↓ applies fixes, runs post-fix premise verification, runs SAME-ROUND focused re-prosecution
   ↓ (≤1 re-pass), runs carry-forward consultation, classifies remaining, renders the
   ↓ three-state verdict, persists state with per-round metrics
```

There is no inner loop. If blockers remain, the user resolves them and re-invokes.

---

## Status-frontmatter check (MANDATORY, HARD SHORT-CIRCUIT)

`Read` vision's leading HTML-comment block and extract the **bare** `Status:` flag — the unbolded form inside the comment, per `_vision-common/vision-format.md` § Two `Status:` lines, told apart by shape. It is a binary mid-cycle signal: `needs-user-input` (mid-cycle) or absent (ready). The bolded `**Status:**` line in the document body is the product-stage line; this check never reads it, and a product-stage line saying anything at all never refuses a review.

- **`Status: needs-user-input`** → stop. Do NOT spawn Stage 0 or anything after. Emit:

  ```
  VISION: <vision-path>
  STATUS: REFUSED (artifact in mid-cycle authoring state)

  This vision has `Status: needs-user-input`. The author skill (`/vision-author`) wrote it as a
  partial draft with unresolved blockers listed in `## Pending blockers`. Reviewing a partial
  draft would re-prosecute issues the author already surfaced.

  Resolve the blockers in `## Pending blockers`; the session agent then applies the resolutions
  and removes the `Status:` line. Re-invoke `/vision-review` once vision is back to no-Status state.
  ```

- **No `Status:` field, OR any other value** → proceed. The Round Memory Pass consults the author sidecar; if `authoring_mode: "draft"` is set there, the verdict surfaces a draft warning and prosecution still runs.

## Stage 0 — Structural Shape Check (MANDATORY, HARD SHORT-CIRCUIT)

### Deterministic floor — `/plan-lint`

Run the lint first; it is cheaper than every check below and its failures are unarguable. The lint dispatches on document type by path shape, so pass the real `vision.md` path:

```bash
python3 ~/.claude/skills/plan-lint/lint.py <vision-path>
```

Exit `0` → continue. Exit `1` → stop; emit `STRUCTURAL_LINT_FAILED` with the lint output verbatim. Exit `2` → stop; emit `STRUCTURAL_LINT_FAILED` with stderr verbatim.

A WARN-level result — a vision carrying no map section at all — does not stop the review. Record it, skip Stage 1's map-dependent sub-passes, and let the verdict name `/vision-author` as the next step: there is no map to prosecute. The reviewer runs the lint without `--strict` for exactly this reason; `/vision-author`'s ship-mode gate passes `--strict` and blocks there, because emitting the map is that skill's job.

### Required sections

Per `~/.claude/skills/_vision-common/vision-format.md` § Section template:

1. **Frontmatter** — the bolded product-stage `**Status:**` and `**Direction:**` lines present in the body. The bare mid-cycle `Status:` flag inside the leading HTML comment is OPTIONAL and separate; any value of it other than `needs-user-input` is a SOFT MEDIUM finding. The two are told apart by shape, never by value (`vision-format.md` § Two `Status:` lines, told apart by shape).
2. **Document conventions** — heading present; body non-empty.
3. **Overview** — heading present; body non-empty.
4. **Non-goals** — heading present; ≥1 bullet.
5. **≥1 mechanism section** — heading present; body non-empty.
6. **Cut list** — present as its own section or a subsection; ≥1 ranked item.
7. **Decision ledger** — heading present; ≥1 entry (or an explicit justified "None").
8. **North-star test** — heading present; body non-empty.
9. **The spec map** — heading present, and it is the **last** section in the document.

Each missing/empty required section is `[HARD: missing required section]`. A map section that is not last is `[HARD: map not appended]` — every `vision §N` reference below it is orphaned.

**One block may sit between the last mechanism section and the map:** `## Pending blockers`, the mid-cycle scaffolding `/vision-author` writes there so the map stays last (`vision-format.md` § Two `Status:` lines, told apart by shape). It is legal only while the bare `Status: needs-user-input` flag is set, and a review with that flag set is refused before Stage 0 — so a `## Pending blockers` block reaching this check means the flag was cleared without removing the block: `[HARD: mid-cycle scaffolding left behind]`.

### Map-entry shape

For each entry in the map:

- Four fields present, in order: **Owns**, **Split line**, **Depends on**, **Covers**. A missing field is `[HARD: malformed map entry]`.
- Slug is concern-named kebab-case. A positional or numbered slug (`phase-N`, `step-N`, `NN-`) is `[HARD: position-encoded slug]`.
- Every slug named under **Split line** or **Depends on** has its own entry. A dangling slug is `[HARD: dangling slug]`.
- Every neighbor named under **Depends on** carries a split line against it. Unpaired is `[HARD: unpaired seam]`.
- An **Unowned** block is present at the end of the map. Absent is `[HARD: coverage unfalsifiable]` — without it, silence and coverage are indistinguishable.

### Forbidden patterns (regex-detectable; HARD per occurrence)

```
# Addendum sections
(?i)^##+\s*(addendum|appendix|review notes|round-\d+ findings)\b

# Review attribution
(?i)\b(architecture review|product review|round[- ]?\d+ tribunal|reviewer A/B)\b found\b

# Historical comparison
(?i)\b(the original vision|previously the vision|the vision used to|in the prior version|revised up from|supersedes|reopened)\b

# Persona-attribution headers
(?i)^##+\s+(architecture|product|game-design|backend|frontend|testing|security)(?:'s|s')\s+(view|notes|take|opinion)\b

# Conflict-resolution metadata
(?i)\b(conflict resolved by|consensus reached|decision pending arbitration)\b
```

**Status tokens, scoped to the map section only** (HARD per occurrence; the same tokens are legitimate elsewhere in vision and always legitimate in `specs/README.md`):

```
(?i)\b(shipped|owed|next up|in flight|parked|on loan|TODO|not yet written|awaiting)\b
\b\d{4}-\d{2}-\d{2}\b
```

**Carve-out:** an entry heading's `name unsettled` marker is format, not state (`vision-format.md` § Entry shape). It says what the heading permanently is until a director mints the name, so neither this scan nor a persona files `DECOMPOSITION_STATUS_LEAK` against it.

Plus prose-detected: hedging future tense (`we will likely`, `this document aims to`) → SOFT MEDIUM; meta-commentary (`this section`, `below we'll cover`) → SOFT MEDIUM.

### Implementation-creep patterns (regex-detectable; HARD)

```
# Path:line citations (longest-first alternation)
[a-z_/]+\.(tsx|prisma|toml|yaml|json|md|ts|js|sql)(:[0-9]+)?

# Function/identifier signatures
\w+\(.*\)\s*(:|=>)\s*\w+

# Schema column names
(column|field|enum)\s+["`]\w+["`]
```

Applied with backtick-fenced spans excluded. **Carve-outs:** a repo-relative path naming a *document* the map legitimately points at (`specs/README.md`, `specs/<slug>/spec.md`, `CLAUDE.md`) is not creep; a precise product rule expressed with a formula or threshold is not creep (P-VISION-WHAT-NOT-HOW).

### Behavior

- **All checks pass** → record `shape_clean=true`, proceed to Round Memory Pass.
- **Any HARD failure** → stop. Emit `VISION_SHAPE_FAILED` with the defect list; no further stages run. SOFT findings defer to Stage 1.
- **SOFT-only failures** → record; proceed. Stage 1g mechanical fixes resolve them.

Why short-circuit: a persona reviewing a map with three malformed entries produces findings that assume the entries parse — wasted budget.

---

## Round Memory Pass (no LLM judgment)

Same purpose and mechanism as the sister skills — `~/.claude/skills/_review-common/round-memory.md`. Read it. The vision layer adds:

- **Slug** — `<project>__vision`, where `<project>` is the repo-root basename.
- **Extra field** — `author_sidecar_consulted: { sidecar_path, sidecar_present, claims_verified_skipped, self_prosecution_findings_skipped, imagined_spec_author_verdict }`, written every round.
- **Extra field** — `map_snapshot: { entries: [{slug, owns_digest, split_lines, depends_on, covers}], unowned: [...] }`, so the next round's map diff is computable without re-deriving it.
- **Extra metric** — `per_round_metrics.round_<N>.cross_file_escalations`, since this layer escalates cross-file findings rather than applying them.
- **Extra metric** — `per_round_metrics.round_<N>.coverage: { units_enumerated, units_claimed, units_unowned }`.
- **Blocker classes seen here** — the full active list above.

### Author sidecar consultation

Read `~/.claude/cache/author-state/<project>__vision.json` if it exists. Extract `claims_verified` count + `ground_truth_log` entries with outcome `verified` / `verified_softened` / `corrected` (Stage 2 MUST NOT re-prosecute these as hallucinations), `self_prosecution_findings` (MUST NOT re-file), `authoring_residual` (informational), `coverage` and `imagined_spec_author_report` (this skill **recomputes** both and files `AUTHOR_GATE_DRIFT` on disagreement), and `seam_decisions_consulted`. If the sidecar is absent (the map was hand-written), record `sidecar_present: false`; Stage 2 has full prosecution latitude. If the sidecar's `last_vision_sha256` differs from vision's current sha, the user edited manually — treat `claims_verified` as a hint, not a binding skip-list.

### Persist on exit

Per the shared file, plus `author_sidecar_consulted` and `map_snapshot` ← what this round observed.

---

## Stage 1 — Ground truth pass (MANDATORY, MOSTLY MECHANICAL)

Produces an `audit_report`. Stage 2 personas MUST NOT re-prosecute facts verified here.

**There is NO upstream trace** — vision is the root. Stage 1's targets are vision's own internal coherence, the invariant ledger, the map's coverage of vision, and the specs already shipped below it.

**LLM-judgment carve-out.** Sub-passes 1b–1d and 1f are mechanical (file Reads, enumeration, substring overlap). Sub-pass 1a is mechanical plus light judgment — whether two sections contradict each other is a reading, not a substring match — and its judgment findings are filed SOFT MEDIUM under the corresponding `P-VISION-*` policy. Sub-pass 1e makes the judgment calls the dry run requires. Sub-pass 1g applies only unambiguous mechanical fixes; predicate applicability is prosecuted in Stage 2 under `P-VISION-SPLIT-LINE-PREDICATE`, never auto-fixed here.

### 1a. Internal consistency and ledger conformance (mechanical + light judgment)

- **Each load-bearing term** used in a mechanism section → verify the vocabulary table binds it. Unbound → `[HARD: unbound vocabulary]` under P-VISION-NAMES-ARE-DIRECTOR.
- **Each mechanism section** → check no other section, cut-list rank, or ledger entry contradicts it. Contradiction → `[HARD: internal contradiction]`, both sides verbatim.
- **Each bound invariant** in `CLAUDE.md` and every relevant memory file under `~/.claude/projects/<project>/memory/` → vision honors it (no finding), contradicts it (`[HARD: contradicts invariant ledger]`, verbatim both sides, routes to `OPEN_QUESTION`), or is silent (no finding — silence is not contradiction).

Output an `Internal Consistency` block and a `Ledger Conformance` block.

### 1b. Coverage audit (mechanical) — the layer's Brief Trace

**Enumerate from `vision.md`, never from the map.** This is the whole point: a map read forward can only show what it contains, and the defect being hunted is what it omits.

The universe, enumerated mechanically:

- **every** section of the document — overview, non-goals, mechanism, delivery, north-star, and the rest,
- every bound term in the vocabulary table (wherever the project keeps it),
- every decision-ledger item,
- every cut-list item.

For each unit, exactly one disposition: **claimed** by a named entry, or **named in the unowned block**. There is no third state. Overview and framing sections are units on the same terms as mechanism sections; a spec is rarely their definition site, so the expected disposition is an explicit unowned line, and its absence is a gap like any other.

- Unit with neither → `[HARD]` `VISION_COVERAGE_GAP`, naming the unit and the three resolution paths (assign it, name it unowned, or drop the vision material it came from).
- Unit claimed by **two** entries → `[HARD]` `SPEC_BOUNDARY_UNBOUND` — two specs claiming one surface is a boundary defect, not a coverage gap.

Record `coverage: { units_enumerated, units_claimed, units_unowned }` and compare all three against the author sidecar's `coverage`. Disagreement → `AUTHOR_GATE_DRIFT`. `units_claimed + units_unowned == units_enumerated` is the two-state rule stated arithmetically; a shortfall is the gap count, and every unit in it is filed individually rather than recorded as a number.

Output a `Coverage` block: the unit universe with each disposition, and every gap verbatim.

### 1c. Map conformance against shipped specs (mechanical)

For each `<slug>` whose `specs/<slug>/spec.md` exists on disk (scoped to the argument slug when one was passed):

- **Every surface the entry claims it Owns** is defined in that spec. Missing → `[HARD]` `MAP_CONFORMANCE_GAP`.
- **Every surface that spec defines** is one its own entry claims. A surface a *neighbor's* entry claims → `[HARD]` `MAP_CONFORMANCE_GAP`, naming both entries.
- **Every vision section the entry's Covers claims** is in fact covered by that spec.
- **Every split line the entry states** is honored by what the spec actually contains — a rule on the wrong side of the predicate is the sharpest form, because it proves the predicate is not being applied.

Quote both sides verbatim in every finding; P-VISION-MAP-IS-CLAIM invalidates an unquoted assertion. An entry whose spec does not exist on disk is skipped here — an unwritten spec cannot falsify anything.

Output a `Map Conformance` block: specs on disk, entries checked, divergences verbatim.

### 1d. Ledger and cut-list grounding (mechanical)

- **No entry depends on content the cut list ranks as expendable above the line the entry needs.** An entry whose Owns rests on material scheduled to be cut first is `[HARD]` — the spec would be authored against a premise the project has already agreed to drop.
- **No entry re-opens something the decision ledger closed.** A boundary or a scope that contradicts a closed ledger entry is `[HARD]`, routing to `OPEN_QUESTION`.
- **Every Active `Status: bound` entry** in `specs/decisions.md` and each `specs/<slug>/decisions.md` is a constraint. A map entry contradicting one is `[HARD]`; a persona finding contradicting one is retracted in Stage 3 rather than relitigated. Only Active-section `Status: bound` entries count — `superseded` / `obsolete` entries never arbitrate (`~/.claude/skills/_review-common/principles.md` § What counts as a bound entry).
- **Parked-item integrity.** For each item `specs/README.md` discharged since `last_review_at`, verify its substance is present in the spec that absorbed it. Absent → `HOIST_INCOMPLETE`, severity inherited from the parked item.

Output a `Ledger and Cut-list Grounding` block.

### 1e. Imagined-spec-author recomputation (LLM judgment, bounded)

Recompute the author's dry run rather than trusting its verdict — this is what the three-state verdict rests on. Follow `~/.claude/skills/_decompose-common/decomposition-principles.md` § The imagined-downstream-author dry run with the vision layer's substitutions: downstream author `/spec-author`, unit a *spec*, class `SPEC_BOUNDARY_UNBOUND`.

Pick the next owed spec (the argument slug when one was passed; otherwise the first entry with no unmet dependency, preferring the one `specs/README.md` marks next). Attempt to author it as a thought experiment from **its map entry plus its roster entry and nothing else**. File every question those entries leave unanswerable, each with the question, where in the spec it would have to be answered, and a falsifiable `severity_test`.

Reaching past the two entries — into vision's other sections, into a sibling's entry, into this review's own reading of the seam — makes the dry run pass on knowledge the spec author will not have. Every reach is the finding.

Verdict `authorable` / `not_authorable`. Disagreement with the author sidecar's `imagined_spec_author_report.verdict` → `AUTHOR_GATE_DRIFT` alongside whatever this recomputation found on its own.

### 1f. Remediation completeness over prior-round blockers (mechanical)

Runs over the **prior** round's blockers — the remediation the user wrote *between* rounds, which no other stage sees. For each entry in `prior_blockers` that no longer appears:

- **Did the fix reach the sites coupled to it?** At this layer the coupled sites are: the map entries on **both** sides of a moved seam, the `Covers` field of every entry whose section the fix touched, the unowned block where a unit changed disposition, `specs/README.md` where the fix moved state, and the `specs/decisions.md` entry the arbitration should have produced. A fix that landed in one entry and not its neighbor reads as closed while its consequence is unbuilt → `REMEDIATION_INCOMPLETE`, severity inherited from the original blocker.
- **Was the arbitration recorded?** An arbitration made to close a prior blocker with no `Status: bound` entry in `specs/decisions.md`, or a map entry citing an entry that does not exist (resolved by heading, not by date alone) → `DECISIONS_PROVENANCE_GAP`, HIGH.

Both classes are exempt from ephemeral carry-forward: each is an assertion about the completeness of the carry-forward record itself. Surviving coupled sites feed Stage 2 as seeds rather than waiting for a persona to rediscover them.

Output a `Remediation Completeness` block; on a cold start, record `prior_blockers: 0` and skip.

### 1g. Stage 1 mechanical fixes

Apply unambiguous fixes immediately: forbidden style-class patterns from Stage 0 SOFT findings, a status token inside the map whose content already exists verbatim in `specs/README.md` (delete from the map, do not move it — moving is the author's job when the roster lacks it), stale `Last updated` where the project carries one. Emit `Stage 1 fixes applied:`. HARDs that cannot be auto-fixed pass to Stage 2 as `pre_resolved_hard_findings`.

**Never auto-fix a split line, an Owns paragraph, or a coverage disposition.** Each is a boundary call; the narrowest honest outcome is a finding, not an edit.

### Stage 1 output (audit_report)

Bulleted facts: vision_path, HEAD sha; plan_lint (exit code, defects); internal_consistency; ledger_conformance; coverage (the three counts + gaps); map_conformance (specs on disk, entries checked, divergences); ledger_and_cut_list_grounding; imagined_spec_author (spec attempted, verdict, gaps); remediation_completeness; stage_1_fixes_applied; pre_resolved_hard_findings; author_sidecar_consulted.

---

## Stage 2 — Persona prosecution (parallel agents, fix-list output)

Read `personas/ai-development.md` once for context. Resolve personas (auto or explicit). Launch one Agent per persona, **all in parallel in a single message**, each with `model: "sonnet"` per `~/.claude/skills/_review-common/agent-prompt.md` § Model pin — never inherit the session model; record `persona_model` in the review state. M agents.

### Spawn agents

Use `~/.claude/skills/_review-common/agent-prompt.md`. Substitute:

- `{persona_name}` — the persona
- `{audit_report_bullets}` — Stage 1 audit (compact bullets)
- `{pre_resolved_hard_findings}` — Stage 1 HARDs
- `{active_critical_pair_subset}` — `P-CLASS-SCOPE, P-FULL-FILE, P-VISION-WHAT-NOT-HOW, P-VISION-SPLIT-LINE-PREDICATE, P-VISION-COVERAGE-TWO-STATE, P-VISION-NO-STATUS, P-VISION-MAP-IS-CLAIM, P-VISION-NAMES-ARE-DIRECTOR, P-VISION-CYCLES-LEGAL, P-VISION-SECTION-BOUND`
- `{target_locator}` — the vision path
- `{how_to_get_it}` — `Read <vision-path>`; agents Read source-of-truth files (`CLAUDE.md`, project memory, `specs/README.md`, shipped specs, decisions logs, persona files) on demand. **Agents never read `handoffs/`.**
- `{pr_description_or_brief_mapping}` — N/A (vision is the root artifact; there is no upstream mapping)
- `{skill_specific_extensions}` — *Imagine you are the spec author who must turn one map entry into a full spec. Hand each split line a rule this document does not contain — does the predicate return a side, with no further argument? Where would two spec authors, reading neighboring entries, both believe they own the same rule? Which mechanism section could you finish reading without knowing which spec will define it? Which bound vocabulary term has no definition site? Which entry rests on something the cut list is scheduled to remove? Where does the map describe a spec that exists on disk in a way that spec does not bear out?*
- `{skill_specific_preamble}` — none (Stage 1's coverage and map-conformance blocks are the ground-truth substitute)
- `{skill_specific_resets_block}` — none (RESETs are an engineering-plan-only mechanism)

Vision is large. Pass the map section inline and instruct agents to `Read` the rest of the document in full. The orchestrator does NOT inline source-of-truth file contents — agents Read on demand.

### Author-sidecar consultation in agent prompts

When the author sidecar is present, prepend the standard directive: list `claims_verified` and `self_prosecution_findings` counts; instruct that author-verified claims MUST NOT be re-prosecuted as hallucinations without citing a *specific change* in `CLAUDE.md` / project memory / `specs/README.md` / a shipped spec since `last_vision_sha256`. When absent, omit.

---

## Stage 3 — Orchestrator decision

Runs in the main thread, per `~/.claude/skills/_review-common/orchestrator.md`.

### 3a–3d. Apply fixes

Confirm Stage 1 mechanical fixes are in place. Filter Stage 2 fix lists against the active critical-pair policies (retract contradicting findings; note in verdict). Retract duplicates of Stage-1 hard findings, findings contradicting an Active `Status: bound` entry, and author-sidecar-verified claims lacking a concrete upstream-change citation. Detect cross-persona disagreement on the same span → `STABLE_DISAGREEMENT` (do not auto-apply). Consolidate non-conflicting fixes, group by section, apply in a single editing pass ordered by severity.

**Cross-file fix scope (vision layer).** This skill edits ONLY `vision.md`. A fix whose substance binds beyond it is never auto-applied:

- **`CLAUDE.md`** (including the vocabulary table) → DO NOT auto-edit. `OPEN_QUESTION`: "fix would amend CLAUDE.md — the director arbitrates whether the ledger changes or vision is re-scoped."
- **Project memory** (`~/.claude/projects/<project>/memory/*`, `MEMORY.md`) → DO NOT auto-edit. `OPEN_QUESTION`.
- **A `specs/<slug>/spec.md`** → DO NOT auto-edit. `MAP_CONFORMANCE_GAP` or `VISION_AMENDMENT_NEEDED`: "fix would amend a shipped spec — the director arbitrates which side moves."
- **`specs/README.md`** → DO NOT auto-edit. The roster is the author's to maintain; a fix that belongs there is `DECOMPOSITION_STATUS_LEAK` against the map with the roster named as the destination.
- **`specs/decisions.md`** → DO NOT auto-edit. A boundary that needs binding is `SPEC_BOUNDARY_UNBOUND`; the director binds it and the entry lands in the log.

Record cross-file escalations in `cross_file_escalations[]`.

**Authority order when artifacts disagree** (highest to lowest):

1. `CLAUDE.md` and project memory — the bound-invariant ledger.
2. Active `Status: bound` entries in `specs/decisions.md` and each `specs/<slug>/decisions.md`.
3. Shipped `specs/<slug>/spec.md` — concrete, but a divergence names which side moves as a director call rather than resolving downward automatically.
4. `vision.md` under review.

**Forbidden fixes:**

- Weakening the map — dropping an entry, softening a predicate into an enumeration, converting a coverage gap into a third disposition, or moving a unit into the unowned block to clear a gap. Each is `OPEN_QUESTION`.
- Coining a spec name, a domain term, an element name, or a split-line term. `OPEN_QUESTION`; names are the director's.
- Rewriting a mechanism section wholesale to clear a map defect (P-VISION-SECTION-BOUND retracts this).
- Auto-editing `CLAUDE.md`, project memory, a shipped spec, `specs/README.md`, or `specs/decisions.md`.
- "Leaving it for the spec" — if the boundary is unclear now, the spec author will invent one.

### Post-fix premise verification

Per `orchestrator.md` § Post-fix premise verification. The claims that matter at this layer: internal cross-section references, invariant-ledger references, `Covers` claims against the sections they name, and every claim about what a shipped spec defines.

### Same-round focused re-prosecution

Per `orchestrator.md` § Same-round focused re-prosecution — one pass, bounded. Mandatory when ANY of: Stage 3d fixes > 0, cross-file escalations > 0, or post-fix premise verification falsified-claim count > 0.

### 3e. Classify remaining unresolved findings

Active classes: the full list under § Active blocker classes.

**Carry-forward consultation (durable-first, then ephemeral cache).**

- **Priority 1 — the decision logs** (durable). Read `specs/decisions.md` and each `specs/<slug>/decisions.md`; search for Active `Status: bound` entries whose subject substring-matches the finding's surface. A finding contradicting a bound entry → drop, recording `[CARRY-FORWARD via <log>]`. Only Active-section `Status: bound` entries count. `SPEC_BOUNDARY_UNBOUND` and `MAP_CONFORMANCE_GAP` are **not** retractable this way when the bound entry is itself what the shipped spec falsifies — a bound seam the code below it does not honor is the defect, not the protection.
- **Priority 2 — `recently_resolved_blockers` ephemeral cache.** For findings surviving Priority 1: if an entry's `carry_forward_until_round >= round_number` AND its `path_or_section` overlaps the finding's section or entry slug, downgrade to `OPEN_QUESTION` with the prior `user_decision` surfaced verbatim; the persona's claim survives only if `current_reclassification_justification` was filed. `REMEDIATION_INCOMPLETE` and `DECISIONS_PROVENANCE_GAP` are exempt — each asserts something about the carry-forward record itself.

### 3f. Render verdict

Three states, per `~/.claude/skills/_review-common/blocker-classes.md` § Verdict gates → Vision review. Pick exactly one.

- **CLOSED** — coverage complete, every seam carries an applicable predicate, the map conforms to every shipped spec, the next spec is named and scoped, and no boundary call is outstanding. `/spec-author <slug>` is unblocked.
- **APPROVED** — shape-correct with one or more `SPEC_BOUNDARY_UNBOUND` calls outstanding. Authoring is not unblocked for any spec a pending call touches; the rest of the roster stays authorable.
- **NEEDS USER INPUT** — anything else.

Tier-1 weights: CRITICAL=8, HIGH=4, MEDIUM=2, LOW=1. Tier-2 floor: 4.

**Final line — verdict banner.** After the output block below, run the shared verdict-banner script and emit its output verbatim (`~/.claude/skills/_review-common/blocker-classes.md` § Verdict banner) as the **very last** thing in your response:

```bash
python3 ~/.claude/skills/_review-common/verdict_banner.py "<STATUS>" <ROUND> [<BLOCKERS>] --skill /vision-review [--next "<one line>"]
```

### 3g. Output

The output **leads with the map diff**, because the director is the reader. Counts and audit detail follow.

```
## Vision Review Complete: {vision_path}

### Map diff
- **Entries changed this round:** {slug} — {what moved, one clause} | none
- **Split lines moved:** {slug} ↔ {slug} — {new predicate, verbatim} | none
- **Coverage:** {units_claimed} claimed, {units_unowned} unowned (of {units_enumerated}); {n} gaps
- **Map conformance:** {n} shipped specs checked, {n} divergences
- **Next spec:** `{slug}` | blocked by {slug}'s open boundary call

**Round:** {round_number} {| `(round 1 — no prior state)` | `(loaded from cache: {n-1} → {n})`}
**State source:** {`Loaded from ~/.claude/cache/review-state/<project>__vision.json` | `Round 1 (no prior state)`}
**Author sidecar:** {`consulted; N claims verified skipped; M self-prosecution findings skipped` | `absent (map was hand-written)` | `present but SHA differs (treated as hint)`}
**Authoring mode warning:** {`none` | `sidecar reports authoring_mode: "draft" — /vision-author --draft skipped its gates`}
**Personas:** {names}
**Stage 0 plan-lint:** PASS / FAIL ({rule ids})
**Stage 0 shape check:** PASS / N hard findings (sections / map entries / forbidden patterns / creep)
**Stage 1 audit:** coverage PASS / N gaps; map_conformance PASS / N divergences; ledger PASS / N hard; cut-list PASS / N hard
**Stage 1 imagined-spec-author:** spec `{slug}`; verdict {authorable | not_authorable}; gaps {n}
**Stage 1 remediation completeness:** {n} prior blockers checked; {n} incomplete; {n} provenance gaps
**Stage 1 mechanical fixes applied:** {count}
**Stage 2 personas:** {N} agents in parallel
**Stage 3 fixes applied:** {count} (HARD: {n}, SOFT: {n})
**Stage 3 retractions (critical-pair policy / bound entry):** {count}
**Cross-file escalations:** {count}
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
- {finding} → retracted because {policy / pre-resolved / bound entry / author-verified without justification}

### Boundary calls (yours to bind) — only under APPROVED
- [SPEC_BOUNDARY_UNBOUND] `{slug}` — {question}; {severity_test}. Director binds at Seam alignment.

### Blockers (if any)
- [VISION_SHAPE_FAILED] {finding} — fix and re-invoke.
- [STRUCTURAL_LINT_FAILED] {lint rule} — {defect}; fix and re-invoke.
- [VISION_COVERAGE_GAP] {unit} — {one-line}; assign it, name it unowned, or drop the material.
- [SPEC_BOUNDARY_UNBOUND] `{slug}` — {question}; {severity_test}. Director binds at Seam alignment. (Only under NEEDS USER INPUT — under APPROVED these render in the Boundary-calls section above, never here.)
- [MAP_CONFORMANCE_GAP] `{slug}` — entry claims "{verbatim}"; spec defines "{verbatim}".
- [SEAM_PREDICATE_MISSING] {seam} — {one-line}; write the predicate, split the seam, or merge it away.
- [DECOMPOSITION_STATUS_LEAK] {span} — {token}; belongs in specs/README.md.
- [DECOMPOSITION_SURFACE_EXCESS] `{slug}` — {structural condition}; split or accept in a bound row.
- [VISION_AMENDMENT_NEEDED] {section} — {one-line}; amend the section or drop the surface.
- [HOIST_INCOMPLETE] {parked item} — {one-line}; complete the hoist or restore the roster entry.
- [REMEDIATION_INCOMPLETE] {prior blocker} — fix landed at {site}; missed {sites}.
- [DECISIONS_PROVENANCE_GAP] {arbitration} — no bound entry in specs/decisions.md.
- [AUTHOR_GATE_DRIFT] {gate} — reviewer recomputed {value}; sidecar records {value}.
- [STABLE_DISAGREEMENT] {finding} — Persona A: {fix A}; Persona B: {fix B}. Pick one.
- [OPEN_QUESTION] {finding} — {question}.
- [FIX_INTRODUCED_PREMISE_INVERSION] {section}: fix asserts "{claim}"; verification: {what was run}; actual: "{evidence}". Working tree dirty.
- [POLISH_PLATEAU] {finding} — non-blocking.
- [REPO_STATE_DRIFT] HEAD changed from {sha} to {sha}. Re-run.

### Vision Status: CLOSED / APPROVED / NEEDS USER INPUT
```

If `NEEDS USER INPUT`: the next step is **targeted edits to clear the listed blockers**, then re-invoke `/vision-review` (optionally triage with `/explain-blockers` or `/solve-blockers`). Do **not** re-run `/vision-author` to clear a handful of blockers.

If `APPROVED`: bind the outstanding boundary calls in `specs/decisions.md`; the session agent rewrites the affected entries and re-invokes this skill.

**Rendering rule for APPROVED.** An outstanding `SPEC_BOUNDARY_UNBOUND` under APPROVED is a decision, not a defect — render it only in `### Boundary calls (yours to bind)` and leave `### Blockers` empty (omit the section). APPROVED with a non-empty Blockers section is a rendering bug: whatever would go there means the verdict is NEEDS USER INPUT. Under NEEDS USER INPUT everything, boundary calls included, renders in Blockers as one list.

---

## Hard rules

- **The compatibility gate runs first.** No `vision.md` at the repo root → decline in one line and stop. Never ask; detect by file presence.
- **Status-frontmatter check runs before Stage 0.** A vision with `Status: needs-user-input` is mid-cycle; refuse and point at `/vision-author`.
- **Stage 0 is mandatory and runs `/plan-lint` first.** Lint is the deterministic floor; the format check sits on top of it. A vision with a malformed map entry is unprosecutable.
- **The map must be vision's last section.** A map that is not last orphans every `vision §N` reference below it and fails Stage 0.
- **Stage 1 is mandatory** and has NO upstream trace. Its targets are internal consistency, the invariant ledger, coverage enumerated from vision, the shipped specs, the cut list and decision ledger, and the prior round's remediation.
- **Coverage is enumerated from `vision.md`, never from the map.** Reading the map forward cannot surface an omission.
- **Map conformance quotes both sides.** An assertion of divergence with only one side quoted is retracted under P-VISION-MAP-IS-CLAIM.
- **Round Memory Pass is mandatory.** State file at `~/.claude/cache/review-state/<project>__vision.json` (NOT in the repo).
- **Author sidecar consultation is mandatory when the sidecar exists.** Re-prosecuting author-verified claims without a concrete upstream-change citation is forbidden. Coverage and the dry run are recomputed regardless; disagreement is `AUTHOR_GATE_DRIFT`.
- **`handoffs/` is never read** — not by the orchestrator, not by a persona agent, not to resolve a parked item.
- **Cross-file fix scope is mandatory.** This skill edits ONLY `vision.md`. `CLAUDE.md`, project memory, a shipped spec, `specs/README.md`, and `specs/decisions.md` escalate.
- **Bound entries are constraints.** A persona finding contradicting an Active `Status: bound` entry is retracted, not relitigated — except where the shipped spec itself falsifies the bound entry, which is the defect.
- **Names are never coined here.** A finding proposing a spec name, domain term, or element name routes to `OPEN_QUESTION`.
- **Same-round focused re-prosecution is mandatory** when ANY of: Stage 3d fixes > 0, cross-file escalations > 0, or falsified-claim count > 0. Bounded: exactly one re-pass.
- **Stage 2 agents return fix lists; never edit files.** All edits applied by the orchestrator in Stage 3.
- **Never** mark CLOSED or APPROVED while one of the **gating** classes the registry lists for this layer is non-empty (`~/.claude/skills/_review-common/blocker-classes.md` § Verdict gates → Vision review). `SPEC_BOUNDARY_UNBOUND` is the carve-out: it gates CLOSED and not APPROVED. `POLISH_PLATEAU` and the other non-blocking classes gate neither — they are surfaced, not enforced.
- **Never** weaken the map to resolve a finding — no dropped entry, no softened predicate, no third coverage state, no gap laundered into the unowned block.
- **Always** quote verbatim from vision, the ledger, a shipped spec, a decisions log, or the audit_report when justifying a finding.
- **No multi-round inner loop.**
- **Do not re-run `/vision-author` to clear a completed review.**

## Compliance self-check (before rendering verdict)

- [ ] Compatibility gate ran first; `vision.md` confirmed at the repo root.
- [ ] Status-frontmatter check ran before Stage 0.
- [ ] Stage 0 ran `/plan-lint`, then the format check: required sections, map-entry shape, map-is-last, banned patterns, status tokens scoped to the map, implementation creep.
- [ ] Round Memory Pass ran; reviewer state loaded; author sidecar consulted (or marked absent).
- [ ] Stage 1 ran in full: internal consistency + ledger, coverage enumerated from vision, map conformance against every shipped spec, ledger and cut-list grounding, imagined-spec-author recomputation, remediation completeness. NO upstream trace attempted.
- [ ] Coverage counts recomputed and compared against the author sidecar; disagreement filed as `AUTHOR_GATE_DRIFT`.
- [ ] Stage 2 spawned all M persona agents in parallel, model-pinned.
- [ ] Stage 3 applied critical-pair and bound-entry retractions before applying fixes.
- [ ] Post-fix premise verification ran on orchestrator-rewritten prose.
- [ ] Same-round re-prosecution ran (or skip conditions met and recorded).
- [ ] Carry-forward consultation: Priority 1 (decision logs) then Priority 2 (state-file).
- [ ] Cross-file fix scope checked; nothing outside `vision.md` was edited.
- [ ] Output leads with the map diff; every metric line present, even at count = 0.
- [ ] State file persisted with new round entry appended, including `map_snapshot` and `coverage`.
- [ ] Verdict banner: the script ran (with `--skill`), its fenced stdout ends the response, nothing follows it.

## Edge cases

- **No `vision.md` at the repo root:** the compatibility gate declines in one line. No state-file changes.
- **`vision.md` present, no map section:** `/plan-lint` warns rather than fails without `--strict`, which is how this skill invokes it. Skip Stage 1's map-dependent sub-passes, run the rest, and name `/vision-author` as the next step — there is no map, so no unit has a disposition and the coverage audit reports its whole universe as unclaimed rather than filing one gap per unit.
- **`specs/` absent:** map conformance records `specs_shipped: 0` and is skipped. Not an error; the dry run still runs and is the only thing gating CLOSED.
- **`specs/README.md` absent:** warn and proceed. Parked-item integrity and the next-spec marker cannot be checked; say so rather than reporting them clean. Creating the roster is `/vision-author`'s job, from the shape in `_vision-common/vision-format.md` § The roster — this skill never writes it.
- **`specs/decisions.md` absent:** Priority-1 carry-forward has no vision-layer log. Fall back to the per-spec logs; note it. A `SPEC_BOUNDARY_UNBOUND` finding in this state names the log's creation as part of its resolution path.
- **Persona file not found:** auto-resolution falls back to the next default persona; explicit personas stop and ask. A project with no `personas/` directory stops.
- **`CLAUDE.md` absent:** warn and proceed. Ledger conformance records `0 entries consulted`. Where the vocabulary table lived there, the coverage universe is incomplete — report coverage as partial, never as complete.
- **Project memory absent:** warn and proceed. `CLAUDE.md` is the minimum ledger source.
- **Map authored via `/vision-author --draft`** (sidecar `authoring_mode: "draft"`): proceed with full prosecution; warn in the verdict that the map is unhardened.
- **Author sidecar SHA differs from vision's SHA:** the user edited manually after authoring. Treat `claims_verified` as a hint; Stage 2 may re-prosecute spans where user edits overlap author-verified claims.
- **State file missing for a vision clearly reviewed before:** cold start at round 1. The ephemeral cache is lost; the decision logs still feed Priority-1 carry-forward, and the remediation-completeness pass records `prior_blockers: 0` and skips.
- **A shipped spec contradicts an Active bound seam entry:** the bound entry does not protect the finding. File `MAP_CONFORMANCE_GAP` with both sides quoted and name the two-step supersede as one of the resolution paths.
- **HEAD changes mid-review:** emit `REPO_STATE_DRIFT`. User re-runs.

---

## Relationship to sister skills

- **`/vision-author`** writes the map and the author sidecar this skill consults. The author runs its gates at write time; this skill prosecutes what the author missed, what the director introduced by hand, and what the specs shipped since have falsified.
- **`/spec-author`** consumes the map as its upstream: a CLOSED verdict here unblocks `/spec-author <slug>`, and an APPROVED one unblocks only the specs no pending boundary call touches.
- **`/spec-review`** re-tests every split line against a concrete rule each time a spec is authored, and files `MAP_CONFORMANCE_GAP` against the same map from below. That downstream re-test is the backstop that keeps split lines honest; a defect it surfaces belongs upstream, feeding the next `/vision-author` invocation.
- **`/explain-blockers`** and **`/solve-blockers`** triage this skill's `### Blockers` block and the boundary calls an APPROVED verdict leaves outstanding.

Vision is the root artifact; this skill exists to give its decomposition the same adversarial review surface the spec, brief, engineering plan, and chunk plans already enjoy.
