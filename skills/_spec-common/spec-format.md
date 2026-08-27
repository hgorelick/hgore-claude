# Product-spec format — the canonical cross-project shape

The global format for a project's product spec (`spec.md`), shared by `/spec-author` (writes to it) and `/spec-review` (prosecutes against it). Project-agnostic: the *shape* and the *drafting rules* are universal; the *content* is per-project.

The spec is the **source-of-truth of its own system**. Every downstream artifact descends from it:

```
[vision.md § spec map]  →  spec.md  →  features/<f>/brief.md  →  engineering-plan.md  →  implementation/<chunk>.md  →  code
```

A brief traces its Goals to the spec; an engineering plan chunks a brief; a chunk plan implements a chunk. That is why the spec earns an author/review pair: a contradiction or hallucination in it cascades through *every* feature, not one, and the downstream review machinery repairs the descendants, never the spec itself.

**Two layouts, detected by file presence and never by asking:**

| Present | Spec | Decisions log |
|---|---|---|
| `specs/<slug>/spec.md` | that file | `specs/<slug>/decisions.md`, plus `specs/decisions.md` scanned alongside |
| root `spec.md` only | that file | root `decisions.md`, created if absent |

A project with a single root `spec.md`, no `vision.md`, and no `specs/` tree is fully supported and takes the identical path. Where `vision.md` carries a spec map, this spec's boundary is bound input and is never re-cut below.

## Authority — what binds the spec

Project-level sources bind the spec:

1. **`CLAUDE.md` and project memory** (`~/.claude/projects/<project>/memory/`) carry the project's bound invariants and conventions. The spec must honor them. When the spec deliberately *changes* a product rule that `CLAUDE.md` or memory also states, that is a real amendment that has to cascade to the invariant ledger — surfaced as an `OPEN_QUESTION`, never silently absorbed, because `/spec-author` and `/spec-review` do not auto-edit the bound-invariant ledger.
2. **`vision.md`, where it exists.** Its spec map assigns this spec a surface: what it owns, the split-line predicate against each neighbor, its dependencies, and the vision sections it is the definition site for. The map entry is binding, not advisory — the spec covers what its entry owns and defines nothing a neighbor owns. A spec that needs a rule vision does not carry, or contradicts one it does, is *amending vision*, and the amendment lands in the contradicted vision section explicitly — escalated as a director call, since neither spec skill edits `vision.md`.
3. **Project design docs** (`docs/`, `context/`, architecture/decision records) are grounding material the spec must stay consistent with, where they exist.

Where there is no `vision.md`, the spec is the root of the artifact chain and nothing above it constrains it.

Below the spec, the brief inherits and never overrides. The spec is where a product rule is *decided*; the brief is where a feature *commits to delivering against* it.

## Section template

A lean universal core (always present) plus optional sections (present when the project type calls for them). Mirror this ordering. Do not invent a new spec shape.

```markdown
# <Product> — Product Spec

<!-- Status frontmatter is OPTIONAL and binary. Set to `needs-user-input` ONLY when the
     spec is mid-cycle (auto-managed by /spec-author's NEEDS_USER_INPUT path). Otherwise omit. -->
<!-- Status: needs-user-input -->  <!-- only when mid-cycle -->

**Created:** <YYYY-MM-DD>
**Last updated:** <YYYY-MM-DD>

## Overview

<One or more paragraphs. The answer to "what is this product, who is it for, and what
problem does it solve?" State the core value at the product level — not architecture.>

## Domain model & core concepts

<The nouns of the system and how they relate — the vocabulary every downstream artifact
must use. Each load-bearing term is defined here (or in the Glossary) before it is used as
a load-bearing noun elsewhere in the spec.>

## Invariants & business rules

- **<Rule name>.** <A checkable condition the system MUST enforce, stated as an observable
  rule, not an aspiration. This is what briefs trace Goals to and what code must honor.>
- ...

## Feature areas

- **<Area name>.** <What this capability does, at the product level — the "what", not the
  "how". Briefs are authored against these areas. A feature area is a product capability,
  not an implementation module or a single feature/brief.>
- ...

## Non-goals & scope bounds

- **<Non-goal>.** <What the product deliberately does NOT do, at the product level. A real
  scope kill the product could plausibly have included, not a platitude.>
- ...

## Decomposition

### Seams

- **<seam name>** — <the split-line predicate: one sentence that decides, for any rule not
  yet written, which side of the seam it lands on.>
- ...

### Briefs

| Slug | Scope | Intent | Depends on |
|---|---|---|---|
| `<concern-named-slug>` | <one line> | Foundation \| Content \| Instrument \| Conformance | `<slug>`, `<slug>` \| — |

### Scope stubs

**`<slug>`**

- *Outcomes owed* — <what this brief must deliver, one line each. The Goal source.>
- *Exclusions inherited* — <the Non-goals and seam exclusions this brief carries, by reference.>
- *Spec units claimed* — <the invariants, feature areas, and terms this brief owns.>

### Coverage

| Spec unit | Brief | Proof |
|---|---|---|
| <unit, verbatim> | `<slug>` \| `excluded by <seam name>` \| `structural — no brief could trespass it` | `<slug>` \| `Director review — <reason>` \| — |

## Glossary

- **<Term>** — <precise definition used consistently across the spec and downstream artifacts.>
- ...

## Open questions                   <!-- optional -->

<Unresolved product questions, one per bullet, each in question form. Include when the spec
carries a rule that waits on a decision nobody has made yet; omit the section otherwise.>

## Roadmap / milestones            <!-- optional -->

<Named delivery milestones (never numbered-as-labels), in sequence. Include when the product
has a staged delivery the spec should commit to.>

## Analytics & observability        <!-- optional -->

<The events or operational signals the product emits. For a user-facing app: analytics events
(project convention governs casing/tense). For an infra/tooling product: the operational
signals it surfaces. Include when the product emits a defined signal surface.>

## External integrations            <!-- optional -->

<Third-party APIs / services the product depends on and the contract surface relied upon.
Include when the product integrates external services.>
```

Feature areas may render as the template's bullets or as `###` subsections — an area carrying
structured content (a table, several paragraphs) earns a subsection; both shapes are canonical.

### Which optional sections apply

| Section | Include when |
|---|---|
| Open questions | a spec rule waits on a product decision nobody has made yet |
| Roadmap / milestones | the product commits to a staged/sequenced delivery |
| Analytics & observability | the product emits a defined event or operational-signal surface |
| External integrations | the product depends on third-party APIs/services |

A section that does not apply is **omitted**, not stubbed with "N/A".

### The Decomposition section

**Required of every spec**, with all four subsections in the order above. It sits after Non-goals so a stub can name its inherited exclusions by reference, and before the Glossary. It is the spec's decomposition into briefs — the same way an engineering plan's required shape includes its chunk DAG — so `/brief-author` reads a slice already cut rather than re-deriving one. The machinery is shared with the vision layer and defined once in `~/.claude/skills/_decompose-common/decomposition-principles.md`; what follows is the shape, not a second copy of the rules.

**Seams.** Each named, each carrying its split-line predicate — one sentence that decides, for any rule the spec does not contain, which side it lands on. A seam without one is a boundary nobody can apply to the next unit. Where `vision.md` exists, a seam against a neighboring spec restates that neighbor's split line from the map rather than inventing a second one.

**Briefs.** One row each: slug, one-line scope, intent, dependencies. Slugs are concern-named kebab-case; the position-encoded shapes `/plan-lint` already rejects (`phase-N`, `step-N`, `NN-`) are forbidden here too, and there are no wave numbers — parallelism is read off the edges. `Depends on` means this brief's scope reads a rule the named brief binds; the graph must be acyclic and every slug it references must appear in the table.

| Intent | Means | Obligation |
|---|---|---|
| Foundation | binds vocabulary or structure other briefs consume | one nothing depends on is dead weight; fold it into its consumer |
| Content | produces the authored surface — cards, cells, catalogs, rosters | — |
| Instrument | its deliverable is a measurement | names what the measurement decides |
| Conformance | proves invariants that range across briefs | the sink: depends on every delivering brief, and is one concern however many invariants it covers |

A **conformance brief** is required whenever an invariant's falsifier ranges over more than one brief. It is the acceptance-chunk analog one layer up.

**Scope stubs.** One block per brief, three fields: outcomes owed (the Goal source), exclusions inherited (each naming its source — a Non-goal or a seam — from which `/brief-author` derives the scope bucket), spec units claimed. A one-line stub sends `/brief-author` back to re-derive the slice, which is the step this section exists to remove. A brief waiting on an unanswered question names that question in its stub; the question itself lives in `## Open questions`.

**A brief's slug is its feature directory name.** The slug in the Briefs table, the block heading in Scope stubs, and the directory holding the brief are one string: `features/<slug>/brief.md`. That is the lookup every downstream skill uses in both directions — a stub is found from a feature directory, and a feature directory from a table row. A Briefs-table row naming no feature directory, or a feature directory named by no row, is the mismatch to flag.

**Coverage.** Every spec unit maps to the brief claiming it or the seam excluding it. Units are enumerated mechanically, never chosen: every invariant under Invariants & business rules, every Feature area, every Non-goal, and every Domain-model or Glossary term owing authored content. Disposition is two-state — claimed by a slug, or excluded — and admits no third; a unit with neither is a blocker, never a row the spec carries.

`excluded by <seam name>` is the ordinary rendering of exclusion, and two named forms carry it where a column takes a different shape: a Non-goal no brief could reach reads `structural — no brief could trespass it` in its Brief cell, and a check no authored artifact could carry reads `Director review — <reason>` in its Proof cell. Both are exclusion written in that column's terms; neither is a third state, because the rule that admits no third is claimed-versus-excluded.

**Proof** names the brief owning that invariant's falsifier, one at a time rather than pooled into a sink. An invariant whose falsifier ranges over more than one brief is **claimed by the conformance brief** in the Brief column — the sink owns the check no single delivering brief can hold — and its Proof cell may name that brief too.

**The section carries no state.** Which briefs exist as folders, which are in flight, which shipped, which surface awaits a spec nobody has written — all of it lives in `features/README.md`. The section says which side of a boundary a unit sits on; the sidecar says where that unit is in the pipeline. So "parked", "on loan", "shipped", "next", and dates never appear here. A unit another domain owns renders as excluded by a named seam with its predicate, which is true whether or not that domain's spec has been written.

## Drafting rules

- **Each invariant states a checkable condition.** "Scores are locked until the user has 5 rankings in a category" is verifiable; "the scoring feels fair" is not. An invariant's checkability is what lets a brief Goal trace to it and a reviewer prosecute against it.
- **Define a load-bearing term before using it.** A noun the spec leans on (a domain concept, a cohort, a state) is defined in Domain model or Glossary before it appears as a load-bearing term in Invariants / Feature areas. Undefined load-bearing terms force downstream authors to invent the definition.
- **WHAT, not HOW.** The spec names product-visible rules and the system's conceptual structure. It does NOT name file paths, schema columns, function signatures, framework choices, or chunk decomposition — those are engineering-plan and chunk-plan territory. The spec *does* carry precise product rules (e.g., a score formula, a threshold) when the rule is itself the product contract; precision about a *rule* is not implementation creep, but a path/identifier/SQL fragment is.
- **Sections must not contradict each other.** A rule in Invariants, a behavior in Feature areas, and a definition in Domain model must agree. Internal contradiction is the spec's highest-severity defect class, because every descendant inherits the contradiction.
- **Honor the invariant ledger.** A spec claim that contradicts a bound invariant in `CLAUDE.md` or project memory is a conflict to surface (amend the spec, or amend the ledger out-of-band) — never a silent override.
- **Name the domain when an invariant or feature area quantifies over one.** "every", "all", "across", "any surface", "going forward" must name the concrete domain ranged over (which surfaces, media types, cohorts, call paths). An unnamed domain cannot be checked for coverage downstream.
- **Each Non-goal is a real scope kill.** Plausible-but-excluded, not a platitude ("we won't break things" is a platitude).
- **Map before you cut.** Draft `## Decomposition` last, after the sections it enumerates exist, and inside it enumerate the units, then apply the seam's predicate, then assign, then write the stubs. Enumerating after cutting hides an unclaimed unit behind the seam that hardened around it.
- **The decomposition re-derives every run.** It is never carried forward byte-identical: an edit above it can change what a unit is. A re-derivation that moves a boundary an Active `Status: bound` entry fixes is `FIX_INTRODUCED_PREMISE_INVERSION` unless the director re-cuts.
- **A brief contradicting the spec is amending it.** The amendment lands in the contradicted spec section explicitly, in the same authoring run, and the decomposition re-derives against it. A stub that does what a Non-goal excludes is `SPEC_NONGOAL_TRESPASS`, not a stub to leave standing.
- **One voice, forward-looking.** Plan style rules apply (`_review-common/principles.md` § Plan style rules): no addendum sections, no review attribution, no historical comparison, no persona-attribution headers, no conflict-resolution metadata. The spec describes the current product, not how the spec was produced.

## Ground-truth claim emphasis (for `/spec-author` and `/spec-review` Stage 1)

The spec sits at or near the root of the artifact chain — the root where there is no `vision.md`, one layer under the spec map where there is — so its verifiable claims skew differently from a chunk plan's:

- **V4 (cross-document)** dominates in four forms: **internal cross-section consistency** (does §Invariants agree with §Feature areas and §Domain model?), **invariant-ledger conformance** (does the spec honor `CLAUDE.md` + project memory?), **coverage-table citations** (does each unit in §Decomposition's Coverage table quote a unit the spec actually carries, and does each claiming slug appear in the Briefs table?), and **seam-decision citations** (does each seam match the Active `Status: bound` entry that fixed it?). Where `vision.md` exists, **map conformance** joins them: the spec covers what its map entry owns, defines nothing a neighbor's entry owns, and honors each split-line predicate — save a neighbor-owned surface the state sidecar (`specs/README.md` § On loan) records as held by this spec until the owner is authored, which passes on that evidence; an unrecorded one is the gap.
- **V5 (external-API)** for any capability claim about a third-party service — verified against the project's wrapper code where one exists, the provider's docs otherwise.
- **V3 (constraint/data reality)** for cohort counts and data-state claims ("~15,800 books", "N existing X") — verified against the most recent migration / seed / query the project supports.
- **V1 (path:line) and V2 (identifier)** are **rare** at the spec layer. If the draft cites them, the spec has drifted into engineering-plan territory — file as a drift finding, not a verified anchor.

## Personas

- **`/spec-author`** self-prosecution: **product** (coherence, scope, contradiction with the invariant ledger) + **architecture** (internal consistency, domain-model soundness, buildability of the committed system).
- **`/spec-review`** default tribunal: **product + architecture + ai-development** (the plan-quality lens — invariant verifiability, banned content, drift into implementation detail).

Persona files are **project-scoped**: both skills resolve `personas/<name>.md` from the **root of the project the spec belongs to** (`git rev-parse --show-toplevel`), never the skill directory — so prosecution is always grounded in the reviewed project's own domain personas (an orchestration tool's personas prosecute orchestration concerns, not a consumer app's). A project authoring/reviewing its own spec must carry its own `personas/`; a project with no `personas/` directory cannot be self-prosecuted or reviewed until it has one.

## Sidecar keying

The spec is **project-level**, not feature-level, so author and review sidecars key on the project rather than a feature. Which key depends on the layout, by the same file-presence gate:

| `vision.md` at the repo root | Author sidecar | Review state |
|---|---|---|
| present | `~/.claude/cache/author-state/<project>__<spec-slug>__spec.json` | `~/.claude/cache/review-state/<project>__<spec-slug>__spec.json` |
| absent | `~/.claude/cache/author-state/<project>__spec.json` | `~/.claude/cache/review-state/<project>__spec.json` |

`<project>` is the basename of the repository root (`git rev-parse --show-toplevel`), or the basename of the current working directory when not in a git repo — e.g. `my-app`, `docs-site`. `<spec-slug>` is the `specs/<slug>/` directory name of the spec under work. A project carrying per-system specs has several of them at once, and the unslugged key collides the moment the second spec lands.
