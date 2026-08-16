# Blocker classes — shared registry

Used by all five reviewers — `/review-pr-v2`, `/plan-review-v2`, `/engineering-plan-review-v2`, `/brief-review-v2`, `/spec-review` — to label remaining unresolved findings (see the `## Brief-only` and `## Spec-only` sections below). Hosting skill names which subset is active. The verdict gate logic at the bottom is also shared.

Throughout this file, "a bound `decisions.md` entry / row" means an entry whose `Status:` is `bound` living in the log's `## Active (bound)` section. An entry marked `Status: superseded by "<title>" (<date>)` or `Status: obsolete` (in the `## Archived (superseded/obsolete)` tail) never arbitrates, never retracts a finding, and never confers carry-forward exemption — see `~/.claude/skills/_review-common/principles.md` § What counts as a bound entry.

---

## Universal blocker classes

| Class | Meaning | Resolution |
|---|---|---|
| `STABLE_DISAGREEMENT` | Two personas filed contradictory fixes on the same span. | User picks one option; orchestrator applies. |
| `OPEN_QUESTION` | Persona filed a question rather than a fix; OR a fix would weaken tests/types/intent. | User answers / decides; orchestrator does not auto-fix. |
| `FIX_INTRODUCED_PREMISE_INVERSION` | Orchestrator's applied fix rewrote prose (comment, docstring, schema directive, plan body, brief, decisions log) that asserts a claim about behavior, but the claim does not survive verification against the actual repo. The fix itself introduced the lie. Working tree left dirty. | User inspects, corrects the prose to match reality OR amends the underlying code/structure to match the claim. |
| `POLISH_PLATEAU` | Tier-2 weight non-zero but ≤ floor (4). | **Non-blocking** — surfaced for visibility only; ship is acceptable. |
| `REPO_STATE_DRIFT` | `git rev-parse HEAD` changed mid-review. | User re-runs the skill from scratch. |

## PR-only

| Class | Meaning | Resolution |
|---|---|---|
| `BASELINE_RED` | Stage 1 detected pre-existing gate failures on branch HEAD before review. Stage 2/3 were skipped. | User fixes failing gates (or carves them out with stable rationale) and re-invokes. |
| `FIX_INTRODUCED_REGRESSION` | Applied fix broke a gate. Working tree left dirty for inspection. | User inspects, fixes, re-invokes. |

## Plan-only (chunk + engineering)

| Class | Meaning | Resolution |
|---|---|---|
| `STRUCTURAL_LINT_FAILED` | `/plan-lint` short-circuited the review at Stage 0. | User fixes structural defects per `/plan-lint` output and re-invokes. |
| `AUTHOR_GATE_DRIFT` | Reviewer's recomputation of an author-side gate disagrees with the author state's recorded values, OR the author state lacks the expected gate field (the author skill was bypassed by hand-edit or pre-dates the gate). Engineering-plan layer: applies to `chunk_surface_estimator`. Chunk-plan layer: applies to `prose_density`. Surfaces the bypass to the user; does not by itself indicate the underlying breach (`CHUNK_SURFACE_EXCESS` or `PROSE_DENSITY_EXCESS` fires separately when thresholds are breached). | The agent reconciles the author state to the reviewer's recomputed values — refresh the recorded gate field and any changed chunk metadata (`chunk_surface_estimator` / `chunk_count` / `chunk_dag` / `introduced_identifiers` at the EP layer, `prose_density` at the chunk layer) so the sidecar matches the on-disk plan the agent edited. Do NOT re-run the author skill to clear this: re-authoring re-emits sections wholesale and overwrites the author sidecar, desyncing the in-flight review state (`section_hashes`, `round_number`, blocker carry-forward) — and it is unnecessary, since the reviewer has already recomputed the gate (the source of truth) and any genuine threshold breach fires separately as `CHUNK_SURFACE_EXCESS` / `PROSE_DENSITY_EXCESS`. |

## Brief-only (`/brief-review-v2`)

| Class | Meaning | Resolution |
|---|---|---|
| `STRUCTURAL_SHAPE_FAILED` | `/brief-review-v2`'s Stage 0 Structural Shape Check short-circuited the review because required sections are missing, banned content patterns appeared, frontmatter is malformed, or implementation creep (path:line, schema columns, SQL fragments) leaked into brief prose. Briefs do not run through `/plan-lint`, so this is the brief-layer equivalent of `STRUCTURAL_LINT_FAILED`. | User fixes the structural defects (typically: add missing sections, strip addendum / review-attribution / historical-comparison content, hoist implementation creep into the engineering plan) and re-invokes. |

## Spec-only (`/spec-review`)

| Class | Meaning | Resolution |
|---|---|---|
| `SPEC_SHAPE_FAILED` | `/spec-review`'s Stage 0 Structural Shape Check short-circuited the review because required sections (per `~/.claude/skills/_spec-common/spec-format.md`) are missing, banned content patterns appeared, frontmatter is malformed, or implementation creep (path:line, schema columns, SQL fragments) leaked into spec prose. The spec is the root artifact and does not run through `/plan-lint`, so this is the spec-layer equivalent of `STRUCTURAL_SHAPE_FAILED` / `STRUCTURAL_LINT_FAILED`. | User fixes the structural defects (add missing sections, strip addendum / review-attribution / historical-comparison content, hoist implementation creep into the engineering plan) and re-invokes. |

## Brief-conformance (engineering-plan, chunk-plan, and PR reviews)

These three classes are filed by the Brief-conformance Prosecutor and Scope-fidelity Adversary (see `~/.claude/skills/_review-common/brief-conformance-prosecutor.md`). Per `principles.md` § Cross-artifact authority order, they are Class A — **exempt from decisions-log-first carry-forward retraction**. A bound entry in `decisions.md` that itself trespasses a brief Non-goal does not protect the finding; the bound entry is the defect.

They fire at three layers. Engineering-plan and chunk-plan reviews judge a *plan* against the brief (Stage 1.5 of `/engineering-plan-review-v2` and `/plan-review-v2`; pre-draft gate of the authors). `/review-pr-v2` judges the *delivered diff* against the brief — its Stage 1.5 Brief-conformance gate runs only when the PR is feature-scoped, and reconstructs each at-risk Goal's domain + authoritative basis to check whether the *code the PR ships* serves the outcome across the slice of that domain the PR's chunk claims (per the engineering plan's Brief-mapping "Delivered by chunks"), on the authoritative input, before anything irreversible consumes it. At the PR layer all three axes are assessable — the diff + branch HEAD are concrete code, so which surfaces it touches, what input it computes on, and what order operations run are observable facts, not DAG-coverage inferences.

| Class | Meaning | Resolution |
|---|---|---|
| `BRIEF_NONGOAL_TRESPASS` | Engineering plan, chunk plan, delivered PR diff, or a `Status: bound` entry in `decisions.md` implements behavior the brief excludes under `## Non-goals`. Detected by the Brief-conformance audit (Stage 1.5 of the plan reviews; pre-draft gate of the authors; Stage 1.5 of `/review-pr-v2` against the delivered diff). | One of: (a) amend `brief.md` to remove the Non-goal (and re-arbitrate any bound entries against the amended brief); (b) drop the trespassing plan section / chunk; (c) un-bind the `decisions.md` entry that committed to the trespass. Resolution path is named in the verdict's blocker entry. |
| `BRIEF_GOAL_UNDELIVERED` | A brief Goal has no chunk in the engineering plan's Brief Mapping table that *non-trivially delivers it*. "Non-trivially delivers" means the chunk's stated work directly produces the Goal's outcome — a chunk whose Brief-mapping entry only routes through `Supporting infrastructure` does not count as delivering a user-facing Goal. Detected by the Brief-conformance audit. At the PR layer, fires when the PR claims (in its description or its chunk's Brief-mapping) to deliver a Goal but the delivered diff produces none of the Goal's outcome — only enabling/infrastructure code. | One of: (a) add a chunk whose stated work delivers the Goal; (b) amend `brief.md` to remove the Goal if it is no longer in scope. |
| `SURFACE_PARITY_GAP` | A brief Goal that quantifies over a domain or names an authoritative signal is delivered short of what its author intended along ANY of three axes: **(1) subset-of-domain** — the outcome holds for some surfaces / media types / call paths / cohorts / cases the Goal covers but not all (the others get a weaker proxy or nothing); **(2) weaker-substitute-basis** — the outcome is produced across the domain but computed on a degraded proxy input instead of the authoritative signal the Goal names (a title heuristic standing in for a classifier verdict; a snapshot dump's count standing in for restored DB links); **(3) premature-action-before-basis** — a consumer acts on the outcome (especially *irreversibly* — a delete, destructive merge, purge) BEFORE its authoritative basis exists at a later pipeline stage, so the action runs on a proxy while the real signal was reachable. Two arrival paths, orthogonal to the axis and both filed here: *silent* (nothing frames the shortfall as a deliberate cut) and *deferred* (a Non-goal / bound decision defers it but the residual is required-work, not a launch-acceptable cut). Weight by reversibility: an irreversible action on a proxy when the authoritative basis was reachable is the sharpest form and defaults to HIGH. Filed at the engineering-plan layer by the per-Goal **Scope-fidelity Adversary** (all three axes; spawned in isolation, one per at-risk Goal — see `_review-common/brief-conformance-prosecutor.md`), NOT the monolithic Brief-conformance Prosecutor. The subset-of-domain and premature-action axes are engineering-plan-layer only (they are chunk-DAG-coverage properties a single-chunk review cannot assess); the **weaker-substitute-basis axis also fires at the chunk-plan layer**, filed by `/plan-review-v2`'s Stage 1 engineering-plan-trace when a chunk computes a Goal's outcome on a weaker proxy than the authoritative signal its EP row committed — the chunk-layer backstop for an engineering-plan-layer miss (it fires only on unacknowledged drift below the row; a proxy the EP row or a bound decision already committed as launch-acceptable is the EP layer's call, not a finding). **At the PR layer all three axes fire against the delivered diff** — `/review-pr-v2`'s Stage 1.5 Scope-fidelity Adversary checks whether the code the PR ships serves the at-risk Goal's outcome across the domain slice the PR's chunk claims (per the EP Brief-mapping), on the authoritative input, before any irreversible step; a bound **Active** decision that already committed the narrower scope as launch-acceptable suppresses the finding, a `superseded`/`obsolete` one does not. Class A — exempt from decisions-log-first carry-forward retraction. Distinct from `BRIEF_GOAL_UNDELIVERED` (which fires when NO chunk delivers the Goal at all; this fires when a chunk delivers it for part of the domain, on a proxy basis, or too early). | One of: (a) extend coverage — add or widen a chunk so the authoritative basis is produced and served at every consumer the domain touches, at a stage before any irreversible action; (b) scope the Goal's domain down in `brief.md` and add a Non-goal naming the residual — only when the residual is a genuine launch-acceptable cut; (c) for the deferred path where the residual is real follow-up work, the brief must say so explicitly and a follow-up feature must own it. When the Goal is mechanism-phrased, the durable fix is also to rephrase it as an outcome upstream (brief-layer `P-BRIEF-GOAL-OUTCOME-SCOPE`), or the same literal-disjunctive reading defeats the check next round. |

## Feature-scope (brief + engineering-plan layers)

Filed by the Feature-surface gate (`~/.claude/skills/_review-common/feature-surface-gate.md`) — the layer-above analog of `CHUNK_SURFACE_EXCESS`. All three are **director decisions**: the orchestrator never auto-fixes them and never applies a split itself; it produces the split proposal defined in the gate file and surfaces the choice (split vs. explicit size acceptance). Carry-forward is size-acceptance-row-only, per the gate file's § Acceptance — a row binding an individual decision or chunk does not suppress.

| Class | Meaning | Resolution |
|---|---|---|
| `BRIEF_SCOPE_BUNDLE` | The Goal-cohesion Adversary found a partition of the brief's Goals into two sets each with independent value, delivery, and verification — the brief bundles what should be ≥ 2 features. Filed by `/brief-author` (partial-drafts) and `/brief-review-v2`. | Director either approves the attached split (session agent applies it in a later turn: two briefs, Non-goals/User-facing changes distributed per the partition) or accepts size via a bound decisions.md row with a size-acceptance keyword naming the accepted Goal set. |
| `FEATURE_SURFACE_EXCESS` | The deterministic Feature-surface estimator breached: `chunk_count >= 10` OR `dag_depth >= 5` OR `cross_chunk_contract_total >= 12` OR `open_decision_count >= 6`. HIGH on ≥ 2 sub-metrics, MEDIUM on 1. Filed by `/engineering-plan-author` and `/engineering-plan-review-v2` (recomputed; disagreement with the author state's `feature_surface` field files `AUTHOR_GATE_DRIFT`). | Director approves the split proposal or accepts size via a bound row naming the sub-metric values. Residual-scope: acceptance re-fires if any accepted sub-metric grows ≥ 25% or a Goal is added. |
| `FEATURE_NONCONVERGENCE` | Round Memory tripwire: `round_number >= 5` AND (open-blocker count not strictly decreasing over 3 rounds OR `open_question_count >= 8`; cold-history fallback: `prior_blockers` length ≥ 8). The review loop is not closing — the empirical signature of a feature-level bundle. Filed by `/brief-review-v2` and `/engineering-plan-review-v2`. Exempt from ordinary carry-forward; a size-acceptance row only re-arms the trigger at acceptance-round + 5, never silences it. | Director approves the split proposal (the usual resolution — non-convergence at this layer almost always traces to a bundle), or accepts size and commits to arbitrating the open decisions within the re-armed window. |

## Engineering-plan-only

| Class | Meaning | Resolution |
|---|---|---|
| `BRIEF_AMENDMENT_NEEDED` | Chunk has no brief Goal AND infrastructure-subsection escape doesn't apply AND brief refused to grow. | User amends brief or drops chunk. |
| `IMPLEMENTABILITY_GAP` | Decision-Closure Audit cross-chunk-wiring deferral OR Imagined-Implementer undecided decision / missing identifier. | User binds the decision in the engineering plan body. **Gates `CLOSED` only; does NOT gate `APPROVED`.** |
| `CHUNK_SURFACE_EXCESS` | Chunk-index row's aggregate surface exceeds the chunk-discipline ceiling: `concern_count >= 5` (top-level "+"-separated noun phrases) OR `introduced_identifier_count >= 8` (distinct identifiers the chunk creates) OR `cross_chunk_contract_count >= 2` (forward-binding contracts the chunk owns). Distinct from `CONCERN_GATE_FAILED` (a single concern can stay bundled if `decisions.md` covers it; this class catches feature-sized aggregate surface even when each component is bound). Exempt from decisions-log carry-forward unless a `decisions.md` row explicitly arbitrates aggregate surface area ("surface acknowledged", "feature-sized chunk accepted", "atomic landing surface arbitrated") — a row binding component concerns does NOT retract. | (a) Split the row into N sibling chunks with explicit dependency edges; (b) extract a foundational sub-chunk that other siblings depend on, reducing the original row's surface to just the foundation; (c) add a `decisions.md` row whose Resolution explicitly arbitrates aggregate surface area (not just one component concern); then re-invoke. |
| `UNCORROBORATED_RESET` | Single-persona RESET reclassified to CRITICAL HARD per the corroboration rule. RESETs have two subclasses with different corroboration thresholds: `repo-state` (requires 2 personas on the same span); `brief-environment` (requires either 2 personas OR 1 persona + a verbatim contradicting citation from `CLAUDE.md` / project memory / source-of-truth). Subclass appears in the verdict label. | User reads the claim, decides whether to re-scope or dismiss. |
| `GOAL_VERIFICATION_GAP` | The engineering plan does not commit an executable proof that a brief Goal is honored or that a testable Non-goal stays excluded. Fires when ANY of: (a) the plan has no **dedicated acceptance chunk** (a final chunk, a DAG sink depending on every delivering chunk, whose concern is the contract-level acceptance suite); (b) a brief Goal's `Verified by` cell in Brief mapping → Goals is empty, or is `Manual review` for a Goal whose outcome is observably automatable (a Goal that *could* be asserted but is left to manual check is a gap, not an exemption); (c) a brief Non-goal classified `testable-absence` in Brief mapping → Non-goals enforcement has no assert-absence test owned by the acceptance chunk; (d) a Non-goal is marked `scope-boundary` (no test) when its exclusion is in fact observably assertable (mis-classification hiding a missing test). Detected by the Ground-Truth Goal-verification audit. This is about brief Goal/Non-goal honoring, so it is **Class A** per `principles.md` § Cross-artifact authority order — exempt from decisions-log-first carry-forward retraction; a bound `decisions.md` entry does not drop it. Distinct from `BRIEF_GOAL_UNDELIVERED` (no chunk *delivers* the Goal) and `SURFACE_PARITY_GAP` (the Goal is delivered short of its domain/basis): this fires when the Goal may be delivered fine but nothing *proves* it, so a future refactor can silently break the contract with no failing test. Contract-level acceptance proof is a distinct property from per-chunk TDD, which proves local behavior only. | One of: (a) add the dedicated acceptance chunk (final DAG sink) and enumerate its Goal/Non-goal acceptance proofs in Brief mapping; (b) fill the missing `Verified by` / absence-test cell, naming the acceptance chunk; (c) re-classify a mis-marked `scope-boundary` Non-goal to `testable-absence` and give it a proof; (d) for a Goal genuinely un-automatable, keep `Manual review` AND record the one-line reason it cannot be an executable assertion, which the review persona scrutinizes. |

## Repo-premise (engineering-plan + chunk-plan layers)

Filed by the Repo Reality Sweep (`~/.claude/skills/_review-common/repo-reality-sweep.md`) — the one stage whose universe is enumerated from the **repository** rather than from the artifact. Every other discovery path checks claims the plan *makes*; this class covers claims the plan *omits*, which no amount of re-reading the plan can surface because silence is not falsifiable.

| Class | Meaning | Resolution |
|---|---|---|
| `REPO_PREMISE_GAP` | The plan's premises about the code it will touch do not survive reading that code, along ANY of three axes. **(1) incumbent divergence** — the chunk replaces or extends shipped code, its design differs from what that code actually does, and the difference is not stated; the sharpest form is a *secondary* write the incumbent performs and the replacement drops (a cache timestamp, an audit row, a provenance column, a cleanup), because the plan describes the primary job and the omission is invisible on the page. **(2) caller closure** — an existing caller of a symbol / file / table / column / route the chunk changes is not accounted for, whether by update, by an unaffected-because argument, or by a named residual; a symbol already enumerated against *one* invariant the plan asserts but not the rest is the common shape, and it reads as coverage. **(3) dependency guarantee** — a primitive the chunk newly makes load-bearing guarantees less than the plan's use of it assumes, judged **at the plan's stated scale**; this fires hardest where the chunk widens a population, drops a filter, or raises a fallback to primary, since a dependency adequate at hundreds of rows can be flatly wrong at thousands. Axis 3 is reachable by neither of the others — the plan does not diverge from the dependency (it adopts it) and the dependency is not a caller (it is a callee), so from inside the plan it reads as a solved primitive. Severity by consequence, not by axis; weight by irreversibility, since these plans routinely gate one-shot or destructive steps. Report the measured blast radius wherever a cheap read-only query or grep settles it — "3,354 of 7,128" and "some" resolve differently. | One of: (a) state the divergence in the plan and, where it was unintentional, restore the dropped behavior as an explicit write-set step; (b) account for the caller — update it, argue it unaffected, or bind it as a disclosed residual; (c) for a dependency gap, either strengthen the use (add the corroborating check), narrow the population the chunk applies it to, or disclose the shortfall with the population **sized** — this is a director decision, not an auto-fix. **When applying any of these, re-run the three questions on the fix itself**: a remedy is new design against the same codebase, and the failure mode is authoring a check the repo already implements adjacent to what you read. Grep before you specify; import rather than redefine. |

## Plan-author-only (chunk-plan authoring)

These classes are filed by `/plan-author` at write time as the prevention-side mirror of `/plan-review-v2`. The reviewer-side equivalents (where they exist) usually fire as `STRUCTURAL_LINT_FAILED` because `/plan-lint` is the reviewer's deterministic floor; the author classes are stricter and named distinctly so the user-facing decomposition recommendation is precise.

| Class | Meaning | Resolution |
|---|---|---|
| `CONCERN_GATE_FAILED` | Chunk plan's H1, Goal sentence, OR engineering-plan chunk-index description matched a multi-concern refusal pattern: self-disclosure (`\bN-concern\b`, `bundle`), conjunctive AND, three+ comma-separated independent noun phrases, plus-separated bundle, OR ≥2 independent clauses in the Goal sentence. The author skill refused to proceed past the Concern gate (`/plan-author`) or Concern-lint gate (`/engineering-plan-author`) and the cross-side warm-mode carry-forward consultation found no applicable arbitration in the engineering-plan reviewer state, the engineering-plan-author state, or the engineering plan's `## Decisions closure` section. | One of (all performed by the agent as targeted plan edits, not by re-running the author): (a) decompose the chunk into one-concern siblings directly in the engineering plan (chunk index + dependency graph + brief mapping); (b) rewrite the engineering-plan chunk-index row description to single-concern phrasing citing a `decisions.md` arbitration entry; (c) add an explicit `## Decisions closure` row arbitrating the bundle (`bound` status, includes a concern-family keyword like `bundle` / `mutually load-bearing` / `transactional invariant`); then reconcile the author state's concern/surface fields to match. Re-running the author skill within a review loop desyncs the in-flight review state and is not the remedy — the author is re-run only for a user-requested wholesale re-author. |
| `BUDGET_EXCEEDED` | Chunk plan exceeded the 500-line / 40k-token hard cap. Almost always signals overscoping that the Concern Gate didn't catch via headers (a single-concern chunk rarely needs more than 300 lines). | User decomposes the chunk via engineering-plan amendment, OR overrides with `--bypass-byte-budget` (logged in the sidecar as a deliberate exception; reviewer treats with extra scrutiny). |
| `PROSE_DENSITY_EXCESS` | Chunk plan's on-disk prose density breached the Prose-Density gate. The gate fires when ANY of: `bytes_per_line_avg >= 200` across §Conventions + §Tests to add + §Acceptance criteria (excluding code-fence blocks and table rows); `bullet_word_count_max >= 400` for any single bullet; `parenthetical_nesting_depth_max >= 3` in any single sentence. Targets the artifact-bloat failure mode: per-bullet defensive accretion regardless of provenance — fix accretion in this invocation, prior-invocation bloat surviving warm-mode rewrite (the partial-draft path preserves ~80% of the plan byte-stable, so prior bloat persists if the current invocation doesn't touch it), first-Draft defensive density, or hand-edits. The on-disk artifact is the measurement target; how the bloat arrived is irrelevant. Distinct from `BUDGET_EXCEEDED` (whole-document length) and from `CONCERN_GATE_FAILED` (number-of-concerns at the row level); this class targets per-bullet structural quality regardless of total document length. Gate runs unconditionally after Self-prosecution; the only skip path is `--draft` mode (Self-prosecution itself is skipped, so the post-Self-prosecution measurement point does not exist). Carry-forward applies only when a `decisions.md` row at the parent feature explicitly arbitrates *density* — Decision column substring-matching the chunk slug, `Status: bound`, AND Resolution column containing a density-acknowledgement keyword (`prose density acknowledged`, `byte-format prescription density accepted`, `procedural verification depth required`, `regex specification accepted`). A row binding the chunk's *content* without acknowledging density does NOT retract. | One of (all performed by the agent as targeted plan edits, not by re-running the author): (a) split each overgrown bullet into N peer bullets at the same indentation level (sub-clauses with their own citations become peers, not nested clauses); (b) promote nested parentheticals to peer bullets (three-deep nesting almost always re-flows as three sibling bullets); (c) cite a `decisions.md` row arbitrating density per the carry-forward criteria above; then reconcile the author state's `prose_density` field to match. Re-running `/plan-author` within a review loop desyncs the in-flight review state and is not the remedy. |

---

## Remediation-completeness (PR, chunk-plan, engineering-plan, and brief layers)

Filed by the between-round completeness check each of those four reviewers runs over the **prior** round's blockers. Post-fix premise verification and same-round focused re-prosecution both scope to the orchestrator's *own* edits inside the round that made them; these two classes cover the remediation the **user** writes *between* rounds, which no other stage sees.

| Class | Meaning | Resolution |
|---|---|---|
| `REMEDIATION_INCOMPLETE` | A prior blocker's fix landed in the section, file, or line that motivated it and did not reach the sites coupled to it — so the blocker reads as closed while its consequences are unbuilt. Coupled sites are layer-specific: other call sites and the tests covering the change (PR); the Factoring Contract and the parent EP's chunk-index row (chunk plan); gate tables, protection enumerations, and count claims over any set the fix resized (engineering plan); every downstream `engineering-plan.md` tracing to the brief (brief). Severity is inherited from the original blocker. | User completes the sweep across the named missed sites. The surviving sites feed the Class Sweep as seeds rather than waiting for a persona to rediscover them next round. |
| `DECISIONS_PROVENANCE_GAP` | An arbitration made to close a prior blocker was never recorded in `decisions.md`, OR an artifact cites a `decisions.md` entry that does not exist (resolved by heading, not by date alone). HIGH. | User writes the missing bound entry. Until they do, the arbitration cannot be retracted by decisions-log-first carry-forward, so the same ground is re-prosecuted every round — which is the failure this class names. |

Both are **exempt from ephemeral (`recently_resolved_blockers`) carry-forward**: each is an assertion about the completeness of the carry-forward record itself, so retracting it against that record is circular. `DECISIONS_PROVENANCE_GAP` is **additionally exempt from decisions-log-first retraction** — a citation to an entry that does not exist cannot be retracted by the log it points at.

## Verdict gates

### Verdict banner — always the LAST thing emitted

Every reviewer ends its response with a verdict banner, and **nothing follows it**, so the user never scrolls up to find the outcome. The banner is **byte-identical across every reviewer and every run** because a shared script renders it — do **not** hand-format it. Run this as the final action, after the state file is persisted:

```bash
python3 ~/.claude/skills/_review-common/verdict_banner.py "<STATUS>" <ROUND> [<BLOCKERS>] [--next "<one line>"]
```

- `<STATUS>` — the reviewer's chosen gate value verbatim: `APPROVED`, `NEEDS USER INPUT`, or (engineering-plan reviewer only) `CLOSED`. Quote it; it contains spaces. Any other value is rejected.
- `<ROUND>` — this verdict's `round_number` (the same number the output block's **Round** line shows; `1` on a cold start).
- `<BLOCKERS>` — the open-blocker count. Pass it for `NEEDS USER INPUT`; omit or `0` on a clean verdict.
- `--next` — one line: on a clean verdict, the next step in the pipeline (for `/plan-review-v2` at a second consecutive APPROVED, `plan-doc PR auto-opened — <url>`); otherwise `resolve the blockers above (or /explain-blockers), then re-invoke /<this-reviewer>`.

Emit the script's stdout **verbatim** as the last lines of your response — do not rewrap, re-space, re-order, or restyle it. It prints exactly:

```
════════════════════════════════════════════
VERDICT: NEEDS USER INPUT — 3 blockers
Round: 4
Next: resolve the blockers above (or /explain-blockers), then re-invoke /plan-review-v2
════════════════════════════════════════════
```

The `VERDICT` and `Round` lines are fixed by the script — same status and round in, same bytes out, for all five reviewers; that is the deterministic contract. This banner is **in addition to** the verdict rendered inside the output block, never a replacement. In multi-plan mode, run the script once per plan (each with that plan's status / round / blockers) and emit the banners stacked, in the summary table's order.

### PR review (`/review-pr-v2`)

- **APPROVED** when ALL of:
  - Tier-1 weight = 0
  - Tier-2 weight ≤ 4
  - All gates GREEN after fixes
  - No `BRIEF_NONGOAL_TRESPASS`, `BRIEF_GOAL_UNDELIVERED`, `SURFACE_PARITY_GAP` (feature-scoped PRs only — see `/review-pr-v2` § Stage 1.5), `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `FIX_INTRODUCED_REGRESSION`, `FIX_INTRODUCED_PREMISE_INVERSION`, `BASELINE_RED`, `REPO_STATE_DRIFT`
- **NEEDS USER INPUT** otherwise.

### Chunk plan review (`/plan-review-v2`)

- **APPROVED** when ALL of:
  - Stage 0 Structural Lint Gate exited 0
  - Tier-1 weight = 0
  - Tier-2 weight ≤ 4
  - No `BRIEF_NONGOAL_TRESPASS`, `BRIEF_GOAL_UNDELIVERED`, `SURFACE_PARITY_GAP`, `PROSE_DENSITY_EXCESS`, `AUTHOR_GATE_DRIFT`, `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `FIX_INTRODUCED_PREMISE_INVERSION`, `REPO_PREMISE_GAP`, `REPO_STATE_DRIFT`
- **NEEDS USER INPUT** otherwise.

### Brief review (`/brief-review-v2`)

- **APPROVED** when ALL of:
  - Stage 0 Structural Shape Check exited clean (no `STRUCTURAL_SHAPE_FAILED`)
  - Tier-1 weight = 0
  - Tier-2 weight ≤ 4
  - No `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `FIX_INTRODUCED_PREMISE_INVERSION`, `REPO_STATE_DRIFT`, `BRIEF_SCOPE_BUNDLE`, `FEATURE_NONCONVERGENCE`
- **NEEDS USER INPUT** otherwise.

### Spec review (`/spec-review`)

- **APPROVED** when ALL of:
  - Stage 0 Structural Shape Check exited clean (no `SPEC_SHAPE_FAILED`)
  - Tier-1 weight = 0
  - Tier-2 weight ≤ 4
  - No `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `FIX_INTRODUCED_PREMISE_INVERSION`, `REPO_STATE_DRIFT`
- **NEEDS USER INPUT** otherwise.

### Engineering plan review (`/engineering-plan-review-v2`)

Three-state verdict. Pick exactly one.

- **CLOSED** — plan is shape-correct AND every cross-chunk decision is bound. Per-chunk plan writing is unblocked. Required:
  - Tier-1 weight = 0
  - Tier-2 weight ≤ 4
  - No `BRIEF_NONGOAL_TRESPASS`, `BRIEF_GOAL_UNDELIVERED`, `SURFACE_PARITY_GAP`, `GOAL_VERIFICATION_GAP`, `BRIEF_AMENDMENT_NEEDED`, `CHUNK_SURFACE_EXCESS`, `FEATURE_SURFACE_EXCESS`, `FEATURE_NONCONVERGENCE`, `AUTHOR_GATE_DRIFT`, `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `IMPLEMENTABILITY_GAP`, `UNCORROBORATED_RESET`, `REPO_PREMISE_GAP`, `REPO_STATE_DRIFT`
  - `imagined_implementer_report.verdict == implementable`

- **APPROVED** — plan is shape-correct BUT cross-chunk decisions remain undecided. Per-chunk plan writing is **NOT** yet unblocked. Required:
  - Tier-1 weight = 0
  - Tier-2 weight ≤ 4
  - No `BRIEF_NONGOAL_TRESPASS`, `BRIEF_GOAL_UNDELIVERED`, `SURFACE_PARITY_GAP`, `GOAL_VERIFICATION_GAP`, `BRIEF_AMENDMENT_NEEDED`, `CHUNK_SURFACE_EXCESS`, `FEATURE_SURFACE_EXCESS`, `FEATURE_NONCONVERGENCE`, `AUTHOR_GATE_DRIFT`, `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `UNCORROBORATED_RESET`, `REPO_PREMISE_GAP`, `REPO_STATE_DRIFT`
  - One or more `IMPLEMENTABILITY_GAP` findings remain
  - `imagined_implementer_report.verdict == not_implementable`

- **NEEDS USER INPUT** — anything else (Tier-1 weight > 0, OR a non-`IMPLEMENTABILITY_GAP` blocker is present, OR a corroborated RESET fired).

The semantic difference: APPROVED says "the *shape* is right; remaining work is decision-making, not structure-fixing." CLOSED says "you can write the next per-chunk plan and have it cohere with the others."
