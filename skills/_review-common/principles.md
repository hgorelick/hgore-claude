# Review tribunal — shared principles

Loaded by `/review-pr-v2`, `/plan-review-v2`, `/engineering-plan-review-v2`. The hosting skill defines workflow; this file defines stance.

## Stance

**REPO REALITY IS LAW.** Every finding, fix, and fact MUST be grounded in files that exist *right now, on this branch*. If a persona cannot produce `path:line` + a verbatim quote, the finding does not exist. Stage 1 grounds objective claims; later stages are forbidden from re-prosecuting Stage-1-verified facts AND from filing new findings without producing the same kind of evidence.

**Cite or drop it.** Every finding states `path:line` and quotes the authority it violates (spec, persona rule, project invariant, existing test). Verbatim quote, not summary. Vibes-based findings AND vibes-based acquittals are inadmissible.

**Class > line.** A finding names a *line*; a defect lives in a *class*. When filing a finding, identify the class and enumerate the universe (every place the class could live). The fix application then resolves every instance in that universe, not just the named line.

**Fix-list, don't annotate.** Persona agents return fix lists; they do not edit files or run gates. The orchestrator applies all fixes once, runs gates after, commits.

**Prosecute, don't collaborate.** A persona's job is to find the reason this PR/plan will *fail*, not to polish prose. Construct scenarios where executing the artifact verbatim produces a broken result.

## Banned rationalizations

Any finding (or acquittal) using one of these is automatically discounted:

- "minor", "nit only", "not worth fixing", "good enough", "acceptable residual"
- "it was already broken", "pre-existing", "not introduced by this PR" (defects in files the PR touches are owned by the PR)
- "out of scope" (for defects *in the diff* or *in the plan body*)
- "we can fix it later", "tracked elsewhere", "follow-up"
- "the tests pass so it's fine"
- "I searched for the literal pattern" (without generalizing to case variants, plurals, alternate forms)
- "probably exists", "should exist", "standard convention", "common pattern"
- "author will figure it out", "trusted author"

For engineering plans specifically:
- "every chunk roughly maps to a goal" — every chunk maps **explicitly** in Brief Mapping, or it doesn't map.
- "the brief implies this" — the brief states; it doesn't imply.
- "we'll figure out the dependency at implementation time" — declared dependencies are part of the plan's contract.
- "rollback is obvious" — rollback path is named and verified or it doesn't exist.

LOW severity may include genuine polish ("nit", "minor") when the finding is real but cosmetic. LOW findings are subject to the polish floor in the verdict — they do not block APPROVED if total Tier-2 weight is below floor.

## Severity and tier classification

**Tier:**
- HARD: hallucinations not caught by Stage 1, gate-breaking defects, security holes, invariant violations, missing tests for behavior changes, scope violations, structural defects, false parallelism, missing rollback, cross-chunk-wiring deferrals.
- SOFT: judgment findings (drift, factoring, perf concerns, vagueness, persona-specific quality).

**Severity:**
- CRITICAL: PR will fail in production / corrupt state / security hole; plan will fail mid-execution or leave half-shipped feature.
- HIGH: significant correctness/quality/rollout-safety risk.
- MEDIUM: real gap that weakens the artifact.
- LOW: polish; "nit" / "minor" allowed for genuinely cosmetic.

Tier-1 weights: CRITICAL=8, HIGH=4, MEDIUM=2, LOW=1.
Polish floor: Tier-2 weight ≤ 4 to avoid `POLISH_PLATEAU`.

## Plan style rules (forward-looking, not archaeological)

A plan is a contract for an implementer with no context about how it was produced. It MUST NOT contain:

- **Addendum sections.** Findings integrate into the section they correct.
- **Review attribution.** No "Architecture review found…", "round-3 tribunal flagged…".
- **Cross-references between fix locations.** No "see addendum E", "binding per round-N finding".
- **Conflict-resolution metadata.** Pre-resolve and state the resolved instruction.
- **Historical comparisons.** No "the original plan said X but actually Y".
- **"Decisions resolved" sections.** Decisions live in `features/<feature>/decisions.md` (engineering plans) or bake into instructions (chunk plans).
- **Persona-attribution headers.** The plan is one document with one voice.

Plans MAY contain forward-looking "Why" rationale for non-obvious choices and a short "Verified facts" section capturing observable repo facts.

The smell test: pretend you've never seen the plan and have 10 minutes to start work. Can you act on every section without reconstructing how the plan got into its current state?
