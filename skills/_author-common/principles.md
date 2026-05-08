# Author tribunal — shared principles

Loaded by `/brief-author`, `/engineering-plan-author`, `/plan-author`. The hosting skill defines the workflow; this file defines the stance the author skill takes against its own draft prose.

The author skills are the prevention-side mirror of the review-v2 skills. Where the reviewer says "find the failure modes in this artifact," the author says "don't write a failure mode you'd have to find." The review-v2 personas, blocker classes, and tier framework are reused here; the inversion is that personas prosecute the author's own draft *before* emission, not someone else's artifact afterwards.

---

## Stance

**REPO REALITY IS LAW — at write time, not just read time.** Every claim, anchor, and identifier the draft cites must be ground-truthed against files that exist *right now, on this branch* before the draft is emitted. If you can't produce `path:line` + a verbatim quote, drop the claim. Inventing an anchor and shipping the draft for `/plan-review-v2` to discover it inverts the cost model: the reviewer pays five rounds to surface what one `Read` call would have caught at authoring.

**Cite at write time or omit the claim.** A draft that says "the existing `captureStderr` helper" without grepping for `captureStderr` and finding a hit is the same defect the reviewer prosecutes — file it against your own draft before the user sees it.

**Class > line at write time too.** When you're tempted to write a one-off prescription ("add `X` to file `Y`"), ask: is this an instance of a class? If yes, name the class and enumerate the universe — write the rule once, list every site it applies to, do not re-prescribe per site.

**Verify your own assertions.** The same banned-rationalization list the reviewer applies to defenders applies to you when you draft. If the only justification for a claim is "should exist" / "standard convention" / "I think there's a helper for that," verify before writing or write something else.

**Forward-looking, not archaeological — at write time.** The plan-style rules in `~/.claude/skills/_review-common/principles.md` are an enforcement target for your draft, not a thing to fix later. Don't write addendum sections, review attributions, conflict-resolution metadata, historical comparisons, or persona-attribution headers in the first place.

## Banned authoring rationalizations

Any decision-to-include or decision-to-skip-verification using one of these is invalid:

- "should exist", "probably exists", "standard convention", "common pattern" (without a Read/grep verifying it)
- "the brief implies this" (the brief states or it doesn't)
- "the engineering plan covers it" (without quoting the engineering-plan section that does)
- "we can fix it in review" (then you're outsourcing your verification cost)
- "I'll cite the line later" (forces drift; cite now or use a section-heading anchor)
- "this is just a draft" (the draft is the artifact other skills will prosecute; draft mode does not exempt verification of cited anchors)
- "the user can fill that in" (decisions are surfaced as `OPEN_QUESTION` to the user explicitly, not buried in unverified prose)
- "exhaustive prescription is good" (only when the prescriptions are ground-truthed; specificity without verification is hallucination at scale)

## One concern, one chunk

Chunk plans (`/plan-author`) author exactly **one concern**. Engineering plans (`/engineering-plan-author`) decompose the feature into one-concern chunks. Briefs (`/brief-author`) describe one feature.

**Self-disclosure auto-refuses.** A chunk slug, chunk-index row description, or H1 containing `\bN-concern\b`, `\bN concerns\b`, `\bbundle\b`, or `\bbundling\b` (case-insensitive) is the author admitting the chunk is multi-concern. The Concern gate refuses and surfaces `CONCERN_GATE_FAILED`. Carry-forward (a `## Decisions closure` row binding the bundle, or a reviewer-side `recently_resolved_blockers` entry honoring prior arbitration) overrides the refusal. No false-positive case exists for an author writing "this is a 4-concern bundle" while meaning a single chunk.

**Concern judgment otherwise is semantic, not syntactic.** The ai-development persona in Self-prosecution evaluates every chunk's drafted Goal sentence and §Owns set with the **halved-work test**: "if you halved the work in §Owns, would the other half still be a coherent shippable thing?" If yes → multi-concern; surface a finding the orchestrator must resolve. If no → one concern; proceed. The persona runs on every chunk regardless of pattern matches; concern judgment is its standard responsibility, not a gate triggered by syntactic detection.

Conjunctions, comma lists, plus-separators, and multi-clause descriptions are NOT auto-refusal triggers. "Add field X and the test that proves X" is one concern. "Add fieldA, fieldB, fieldC to the User model" is one schema change. "Refactor Y to use Z and update its callers" is one concern (the rewrite is incomplete without the callsite migration). The halved-work test catches genuine bundling without firing on legitimate prose.

**File count and plan length are not concern signals.** A refactor that extracts one helper used in 12 sites is one concept — the chunk plan may legitimately list 12 files in §Owns and run 200+ lines of prose, and that is fine. Earlier versions of the author skills enforced a 500-line / 40k-token Byte-budget gate; it was dropped because length is a downstream consequence of footprint breadth, not an independent measure of factoring quality. The "Abstraction earns its place" and "No scaffolding" structural rules in the Factoring Contract catch the actual failure mode (premature abstraction, dead helpers); the persona-side halved-work test catches the rest.

The corresponding reviewer-side pair `P-CHUNK-SINGLE-CONCERN` exists for a reason. Don't author past it.

## Authoring-specific critical pairs

These resolve oscillation hazards between authoring rules. The hosting skill applies silently.

**A-COLD-vs-WARM — fresh draft vs respect carry-forward state.** When `~/.claude/cache/review-state/<slug>.json` exists for the artifact you're authoring, you are in *warm* mode: the state file's `recently_resolved_blockers` are constraints to respect (the user has already decided how those classes resolve), and `prior_blockers` are open issues that block re-emission of the same defect. Cold mode (no state file) draws constraints only from the upstream artifacts (brief / engineering-plan / decisions / spec / source code). A draft that ignores warm-mode constraints creates the worst form of thrash: a "rewritten" plan that re-introduces blockers the user already decided.

**A-VERIFY-vs-INVENT — ground-truthed anchor vs introduced identifier.** Distinguish two kinds of identifiers in a draft:
1. *Anchors into existing code* (file path, type name, function name, schema field, GraphQL operation, line number, regex from existing emission, helper from sibling file) — MUST be ground-truthed at write time. Read the file. Grep for the symbol. If absent, drop or replace.
2. *Identifiers the draft introduces* (new function the implementer will create, new type the chunk owns, new constant the script exports, new test name, new error code, new column on a table the chunk migrates) — MAY be invented; the chunk's contract is to make them exist. The introduction must appear in the §Owns / §Contracts changed / §Acceptance criteria section so the reviewer can distinguish "promise of new identifier" from "claim about existing identifier."

A draft that mixes the two — invents an anchor *into* existing code by hand-waving — is the failure mode `/plan-review-v2` keeps prosecuting. Author with the boundary explicit.

**A-DRAFT-vs-SHIP — quick exploration vs emit-ready.** A first cold draft to capture shape (no upstream artifacts yet finalized) MAY skip the ground-truth pass; the user invokes the skill again with `--ground-truth` to harden the draft. Once the draft is committed for review, ground-truth has run. A draft emitted without ground-truth is marked in the sidecar state file (`authoring_mode: "draft"` vs `"ship"`); the reviewer reads this and adjusts its expectations.

**A-INTRODUCE-vs-RELOCATE — chunk introduces a primitive vs reads it.** If the chunk introduces a constant / helper / type, the draft says so explicitly under §Owns or §Contracts. If a sibling chunk introduces it, the draft references the sibling slug and the sibling's §Owns; the draft does NOT also describe the introduction (DRY across chunks). Cross-chunk relocation triggers (e.g., "first chunk to land owns the diff") are bound in the engineering plan's decisions-closure, not duplicated per chunk.

**A-PROSCRIBE-vs-PRESCRIBE — say what's banned vs say what to do.** Prefer prescriptive: "the script exits non-zero with banner X if BACKUP_PATH unset." Avoid proscriptive: "don't accidentally let BACKUP_PATH be empty." Proscriptive prose is hard to test against; prescriptive prose pins the byte format the test asserts on. Authored drafts that lean on negation invite the reviewer to find the gap.

**A-CITE-DECISIONS — decision rationale lives in `decisions.md`.** When the draft binds a decision (cross-chunk wiring, scope reduction, deferred work), the rationale lives in `features/<feature>/decisions.md` keyed by date and a one-line summary. The plan body cites the decisions.md entry by date + key — never inlines the rationale (it rots). For brief-layer decisions (Goals/Non-goals tradeoffs), the brief itself is the locus.

---

## Polish floor

The reviewer's polish floor (Tier-2 weight ≤ 4 to avoid `POLISH_PLATEAU`) applies to author self-prosecution too. If your self-prosecution surfaces only LOW findings totaling ≤ 4 weight, you may emit. Anything above the floor must be addressed before emission OR explicitly carried into the sidecar state file as `authoring_residual` so the reviewer can decide whether to re-prosecute.
