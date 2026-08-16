# Class Sweep — dedicated same-round sibling-enumeration stage

Loaded by `/brief-review-v2`, `/engineering-plan-review-v2`, `/plan-review-v2`, `/review-pr-v2`. The hosting skill names where this stage sits in its pipeline and fills the per-layer slots; this file defines the mechanism.

## The problem this stage exists to solve

Personas file **one instance of a defect class per round**. A persona reading a plan with four vaguely-worded acceptance criteria flags *one*, defines the class as "*this* chunk's criterion is vague," sets the universe to "*this* chunk," and moves on. The fix resolves the one named instance; the three siblings survive, and next round another persona flags a second one. The class closes at a rate of one instance per round — the exact churn this stage kills.

The root cause is that **"enumerate the universe" is passive and under-served by the default class notion.** There are two notions of "class," and only one is served well by identifier-grepping:

- **Propagated identity.** ONE root defect surfaces at N locations linked by a shared token: a renamed symbol used at 5 callsites, a schema column referenced in 3 files, a retired flag named in 4 places. The universe is found by grepping the token — every hit is the same wrong thing, and the existing "sections, files, callsites, derived names" enumeration already handles this well.

- **Recurring category.** N *independent* defects of the same *kind*, NOT linked by any shared token: four chunks each with a distinct vague criterion, three Goals each failing outcome-scope parity, five sections each carrying review-attribution prose, every mutation missing the same guard. No grep finds these — the only way to enumerate them is an **active pass over every peer location**, asking of each "does the class live here too?" This is the notion personas systematically under-enumerate, because there is no token to grep and the passive "enumerate the universe" instruction does not force the peer-by-peer scan.

`P-CLASS-SCOPE` already commits the design to "the universe must be right the first time — no Round-2 widens." This stage is the mechanism that makes that commitment real for the recurring-category notion: a **dedicated fan-out**, one sweep agent per distinct category, that exhaustively walks the peer-set so the whole class closes in the round it was discovered.

## Where the stage sits

The Class Sweep is a finding-**expansion** pass. It runs:

- **after** every finding-producing stage (persona prosecution; and, where present, the imagined-implementer / RESET / premise short-circuit checks) — so it has the full set of seed categories,
- **after** any short-circuit that would abort the round (a RESET corroboration short-circuit, a baseline-red stop) — so a round that is about to stop does not pay for a sweep,
- **after** the persona findings have been through critical-pair retraction — so a category whose only seed was retracted does not get swept,
- **before** the orchestrator consolidates and applies fixes — so the swept siblings are fixed in the *same* editing pass as their seeds.

It is distinct from, and complementary to, the same-round focused re-prosecution: the sweep is the **pre-fix** pass that widens the finding set to the whole class; re-prosecution is the **post-fix** pass that re-checks the prose the orchestrator just wrote. Both are bounded to exactly one pass and neither recurses.

## Eligibility — which categories get a sweep agent

Group the surviving seed findings by their declared `class`. For each distinct class, decide sweep-eligibility deterministically:

- **Sweep-eligible** when the class is a *recurring category* OR a *propagated identity* whose peer-set has cardinality > 1 — i.e. there exists more than one peer location where the class could live. The persona's `class_notion` and `peer_set` fields (see `agent-prompt.md` § Class sweep obligation) name this directly; when `peer_set` names a repeated structural unit (chunks, Goals, Non-goals, sections, acceptance criteria, mutations, callsites, changed files, …), it is sweep-eligible.
- **Singleton — skip** when the class can, by its nature, live in exactly one place: "the plan has no rollback path," "the brief's single Problem statement is wrong," "this one cross-chunk seam is unregistered." A singleton has no peer-set to walk. Record it as `singleton: true` in the sweep block and do not spawn an agent.

Do NOT skip a category because a persona already listed two instances — the sweep's job is to confirm the enumeration is *complete*, and a persona that found two may still have missed the third. The only skip is genuine singleton-ness.

**The persona's declared `peer_set` is the sweep's starting point, never its bound.** Eligibility is decided on the declared peer-set, but the sweep agent's first mandatory step is to restate the class as its bare invariant and widen the peer-set to the broadest set that invariant applies to (§ The sweep, Method step 1). This matters at the eligibility gate too: a class declared `singleton` because its *declared* peer-set has one member is NOT a singleton if the bare invariant applies to a repeated unit. Before recording `singleton: true`, restate the invariant yourself and confirm the widest set really has cardinality 1 — "the plan has no rollback path" is a true singleton; "*this* gate condition can never be satisfied" is not, because the invariant applies to every gate condition. A misjudged singleton skips the stage entirely for that class, which is strictly worse than a sweep that walks a wide set and returns all-clean.

When the distinct-eligible-category count is large (> 8), group near-identical classes (same invariant property, different wording) under one sweep agent and **`log()` what was grouped** — never silently cap the fan-out (per `principles.md`'s no-silent-caps discipline). One category, one agent; many seeds of one category still spawn one agent.

## The sweep

For each sweep-eligible category, spawn **one** Agent with `model: "sonnet"` (per `principles.md` § Station model policy — this is prosecution-class work against a fixed template, so the execution tier suffices; never inherit the session model). Record `class_sweep_model: "sonnet"` in the state file.

### Sweep-agent prompt template

> You are running a **class sweep** on an adversarial review tribunal. You are NOT prosecuting the whole artifact — a persona already did that and found the seed(s) below. Your one job: given a defect *class* and the seed instance(s) that established it, find **every other instance of the same class** in the artifact, so the whole class is closed in this round instead of leaking one instance at a time across future rounds.
>
> ## The class
> - **Class (invariant property):** {class_name}
> - **Class notion:** {class_notion}   # propagated_identity | recurring_category
> - **Seed instance(s):** {seed_findings}   # each with path_or_section + verbatim evidence + the persona's proposed_fix
> - **Peer-set to walk:** {peer_set_definition}   # the repeated structural unit where this class can live, per the hosting skill
>
> ## Artifact access
> {artifact_access}   # how to Read the target in full; for propagated_identity, the grep to run
> {layer_notes}       # layer-specific scope bounds (e.g. PR ownership: diff + blast radius only)
> {structural_sweep_universes_run}   # universes the Structural Sweep already walked exhaustively this round, with their member sets; "none" when that stage did not run at this layer. Do not re-walk an overlap — fold it in.
>
> ## Method
> 1. **Challenge the handed peer-set before you walk it — this step is mandatory and comes first.** The peer-set above was declared by the persona who found the seed, and personas systematically declare it at the level of *the instance they found* rather than the level of *the invariant*. So: restate the class as its bare invariant property — "an X that lacks Y", "an X whose Y can never be Z" — stripped of every detail specific to the seed. Then ask: **what is the widest set of things in this artifact to which that invariant applies?** If that set is wider than the handed peer-set, **walk the wider one**, and record both sets in your output.
>
>    A handed peer-set that names a *subtype* where the bare invariant applies to a *supertype* is the single most common way a sweep under-closes its class. Worked example, from a real round: a seed was filed as "a *cascade no-verdict outcome* routed to a blocking gate with no terminal state" and handed the peer-set "every cascade consumer × outcome" — 13 members. The bare invariant is "a blocking gate condition with a failure state that can never be exited," whose widest set is *every gate condition in the artifact* — 23 members. The sweep walked the handed 13, closed them correctly, and missed a CRITICAL sitting in the other 10; it surfaced a round later as a fresh blocker. Walking the supertype was free — same agent, same pass.
>
>    Widening is not license to drift to a *different* class (step 6 still binds). It is license to apply the SAME invariant to every place it can hold. If you widen, say so explicitly and justify the supertype in one sentence; if the handed set is already the widest, say that too — a confirmed peer-set is a useful signal, not a non-answer.
>
>    **Do not re-walk a universe the Structural Sweep already covered this round.** If your widened peer-set matches (or is a subset of) a universe listed in `{structural_sweep_universes_run}`, that exhaustive matrix already exists — say so, fold its cells in as your `swept_clean` / instances for the overlapping members, and spend your effort only on members outside it. The two stages ask overlapping questions by design (that stage's gate-liveness universe is the same set this widening example reaches), so the round should pay for the matrix once, not twice.
> 2. Read the target in full. Enumerate the peer-set you settled on exhaustively — list every member (every chunk, every Goal, every Non-goal, every acceptance criterion, every gate condition, every changed file, every callsite, …), not a sample.
> 3. For **propagated_identity**: grep the shared token across the declared scope; every hit that is the same wrong thing is an instance.
>    For **recurring_category**: walk EACH peer member and judge it against the class's invariant property — "does THIS member also exhibit the class?" Judge each member on its own evidence; do not assume uniformity in either direction.
> 4. For every instance found (INCLUDING re-confirming the seeds), produce a finding row: `path_or_section`, verbatim `evidence` (quote the offending text with an anchor), `severity` (judge per-instance; default to the seed's severity when the instance is materially identical), and a concrete `proposed_fix` for that specific instance.
> 5. For every peer member you checked and found **free** of the class, record it in `swept_clean` — this is the exhaustiveness proof. A sweep that lists 2 instances and 0 swept_clean members did not walk the peer-set.
> 6. Stay inside the class. A sweep widens to genuine siblings of the SAME invariant property, each carrying its own evidence — NOT to "everything that looks vaguely similar" and NOT to a different defect class you happen to notice (that is a new persona finding, out of scope here). Per `P-CLASS-SCOPE`, an instance you cannot back with its own verbatim evidence is not an instance.
> 7. If, after walking the peer-set, the class genuinely has exactly one possible location (a true singleton the eligibility filter misjudged), return `singleton: true` and stop.
>
> ## Output
>
> ```
> class: {class_name}
> bare_invariant: {the class restated as its invariant property, stripped of seed-specific detail}
> class_notion: propagated_identity | recurring_category
> peer_set_handed: {the peer-set definition you were given}
> peer_set_walked: {the peer-set you actually enumerated}
> peer_set_widened: true | false
> widening_justification: {one sentence — why the walked supertype is where the bare invariant lives; empty when peer_set_widened is false}
> peer_set_size: {integer — total members enumerated in peer_set_walked}
> singleton: false            # true only if the class turned out to have one possible location
> instances:
>   - path_or_section: {…}
>     evidence: {verbatim quote + anchor}
>     severity: CRITICAL | HIGH | MEDIUM | LOW
>     is_seed: true | false   # true if this is one of the seeds you were handed
>     proposed_fix: {specific change for THIS instance}
> swept_clean:
>   - {peer member checked and found free of the class}
>   ...
> ```
>
> Do NOT edit any files. Do NOT run gates. Return only the finding rows.

## Orchestrator merge

1. **Collect** every sweep agent's output. For each, sanity-check exhaustiveness: `peer_set_size` should equal `len(instances) + len(swept_clean)` (± seed rows); a sweep reporting instances but an empty `swept_clean` on a peer-set of size > (instances found) did not walk the set — re-spawn that one agent once. `singleton: true` is a valid terminal outcome (no expansion).
2. **Dedup** each instance against the existing finding pool by `(class, path_or_section)`. A seed that the sweep re-confirms is already in the pool — keep the existing finding (merge in the sweep's `proposed_fix` if richer). Every **non-seed** instance becomes a NEW finding of the seed's class, at the sweep-judged severity/tier.
3. **Filter the new siblings through the same critical-pair retraction** the persona findings went through (mirroring the same-round re-pass's re-filtering). A sibling that contradicts an active critical-pair policy is retracted, not applied.
4. **Fold** the surviving siblings into the consolidation/fix-application pass, so seed and siblings are fixed together. Class A siblings (those whose evidence quotes a brief Goal / Non-goal / User-facing change) inherit the Class A carry-forward exemption exactly as their seed would.

## State recording (hosting skill writes into its state file / per-round metrics)

```
class_sweep:
  ran: true | false            # false only when zero sweep-eligible categories existed
  class_sweep_model: "sonnet"
  sweep_agents_spawned: {n}     # == count of distinct sweep-eligible (non-singleton) categories, after grouping
  categories:
    - class: {name}
      bare_invariant: {the invariant property, stripped of seed-specific detail}
      peer_set_handed: {what the persona declared}
      peer_set_walked: {what the sweep actually enumerated}
      peer_set_widened: true | false
      widening_justification: {one sentence; empty when not widened}
      peer_set_size: {n — members in peer_set_walked}
      seeds: {n}
      siblings_found: {n}       # non-seed instances the sweep surfaced
      siblings_after_critical_pair_filter: {n}
      swept_clean: {n}
      singleton: true | false
  siblings_promoted_to_findings: {total n}
  categories_grouped: [{...}]    # non-empty only when > 8 eligible categories were grouped; names what merged
```

## Verdict reporting

Render a **Class sweep audit** block in the verdict. When the hosting skill already renders a `### Class > line audit` (as `/review-pr-v2` does), extend that block rather than adding a second one:

```
### Class sweep audit
For each class swept:
- Class: {name} ({class_notion}) — bare invariant: {bare_invariant}
- Peer-set: handed {peer_set_handed} → walked {peer_set_walked} {(widened: {widening_justification}) | (confirmed widest)}
- Peer-set walked: {n} members; swept clean: {n}
- Instances: {n} total ({seeds} seed + {siblings_found} sibling; {siblings_after_critical_pair_filter} siblings survived critical-pair filter)
- Resolution: every instance fixed in this round | {n} escalated as {blocker class}
- Singleton (no peer-set): {list of classes recorded singleton}
```

## Compliance self-check line (hosting skill adds to its pre-verdict gate)

- **Did the Class Sweep run for every distinct recurring category?** `class_sweep.sweep_agents_spawned` equals the count of distinct sweep-eligible (non-singleton) seed categories after grouping; every spawned agent recorded a `peer_set_size` and a `swept_clean` list (an agent reporting instances with an empty `swept_clean` on a multi-member peer-set did not walk it — re-run before posting); and every surviving sibling appears in the consolidated fix set or in a blocker. A round with seed findings whose `class_notion: recurring_category` but `sweep_agents_spawned: 0` skipped the stage — back up and run it.
- **Did every sweep agent perform the peer-set challenge?** Each category records a non-empty `bare_invariant`, both `peer_set_handed` and `peer_set_walked`, and an explicit `peer_set_widened` boolean — with a `widening_justification` whenever it is true. A category where `bare_invariant` merely restates the seed's wording, or where `peer_set_walked` was copied from `peer_set_handed` with no evidence the supertype question was asked, did not perform Method step 1; re-run that one agent. This check exists because a faithfully-walked *narrow* peer-set produces a clean-looking sweep that silently leaves the class open — the failure mode is invisible in the instance counts, so it has to be checked on the peer-set fields themselves.

## Bounding

Exactly one sweep pass per round. Siblings surfaced by the sweep do NOT spawn their own sweeps in the same round, even if a sibling suggests a fresh category — that category's seeds (if any) will have their own sweep from the seed grouping, and a genuinely-new category discovered only through a sibling lands in the verdict and is picked up next round. The one-pass cap is the natural backstop against an inner loop, exactly as it is for the same-round focused re-prosecution.
