---
name: scope-check
description: Checks whether a feature's plan actually delivers each brief Goal in full, or quietly narrows it to a subset, a weaker signal, or an action taken before its basis exists. Every unapproved narrowing is rendered as a decision for you to approve or reject. The same check runs inside the engineering-plan skills; use this when you want the scope verdict on demand.
user-invocable: true
---

# Scope-check — adversarial scope-fidelity pass

## Why this exists

A recurring failure: a brief Goal commits to an outcome over a domain ("across the catalog", "junk can't silently return", "every Person the user can reach") or on an authoritative signal ("judged on the work itself"), and the plan delivers that outcome over a *subset* — one media type, one surface, one call path — or computes it on a weaker proxy, or acts irreversibly on the proxy before the authoritative input exists. Every conformance gate passes (the Goal maps to a delivering chunk, the decisions are bound, the plan is implementable), because none of them measure whether *delivery-scope equals intended-scope*. The narrowing gets bound silently and surfaces only at PR review or in production.

This is one failure wearing many shapes. The single question underneath: **has the plan silently substituted a narrower outcome than the one the Goal's author intended?** Surface-coverage, input-fidelity, and pipeline-timing are just the axes the substitution hides along.

The catch is unreliable when the *author* is asked to see it (the author who chose the narrow reading is blind to it, or has already rationalized it). It is reliable when a *separate adversary* — one whose only incentive is to find the shortfall — looks. That separation is why this is a dedicated pass, not an instruction folded into authoring.

## Usage

```
/scope-check <feature>                 # resolves features/<feature>/{brief,decisions}.md + every engineering plan
/scope-check <brief-path> <ep-path> [<ep-path> ...] [<decisions-path>]
```

Resolve the engineering plan(s) per `~/.claude/skills/_plan-common/layout.md`: `features/<feature>/engineering-plan.md` when the feature is **flat**, or every `features/<feature>/plans/<track>/engineering-plan.md` when it is **tracked**. `brief.md` and `decisions.md` are always at the feature root.

**A tracked feature is checked against the union of its plans, never one plan alone.** Scope-fidelity asks whether the *feature* delivers each Goal's full outcome. One track of a multi-track feature delivers a declared slice by construction, so judging it in isolation reports every other track's work as a narrowing — the check would produce nothing but false positives, and a director who learns to ignore it stops reading the real ones. Never invoke this skill on a single track of a tracked feature.

Run it AFTER the brief and engineering plan(s) exist and have passed their own reviews, BEFORE committing to build. It does not replace `/brief-review-v2` or `/engineering-plan-review-v2`; it adds the one check they structurally miss.

## Procedure

1. **Read the artifacts.** `brief.md` (Goals with their `Measured by:` clauses, the four `## Scope` buckets — or a legacy bare `## Non-goals` list, which reads as *Not planned* — and User-facing changes), **every** engineering plan of the feature (Brief mapping, Goal scope, Chunk index, Decisions closure), `decisions.md` if present — consult only Active-section `Status: bound` entries; a `superseded`/`obsolete` entry in the `## Archived` tail does not bind (per `~/.claude/skills/_review-common/principles.md` § What counts as a bound entry).

   For a tracked feature, also build a **Goal-clause ownership map** before spawning anything: for each Goal, which plan claims which clause. Each plan's `## Goal scope` section is the declaration; a Goal claimed by no plan, or a clause every plan disclaims, is the finding the union check exists to catch. Pass the map to every adversary — it is what lets them tell a declared hand-off from a hole.

2. **Spawn one adversary PER GOAL, in parallel — do NOT batch.** Launch one `general-purpose` subagent per brief Goal (Agent tool), each pinned to an off-model `model` override per `~/.claude/skills/_review-common/brief-conformance-prosecutor.md` § Model pin (default `sonnet`; `opus` if the session is already Sonnet — never inherit), and each given the mandate below plus that ONE Goal (with the full brief for Non-goal context, **every** engineering plan of the feature, the Goal-clause ownership map when tracked, and decisions). Do NOT run one adversary over all Goals in a single call, and do NOT run the analysis in the authoring/main thread. TWO separations are load-bearing: adversary-not-author, and one-Goal-per-call. Batching many items into a single judge call degrades recall sharply — validated: one call asked to judge 54 real decisions returned zero flags, missing a narrowing that the identical mandate flagged when that decision was judged in isolation. Attention dilutes across items and each gets a charitable read.

3. **Each adversary judges its one Goal.** Reconstruct that Goal's maximal reasonable scope, determine what the chunk set + bound decisions actually deliver, and classify any narrowing.

4. **Surface narrowings as decisions.** The output is not "bugs" — it is a short list of scope decisions the director must make: *approve this narrowing as a launch-acceptable cut, or send it back to widen coverage.* Goals with no narrowing get a clean bill.

## The adversary mandate (spawn with this verbatim)

> You are a scope-fidelity adversary. You are given a feature's brief, engineering plan, and decisions log. Your ONLY job is to catch, for each Goal, a plan that delivers the Goal's outcome over LESS than the full scope its author intended, without that narrowing being explicitly approved as a launch-acceptable cut. You are not the author; your incentive is to find the shortfall, not to justify the plan.
>
> For EACH Goal in the brief:
> 1. **maximal_scope** — reconstruct the fullest outcome a reasonable author of this Goal would expect: across every surface, media type, call path, consumer, case, and input the outcome must hold for the Goal to be honestly satisfied; and the authoritative signal the outcome must be judged/computed on (or "none"). Be concrete and name the domain members explicitly.
> 2. **delivered_scope** — from the chunk index, brief mapping, and bound decisions (count only Active-section `Status: bound` decisions toward delivered scope — a `superseded`/`obsolete` entry in the `## Archived` tail does not; per `~/.claude/skills/_review-common/principles.md` § What counts as a bound entry), state what scope the plan actually delivers the outcome over, on what input, at which consumers. **If you were given more than one engineering plan, delivered_scope is their UNION.** These are tracks of one feature, not competing proposals: a clause this plan disclaims and a sibling plan claims IS delivered, and reporting it as a narrowing is a false positive. Name which plan delivers each part.
> 3. **narrowing_present (yes/no)** — is delivered_scope a strict subset of maximal_scope? I.e., is there a consumer / surface / media type / case / input the Goal covers where the outcome is delivered by a weaker proxy, not at all, or acted on (especially irreversibly) before its authoritative basis exists?
> 4. If yes, classify:
>    - **LEGITIMATE (no flag):** the narrowing is explicitly acknowledged AND justified as acceptable to ship — a stated sound reason, an environment fact that makes the residual moot, or affirmative evidence supporting the smaller scope — AND the residual does not leave the user-visible outcome half-delivered.
>      A residual sitting in the brief's `## Scope` → `### Intentionally deferred` bucket **with a named destination** (an issue number or a follow-on feature slug) is LEGITIMATE by construction: that bucket exists to say "committed, later, here is where," and the author already made this call deliberately. Do not re-flag it. A residual in `### Not in scope (this release)` or `### Not planned` is likewise an explicit acknowledgement — judge only whether it leaves the user-visible outcome half-delivered. A deferral with **no** destination is NOT legitimate: an unaddressed promise is a silent narrowing wearing a bucket label, and nothing will ever notice it went unkept.
>    - **DECISION (flag):** the narrowing is silent (nothing frames the smaller scope as a deliberate acceptable cut), OR it is acknowledged but the residual is actually required to make the user-visible outcome whole (deferring it ships the outcome incomplete and needs later work to finish). This is the director's call, not one to bind silently.
>    - **UNOWNED (flag):** multi-plan features only — every plan explicitly disclaims this clause and none claims it. A hand-off that both sides decline is the failure mode the union check exists to catch: each plan looks locally complete and reviews clean, and the clause ships nowhere. Name the clause and both disclaimers verbatim; the resolution is to assign an owner, not to widen a plan arbitrarily.
>
> Calibration — this cuts both ways:
> - Do NOT flag legitimate scope cuts. Features cut scope on purpose; a sound, stated reason is not a gap. Over-flagging every narrowing is a failure.
> - BE SUSPICIOUS of a narrowing justified by comparison to a prior or alternative implementation ("richer than before", "strictly better than the old way") rather than to the Goal itself — that is a common way under-delivery hides.
> - Weight by reversibility: a narrowing whose consequences a later pass can correct is weaker than one that cannot be undone. An irreversible or hard-to-correct action taken on a proxy/degraded basis, when the authoritative basis exists elsewhere or at a later stage, is the sharpest flag.
> - READ FOR THE INTENDED OUTCOME, NOT THE LITERAL WORDS. If the Goal names a *mechanism* ("using an allowlist/ML approach", "via a dedupe step", "with an LLM pass") rather than an observable outcome, do NOT treat performing that mechanism *somewhere* as satisfying the Goal — a mechanism-phrased Goal is satisfiable on a subset (allowlist here, ML there) while the user-visible outcome ships nowhere whole. Reconstruct the outcome the mechanism was meant to produce and check *that* across the domain. FLAG the partition, and note that the Goal itself should be rephrased as an outcome upstream — because a conservative reader taking the mechanism words literally will wrongly acquit it (this is the exact failure that shipped the original bug). The check is only reliable on a mechanism-phrased Goal once the brief restates it as an outcome.
>
> Output, per Goal:
> ```
> Goal: <verbatim>
> maximal_scope: ...
> delivered_scope: ...            # union across plans; name which plan delivers each part
> verdict: CLEAR | DECISION | UNOWNED
> narrowing: <the specific consumer/surface/input/case left short> (if DECISION or UNOWNED)
> disclaimed_by: <each plan's verbatim disclaimer of this clause> (if UNOWNED)
> why_not_legitimate: <why it is silent or required-work, not an acceptable cut> (if DECISION)
> resolution: widen_coverage: <what chunk must be added/widened> | scope_down: <how the Goal's domain would shrink + the Non-goal that names the residual, only if genuinely launch-acceptable>
> confidence: 0-100
> ```
> End with a one-paragraph summary: how many Goals CLEAR, how many DECISION, and the single most consequential decision the director faces.

## Output to the director

Render the adversary's DECISION items as a short, ordered list of scope calls — one line each: the Goal, what gets narrowed, and the two choices (approve the cut / widen coverage). Keep review-machinery jargon out; the audience is the director deciding what to build. CLEAR Goals get a single line of acknowledgement. If every Goal is CLEAR, say so plainly.

## Relationship to the automatic gate

The mandate this skill runs is now **integrated** into the shared `_review-common/brief-conformance-prosecutor.md` as the **Scope-fidelity Adversary** — `/engineering-plan-author` (Brief-conformance gate) and `/engineering-plan-review-v2` (Stage 1.5) spawn it automatically, one adversary per at-risk Goal, and route flagged narrowings as `SURFACE_PARITY_GAP` blockers. So scope-fidelity is no longer something you have to remember to run; the author/reviewer cycle enforces it.

Both renderings carry the multi-plan union rule and the `UNOWNED` verdict; the prosecutor doc's `{sibling_plan_paths}` substitution is what feeds sibling tracks to the integrated adversary, and this skill's Goal-clause ownership map is the same input in director-facing form.

The adversary mandate in this skill and the canonical one in the prosecutor doc are the **same check with two renderings**: the integrated adversary emits `SURFACE_PARITY_GAP` JSON findings for the orchestrator to gate on; this skill renders the same analysis as a short list of **director decisions** (approve the cut / widen coverage), review-machinery jargon stripped. Keep the two mandates in sync — if you refine the analysis, refine both (the prosecutor doc's § Scope-fidelity Adversary is the source of truth; this skill mirrors it in director-facing form).

When to reach for this skill rather than the gate: you want the scope verdict framed as product decisions outside a full review round, or you want to sanity-check a brief/EP pair before committing to build without invoking the whole author/reviewer machinery. Run it deliberately on the at-risk class of Goal (domain-quantified or authoritative-signal Goals); single-surface concrete Goals rarely have a narrowing to find.
