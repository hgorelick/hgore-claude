# Vision format — the canonical cross-project shape

The global format for a project's product vision (`vision.md`), shared by `/vision-author` (writes to it) and `/vision-review` (prosecutes against it). Project-agnostic: the *shape* and the *drafting rules* are universal; the *content* is per-project.

Vision is the **root source-of-truth** in a project that decomposes into per-system specs. Every downstream artifact descends from it:

```
vision.md § The spec map  →  specs/<slug>/spec.md  →  features/<f>/brief.md  →  engineering-plan.md  →  implementation/<chunk>.md  →  code
```

A spec is the source of truth for one mechanism cluster vision states; a brief traces Goals to its spec; an engineering plan chunks a brief; a chunk plan implements a chunk. Vision has **nothing above it in the artifact chain** — it is where product intent is canonical, and where the boundaries between specs are decided. That is why it earns an author/review pair: a contradiction, a coverage gap, or a boundary nobody can apply cascades into *every* spec, not one, and the downstream review machinery repairs the descendants, never vision itself.

## Applicability

This format applies where `vision.md` exists at the repository root. Detected by file presence, never by asking. A project whose root artifact is a single `spec.md` has no vision layer: `~/.claude/skills/_spec-common/spec-format.md` is its root format and `/spec-author` + `/spec-review` its root pair.

## Authority — what binds vision

Vision is the top of the *artifact* chain, but three things still bind it:

1. **`CLAUDE.md` and project memory** (`~/.claude/projects/<project>/memory/`) carry the project's bound invariants, conventions, and — in most projects — the vocabulary table. Vision honors them. When vision deliberately *changes* a rule the ledger also states, that is a real amendment that has to cascade to the ledger, surfaced as an `OPEN_QUESTION` and never silently absorbed.
2. **The director.** Whether a spec exists, what it is named, where a split line falls when two placements are both defensible, and the authoring order when the graph allows more than one next are the director's calls, arbitrated per `~/.claude/skills/_decompose-common/decomposition-principles.md` § Director arbitration and recorded in `specs/decisions.md`.
3. **The shipped specs.** Downstream but concrete. A map entry is a claim about a real file, so a shipped `specs/<slug>/spec.md` falsifies an entry that misdescribes it.

Below vision, a spec inherits and never overrides. Vision is where a mechanism and a boundary are *decided*; a spec is where the mechanism is *specified in full*.

## Section template

A universal core, always present. Mirror this ordering. Do not invent a new vision shape.

Sections are **named**; where a vision numbers them, the number is a stable citation anchor (`vision §14`) rather than the section's identity. Every reference elsewhere in the repo cites that anchor, which is why the spec map appends as the last numbered section and never inserts mid-document.

```markdown
# <Product> — Product Vision

<!-- Status frontmatter is OPTIONAL and binary. Set to `needs-user-input` ONLY when the
     document is mid-cycle (auto-managed by /vision-author's NEEDS_USER_INPUT path). Otherwise omit. -->
<!-- Status: needs-user-input -->  <!-- only when mid-cycle -->

**Status:** <one line — where the product sits: pre-production vision, in production, …>
**Direction:** <one line — who directs the work and how it is executed>

## Document conventions

<How this document's own names and numbers bind: whether names are provisional, what marks a
figure as a hard constraint versus a target, and any notation the mechanism sections rely on.
The spec map's vocabulary claims are only enforceable because this section says names are real.>

## <N>. Overview

<What this product is, who it is for, and the experience it commits to. Product level, not
architecture.>

## <N>. Non-goals

- **<Non-goal>.** <A real scope kill the product could plausibly have included, not a platitude.>
- ...

## <N>. <Mechanism section>            <!-- one or more; the substance of the document -->

<A cluster of product mechanisms stated at vision level: what the system does and why, the rules
that are already decided, and the figures that are targets versus constraints. Each mechanism
section is a candidate spec-map entry, and the map must dispose of every one.>

## <N>. <Delivery / production section>

### Cut list

<Ordered. What goes first when scope has to shrink, most-expendable first. The order is the
content — a cut list whose items are unranked cannot tell a spec what it may assume survives.>

## <N>. <Decision ledger>

<Every open product decision, and every closed one whose outcome downstream artifacts lean on.
A closed entry states the outcome only. The reasoning that produced it lives here; the fact that
an earlier answer differed does not.>

## <N>. North-star test

<The single question that decides whether the product is working. One paragraph, falsifiable,
phrased so a build can be held against it.>

## <N>. The spec map                   <!-- ALWAYS the last section -->

<Per § The spec map below.>
```

### Two `Status:` lines, told apart by shape

The document carries two things spelled `Status:`, and every scanner tells them apart **by shape**, never by value:

- **The product-stage line** — `**Status:** <one line>`, bolded, in the document body's frontmatter block, always present. It says where the product sits. No scanner reads it, and it never fires a mid-cycle check.
- **The mid-cycle flag** — `Status: needs-user-input`, bare and unbolded, inside the leading HTML comment. Present only while `/vision-author` has left unresolved blockers on disk, auto-managed, and removed on the next clean emission. This is the only form the mid-cycle check reads.

**Mid-cycle scaffolding has one legal placement.** While the flag is set, `/vision-author` writes a `## Pending blockers` section **immediately before the spec map**, so the map stays the last section and no `vision §N` anchor moves. That block is tolerated only while `Status: needs-user-input` is set; with the flag absent it is a shape defect like any other section after the map.

### Optional sections

| Section | Include when |
|---|---|
| Vocabulary table | the project does not keep its bound vocabulary in `CLAUDE.md` |
| Design pillars | the product's mechanism sections are arbitrated against a stated set of pillars |
| Framing / fiction | the product's premise is itself a designed surface downstream artifacts must honor |

A section that does not apply is **omitted**, not stubbed with "N/A". A vocabulary table living in `CLAUDE.md` is the normal shape and is not a defect; the spec map's **Covers** field names definition sites for those terms wherever the table lives.

## The spec map

The decomposition of vision into per-system specs is **required format of `vision.md`**, not the output of a separate skill — an engineering plan's required shape includes its chunk DAG, and vision's includes its spec map. The document that decides a seam is the document that carries it. The shared machinery — split-line predicates, the coverage-map contract, the truth-versus-state split, the imagined-downstream-author dry run, and the director-arbitration format — is defined once in `~/.claude/skills/_decompose-common/decomposition-principles.md`, read through that file's Vision-layer column. What follows is only the shape the map takes on the page.

### Placement

The map appends as vision's **last** section, always. Inserting it mid-document renumbers every section below it and orphans every existing `vision §N` reference across the specs, the decision logs, and `CLAUDE.md`.

### Entry shape

One entry per spec, headed by its slug, four fields in fixed order:

```markdown
### `<spec-slug>`

**Owns** — <One paragraph. The mechanism cluster this spec is the source of truth for — what a
reader would have to change this spec to change.>

**Split line**

- `<neighbor-slug>` — <one predicate sentence>
- `<neighbor-slug>` — <one predicate sentence>

**Depends on** — `<slug>` (<what this spec reads from it>); `<slug>` (<what it reads>). Where the
dependency runs both ways, the assumption this spec states instead of citing the other.

**Covers** — <The vision sections this spec is the definition site for, and the vocabulary terms
it defines.>
```

- **Field labels are bold and bare** — `**Owns** — …`, not `**Owns.**`. The label ends at the closing asterisks; the separator follows outside them.
- **Split line is one bullet per neighbor**, each leading with the neighbor's backticked slug. One bullet is what makes "exactly one predicate per neighbor" checkable in both directions.
- **Slugs are backticked wherever they are referenced** — in the entry heading, in each split-line bullet, and in **Depends on**. An entry with no dependencies writes `none`.
- **Slugs are concern-named kebab-case.** No `phase-N`, no `step-N`, no `NN-` prefix — numbering is never a naming scheme, and authoring order is read off the dependency edges.
- **A name that is unsettled says so** in the heading, after the settled part, with candidates marked as illustrative: ``### `terrain` — name unsettled; `ecology` is illustrative``. Names are minted only on an explicit director call, and the spec's folder does not exist until authoring. The marker is **format, not state** — it says what the entry's heading permanently is until a director mints the name, so it is carved out of the map's status-token scan and never files `DECOMPOSITION_STATUS_LEAK`.
- **Split lines are predicates, not lists.** One sentence that decides, for any rule not yet written, which side of the seam it lands on. A split line phrased as an enumeration of what is already assigned classifies nothing new and is a defect; a seam needing two predicates against the same neighbor is two seams, and the entry it splits is two specs. The bar and the failure shapes are in `decomposition-principles.md` § Split-line predicates.
- **Every neighbor named under Depends on carries a split line against it**, and every slug either field names has its own entry in the map. No entry depends on itself.
- **Cycles are legal.** Two specs that genuinely need each other are resolved by a stated assumption on the earlier-authored side, written into that side's **Depends on** field, never by deleting the edge.

### The unowned block

One map-level block, last, after every entry:

```markdown
### Unowned

- **<vision section, vocabulary term, ledger item, or cut-list item>** — <why no spec owns it:
  director-only, cross-cutting and stated here in full, or deliberately outside the decomposition.>
```

The block is never empty and never absent. Where every section, term, ledger item, and cut-list item is owned, it says so in one line — the articulated answer is the deliverable, and an empty block reads identically to an unexamined one.

Coverage disposition is two-state and admits no third: every unit is claimed by an entry or named here. Silence is never coverage. The enumeration runs from `vision.md` itself — **every** section, every bound vocabulary term, every decision-ledger item, every cut-list item — never from the map, so an omitted unit is falsifiable rather than invisible. Overview, framing, and delivery sections are units on the same terms as mechanism sections; a spec is rarely their definition site, so the block names them explicitly.

### Truth versus state

Per `decomposition-principles.md` § Truth versus state, one predicate decides what may enter the map at all:

> **Vision says what is permanently true about the decomposition. The roster says where the work stands right now.**

`vision.md` carries the set of specs, ownership, split lines, dependency edges, and coverage. Nothing in it changes when a spec ships. **`specs/README.md`** is vision's state sidecar and carries everything that churns: shipped / next / owed status, what a shipped spec holds **on loan** and for whom, the hoist list each owed spec pulls at its authoring pass, dated parked items with the pointer to where each binds today, and pending upstream amendments awaiting a director call. Its canonical shape is § The roster below.

The two read together cleanly. Vision states which spec owns a surface; the roster records who is holding that surface until the owner is authored. Vision is the end state; the roster is today's deviation from it.

Status tokens are therefore **banned inside the map section** — `shipped`, `owed`, `next`, `in flight`, `parked`, `on loan`, `TODO`, dates, counts of what exists yet, and any pointer to a folder's existence. A surface another spec owns renders as owned by that spec's entry, never as parked or deferred; that the owning spec has not been written is state.

## The roster — `specs/README.md`

Vision's state sidecar, and the only place decomposition state lives. `/vision-author` owns it: it is created on the first run that has state to record, and maintained on every run after. Five named sections, in this order; a section with nothing in it says `None.` rather than being dropped, because absent and empty read identically to the next run.

```markdown
# Specs

## Roster

| Spec | Status | Note |
|---|---|---|
| `<slug>` | shipped / next / owed | <one clause — what the status turns on> |

## On loan

- **<surface>** — held by `<holder-slug>`, owned by `<owner-slug>`; released when `<owner-slug>` is authored.

## Hoist lists

### `<owed-slug>`

- <material this spec pulls at its authoring pass, and where it sits until then>

## Parked

- **<YYYY-MM-DD> — <item>** — binds today at `<pointer>`; unparked when <condition>.

## Pending upstream amendments

- **<vision section>** — <the amendment awaiting a director call>, raised by `<slug>`.
```

- **The roster mints nothing.** Every row names a slug the map already carries; a row with no map entry is the defect, and the fix is upstream in the map.
- **Status is the roster's word, never the map's.** `shipped` means `specs/<slug>/spec.md` exists on disk; `next` is the director's authoring order; `owed` is everything else.
- **On-loan entries name both sides.** A surface with a holder and no owner is unassignable, which is a coverage gap in the map rather than a roster note.
- **Parked items are dated and pointed.** A parked item with no pointer to where it binds today cannot be discharged, and discharging one before its substance lands in the authored spec is `HOIST_INCOMPLETE`.

## Drafting rules

- **Vision states mechanisms; a spec specifies them.** Vision names what the system does, the rules already decided, and which figures are constraints. It does not carry the exhaustive tables, catalogs, and per-case rulings a spec exists to hold — that is the spec's job, and pulling it up flattens the seam the map just drew.
- **WHAT, not HOW.** No file paths, schema columns, function signatures, framework choices, or chunk decomposition. Precision about a *product rule* — a formula, a threshold, a numeric constraint — is vision's job, not implementation creep.
- **Mark constraints against targets.** A figure downstream work must not change reads differently from one it may tune. The document conventions section defines the notation; every mechanism section uses it.
- **The cut list is ordered.** A spec may assume everything below its own line survives and nothing above it. An unranked cut list gives a spec no such guarantee.
- **The decision ledger states outcomes.** A closed entry gives the current answer and its reasoning. It never narrates the answer it replaced.
- **Sections must not contradict each other.** A rule in one mechanism section, a figure in another, and an entry in the decision ledger must agree. Internal contradiction is vision's highest-severity defect, because every spec inherits it.
- **Honor the invariant ledger.** A vision claim contradicting a bound invariant in `CLAUDE.md` or project memory is a conflict to surface — amend vision, or amend the ledger out-of-band — never a silent override.
- **Name the domain when a claim quantifies over one.** "every", "all", "across", "any" must name the concrete domain ranged over. An unnamed domain cannot be checked for coverage by the map.
- **Vocabulary is real.** Vision uses only terms the vocabulary table binds. A new term — including a spec name — is a director call.
- **One voice, forward-looking.** Plan style rules apply (`~/.claude/skills/_review-common/principles.md` § Plan style rules): no addendum sections, no review attribution, no historical comparison, no persona-attribution headers, no conflict-resolution metadata. A rescoped spec entry reads as though it always had that scope; `specs/decisions.md` is the arbitration record and carries the carve-out.

## Ground-truth claim emphasis (for `/vision-author` and `/vision-review`)

Vision is the root, so its verifiable claims skew differently from a spec's:

- **V4 (cross-document)** dominates in three forms: **internal cross-section consistency** (does a mechanism section agree with the decision ledger and the cut list?), **invariant-ledger conformance** (does vision honor `CLAUDE.md` + project memory?), and — unique to this layer — **map-to-shipped-spec conformance** (does each entry describe what its shipped `specs/<slug>/spec.md` actually defines?). The third is falsifiable against a real file, which is what makes a map entry binding rather than advisory.
- **V3 (constraint/data reality)** for figures marked as constraints and for any count vision states.
- **V1 (path:line) and V2 (identifier)** are **rare**. If the draft cites them, vision has drifted into spec or engineering-plan territory — file as a drift finding, not a verified anchor.
- **V5 (external-API)** applies only where vision commits to a third-party capability; verified against the project's wrapper code where one exists, the provider's docs otherwise.

## Personas

- **`/vision-author`** self-prosecution: **product** (coherence, scope, contradiction with the invariant ledger) + **architecture** (internal consistency, whether the decomposition is buildable) + the project's **domain-ownership persona** — the one whose domain decides where a mechanism belongs (`game-design.md` in a game project). Boundary questions at this layer are design-ownership questions, so that seat is not optional where the project has one.
- **`/vision-review`** default tribunal: **product + architecture + ai-development** (the plan-quality lens — coverage falsifiability, banned content, drift into spec detail) + the domain-ownership persona where the project carries one.

Persona files are **project-scoped**: both skills resolve `personas/<name>.md` from the **root of the project vision belongs to** (`git rev-parse --show-toplevel`), never the skill directory. A project authoring or reviewing its own vision must carry its own `personas/`; a project with no `personas/` directory cannot be self-prosecuted or reviewed until it has one.

## Sidecar keying

Vision is **project-level**. Author and review sidecars key on the project:

- author: `~/.claude/cache/author-state/<project>__vision.json`
- review: `~/.claude/cache/review-state/<project>__vision.json`

`<project>` is the basename of the repository root (`git rev-parse --show-toplevel`), or the basename of the current working directory when not in a git repo.
