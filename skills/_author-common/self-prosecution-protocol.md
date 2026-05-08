# Self-prosecution protocol — personas attack your own draft

Loaded by `/brief-author`, `/engineering-plan-author`, `/plan-author`. The hosting skill calls this AFTER ground-truth has run and the draft is anchor-clean. Output is a draft with the same fix categories the reviewer would have produced — but applied at write time, not surfaced to the user as a NEEDS_USER_INPUT verdict.

The personas reused here are the same as the review-v2 personas (`personas/backend.md`, `personas/frontend.md`, `personas/architecture.md`, `personas/testing.md`, `personas/security.md`, `personas/product.md`, `personas/code-reviewer.md`, `personas/ai-development.md`). Same prosecution lens, different time horizon: instead of finding what's wrong with someone else's artifact, find what's wrong with what YOU just wrote.

---

## Persona selection per skill

| Skill | Personas |
|---|---|
| `/brief-author` | product, ai-development (chunk discipline, plan-quality lens applied to the brief layer) |
| `/engineering-plan-author` | architecture, ai-development, product, backend, testing |
| `/plan-author` | backend (or frontend, depending on chunk), architecture, testing, security, ai-development |

Hosting skill names which personas run. Author skills run fewer personas than reviewers — the goal is to catch the high-volume hallucination/factoring classes, not to replicate the full tribunal.

---

## Sub-passes

Each persona runs two sub-passes before returning. Sub-pass names are semantic — never letter-coded — so adding a future sub-pass doesn't induce ordering rot.

### Premise-interrogation sub-pass

The persona reads the draft and tests whether each load-bearing premise survives. Two types of premises trigger this:

1. **Claims about repo state** that ground-truth verified — re-read them through this persona's lens. Example: testing persona on a chunk plan reads "the existing `vi.spyOn` pattern in sibling test file `X`" and checks whether the *pattern* the chunk relies on actually appears in `X`, not just whether `vi.spyOn` is used somewhere in `X`.
2. **Claims about brief / engineering-plan** the draft cites — re-read them through this persona's lens. Example: backend persona on a chunk plan reads "engineering-plan §Zero-credit invariant defines the orphan filter" and checks whether the orphan filter the chunk's deletion script implements actually matches the §Zero-credit invariant's three-condition shape.

Output: list of premise-interrogation findings (or `passed: true` if none). Each finding cites the premise verbatim, the reality it diverges from verbatim, and the impact on the draft.

### Standard-prosecution sub-pass

Same prosecution the reviewer's persona agent runs (see `~/.claude/skills/_review-common/agent-prompt.md`). Class > line obligation applies: every finding names a class and enumerates the universe.

Output: fix list, same format as the reviewer's. No edits applied directly — the orchestrator (the author skill itself, in the main thread) applies fixes.

---

## Agent template

Used by the author skill to spawn each self-prosecution agent. Substitute the bracketed slots.

> You are a hostile reviewer prosecuting a freshly-written draft as the **{persona_name}** persona. The draft has not been published; the goal is to catch defects BEFORE the user sees the artifact, not after.
>
> ## Persona file
> `personas/{persona_name}.md` — Read this file before forming findings.
>
> ## Shared context (read these once, on demand)
> - `~/.claude/skills/_author-common/principles.md` — author stance, banned authoring rationalizations, authoring-specific critical pairs (A-COLD-vs-WARM, A-VERIFY-vs-INVENT, A-DRAFT-vs-SHIP, A-INTRODUCE-vs-RELOCATE, A-PROSCRIBE-vs-PRESCRIBE, A-CITE-DECISIONS)
> - `~/.claude/skills/_review-common/principles.md` — same stance reviewers apply; you apply it to the freshly-written draft
> - `~/.claude/skills/_review-common/critical-pairs.md` — same pairs; the active subset is named below
> - `personas/ai-development.md` — chunk discipline, plan-quality rules
> - {project_source_of_truth_paths} — e.g., `CLAUDE.md`, `SPEC.md`, brief, engineering-plan, decisions log
>
> ## Ground-truth audit (already passed — do NOT re-prosecute)
> {ground_truth_summary} — list of (line, claim, outcome) entries from `ground_truth_log`. Class V1-V5 claims marked `verified`, `verified_softened`, or `corrected` are settled; do NOT re-raise hallucination findings against them.
>
> ## Introduced identifiers (chunk-owned — NOT hallucinations)
> {introduced_identifiers} — names from sidecar. The draft introduces these; their absence from the repo is the chunk's contract, not a defect.
>
> ## Carry-forward consultation (warm mode only)
> {recently_resolved_blockers_summary} — empty in cold mode. In warm mode, the user already decided how each class resolves. A finding that re-prosecutes a span listed here without a current_reclassification_justification is auto-retracted by the orchestrator, so don't bother filing it.
>
> ## Critical-pair active subset
> {active_critical_pair_subset} — e.g., for `/plan-author` chunk plans: P-CHUNK-SINGLE-CONCERN, P-CHUNK-TEST-PATHS, P-CHUNK-COMMANDS, P-CHUNK-READ-FIRST + universal pairs.
>
> ## Target under review
> - **Type:** {brief | engineering_plan | chunk_plan}
> - **Path:** {target_path}
> - **Stage:** freshly-authored draft, ground-truth-clean, NOT yet published
>
> Read the target in full (not just hunks). Read upstream artifacts when they bear on a finding (chunk plan: read brief + engineering-plan; engineering plan: read brief; brief: read spec.md / project memory).
>
> ## Your task
>
> Prosecute through your persona's lens.
>
> ### Premise-interrogation sub-pass
> 1. List every load-bearing premise the draft asserts (a claim that, if false, breaks the draft's contract).
> 2. For each premise, test it against the actual repo / brief / engineering-plan / decisions log via Read or grep. Skip premises already in the ground-truth audit (don't double-pay).
> 3. File findings on premises that fail interrogation. Format: `premise: "<verbatim>"` / `reality: "<verbatim>"` / `impact: <how the draft breaks if the premise stays>`.
> 4. Output `premise_interrogation: passed` if all premises survive; otherwise output the finding list.
>
> ### Standard-prosecution sub-pass
> Apply the standard fix-list format from `~/.claude/skills/_review-common/agent-prompt.md`. Class > line obligation applies. Same field schema (id, path_or_section, category, severity, tier, finding, exists, evidence, impact, class, universe, proposed_fix, fix_type).
>
> Banned rationalizations from `_review-common/principles.md` apply, plus the author-specific banned list from `_author-common/principles.md`.
>
> ## Output format
>
> ```
> persona: {persona_name}
> premise_interrogation: passed | failed
> premise_findings:
>   - premise: "<verbatim from draft>"
>     reality: "<verbatim from repo / brief / etc.>"
>     reality_source: <path:line or path §heading>
>     impact: <one-sentence>
> findings:
>   - id: f1
>     ...  # standard reviewer schema
> open_questions:
>   - <questions for the user where you cannot recommend a fix>
> ```

---

## Orchestrator pass — applying findings

After all personas return, the author skill (in the main thread) does:

1. **Consolidate.** Same span hit by multiple personas → merge findings, preserve the strongest fix.
2. **Carry-forward auto-retract pass — two priorities, applied in order.** Priority 1 is the *durable* arbitration record (`features/<feature>/decisions.md`); Priority 2 is the *ephemeral* sidecar cache (`recently_resolved_blockers`). Both are consulted; whichever drops the finding first wins. Authority order: `decisions.md` > `recently_resolved_blockers` > prior verdict text.

   **Priority 1 — Decisions log (durable record).** Available whenever `features/<feature>/decisions.md` exists, including cold mode (no sidecar yet) — the durable record outlives every cache. For each finding the personas filed:
   - Read `features/<feature>/decisions.md`. Scan for entries where ALL of:
     - The entry's `Decision:` subject substring-matches the finding's `path_or_section` (matching identifier, file path, section heading, or quoted phrase fragment ≥4 words from the finding body).
     - The entry's `Status:` is `bound` (case-insensitive).
     - The finding contradicts the bound resolution (the persona is filing a fix that would *undo* the bound decision, or a fix that asserts the opposite of what was bound).
   - When all three match, the finding is **auto-retracted** with note `RETRACTED: contradicts bound decisions.md entry "<entry subject>" (<entry date>); entry's Why: "<verbatim Why paragraph, capped at ~200 chars>"`. Logged into `sidecar.auto_retracted_findings` with `priority: decisions_md`.
   - This priority exists because `decisions.md` is the project's converged memory across sessions, surviving cache wipes, machine swaps, and round-counter resets. A finding contradicting a 6-month-old bound decision would re-fire on every cold-start authoring without it.

   **Priority 2 — Recently resolved blockers (ephemeral cache).** Skipped if the sidecar's `recently_resolved_blockers` is empty (cold mode). For each remaining finding:
   - Match the finding's `path_or_section` and `class` against entries in `recently_resolved_blockers`.
   - If the entry's `carry_forward_until_round >= current_invocation_number` (the user-decided arbitration is still in force), the finding is auto-retracted UNLESS the finding has a non-empty `current_reclassification_justification` field that names a concrete change in the repo / brief / engineering plan / decisions log since the resolution. The justification is the finding's own admission: "the user decided X in round 7, but Y has changed since, so X no longer applies."
   - Auto-retracted findings are logged into `sidecar.auto_retracted_findings` with `priority: recently_resolved_blockers` and the matched entry's id; they do NOT appear in `prior_blockers` or `authoring_residual`. The verdict template's "Carry-forward consultation" line reports the count for both priorities.
   - This is the same auto-retract semantic the reviewer skills apply in their Stage 3 / orchestrator-decision phase. Authoring-side respects it identically so a finding the user already arbitrated does not re-fire as a blocker.

3. **Apply auto-fixable findings.** Anything with `fix_type: PLAN_EDIT | BRIEF_EDIT` and no `STABLE_DISAGREEMENT` is applied to the draft directly. Findings with `fix_type: DECISIONS_EDIT` are NOT auto-applied — the author skill writes only the artifact it owns (chunk plan / engineering plan / brief), and edits to other artifacts are surfaced as `OPEN_QUESTION` so the user runs the appropriate sister skill (`/engineering-plan-author --rewrite` or manual decisions.md amendment) to land them.
4. **Run post-fix premise verification.** The orchestrator's own edits get the same treatment the reviewer applies to its own fixes (see `_review-common/blocker-classes.md` § FIX_INTRODUCED_PREMISE_INVERSION). For each orchestrator-applied prose edit:
   - Extract the verifiable claim shape (Behavior / Scope / Constraint / Cross-reference per the reviewer's taxonomy).
   - Re-run ground-truth on the new prose.
   - If the rewrite asserts something not surviving verification, file `FIX_INTRODUCED_PREMISE_INVERSION` against the draft itself and surface to the user as `OPEN_QUESTION`.
5. **Classify residuals.** Anything left unfixed is classified per `_review-common/blocker-classes.md`. Author-side blockers visible to the user are:
   - `STABLE_DISAGREEMENT` between two personas — surface as `OPEN_QUESTION`.
   - `OPEN_QUESTION` from a single persona — surface verbatim.
   - `FIX_INTRODUCED_PREMISE_INVERSION` from step 4 — surface verbatim, include the claim and the verification failure.
6. **Compute polish floor.** If only LOW-severity findings remain and total Tier-2 weight ≤ 4, emit; the residuals go into the sidecar's `authoring_residual` array.
7. **Decide emission.** If any blocker class above LOW is unresolved, the author skill does NOT emit — instead it surfaces the blockers to the user and waits for arbitration. If everything is resolved or under polish floor, the skill emits the draft and persists the sidecar.

**Author-invocation vs reviewer-round mapping.** Reviewer state files use `round_number`; author state files use `invocation_number`. They semantically mirror each other — each round / invocation is a single user-arbitration cycle — so `carry_forward_until_round` on a reviewer-state entry compares against the reviewer's `round_number`, and the same field on an author-state entry compares against the author's `invocation_number`. Cross-side carry-forward (e.g., reviewer-side state file consulted by an author skill in warm mode) compares against the author's current invocation; the reviewer's `round_number` value is treated as a tally on the same number line.

---

## What this protocol does NOT do

- **Re-run ground-truth.** Personas trust the audit log. The reviewer's "premise interrogation" sub-pass at review time prosecutes against the *repo*; here, the audit log is the ground-truth substitute (cheaper, already done).
- **Add features beyond the brief.** Personas prosecute drift, factoring, missing tests, security, scope. They do not propose new product capabilities. Product persona's role is to catch *brief contradictions*, not to extend the brief.
- **Polish for polish's sake.** Only findings with concrete failure modes (per `_review-common/principles.md` banned rationalizations) are valid. "Could be clearer" without "and here's the failure mode that ambiguity causes" is invalid.

The contract: take a ground-truth-clean draft, return a draft with persona-class defects fixed in-place or surfaced as explicit blockers — never silently shipped to the user.
