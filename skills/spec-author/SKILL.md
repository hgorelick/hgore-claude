---
name: spec-author
description: Writes or rewrites a `spec.md` — the source-of-truth every brief, engineering plan, and chunk plan descends from, including the decomposition that cuts its briefs — applying ground-truth verification and self-prosecution at write time rather than review time. Run once per cycle, then `/spec-review`. Sister to `/vision-author`, `/brief-author`, `/engineering-plan-author`, `/plan-author`.
user-invocable: true
---

# Spec author

Produces or rewrites a `spec.md` with the same prosecution rigor `/spec-review` applies, but front-loaded at write time.

The spec is the **source-of-truth of its own system**: every downstream artifact — every brief, engineering plan, chunk plan, and line of code under that system — descends from it. A spec that contradicts its own invariants, invents a capability, leaves a load-bearing term undefined, or smuggles in a rule that contradicts the project's bound-invariant ledger will cascade through *every* feature, and the downstream review machinery repairs the descendants, never the spec itself. This skill makes the spec the cleanest artifact in the project.

It also cuts the briefs. `## Decomposition` is required format of every spec — the seams, the brief roster, the scope stubs `/brief-author` consumes, and the coverage table proving no spec unit fell through — so the decomposition is authored and prosecuted here rather than re-derived one brief at a time downstream.

The canonical spec shape and drafting rules live in `~/.claude/skills/_spec-common/spec-format.md` — read it before drafting. The decomposition machinery it shares with the vision layer lives in `~/.claude/skills/_decompose-common/decomposition-principles.md` — read that before drafting `## Decomposition`. Both are project-agnostic; this skill applies them to whatever project it is invoked in.

## Inputs

- `$ARGUMENTS` (optional):
  - `<slug>` or `<path>` — which spec to author. See § Spec resolution.
  - `--draft` — quick-exploration mode; skip the Decomposition conformance gate, ground-truth, and self-prosecution, with the Shape and Lint gates reporting instead of blocking; emit a sidecar marked `authoring_mode: "draft"` (unhardened by choice; downstream reviewers warn rather than refuse).

### Spec resolution

By file presence, never by asking:

| Argument | Resolves to |
|---|---|
| `<slug>` | `specs/<slug>/spec.md` |
| a path to a directory | `<dir>/spec.md` |
| a path to a file | that file |
| none, and `specs/` holds exactly one spec folder | that folder's `spec.md` |
| none, and root `spec.md` exists (or nothing exists yet) | root `spec.md` |

**Ambiguous invocation** — no argument, and `specs/` holds more than one spec folder — lists the specs and asks which, the way the engineering-plan reviewer handles tracks. Never guess, and never default to the first.

Everything keyed on layout below follows from this one resolution: the decisions log beside the resolved spec, the sidecar key, and whether a `vision.md` map entry binds the run.

**The author runs once per cycle.** It produces the first draft; the next step in the cycle is to run `/spec-review`, and the session agent then applies its findings — plus your blocker resolutions — directly to `spec.md`. The author is not re-invoked to apply changes. There is no `--rewrite` flag. When `spec.md` already exists or its author sidecar is present, invoke `/spec-author` again only for an explicit clean-slate re-author (ask in plain language); that fresh run treats the existing spec and any prior review state as carry-forward constraints — an invariant / feature area / non-goal the user already removed is not re-introduced.

**`spec.md` being absent is normal.** Unlike the downstream skills (which hard-refuse without a spec to anchor against), this skill *creates* the spec. A missing `spec.md` is the cold-start case, not an error.

## Sidecar location

Per `_spec-common/spec-format.md` § Sidecar keying, gated on `vision.md` at the repository root:

- **`vision.md` present** → `~/.claude/cache/author-state/<project>__<spec-slug>__spec.json`, where `<spec-slug>` is the `specs/<slug>/` directory name of the resolved spec — e.g. `instar__typing-system__spec.json`. A project carrying per-system specs has several at once, and an unslugged key collides the moment the second lands.
- **`vision.md` absent** → `~/.claude/cache/author-state/<project>__spec.json` — e.g. `my-app__spec.json`.

`<project>` is the basename of the repository root (or cwd when not a git repo). Same directory as the brief/engineering-plan/chunk author sidecars; the spec is keyed on the **project and its spec**, never on a feature. `/spec-review` consults this sidecar to skip re-prosecuting claims the author already verified, and resolves the same key by the same gate.

---

## Workflow

```
State load (deterministic; ~5 seconds)
  ├─ mkdir -p ~/.claude/cache/author-state (Write does NOT auto-create parents)
  ├─ Resolve the spec per § Spec resolution; derive <project>, <spec-slug>, and the vision gate
  ├─ Read sidecar at the § Sidecar location key (if exists)
  ├─ Read review-state at the matching ~/.claude/cache/review-state/ key (if exists — warm carry-forward)
  └─ Determine cold vs warm mode

Source ingest (deterministic; ~30 seconds)
  ├─ Read ~/.claude/skills/_spec-common/spec-format.md (the format being applied)
  ├─ Read ~/.claude/skills/_decompose-common/decomposition-principles.md (the decomposition machinery)
  ├─ Read CLAUDE.md (project conventions + bound invariants)
  ├─ Read MEMORY.md + relevant project memory files (bound invariants the spec must honor)
  ├─ Read vision.md and this spec's map entry (when vision.md exists — HARD-blocking upstream)
  ├─ Read existing spec.md (warm mode — when the file or sidecar already exists)
  ├─ Read project design docs (docs/*, context/*, architecture/decision records) where they exist
  ├─ Read the spec's decisions log Active entries + specs/decisions.md (mandatory under vision.md)
  ├─ Read features/README.md and specs/README.md where present (state sidecars, never truth)
  ├─ Read external-API wrapper code for any third-party service the product integrates (for V5 claims)
  └─ Build the invariants ledger the spec MUST honor (the prosecution target for the product persona)

Seam alignment (director call; runs ONLY when a seam is unbound)
  ├─ Skip — and record the skip — when Active bound entries already cover every seam
  ├─ Two or three named directions, each stating its split-line predicate, rough brief count, seam placement
  ├─ A seam that only lands if another spec section changes → file SPEC_AMENDMENT_NEEDED and stop
  ├─ One AskUserQuestion with a stated pick (_decompose-common § Director arbitration)
  └─ Append the pick to the spec's decisions log as a Status: bound entry

Draft (LLM judgment; main thread)
  ├─ Mirror the section template in _spec-common/spec-format.md (core + applicable optional sections)
  ├─ State each invariant as a checkable condition; define each load-bearing term before use
  ├─ Name the domain for every quantified invariant / feature area
  ├─ Surface unresolved product questions in ## Open questions; omit the section when there are none
  ├─ Draft ## Decomposition LAST: enumerate units → apply the bound seam's predicate → assign → write stubs
  └─ Emit first draft to in-memory buffer (NOT yet written to disk)

Shape gate (deterministic, HARD-blocking; against the in-memory draft)
  ├─ Required sections present and ordered per _spec-common/spec-format.md, Decomposition's four subsections present
  ├─ Banned-pattern, status-token, and implementation-creep scan; frontmatter shape
  └─ FAIL → partial draft with SPEC_SHAPE_FAILED in ## Pending blockers

Decomposition conformance gate (HARD-blocking; mirrors the EP author's Brief-conformance gate slot)
  ├─ Materialize the in-memory draft to ~/.claude/cache/author-state/<key>-DRAFT.md
  ├─ Spawn one Scope-fidelity Adversary per claimed quantifying invariant, isolated, one each, off-model
  ├─ Check: every unit claimed or excluded, every seam carrying a predicate, every claimed invariant carrying a proof owner
  ├─ Check: status-token scan over the section (files DECOMPOSITION_STATUS_LEAK)
  ├─ Check (vision.md present): map conformance — owns what its entry owns, defines nothing a neighbor owns
  ├─ A stub that only works if another spec section changes → file SPEC_AMENDMENT_NEEDED and stop
  └─ Findings → DECOMPOSITION_COVERAGE_GAP / DECOMPOSITION_STATUS_LEAK / SEAM_PREDICATE_MISSING /
      SURFACE_PARITY_GAP / SPEC_NONGOAL_TRESPASS / SPEC_AMENDMENT_NEEDED / MAP_CONFORMANCE_GAP

Lint gate (deterministic, HARD-blocking in ship mode; reporting under --draft)
  ├─ Write the in-memory draft to a temp file; run plan-lint/lint.py --type spec --strict against it
  ├─ Exit 0 → continue; exit 1 → local fixes, re-run up to 2x, else STRUCTURAL_LINT_FAILED
  └─ Delete the temp file regardless of outcome

Ground-truth audit  (_author-common/ground-truth-protocol.md; skipped in --draft mode)
  ├─ Tokenize draft for V1-V5 claims
  │   (V4 internal-cross-section + invariant-ledger conformance and V5 external-API dominate;
  │    V4 also covers coverage-table citations, seam-decision citations, and the map entry;
  │    V3 data/constraint reality; V1/V2 path/identifier are RARE → drift if present)
  ├─ Verify each claim against the invariant ledger / vision / decisions log / design docs / APIs / data state
  ├─ Apply outcomes (verified / softened / corrected / dropped / restructured)
  └─ Write sidecar audit log

Self-prosecution and emission  (_author-common/self-prosecution-protocol.md; skipped in --draft mode)
  ├─ Spawn product + architecture persona agents in parallel
  │   (each runs the premise-interrogation sub-pass + the standard-prosecution sub-pass)
  ├─ THEN run the Imagined-brief-author dry run (_decompose-common § The imagined-downstream-author dry run):
  │     - Take the first brief with no unmet dependency
  │     - Attempt its Goals as a thought experiment from its stub + features/README.md entry alone
  │     - File every unanswerable question as IMPLEMENTABILITY_GAP against that brief slug
  ├─ Consolidate findings; apply auto-fixable
  ├─ Run post-fix premise verification on orchestrator-rewritten prose
  ├─ Classify residuals (STABLE_DISAGREEMENT, OPEN_QUESTION, FIX_INTRODUCED_PREMISE_INVERSION)
  └─ Decide emission:
      ├─ APPROVED: write spec.md with NO `Status:` frontmatter + persist sidecar + render verdict
      │            (open IMPLEMENTABILITY_GAPs travel here, keyed by brief slug — they do NOT gate APPROVED)
      └─ NEEDS_USER_INPUT: write partial draft with `Status: needs-user-input` and inline `## Pending blockers` + persist sidecar + render verdict
```

In `--draft` mode the Decomposition conformance gate, Ground-truth audit, and Self-prosecution stages are skipped; the draft is emitted directly with `verdict: "DRAFT_EMITTED"`. The Shape gate and the Lint gate still run but report instead of blocking — the Lint gate drops `--strict`, so a WARN stays a WARN. `--draft` is unhardened by choice, and a shape or lint defect in it is information, not a refusal.

---

## State load

Resolve in this order, because everything below keys off the result:

1. **The spec path**, per § Spec resolution.
2. **`<project>`** — `git rev-parse --show-toplevel` basename, else cwd basename.
3. **The vision gate** — does `vision.md` exist at the repository root? This one file-presence test decides the sidecar key, whether a map entry binds the run, and whether the decisions log is mandatory. Never ask; never infer it from anything else.
4. **`<spec-slug>`** — the `specs/<slug>/` directory name of the resolved spec, when the gate is on.

Read the sidecar if it exists. Schema:

```json
{
  "project": "<project>",
  "spec_slug": "<slug> | null",
  "vision_present": true,
  "artifact_path": "specs/<slug>/spec.md",
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
  "shape_gate": "passed | findings_filed",
  "decomposition_gate": {
    "conformance_gate_model": "<pinned off-model>",
    "seam_decisions_consulted": [
      { "seam": "<name>", "log": "<decisions-log path>", "entry": "<heading>", "status": "bound" }
    ],
    "seam_alignment": "skipped_all_bound | ran",
    "coverage": {
      "units_total": <int>,
      "units_claimed": <int>,
      "units_excluded": <int>,
      "invariants_with_proof_owner": <int>,
      "brief_count": <int>,
      "dag_depth": <int>,
      "open_seam_decisions": <int>
    },
    "scope_adversaries": [
      { "invariant": "<verbatim>", "brief": "<slug>", "verdict": "passed | surface_parity_gap_fixed_in_gate | surface_parity_gap" }
    ],
    "invariants_skipped_not_quantifying": [<verbatim>, ...],
    "map_conformance": "not_applicable | passed | findings_filed",
    "dry_run": {
      "brief_attempted": "<slug>",
      "verdict": "implementable | gaps_filed",
      "gaps_by_slug": { "<slug>": [ { "question": "<verbatim>", "where": "<brief section>", "severity_test": "<falsifiable scenario>" } ] }
    },
    "blockers": [<verbatim findings, merged>]
  },
  "plan_lint_log": {
    "invocation": "<command line as run, including --type spec and --strict when ship mode>",
    "exit_code": <int>,
    "stdout": "<verbatim>",
    "reruns": <int>
  },
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

`DRAFT_EMITTED` is written when the user invokes with `--draft` (the conformance gate, ground-truth, and self-prosecution skipped; shape and lint reporting rather than blocking). The reviewer (`/spec-review`) treats `DRAFT_EMITTED` as "intentionally unhardened" and warns rather than re-prosecutes.

`prior_blockers` / `recently_resolved_blockers` mirror the reviewer state schema in `~/.claude/cache/review-state/`. HIGH+ self-prosecution residuals land in `prior_blockers`; LOW residuals under the polish floor stay in `authoring_residual`. Every open `IMPLEMENTABILITY_GAP` lands there too — one entry per affected brief slug, `path_or_section` carrying the slug — so `/explain-blockers` sees them on an APPROVED sidecar, which is the verdict they normally travel with. They stay in `decomposition_gate.dry_run.gaps_by_slug` as well; that block is what `/brief-author` reads to refuse a slug.

`decomposition_gate` is the block `/spec-review` recomputes. It re-derives the coverage map from the spec on disk and files `AUTHOR_GATE_DRIFT` when its numbers disagree with `coverage`, or when the block is absent from a sidecar that should carry it — the same way the engineering-plan reviewer treats its own gates. `dry_run.gaps_by_slug` is what `/brief-author` reads to refuse an affected slug, so the keys are brief slugs and never section names.

If `last_spec_sha256` matches the SHA of the resolved spec on disk, it is unchanged since the last invocation. If it differs (the user edited it manually), treat as a fresh authoring round (cold w.r.t. ground-truth, warm w.r.t. carry-forward).

Also read the reviewer's state at the matching `~/.claude/cache/review-state/` key if it exists — its `recently_resolved_blockers` may include spec-layer items the user already arbitrated. Re-introducing an invariant / feature area / non-goal the user already removed is the worst thrash form.

**Legacy sidecar under a newly-arrived `vision.md`.** A project that grew a `vision.md` after its first authoring run has state under the unslugged key. Read it as carry-forward for the spec it actually describes, write forward under the slugged key, and say so in the verdict. Never merge two specs' histories into one file.

---

## Source ingest

Read in this order. Read once into context; do not re-read in later stages.

1. `~/.claude/skills/_spec-common/spec-format.md` — the format being applied (section template, drafting rules, claim emphasis, persona set).
2. `~/.claude/skills/_decompose-common/decomposition-principles.md` — split-line predicates, the coverage-map contract, the truth-versus-state split, the dry run, and the arbitration format. The `## Decomposition` section is drafted against this file.
3. `CLAUDE.md` (project root, and any nested `CLAUDE.md`) — project conventions and bound invariants. The spec must honor these.
4. `MEMORY.md` + every memory file under `~/.claude/projects/<project>/memory/` whose `description` hints at relevance — bound invariants and project assumptions the spec must honor.
5. **`vision.md` and this spec's map entry, where `vision.md` exists** — HARD-blocking. The entry states what this spec owns, its split line against each neighbor, its dependencies, and the vision sections it is the definition site for. Read the cut list and the decision ledger too: the cut list orders what the spec may assume survives, the ledger says what is already closed. A spec whose map entry is missing from an existing `vision.md` stops and reports — the boundary is a director call, not something to invent here.
6. Existing spec (when re-authoring). The current content is a carry-forward constraint. A mid-cycle `Status: needs-user-input` spec is resolved by the session agent applying blocker resolutions directly, not by re-running this skill.
7. Project design docs where they exist — `docs/*`, `context/*`, architecture or decision records. Grounding the spec must stay consistent with.
8. **The spec's decisions log**, Active `Status: bound` entries only, plus `specs/decisions.md` where a `specs/` tree exists, nearest log first. Under `vision.md` the log is **mandatory**: a resolved spec with no decisions log beside it is a blocker, not a degraded run, because Seam alignment has nowhere to land its pick and bound seams have nowhere to be read from. Without `vision.md` the log is created at root if absent.
9. **State sidecars where they exist** — `features/README.md` and `specs/README.md`. These say where work stands; they are read for context and are never a source for a truth-doc sentence. Nothing read here enters `## Decomposition`, though a Deferred-spec-surface entry paired with a bound decisions entry is what the conformance gate checks a deferral against.
10. External-API wrapper code for each third-party service the product integrates (e.g. `backend/src/lib/<service>.ts`) — the canonical contract for V5 claims.

The bound sources come before the decomposition inputs on purpose: the ledger, the map entry, the existing spec, and the design docs are what a seam decision is read *against*, so they are in context before the decisions log and the state sidecars are opened.

Never `handoffs/`. It holds point-in-time working files; nothing in it is current truth and it is never a source for a stub.

After reading, build an **invariants ledger** — the facts the spec MUST honor, drawn from `CLAUDE.md` + project memory + the Active bound entries + the map entry where one exists. Examples vary per project (an app: business rules, banned data patterns, "no existing users yet"; an infra product: isolation guarantees, safety preconditions, autonomy boundaries). The ledger is the prosecution target for the Self-prosecution stage's product persona.

**What the spec anchors against depends on the vision gate.** Without `vision.md` the spec is the root: its grounding is *internal* (cross-section consistency), the *invariant ledger*, *design docs*, and *external reality* (APIs, data state), and there is no upstream product document to look for. With `vision.md` the map entry is a real upstream — the spec covers what its entry owns, defines nothing a neighbor owns, and honors each split-line predicate. A spec that needs a rule vision does not carry is amending vision: escalate `VISION_AMENDMENT_NEEDED`; this skill never edits `vision.md`.

---

## Seam alignment

Where the briefs get cut is the director's call, not this skill's. The stage runs in `_decompose-common/decomposition-principles.md` § Director arbitration's shape — the same shape `/plan-alignment` uses for architecture directions.

**It runs only when a seam is unbound.** Enumerate the seams the draft will need, then read the Active `Status: bound` entries in the spec's decisions log (and `specs/decisions.md` where present). If every seam is covered by a bound entry, skip the stage, record `seam_alignment: "skipped_all_bound"` with the entries consulted, and go to Draft. Re-asking a bound seam every run is how a director learns to skip the question.

For each unbound seam:

1. **Two or three named directions.** Named for what they do (`pair-table-first`), never lettered or numbered — a named direction is referable in the log months later.
2. **Each states its split-line predicate**, plus one clause on what the direction commits to, a rough brief count, and where the seam lands. A direction whose predicate cannot be written is not a direction; drop it rather than pad the list.
3. **One `AskUserQuestion`**, with the pick stated and one sentence leading with what the call makes expensive to reverse. Cluster seams that share one answer into a single call. Never pad to three with strawmen — a single named direction with its reason is a valid shape.
4. **The pick appends to the spec's decisions log** as a `Status: bound` entry under `## Active (bound)`, in that log's entry format. The spec states only the outcome; rejected directions and arbitration reasoning live in the log, which carries the historical-commentary carve-out the spec does not.

A direction that contradicts an Active bound entry is never offered. Surface the contradiction as a question instead, and supersede the old entry the log's two-step way only if the director re-cuts.

**A seam that only lands if the spec changes files rather than picks.** Where every candidate split line needs another spec section — an invariant, a feature area, a Non-goal — to say something it does not, the amendment is the decision and the seam is downstream of it. A wording change that is the author's to make lands in the contradicted section in this run, and the directions are re-offered against the amended spec. A change that is the director's — a bound rule, a Non-goal the seam would have to trespass — files `SPEC_AMENDMENT_NEEDED` naming the section that owes it, and the stage stops there. Binding a boundary against a rule the spec does not carry leaves every stub below it reading as settled.

Under `vision.md`, a seam against a neighboring spec is already bound by the map's split line. Restate it; do not re-cut it. Re-cutting a boundary vision fixes is a `VISION_AMENDMENT_NEEDED` escalation, not an option on this menu.

---

## Draft

Mirror the section template in `~/.claude/skills/_spec-common/spec-format.md` — the universal core (Overview, Domain model & core concepts, Invariants & business rules, Feature areas, Non-goals & scope bounds, Decomposition, Glossary) plus the optional sections (Open questions, Roadmap / milestones, Analytics & observability, External integrations) that apply to this project type. Omit optional sections that do not apply; do not stub them.

### Section order within the draft

`## Decomposition` is drafted **last**, after every section it enumerates exists. Inside it, the order is fixed and is the point of the stage:

1. **Enumerate the units** mechanically — every invariant, every feature area, every non-goal, every domain-model or glossary term owing authored content. The enumeration reads the draft and returns its units; do not hand-pick, because a hand-picked universe cannot show an omission.
2. **Apply the bound seam's predicate** to each unit.
3. **Assign** — a claiming slug, or `excluded by <seam name>`. Two states, no third.
4. **Write the stubs and the Briefs table** against what the assignment produced.

Mapping before cutting is what makes an unclaimed unit visible before a seam hardens around it. A decomposition drafted in the other order reads clean and hides exactly the narrowing the coverage table exists to catch.

**Re-author semantics.** The section re-derives every run against the bound seam decisions — never carried forward byte-identical, because an edit above it can change what a unit is. A re-derivation that moves a boundary an Active bound entry fixes is `FIX_INTRODUCED_PREMISE_INVERSION` unless the director explicitly re-cut at Seam alignment, which supersedes the old entry in the log.

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
- **The decomposition carries no state** — no lifecycle words, no dates, no counts of what exists yet, no park or loan language. A unit another domain owns is excluded by a named seam, which is true whether or not that domain's spec has been written. Everything that churns belongs in `features/README.md`. The token scan is lexical: an ordinary-word use ("shipped unaccented") trips it the same as a status claim, so write around the token list.
- **Vocabulary is real.** Seams, slugs, and stubs use the project's own terms and this spec's glossary. A new term is a director call.
- **The cut list binds** where the project keeps one: no brief for material the cut list cuts, and a brief straddling the line names where the line sits.

---

## Shape gate

Deterministic, runs against the in-memory draft before any agent is spawned, and hard-blocking in `ship` mode. It is the same structural check `/spec-review` runs at its Stage 0, applied here so a malformed draft never reaches a gate that costs subagents — the brief and engineering-plan authors gate on their own in-memory drafts the same way.

Apply `_spec-common/spec-format.md`: required core sections present and in order, `## Decomposition` carrying all four subsections non-empty, optional sections non-empty where present, frontmatter shape, banned-pattern absence, status-token absence inside `## Decomposition`, implementation-creep absence. The status-token list is the spec layer's, given in full at the Decomposition conformance gate below.

A failure emits the partial draft with `Status: needs-user-input` and `SPEC_SHAPE_FAILED` in `## Pending blockers`, naming each defect. In `--draft` mode the gate reports its findings in the verdict and does not block.

---

## Decomposition conformance gate

Mandatory in `ship` mode, hard-blocking, runs after the Shape gate and before the Lint gate. This is the spec layer's analog of `/engineering-plan-author`'s Brief-conformance gate — the author prosecuting its own in-flight decomposition before it reaches disk, so a coverage gap is refused at write time rather than surfaced a review later.

### Procedure

1. **Materialize the in-memory draft** to `~/.claude/cache/author-state/<sidecar-key>-DRAFT.md`. The adversaries need a file to Read, not a prompt-embedded string. Cleared on gate exit, pass or fail.

2. **Mechanical checks**, in the main thread, per `_decompose-common/decomposition-principles.md`:
   - Every enumerated unit is claimed by a slug in the Briefs table or excluded by a named seam → otherwise `DECOMPOSITION_COVERAGE_GAP`. The rule that admits no third state is claimed-versus-excluded: `structural — no brief could trespass it` in a Non-goal's Brief cell and `Director review — <reason>` in a Proof cell are exclusion written in those columns' terms, and both pass.
   - A unit the director deferred passes on evidence rather than assertion: a `features/README.md` Deferred-spec-surface entry **and** an Active `Status: bound` entry in the decisions log naming its destination. Verify the pair exists. Either half without the other is the gap, filed as `DECOMPOSITION_COVERAGE_GAP`.
   - Every seam carries a split-line predicate that decides the units the Coverage table assigns by it → otherwise `SEAM_PREDICATE_MISSING`.
   - Every claimed invariant carries a proof owner — a brief slug, or `Director review — <reason>` where no authored artifact could carry the check → otherwise `DECOMPOSITION_COVERAGE_GAP`. An invariant whose falsifier ranges over more than one brief is claimed by the conformance brief.
   - No stub does what a Non-goal excludes or what the project's cut list cuts → otherwise `SPEC_NONGOAL_TRESPASS`.
   - A stub that only works if another spec section changes → a wording change the author owns lands in that section in this run and the decomposition re-derives against it; a product call the director owns files `SPEC_AMENDMENT_NEEDED` naming the section, and the gate stops there.
   - The status-token scan runs over `## Decomposition` — `shipped`, `next up`, `in flight`, `parked`, `on loan`, `deferred until`, `TODO`, `not yet written`, `awaiting`, and any `YYYY-MM-DD` date — filing `DECOMPOSITION_STATUS_LEAK` per occurrence. `owed` is not a spec-layer token: `*Outcomes owed*` is a mandated Scope-stub field name and carries no lifecycle claim.
   - Compute `brief_count`, `dag_depth`, and `open_seam_decisions` and test them against the registry's spec-layer thresholds — `brief_count >= 9`, `dag_depth >= 4`, `open_seam_decisions >= 4` (`~/.claude/skills/_review-common/blocker-classes.md` § Decomposition); a breach files `DECOMPOSITION_SURFACE_EXCESS`, which is a director decision — never split the spec here. `dag_depth` is the longest dependency path through the Briefs table counted in edges, with the conformance sink excluded — the format mandates the sink and its depends-on-every-brief edges, so counting it would tax every spec one level for its required shape. `open_seam_decisions` is the count of seam questions awaiting a director pick: those surfaced at Seam alignment and not bound in either decisions log. The structural condition files the same class: the spec carries material on loan for more than one unwritten spec, read from `specs/README.md` § On loan or `features/README.md`'s deferred-surface list. Either form passes without filing when an Active `Status: bound` entry in the spec's decisions log accepts the size at values covering the recomputed ones; otherwise the finding routes to the director here, at write time, rather than a review later.

3. **One Scope-fidelity Adversary per claimed quantifying invariant.** Enumerate the invariants the Coverage table assigns to a brief; select those that quantify over a domain ("every", "all", "across", "any", "for each of the four…") or name an authoritative signal the outcome must be judged on. Concrete single-surface invariants are not at risk and get none. For each selected invariant spawn one adversary with the prompt in `~/.claude/skills/_review-common/brief-conformance-prosecutor.md`, substituting the claiming brief's stub for the plan under judgment and that one invariant for `{goal_under_review}`. **Never batch two invariants into one adversary** — isolation is the load-bearing separation. A brief claiming an invariant while its stub covers part of the invariant's domain files `SURFACE_PARITY_GAP`.

   **Expect the fan-out to be large at this layer.** Spec invariants almost all quantify, so a mature spec selects most of its claimed invariants — thirty-plus spawns including re-checks is normal, and the cost is deliberate. Conformance-claimed invariants are not exempt: the conformance stub's proof-shape wording is where parity gaps concentrate, so narrowing the selection to delivering-brief claims to save spawns trades away exactly the findings the gate exists for.

   **Model pin.** Every adversary takes an explicit off-model `model` override per that file's § Model pin (default `sonnet`; `opus` when the session is already Sonnet). Never inherit — this gate judges the author's own draft, and a judge sharing the drafter's priors is the bias it exists to remove. Record it as `decomposition_gate.conformance_gate_model`.

4. **Map conformance**, when `vision.md` exists. Check the draft against this spec's map entry along three lines: it covers every surface the entry says it owns; it defines nothing a neighbor's entry owns; each split-line predicate in the entry is honored by the seam that restates it. A mismatch files `MAP_CONFORMANCE_GAP` — the entry is a claim about a real file, so this is falsifiable rather than a judgment call. One deviation passes on evidence instead of filing: a neighbor-owned surface the project's state sidecar (`specs/README.md` § On loan) records as held by this spec until the owner is authored. The loan is state and the map is the end state — verify the loan entry names this spec as holder and the neighbor as owner, note it in the sidecar's `map_conformance` value, and do not file the gap; a neighbor-owned surface with no recorded loan is still the gap. Where `vision.md` is absent, record `map_conformance: "not_applicable"` and skip.

5. **Process findings.** All checks clean → proceed to the Lint gate. **Author-fixable findings are fixed inside the gate, not escalated.** A finding is author-fixable when its resolution is stub or coverage wording the author owns — it contradicts no Active bound entry, moves no bound boundary, and needs no other spec section to change. Apply the fix to the in-memory draft, re-spawn only the affected adversaries against the fixed text (up to twice per finding, mirroring the Lint gate's rerun loop), and record the finding, the fix, and the re-check verdict in the sidecar. Whatever the author does not own escalates: a finding whose every resolution path is a director call (a bound-entry contradiction, a boundary move, a scope cut) → partial draft to disk with `Status: needs-user-input` and the findings verbatim in `## Pending blockers`, each with its resolution paths — HIGH HARD as blockers, MEDIUM HARD for the user to adjudicate rather than being told the draft is wrong. A `SPEC_AMENDMENT_NEEDED` finding always stops the gate here: the section it names is the decision, and re-deriving the decomposition against an unamended spec re-produces the same finding.

6. **Sidecar block.** Write the aggregated output to `decomposition_gate` per the State-load schema — the seam decisions consulted, the coverage counts, the per-invariant adversary verdicts, the map-conformance result, and the merged findings. `/spec-review` recomputes these and files `AUTHOR_GATE_DRIFT` on disagreement.

---

## Lint gate

Deterministic, runs immediately after the Decomposition conformance gate and before the Ground-truth audit. Hard-blocking in `ship` mode; reporting under `--draft`.

Write the in-memory draft to a temp file, then:

```bash
python3 ~/.claude/skills/plan-lint/lint.py --type spec --strict <temp-draft-path>
```

The linter dispatches on path shape by default; `--type spec` forces the kind for a draft whose temp filename does not carry its identity, and the flag is positional-first. `--strict` exits 1 on a WARN as well as a FAIL, which is what makes a decomposition-less draft block here: legacy-warn severity is for a document already on disk, never for one this skill is writing now. Under `--draft` the flag is dropped, the run reports, and its exit code is recorded rather than acted on. Capture the invocation, stdout, and exit code into the sidecar's `plan_lint_log`. Exit codes: `0` clean, `1` FAIL (under `--strict`, WARN too), `2` usage/IO error.

On exit 1 in `ship` mode, read the failure list, apply **local** fixes to the in-memory draft (rewrite prose, fill a cell), and re-run — up to twice. A defect needing a structural fix (dropping a brief, re-cutting a seam, reordering the graph) is not fixed in-loop: surface `STRUCTURAL_LINT_FAILED` with the lint output verbatim and let the director arbitrate. On exit 2, re-check the temp path and content; a persistent error is also `STRUCTURAL_LINT_FAILED`, with stderr verbatim.

Delete the temp file regardless of outcome.

---

## Ground-truth audit

Apply `_author-common/ground-truth-protocol.md`. At the spec layer the dominant claim classes are:

- **V4 (Cross-document)** in five forms:
  - **Internal cross-section consistency** — a claim in one section that references or depends on another (e.g. §Feature areas leaning on a §Invariants rule, §Invariants leaning on a §Domain model definition). Verify the referenced section says what the claim assumes.
  - **Invariant-ledger conformance** — every spec rule that restates or depends on a `CLAUDE.md` / project-memory invariant. Verify the spec does not contradict the bound invariant.
  - **Coverage-table citations** — every unit in §Decomposition's Coverage table quotes a unit the spec actually carries, and every claiming slug appears in the Briefs table. A row citing a unit that no longer exists is a false claim about the document it sits in.
  - **Seam-decision citations** — every seam matches the Active `Status: bound` entry that fixed it. A seam whose predicate has drifted from its bound entry is the re-derivation failure `FIX_INTRODUCED_PREMISE_INVERSION` names.
  - **Map-entry conformance**, where `vision.md` exists — the surfaces the spec defines are the surfaces its entry assigns it. Verified in full at the Decomposition conformance gate; re-checked here for any sentence the gate's fixes rewrote.
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

### Imagined-brief-author dry run (after the personas return)

The spec layer's Imagined-Implementer, run per `_decompose-common/decomposition-principles.md` § The imagined-downstream-author dry run with the downstream author `/brief-author` and the unit *brief*. It is what separates a decomposition that is merely shape-correct from one a brief author can start from.

1. **Pick the first brief with no unmet dependency** — `Depends on` empty, or every dependency already bound. Where several qualify, take the one `features/README.md` marks next, otherwise the first in the Briefs table.
2. **Attempt its Goals as a thought experiment, without writing the brief**, from its scope stub plus its `features/README.md` entry and nothing else. Follow what `/brief-author` would do: read outcomes owed as the Goal source, sort the inherited exclusions into Scope buckets, and consult the Active bound entries in the spec's decisions log.
3. **File every question the entries leave unanswerable** as `IMPLEMENTABILITY_GAP` **against that brief slug**, each carrying the question, where in the brief it would have to be answered, and a `severity_test` — a falsifiable scenario in which leaving it open stops the brief author ("if the seam between X and Y is unstated, the brief's second Goal cannot name the domain it quantifies over").

**The entries are the whole input.** Reaching past them — into the spec's other sections, into a sibling's stub, into this skill's own memory of the draft — makes the dry run pass on knowledge the brief author will not have. Every reach is the finding.

The gaps are per-brief, so they do **not** gate the verdict. They travel in the sidecar under `decomposition_gate.dry_run.gaps_by_slug` and in the verdict's `### Implementability gaps` block; `/brief-author` refuses for a slug carrying an open gap, the same way it refuses against a `Status: needs-user-input` upstream, and every other slug stays authorable.

After consolidation, run post-fix premise verification on any orchestrator-rewritten prose. Classify residuals.

### Verdict template

```markdown
# Spec authoring verdict — <spec-path> (<project>[/<spec-slug>])

**Mode:** cold | warm
**Authoring mode:** ship | draft
**Round:** <invocation_number>
**Last spec sha:** <hex>
**Upstream:** vision.md § spec map, entry `<slug>` | none (root spec)

## Seam alignment
**Status:** skipped (all seams bound) | ran
**Seams bound this run:** <name> → <decisions-log entry heading> ... (omit when skipped)
**Bound entries consulted:** <N>

## Shape gate
**Status:** PASS | FAIL
**Defects:** <N>; if FAIL, list each.

## Decomposition conformance gate
**Coverage:** <units_claimed> claimed + <units_excluded> excluded of <units_total>; <invariants_with_proof_owner> invariants with a proof owner
**Briefs:** <brief_count>; DAG depth <dag_depth>; open seam decisions <open_seam_decisions>
**Scope-fidelity adversaries:** <N> spawned (<M> passed, <K> gaps); model `<conformance_gate_model>`
**Map conformance:** not applicable | PASS | <N> findings
**Findings:** <N>; <by class>

## Lint
**Status:** PASS | FAIL
**Defects:** <N>; if FAIL, list each.

## Ground-truth audit
**Claims total:** <N>
**Verified:** <V>  **Softened:** <S>  **Corrected:** <C>  **Dropped:** <D>  **Restructured:** <R>  **Skipped (carve-out):** <K>

## Self-prosecution
**Personas:** product, architecture
**Premise interrogation:** <product=passed/failed>, <architecture=passed/failed>
**Standard findings:** <N total>; <by tier+severity>
**Post-fix premise verification:** <P claims rewritten; Q falsified> → <FIX_INTRODUCED_PREMISE_INVERSION count>
**Carry-forward consultation:** <skipped because cold mode | M recently-resolved blockers cross-checked, R re-prosecutions auto-retracted>

## Imagined-brief-author dry run
**Brief attempted:** `<slug>`
**Verdict:** implementable | gaps_filed
**Implementability gaps:** <N>, keyed by brief slug

## Verdict
**APPROVED** | **NEEDS_USER_INPUT** | **DRAFT_EMITTED**

### Blockers (if NEEDS_USER_INPUT)
- [STABLE_DISAGREEMENT] <span> — <one-line>
- [OPEN_QUESTION] <span> — <one-line>
- [FIX_INTRODUCED_PREMISE_INVERSION] <span> — <one-line>
- [SPEC_SHAPE_FAILED] <defect> — <one-line>
- [STRUCTURAL_LINT_FAILED] <lint defect> — <one-line>
- [DECOMPOSITION_COVERAGE_GAP] <unit> — <one-line>
- [DECOMPOSITION_STATUS_LEAK] <span> — <one-line>
- [SEAM_PREDICATE_MISSING] <seam> — <one-line>
- [DECOMPOSITION_SURFACE_EXCESS] <sub-metric values> — <one-line; director call>
- [SPEC_NONGOAL_TRESPASS] <stub> — <one-line>
- [SPEC_AMENDMENT_NEEDED] <spec section> — <one-line; the seam or stub needs that section to change; director call>
- [SURFACE_PARITY_GAP] <invariant> — <one-line>
- [MAP_CONFORMANCE_GAP] <surface> — <one-line>
- [VISION_AMENDMENT_NEEDED] <rule> — <one-line; director call>
- [HOIST_INCOMPLETE] <parked item> — <one-line; substance missing from the authored spec>
- [REPO_STATE_DRIFT] <what moved> — <one-line>

### Implementability gaps (do NOT gate APPROVED)
- `<brief-slug>`: <question>; <where it must be answered>; <severity_test>

### Authoring residuals (LOW, under polish floor)
- ...
```

### Verdict gates

- **APPROVED** when ALL of:
  - Authoring mode is `ship` (not `--draft`).
  - Shape gate PASS, Decomposition conformance gate clean, Lint PASS.
  - Ground-truth complete (no V1-V5 class left unverified outside carve-out).
  - All HIGH+CRITICAL self-prosecution findings resolved.
  - Tier-1 weight = 0.
  - Tier-2 weight ≤ 4 (polish floor).
  - No `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `FIX_INTRODUCED_PREMISE_INVERSION`, `SPEC_SHAPE_FAILED`, `STRUCTURAL_LINT_FAILED`, `DECOMPOSITION_COVERAGE_GAP`, `DECOMPOSITION_STATUS_LEAK`, `SEAM_PREDICATE_MISSING`, `DECOMPOSITION_SURFACE_EXCESS`, `SPEC_NONGOAL_TRESPASS`, `SPEC_AMENDMENT_NEEDED`, `SURFACE_PARITY_GAP`, `MAP_CONFORMANCE_GAP`, `VISION_AMENDMENT_NEEDED`, `HOIST_INCOMPLETE`, `REPO_STATE_DRIFT`.
- **NEEDS_USER_INPUT** when authoring mode is `ship` AND any APPROVED condition fails.
- **DRAFT_EMITTED** when authoring mode is `--draft`.

**The verdict stays two-state in `ship` mode.** `IMPLEMENTABILITY_GAP` gates neither: the gap is per-brief, so blocking the one slug it names is more precise than a whole-spec third state, and it matches the engineering-plan semantics it borrows. An APPROVED spec carrying gaps is a spec whose roster is authorable except for the named slugs.

Disk-write semantics:
- **APPROVED** → write `spec.md` with NO `Status:` frontmatter; persist sidecar; print verdict. If the on-disk file still carries `Status: needs-user-input` and a `## Pending blockers` section, this emission removes that line and the section. **Next step:** run `/spec-review` to prosecute the draft.
- **NEEDS_USER_INPUT** → write `spec.md` with frontmatter `Status: needs-user-input` AND an inline `## Pending blockers` section listing each unresolved finding verbatim; persist sidecar with `verdict: "NEEDS_USER_INPUT"`; print verdict including the unresolved blockers. The session agent then applies your blocker resolutions directly to `spec.md` and removes the `Status:` line + `## Pending blockers` section once the blockers clear — the author is not re-invoked. Downstream skills that anchor on the spec treat a `Status: needs-user-input` spec as mid-cycle.
- **DRAFT_EMITTED** → write the spec with NO `Status:` frontmatter; persist sidecar with `verdict: "DRAFT_EMITTED"` AND `authoring_mode: "draft"`; print verdict noting the draft is unhardened by choice (`--draft` skipped the Decomposition conformance gate, Ground-truth audit, and Self-prosecution) and listing any Shape-gate and Lint-gate defects the reporting passes found.

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

- **Stage order is fixed.** Source ingest, then Seam alignment, then Draft. Shape gate, then the Decomposition conformance gate, then the Lint gate, then Ground-truth audit, then Self-prosecution and emission. `--draft` skips the Decomposition conformance gate, Ground-truth audit, and Self-prosecution, and downgrades the Shape gate and the Lint gate to reporting.
- **Seam alignment never re-asks a bound seam.** Bound entries covering every seam skip the stage, and the skip is recorded. A boundary an Active bound entry fixes is moved only when the director re-cuts, which supersedes the old entry the log's two-step way — a re-derivation that moves it silently is `FIX_INTRODUCED_PREMISE_INVERSION`.
- **`## Decomposition` is drafted last and re-derived every run.** Never carried forward byte-identical. Enumerate, then apply the predicate, then assign, then write stubs — mapping before cutting is what makes an unclaimed unit visible.
- **The Decomposition conformance gate is mandatory in `ship` mode and hard-blocking.** Its adversaries run off-model, one invariant each, never batched.
- **The decomposition carries no state.** Lifecycle words, dates, counts of what exists yet, and park/loan language belong in `features/README.md`. This skill never writes status into the spec to make the coverage table read better.
- **Under `vision.md` the map entry binds.** The spec covers what its entry owns and defines nothing a neighbor owns. This skill never edits `vision.md`; a needed rule vision does not carry escalates as `VISION_AMENDMENT_NEEDED`.
- **Under `vision.md` the spec's decisions log is mandatory.** A resolved spec with no log beside it is a blocker, not a degraded run.
- **`handoffs/` is never read.** Not as a source for a stub, not as grounding, not as context.
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

**`--draft` mode:** Decomposition conformance gate, Ground-truth audit, and Self-prosecution skipped; the Shape gate and the Lint gate report without blocking, the latter running without `--strict`. Sidecar written with `authoring_mode: "draft"` and `verdict: "DRAFT_EMITTED"`. The spec IS written to disk with NO `Status:` frontmatter. `/spec-review` proceeds with full prosecution but surfaces a draft warning.

**No argument and several spec folders under `specs/`:** ambiguous. List the specs and ask which to author. Never guess, and never default to the first — authoring the wrong spec writes a decomposition against the wrong boundary.

**`vision.md` present, no map entry for the resolved spec:** stop and report. The entry is where this spec's boundary is bound, and inventing one here would let a spec claim surface a neighbor owns. Point the user at `/vision-author <slug>` to deepen the map first.

**`vision.md` present, no decisions log beside the spec:** blocker. Seam alignment has nowhere to land a pick and bound seams have nowhere to be read from. Create the log's path only on the director's say-so; report otherwise.

**`vision.md` absent:** every per-system behavior is off — unslugged sidecar key, no map entry, no vision trace, root `spec.md` and root `decisions.md` (created if absent). The Decomposition section is still required: a project with one spec still needs its briefs cut and its coverage proved.

**A seam is unbound and the director is unavailable:** do not pick one to keep moving. Emit the partial draft with the seam question in `## Pending blockers` — a decomposition cut against a guessed boundary is worse than no decomposition, because every stub below it reads as settled.

**`CLAUDE.md` absent:** Run with degraded ground-truth coverage. Print a warning. The product persona's prosecution is weaker (fewer ledger invariants), but internal-consistency and external-API verification still run.

**Project memory absent (no `~/.claude/projects/<project>/memory/MEMORY.md`):** Run with degraded coverage. Print a warning. The invariant ledger is built from `CLAUDE.md` alone.

**`features/README.md` absent (the `features/` workflow never scaffolded):** Run with the dry run degraded — the imagined brief author reads the stub and the decisions log alone, and the verdict says so. The deferral evidence-pair check cannot pass without the sidecar half, so a director-deferred unit cannot be recorded until `/features-init` runs; with no deferrals claimed this is a warning, not a blocker.

**Design docs contradict each other:** The spec cannot inherit from two contradictory design docs silently. Surface the contradiction as `OPEN_QUESTION` (the user picks which design doc is canonical, or the spec resolves it explicitly).

---

## Relationship to sister skills

- **`/vision-author`** owns the layer above, where `vision.md` exists. Its spec map decides which specs exist, what each owns, and the split line between neighbors — all of it bound input here, never re-cut. A boundary that needs to move is a `/vision-author` run, not a seam this skill re-arbitrates. Where there is no `vision.md`, nothing sits above the spec and this skill is the root author.
- **`/spec-review`** prosecutes the spec written here and consults this skill's sidecar to skip re-prosecuting author-arbitrated claims. It recomputes the `decomposition_gate` block and files `AUTHOR_GATE_DRIFT` on disagreement. It is the immediate next step after this author's first clean draft.
- **`/brief-author`** consumes the spec downstream: it resolves the spec by the same layout detection, reads its `## Decomposition` stub for the feature under work (outcomes owed are the Goal source; each inherited exclusion names its source, from which the brief's scope bucket is derived), and reads the spec's decisions log Active entries alongside the feature's own. It refuses for a slug carrying an open `IMPLEMENTABILITY_GAP` in this skill's sidecar. **A spec is what unblocks its own downstream chain** — `/brief-author` hard-refuses without one to anchor against. Below the brief the dependency is indirect: `/engineering-plan-author` reaches the spec through the brief's `**Spec:**` header and degrades to a recorded no-op when the header is absent, and `/plan-author` has no spec concept at all.
- **`/features-init`** scaffolds the `features/` workflow folder (briefs, engineering plans, chunk plans, decision logs) and its `README.md` — the state sidecar carrying everything the decomposition section may not: which briefs exist as folders, what is in flight, and which spec surface awaits a spec nobody has written. It does not write the spec.

Two decision logs, split by subject: a call about **which briefs exist or where a boundary sits** lands in the spec's decisions log; a call **inside one brief's scope** lands in `features/<brief-slug>/decisions.md`.

This skill exists to make the spec the cleanest artifact its briefs could descend from.
