# Review tribunal — shared principles

Loaded by `/review-pr-v2`, `/plan-review-v2`, `/engineering-plan-review-v2`, `/brief-review-v2`, `/spec-review`, `/vision-review`. The hosting skill defines workflow; this file defines stance.

## Stance

**REPO REALITY IS LAW.** Every finding, fix, and fact MUST be grounded in files that exist *right now, on this branch*. If a persona cannot produce `path:line` + a verbatim quote, the finding does not exist. Stage 1 grounds objective claims; later stages are forbidden from re-prosecuting Stage-1-verified facts AND from filing new findings without producing the same kind of evidence.

**Cite or drop it.** Every finding states `path:line` and quotes the authority it violates (spec, persona rule, project invariant, existing test). Verbatim quote, not summary. Vibes-based findings AND vibes-based acquittals are inadmissible.

**Class > line → class sweep.** A finding names a *line*; a defect lives in a *class*. When filing a finding, identify the class and enumerate the universe (every place the class could live). The fix application then resolves every instance in that universe, not just the named line.

There are two notions of "class," and the review pipeline systematically under-serves the second:
- **Propagated identity** — one root defect at N locations linked by a shared token (a renamed symbol across its callsites, a schema column across the files that read it). The universe is found by grepping the token; every hit is the same wrong thing.
- **Recurring category** — N *independent* defects of the same *kind*, linked by no shared token (four chunks each with a distinct vague criterion, three Goals each failing outcome-scope parity, every mutation missing the same guard). No grep finds these; the only way to enumerate them is an active peer-by-peer scan of the whole artifact.

Personas reliably file **one instance of a recurring category per round** — they flag one vague criterion, scope the universe to its one chunk, and the siblings leak out one per round. The **class sweep** closes this: a dedicated same-round fan-out (one agent per distinct recurring category) that walks the peer-set exhaustively so the whole class is enumerated and fixed in the round it was discovered, not one instance at a time. The mechanism, the sweep-agent template, and the orchestrator merge are defined in `~/.claude/skills/_review-common/class-sweep.md`; every hosting skill runs it as a dedicated stage between finding production and fix application. This is what operationalizes `P-CLASS-SCOPE`'s "the universe must be right the first time — no Round-2 widens."

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
- "the brief Non-goal is too strict" — that's a brief-amendment, not a plan-level override. If a Non-goal genuinely needs relaxing, amend the brief; do not silently absorb the contradiction into `decisions.md`.

LOW severity may include genuine polish ("nit", "minor") when the finding is real but cosmetic. LOW findings are subject to the polish floor in the verdict — they do not block APPROVED if total Tier-2 weight is below floor.

## Cross-artifact authority order

Authority order resolves contradictions between artifacts. **The order is class-aware**: which artifact wins depends on what kind of decision is being contradicted, not which artifact is closer to the chunk plan.

**Class A — Product contract.** The product contract is what is being built, what is explicitly excluded, and what user-facing outcomes are committed to. The brief is where a *feature's* contract lives: every entry under `## Goals`, `## Non-goals`, `## User-facing changes`, and any equivalent product-shape claim in the brief body. Above the brief the same kind of claim lives in a spec's invariants, feature areas, and Non-goals, and above that in vision's mechanism sections, non-goals, and decision ledger. For Class A contradictions, the authority order is:

```
vision.md > specs/<slug>/spec.md (+ its decisions logs) > brief.md > feature decisions.md > engineering-plan.md > chunk plan
```

Each link is read the same way: the lower artifact inherits and never overrides, and a contradiction is an *amendment* to the higher one — landing in the contradicted section explicitly, never absorbed silently below it. That is what `VISION_AMENDMENT_NEEDED`, `SPEC_AMENDMENT_NEEDED`, and `BRIEF_AMENDMENT_NEEDED` each name, one link apart.

A bound entry in `decisions.md` that contradicts a brief Non-goal, fails to deliver a brief Goal, or commits to a user-facing behavior the brief does not list is **not protected by carry-forward**. The right resolution is either (a) amend the brief to legitimize the addition (and re-arbitrate the bound entry against the amended brief), or (b) un-bind the entry and drop the contradicting plan/chunk content. A reviewer-stage finding flagging a Class A contradiction is HARD-blocking and exempt from decisions-log-first retraction.

**Class B — Cross-chunk wiring.** Identifiers, file paths, schema columns, module ownership, transaction boundaries, and other choices about *how* chunks compose. The brief is silent on these by design; the user arbitrates them across review rounds and records the resolutions in `decisions.md`. For Class B contradictions, the authority order is:

```
decisions.md > engineering-plan.md > chunk plan
```

A bound entry wins over a later-round reviewer finding on the same wiring question. This is the existing decisions-log-first carry-forward behavior; it is preserved unchanged for Class B.

**Class C — Chunk-internal detail.** Test names, single-file function names, helper signatures inside one chunk's scope, internal phase splits. For Class C, the chunk plan is authoritative on its own internals; neither `decisions.md` nor `engineering-plan.md` should re-prosecute chunk-internal detail (per `P-EP-IMPL-DETAIL`).

**What counts as a bound entry.** Only a `decisions.md` entry whose `Status:` is `bound` carries the authority above. The log is append-only, so a decision a later entry replaces is never deleted — it is marked `Status: superseded by "<title>" (<date>)` (a newer bound entry now governs the same surface) or `Status: obsolete` (the decision no longer applies at all) and moved to the log's `## Archived (superseded/obsolete)` section. A superseded or obsolete entry does NOT bind, does NOT retract a later finding, and does NOT confer launch-acceptable authority (e.g. it cannot suppress a `SURFACE_PARITY_GAP`). Every scanner reads only the `## Active (bound)` head — or, in a flat log with no split, treats any `Status:` other than `bound` as retired. This is what stops a stale, narrower decision from silently beating the wider promise that replaced it — the exact hazard that accumulates when the same surface is re-arbitrated across many rounds (three "dismissal filtering covers X" entries, each widening the last, all left reading `bound`).

**Classification at finding time.** When a reviewer persona files a finding that names a contradiction, the orchestrator classifies the finding's class before applying carry-forward filters:

- The finding cites a brief Goal, Non-goal, or User-facing-change entry verbatim → **Class A**. Exempt from decisions-log retraction; routes to the user as a HARD blocker (`BRIEF_NONGOAL_TRESPASS` or `BRIEF_GOAL_UNDELIVERED` per the blocker registry).
- The finding cites a cross-chunk identifier, file ownership, schema column, or wiring contract → **Class B**. Subject to existing decisions-log carry-forward retraction.
- The finding cites a chunk-internal detail not named in either of the above → **Class C**. Subject to existing carry-forward and the `P-EP-IMPL-DETAIL` retraction.

When the class is ambiguous (a finding cites both a brief Non-goal and a wiring identifier), classify as Class A — the stricter class wins, because a brief Non-goal trespass dressed in wiring language is still a trespass.

**Why the order is class-aware.** A single rule `decisions.md > brief.md > everything` produces the failure mode where `decisions.md` accumulates platform-additions across arbitration rounds that each contradict a brief Non-goal in isolation. Per-round, no reviewer flags it because the bound entry beats the brief; cumulatively, the engineering plan no longer respects the brief. Splitting the rule by class blocks the accumulation path without re-prosecuting wiring decisions the user has already arbitrated.

## Outcome-scope parity

A brief Goal commits the feature to producing its intended outcome *whole* — over every member of the domain it quantifies over, on the authoritative signal it names, before any irreversible action consumes that outcome. The recurring failure this principle guards against is a plan that passes every conformance and implementability check (the Goal maps to a delivering chunk; the cross-chunk decisions are bound; the plan is implementable) while silently substituting a **narrower** outcome than the author intended. Delivery-scope under-covering outcome-scope is a distinct property from conformance; it needs its own check. The substitution hides along three axes, and all three are the same defect wearing different clothes:

- **Domain.** A Goal quantifying over a domain — "across the catalog", "every live surface", "all real authors", "every Person the user can reach", "going forward" — is delivered over one surface / media type / call path / cohort while the others it also covers are left on a weaker proxy or on nothing.
- **Authoritative basis.** A Goal that names the signal its outcome must be judged on — "the same junk verdict that governs the purge", "judged on the work itself", "on the restored author links" — is delivered on a *degraded proxy* of that signal instead (a title heuristic in place of the classifier verdict; a snapshot count in place of restored DB links).
- **Pipeline timing.** A consumer *acts* on the outcome before its authoritative basis exists at a later stage, so the action runs on a proxy. Weight this hardest when the action is irreversible (a delete, a destructive merge, a purge) and the authoritative basis was reachable — just later. An irreversible action on a proxy, when the real signal exists elsewhere or downstream, is the sharpest gap.

The load-bearing question, usable at the brief layer (are the domain and basis named?), the engineering-plan layer (does the chunk set cover them, on the authoritative basis, before any irreversible step?), and PR review (does the diff serve the outcome everywhere it is claimed):

**Where does the authoritative judgment or computation that produces this outcome run — on what input, at what pipeline stage — and is its result served at every consumer the domain touches, before anything irreversible consumes it?**

Each axis arrives two ways, both defects: *silent* (nothing frames the shortfall as a deliberate cut) and *deferred* (a Non-goal or bound decision defers it, but the residual is required to make the user outcome whole). A deferral is legitimate only when the residual is genuinely acceptable to ship without; "we'll finish it in a follow-up" means the outcome was required and the deferral is itself the defect.

**Read Goals for their intended outcome, not their literal words.** A Goal phrased as a *mechanism* ("using an allowlist/ML approach", "via a dedupe step", "with an LLM pass") is a trap: a reader taking the words literally-disjunctively counts the mechanism as satisfied by performing it *somewhere* (allowlist here, ML there) while the user-visible outcome ships nowhere whole. Reconstruct the outcome the mechanism was meant to produce and check *that*. When a Goal is mechanism-phrased the parity check is unreliable until the brief restates it as an outcome — so mechanism-phrasing is itself a finding at the brief layer (`P-BRIEF-GOAL-OUTCOME-SCOPE`), and the durable fix is upstream, not a cleverer downstream reader.

Mechanical enforcement spans three layers. At the **brief layer**, Goals must name their domain and authoritative signal, and state outcomes not mechanisms, so the parity check has something to measure against (`P-BRIEF-GOAL-OUTCOME-SCOPE`). At the **engineering-plan layer**, the dedicated per-Goal **Scope-fidelity Adversary** files `SURFACE_PARITY_GAP` across all three axes, spawned in isolation — one adversary per at-risk Goal, never batched, because a shortfall an isolated judgment catches is missed when many items share one attention window. At the **chunk-plan layer**, only one axis reaches: the weaker-substitute-basis axis, caught deterministically by `/plan-review-v2`'s Stage 1 engineering-plan-trace (does the chunk compute the outcome on the authoritative signal its EP row committed, or drift to a proxy?) and prevented at write time by the matching `/plan-author` drafting rule — the subset-of-domain and pipeline-timing axes are chunk-DAG-coverage properties a single-chunk review structurally cannot assess, so they stay at the engineering-plan layer. At **PR review** — the last gate before merge, where the artifact under judgment is delivered *code*, not a plan — the parity question runs two ways: a dedicated **Stage 1.5 Brief-conformance gate** spawns the per-Goal Scope-fidelity Adversary against the *diff* for at-risk Goals (domain-quantified or authoritative-signal), reconstructing each Goal's domain + authoritative basis and checking whether the delivered code serves the outcome at every consumer the domain touches, on the authoritative input, before anything irreversible consumes it; and every persona applies the mechanism-vs-outcome lens (read below) to the concrete single-surface Goals the at-risk filter excludes. Handling parity at the PR layer as an informal per-persona lens alone is what lets a subset-of-domain gap ship and be caught reactively across many later plan-layer rounds — the failure this dedicated gate exists to prevent. See `/review-pr-v2` § Stage 1.5.

## Sibling-plan co-delivery

A feature has one brief and may have more than one engineering plan (`~/.claude/skills/_plan-common/layout.md` § tracks). The tracks **decompose one feature for implementation; they are not independent releases.** The feature is delivered by implementing **all** of its plans, and reaches users only through a deliberate whole-feature deploy — nothing goes live on a merge to `main`. So there is no reachable state in which one track is live and its sibling is not, and no cross-track intermediate, orphan, integration, or go-live state to guard.

This retires a whole class of finding **between sibling tracks** — file none of these:

- A track that delivers **no brief Goal on its own** is not an undelivered-Goal defect. It ships shared infrastructure its siblings consume; the Goals are delivered and verified in the sibling tracks.
- A chunk, export, module, column, event, or seam whose only consumer is a **sibling track** is not orphaned, inert, or dead scaffolding. Its consumer is real; it lives in a plan not under review.
- Cross-track **consumption and wiring** ("who calls this?", "who repoints the sibling onto this core?") is **inherent in the siblings being built** — done and verified in each sibling's own review/execute cycle. It is never a separate task, issue, DAG node, feature flag, or cross-track gate; **its absence is correct by design, not a gap.**
- No orphan / integration / go-live / rollout-intermediate-state mitigation is required between sibling tracks. A director may record combined-release *intent* in `decisions.md`; the reviewer never manufactures it as a finding, `OPEN_QUESTION`, or gate.

**What still holds — coverage and contracts, not shipping.** Delivered scope is the **union** of the sibling plans (`/scope-check`, `~/.claude/skills/_review-common/brief-conformance-prosecutor.md`): a Goal **no** sibling delivers is a real gap, and a clause **every** sibling disclaims is unowned — both valid findings. A cross-track **contract** — a shared type, constant, or predicate two tracks import — must stay consistent; drift between one track's export and another's import is a real finding. The principle removes the *shipping / orphan / integration* concern, not the *coverage* or *contract-consistency* concern.

Within a **single** plan, chunk-to-chunk sequencing, expand-then-contract, and no-dead-scaffolding rules are unchanged — a chunk with no consumer **in its own plan** is still dead scaffolding, because a same-plan consumer would exist if the chunk were live.

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

## Station model policy

The pipeline's design premise is compute arbitrage: expensive-model judgment is spent once, at plan time, so cheaper models can do the mechanical and prosecutorial work reliably. This table is the single authority for which model tier each station runs on. Hosting skills pass the pinned tier as an explicit `model` param on every Agent spawn — **never inherit the session model at a pinned station** (the session model may be the most expensive tier, and un-pinned fan-outs at that tier are the pipeline's dominant cost).

| Station | Tier | Mechanism | Why this tier suffices |
|---|---|---|---|
| Ground-truth verification batches (V1–V5 checks) | `haiku` | Agent spawns per `_author-common/ground-truth-protocol.md` (procedure step: "Execute verification calls") | Existence + verbatim-quote checks are mechanical Read/grep; fail-action *decisions* stay in the author's main thread |
| Persona prosecution (review-side Stage 2 + re-pass) | `sonnet` | Agent spawns per `_review-common/agent-prompt.md` § Model pin | Prosecution follows a fixed template against inlined rules; quality regressions are observable via the exclusion-challenge log and stage-1.5 miss recovery |
| Self-prosecution personas (author-side) | `sonnet` | Agent spawns per `_author-common/self-prosecution-protocol.md` § Model pin | Same template, same observability |
| Brief-conformance Prosecutor + Scope-fidelity Adversaries | `sonnet` (off-model; `opus` if session is Sonnet) | Per `_review-common/brief-conformance-prosecutor.md` § Model pin | Independence from the authoring model's priors is the point; cost drop is a side benefit |
| Imagined-Implementer dry-run | `sonnet` | Agent spawn in `/engineering-plan-review-v2` | It simulates the *execution-tier* implementer — running it on the execution-tier model makes the simulation more faithful, not less |
| Class Sweep (sibling enumeration) | `sonnet` | Agent spawns per `_review-common/class-sweep.md` § The sweep | Walking a declared peer-set against a fixed invariant is prosecution-class work against a fixed template; the peer-set-challenge step is procedural, not arbitration |
| Structural Sweep (unseeded matrix completion) | `sonnet` | Agent spawns per `_review-common/structural-sweep.md` § The sweep | Asking one fixed question of every cell in a mechanically-enumerated universe is the most template-bound station in the pipeline; the judgment lives in the universe definition, which the host skill fixes |
| Repo Reality Sweep (codebase-derived) | `sonnet` | Agent spawns per `_review-common/repo-reality-sweep.md` § The sweep | Reading shipped code against three fixed questions is execution-tier work; the judgment lives in the universe definitions and the trigger, both fixed by the host skill |
| Chunk implementation (`/execute-plan`) | `sonnet` (intended) | Inline station — the tier is set at invocation; interactive runs ride the session model | The passed chunk plan is the contract that de-skills execution |
| EP authoring, brief/spec authoring, `/solve-blockers` research, orchestrator fix-application | session model (Opus/Fable) | Main thread — no pin | Factoring and arbitration judgment is where the expensive model earns its cost; these decisions ripple through every downstream chunk |

Recording: every skill that spawns pinned agents records the model used in its state file / sidecar (`persona_model`, `conformance_gate_model`, `ground_truth_model`, `class_sweep_model`, `structural_sweep_model`) so an accidental inheritance is auditable. A recorded value that matches the session's expensive tier at a pinned station is a defect, not a preference.
