# Self-prosecution protocol — personas attack your own draft

Loaded by `/spec-author`, `/brief-author`, `/engineering-plan-author`, `/plan-author`. The hosting skill calls this AFTER ground-truth has run and the draft is anchor-clean. Output is a draft with the same fix categories the reviewer would have produced — but applied at write time, not surfaced to the user as a NEEDS_USER_INPUT verdict.

The personas reused here are the same as the review-v2 personas (`personas/backend.md`, `personas/frontend.md`, `personas/architecture.md`, `personas/testing.md`, `personas/security.md`, `personas/product.md`, `personas/code-reviewer.md`, `personas/ai-development.md`). Same prosecution lens, different time horizon: instead of finding what's wrong with someone else's artifact, find what's wrong with what YOU just wrote.

---

## Persona selection per skill

| Skill | Personas |
|---|---|
| `/spec-author` | product, architecture (internal consistency, domain-model soundness, invariant-ledger conformance applied to the root spec layer) |
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

### Model pin (HARD requirement)

Every self-prosecution agent takes an explicit `model: "sonnet"` on the Agent call — never inherit the session model. Per `_review-common/principles.md` § Station model policy: the personas prosecute against verbatim-inlined rules with a fixed output schema, and the exclusion-challenge log makes their quality observable, so the execution tier suffices — while the authoring main thread (where factoring judgment lives) stays on the session model. The author skill records `persona_model: "sonnet"` in the sidecar; a recorded session-tier value here is a defect.

The orchestrator constructs two of these slots ONCE in the main thread and substitutes the same text into every persona prompt, so N personas no longer each re-Read static files that never change between invocations:

- `{inlined_rules_block}` — built by reading `_author-common/principles.md`, `_review-common/principles.md`, `_review-common/critical-pairs.md`, and the chunk-discipline / halved-work section of `personas/ai-development.md` once, then inlining those sections **verbatim and in full**. This replaces the four static-file reads each persona used to do.
- `{project_invariants_digest}` — the `project_invariants` list from the context-pack (`_author-common/context-pack-protocol.md`). This replaces each persona re-Reading `CLAUDE.md` for the project rules.

One main-thread read each replaces one re-read per persona (5 personas × 3 skills × ~5 static files = the redundant-read tax this removes). The persona's OWN file is still Read live per agent — it is the lens, it is large, and it is persona-specific.

### Verbatim, not digested (HARD requirement)

The orchestrator is a **pipe, not an editor**. Inlining exists to save the persona a file read — it does NOT license the orchestrator to summarize, paraphrase, rank, or subset what it inlines. Specifically:

- Inline the **full** banned-rationalization list from both `principles.md` files. Not "the relevant ones."
- Inline the **entire** `_review-common/critical-pairs.md` pair set. Do NOT pre-select an "active subset" — the file is small, and letting the persona judge which pairs bear on the draft is the whole point. `{active_critical_pair_subset}` is retained below only as a *hint* ("these are the pairs the hosting skill expects to bite"), explicitly non-exhaustive and explicitly non-binding.
- Inline the chunk-discipline / halved-work section of `personas/ai-development.md` verbatim.

**Why this is a HARD requirement, not a style preference.** The author is the party being prosecuted. Any step where the author chooses *which rules the prosecutor is judged against* is a channel through which the author can — without any intent to deceive — quietly omit the exact rule that would catch its own draft. A digest is an editorial act; verbatim inlining is not. The cost delta is roughly 100 lines per persona prompt, which is noise against a run that spawns five prosecutors, and it buys the removal of the sharpest remaining bias channel in the self-prosecution loop.

If a rules file grows large enough that verbatim inlining becomes genuinely expensive, the fix is to have personas Read it directly — NOT to reintroduce an author-written digest.

> You are a hostile reviewer prosecuting a freshly-written draft as the **{persona_name}** persona. The draft has not been published; the goal is to catch defects BEFORE the user sees the artifact, not after.
>
> ## Persona file (Read this — it is your lens)
> `personas/{persona_name}.md` — Read this file in full before forming findings. This is the ONE rules file you Read; it is not inlined because it is large and persona-specific.
>
> ## Shared rules (inlined by the orchestrator — do NOT re-Read these files)
> The orchestrator read the static rules files ONCE in the main thread and inlined them **verbatim and in full** below, so you do not pay a per-persona re-read of files that never change between invocations. This is a mechanical copy, not a summary: what follows is the complete text, not the orchestrator's selection from it. Treat it as authoritative — exactly as if you had read it from source.
> - {inlined_rules_block} — the full banned-rationalization list (from `_author-common/principles.md` + `_review-common/principles.md`), the complete critical-pair set (from `_review-common/critical-pairs.md`), and the chunk-discipline / halved-work rule (from `personas/ai-development.md`).
> - {project_invariants_digest} — the project-level invariants (from the context-pack, per `_author-common/context-pack-protocol.md`): feature-independent banned patterns, business rules, and project assumptions. You therefore do NOT Read `CLAUDE.md` to know the project rules — but you MAY Read a specific `CLAUDE.md` span if a finding needs to quote a rule verbatim (targeted, not a full read).
>
> If the rules block appears abridged — a list that trails off, a pair set visibly smaller than the file it cites, a section header with no body — that is an orchestrator defect. Report it in your output under `rules_block_integrity` and Read the source file yourself for the affected section.
>
> ## The exclusion set — two kinds, treated differently
>
> Some spans of the draft arrive pre-marked as settled. **The two kinds below have different authority, and you must not conflate them.**
>
> ### Kind 1 — Author self-attestation (presumptively settled, but CHALLENGEABLE)
>
> These are things the *author of the draft you are prosecuting* asserts it already checked. Nobody independent arbitrated them.
>
> - **Ground-truth audit.** {ground_truth_summary} — list of (line, claim, outcome) entries from `ground_truth_log`. Class V1-V5 claims marked `verified`, `verified_softened`, or `corrected` are presumed settled.
> - **Introduced identifiers.** {introduced_identifiers} — names from sidecar. The draft introduces these; their absence from the repo is presumed to be the chunk's contract, not a defect.
>
> **Default: accept both and spend your budget elsewhere.** The presumption is strong and usually correct; do not burn the run re-verifying settled claims.
>
> **But the presumption is rebuttable.** If, in the course of prosecuting something else, you find concrete evidence that an entry in Kind 1 is wrong — the claim marked `verified` does not actually hold at repo HEAD, or a name in `introduced_identifiers` already exists and the draft is colliding with it rather than introducing it — you MAY file a finding against it. Set `exclusion_challenge: true` and populate `challenged_entry` with the verbatim entry you are rebutting.
>
> Rules for a challenge:
> - It requires **concrete evidence you actually observed this run** — a Read/grep result you can quote with `path:line`. "The author might not have checked carefully" is not evidence and is a banned rationalization.
> - Do NOT go hunting. Challenges are a byproduct of prosecution you were doing anyway, not a work item. Never open a systematic re-audit of the ground-truth log.
> - A challenge you cannot anchor verbatim is malformed and will be discarded.
>
> The orchestrator will adjudicate every challenge and log it either way (see § Orchestrator pass). Filing a well-anchored challenge that turns out to be wrong costs you nothing.
>
> ### Kind 2 — User arbitration (settled, NOT challengeable)
>
> {recently_resolved_blockers_summary} — empty in cold mode. In warm mode, **the user already decided how each class resolves.** This is a human arbitration, not a machine's self-report.
>
> Do NOT file against these, and do NOT set `exclusion_challenge` on them — the flag does not apply to Kind 2 and the orchestrator ignores it there. A finding that re-prosecutes a span listed here without a `current_reclassification_justification` naming a concrete change since the resolution is auto-retracted. Re-opening a decision the user already made is the specific failure this carve-out exists to prevent; the same applies to bound entries in `features/<feature>/decisions.md`.
>
> ## Critical-pair set
> The complete pair set is inlined in `{inlined_rules_block}` above — judge for yourself which pairs bite on this draft.
>
> {active_critical_pair_subset} — a **non-binding hint** from the hosting skill about which pairs it expects to be relevant (e.g., for `/plan-author` chunk plans: P-CHUNK-SINGLE-CONCERN, P-CHUNK-TEST-PATHS, P-CHUNK-COMMANDS, P-CHUNK-READ-FIRST + universal pairs). This list is explicitly **not exhaustive and not a restriction**. A pair absent from the hint is fully in scope; file against it normally and note `pair_outside_hint: true`.
>
> ## Target under review
> - **Type:** {brief | engineering_plan | chunk_plan}
> - **Path:** {target_path}
> - **Stage:** freshly-authored draft, ground-truth-clean, NOT yet published
>
> Read the target in full (not just hunks) — the target is the artifact under prosecution and must be read live. For UPSTREAM artifacts, the orchestrator has already ground-truthed every V1–V5 claim (see the ground-truth digest below) and inlined the project invariants above: do a TARGETED Read of a specific upstream span ONLY to test a premise the ground-truth audit did not settle — a semantic / pattern-match premise that goes deeper than an existence or quote check (see the premise-interrogation sub-pass). Do NOT re-Read the full brief / engineering-plan / spec / `CLAUDE.md` to re-verify existence or quote claims already in the digest; that blanket re-read is the redundant cost this protocol eliminates. Premise interrogation is NOT weakened — its targeted reads are exactly the deeper checks ground-truth does not perform.
>
> ## Your task
>
> Prosecute through your persona's lens.
>
> ### Premise-interrogation sub-pass
> 1. List every load-bearing premise the draft asserts (a claim that, if false, breaks the draft's contract).
> 2. For each premise, test it against the actual repo / brief / engineering-plan / decisions log via a TARGETED Read or grep (the specific span, not a full-file re-read). Skip premises already settled in the ground-truth audit (don't double-pay) — your reads are reserved for the semantic / pattern-match premises ground-truth's existence-and-quote checks do not reach.
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
> rules_block_integrity: intact | abridged: <which section looked truncated>
> premise_interrogation: passed | failed
> premise_findings:
>   - premise: "<verbatim from draft>"
>     reality: "<verbatim from repo / brief / etc.>"
>     reality_source: <path:line or path §heading>
>     impact: <one-sentence>
> findings:
>   - id: f1
>     ...  # standard reviewer schema
>     exclusion_challenge: true | false        # omit or false unless rebutting a Kind 1 entry
>     challenged_entry: "<verbatim entry from ground_truth_log / introduced_identifiers>"
>     challenge_evidence: "<path:line + verbatim quote observed THIS run>"
>     pair_outside_hint: true | false          # true if filed against a pair absent from the hint
> open_questions:
>   - <questions for the user where you cannot recommend a fix>
> ```

---

## Orchestrator pass — applying findings

After all personas return, the author skill (in the main thread) does:

1. **Consolidate.** Same span hit by multiple personas → merge findings, preserve the strongest fix.
2. **Adjudicate exclusion challenges.** Partition the consolidated findings on `exclusion_challenge: true`. These are personas rebutting a Kind 1 author self-attestation (a `ground_truth_log` entry or an `introduced_identifiers` name). For each:
   - **Discard as malformed** if `challenge_evidence` is absent, or is not a `path:line` + verbatim quote the persona observed this run. Log with `disposition: malformed`. Do not adjudicate it further.
   - **Otherwise re-verify the challenged entry directly** — one targeted Read/grep against repo HEAD (or the cited upstream artifact). This is the orchestrator's own check, not a re-run of the persona's reasoning.
     - Challenge **upheld** (the entry is wrong): correct the `ground_truth_log` entry in the sidecar, let the finding proceed into the normal fix pipeline, and log `disposition: upheld`.
     - Challenge **rejected** (the entry holds): retract the finding with note `RETRACTED: exclusion challenge rejected; "<entry>" re-verified at <path:line>`, and log `disposition: rejected`.
   - Log EVERY challenge — upheld, rejected, and malformed — into `sidecar.exclusion_challenges` (schema below). **The log is the point.** A rejected challenge is not waste: the rejection rate across runs is the only signal that says whether the author's self-attestation is trustworthy, and it is unobservable if challenges are silently dropped.
   - **Kind 2 (user arbitration) is out of scope here.** An `exclusion_challenge` flag set against a `recently_resolved_blockers` entry or a bound `decisions.md` entry is ignored — strip the flag and let the finding fall through to the carry-forward pass below, which retracts it as it always has. User decisions are not re-opened by this mechanism.
3. **Carry-forward auto-retract pass — two priorities, applied in order.** Priority 1 is the *durable* arbitration record (`features/<feature>/decisions.md`); Priority 2 is the *ephemeral* sidecar cache (`recently_resolved_blockers`). Both are consulted; whichever drops the finding first wins. Authority order: `decisions.md` > `recently_resolved_blockers` > prior verdict text.

   **Priority 1 — Decisions log (durable record).** Available whenever `features/<feature>/decisions.md` exists, including cold mode (no sidecar yet) — the durable record outlives every cache. For each finding the personas filed:
   - Read `features/<feature>/decisions.md`. Scan for entries where ALL of:
     - The entry's `Decision:` subject substring-matches the finding's `path_or_section` (matching identifier, file path, section heading, or quoted phrase fragment ≥4 words from the finding body).
     - The entry's `Status:` is `bound` (case-insensitive) and the entry is in the `## Active (bound)` section — an entry marked `superseded by "<title>" (<date>)` or `obsolete` in the `## Archived (superseded / obsolete)` tail never binds or retracts (per `~/.claude/skills/_review-common/principles.md` § What counts as a bound entry).
     - The finding contradicts the bound resolution (the persona is filing a fix that would *undo* the bound decision, or a fix that asserts the opposite of what was bound).
   - When all three match, the finding is **auto-retracted** with note `RETRACTED: contradicts bound decisions.md entry "<entry subject>" (<entry date>); entry's Why: "<verbatim Why paragraph, capped at ~200 chars>"`. Logged into `sidecar.auto_retracted_findings` with `priority: decisions_md`.
   - This priority exists because `decisions.md` is the project's converged memory across sessions, surviving cache wipes, machine swaps, and round-counter resets. A finding contradicting a 6-month-old bound decision would re-fire on every cold-start authoring without it.

   **Priority 2 — Recently resolved blockers (ephemeral cache).** Skipped if the sidecar's `recently_resolved_blockers` is empty (cold mode). For each remaining finding:
   - Match the finding's `path_or_section` and `class` against entries in `recently_resolved_blockers`.
   - If the entry's `carry_forward_until_round >= current_invocation_number` (the user-decided arbitration is still in force), the finding is auto-retracted UNLESS the finding has a non-empty `current_reclassification_justification` field that names a concrete change in the repo / brief / engineering plan / decisions log since the resolution. The justification is the finding's own admission: "the user decided X in round 7, but Y has changed since, so X no longer applies."
   - Auto-retracted findings are logged into `sidecar.auto_retracted_findings` with `priority: recently_resolved_blockers` and the matched entry's id; they do NOT appear in `prior_blockers` or `authoring_residual`. The verdict template's "Carry-forward consultation" line reports the count for both priorities.
   - This is the same auto-retract semantic the reviewer skills apply in their Stage 3 / orchestrator-decision phase. Authoring-side respects it identically so a finding the user already arbitrated does not re-fire as a blocker.

4. **Apply auto-fixable findings.** Anything with `fix_type: PLAN_EDIT | BRIEF_EDIT` and no `STABLE_DISAGREEMENT` is applied to the draft directly. Findings with `fix_type: DECISIONS_EDIT` are NOT auto-applied — the author skill writes only the artifact it owns (chunk plan / engineering plan / brief), and edits to other artifacts are surfaced as `OPEN_QUESTION` so the user runs the appropriate sister skill (`/engineering-plan-author` or manual decisions.md amendment) to land them.
5. **Run post-fix premise verification.** The orchestrator's own edits get the same treatment the reviewer applies to its own fixes (see `_review-common/blocker-classes.md` § FIX_INTRODUCED_PREMISE_INVERSION). For each orchestrator-applied prose edit:
   - Extract the verifiable claim shape (Behavior / Scope / Constraint / Cross-reference per the reviewer's taxonomy).
   - Re-run ground-truth on the new prose.
   - If the rewrite asserts something not surviving verification, file `FIX_INTRODUCED_PREMISE_INVERSION` against the draft itself and surface to the user as `OPEN_QUESTION`.
6. **Classify residuals.** Anything left unfixed is classified per `_review-common/blocker-classes.md`. Author-side blockers visible to the user are:
   - `STABLE_DISAGREEMENT` between two personas — surface as `OPEN_QUESTION`.
   - `OPEN_QUESTION` from a single persona — surface verbatim.
   - `FIX_INTRODUCED_PREMISE_INVERSION` from the post-fix premise verification step — surface verbatim, include the claim and the verification failure.
   - An **upheld** exclusion challenge whose finding could not be auto-fixed — surface verbatim, and say plainly that the author's own ground-truth log was wrong about it. This class is never silently absorbed.
7. **Compute polish floor.** If only LOW-severity findings remain and total Tier-2 weight ≤ 4, emit; the residuals go into the sidecar's `authoring_residual` array. Upheld exclusion challenges do NOT count toward the polish floor regardless of severity — a wrong ground-truth entry is a correctness signal about the audit itself, not polish.
8. **Decide emission.** If any blocker class above LOW is unresolved, the author skill does NOT emit a clean artifact — instead it writes the partial draft under the `Status: needs-user-input` gate, surfaces the blockers to the user, and the run ends; the session agent applies the arbitration directly (the author is not re-invoked). If everything is resolved or under polish floor, the skill emits the draft and persists the sidecar.

### `sidecar.exclusion_challenges` schema

Written by orchestrator step 2. Present (possibly empty) on every non-`--draft` run, so "no challenges filed" is distinguishable from "the mechanism didn't run."

```json
"exclusion_challenges": [
  {
    "persona": "<persona_name>",
    "finding_id": "<f1>",
    "challenged_kind": "ground_truth_log" | "introduced_identifiers",
    "challenged_entry": "<verbatim entry the persona rebutted>",
    "challenge_evidence": "<path:line + verbatim quote the persona observed>",
    "disposition": "upheld" | "rejected" | "malformed",
    "adjudication_evidence": "<path:line the orchestrator re-verified against, or null if malformed>"
  }
]
```

**Reading the log.** The rejection rate is the metric this exists to produce. A run of invocations where challenges are consistently `rejected` says the author's self-attestation is reliable and the reviewer skills' sidecar trust is well-founded. A material `upheld` rate says the opposite, and is the evidence that would justify loosening the reviewer-side mandatory sidecar consultation (`/brief-review-v2` § Author sidecar consultation and its siblings). Do not change that reviewer behavior on intuition — change it on this log.

**Author-invocation vs reviewer-round mapping.** Reviewer state files use `round_number`; author state files use `invocation_number`. They semantically mirror each other — each round / invocation is a single user-arbitration cycle — so `carry_forward_until_round` on a reviewer-state entry compares against the reviewer's `round_number`, and the same field on an author-state entry compares against the author's `invocation_number`. Cross-side carry-forward (e.g., reviewer-side state file consulted by an author skill in warm mode) compares against the author's current invocation; the reviewer's `round_number` value is treated as a tally on the same number line.

---

## What this protocol does NOT do

- **Re-run ground-truth.** Personas trust the audit log by default. The reviewer's "premise interrogation" sub-pass at review time prosecutes against the *repo*; here, the audit log is the ground-truth substitute (cheaper, already done). The exclusion-challenge affordance is a narrow exception, not a repeal: it fires on evidence a persona stumbled into while prosecuting something else. A persona that opens a systematic re-audit of the ground-truth log has misread the protocol.
- **Re-open user decisions.** Bound `decisions.md` entries and in-force `recently_resolved_blockers` are settled. No challenge mechanism reaches them.
- **Add features beyond the brief.** Personas prosecute drift, factoring, missing tests, security, scope. They do not propose new product capabilities. Product persona's role is to catch *brief contradictions*, not to extend the brief.
- **Polish for polish's sake.** Only findings with concrete failure modes (per `_review-common/principles.md` banned rationalizations) are valid. "Could be clearer" without "and here's the failure mode that ambiguity causes" is invalid.

The contract: take a ground-truth-clean draft, return a draft with persona-class defects fixed in-place or surfaced as explicit blockers — never silently shipped to the user.
