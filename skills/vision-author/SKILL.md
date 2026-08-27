---
name: vision-author
description: Writes or rewrites `vision.md`'s spec map — the decomposition of vision into per-system specs, which is required format of `vision.md` rather than a separate artifact — applying ground-truth verification and self-prosecution at write time rather than review time. Section-bounded by default. Run once per cycle, then `/vision-review`. Sister to `/spec-author`, `/brief-author`, `/engineering-plan-author`.
user-invocable: true
---

# Vision author

Produces or rewrites the spec map in a project's `vision.md` with the same prosecution rigor `/vision-review` applies, but front-loaded at write time.

Vision is the **root** of the artifact lifecycle in a project that decomposes into per-system specs: every spec, brief, engineering plan, chunk plan, and line of code descends from it. A map that leaves a mechanism unowned, draws a seam nobody can apply to the next rule, or claims a spec owns a surface that spec does not define will cascade through *every* spec, and the downstream review machinery repairs the descendants, never vision itself. This skill makes the decomposition the cleanest thing in the document.

The canonical vision shape, the map's entry shape, the drafting rules, the claim emphasis, and the persona set live in `~/.claude/skills/_vision-common/vision-format.md` — read it before drafting. The decomposition machinery this layer shares with `/spec-author` — split-line predicates, the coverage-map contract, the truth-versus-state split, the imagined-downstream-author dry run, and the director-arbitration format — lives in `~/.claude/skills/_decompose-common/decomposition-principles.md`, read through its **Vision layer** column. Neither is duplicated here.

## Compatibility gate (runs first, before anything else)

This skill applies only where **`vision.md` exists at the repository root** (`git rev-parse --show-toplevel`, or cwd when not in a git repo). Detected by file presence, never by asking.

Where it is absent, decline in one line and stop:

```
No vision.md at the repo root — this project's root artifact is spec.md. Use /spec-author.
```

There is nothing to decompose: a project with a single root `spec.md` already has its root artifact, and `/spec-author` + `/spec-review` are its root pair.

## Inputs

- `$ARGUMENTS` (optional):
  - `<spec-slug>` — scope the run to deepening one map entry. This is the pass run immediately before authoring that spec, when the entry has to go from a paragraph to something `/spec-author <slug>` can start from. The rest of the map is a carry-forward constraint and is not re-cut.
  - `--draft` — quick-exploration mode; skip the Ground-truth audit and Self-prosecution, downgrade the Shape gate and the Plan-lint gate to reporting runs, and emit a sidecar marked `authoring_mode: "draft"` (unhardened by choice; `/vision-review` warns rather than refuses).

**The author runs once per cycle.** It produces the draft; the next step is `/vision-review`, and the session agent then applies its findings — plus your blocker resolutions — directly to `vision.md`. The author is not re-invoked to apply changes. There is no `--rewrite` flag.

## Scope — section-bounded by default

**The spec map is the section this skill owns unconditionally.** Every other section of `vision.md` it touches only when the run's trigger implicates that section, and it touches only the passage implicated.

Vision is the most hand-shaped document in the repo. A wholesale re-author on every invocation would flatten the director's own prose to clear a map defect, and the format cannot describe what would be lost. So the default is narrow by construction:

| Scope | Reached by | What may be edited |
|---|---|---|
| Map only | the default | the spec map section |
| Map + implicated sections | a trigger whose finding lands outside the map — an unranked cut-list item a seam depends on, a ledger entry that contradicts a mechanism section, a term used before it is bound | the map, plus the named passages |
| Whole document | an explicit plain-language clean-slate ask ("rewrite vision from scratch") | everything |

A whole-document re-author treats the existing `vision.md`, the roster, and any prior review state as carry-forward constraints: a mechanism, a non-goal, or a spec the director already removed is not re-introduced.

Record the resolved scope in the sidecar's `scope` field and on the verdict's `Scope` line, every run. A section edited outside the recorded scope is `FIX_INTRODUCED_PREMISE_INVERSION` against vision itself.

## Triggers

Four, resolved deterministically at State load from the sidecar plus disk. More than one may fire; the run handles all that do.

| Trigger | Fires when | What the run does |
|---|---|---|
| **Seed** | `vision.md` carries no spec map section | Survey vision whole and propose the full set of specs. |
| **Vision moved** | the vision sha differs from `last_vision_sha256` | Re-survey and propose the delta — only the entries the moved sections touch. |
| **A spec landed** | a `specs/<slug>/spec.md` is present or edited since `last_reconciled_specs[<slug>].sha` | Reconcile. The map changes only where the authored spec's real ownership diverged from what its entry claimed. |
| **A review parked something** | `specs/README.md` or a `specs/<slug>/decisions.md` gained a parked item since `last_review_at` | The roster absorbs it. The map changes only if the parking implies a boundary move. |

The last two are reconcile triggers and usually leave the map byte-stable. That is the expected outcome, not a failed run — say so in the verdict rather than manufacturing a diff.

## Sidecar location

`~/.claude/cache/author-state/<project>__vision.json`, where `<project>` is the basename of the repository root (or cwd when not a git repo). Same directory as the spec / brief / engineering-plan / chunk author sidecars; vision is keyed on the **project**, not a feature. `/vision-review` consults this sidecar to skip re-prosecuting claims the author already verified.

---

## Workflow

```
Compatibility gate (deterministic; runs first)
  └─ vision.md at repo root? no → decline in one line and stop

State load (deterministic; ~5 seconds)
  ├─ mkdir -p ~/.claude/cache/author-state (Write does NOT auto-create parents)
  ├─ Derive <project> from git toplevel (or cwd) basename
  ├─ Read sidecar at ~/.claude/cache/author-state/<project>__vision.json (if exists)
  ├─ Read review state at ~/.claude/cache/review-state/<project>__vision.json (warm carry-forward)
  ├─ Resolve the trigger set and the scope; record both
  └─ Determine cold vs warm mode

Source ingest (deterministic; ~60 seconds)
  ├─ Read _vision-common/vision-format.md and _decompose-common/decomposition-principles.md
  ├─ Read vision.md IN FULL (the cut list orders what a spec may assume survives;
  │   the decision ledger says what is already closed)
  ├─ Read CLAUDE.md, including the vocabulary table
  ├─ Read MEMORY.md + relevant project memory files
  ├─ Read specs/README.md (the roster — state, on-loan surface, hoist lists, parked items)
  ├─ Read every shipped specs/<slug>/spec.md and its specs/<slug>/decisions.md
  ├─ Read specs/decisions.md (the boundary-arbitration log)
  ├─ Read personas/README.md (which domain perspective owns which question)
  └─ NEVER handoffs/

Seam survey (LLM judgment; main thread)
  ├─ Enumerate candidate owners from three sources, each also a coverage obligation:
  │     mechanism sections · the vocabulary table · the decision ledger + the cut list
  ├─ Apply the seam test to every candidate boundary
  └─ Produce the candidate map + the unowned set, before writing a single entry

Seam alignment (per _decompose-common § Director arbitration)
  ├─ Skip — and record the skip — where Active `Status: bound` entries already cover every seam
  ├─ Cluster contested seams that share one answer into a single AskUserQuestion
  └─ Append each pick to specs/decisions.md as a `Status: bound` entry

Draft (LLM judgment; main thread)
  ├─ Map before you cut: enumerate units, apply the predicate, assign, then write the entries
  ├─ Write the map as vision's LAST section; never insert mid-document
  ├─ Edit implicated sections only where the trigger reached them
  └─ Emit the in-memory draft (NOT yet written to disk)

Shape gate (deterministic, HARD-blocking; against the in-memory draft; reports in --draft)
  ├─ Required sections present and ordered per _vision-common/vision-format.md
  ├─ Map-entry shape, map-is-last, frontmatter shape
  ├─ Banned-pattern and implementation-creep scan
  └─ FAIL → partial draft with VISION_SHAPE_FAILED in ## Pending blockers

Plan-lint gate (deterministic, HARD-blocking; reporting run in --draft)
  ├─ Materialize the draft to /tmp/<project>-vision-<timestamp>/vision.md
  ├─ Bash: python3 ~/.claude/skills/plan-lint/lint.py --strict <that path>
  ├─ Exit 0 → continue; exit 1 → local fixes, re-run up to 2x, else STRUCTURAL_LINT_FAILED
  └─ Delete the temp directory regardless of outcome

Ground-truth audit (_author-common/ground-truth-protocol.md; skipped in --draft)
  ├─ V4 internal cross-section consistency + invariant-ledger conformance
  ├─ V4 map-to-shipped-spec conformance → MAP_CONFORMANCE_GAP
  ├─ V3 constraint figures; V1/V2 rare → drift findings
  └─ Write sidecar audit log

Self-prosecution and imagined-spec-author (_author-common/self-prosecution-protocol.md; skipped in --draft)
  ├─ Spawn product + architecture + the project's domain-ownership persona, in parallel
  ├─ THEN run the Imagined-spec-author dry run → SPEC_BOUNDARY_UNBOUND
  ├─ Consolidate findings; apply auto-fixable; post-fix premise verification
  └─ Classify residuals

Coverage audit (runs in every mode; reports rather than blocks in --draft)
  ├─ Every vision section, vocabulary term, ledger item, and cut-list item resolves to an
  │   owning entry or to an explicit unowned line — enumerated from vision.md, never from the map
  └─ Gaps file VISION_COVERAGE_GAP

Emission
  └─ Decide emission via the three-state verdict
```

In `--draft` mode the Ground-truth audit and Self-prosecution are skipped, and the Shape gate and Plan-lint gate report instead of blocking; the draft is emitted with `verdict: "DRAFT_EMITTED"`. The Coverage audit still runs — enumerating the units is most of what a draft map is for — and its gaps land in the verdict as information rather than as blockers.

---

## State load

Derive `<project>` first: `git rev-parse --show-toplevel` basename, else cwd basename.

Read the sidecar if it exists. Schema:

```json
{
  "project": "<project>",
  "artifact_path": "vision.md",
  "authoring_mode": "ship | draft",
  "trigger": ["seed" | "vision_moved" | "spec_landed" | "review_parked"],
  "scope": "map | map_plus_sections | whole_document",
  "sections_touched": ["<section name>"],
  "argument_slug": "<spec-slug> | null",
  "ground_truth_at": "<ISO 8601 UTC>",
  "self_prosecution_at": "<ISO 8601 UTC>",
  "invocation_number": 1,
  "last_vision_sha256": "<hex>",
  "shape_gate": "passed | findings_filed",
  "map_entries": [
    {
      "slug": "<spec-slug>",
      "name_settled": true,
      "owns_digest": "<one line>",
      "split_lines": [{ "neighbor": "<slug>", "predicate": "<verbatim>" }],
      "depends_on": ["<slug>"],
      "covers": ["<vision section / term>"],
      "spec_shipped": false,
      "map_conformance": "conformant | divergent | not_applicable"
    }
  ],
  "unowned": [{ "unit": "<verbatim>", "reason": "<one line>" }],
  "coverage": {
    "units_enumerated": 0,
    "units_claimed": 0,
    "units_unowned": 0
  },
  "seam_decisions_consulted": [{ "entry": "<heading>", "log": "specs/decisions.md", "status": "bound" }],
  "seam_arbitration": "ran | skipped_all_seams_bound",
  "last_reconciled_specs": { "<slug>": { "sha256": "<hex>", "reconciled_at": "<ISO 8601 UTC>" } },
  "plan_lint_log": { "exit_code": 0, "stdout": "<verbatim>" },
  "claims_total": 0,
  "claims_verified": 0,
  "claims_verified_softened": 0,
  "claims_corrected": 0,
  "claims_dropped": 0,
  "claims_restructured": 0,
  "claims_skipped_carveout": 0,
  "ground_truth_log": [],
  "self_prosecution_findings": [],
  "imagined_spec_author_report": {
    "spec_attempted": "<slug>",
    "verdict": "authorable | not_authorable",
    "gaps": [{ "question": "<verbatim>", "answered_where": "<downstream section>", "severity_test": "<falsifiable scenario>" }]
  },
  "authoring_residual": [],
  "prior_blockers": [
    {
      "blocker_class": "<class>",
      "path_or_section": "<verbatim>",
      "summary": "<verbatim>",
      "raised_in_round": 1,
      "current_reclassification_justification": "<optional>"
    }
  ],
  "recently_resolved_blockers": [
    {
      "blocker_class_when_resolved": "<class>",
      "path_or_section": "<verbatim>",
      "summary": "<verbatim>",
      "resolved_in_round": 1,
      "user_decision": "<verbatim>",
      "carry_forward_until_round": 3
    }
  ],
  "verdict": "CLOSED | APPROVED | NEEDS_USER_INPUT | DRAFT_EMITTED"
}
```

`DRAFT_EMITTED` is written when the user invokes with `--draft`. `/vision-review` treats it as "intentionally unhardened" and warns rather than re-prosecutes.

If `last_vision_sha256` matches the sha of `vision.md` on disk, vision is unchanged since the last invocation; the **Vision moved** trigger does not fire. If it differs, it does, and the delta names which sections moved.

Also read the reviewer's state at `~/.claude/cache/review-state/<project>__vision.json` — its `recently_resolved_blockers` may include boundary calls the director already arbitrated. Re-proposing a seam the director already bound is the worst thrash form at this layer, and it is what teaches a director to stop reading the question.

---

## Source ingest

Read in this order. Read once into context; do not re-read in later stages.

1. `~/.claude/skills/_vision-common/vision-format.md` — the format being applied.
2. `~/.claude/skills/_decompose-common/decomposition-principles.md` — the machinery, read through its Vision-layer column.
3. **`vision.md` in full.** Not the map alone. The cut list orders what a spec may assume survives; the decision ledger says what is already closed; the mechanism sections are the units the coverage audit enumerates.
4. `CLAUDE.md` (project root, and any nested) — conventions, bound invariants, and **the vocabulary table**. Every bound term needs exactly one owning spec.
5. `MEMORY.md` + every memory file under `~/.claude/projects/<project>/memory/` whose `description` hints at relevance.
6. **`specs/README.md`** — the roster, in the shape `_vision-common/vision-format.md` § The roster fixes: state, on-loan surface, hoist lists, dated parked items, pending upstream amendments. This is where state lives; nothing read here is copied into the map.
7. **Every shipped `specs/<slug>/spec.md`** and its **`specs/<slug>/decisions.md`**. The specs are what map-to-shipped-spec conformance is checked against; the logs carry Active `Status: bound` entries that are constraints.
8. **`specs/decisions.md`** — the boundary-arbitration log. Every Active `Status: bound` entry is a seam the director already decided.
9. `personas/README.md` — which domain perspective owns which question, for persona resolution at Self-prosecution.

**Never `handoffs/`.** It holds untracked, point-in-time working files that are not current truth. A parked item that originated in a handoff is already distilled into the roster and is read from there.

After reading, build the **invariants ledger** — the facts vision must honor, drawn from `CLAUDE.md` + project memory — and the **bound-seam ledger** — every Active `Status: bound` entry across `specs/decisions.md` and each `specs/<slug>/decisions.md`. The first is the prosecution target for the product persona; the second is the set of boundaries that are never re-litigated.

**There is no upstream document above vision.** Its grounding is internal (cross-section consistency), the invariant ledger, and — uniquely at this layer — the shipped specs below it, which are concrete files a map entry can be falsified against.

---

## Seam survey

Enumerate candidate owners from **three sources**, each of which is simultaneously a coverage obligation. Run the enumeration before naming anything: a seam discovered by naming two plausible specs and looking for a line between them is a line drawn to fit the names.

- **Vision's own sections.** The mechanism sections are the candidate clusters; the coverage obligation is wider than they are, and **every** section — overview, non-goals, delivery, north-star, and the rest — must end the run claimed by exactly one entry or named in the unowned block.
- **The vocabulary table.** Every bound term needs exactly one owning spec — its definition site. A term no spec owns is a coverage gap; a term two specs define is a boundary defect.
- **The decision ledger and the cut list.** Each open ledger item is assigned to the spec that will close it, or marked director-only. Each cut-list item names the spec that would lose content if that cut lands, so nothing above a cut line becomes a spec's load-bearing premise.

### The seam test

One question, applied to every candidate boundary:

> **If you changed a rule on one side, would you have to edit the other side's spec?**

Yes means one spec. No means a seam. Nothing else decides it — not how big the resulting specs are, not how naturally the names read, not which surface was written first.

Every seam the test finds needs a split-line predicate before it can be written down. The bar, the predicate's shape, and the three failure modes are in `decomposition-principles.md` § Split-line predicates. A seam that survives the test but carries no applicable predicate files `SEAM_PREDICATE_MISSING`.

### Structural surface check

The vision layer's oversize signal is structural, not numeric. An entry is oversized when it carries material on loan for **more than one** unwritten spec.

That files `DECOMPOSITION_SURFACE_EXCESS` as a director decision — split the entry, or accept the size in a bound row naming the accepted structural condition. Never apply a split unilaterally. Inventing a numeric threshold with no evidence behind it is not available here.

A seam needing two predicates against the same neighbor is not a size signal: two predicates are two seams, so the entry they split is two specs. That files `SEAM_PREDICATE_MISSING`, and `/plan-lint` hard-fails it before this check runs.

---

## Seam alignment

Follow `~/.claude/skills/_decompose-common/decomposition-principles.md` § Director arbitration exactly. The shape it prescribes — one-line question phrased as a choice, two or three named directions each stating its split-line predicate, the pick leading with what the call commits to, clustered calls, `Status: bound` records in `specs/decisions.md` — is not restated here.

Three things the hosting layer fixes:

- **The log is `specs/decisions.md`**, in the same entry format the per-spec logs use.
- **Arbitration runs only when a seam is unbound.** Where Active `Status: bound` entries already cover every seam the survey found, skip the call and record `seam_arbitration: "skipped_all_seams_bound"` with the entries consulted. Re-asking a bound seam every run is how a director learns to skip the question.
- **A proposed boundary that contradicts a bound entry is surfaced as a question, never offered as a direction.** Superseding a bound seam call is the log's two-step edit, done together.

**The director decides** whether a spec exists at all, its name, where a split line falls when two placements are both defensible, and the authoring order when the graph allows more than one next. **This skill decides** coverage bookkeeping, parked-item filing, pointer maintenance, and ordering the dependency graph already forces.

---

## Draft

Write the map to the entry shape in `_vision-common/vision-format.md` § The spec map. The load-bearing drafting rules at this stage:

- **Map before you cut.** Enumerate the units, apply the chosen seam's predicate, assign, *then* write the entries. Enumerating after cutting hides an unclaimed unit behind the seam that hardened around it.
- **The map is vision's last section.** Append. Inserting it mid-document renumbers every section below and orphans every existing `vision §N` reference across the specs, the decision logs, and `CLAUDE.md`.
- **No status in the map.** Ownership, seams, dependency edges, and coverage only. Everything that flips the day a spec ships belongs in `specs/README.md`. A surface another spec owns renders as owned by that spec's entry, never as parked, deferred, or on loan.
- **No historical commentary.** A rescoped entry reads as though it always had that scope. `specs/decisions.md` is the arbitration record and carries the carve-out.
- **Names are the director's.** An owed spec whose name is unsettled says so in its heading and carries candidates marked as illustrative. This skill coins no spec name, no domain term, and no split-line term.
- **The section re-derives every run.** It is never carried forward byte-identical, because an edit above it can change what a unit is. A re-derivation that moves a boundary an Active bound entry fixes is `FIX_INTRODUCED_PREMISE_INVERSION` unless the director re-cut at arbitration.

With a `<spec-slug>` argument, the run deepens that one entry — **Owns** goes from a paragraph to something a spec author can start from, **Split line** gains a predicate against every neighbor, **Depends on** names what it reads from each, **Covers** enumerates its definition sites. Sibling entries change only where the deepening moved a shared seam, and a moved shared seam is a director call.

---

## Shape gate

Deterministic, runs against the in-memory draft before any agent is spawned, and hard-blocking in `ship` mode. It is the same structural check `/vision-review` runs at its Stage 0, applied here so a malformed draft never reaches a gate that costs subagents — the spec, brief, and engineering-plan authors gate on their own in-memory drafts the same way.

Apply `_vision-common/vision-format.md`: required core sections present and in order, the spec map present and **last**, each entry carrying its four fields in order with a backticked concern-named slug, the unowned block present, frontmatter shape, banned-pattern absence, implementation-creep absence. The `## Pending blockers` block is legal only immediately before the map and only while `Status: needs-user-input` is set.

A failure emits the partial draft with `Status: needs-user-input` and `VISION_SHAPE_FAILED` in `## Pending blockers`, naming each defect. In `--draft` mode the gate reports its findings in the verdict and does not block.

---

## Plan-lint gate

Deterministic, HARD-blocking, runs after the Shape gate and before the Ground-truth audit — exactly as the engineering-plan author gates on it.

The lint dispatches on document type by path shape, so the draft is materialized under a basename the vision type matches:

```bash
mkdir -p /tmp/<project>-vision-<timestamp>
# write the in-memory draft to /tmp/<project>-vision-<timestamp>/vision.md
python3 ~/.claude/skills/plan-lint/lint.py --strict /tmp/<project>-vision-<timestamp>/vision.md
```

Capture stdout and exit code into `sidecar.plan_lint_log`. Exit codes: `0` = clean, `1` = FAIL, `2` = usage/IO error.

- **Exit 0** → continue to Ground-truth audit.
- **Exit 1** → read the failure list. Apply local fixes to the in-memory draft (rewrite an entry, write a missing predicate, move a status token to the roster) and re-run, up to 2x. Fixes that would move a boundary are not local — refuse and surface `STRUCTURAL_LINT_FAILED`.
- **Exit 2** → re-check the temp path and content; if it persists, `STRUCTURAL_LINT_FAILED` with the lint stderr verbatim.

Delete the temp directory regardless of outcome. A draft that fails lint never reaches the Ground-truth audit.

**`--strict` is what makes a map-less draft block.** Without it the lint reports a map-less vision as a WARN and exits 0, which is the right answer for a reporting run and the wrong one for a gate whose whole job is emitting a map. `--strict` exits 1 on WARN, so a `ship`-mode run that produced no map stops here. In `--draft` mode the gate runs **without** `--strict` and reports: a draft may legitimately be a map in progress.

---

## Ground-truth audit

Apply `_author-common/ground-truth-protocol.md` with the emphasis in `_vision-common/vision-format.md` § Ground-truth claim emphasis. **V4 dominates in three forms:**

- **Internal cross-section consistency** — a map entry's **Covers** claim against what the cited vision section actually says; a **Depends on** edge against the mechanism sections both sides rest on; a cut-list dependency against the cut list's actual order.
- **Invariant-ledger conformance** — every vision rule that restates or depends on a `CLAUDE.md` / project-memory invariant. Verify vision does not contradict the bound invariant.
- **Map-to-shipped-spec conformance** — for every `<slug>` whose `specs/<slug>/spec.md` exists: the surfaces that spec defines match what its entry claims it **Owns**, and it defines nothing a neighbor's entry claims. A map entry is a claim about a real file, so a divergence is falsifiable rather than a matter of judgment. Each divergence files `MAP_CONFORMANCE_GAP` with both sides quoted and three resolution paths named: rewrite the entry to match the spec, move the surface into the spec the map assigns it to, or re-cut the boundary. Which path is right is a director call.

V3 (constraint/data) covers figures vision marks as constraints. V1 (path:line) and V2 (identifier) are rare; if the draft cites them, vision has drifted into spec territory — file as a drift finding, not a verified anchor.

Emit the sidecar audit log even when the draft is rejected at Self-prosecution.

---

## Self-prosecution and imagined-spec-author

### Persona prosecution

Spawn persona agents in parallel using the template in `_author-common/self-prosecution-protocol.md`. **Personas resolve from the project's own `personas/` directory** (`git rev-parse --show-toplevel`), never the skill directory — read `personas/README.md` at Source ingest to resolve names. A project with no `personas/` cannot be self-prosecuted; stop and report.

- **product** — coherence of the decomposition against the product it decomposes, scope, contradictions with the bound-invariant ledger.
- **architecture** — internal consistency, dependency-graph soundness, whether the set of specs is a buildable whole rather than a partition that reads well.
- **the project's domain-ownership persona** — the perspective whose domain decides where a mechanism belongs (`game-design.md` in a game project). Boundary questions at this layer are design-ownership questions, so this seat is filled wherever the project has one to fill.

Active critical pairs: universal pairs from `_review-common/critical-pairs.md` only (`P-CLASS-SCOPE`, `P-FULL-FILE`). The vision-specific `P-VISION-*` pairs are a review-stage filter, defined in `/vision-review`.

### Imagined-spec-author dry run (after personas return)

The load-bearing gate between APPROVED and CLOSED, ported directly from the engineering-plan layer's Imagined-Implementer. Follow `_decompose-common/decomposition-principles.md` § The imagined-downstream-author dry run, with the vision layer's substitutions: downstream author `/spec-author`, unit a *spec*, class `SPEC_BOUNDARY_UNBOUND`.

1. **Pick the next owed spec** — the first entry with no unmet dependency. Where several qualify, take the one `specs/README.md` marks next; otherwise the first in map order. With a `<spec-slug>` argument, pick that slug.
2. **Attempt to author it as a thought experiment, without writing it**, from its **map entry plus its roster entry and nothing else**, following what `/spec-author` would do: read the entry's Owns, its split lines, its Depends on, its Covers, and the Active `Status: bound` entries in `specs/decisions.md`.
3. **File every question the entries leave unanswerable** against that slug, each with the question, where in the spec it would have to be answered, and a `severity_test` — a falsifiable scenario in which leaving it open stops the spec author.
4. **No gaps** → `imagined_spec_author_report.verdict: "authorable"`. Otherwise `not_authorable`.

**The entries are the whole input.** Reaching past them — into vision's other sections, into a sibling's entry, into this run's own memory of the seam survey — makes the dry run pass on knowledge the spec author will not have. Every reach is the finding.

---

## Coverage audit

Its own stage, run in every mode, immediately before emission. Enumerate the units **from `vision.md`, never from the map**: **every** section, every bound vocabulary term, every decision-ledger item, every cut-list item. Overview and framing sections are units on the same terms as mechanism sections. Each resolves to exactly one owning entry or to an explicit unowned line. Disposition is two-state and admits no third; a unit with neither files `VISION_COVERAGE_GAP`.

Record `coverage: { units_enumerated, units_claimed, units_unowned }`. `units_claimed + units_unowned == units_enumerated` is the invariant the two-state rule states arithmetically, and it is what `/vision-review` recomputes; a run where the sum falls short has gaps it has not filed.

A term two entries claim as a definition site is a boundary defect, not a coverage gap — it files `SPEC_BOUNDARY_UNBOUND`.

In `--draft` mode the audit still runs and its gaps are reported in the verdict rather than blocking — `DRAFT_EMITTED` is the verdict either way, and a draft map whose coverage was never enumerated is the one thing a draft is least useful without.

---

## Emission

### Verdict template

The output **leads with the map diff**, because the director is the reader. Counts and audit detail go to the sidecar, not the screen.

```markdown
# Vision authoring verdict — vision.md (<project>)

**Trigger:** seed | vision moved | spec landed | review parked  (all that fired)
**Scope:** map | map + <sections touched> | whole document
**Mode:** cold | warm   **Authoring mode:** ship | draft
**Round:** <invocation_number>
**Last vision sha:** <hex>

## Map diff

**Specs added:** <slug> — <one clause>; ... | none
**Specs renamed:** <old> → <new> (bound by <decisions.md entry>) | none
**Specs rescoped:** <slug> — <what moved in or out, one clause> | none
**Split lines moved:** <slug> ↔ <slug> — <the new predicate, verbatim> | none
**Parked items filed:** <item> → <roster destination> | none
**Parked items discharged:** <item> — substance verified in `<slug>` | none
**Unowned block:** <N added>, <N discharged> | unchanged
**Next spec:** `<slug>` — <one line on what it is scoped to cover> | blocked by <slug>'s open call

## Verdict

**CLOSED** | **APPROVED** | **NEEDS_USER_INPUT** | **DRAFT_EMITTED**

### Blockers (if NEEDS_USER_INPUT)
- [VISION_SHAPE_FAILED] <defect> — <one-line>; <resolution path>.
- [VISION_COVERAGE_GAP] <unit> — <one-line>; <resolution path>.
- [MAP_CONFORMANCE_GAP] <slug> — <one-line>; <resolution path>.
- [SEAM_PREDICATE_MISSING] <seam> — <one-line>; <resolution path>.
- [DECOMPOSITION_STATUS_LEAK] <span> — <one-line>; <resolution path>.
- [DECOMPOSITION_SURFACE_EXCESS] <slug> — <one-line>; <resolution path>.
- [HOIST_INCOMPLETE] <parked item> — <one-line>; <resolution path>.
- [VISION_AMENDMENT_NEEDED] <section> — <one-line>; <resolution path>.
- [STABLE_DISAGREEMENT] <span> — <one-line>.
- [OPEN_QUESTION] <span> — <one-line>.
- [FIX_INTRODUCED_PREMISE_INVERSION] <span> — <one-line>.
- [STRUCTURAL_LINT_FAILED] <lint defect> — <one-line>.

### Boundary calls outstanding (if APPROVED)
- [SPEC_BOUNDARY_UNBOUND] `<slug>`: <question> — <severity_test>; bound at Seam alignment.

### Authoring residuals (LOW, under polish floor)
- ...
```

The `### Blockers` block is the parse target for `/explain-blockers`; keep the `- [CLASS] <span> — <summary>` line shape exactly.

### Verdict gates

- **CLOSED** ⇔ ALL of:
  - Authoring mode is `ship` (not `--draft`).
  - Shape gate PASS; Plan-lint (`--strict`) PASS.
  - Coverage complete — every enumerated unit claimed or explicitly unowned.
  - Every seam carries an applicable split-line predicate.
  - The next spec is named and scoped.
  - `imagined_spec_author_report.verdict == authorable`.
  - Tier-1 weight = 0; Tier-2 weight ≤ 4 (polish floor).
  - No `VISION_SHAPE_FAILED`, `VISION_COVERAGE_GAP`, `MAP_CONFORMANCE_GAP`, `SEAM_PREDICATE_MISSING`, `DECOMPOSITION_STATUS_LEAK`, `DECOMPOSITION_SURFACE_EXCESS`, `HOIST_INCOMPLETE`, `VISION_AMENDMENT_NEEDED`, `SPEC_BOUNDARY_UNBOUND`, `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `FIX_INTRODUCED_PREMISE_INVERSION`, `STRUCTURAL_LINT_FAILED`, `REPO_STATE_DRIFT`.

  `/spec-author <slug>` is unblocked for every spec in the map.

- **APPROVED** ⇔ shape-correct on every CLOSED condition above except that `imagined_spec_author_report.verdict == not_authorable` and one or more `SPEC_BOUNDARY_UNBOUND` calls remain. The map is correct as far as it goes; **authoring stays blocked for every spec a pending call touches**, and the rest of the roster stays authorable. The director binds the calls at Seam alignment and the session agent rewrites the affected entries — the author is not re-invoked.

- **NEEDS_USER_INPUT** ⇔ authoring mode is `ship` AND any blocker class above (other than `SPEC_BOUNDARY_UNBOUND`) fires.

- **DRAFT_EMITTED** ⇔ authoring mode is `--draft`. Ground-truth audit and Self-prosecution skipped, Shape gate and Plan-lint reporting only; no spec is unblocked, since the gate that unblocks one did not run.

### Disk-write semantics

- **CLOSED / APPROVED** → write `vision.md` with NO `Status:` frontmatter; persist the sidecar; print the verdict. If the on-disk file still carries `Status: needs-user-input` and a `## Pending blockers` section, this emission removes both. **Next step:** run `/vision-review`.
- **NEEDS_USER_INPUT** → write `vision.md` with frontmatter `Status: needs-user-input` AND an inline `## Pending blockers` section listing each unresolved finding verbatim; persist the sidecar. The session agent then applies the resolutions directly and removes the `Status:` line and the section — the author is not re-invoked. `SPEC_BOUNDARY_UNBOUND` findings, which gate CLOSED but not APPROVED, do **not** appear in `## Pending blockers`; they live in the verdict's boundary-calls block and are bound in `specs/decisions.md` where they belong.
- **DRAFT_EMITTED** → write `vision.md` with NO `Status:` frontmatter; persist the sidecar with `authoring_mode: "draft"`; note in the verdict that the map is unhardened by choice, listing any Shape-gate, lint, or coverage findings the reporting passes produced.

### Pending-blockers section (NEEDS_USER_INPUT mode)

**Placement is fixed: immediately before the spec map.** The map stays vision's last section in every state of the document, so no `vision §N` anchor moves while blockers are open, and the block is tolerated by `/vision-review`'s Stage 0 and by `/plan-lint` only while `Status: needs-user-input` is set. Clearing the flag and removing the block happen together.

```markdown
## Pending blockers

<!-- This section is auto-managed by /vision-author. Resolve each blocker below; the session agent
then applies your resolutions directly to this file and removes this section along with the
`Status: needs-user-input` line — the author skill is not re-run. -->

- [<BLOCKER_CLASS>] <span / section> — <one-line summary>; <actionable resolution path>.
- ...
```

While any blocker remains unresolved, the section keeps only the still-open blockers (replaced, not appended) and the `Status:` line stays.

---

## Hard rules

- **The compatibility gate runs first.** No `vision.md` at the repo root → decline in one line and stop. Never ask; detect by file presence.
- **Stage order is fixed.** State load → Source ingest → Seam survey → Seam alignment → Draft → Shape gate → Plan-lint → Ground-truth audit → Self-prosecution and imagined-spec-author → Coverage audit → emission. `--draft` skips exactly two stages — Ground-truth audit and Self-prosecution — and downgrades the Shape gate and Plan-lint to reporting runs. Every other stage runs in every mode.
- **Scope is section-bounded unless the ask says otherwise.** The map is owned unconditionally; every other section is touched only where a trigger reached it, and only in the implicated passage. A whole-document re-author happens on an explicit plain-language clean-slate ask, never as a side effect of clearing a map defect.
- **`handoffs/` is never read.** Not as a source, not as a citation, not to resolve a parked item.
- **The Shape gate and Plan-lint are HARD-blocking in `ship` mode.** Shape failures emit the partial draft with `VISION_SHAPE_FAILED`; lint failures are fixed in-loop or surfaced as `STRUCTURAL_LINT_FAILED`. A draft with structural defects never reaches the Ground-truth audit, and `--strict` is what makes a map-less `ship` run stop rather than warn.
- **The imagined-spec-author dry run is mandatory in `ship` mode.** It is the load-bearing gate between APPROVED and CLOSED.
- **No status in the map.** Enforced by lint, backstopped by `DECOMPOSITION_STATUS_LEAK`. Everything that churns lives in `specs/README.md`.
- **The map appends as vision's last section.** Never inserted mid-document.
- **Cross-file scope.** This skill edits `vision.md` and appends bound entries to `specs/decisions.md`. It never edits a `specs/<slug>/spec.md`, `CLAUDE.md`, or project memory — those escalate as director calls (`VISION_AMENDMENT_NEEDED` or `OPEN_QUESTION`). `specs/README.md` is the roster this skill maintains: parked items are filed and discharged there, never in the map.
- **Bound decisions are never re-litigated.** Every Active `Status: bound` entry across `specs/decisions.md` and each `specs/<slug>/decisions.md` is a constraint. A proposed boundary contradicting one is surfaced as a question, never offered as a direction.
- **Parked items move at authoring, never before.** A parked item is dropped only in the reconcile pass following its owner's authoring, and only after its substance is verified present in the authored spec. Dropping it early is `HOIST_INCOMPLETE`.
- **Vocabulary is real.** No spec name, domain term, or split-line term is coined here. An unsettled name says so and carries illustrative candidates; the spec's folder does not exist until authoring.
- **The cut list binds.** No entry's Owns rests on material the cut list ranks above the line that entry needs.
- **Sidecar is always written.** Every invocation, every verdict. The one exception is the compatibility gate's decline: no `vision.md` means there is no artifact to key a sidecar to, so the run stops before State load and writes nothing.
- **Source ingest before the seam survey.** A map drafted without reading vision in full, the roster, the shipped specs, and the bound-seam ledger is fan fiction. Source ingest is hard-blocking.

---

## Edge cases

**No `vision.md` at the repo root:** the compatibility gate declines in one line. Not an error, and no sidecar is written.

**`vision.md` present, no map section (seed):** the Seed trigger. Survey vision whole, propose the full set, and expect Seam alignment to run — a seed run with no director call almost always means the survey named specs after existing sections rather than finding seams.

**Sidecar absent, map present (hand-written map, or a wiped cache):** warm mode against the on-disk map. Its current content is a carry-forward constraint. No blocker history; the map itself is the constraint.

**Sidecar present, vision sha matches, no trigger fires:** no-op when the request adds no new constraint or instruction. Print "no changes; the map is in the last CLOSED state" and exit. A plain-language ask to re-cut or deepen an entry IS a new instruction and proceeds in warm mode.

**Sidecar present, vision sha differs:** the director's manual edit takes precedence. Reset `ground_truth_log`; re-run from Source ingest. Carry-forward of `recently_resolved_blockers` still applies.

**A spec landed and its ownership matches its entry:** the map is byte-stable. Record the reconcile in `last_reconciled_specs`, report "map unchanged; `<slug>` conforms" in the diff block, and do not manufacture an edit.

**A spec landed and its ownership diverged:** `MAP_CONFORMANCE_GAP`. Which side is wrong — the entry or the spec — is a director call, so the run surfaces the divergence with both sides quoted rather than choosing.

**A parked item was discharged but its substance is absent from the authored spec:** `HOIST_INCOMPLETE`. Restore the roster entry until the substance lands.

**A seam the survey finds contradicts an Active bound entry:** surface as a question with the bound entry quoted. Never offer it as a direction, and never silently supersede.

**`specs/README.md` absent:** create it from the shape in `_vision-common/vision-format.md` § The roster, populated from this run — one row per map entry, and `None.` under every section this run has nothing for. Until it exists the run has degraded coverage: parked items and the next-spec marker have nowhere to live, so `Next spec` falls back to map order. Say in the verdict that the roster was created.

**`specs/decisions.md` absent:** no vision-layer bound entries exist yet, so every seam the survey finds is unbound and Seam alignment runs on all of them. The log is created by the first pick that binds one, in the entry format the per-spec logs use; a run that binds nothing leaves it uncreated rather than writing an empty file.

**`specs/` absent entirely:** the Seed trigger with no shipped specs. Map-to-shipped-spec conformance records `specs_shipped: 0` and is skipped; the imagined-spec-author dry run still runs against the first entry.

**`CLAUDE.md` absent:** degraded ground-truth coverage; print a warning. Where the vocabulary table lived in `CLAUDE.md`, the vocabulary coverage obligation cannot be enumerated — say so in the verdict rather than reporting coverage complete.

**`personas/` absent:** stop and report. Self-prosecution cannot run, and a map that skipped it is not a map anyone should author against.

**`--draft` mode:** Ground-truth audit and Self-prosecution skipped; the Shape gate and Plan-lint (without `--strict`) report without blocking; the Coverage audit runs and reports. Sidecar marked `authoring_mode: "draft"` and `verdict: "DRAFT_EMITTED"`. Vision IS written to disk with NO `Status:` frontmatter. No spec is unblocked.

---

## Relationship to sister skills

- **`/vision-review`** prosecutes the map written here and consults this skill's sidecar to skip re-prosecuting author-arbitrated claims. It is the immediate next step after a CLOSED or APPROVED draft.
- **`/spec-author`** consumes the map downstream: its Source ingest reads `vision.md` and the entry for the spec under work, and its map conformance holds the spec to what its entry says it owns. **A CLOSED verdict here is what unblocks `/spec-author <slug>`;** APPROVED unblocks only the specs no pending boundary call touches.
- **`/spec-review`** re-tests every split line each time a spec is authored against it, on a concrete rule rather than in the abstract. That downstream re-test is the map's strongest backstop, the same way the chunk-plan layer is what finally proves an engineering plan's DAG.
- **`/explain-blockers`** triages this skill's `### Blockers` block and the boundary calls an APPROVED verdict leaves outstanding.

Vision is the root artifact; this skill exists to make its decomposition the part of it nothing downstream has to guess at.
