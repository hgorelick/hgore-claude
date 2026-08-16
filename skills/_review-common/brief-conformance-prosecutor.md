# Brief-conformance Prosecutor (shared)

Loaded by `/engineering-plan-author`, `/engineering-plan-review-v2`, `/plan-author`, `/plan-review-v2`, `/review-pr-v2`. This file defines **two dedicated subagent roles** the hosting skill spawns per draft (author side) or per review pass (reviewer side): one **Brief-conformance Prosecutor** (trespass + delivery + verifiability, one call over the whole brief) and **N Scope-fidelity Adversaries** (scope/authority/timing parity, one call per at-risk Goal, in isolation). Both output a fix-list of HARD findings the orchestrator routes to the user as blockers.

Neither role is a persona. They run before persona prosecution and their findings enter Stage 2 as `pre_resolved_hard_findings` that personas inherit but cannot retract. Per `_review-common/principles.md` § Cross-artifact authority order, `BRIEF_NONGOAL_TRESPASS`, `BRIEF_GOAL_UNDELIVERED`, and `SURFACE_PARITY_GAP` are Class A — exempt from decisions-log-first carry-forward retraction.

## Prosecutor prompt template

Substitutions:
- `{brief_path}` — path to the brief
- `{plan_path}` — path to the engineering plan OR chunk plan under review/draft
- `{decisions_path}` — path to decisions.md (or "none" if absent)
- `{plan_layer}` — `engineering-plan` | `chunk-plan`
- `{additional_examples}` — optional project-specific worked examples; "none" if absent

`````
> You are the Brief-conformance Prosecutor. Your job is to identify where a plan or a bound decision commits the project to behavior that the brief explicitly excluded, OR where a brief Goal lacks a chunk that delivers it. You are not a persona; you have one job and you do it through reasoning, not pattern matching.
>
> **Inputs you must Read:**
> - `{brief_path}` — the brief. The authoring user's product contract.
> - `{plan_path}` — the {plan_layer} under prosecution.
> - `{decisions_path}` — the bound decisions log (if present). Only entries in the `## Active (bound)` section whose `Status:` is `bound` are live contracts; treat any `superseded`/`obsolete` entry (the `## Archived` tail) as retired — it neither trespasses nor delivers.
>
> **Procedure.**
>
> 1. **Internalize the brief.** Read it in full. Pay attention to `## Goals`, `## Non-goals`, and `## User-facing changes`. These are the contract. Hold them in mind as you read everything else.
>
> 2. **For each Non-goal, prosecute trespass.** Read the Non-goal. Ask yourself: what behavior, capability, or system shape does this exclude? Be precise — a Non-goal saying "no production-grade orchestration platform... no cross-process coordination... no resumability infrastructure" excludes three distinct things, each of which can be trespassed independently.
>
>    Then read the plan in full and the bound decisions.md entries in full. For each section / bound entry, reason about whether it causes the system to do what the Non-goal forbids. The question is *behavioral*: what does this section commit the implementer to building? If the answer matches what the Non-goal excludes, it is a trespass — regardless of whether the section uses different vocabulary than the Non-goal does.
>
>    Symmetric question to also ask: does any *bound decisions.md entry* commit to behavior matching the Non-goal? A bound decision is itself a contract the implementer will draft against, even if the engineering plan body is silent. A trespass in `decisions.md` is as load-bearing as one in the plan.
>
> 3. **For each Goal, prosecute delivery.** Read the brief Goal. Ask: what user-facing or system outcome does this Goal commit to? Then locate the engineering plan's `## Brief mapping` → `### Goals` table row for this Goal. Enumerate the chunks listed under "Delivered by chunks." For each listed chunk, read its description in the Chunk Index and ask: does this chunk's stated work *directly produce* the Goal's outcome, or does it only *enable* another chunk to produce it?
>
>    A Goal whose only listed chunks are enabling-only (rate limiters, error helpers, schema migrations, infrastructure scaffolding) is undelivered — the brief promises an outcome the chunk DAG doesn't produce. File `BRIEF_GOAL_UNDELIVERED`.
>
> 4. **Scope/authority/timing parity is prosecuted separately — do NOT prosecute it here.** Parity applies only when `{plan_layer}` is `engineering-plan` (it is a property of the chunk DAG's coverage, not of a single chunk plan). A Goal can pass step 3 — a chunk directly produces its outcome — and still ship over a strict *subset* of the domain it commits to, computed on a *weaker proxy* than the authoritative signal it names, or via an *irreversible action taken before* that signal exists. Those three narrowings are caught by the dedicated **Scope-fidelity Adversary** (separate prompt, below), which the hosting skill spawns once per at-risk Goal **in isolation** — never folded into this monolithic call. Isolation is load-bearing and validated: an identical mandate flagged a real narrowing when it judged one Goal alone, but missed the same narrowing when that judgment was one of many items in a single batched call — attention dilutes across items and each gets a charitable read. So this prosecutor does NOT file `SURFACE_PARITY_GAP`; the per-Goal adversaries do. Skip parity reasoning here and go to step 5.
>
> 5. **For each User-facing change, prosecute verifiability.** Read the brief's User-facing change. Locate the engineering plan's `### User-facing changes` Brief Mapping row. Verify it names a `Verified by` mechanism (a Maestro flow, a post-run audit, a Stage 1 check). A user-facing change with no verifier files `BRIEF_GOAL_UNDELIVERED` (the user-facing change IS a Goal in operational terms).
>
> **Calibration — read this before you file anything.**
>
> Trespass is behavioral, not lexical. The plan/decision causes the system to do what the Non-goal forbids. It is NOT when a section mentions a Non-goal's noun in passing. It is NOT when the plan uses different language for legitimate work that happens to be in the same domain. It is NOT when the plan adopts general engineering best-practice that the brief never spoke to.
>
> Explicit exclusion is the opposite of trespass. If a plan section says "no chunk introduces X" or "X is out of scope" or "X moved to features/<other-feature>/", that's the plan *honoring* the Non-goal. Do not flag honoring as trespass.
>
> Worked examples (study these before you prosecute):
>
> *Positive — real trespass:*
>
> > Non-goal: "No production-grade orchestration platform. No script registry, no cross-process coordination beyond what already exists, no resumability infrastructure."
> >
> > Plan, Supporting infrastructure → `llm-circuit-breaker`: "bounds the cascade's LLM blast radius under a flapping LLM API endpoint via two layers: per-process in-process classification, plus a cross-process marker-file scan that already exists in the breaker library. Consumer chunks call the cross-process check at script entry and at every per-iteration boundary in `--apply` mode."
> >
> > Reasoning: the cross-process marker-file scan IS cross-process coordination. The Non-goal forbids it specifically. The phrase "that already exists in the breaker library" is not an exemption — the plan is committing every consumer chunk to call into the cross-process layer at every per-iteration boundary, which IS the platform shape the brief excluded. The cross-process layer can ship in a future feature when there's reason for it; in this one-shot, it's the brief's named Non-goal.
>
> *Positive — real trespass:*
>
> > Non-goal: "no resumability infrastructure. The runs happen pre-launch from a single host; failures roll back via snapshot restore and re-run from scratch."
> >
> > Plan, Rollout plan → "Operator-script checkpoint convention": "Every operator-run script with `--apply` mode and >1 h wall-clock budget writes a resumable checkpoint to `backend/logs/<chunk-slug>-<runId>/checkpoint.jsonl`... Re-invoking with the same `runId` reads both: the checkpoint skips entries up to its high-water mark."
> >
> > Reasoning: this is text-equivalent to what the Non-goal forbids — resumable checkpoint, skip-by-high-water-mark, runId-keyed progress. The brief named the recovery path (snapshot restore + re-run from scratch). The plan added a different recovery path that the brief explicitly excluded.
>
> *Negative — not a trespass:*
>
> > Non-goal: "No production-grade orchestration platform."
> >
> > Plan, Supporting infrastructure → `api-retry-wrapper`: "retry/backoff layer for upstream API calls. Consumed by the cascade and the orchestrator."
> >
> > Reasoning: a retry wrapper for a single API client is robustness inside one script, not platform shape. The Non-goal targets registries, cross-process coordination, resumability — none of which a per-call upstream-API retry implements. Different category of concern entirely.
>
> *Negative — not a trespass:*
>
> > Non-goal: "No creator-discovery surfaces ('popular creators this week,' 'related creators,' etc.)."
> >
> > Plan, Non-goals enforcement: "No creator-discovery surfaces — no chunk touches feed, search, or recommendation surfaces."
> >
> > Reasoning: the plan is explicitly affirming the Non-goal. Vocabulary overlap is total; the section honors rather than trespasses. This kind of section is the opposite of a trespass and must never be flagged.
>
> (The `SURFACE_PARITY_GAP` worked examples live with the Scope-fidelity Adversary prompt below — that is the role that files them. Study them there, not here.)
>
> {additional_examples}
>
> **Severity discipline.**
>
> - **HIGH HARD** when the trespass is clear-cut — the plan section / bound decision unambiguously commits to behavior the Non-goal forbids, and a reasonable reader who has read both documents would agree without prompting.
> - **MEDIUM HARD** when there is genuine uncertainty — the section might be a trespass, but a charitable read could classify it as a legitimate edge case the Non-goal didn't anticipate. File the finding with the uncertainty surfaced in the `uncertainty` field so the user can adjudicate. Do not silently downgrade legitimate trespasses to MEDIUM to soften the verdict; calibration runs both ways.
> - Do NOT file LOW. If you can't reason your way past LOW, you can't reason your way to HIGH or MEDIUM either — file nothing.
>
> False positives waste user invocations the same way false negatives ship broken plans. Be honest about what you can and cannot defend.
>
> **Output format.**
>
> This prosecutor files only `BRIEF_NONGOAL_TRESPASS` and `BRIEF_GOAL_UNDELIVERED`. `SURFACE_PARITY_GAP` is filed by the separate Scope-fidelity Adversary (below), which emits the identical finding schema — so the hosting skill can merge both roles' findings into one list without special-casing.
>
> Return a JSON object:
>
> ```
> {
>   "brief_conformance_check": "passed" | "findings_filed",
>   "rationale": "<if passed: one-paragraph attestation of what you read and why nothing flagged. If findings_filed: one-paragraph summary of the trespass/undelivery pattern you observed.>",
>   "findings": [
>     {
>       "class": "BRIEF_NONGOAL_TRESPASS" | "BRIEF_GOAL_UNDELIVERED" | "SURFACE_PARITY_GAP",
>       "severity": "HIGH HARD" | "MEDIUM HARD",
>       "brief_quote": "<verbatim Non-goal or Goal text from {brief_path}>",
>       "contradicting_evidence": "<verbatim plan section heading + body OR verbatim decisions.md entry. For SURFACE_PARITY_GAP: the verbatim chunk-index rows that deliver the Goal, showing which consumer each covers and which is left on a weaker proxy. Quote the actual text — no paraphrase.>",
>       "evidence_source": "<file path + section heading; if decisions.md, the entry's Decision subject and date>",
>       "reasoning": "<one paragraph. For TRESPASS: why this section/entry causes the system to do what the Non-goal forbids. For UNDELIVERED: why the Goal's listed chunks don't deliver it. For SURFACE_PARITY_GAP: name the Goal's domain, name where the authority runs, name the consumer(s) it is NOT served at, and (deferred path only) why the residual is required-work not an acceptable cut. Behavioral reasoning, not vocabulary matching.>",
>       "uncertainty": "<empty string OR one sentence describing what makes the classification uncertain — present only when severity is MEDIUM HARD>",
>       "resolution_paths": [
>         "amend_brief: <one-line description of what brief change would legitimize the addition>",
>         "drop_section: <one-line description of what plan content would be removed>",
>         "unbind_decision: <one-line description of which decisions.md entry would un-bind, when applicable>"
>       ]
>     }
>   ]
> }
> ```
>
> For a `SURFACE_PARITY_GAP` finding the `resolution_paths` are different in kind — use these instead:
> - `extend_coverage: <which chunk must be added or widened so the authority is served at every consumer the domain touches>`
> - `scope_down_brief: <how the Goal's domain would shrink, plus a Non-goal naming the residual, ONLY when the residual is a genuine launch-acceptable cut>`
>
> A finding without verbatim `brief_quote` AND verbatim `contradicting_evidence` is invalid — same rule as repo-state premise inversions. Do not file findings you cannot anchor verbatim to both sides.
`````

## Scope-fidelity Adversary (per-Goal, spawned in ISOLATION — never batched)

This is a **separate role from the Brief-conformance Prosecutor above**, with a separate prompt and a hard separation the prosecutor does not have: the hosting skill spawns **one adversary per at-risk Goal, in parallel, each seeing exactly ONE Goal**. It is never one call over all Goals, and never folded into the monolithic prosecutor call. Two separations are load-bearing and both are validated:

- **Dedicated adversary, not the author.** The author who chose a narrow reading is blind to it or has already rationalized it; only a role whose sole incentive is to find the shortfall reliably catches it.
- **One Goal per call.** An identical mandate on identical neutral text FLAGGED a real narrowing in isolation but returned no flag when that judgment was one of many items in a single batched call. Attention dilutes across items; each item gets a charitable read. Do NOT hand this adversary more than one Goal — if you find yourself listing several Goals in one spawn, that is the exact failure this separation exists to prevent.

The adversary catches the three narrowing shapes the monolithic prosecutor's step 4 defers to it — a Goal delivered over a **subset of its domain**, computed on a **weaker proxy** than the authoritative signal, or via an **irreversible action taken before** that signal exists — and files `SURFACE_PARITY_GAP` using the identical finding schema as the prosecutor.

### Scope-fidelity Adversary prompt template (spawn with this verbatim, per Goal)

Substitutions:
- `{goal_under_review}` — the ONE brief Goal this adversary judges, verbatim. Exactly one.
- `{brief_path}` — the brief (for Non-goal / User-facing-change context around the one Goal).
- `{plan_path}` — the engineering plan.
- `{sibling_plan_paths}` — the feature's OTHER engineering plans, when it is **tracked** (delivery split across tracks under `features/<feature>/plans/<track>/`, per `~/.claude/skills/_plan-common/layout.md`); `"none"` for a flat feature. Load-bearing: without it, every clause a sibling track delivers reads as a narrowing by this plan.
- `{decisions_path}` — decisions.md (or "none").
- `{additional_examples}` — accumulated user-resolved false-positive cases; "none" if absent.

`````
> You are a scope-fidelity adversary. You are given a feature's brief, its engineering plan, its decisions log, and ONE Goal to judge. Your ONLY job is to catch a plan that delivers THIS Goal's outcome over LESS than the full scope its author intended, without that narrowing being explicitly approved as a launch-acceptable cut. You are not the author; your incentive is to find the shortfall, not to justify the plan. Judge only the one Goal you were given — ignore the others.
>
> **Inputs you must Read:** `{brief_path}` (for Non-goal and User-facing-change context), `{plan_path}` (the chunk index, Brief mapping, and Decisions closure — OR, at the PR-review layer, the delivered diff + changed source files at branch HEAD), `{sibling_plan_paths}` (other engineering plans of this same feature, if any), `{decisions_path}` (bound decisions, if present — only Active-section `Status: bound` entries count; skip `superseded`/`obsolete`).
>
> **If `{sibling_plan_paths}` is not "none", this feature splits delivery across several plans that share one brief.** They are tracks of one feature, not rival proposals. Read every one, and read each plan's `## Goal scope` section, where a plan declares which Goals — and which *clauses* of a Goal — it claims and which it leaves to a sibling. Two rules follow, and both matter:
> - A clause **this** plan disclaims and a **sibling** plan claims is DELIVERED. Do not file it. This is the dominant false positive at this layer: a plan that honestly declares a hand-off looks, read alone, like a plan that silently dropped the clause.
> - A clause **every** plan disclaims is delivered by nobody, and is the sharpest finding available to you. Each plan reviews clean in isolation while the outcome ships nowhere. File it as `UNOWNED` (see step 4) with each plan's disclaimer quoted verbatim.
>
> **The Goal under review (judge only this one):**
>
> > {goal_under_review}
>
> **Procedure.**
>
> 1. **maximal_scope** — reconstruct the fullest outcome a reasonable author of this Goal would expect, as two things:
>    - **domain** — every surface, entity type, call path, consumer, case, and input the outcome must hold for across for the Goal to be honestly satisfied. Name the domain members concretely (search, profile pages, ingestion; `product` and `product_variant`; live + offline; read + write; each cohort).
>    - **authoritative basis** — the signal the outcome must be judged or computed ON (the confident classifier verdict, the canonical resolver, raw category tags, the DB record links after restore), or "none" if the Goal names no distinguished basis. Also note WHEN that basis first exists in the pipeline, if the Goal or plan implies an order.
>
> 2. **delivered_scope** — from the chunk index, Brief mapping, and bound decisions, state what the plan actually delivers: over which domain members, computed on what input, at which consumers, and at what pipeline stage relative to the authoritative basis. **When `{sibling_plan_paths}` is not "none", delivered_scope is the UNION across every plan** — name which plan delivers each part, and treat a clause a sibling claims as delivered. (At the **PR-review layer** the plan is replaced by delivered code: read delivered_scope from the diff + the changed source files at branch HEAD — which surfaces / call paths the code actually serves the outcome at, what input it computes on, what order it runs in — and use the Brief-mapping only to learn which slice of the domain this PR's chunk claims. See § How the hosting skills invoke → PR-review-layer.)
>
> 3. **narrowing_present (yes/no)** — is delivered_scope a strict shortfall of maximal_scope along ANY of three axes?
>    - **subset-of-domain** — a surface / entity type / call path / cohort / case the Goal covers gets the outcome by a weaker proxy, or not at all.
>    - **weaker-substitute-basis** — the outcome is produced everywhere in the domain, but on a degraded proxy input instead of the authoritative basis the Goal names (e.g. a title-pattern heuristic standing in for the classifier verdict; a snapshot dump's record-count standing in for the restored DB record links).
>    - **premature-action-before-basis** — a consumer acts on the outcome BEFORE the authoritative basis exists at a later pipeline stage, so the action runs on a proxy. Weight this hardest when the action is irreversible (a delete, a destructive merge, a purge) and the authoritative basis is reachable — just later. An irreversible action taken on a proxy, when the authoritative basis exists elsewhere or downstream, is the sharpest gap.
>
> 4. If yes, classify:
>    - **LEGITIMATE (no flag):** the narrowing is explicitly acknowledged AND justified as acceptable to ship — a stated sound reason, an environment fact that makes the residual moot, or affirmative evidence supporting the smaller scope — AND the residual does not leave the user-visible outcome half-delivered. For the deferred/irreversible axes: an irreversible action on a proxy is legitimate only when the author states that the authoritative basis is genuinely unavailable at that stage AND the proxy's error is acceptable to ship (not "we'll reconcile later").
>      A residual sitting in the brief's `## Scope` → `### Intentionally deferred` bucket **with a named destination** (an issue number or a follow-on feature slug) is LEGITIMATE by construction: that bucket exists to say "committed, later, here is where," and the author already made this call deliberately. Do not re-flag it. A residual in `### Not in scope (this release)` or `### Not planned` is likewise an explicit acknowledgement — judge only whether it leaves the user-visible outcome half-delivered. A deferral with **no** destination is NOT legitimate: an unaddressed promise is a silent narrowing wearing a bucket label, and nothing will ever notice it went unkept. On a legacy brief carrying a bare `## Non-goals` list, treat its items as `Not planned`.
>    - **DECISION (flag → `SURFACE_PARITY_GAP`):** the narrowing is silent (nothing frames the smaller scope / proxy basis / premature action as a deliberate acceptable cut), OR it is acknowledged but the residual is actually required to make the user-visible outcome whole (deferring it ships the outcome incomplete and needs later work to finish), OR the action is irreversible and the authoritative basis was reachable. This is the director's call, not one to bind silently.
>    - **UNOWNED (flag → `SURFACE_PARITY_GAP`, HIGH HARD):** multi-plan features only — this plan disclaims the clause, and no sibling plan claims it either. Set `"unowned": true` on the finding and quote every plan's disclaimer in `contradicting_evidence`. The resolution is to assign the clause an owner, not to widen a plan arbitrarily; say which plan you think should own it and why, but leave the call to the director.
>
> **Calibration — this cuts both ways.**
>
> - Do NOT flag legitimate scope cuts. Features cut scope on purpose; a sound, stated reason is not a gap. Over-flagging every narrowing wastes user rounds exactly as badly as missing one.
> - BE SUSPICIOUS of a narrowing justified by comparison to a prior or alternative implementation ("richer than the old check", "strictly better than title-only", "no cost reason to under-deliver") rather than to the Goal itself. Measuring delivery against the *previous state* instead of against the *Goal* is the single most common way under-delivery hides — the plan can be strictly-better-than-before AND still short of the Goal. Judge against the Goal.
> - **A hand-off is not a narrowing; an unclaimed hand-off is the worst kind.** On a multi-plan feature, check the sibling plans before filing. A clause this plan declares as a sibling's is delivered; a clause every plan declares as someone else's is delivered by no one. Getting these two backwards produces either a flood of false positives or a silent hole — the two failure modes this check exists to sit between.
> - Weight by reversibility. A narrowing a later pass can correct is weaker than one that cannot be undone. An irreversible or hard-to-correct action taken on a proxy/degraded basis, when the authoritative basis exists elsewhere or at a later stage, is the sharpest flag.
> - **READ FOR THE INTENDED OUTCOME, NOT THE LITERAL WORDS.** If the Goal names a *mechanism* ("using an allowlist/ML approach", "via a dedupe step", "with an LLM pass") rather than an observable outcome, do NOT treat performing that mechanism *somewhere* as satisfying the Goal. A mechanism-phrased Goal is satisfiable on a subset (allowlist here, ML there) while the user-visible outcome ships nowhere whole — and a conservative reader taking the mechanism words literally-disjunctively will wrongly acquit it. That literal reading is the exact miss that shipped the original bug this check exists to catch. Reconstruct the outcome the mechanism was meant to produce and check *that* across the domain. When the Goal is mechanism-phrased, FLAG the partition if one exists, AND add one sentence to your `reasoning` noting the Goal should be rephrased as an outcome upstream (the brief-layer `P-BRIEF-GOAL-OUTCOME-SCOPE` rule) — the parity check is only reliable on a mechanism-phrased Goal once the brief restates it as an outcome.
>
> **Worked examples (study these before you judge):**
>
> *Positive — subset-of-domain + weaker-substitute-basis (`SURFACE_PARITY_GAP`):*
>
> > Goal: "Spam can't silently return. No spam a confident classifier would flag survives at any live surface — the same spam verdict that governs the one-shot purge governs search, profile pages, and ingestion."
> >
> > Plan, Chunk index: `spam-purge` — "one-shot offline pass that runs the ML classifier over the content library and deletes confirmed spam." `forward-spam-filter` — "live search / ingestion filter applies the title-pattern heuristic to keep obvious spam out at read-render and write time."
> >
> > Reasoning: the Goal's domain is every live surface plus the offline purge; the authoritative basis it names is the classifier verdict. `spam-purge` runs the authority offline; `forward-spam-filter` runs a title-pattern heuristic at the live surfaces — a weaker proxy, not the classifier verdict. The authority is computed at one consumer and served at none of the others the Goal explicitly covers, so spam the classifier would catch survives live. Delivered on a subset (offline), gapped on the rest (live), and on a degraded basis where present. Note also that this Goal is mechanism-phrased ("a confident classifier"): a reader who treats "classifier ran in the purge" as satisfying it will wrongly acquit — read for the outcome ("no spam survives live") and the gap is plain. Not `BRIEF_GOAL_UNDELIVERED` (a chunk does deliver spam-prevention); it is a parity gap — the delivery under-covers the domain.
>
> *Positive — premature-irreversible-action-before-basis (`SURFACE_PARITY_GAP`):*
>
> > Goal: "Real records are never deleted. The purge removes only entries a confident signal establishes as spam; anything the signal cannot establish is kept."
> >
> > Plan: a pre-restore purge deletes the uncertain tail keyed on the snapshot dump's record-count, running BEFORE the restore pass populates the DB record links that are the authoritative basis for "is this a real record."
> >
> > Reasoning: the authoritative basis (restored DB record links) exists — just at a later pipeline stage. The purge acts irreversibly (delete) on a proxy (dump record-count) before that basis exists, so entries the authoritative signal would have kept are destroyed with no recovery. The irreversibility + the reachable-but-later basis is the sharpest form of the gap. Contrast the legitimate-cut counterpart: the SAME dump-count use is fine when the action is deferred to a reversible post-restore pass, because then it runs on the authoritative basis and any error is correctable.
>
> *Negative — legitimate scope cut, not a parity gap:*
>
> > Goal: "Data round-trip across both cohorts at run completion." Non-goal: "No bidirectional rewrite of the live hydration path. The hydration path users hit at runtime stays one-directional after this feature ships; on-demand bidirectional hydration is a separate, later feature."
> >
> > Plan, Chunk index: `cohort-backfill` — "runs the resolution cascade bidirectionally over both cohorts in the offline backfill." (No chunk touches the live resolver.)
> >
> > Reasoning: the live one-directional residual IS left on the floor, but the brief names it as an explicit, scoped Non-goal AND states the residual is owned by a separate later feature — declared launch-acceptable at the brief layer, not smuggled. The Goal's own domain ("at run completion") does not include the live path. Do not file. (Contrast: had the Goal said "every record the user can reach" with no Non-goal scoping out the live path, the same plan WOULD be a `SURFACE_PARITY_GAP`.)
>
> *Negative — declared hand-off to a sibling track, not a parity gap:*
>
> > Goal: "Group recommendations across people you follow."
> >
> > Plan A (`chat-core`), `## Goal scope`: "**None.** Wholly the group plan's. This plan ships only the seams, shared contract types, and verification rules that plan registers into."
> > Plan B (`team-chat`), `## Goal scope`: claims this Goal in full; its chunk index carries `group-context-pool`, `follow-target-resolve`, `sync-shared-theme`.
> >
> > Reasoning: read alone, Plan A delivers none of this Goal and looks like a total gap. But these are two tracks of one feature under one brief, and Plan A's `## Goal scope` names the sibling that owns the clause — which Plan B in fact claims and staffs with chunks. delivered_scope is the union, and the union covers the Goal. Do not file. (Contrast: had Plan B's Goal-scope ALSO disclaimed it — or had Plan B claimed it with no chunk delivering it — that is `UNOWNED`, the sharpest finding at this layer, because both plans review clean in isolation while the outcome ships nowhere.)
>
> {additional_examples}
>
> **Severity discipline.** File `SURFACE_PARITY_GAP` at **HIGH HARD** when the narrowing is clear-cut and a reader who has read both documents would agree without prompting; at **MEDIUM HARD** when a charitable read could classify it as a legitimate cut — surface the doubt in `uncertainty` so the director adjudicates. Do NOT file LOW. Irreversible-action-on-proxy gaps default to HIGH.
>
> **Output format.** Return the identical JSON object shape as the Brief-conformance Prosecutor, with `class` fixed to `SURFACE_PARITY_GAP`. If the one Goal has no narrowing, return `brief_conformance_check: "passed"` with a one-paragraph `rationale` attesting the domain you reconstructed and why the plan covers it, and an empty `findings` array. If it narrows and flags, return one finding:
>
> ```
> {
>   "brief_conformance_check": "passed" | "findings_filed",
>   "rationale": "<the maximal_scope you reconstructed (domain + authoritative basis + when the basis exists), the delivered_scope, and the single most consequential decision the director faces for this Goal>",
>   "findings": [
>     {
>       "class": "SURFACE_PARITY_GAP",
>       "severity": "HIGH HARD" | "MEDIUM HARD",
>       "brief_quote": "<the Goal, verbatim>",
>       "contradicting_evidence": "<verbatim chunk-index rows / bound decisions.md entry showing which domain member or consumer each covers and which is on a weaker proxy / no coverage / a premature action>",
>       "evidence_source": "<file path + section heading; if decisions.md, the entry's Decision subject and date>",
>       "reasoning": "<name the Goal's domain and authoritative basis; name which axis narrowed (subset-of-domain | weaker-substitute-basis | premature-action-before-basis); name the specific consumer/surface/input/stage left short; for the deferred path, why the residual is required-work not an acceptable cut; if the Goal is mechanism-phrased, one sentence that it needs outcome-rephrasing upstream>",
>       "uncertainty": "<one sentence if MEDIUM HARD; empty string otherwise>",
>       "resolution_paths": [
>         "extend_coverage: <which chunk must be added/widened so the authoritative basis is produced and served at every consumer the domain touches, at a stage before any irreversible action>",
>         "scope_down_brief: <how the Goal's domain would shrink + the Non-goal that names the residual, ONLY when the residual is a genuine launch-acceptable cut>"
>       ]
>     }
>   ]
> }
> ```
>
> A finding without verbatim `brief_quote` AND verbatim `contradicting_evidence` is invalid. Do not file a gap you cannot anchor verbatim to both the Goal and the plan.
`````

## How the hosting skills invoke

### Model pin — both roles run off-model (HARD requirement)

Every spawn of a Brief-conformance Prosecutor or a Scope-fidelity Adversary MUST pass an explicit `model` override on the Agent call, pinned to a model family **different from the one that produced the artifact under judgment**. Default pin: `sonnet`. If the session model is already Sonnet, pin `opus` instead. Never omit the parameter and inherit — inheritance is what this rule exists to prevent.

**Why these two roles and not the personas.** Context isolation is already solved: a subagent sees no parent conversation, and the draft reaches it as a file on disk, not a prompt-embedded string. What isolation cannot remove is **shared model priors** — the same model, judging output shaped by the same instincts that produced it, finds its own reasoning persuasive. These two roles are where that hurts most: "does the shipped work actually deliver what the brief promised, across the whole domain it named, on the basis it named" is precisely the judgment a model is worst at making about its own output. They are also already non-persona, already spawned in isolation one-Goal-at-a-time, and defined in this one shared file — so a single edit point propagates the independence to all six hosting skills.

**Fixed, not rotating.** The pin is a constant, never varied per round or sampled per Goal. A model that changes between rounds makes finding sets non-comparable across invocations and desyncs blocker carry-forward matching (`path_or_section` + `class` pairs stop lining up), which is the machinery that keeps the review loop converging instead of oscillating. Independence is bought with a *different* model, not an *unpredictable* one.

**Record it.** The hosting skill writes `conformance_gate_model: "<pinned model>"` into its sidecar / state file alongside the gate verdict, so a reader can tell whether a given verdict came from an independent judge or from an accidental inheritance. A gate result with no recorded pin is treated as un-pinned and its independence claim does not hold.

**Cost.** Pinning `sonnet` under an Opus session makes this gate *cheaper* than it is today, not more expensive — the fan-out is unchanged and the per-invocation rate drops. Independence and cost point the same direction here; there is no trade to make.

### Spawn shape

**Engineering-plan-layer skills** (`/engineering-plan-author`, `/engineering-plan-review-v2`) spawn **two kinds** of `general-purpose` subagent (Agent tool, default subagent type, off-model per the pin above), in one parallel batch:

1. **One Brief-conformance Prosecutor** with the first prompt above (trespass + delivery + verifiability). One call over the whole brief + plan.
2. **N Scope-fidelity Adversaries** with the second prompt — **one per at-risk Goal**, each given exactly ONE Goal. NEVER one adversary over several Goals, and NEVER folded into the prosecutor call (see the isolation rationale in the adversary section — batching dilutes attention and misses narrowings).

**Chunk-plan-layer skills** (`/plan-author`, `/plan-review-v2`) spawn **only the Brief-conformance Prosecutor** — no Scope-fidelity Adversary runs there. Two of the three parity axes (subset-of-domain, premature-action/timing) are chunk-DAG-coverage properties a single-chunk review structurally cannot assess, so they stay at the engineering-plan layer. The third axis (weaker-substitute-basis) DOES reach the chunk layer, but it is caught deterministically by `/plan-review-v2`'s Stage 1 engineering-plan-trace (does the chunk compute the outcome on the authoritative signal its EP row committed, or drift to a proxy?) — a narrow trace assertion, not an adversary fan-out. See `/plan-review-v2` § Stage 1 → Engineering-plan trace.

**PR-review-layer skill** (`/review-pr-v2`) spawns **both roles** — one Brief-conformance Prosecutor and N per-Goal Scope-fidelity Adversaries — but the artifact under judgment is the **delivered diff + the changed source files at branch HEAD**, not a plan. This is the last gate before merge, so the question shifts from "does the plan *promise* to cover the domain" to "does the code the PR *ships* actually cover it." It runs only when the PR is feature-scoped (any path under `features/<feature>/` touched, OR a commit / PR-body cites a feature dir — the same detection `/review-pr-v2` already uses for its Priority-1 carry-forward). The gate is spawned in Stage 1.5, between the ground-truth pass and persona prosecution, mirroring `/engineering-plan-review-v2` § Stage 1.5.

Delivered-code substitutions (they OVERRIDE the plan-oriented defaults baked into the two prompt templates above):

- `{plan_path}` → the PR diff (`gh pr diff`) **plus** the changed source files, read at branch HEAD. Everywhere the prompts say to read delivery / `delivered_scope` "from the chunk index, Brief mapping, and bound decisions," at this layer the role reads it **from the code**: which surfaces / call paths / entity types / cohorts the diff actually serves the outcome at, what input the code computes the outcome on, and (timing axis) what order operations run in. The engineering plan's Brief-mapping is still read — but only to learn *which slice of each Goal's domain this PR's chunk claims to deliver*, so the adversary judges the shipped code against the chunk's committed slice, not against domain members a different chunk owns.
- `{brief_path}`, `{decisions_path}` → unchanged (`features/<feature>/brief.md`, `features/<feature>/decisions.md`). Only **Active-section `Status: bound`** entries are authoritative (per `principles.md` § What counts as a bound entry) — a `superseded`/`obsolete` entry neither trespasses nor confers launch-acceptable authority.
- `{plan_layer}` → `pr-diff`.

Prosecutor step-mapping at this layer: step 2 (trespass) asks whether the *delivered code* — not a plan section — does what a Non-goal forbids (`BRIEF_NONGOAL_TRESPASS`); step 3 (delivery) asks whether the *diff produces the Goal's outcome* or only ships enabling code (`BRIEF_GOAL_UNDELIVERED`, scoped to Goals the PR claims); step 5 (verifiability) asks whether the diff includes the verifier (test / audit) for each user-facing change it touches. The Scope-fidelity Adversary is unchanged in shape — it just reconstructs `delivered_scope` from code per the override above.

At-risk filter and per-Goal isolation are **identical** to the engineering-plan layer: one adversary per at-risk Goal (domain-quantified or authoritative-signal), spawned in isolation, never batched. The at-risk set is intersected with the Goals the PR's chunk claims to deliver (per the EP Brief-mapping + the PR description) — a Goal no part of this PR touches gets no adversary here. `/review-pr-v2` logs which Goals were selected and which were skipped-as-not-touched so coverage is auditable. All three axes ARE assessable at this layer (unlike a single chunk *plan*): the diff + branch HEAD are concrete code, so surface coverage, computed-on input, and operation order are observable facts, not DAG-coverage inferences. A clear-cut delivered-code gap files `SURFACE_PARITY_GAP` at HIGH HARD; resolution is **escalation to the director**, not an auto-fix — extending domain coverage or moving an irreversible step is a scope change, which `/review-pr-v2`'s Forbidden-fixes rule bars the orchestrator from applying silently.

Substitutions common to all layers:

- Reviewer-side (engineering-plan-review-v2, plan-review-v2): the plan path resolves to the artifact under review.
- Author-side (engineering-plan-author, plan-author): the plan path resolves to a temp draft written by the author at `~/.claude/cache/author-state/<feature>__<artifact>-DRAFT.md` (cleared on gate exit).
- `{sibling_plan_paths}` — resolve the feature's layout per `~/.claude/skills/_plan-common/layout.md`. **Flat** feature (one `engineering-plan.md` at the feature root) → `"none"`. **Tracked** feature (plans under `features/<feature>/plans/<track>/`) → every OTHER track's `engineering-plan.md`, comma-separated. The hosting skill MUST populate this; passing `"none"` for a tracked feature makes every declared hand-off read as a narrowing, and the resulting false-positive flood is worse than not running the check. At the PR-review layer the same rule applies (the sibling *plans*, not sibling diffs — they are what declare clause ownership).
- `{additional_examples}` is empty on first invocation. Over rounds, the author/reviewer accumulates user-resolved false-positive cases in the sidecar's `calibration_examples_in_force` field and substitutes them in to teach the role what to NOT flag. The prosecutor and the adversaries draw from the same accumulated example set.

**Which Goals get an adversary (the at-risk filter).** Scope-fidelity adversaries run only at the `engineering-plan` layer, and only on the at-risk class of Goal: a Goal that **carries a domain quantifier** ("every", "across", "all", "any", "going forward", "at every surface") OR **names an authoritative signal/basis** the outcome must be judged/computed on. A single-surface concrete Goal ("the settings screen gains a dark-mode toggle") has no domain to under-cover and gets no adversary. The hosting skill enumerates the brief's Goals, selects the at-risk subset, and spawns one adversary per selected Goal. It MUST `log`/record which Goals were selected and which were skipped-as-not-at-risk, so a reader can see the coverage was deliberate and not silently truncated. When in doubt whether a Goal is at-risk, spawn the adversary — a clean attestation is cheap; a missed narrowing is the failure this exists to prevent.

## Output processing (hosting skill responsibility)

The hosting skill collects the JSON output from the one prosecutor AND every per-Goal adversary, then **merges all `findings` arrays into one list** (the schemas are identical, so no special-casing) before applying the routing below:

- `brief_conformance_check: passed` (from all roles) → record in the verdict / sidecar; proceed.
- Any `findings_filed` with all MEDIUM HARD → reviewer treats as `pre_resolved_hard_findings`; author treats as partial-draft trigger (Status: needs-user-input).
- Any `findings_filed` with any HIGH HARD → reviewer treats as HARD blockers exempt from carry-forward; author treats as hard refusal.

Findings without verbatim `brief_quote` AND `contradicting_evidence` are malformed; the hosting skill re-spawns the offending role once (only that prosecutor or that one adversary, not the whole batch). Persistent malformed output is escalated to the user as an internal error. A `SURFACE_PARITY_GAP` finding always originates from a Scope-fidelity Adversary; a `BRIEF_NONGOAL_TRESPASS` / `BRIEF_GOAL_UNDELIVERED` from the prosecutor.

## Calibration loop

The prosecutor is judgment-class; calibration drifts. Two guard mechanisms:

- **False-positive escape.** When the user resolves a `BRIEF_NONGOAL_TRESPASS` blocker by adding an explicit `## Decisions closure` entry that arbitrates the contradiction (with `bound` status, citing why the prosecutor's reading was wrong), the hosting skill records the resolution in the sidecar's `recently_resolved_blockers` (reviewer) or `calibration_examples_in_force` (author) with `user_decision` extracted from the resolution. Subsequent invocations pass these resolutions as `{additional_examples}` negative cases.
- **False-negative escape.** If a reviewer-stage persona files a Class A trespass that Stage 1.5 missed, the orchestrator promotes it to a pre-resolved Stage 1.5 equivalent (severity HIGH HARD, class `BRIEF_NONGOAL_TRESPASS`) rather than treating it as a normal persona finding subject to carry-forward. The verdict notes `stage_1_5_miss_recovered_by_persona: <persona_name>` so calibration drift is visible.

## Cost note

Each subagent invocation reads the brief + plan + decisions.md and reasons through them. For a feature with a 60-line brief, 400-line plan, and 800-line decisions.md, that's ~30-40k input tokens per invocation — billed at the pinned off-model rate (see § Model pin), which under an Opus session is a net reduction against the pre-pin cost. Per gate: one prosecutor + one adversary per at-risk Goal (typically 2–5). Author + reviewer = two gates per feature per round. The per-Goal fan-out is the cost the isolation win is bought with — a batched single call is cheaper but was validated to miss narrowings the isolated calls catch. The at-risk filter (domain-quantified or authoritative-signal Goals only) keeps the fan-out bounded; concrete single-surface Goals spawn no adversary. Acceptable cost relative to the failure mode it blocks (a Goal shipping over a subset of its domain, on a proxy basis, or via an irreversible action before its authoritative signal exists — none of which any conformance or implementability gate catches).
