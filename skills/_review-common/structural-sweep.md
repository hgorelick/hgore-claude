# Structural Sweep — unseeded matrix-completion stage

Loaded by `/engineering-plan-review-v2`, and adoptable by `/brief-review-v2`, `/plan-review-v2`, `/review-pr-v2`, `/spec-review`. The hosting skill names which universes apply at its layer and where the stage sits; this file defines the mechanism.

## The problem this stage exists to solve

Every other discovery path in the review pipeline is one of two kinds:

- **Mechanical verification** (Ground Truth) — takes a claim the artifact *makes* and checks it against reality. It can only reach claims that were written down.
- **Judgment recall** (persona prosecution) — a reviewer reads the artifact and notices what is wrong. It can only reach what a reader happens to notice.

The Class Sweep multiplies the second: given one instance a persona filed, it closes the whole class. That is its stated design — it is a finding-**expansion** pass, seeded from surviving findings. Which means **a defect class with zero filed instances is invisible to it.** Multiplying zero recall gives zero coverage, and no compliance check fires, because there was no seed to be incomplete about.

This is not a hypothetical. A real round shipped a `CLOSED`-adjacent verdict while carrying a CRITICAL defect that made an irreversible launch step permanently unreachable: a gate condition whose failure state could never be exited. Three personas read the artifact in full and none filed it; the Class Sweep therefore never looked at the gate table; the Imagined-Implementer had simulated a different chunk. It surfaced only when someone later enumerated *every gate condition* and asked the same question of each. That enumeration cost one agent.

The Structural Sweep is that enumeration, promoted to a stage: **an unseeded, exhaustive pass over a universe derived from the artifact's own shape, asking one fixed question of every cell.** It finds classes nobody filed.

## What makes a universe legitimate

This stage only works because its universes are **enumerable from the artifact's structure**, not from a reviewer's imagination. That constraint is what keeps it convergent, and it is the difference between this stage and a useless "think harder about everything" pass.

A universe qualifies when all three hold:

1. **Mechanically enumerable.** The members can be listed by reading a table, a section, a DAG, or a diff — not inferred. "Every row in the Manual gates table × every condition that row asserts" qualifies. "Every way this could go wrong" does not.
2. **One fixed question, asked identically of every cell.** The question is a property, not an opinion: *is every failing state exitable?*, *does this action carry this protection?*, *does this contract have both a writer and a reader?* A cell's answer must be defensible without weighing tradeoffs.
3. **A GAP is actionable on its own.** Finding one tells the director something to change, without needing the rest of the matrix as context.

If a proposed universe fails any of the three, do not add it. An open-ended universe produces a sweep that returns plausible noise every round and trains the reader to ignore the stage.

## The universes

### Universe L — condition liveness (run wherever the artifact asserts conditions that must hold)

**Members: every condition the artifact asserts must hold — NOT only the ones written as gates.** The defect this universe targets is *a required condition that can never be satisfied*, and that shape is indifferent to which section heading it sits under. Enumerate all of:

- every manual-gate table row × every condition it asserts;
- every scripted or automated gate (completion checks, post-run audits, coverage gates) × every condition;
- every CI gate the artifact names;
- every condition in a capture-time / pre-commit / pre-merge re-verification set;
- every chunk's **acceptance criteria**;
- every **Non-goal enforcement clause** that asserts something is prevented;
- every **cross-chunk contract invariant** the artifact says must hold;
- every **Risk mitigation the artifact claims closes the risk** (an unsatisfiable mitigation is an open risk wearing a closed label).

Scoping this universe to gate-table rows alone was an early draft's mistake and would have left the identical logical defect uncaught whenever it happened to be phrased as an acceptance criterion or an enforcement clause instead. Membership is decided by *"is this an assertion that must hold?"*, never by the heading it appears under.

**The question, asked of every member:** is there a reachable state in which this condition can never be satisfied — no matter how many re-runs — with no specified remedy? Equivalently: from every failing state, name the terminating path to a passing state. A failing state with no named exit is an **absorbing state**; when the condition blocks an irreversible or one-shot step, that is a CRITICAL.

**Mandatory trace procedure — do this per member; do NOT judge a condition by reading only its own sentence.** This is the step the universe lives or dies on. The defect that motivated this stage was invisible to three careful readers precisely because it was *not* visible in the condition's own text — the condition read as prudent, and only became unsatisfiable through two other sections. So for every member:

1. **Enumerate every term the condition references** — every named predicate, marker, flag, column, state, count, or defined phrase.
2. **Locate each term's definition** wherever it lives in the artifact, and quote it. A term used in a condition but defined three sections away is the normal case, not an edge case.
3. **Find every other step or path that writes, sets, or influences that term's inputs** — especially steps the artifact *requires* to run before the condition is evaluated. A required earlier step that forces a term to a particular value is the single most common source of an absorbing state.
4. **Only now** judge satisfiability, against the term's real definition and everything that sets it — not against the condition's plain-language reading.

A cell judged without steps 1–3 is not judged. If you find yourself clearing a condition because "it looks reasonable," you have skipped the procedure.

**Why this universe is the flagship.** A required condition is a liveness obligation, and liveness is exactly the property that reads as safety when checked one condition at a time. Each one looks prudent in isolation; the defect appears only when you ask whether it is satisfiable from every reachable state, given every other thing the artifact requires. Reviewers reliably read such conditions as protections rather than as obligations, which is why this universe has the worst recall-to-consequence ratio in the pipeline.

**Legitimate closures** (a cell is CLOSED, not a GAP, when any hold): a re-run genuinely produces a different outcome because the cause was transient; a named operator action resolves it; an exempting marker or disposition reaches it; a **disclosed** accepted residual covers it. "The operator would work something out" is a GAP — the remedy must be specified.

### Universe P — protection parity (run wherever the artifact defines several paths to the same dangerous effect)

**Members:** every protection the artifact *itself* treats as required for a dangerous action × every path that reaches that effect.

**Derive the protection list inductively from the artifact, never from a generic checklist.** Read what guards the artifact already specifies anywhere, and treat that set as the obligation: atomicity, ordering constraints, pre-action recovery points, input validation, refusal-to-override-a-prior-decision, pre-action review or confirmation, evidence recording, post-action observability, concurrency bounds, fail-closed defaults. A generic security checklist produces false gaps and misses the artifact's own invariants.

**The question, asked of every cell:** does this path carry this protection? Mark **HAS** (quote the specifying text), **N/A** (structurally inapplicable — say why in a clause), or **GAP**. Be strict about the distinction: *"the operator would not do that"* is a GAP; N/A means the protection **cannot** apply, as input validation cannot apply to a path that takes no input.

**Why this universe.** When a new path to an existing dangerous effect is added — an operator flag beside an automated pass, a second write route, a bypass for a special case — it inherits the *shape* of its model but not necessarily the *protections*, and each missing protection surfaces as its own separate round. The matrix closes all of them at once.

**Membership stability (mandatory — this universe's known weakness).** Universe P's members are *inductively derived* rather than read off a fixed structure, which makes it the one universe whose membership can drift between rounds on an unchanged artifact — and an unstable universe produces arguable findings that train the reader to ignore the stage. So the derived protection list is **recorded in state and carried forward as the baseline**: round N+1 is handed round N's list and may only *add* to it (with a one-line justification per addition), never silently drop or re-derive from scratch. A protection that genuinely no longer applies is removed explicitly, with its reason recorded. Two consequences: the universe becomes auditable across rounds, and a round cannot quietly narrow the obligation set to make a GAP disappear. If the handed list is empty (first run), derive it and record it as the baseline.

### Universe A — acceptance-criterion observability (chunk-plan layer)

**Members:** every acceptance criterion the chunk plan states.

**The question:** does this criterion name **how it is observed** — a specific test, a command whose output settles it, a gate, or an explicit manual check with what the checker looks at? A criterion that cannot be observed cannot be met or missed, so it is decoration; an implementer will mark it done on their own reading.

Distinct from Universe L, which asks whether a criterion is *satisfiable*. This asks whether satisfaction is *detectable*. A criterion can pass L and fail A.

**Legitimate closures:** the criterion names its observation; or it restates a criterion observed elsewhere in the same plan (name that one). "It will be obvious" is a GAP.

### Universe T — changed-surface test coverage (PR layer)

**Members:** every public surface the diff adds or changes — exported function, endpoint, resolver, mutation, hook, CLI flag, schema field.

**The question:** does the diff include a test that exercises this surface's changed behavior — not merely that it compiles or is imported? Judge the assertion, not the file's existence.

**Legitimate closures:** a test in the diff asserts the changed behavior; an existing test already covers it and the diff does not change what it asserts (name the test); the surface is a pure re-export or rename with no behavior change.

### Universe Z — mutation authorization (PR layer)

**Members:** every mutation, write path, or state-changing operation the diff adds or changes.

**The question:** does this path perform its authentication and authorization checks, in the project's established pattern, before it mutates? Read the project's own convention (its `CLAUDE.md`, a sibling resolver) and judge against that, not a generic notion of auth.

**Why this is a universe and not a persona's job.** Auth is the canonical case of a check that is *individually* obvious and *collectively* forgotten: a reviewer reads a new mutation, sees the surrounding pattern, and assumes it applies. Enumerating every mutation and asking once per mutation is the only way the omission surfaces. A GAP here is high-severity by default.

### Candidate universes not yet adopted

These plausibly pass the three-part test but have not been validated in a real round; adopt one only after checking it against the test and after deciding it is not already covered by an existing stage.

- **engineering-plan:** cross-chunk contract closure — every declared contract has a named writer *and* a named reader. DAG integrity — every chunk reachable, every dep satisfiable in the stated order.
- **chunk-plan:** declared-ownership closure — every file the chunk writes is declared in its Owns list. (Check first whether the host's Stage 1 trace already covers this; do not duplicate a stage.)
- **brief:** Non-goal enforceability — every Non-goal is either test-assertable or reasoned as a scope boundary. (Goal × domain parity is already covered exhaustively by the Stage 1.5 per-Goal adversaries; do **not** duplicate it here.)
- **spec:** every stated invariant × a named enforcement site.

### Which universes each layer runs

| Layer | Universes |
|---|---|
| engineering-plan | **L** (condition liveness), **P** (protection parity) |
| chunk-plan | **L** (over the chunk's acceptance criteria and any gate it defines), **A** (observability) |
| PR | **L** (over guards/assertions in the diff — a permanently-unsatisfiable or dead guard), **T** (changed-surface tests), **Z** (mutation authorization) |
| brief, spec | none adopted — Stage 1.5 already covers the brief's Goal domain exhaustively, and no spec universe is validated |

Universe L is the one universe that applies at every layer where the artifact asserts conditions, and it carries its mandatory trace procedure at every layer. At the PR layer the trace runs over code rather than prose: resolve each term the guard references to its definition, and find every path that sets it.

## Where the stage sits

- **After** Ground Truth (so verified facts are available and not re-derived) and after the finding-producing stages.
- **After any short-circuit that would abort the round** — a RESET corroboration short-circuit, a baseline-red stop — for exactly the reason the Class Sweep sits there: a round that is about to stop does not pay for a sweep. This stage is spawned at the same point in the pipeline as the Class Sweep and is subject to the same cost-avoidance rule; it is *not* exempt, and it is **not** run concurrently with persona prosecution even though being unseeded would technically allow it. Consistency with the sibling stage and not paying on an aborted round both beat the wall-clock saving.
- **Alongside the Class Sweep**, and independent of it: the Class Sweep expands what was found, this stage discovers what was not. Neither is a substitute for the other, and **this stage runs even when the round produced zero findings** — that is the whole point, and it is the one respect in which it differs from its sibling.
- **Before** the orchestrator consolidates, so a GAP is fixed or escalated in the same pass as everything else.
- **Skipped** only when the layer has no qualifying universe (e.g. an artifact with no gates skips Universe L). Record the skip and its reason; never skip silently.

## The sweep

One Agent per universe, `model: "sonnet"` (per `principles.md` § Station model policy — matrix completion against a fixed question is execution-tier work; never inherit the session model). Record `structural_sweep_model: "sonnet"`.

### Agent prompt template

> You are running an **exhaustive structural sweep** on an adversarial review tribunal. This is not a review — it is matrix completion. You were given a universe derived from the artifact's own structure and ONE fixed question. Ask that question of every cell and report the answers. You are not looking for what seems important; you are filling in a table.
>
> Nobody filed a finding to seed you. That is deliberate: this stage exists to catch defect classes no reviewer noticed, so an empty result is a real and useful outcome — and so is a single CRITICAL in a table of otherwise-clean cells.
>
> ## Universe
> - **Members:** {universe_definition}   # how to enumerate them from the artifact
> - **The fixed question:** {the_question}
> - **What counts as a legitimate closure:** {closure_criteria}
> - **Reference for what "closed" looks like:** {known_good_reference}   # an in-artifact example already solved correctly, or "none"
>
> ## Artifact access
> {artifact_access}
> {layer_notes}
>
> ## Method
> 1. **Enumerate the universe first, before judging anything.** List every member explicitly. If you cannot enumerate it mechanically from the artifact's structure, stop and say so — that means the universe was mis-specified, and a sweep over a universe you inferred is worthless.
> 2. **If the universe specifies a mandatory trace procedure, perform it for every member before judging that member** — and record what you traced in the cell's `traced` field. Do not judge a member by reading only its own sentence. A universe that carries a trace procedure carries it because the defect it targets is invisible in the member's own text; skipping the trace turns this stage back into the shallow read that already missed the defect.
> 3. Ask the fixed question of **every** member. Judge each on the evidence you traced; do not assume uniformity, and do not skip a member because it resembles one you just cleared.
> 4. Record every cell. A GAP needs verbatim evidence and a concrete failure scenario. A closure needs the specific reason it closes — name the exit path, the exemption, or the disclosure, quoted.
> 5. Report members you checked and found clean. **The clean list is the exhaustiveness proof**; a sweep reporting gaps with no clean cells did not walk the universe.
> 6. **Record `sections_read`** — every section of the artifact you actually read to reach your judgements, including sections you reached only through a trace (a term's definition, a required earlier step), not merely the sections the members live in. A later round uses this list to decide whether it may inherit your clean result; an incomplete list makes that inheritance unsafe, so under-reporting here silently breaks a future round.
> 7. Stay on the fixed question. A different defect you happen to notice is a persona finding, not a cell in this matrix — mention it once under `incidental_observations` and do not let it pull the sweep off the question.
>
> ## Calibration
>
> This cuts both ways, hard. A false GAP costs the director a round exactly as much as a missed one, and this stage's credibility depends on its gaps being real — it runs every round, so a stage that cries wolf gets ignored precisely when it is right. Equally: do not soften a real gap to look agreeable. The defect this stage exists to catch was severe enough to make an irreversible step permanently unreachable, and three careful readers missed it.
>
> Prefer "CLOSED, and here is the exit path I found" over a hedge. If a cell's status genuinely cannot be determined from the artifact, say `UNDETERMINED` and name what would settle it — do not round it to either side.
>
> ## Output
>
> ```
> universe: {name}
> universe_enumerable: true | false
> members_enumerated: {integer}
> sections_read: [{section heading}, ...]          # every section you read, trace targets included
> protection_baseline_used: [{protection}, ...]    # Universe P only: the list you were handed
> protection_baseline_additions: [{protection, justification}, ...]   # Universe P only: what you added, and why
> cells:
>   - member: {…}
>     traced: {for a universe with a trace procedure — the terms you resolved, where each was defined, and the steps you found that set them; empty otherwise}
>     status: CLOSED | GAP | N/A | UNDETERMINED
>     evidence_or_reason: {verbatim quote for CLOSED/GAP; one clause for N/A; what would settle it for UNDETERMINED}
> gaps:
>   - member: {…}
>     severity: CRITICAL | HIGH | MEDIUM | LOW
>     failure_scenario: {concrete — the reachable state, and what breaks}
>     proposed_fix: {specific change; mirror the known-good reference where one exists}
> clean: [{members checked and found closed}]
> incidental_observations: [{at most 2, one line each, off-question}]
> rationale: {one paragraph — confidence the enumeration is complete, and anything undeterminable}
> ```
>
> Do NOT edit files. Do NOT run gates. Return only the matrix.

## Orchestrator merge

1. **Collect** each universe's matrix. Sanity-check exhaustiveness: `members_enumerated` should equal `len(cells)`; a matrix with fewer cells than members did not complete — re-spawn that one agent once. `universe_enumerable: false` is a valid terminal outcome and means the host skill's universe definition needs fixing; surface it as a workflow defect, not as a clean result.
2. **Promote** every GAP to a finding of the round, at the sweep-judged severity, and run it through the same critical-pair retraction the persona findings went through.
3. **Route** GAPs by the same authority rules as any other finding. A GAP that requires amending an upper-authority artifact is a blocker for the director, not an auto-fix — a structural gap is frequently a scope or contract decision.
4. **Do not** let `UNDETERMINED` cells silently vanish. Each becomes either a resolved cell (after a cheap check the orchestrator can run itself) or a `POLISH_PLATEAU`-class note naming what would settle it.

## State recording

```
structural_sweep:
  ran: true | false
  structural_sweep_model: "sonnet"
  universes_run: {n}
  universes_skipped: [{universe, reason}]                    # never empty-and-silent
  universes_inherited_clean: [{universe, from_round}]        # see carry-forward rule below
  universes:
    - universe: {name}
      members_enumerated: {n}
      sections_read: [{section heading}, ...]   # EVERY section the sweep actually read to judge its cells,
                                               # including sections reached only via the Universe-L trace
                                               # procedure (term definitions, required earlier steps) —
                                               # not merely the section the members live in
      protection_baseline: [{protection}, ...]  # Universe P only: the carried-forward derived list
      protection_baseline_additions: [{protection, justification}, ...]
      cells_closed: {n}
      cells_gap: {n}
      cells_na: {n}
      cells_undetermined: {n}
      gaps_promoted_to_findings: {n}
  gaps_total: {n}
```

**Completeness identity:** `universes_run + universes_skipped + universes_inherited_clean` must account for every universe the host skill declares. An inherited-clean universe is neither "run" nor "skipped", so it needs its own bucket or the compliance check cannot tell a deliberate inheritance from an omission.

**Carry-forward rule.** A universe that returned all-clean may be recorded `inherited_clean` next round rather than re-run — but **only when the section hash is unchanged for every section in that universe's recorded `sections_read`**, not merely for the section its members live in. This distinction is the whole safety of the optimization: a condition's satisfiability routinely depends on a term defined elsewhere and on a required step elsewhere again (that is what the Universe-L trace procedure exists to surface), so a round that edits only the *definition* section while leaving the gate table untouched has changed the answer without changing the obvious hash. Inheriting clean on the narrow hash would silently stop re-checking a condition whose truth value just flipped — a delayed recurrence of the exact failure this stage was added to catch. If `sections_read` was not recorded for a universe, it is **not** eligible for inheritance; re-run it.

## Verdict reporting

```
### Structural sweep
- Universe: {name} — {members_enumerated} members: {cells_closed} closed, {cells_gap} gap, {cells_na} n/a, {cells_undetermined} undetermined
- Skipped: {universe} ({reason})
- Gaps promoted: {n} ({severities})
```

An all-clean structural sweep is reported, not omitted. It is the evidence that the universe was covered, and it is what makes a `CLOSED` verdict mean something stronger than "no reviewer noticed anything."

## Compliance self-check line (hosting skill adds to its pre-verdict gate)

- **Did the Structural Sweep run every applicable universe?** `structural_sweep.ran` is true whenever the layer has at least one qualifying universe; `universes_run` + `universes_skipped` + `universes_inherited_clean` accounts for **every** universe the host skill declares, with a reason recorded per skip and a `from_round` per inheritance; every run universe records `members_enumerated`, a non-empty `cells` list, and a non-empty `sections_read`; every universe carrying a trace procedure has a non-empty `traced` field on each cell (a cell with an empty `traced` was judged on the member's own text alone — re-run that universe); Universe P records the `protection_baseline` it was handed plus any additions with justifications; and every GAP appears in the consolidated fix set or in a blocker. A universe recorded `inherited_clean` without a stored `sections_read` from the inherited round is non-compliant — inheritance is unverifiable without it, so re-run. **This stage's completion is NOT contingent on the round having produced findings** — a round with zero persona findings still runs it, and a verdict that reports no structural sweep on a gated artifact is incomplete regardless of how clean the rest of the round looked.

## Bounding

Exactly one pass per universe per round. A GAP does not spawn a follow-up sweep in the same round; the class it belongs to is picked up by the Class Sweep's seed grouping (a promoted GAP is a finding, so it seeds normally). No recursion, no inner loop — the same one-pass cap the Class Sweep and the focused re-prosecution carry.

## Cost

One agent per universe per round, at the execution tier. On the engineering-plan layer that is typically two (Universe L, Universe P), rising to four if the host adopts contract-closure and DAG-integrity. The `inherited_clean` carry-forward keeps steady-state cost near zero on artifacts whose gated sections are stable, so the recurring cost concentrates on exactly the rounds where the artifact is actually changing. Against the failure mode — an artifact reaching a `CLOSED` verdict while carrying a defect that makes its terminal step unreachable — this is the cheapest stage in the pipeline.
