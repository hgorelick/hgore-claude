# Feature-surface gate — catching feature-level bundling (shared)

Loaded by `/brief-author`, `/brief-review-v2`, `/engineering-plan-author`, `/engineering-plan-review-v2`. Fills the layer gap above the chunk-level bundling guards: the Concern gate, halved-work test, and Chunk-surface estimator catch a *chunk* that bundles too much, but nothing above them catches a *brief* that bundles two features or an *engineering plan* whose aggregate DAG is feature-factory-sized. A bundle at those layers doesn't fail loudly — it spins: the decision surface is too large for review rounds to close, so each round surfaces more arbitrations than the previous round retired.

## Calibration evidence (why the thresholds sit where they do)

Observed in this pipeline's own state files (July 2026): three features stuck at EP review rounds 14–26 with open blockers *accumulating* (14–15 open `OPEN_QUESTION`s each), while their chunk-level reviews converged normally in rounds 1–3 — the pathology lives strictly above the chunk layer. The largest feature that *did* converge (~18 chunks) still paid 17 EP rounds to land, so raw size predicts cost even when it doesn't predict divergence. Two implications baked into this gate: the discriminator is **decision-surface size and blocker trajectory**, not chunk count alone; and even a feature the director chooses to keep whole should make that choice *explicitly*, with the cost visible.

## Blocker classes filed

`BRIEF_SCOPE_BUNDLE`, `FEATURE_SURFACE_EXCESS`, `FEATURE_NONCONVERGENCE` — definitions, resolutions, and verdict-gate effects in `_review-common/blocker-classes.md` § Feature-scope. All three are **director decisions**: never auto-fixed, never silently narrowed. The orchestrator's only permitted action is to produce the split proposal (below) and surface the choice.

## Goal-cohesion check (brief layer — semantic, spawned adversary)

Run by `/brief-author` (against the in-memory draft, alongside self-prosecution) and `/brief-review-v2` (Stage 2, alongside the persona batch). Trigger filter: run the check when the brief has ≥ 4 Goals, OR its Goals name ≥ 3 distinct user-facing surfaces, OR its User-facing changes span ≥ 3 distinct product areas. Below all three, record `goal_cohesion: not_at_risk` and skip — a two-Goal brief cannot bundle two features.

Spawn ONE `general-purpose` agent, `model: "sonnet"` (per `principles.md` § Station model policy), in isolation — never folded into a persona's prompt (the same isolation rationale as the Scope-fidelity Adversary: batched judgment goes charitable). The mandate is the **halved-feature test**, the feature-layer analog of the chunk-layer halved-work test:

> You are the Goal-cohesion Adversary. Read `{brief_path}` in full. Attempt to partition its Goals into two non-empty sets A and B such that ALL of:
>
> 1. **Independent value** — each set, shipped alone, delivers user-visible value a director could reasonably launch without the other.
> 2. **Independent delivery** — no Goal in A requires, for its own outcome, machinery that only B's Goals would cause to be built (and vice versa). Shared *existing* infrastructure doesn't couple them; only new work does.
> 3. **Independent verification** — each set's Goals are observable without the other's surfaces existing.
>
> If such a partition exists, the brief is a bundle: report the partition (which Goals in each set, one sentence per set naming its unified outcome), which Non-goals and User-facing changes follow each set, and your confidence. If every partition fails at least one criterion, report `cohesive` and name the single load-bearing coupling that makes the strongest candidate partition fail — quoted verbatim from the brief, not paraphrased. A shared *theme* ("both are about chat") is NOT coupling; coupling is shared NEW machinery or one set's outcome consuming the other's output. Do not soften: if you are torn, the partition probably exists.

A reported partition files `BRIEF_SCOPE_BUNDLE` (HIGH) with the partition attached. The author partial-drafts on it (`Status: needs-user-input`); the reviewer surfaces it as a blocker. Either way the resolution is the director's: split (the partition becomes two briefs) or accept size explicitly (decisions.md row per § Acceptance below).

## Feature-surface estimator (engineering-plan layer — deterministic, no LLM)

Run by `/engineering-plan-author` (after the Chunk-surface estimator, whose per-row counts this aggregates) and `/engineering-plan-review-v2` (Structural Lint, recomputed — the author state's recorded values are cross-checked and disagreement files `AUTHOR_GATE_DRIFT`, same convention as the chunk-surface cross-check). Compute over the whole chunk index:

- `chunk_count` — rows in the chunk index, **excluding the dedicated acceptance chunk** (the mandatory contract-verification DAG sink every plan carries). It is per-feature overhead, not feature scope; counting it would tip a feature one delivering chunk below the threshold into a false breach.
- `dag_depth` — longest dependency chain in the dependency graph, measured over the delivering chunks only — the acceptance sink adds a final +1 hop to every feature by construction, so it is excluded here for the same reason.
- `cross_chunk_contract_total` — sum of per-row `cross_chunk_contract_count` (already computed by the Chunk-surface estimator).
- `open_decision_count` — Decisions-closure rows not yet `bound` + undecided cross-chunk decisions the draft itself discloses (the population that becomes `IMPLEMENTABILITY_GAP` / `OPEN_QUESTION` findings).

**Threshold — flag when ANY of:** `chunk_count >= 10`, `dag_depth >= 5`, `cross_chunk_contract_total >= 12`, `open_decision_count >= 6`. Fires `FEATURE_SURFACE_EXCESS` (HIGH when two or more sub-metrics breach, MEDIUM on one), with the sub-metric values in the finding. Thresholds are provisional, calibrated so the three observed spinning features would have fired at EP-authoring time; tighten or loosen only from observed convergence data, and record any change as a bound decisions.md row at the project level.

Record the four sub-metric values in the author sidecar / review state as `feature_surface` regardless of verdict, so trajectories are visible across rounds.

## Non-convergence tripwire (reactive — reviewer Round Memory, both layers)

The proactive gates protect future features; this catches ones already in flight. Run by `/brief-review-v2` and `/engineering-plan-review-v2` in the Round Memory Pass (deterministic, no LLM judgment).

State: on every verdict, append `{round, open_blocker_count, open_question_count}` to an `open_blocker_history` array in the reviewer state file.

**Trigger — fire when `round_number >= 5` AND either:**

- `open_blocker_count` has not strictly decreased over the last 3 recorded rounds (plateau or growth), OR
- current `open_question_count >= 8` (the decision surface is outrunning arbitration regardless of trend).

**Cold-history fallback:** when `open_blocker_history` is absent (state predates this gate), substitute the loaded state's `prior_blockers` length for the current count and fire on `round_number >= 5 AND prior_blockers length >= 8`. This is deliberate: an in-flight feature that has been spinning fires on its first post-gate round, not three rounds later.

Fires `FEATURE_NONCONVERGENCE` (HIGH) and triggers the split proposal below. This class is exempt from decisions-log carry-forward retraction by ordinary rows; even a size-acceptance row (§ Acceptance) only resets its counter rather than silencing it — a feature the director chose to keep whole must still actually converge.

## Split proposal (shared output — all three trigger paths)

When any class above fires, spawn ONE `general-purpose` agent, `model: "sonnet"`, to draft the partition the director will decide on. Inputs: the brief, the engineering plan (when it exists), the current open blockers, and `features/<feature>/decisions.md`. Mandate:

> Propose the minimum-coupling partition of this feature into two (or, only if unavoidable, three) features. For each proposed feature: its name, which Goals / Non-goals / User-facing changes it takes, which chunk-index rows and chunk plans follow it, which bound decisions.md rows migrate with it (a bound row follows the chunks it arbitrates), and which open blockers it inherits. Cut along the fewest cross-chunk contracts: prefer a partition where severed dependencies are countable on one hand, and name each severed edge with the interim seam that replaces it (e.g., "feature B consumes A's table as an existing schema, not a co-designed one"). State what CANNOT be cleanly split, verbatim from the plan. Do not advocate — the director may still choose to keep the feature whole; your job is to make the alternative concrete enough to choose between.

The proposal renders in the verdict / partial-draft in the `/explain-blockers` decision shape: one-line question, the two options (split as proposed / keep whole with explicit acceptance), what each collapses. Applying an approved split is session-agent work in a later turn (new feature dirs, brief split, decisions migration, state-file re-keying) — never done inside the review that proposed it.

## Acceptance and carry-forward

A director who keeps a flagged feature whole binds it explicitly: a `features/<feature>/decisions.md` row, `Status: bound`, whose Resolution contains a size-acceptance keyword (`feature surface accepted`, `bundle accepted whole`, `single-feature landing arbitrated`) AND names the sub-metric values (or Goal partition) it accepts. Effects:

- `BRIEF_SCOPE_BUNDLE` / `FEATURE_SURFACE_EXCESS` — suppressed while the row stands. **Residual-scope check:** re-fires if any accepted sub-metric later grows ≥ 25% past the accepted value, or a Goal is added — acceptance covers the size that was accepted, not all future growth.
- `FEATURE_NONCONVERGENCE` — the row resets its round counter (trigger re-arms at acceptance-round + 5) but never silences it permanently.

A row binding an individual decision, concern, or chunk does NOT suppress any of these — same discipline as the Chunk-surface estimator's carry-forward: the row must arbitrate the *aggregate*, in words.
