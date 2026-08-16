# Product-spec format — the canonical cross-project shape

The global format for a project's product spec (`spec.md`), shared by `/spec-author` (writes to it) and `/spec-review` (prosecutes against it). Project-agnostic: the *shape* and the *drafting rules* are universal; the *content* is per-project.

The spec is the **root source-of-truth** of the artifact lifecycle. Every downstream artifact descends from it:

```
spec.md  →  features/<f>/brief.md  →  engineering-plan.md  →  implementation/<chunk>.md  →  code
```

A brief traces its Goals to the spec; an engineering plan chunks a brief; a chunk plan implements a chunk. The spec has **nothing above it in the artifact chain** — it is where product intent is canonical. That is exactly why it earns an author/review pair: a contradiction or hallucination in the spec cascades through *every* feature, not one, and the downstream review machinery repairs the descendants, never the spec itself.

## Authority — what binds the spec

The spec is the top of the *artifact* chain, but two project-level sources still bind it:

1. **`CLAUDE.md` and project memory** (`~/.claude/projects/<project>/memory/`) carry the project's bound invariants and conventions. The spec must honor them. When the spec deliberately *changes* a product rule that `CLAUDE.md` or memory also states, that is a real amendment that has to cascade to the invariant ledger — surfaced as an `OPEN_QUESTION`, never silently absorbed, because `/spec-author` and `/spec-review` do not auto-edit the bound-invariant ledger.
2. **Project design docs** (`docs/`, `context/`, architecture/decision records) are grounding material the spec must stay consistent with, where they exist.

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

## Glossary

- **<Term>** — <precise definition used consistently across the spec and downstream artifacts.>
- ...

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

### Which optional sections apply

| Section | Include when |
|---|---|
| Roadmap / milestones | the product commits to a staged/sequenced delivery |
| Analytics & observability | the product emits a defined event or operational-signal surface |
| External integrations | the product depends on third-party APIs/services |

A section that does not apply is **omitted**, not stubbed with "N/A".

## Drafting rules

- **Each invariant states a checkable condition.** "An order cannot ship until payment has settled" is verifiable; "checkout feels smooth" is not. An invariant's checkability is what lets a brief Goal trace to it and a reviewer prosecute against it.
- **Define a load-bearing term before using it.** A noun the spec leans on (a domain concept, a cohort, a state) is defined in Domain model or Glossary before it appears as a load-bearing term in Invariants / Feature areas. Undefined load-bearing terms force downstream authors to invent the definition.
- **WHAT, not HOW.** The spec names product-visible rules and the system's conceptual structure. It does NOT name file paths, schema columns, function signatures, framework choices, or chunk decomposition — those are engineering-plan and chunk-plan territory. The spec *does* carry precise product rules (e.g., a score formula, a threshold) when the rule is itself the product contract; precision about a *rule* is not implementation creep, but a path/identifier/SQL fragment is.
- **Sections must not contradict each other.** A rule in Invariants, a behavior in Feature areas, and a definition in Domain model must agree. Internal contradiction is the spec's highest-severity defect class, because every descendant inherits the contradiction.
- **Honor the invariant ledger.** A spec claim that contradicts a bound invariant in `CLAUDE.md` or project memory is a conflict to surface (amend the spec, or amend the ledger out-of-band) — never a silent override.
- **Name the domain when an invariant or feature area quantifies over one.** "every", "all", "across", "any surface", "going forward" must name the concrete domain ranged over (which surfaces, entity types, cohorts, call paths). An unnamed domain cannot be checked for coverage downstream.
- **Each Non-goal is a real scope kill.** Plausible-but-excluded, not a platitude ("we won't break things" is a platitude).
- **One voice, forward-looking.** Plan style rules apply (`_review-common/principles.md` § Plan style rules): no addendum sections, no review attribution, no historical comparison, no persona-attribution headers, no conflict-resolution metadata. The spec describes the current product, not how the spec was produced.

## Ground-truth claim emphasis (for `/spec-author` and `/spec-review` Stage 1)

The spec is the root, so its verifiable claims skew differently from a chunk plan's:

- **V4 (cross-document)** dominates in two forms: **internal cross-section consistency** (does §Invariants agree with §Feature areas and §Domain model?) and **invariant-ledger conformance** (does the spec honor `CLAUDE.md` + project memory?).
- **V5 (external-API)** for any capability claim about a third-party service — verified against the project's wrapper code where one exists, the provider's docs otherwise.
- **V3 (constraint/data reality)** for cohort counts and data-state claims ("~15,800 records", "N existing X") — verified against the most recent migration / seed / query the project supports.
- **V1 (path:line) and V2 (identifier)** are **rare** at the spec layer. If the draft cites them, the spec has drifted into engineering-plan territory — file as a drift finding, not a verified anchor.

## Personas

- **`/spec-author`** self-prosecution: **product** (coherence, scope, contradiction with the invariant ledger) + **architecture** (internal consistency, domain-model soundness, buildability of the committed system).
- **`/spec-review`** default tribunal: **product + architecture + ai-development** (the plan-quality lens — invariant verifiability, banned content, drift into implementation detail).

Persona files are **project-scoped**: both skills resolve `personas/<name>.md` from the **root of the project the spec belongs to** (`git rev-parse --show-toplevel`), never the skill directory — so prosecution is always grounded in the reviewed project's own domain personas (an orchestration tool's personas prosecute orchestration concerns, not a consumer app's). A project authoring/reviewing its own spec must carry its own `personas/`; a project with no `personas/` directory cannot be self-prosecuted or reviewed until it has one.

## Sidecar keying

The spec is **project-level**, not feature-level. Author and review sidecars key on the project, not a feature:

- author: `~/.claude/cache/author-state/<project>__spec.json`
- review: `~/.claude/cache/review-state/<project>__spec.json`

`<project>` is the basename of the repository root (`git rev-parse --show-toplevel`), or the basename of the current working directory when not in a git repo — e.g. `your-project`, `internal-toolkit`.
