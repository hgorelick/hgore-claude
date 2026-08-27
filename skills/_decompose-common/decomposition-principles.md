# Decomposition — shared principles

Loaded by `/vision-author` and `/spec-author`, and prosecuted against by `/vision-review` and `/spec-review`. The hosting skill defines the pipeline and the document format; this file defines the machinery both decomposition layers run, stated once so the two layers cannot drift apart.

A decomposition is a **section of the document it decomposes**, never a separate artifact. An engineering plan's required shape includes its chunk DAG; a vision's includes its spec map; a spec's includes its brief decomposition. The document that decides a seam is the document that carries it.

## The two layers

| | Vision layer | Spec layer |
|---|---|---|
| Upstream document | `vision.md` | `specs/<slug>/spec.md`, or root `spec.md` |
| Decomposition section | the spec map | `## Decomposition` |
| Downstream unit | a spec | a brief |
| Downstream author | `/spec-author` | `/brief-author` |
| State sidecar | `specs/README.md` | `features/README.md` |
| Decisions log | `specs/decisions.md` | the spec's own log (root `decisions.md` where there is no `specs/` tree) |
| Coverage-gap class | `VISION_COVERAGE_GAP` | `DECOMPOSITION_COVERAGE_GAP` |
| Implementability-gap class | `SPEC_BOUNDARY_UNBOUND` | `IMPLEMENTABILITY_GAP` |

Every rule below is read through that table. Where a rule genuinely differs by layer, the layer is named in the rule.

---

## Split-line predicates

**One question finds a seam.** If you changed a rule on one side, would you have to edit the other side's unit? Yes means one unit. No means a seam. Run it before naming anything — a seam discovered by naming two plausible units and looking for a line between them is a line drawn to fit the names.

**A seam's split line is one predicate sentence that decides, for any rule not yet written, which side it lands on.** The predicate is the whole of the seam. A name without one is a label; a paragraph of context around one is padding.

**The bar is applicability, not elegance.** Hand the predicate a rule the document does not contain and it must return a side with no further argument. A predicate that needs the arbiter to recall which unit was authored first, or to weigh two goods, has not decided anything.

The predicate reads as a test over a property of the rule itself — *what a thing is* versus *when it is offered*, *how a state behaves* versus *what that state means to a typed thing*. Both halves are readable off the rule, which is what makes the next rule classifiable.

**Failure shapes.** Each is a defect, not a style note:

- **Examples instead of a test.** A split line that enumerates what is already assigned ("cells, durations, and spread rules go left") classifies nothing new. It is a coverage restatement wearing a predicate's clothes.
- **A predicate two seams both satisfy.** If two seams accept the same unit, neither decides it, and the coverage map's assignment is arbitrary. Re-cut so exactly one seam claims each unit, or merge the two.
- **A seam needing two predicates.** Two predicates means two seams, and the entry they split is two units. Splitting it is the fix; writing both predicates under one seam name is not.

**`SEAM_PREDICATE_MISSING`** fires when a seam carries no predicate, or carries one that does not decide the units the coverage map already assigns by it. Resolution: write the predicate as one sentence, split the seam where it needed two, or merge the seam away. It is distinct from the implementability classes — those fire when a *unit* cannot be authored; this fires when the *seam* cannot classify the next rule.

---

## The coverage map

Silent narrowing is the failure this exists to prevent, so coverage renders as a structure a reader can enumerate, never as prose.

**Units are enumerated mechanically, never hand-picked.** The enumeration reads the upstream document and returns its units; the author does not choose which to list. A hand-picked universe cannot show an omission, because the omission was never a row.

- **Spec layer** — every invariant under `## Invariants & business rules`, every `## Feature areas` entry, every `## Non-goals & scope bounds` entry, and every Domain-model or Glossary term owing authored content.
- **Vision layer** — **every** section of the document, every bound term in the vocabulary table, every decision-ledger item, and every cut-list item. Overview and framing sections are units like any other: where no spec is their definition site, the unowned block names them.

**Disposition is two-state.** Each unit is either **claimed** by a named downstream artifact, or **excluded** by a named seam. There is no third state. A unit with neither is a gap, and gaps are blockers rather than a list the document carries — the moment "unassigned" becomes a legal cell, the map stops being a proof.

**Two phrasings are named forms of exclusion, not a third state.** At the spec layer, a Non-goal row reading `structural — no brief could trespass it` and a proof cell reading `Director review — <reason>` both say *excluded*, and say which kind. The two-state rule is about claimed versus excluded; these decide nothing about whether a unit is disposed, only how.

**A director-deferred unit resolves by deferral, and still not by a third disposition.** At the spec layer, a unit the director defers is recorded in `features/README.md`'s Deferred spec surface list **and** in a `Status: bound` entry in the spec's decisions log naming its destination. A coverage-gap finding whose unit carries that matching pair is resolved by the deferral, so the reviewer verifies the pair exists rather than filing the gap; a deferral missing either half is the gap.

At the vision layer, material outside every seam lands in the map's **unowned block**, named explicitly, so silence is never mistaken for coverage. An exclusion is written as `excluded by <seam name>`, which stays true whether or not the unit that would own it has been authored.

**Proof ownership is per invariant** — spec layer. Every claimed invariant names the downstream artifact owning its falsifier. The upstream document already ships falsifiers as its violation clauses, so proof is assignable one at a time rather than pooled into a single sink. `Director review — <reason>` is legal only where no authored artifact could carry the check. A claimed invariant with no proof owner is a coverage gap, filed under the layer's coverage-gap class.

**Non-goals carry a disposition too** — spec layer: the downstream unit whose inherited exclusions carry it, or `structural — no brief could trespass it`.

**The rendering is per layer.** At the spec layer it is a three-column table — the unit, its disposition, the proof owner — reading `| Spec unit | Brief | Proof |`. At the vision layer it is each entry's **Covers** field plus the unowned block, with no proof-owner column: vision ships no violation clauses to assign falsifiers from, so the vision layer disposes units without owning proof.

**Map before you cut.** Enumerate the units, then apply the chosen seam's predicate, then assign, then write the stubs. Enumerating after cutting hides an unclaimed unit behind the seam that hardened around it.

**A quantifying invariant gets an adversary** — spec layer. One Scope-fidelity Adversary per claimed invariant that quantifies over a domain, spawned in isolation, one invariant each, off-model per `~/.claude/skills/_review-common/brief-conformance-prosecutor.md`. A brief claiming a domain-wide invariant while covering part of the domain files `SURFACE_PARITY_GAP` — the same class and the same adversary the engineering-plan layer uses, substituted one layer up.

**The section re-derives every run.** It is never carried forward byte-identical, because an edit above it can change what a unit is. A re-derivation that moves a boundary an Active `Status: bound` entry fixes is `FIX_INTRODUCED_PREMISE_INVERSION` unless the director re-cuts, which supersedes the old entry the log's usual two-step way.

---

## Truth versus state

One predicate decides what may enter the section at all:

> **The decomposition section says what is permanently true about the boundary. The state sidecar says where the work stands right now.**

**Nothing in the section changes when a downstream unit ships.** The set of units, their ownership, the split lines, the dependency edges, and the coverage disposition are all end-state facts. If a sentence would need editing the day a unit lands, it is state and belongs in the sidecar.

**The sidecar carries everything that churns:** which units exist as folders, which are in flight, which shipped, which surface is held on loan and for whom, the hoist list an owed unit pulls at its authoring pass, dated parked items with the pointer to where each binds today, and pending upstream amendments awaiting a director call. Vision's sidecar is `specs/README.md`; a spec's is `features/README.md`.

The two read together cleanly. The upstream document states which unit owns a surface. The sidecar records who is holding that surface until the owner is authored. The document is the end state; the sidecar is today's deviation from it.

**Banned in the section:** lifecycle words (shipped, next, in flight, parked, on loan, TODO), dates, counts of what exists yet, and any pointer to a folder's existence. `owed` joins that list at the **vision layer**, where it is roster vocabulary; at the spec layer the mandated stub field `*Outcomes owed*` carries the word, so the spec-layer token scan does not. `/plan-lint`'s status-token rule is the deterministic floor and implements exactly that split; `DECOMPOSITION_STATUS_LEAK` is the review-layer backstop for leaks the token scan misses.

**A unit another domain owns renders as excluded by a named seam**, with its predicate — never as parked or deferred. The exclusion is a permanent fact about the boundary. That the owning unit has not been written is state, and it lives in the sidecar.

**No historical commentary.** A rescoped unit reads as though it always had that scope. The rationale for the current cut stays; the fact that an earlier cut differed does not. The decisions log is the arbitration record and carries the carve-out.

---

## The imagined-downstream-author dry run

Runs inside **Self-prosecution**, after the personas return. It is the decomposition layers' Imagined-Implementer, and it is what separates a decomposition that is merely shape-correct from one a downstream author can start from.

1. **Pick the first downstream unit with no unmet dependency** — `Depends on` empty, or every dependency already bound. Where several qualify, take the one the state sidecar marks next, otherwise the first in document order.
2. **Attempt to author it as a thought experiment, without writing it**, from its decomposition entry plus its state-sidecar entry and nothing else. Follow what the downstream author would do: read the stub's outcomes owed, its inherited exclusions, its claimed units, and the Active `Status: bound` entries in the layer's decisions log.
3. **File every question the entries leave unanswerable** against that unit's slug, each with the question, where in the downstream artifact it would have to be answered, and a `severity_test` — a falsifiable scenario in which leaving it open stops the downstream author ("if the seam between X and Y is unstated, the brief's second Goal cannot name the domain it quantifies over").
4. **File under the layer's implementability-gap class.** Vision layer: `SPEC_BOUNDARY_UNBOUND`, downstream author `/spec-author`, unit a spec. Spec layer: `IMPLEMENTABILITY_GAP`, downstream author `/brief-author`, unit a brief.

**The entries are the whole input.** Reaching past them — into the upstream document's other sections, into a sibling's stub, into the reviewer's own memory of the design — makes the dry run pass on knowledge the downstream author will not have. Every reach is the finding.

**What the verdict does with it differs by layer, and this is a real difference:**

- **Vision layer.** No gaps and everything else clean is `CLOSED`, and `/spec-author <slug>` is unblocked. Gaps with everything else clean is `APPROVED`: the map is shape-correct, and authoring stays blocked for every spec a pending call touches.
- **Spec layer.** The verdict stays two-state. `IMPLEMENTABILITY_GAP` does not gate `APPROVED`; it blocks `/brief-author` for the slug it names, and the rest of the roster stays authorable. The gap is per-brief, so blocking one slug is more precise than a whole-spec third state.

---

## Director arbitration

Seam calls are the director's. They are presented in `/plan-alignment`'s shape, and nothing about the review machinery appears in them.

- **One-line question, phrased as a choice.**
- **Two or three named directions**, named for what they do (`pair-table-first`), never lettered or numbered — a named direction is referable in the log months later, a letter is not.
- **One short clause each**, and each direction states its **split-line predicate**. A direction whose predicate cannot be written is not a direction.
- **The pick, one sentence, leading with what the call commits to.** Not which is more flexible — what becomes expensive to reverse.
- **Cluster calls that share one answer** into a single `AskUserQuestion`. Never pad to three with strawmen; a single named direction with its reason stated is a valid shape.

**The director decides** whether a downstream unit exists at all, its name, where a split line falls when two placements are both defensible, and the authoring order when the graph allows more than one next. **The skills decide** coverage bookkeeping, parked-item filing, pointer maintenance, and ordering the graph already forces.

**Names are minted only on an explicit call.** A unit whose name is unsettled says so, carries candidates marked as illustrative, and its folder does not exist until authoring. Slugs are concern-named kebab-case; numbering is never a naming scheme, and order is read off the dependency edges.

**The pick lands as a `Status: bound` entry** under `## Active (bound)` in the layer's decisions log, in the log's entry format. The upstream document states only the outcome — rejected directions and arbitration reasoning cannot live in a truth doc, and the never-re-litigated machinery needs a `Status: bound` scan target.

**Bound is never re-litigated.** Every Active `Status: bound` entry in the layer's log is a constraint. A proposed boundary that contradicts one is surfaced as a question, never offered as a direction. Superseding a bound seam call is the log's two-step edit, done together.

**Arbitration runs only when a seam is unbound.** Bound entries covering every seam skip the call, and the skip is recorded. Re-asking a bound seam every run is how a director learns to skip the question.
