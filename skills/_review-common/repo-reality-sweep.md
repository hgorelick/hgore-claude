# Repo Reality Sweep — codebase-derived discovery stage

Loaded by `/engineering-plan-review-v2` and `/plan-review-v2`. Adoptable by `/engineering-plan-author` and `/plan-author` as a pre-emit pass. Not applicable to `/brief-review-v2` or `/spec-review` (those layers have no chunks and name no code). Not applicable to `/review-pr-v2` — at the PR layer the incumbent *is* the diff's base, and the existing stages already read code.

Sibling to the Structural Sweep (`~/.claude/skills/_review-common/structural-sweep.md`), and deliberately a separate stage rather than three more universes inside it. That file's founding constraint is that its universes are "enumerable from the artifact's structure"; this stage's are enumerable from the **repository**. Folding them in would break that invariant and, more concretely, would break the Structural Sweep's carry-forward rule, which keys inheritance on artifact `section_hashes` — the wrong key entirely for a universe whose inputs are source files.

## The problem this stage exists to solve

Every discovery stage in the suite — Ground Truth, persona prosecution, the Imagined-Implementer, the Class Sweep, the Structural Sweep — enumerates its universe from **the artifact**: gate tables, chunk rows, Goals, Non-goals, section headings, declared contracts. Ground Truth reads code, but only to verify claims the plan already *made*.

The defects that survive to implementation are claims the plan **omits**. Silence is not falsifiable, so nothing fires. A plan can be internally consistent, lint-clean, brief-conformant, liveness-complete and protection-complete while being wrong about the code it will actually touch — and no amount of re-reading it will say so, because the missing information was never on the page.

The evidence is a repeated round-shape, not a single incident. Three engineering plans in one project reached a converged or near-converged verdict and then climbed again: open blockers `3,5,4,4,8,9,2,2,2,0,1,3,4,8,10` on one; `…,0,1,1,5` on a second; a third shipped with 8 chunks, ended with 20, and reached `CLOSED` at round 17 *after* every chunk plan had already been written. A retro of five confirmed scope-parity failures in the same project found **all five caught by reviewing delivered code and none by plan review**, across seventeen rounds of it.

Adding rounds finds more of what the existing stages can already see. This stage changes the enumeration source.

## Validation status

**Validated by hand before encoding** (2026-07-30), on two engineering plans of one feature, 10 chunks, against a plan that had passed 15 review rounds and was lint-clean. Three findings, each one file-read deep, none reachable by re-reading the plan:

- A chunk replaced a shipped writer and silently dropped a timestamp stamp that two live readers keyed off — caught by Universe R.
- A live pre-campaign writer had been enumerated against one invariant and broke three — caught by Universe C.
- A dependency the chunk promoted to primary and scaled ~21× had no identity verification at all — caught by Universe D, and **by neither R nor C**, which is why D exists.

That last point is the reason all three universes ship together. An earlier draft of this stage proposed only R and C. D's finding was the most severe of the three and structurally invisible to both: the chunk neither diverges from that dependency nor is called by it — it *adopts* it. Encoding R and C alone would have reproduced the previous countermeasure's failure at one remove — a validated check with a blind spot in a shape it could not see.

Keep that order for future stages: exercise a proposed check by hand on a live artifact **before** encoding it, and record what it misses alongside what it catches. The predecessor countermeasure to this one was encoded unvalidated, and a fifth instance of its own target class then slipped through in a shape it could not see.

## What makes a universe legitimate here

Same three-part test as the Structural Sweep, with criterion 1 rebased on the repo:

1. **Mechanically enumerable from the repository** — by grep, by import graph, by `git log`/`git blame` — not inferred. "Every existing caller of every symbol this chunk changes" qualifies. "Everything that could interact with this" does not.
2. **One fixed question, asked identically of every cell.**
3. **A GAP is actionable on its own.**

A universe that cannot be enumerated without judgement calls about what to include produces a sweep that returns plausible noise every round and trains the reader to ignore the stage.

## The universes

The three have **distinct enumeration sources**, which is precisely why none substitutes for another: R enumerates from what the chunk **replaces**, C from what **calls** what the chunk touches, D from what the chunk **imports**. A defect visible to one is routinely invisible to the other two.

### Universe R — incumbent divergence

**Members:** for every chunk, the shipped code doing the closest job today — the function, script, or path the chunk replaces, extends, or writes alongside. Enumerate by grepping for the behavior the chunk describes (the table it writes, the API it calls, the column it sets), not by trusting the plan's own file citations, which are exactly what may be stale or absent.

A chunk with no incumbent (genuinely new surface) is `N/A` **only after** the search is recorded — say what you grepped for and found nothing. A silent `N/A` here is the stage's main failure mode: the incumbent that was never looked for reads identically to the incumbent that does not exist.

**The question:** where the plan's design differs from what the incumbent actually does, is the difference deliberate and stated in the plan?

**Read the incumbent's side effects, not only its main path.** The divergence that matters is usually a *secondary* write the incumbent performs and the replacement does not: a cache timestamp, an audit row, a provenance column, a cleanup, a lock release. These are invisible in the plan by construction — the plan describes the primary job.

**Legitimate closures:** the plan states the difference and why; the plan's design matches the incumbent on this point; the difference is confined to behavior no other code observes (name the readers you checked, and how you enumerated them).

### Universe C — caller closure

**Members:** every existing caller of every symbol, file, table, column, or route the chunk changes. Enumerate by grep across the repo, including tests, scripts, and generated/runtime layers — not only the module under discussion.

**The question:** does the plan account for this caller — either by updating it, by establishing that it is unaffected, or by naming it as an accepted residual?

**A symbol enumerated against one invariant is not enumerated against the rest.** When the plan already names a caller for one property (an ungated name write, say), check it against every *other* invariant the plan asserts. Partial enumeration is the common shape, and it reads as coverage.

**Legitimate closures:** the plan updates the caller; the plan states why it is unaffected; a bound decision accepts it as a residual. "It's pre-existing" is a GAP unless the plan says so — the plan's invariant either holds over the column or it does not, and the plan should say which.

### Universe D — dependency guarantee

**Members:** every external primitive, helper, library call, or shipped function the chunk **newly makes load-bearing** — imports and relies on for a correctness property. Enumerate from the chunk's stated design: every named function it calls, every service it fetches from, every predicate it defers to.

Prioritise by the trigger below rather than sweeping every import; a chunk that merely calls an existing logger does not need this cell.

**The question:** read the dependency. What does it *actually* guarantee? Does the plan's use survive that guarantee, at the plan's scale?

**The trigger — run this universe hardest wherever the chunk widens a population, drops a filter, or raises a fallback to primary.** That is the shape in which a tolerable weakness becomes a Goal violation. A dependency correct enough at 300 rows can be flatly wrong at 7,000; a helper acceptable as a last-resort fallback can be unacceptable as the primary source. **Scale is part of the question, not context for it** — a cell that judges the guarantee without judging it at the plan's stated volume has not been judged.

**Why R and C cannot cover this.** The plan does not *diverge* from the dependency — it adopts it. The dependency is not a *caller* — it is a callee. From inside the plan the dependency reads as a solved primitive, which is exactly why no reviewer opens it. This universe is the only one that does.

**Legitimate closures:** the plan states the dependency's real guarantee and its use is within it; the dependency's guarantee is stronger than the plan needs; the plan discloses the shortfall as an accepted residual with the population sized.

### Which layers run which universes

| Layer | Universes |
|---|---|
| engineering-plan | **R**, **C**, **D** — one agent per chunk, all three questions |
| chunk-plan | **R**, **C**, **D** — one agent for the single chunk |
| brief, spec | none — no chunks, no code named |
| PR | none — the diff's base *is* the incumbent, and existing stages read it |

## Batching (deliberate departure from the Structural Sweep)

The Structural Sweep spawns one agent per universe. This stage spawns **one agent per chunk, carrying all three questions**, because all three are answered by reading the same files. Three agents per universe over N chunks would read each incumbent three times for no additional coverage.

The "one fixed question" criterion exists to prevent open-ended judgement, not to prevent batching. Each question stays fixed and each cell is recorded separately; only the reading is shared.

**Chunk selection.** Sweep every chunk on the first round. On later rounds, sweep chunks whose **chunk-index row hash changed**, plus any chunk whose recorded incumbent files changed at HEAD (see carry-forward). Cap at 6 chunk-agents per round; when more qualify, take them in dependency order (earliest-wave first — a wrong premise in an early chunk propagates) and **`log()` which were deferred and to which round**. A silent cap reads as coverage.

## The sweep

One Agent per selected chunk, `model: "sonnet"` (per `principles.md` § Station model policy — reading code against a fixed question is execution-tier work; never inherit the session model). Record `repo_reality_sweep_model: "sonnet"`.

### Agent prompt template

> You are running a **repo reality sweep** on an adversarial review tribunal. This is not a plan review. Your universe comes from the **repository**, not from the plan — you are checking the plan's premises about code by reading that code.
>
> Nobody filed a finding to seed you, and the plan may have passed many clean review rounds. That is expected: this stage exists to catch what the plan does not say, and silence is not something a reader can falsify. An empty result is a real outcome; so is a single CRITICAL against an otherwise-clean plan.
>
> ## Chunk under sweep
> {chunk_slug} — {chunk_description}
> Plan text for this chunk: {chunk_rows_and_referencing_sections}
>
> ## Repo access
> {repo_root}, at HEAD {head_sha}. Read freely. Do NOT edit files. Do NOT run gates or migrations.
>
> ## The three questions
>
> **R — incumbent divergence.** Grep for the shipped code doing this chunk's job today — by the behavior described (the table written, the API called, the column set), NOT by trusting the plan's file citations. Read it, **including its secondary writes**: cache timestamps, audit rows, provenance columns, cleanups, lock releases. Where the plan's design differs from what that code does, is the difference deliberate and stated? If you find no incumbent, record what you grepped for — an unrecorded `N/A` is indistinguishable from not having looked.
>
> **C — caller closure.** Grep every existing caller of every symbol, file, table, column, or route this chunk changes — tests, scripts and runtime layers included. For each: does the plan account for it? If the plan already names a caller for one property, check it against **every other invariant the plan asserts** — partial enumeration reads as coverage.
>
> **D — dependency guarantee.** For every external primitive this chunk **newly makes load-bearing**, open it and determine what it actually guarantees. Does the plan's use survive that guarantee **at the plan's stated scale**? Run this hardest wherever the chunk widens a population, drops a filter, or raises a fallback to primary — that is where a tolerable weakness becomes a violation. Judging the guarantee without judging it at the stated volume is not judging it.
>
> ## Method
> 1. Enumerate each universe's members **from the repo, explicitly, before judging any of them.** Record the grep or import-graph query you used.
> 2. Read the code. Quote it. A cell judged from a filename, a symbol name, or the plan's description of the code is not judged.
> 3. Record every cell, including clean ones. **The clean list is the exhaustiveness proof.**
> 4. A GAP needs the verbatim code, the plan text it contradicts or omits, and a concrete failure scenario naming the reachable state.
> 5. **Quantify where the repo can tell you.** If a gap's blast radius is a row count, a caller count, or a population, and a cheap read-only query or grep settles it, run it and report the number. "Some authors" is a weaker finding than "3,354 of 7,128"; the number is often what decides whether the director fixes or discloses.
> 6. Stay on the three questions. Anything else is a persona finding — one line under `incidental_observations`.
>
> ## Calibration
>
> A false GAP costs the director a round exactly as much as a missed one, and this stage runs against plans that have already passed review — its credibility depends on its gaps being real. Equally: do not soften a real gap to look agreeable. Prefer "CLOSED, and here is the code that closes it" over a hedge; if a cell cannot be settled from the repo, say `UNDETERMINED` and name what would settle it.
>
> ## Output
>
> ```
> chunk: {slug}
> head_sha: {sha}
> incumbent_files_read: [{path}, ...]      # every source file you opened, for carry-forward
> universes:
>   R:
>     enumeration_query: {what you grepped for}
>     cells:
>       - member: {incumbent path + symbol}
>         status: CLOSED | GAP | N/A | UNDETERMINED
>         evidence: {verbatim code + the plan text it meets or misses}
>   C:
>     enumeration_query: {…}
>     cells: [{member: caller path + symbol, status, evidence}, ...]
>   D:
>     enumeration_query: {…}
>     cells:
>       - member: {dependency path + symbol}
>         actual_guarantee: {what reading it established}
>         plan_scale: {the population/volume the plan applies it at}
>         status: CLOSED | GAP | N/A | UNDETERMINED
>         evidence: {verbatim}
> gaps:
>   - universe: R | C | D
>     member: {…}
>     severity: CRITICAL | HIGH | MEDIUM | LOW
>     blast_radius: {measured count where the repo could settle it, else "unmeasured — <what would settle it>"}
>     failure_scenario: {concrete}
>     proposed_fix: {specific}
> clean: [{members checked and found closed}]
> incidental_observations: [{at most 2, one line each}]
> rationale: {one paragraph — confidence the enumeration is complete}
> ```

## Orchestrator merge

1. **Collect** each chunk's matrix. A chunk agent returning no `enumeration_query` for a universe did not run it — re-spawn that agent once.
2. **Promote** every GAP to a finding of the round, at the swept severity, through the same critical-pair retraction as persona findings.
3. **Route** by the standard authority rules. A GAP here is frequently a scope or contract decision rather than an auto-fix — particularly Universe D gaps, where the choice between hardening the dependency, narrowing the population, and disclosing a residual belongs to the director.
4. **Run the three questions on the fix, too.** When the orchestrator or the director applies a remedy, that remedy is new design against the same codebase — and a fix authored without re-reading the *adjacent* incumbent is how a remedy under-delivers. This is not hypothetical: in this stage's own validation run, the Universe-D finding's first proposed fix wrote off 47% of the affected population by stopping at two corroborating signals, while a third signal sat in an adjacent shipped helper (`checkTitleOverlap`) that a single grep would have surfaced. The director caught it, not the pass. Before emitting a fix that adds a check, a filter, or a fallback: grep for whether the codebase already implements the thing you are about to specify, and prefer importing it to redefining it.

## State recording

```
repo_reality_sweep:
  ran: true | false
  repo_reality_sweep_model: "sonnet"
  head_sha: {sha at sweep time}
  chunks_swept: [{chunk_slug, round}]
  chunks_deferred: [{chunk_slug, reason, deferred_to_round}]   # never empty-and-silent
  chunks_inherited_clean: [{chunk_slug, from_round}]
  per_chunk:
    - chunk: {slug}
      incumbent_files_read: [{path}, ...]
      incumbent_files_blob_shas: {path: sha}      # carry-forward key — NOT artifact section hashes
      cells_closed: {n}
      cells_gap: {n}
      cells_na: {n}
      cells_undetermined: {n}
  gaps_total: {n}
```

**Carry-forward rule — keyed on the repo, not the artifact.** A chunk that swept fully clean may be recorded `inherited_clean` next round **only when both hold**: its chunk-index row hash is unchanged, **and** every path in its recorded `incumbent_files_blob_shas` still resolves to the same blob sha at the current HEAD. Either changing re-admits the chunk.

This is the one place where copying the Structural Sweep's mechanism verbatim would be a bug. That stage inherits on artifact `section_hashes`, which say nothing about whether the code moved underneath the plan — and a plan whose premises were verified against a since-changed incumbent is precisely this stage's target. A chunk with no recorded `incumbent_files_blob_shas` is **not** eligible for inheritance; re-sweep it.

## Verdict reporting

```
### Repo reality sweep
- Chunks swept: {n} of {total} at HEAD {sha}
- Deferred to a later round: {chunk} ({reason})
- Inherited clean: {chunk} (round {n}, incumbents unchanged)
- Gaps: {n} ({severities}) — R: {n}, C: {n}, D: {n}
```

An all-clean sweep is reported, not omitted. It is what makes a `CLOSED` verdict mean "the plan's premises about the code were checked against the code" rather than "no reviewer noticed anything."

## Compliance self-check line (hosting skill adds to its pre-verdict gate)

- **Did the Repo Reality Sweep run?** `repo_reality_sweep.ran` is true at any layer that has chunks. `chunks_swept` + `chunks_deferred` + `chunks_inherited_clean` accounts for **every** chunk in the plan, with a reason per deferral and a `from_round` per inheritance. Every swept chunk records a non-empty `incumbent_files_read` and an `enumeration_query` per universe — a universe with no recorded query was not run, regardless of what its cells say. Every `inherited_clean` chunk has stored `incumbent_files_blob_shas` from the inherited round and they still match HEAD. Every GAP appears in the consolidated fix set or in a blocker. **This stage's completion is not contingent on the round having produced findings** — a round with zero persona findings still runs it, and that is the case it exists for.

## Bounding

One pass per chunk per round. A GAP does not spawn a follow-up sweep in the same round; it seeds the Class Sweep normally. No recursion, no inner loop.

## Cost

One execution-tier agent per swept chunk, capped at 6 per round. On a first round over a 6-chunk plan that is 6 agents — the most expensive single stage in the pipeline, and the reason for both the cap and the blob-sha carry-forward. Steady state is near zero on a plan whose chunk rows and incumbents are stable, so the recurring cost lands on exactly the rounds where the plan or the code is actually moving.

Weigh it against what it replaces: the failure mode is an engineering plan reaching `CLOSED` after fifteen rounds and then needing new chunks discovered during implementation. One 6-agent round is cheaper than one wrong chunk graph.
