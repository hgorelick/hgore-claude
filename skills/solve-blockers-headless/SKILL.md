---
name: solve-blockers-headless
description: Non-interactive sibling of `/solve-blockers`, for the feature factory's resolution station. Same research engine and confidence bar, no human in the loop: requires an explicit target, auto-applies what clears the bar, records the rest as residuals for the orchestrator to escalate. Invoked headlessly; humans want `/solve-blockers`.
user-invocable: true
---

# /solve-blockers-headless

This is the **non-interactive twin of `/solve-blockers`**, built to be the feature factory's resolution station. It is invoked by the orchestrator via `claude -p` against a single artifact's blockers, with no human in the conversation to answer questions or approve an apply. Everything that the interactive skill does by *asking the operator*, this skill does by *deciding autonomously within the ≥95% bar and escalating what it can't*.

The research engine is **identical** to `/solve-blockers`: the same six-condition ≥95%-confidence bar, the same per-decision research pass, the same sibling-dependency DAG, the same render format. Read `/solve-blockers` SKILL.md for any of that machinery — this skill does not restate it, it changes only the **I/O contract** at three points:

1. **Input is an explicit target, never inferred.** The orchestrator passes the exact slug / state-file path / author-artifact reference / PR reference. There is no conversation history to read, no `latest` fallback, and no disambiguation question. If the target can't be resolved deterministically, the skill **refuses** (writes no sidecar, exits with a clear `REFUSED:` line) rather than guessing — the factory treats that as an escalation.

2. **Below the bar → a `needs_human` residual, never a question.** A headless run has no operator to answer an up-front `AskUserQuestion`. So a decision that research cannot clear to ≥95% is **not** batched into a question — it is recorded as a residual with disposition `needs_human`. The factory escalates the whole batch of residuals to the human through the coordinator, not through an interactive prompt inside the skill. This is the exact same boundary the interactive skill draws — "Claude must not ship a confident-framed low-confidence answer" — landing on *escalate* instead of *ask*.

3. **Apply is pre-authorized, and the outcome is a sidecar.** The orchestrator routed here precisely to have the cleared fixes applied, so there is no apply/don't-apply prompt: every decision that clears the ≥95% bar is **auto-applied** in dependency order. The machine-readable outcome is a **resolution-state sidecar** the factory parses (see "Write the resolution-state sidecar"). The rendered report is still produced, but only as the audit trail / escalation context carried in the run's result text — the sidecar, not the prose, is authoritative.

The ≥95% bar is still the load-bearing discipline, and it is *more* load-bearing here than in the interactive skill: there is no operator yes gating the apply, so the bar is the only thing standing between research and an autonomous edit. The bar raises confidence but does not eliminate hallucination / authority-bypass risk, so the conditions below are mandatory and un-weakenable — a decision that cannot clear all six is a residual, full stop, never an auto-applied "probably right." Anything that clears the bar is auto-applied; anything that doesn't escalates. There is no middle path.

The **research pass is read-only** exactly as in `/solve-blockers`: it verifies, scores, and recommends without touching the plan, code, PR, or any state file. Auto-apply begins only *after* the full research pass and the sidecar are complete, and it edits only the plan / code / brief / PR — the input review/author state files stay read-only no matter what. The one new write this skill owns is its own resolution-state sidecar.

The skill runs **in the single headless `claude -p` thread** the orchestrator spawned it in. Per-blocker research is heavy — typically 10–30 Read/grep calls per blocker, plus `context7` lookups when third-party library behavior matters — but is tractable inline at typical blocker counts (1–10). For unusually heavy single-blocker research (>20 files spread across a monorepo, or extensive external-doc reading), spawn one `Explore` agent for that blocker; cross-blocker context stays in the main thread. There is no operator watching this thread — never emit a question, a confirmation prompt, or an apply gate into it; all human-facing decisions become residuals in the sidecar (see below).

## Shared scaffolding (read on demand)

- `~/.claude/skills/solve-blockers/SKILL.md` — **the interactive parent.** Its research engine is this skill's research engine: the six-condition ≥95% bar, the per-decision research pass, the sibling-dependency DAG, and the per-decision render format are all defined there and used here verbatim. Read it for any of that machinery; this skill restates only the headless I/O contract.
- `~/.claude/skills/_review-common/blocker-classes.md` — the registry of blocker classes, their meanings, and prescribed resolution shape. Consult on any unfamiliar class.
- `~/.claude/skills/explain-blockers/SKILL.md` — its **Locate and parse blockers** section defines the deterministic input-parsing / clustering logic this skill reuses; its **Render the decision list** section defines the per-decision output format (extended here with `Apply` and `Verification` lines).

## Relationship to `/solve-blockers`

`/solve-blockers` is the human-facing skill: a person invokes it, it may ask one up-front question batch, and it applies on the operator's explicit yes. **This skill is its headless twin** — same research, no human. The factory invokes it via `claude -p` when the coordinator reaches the `RESOLVING` state. Everything `/solve-blockers` resolves by *asking* or *waiting*, this skill resolves by *deciding within the ≥95% bar* (auto-apply) or *escalating as a residual* (the factory asks the human, not the skill). A human should never invoke this skill directly — they want `/solve-blockers`.

## Inputs

`$ARGUMENTS` is **the explicit target the orchestrator passes** — there is no inference here. The headless run has no conversation history to read, no operator to disambiguate, and must never fall back to "whatever's latest." Exactly one of these shapes is accepted:

1. **Slug / state-file path / author-artifact reference / PR reference** — same shapes and resolution rules as `/explain-blockers` (read its **Inputs** section for the exact match logic; this skill reuses that parsing branch verbatim). The orchestrator computes the slug from the lane context, so in practice this is a concrete `~/.claude/cache/{review,author}-state/<slug>.json` path or a `<owner>/<repo>#<pr>` reference.

The interactive parent's other input shapes — conversation-history `/explain-blockers` reports, `from-explain`, `latest`, saved report paths, pasted report text — are **all removed**. Each of them depends on a human or scrollback that a headless `claude -p` run does not have. If `$ARGUMENTS` does not resolve to exactly one target by the rule above, **refuse**: write no sidecar and exit with a single line `REFUSED: no resolvable target (<reason>)`. Never guess, never scan for the newest file, never ask. A refusal is the factory's signal to escalate the lane.

### Decision scaffold (raw blockers only)

There is never an `/explain-blockers` report in the headless path, so the skill always does its **own clustering** on the resolved state file / PR — identical to `/explain-blockers` step 2b. Read `/explain-blockers` SKILL.md for the clustering tests ("same cluster" vs "different cluster"). The resulting cluster set becomes the `decisions: []` array (`index`, `question`, `options`, `pick`, `resolves_blockers`), keyed back to each raw blocker's `blocker_class` / `path_or_section` / `summary` — the per-class research mandate below keys off `blocker_class`, so that cross-reference is mandatory. After this step the rest of the skill operates on `decisions: []`; the source path stays known only because the **sidecar filename is derived from it** (see "Write the resolution-state sidecar").

### Pre-flight verdict-status check

Before any clustering or research, apply the same pre-flight as `/explain-blockers`:

- Verdict is `NEEDS_USER_INPUT` (any source skill, either side), **OR**
- Verdict is `APPROVED` and `prior_blockers` contains `IMPLEMENTABILITY_GAP` entries (engineering-plan layer, either review or author side).

→ **proceed** to research.

The non-proceed cases are handled headlessly, never by asking:

- **Nothing to solve** (CLOSED, clean APPROVED with no `IMPLEMENTABILITY_GAP`, etc.) — there are no blockers to resolve, which is a *clean* outcome. Write an **empty sidecar** (`{"decisions": []}`) and exit. An empty `decisions` array has no residuals, so the factory reads it as `RESOLVED` and loops back to re-review, which will confirm the clean state. Do not treat "nothing to solve" as an error.
- **`DRAFT_EMITTED`** (author-side only) — the author skill skipped its hardening stages; its blockers are not the real blockers, so researching them is wrong. **Refuse**: write no sidecar and exit with `REFUSED: DRAFT_EMITTED — re-author without --draft before resolving`. The factory escalates (the lane must re-run the author skill without `--draft` first). Do **not** research a draft.

Echo a one-line confirmation into the result text (it is the audit trail, not an operator prompt):

```
Researching N decisions (covering M blockers) from <plain source name>.
```

---

## The 95%-confidence bar (explicit calibration)

A recommended solution qualifies as ≥95% confidence only when **all six** of these conditions hold. Each condition must be checkable mechanically or by direct observation — none rely on Claude's self-rating of certainty.

1. **Premise CONFIRMED against repo HEAD.** The blocker's factual claims about repo state (file contents, function signatures, schema fields, dependencies, lint/test status) have been verified against the current working tree. If the blocker cites `foo.ts:42 calls bar()`, the verification reads `foo.ts` at HEAD and confirms the call. If the blocker's premise is STALE or FALSE, the solution path changes — surface the retraction explicitly rather than recommending a fix for a problem that no longer exists.

2. **Single viable resolution OR clear dominance.** Either only one resolution makes sense given the constraints, or one resolution strictly dominates alternatives on every relevant axis: correctness, blast radius, alignment with brief Goals / Non-goals, conformance to `decisions.md` bindings, follow-on cost, reviewer reaction. "Slightly cleaner" is not dominance — every relevant axis must favor (or be neutral on) the recommended path.

3. **No unverified external-library assumptions.** If the solution depends on third-party library behavior (API shape, default config, version-specific quirk, error semantics), that behavior has been verified via the `context7` MCP server (`resolve-library-id` → `query-docs`) or by reading the library's source / type definitions in `node_modules` or equivalent. "I remember React works this way" does not count. Verification must cite the library version actually installed (`package.json` / `Cargo.toml` / `requirements.txt`).

4. **Authority order respected.** The solution does not contradict a bound entry in `decisions.md` for the feature (when feature-scoped — only Active-section `Status: bound` entries are authoritative; a `superseded`/`obsolete` entry in the `## Archived` tail is not a bound entry to contradict, per `~/.claude/skills/_review-common/principles.md` § What counts as a bound entry), the brief's Goals / Non-goals / User-facing changes (Class A), the engineering plan's chunk-DAG decisions (Class B), or `~/.claude/CLAUDE.md` / project `CLAUDE.md` rules. The class-aware authority order in `~/.claude/skills/_review-common/principles.md` § Cross-artifact authority order is binding: brief > decisions.md > engineering plan (Class A); decisions.md > engineering plan (Class B). If the recommended solution would require amending an upper-authority artifact, that becomes a downstream call (flag explicitly in the verification line) — not a reason to weaken the recommendation.

5. **No open dependency on a sub-95% sibling blocker.** If two blockers are linked such that solution X for blocker A presupposes solution Y for blocker B, then Y must also be at ≥95% within this same pass before X can be confirmed at ≥95%. Cascading low confidence through dependencies is a forbidden short-circuit — each cluster head must clear the bar on its own merits OR the entire cluster gets the unknown-question treatment.

6. **User stake articulable in one sentence.** Claude must be able to write, in a single concrete sentence, what the user is committing to by accepting this solution. Not the implementation reason ("uses the existing helper") — the user-visible commitment ("the cart auto-clear will fire even when the order is created via the bulk-import path, not just the checkout flow"). If the stake can't be articulated cleanly, the framing isn't tight enough, which means the research isn't deep enough, which means the bar isn't met.

**All six are mandatory.** If any one fails, the recommendation does not qualify as ≥95%. Either continue research to close the gap, or record the decision as a `needs_human` residual (see "When research cannot reach ≥95%"). Do not weaken the bar to fit the available research.

---

## Workflow

```
$ARGUMENTS
   ↓
Resolve explicit target → own clustering → decisions: []   (refuse if unresolvable; empty sidecar if nothing to solve)
   ↓
Pre-flight verdict-status check          (proceed / empty-sidecar / refuse — never ask)
   ↓
Per-decision research pass               (each decision researched individually against conditions 1–4, 6)
   ↓
Build sibling-dependency DAG             (condition 5 — verify acyclic, propagate confidence floor)
   ↓
Partition each decision by the bar:
   cleared all six conditions      → disposition auto_applied
   any condition unmet             → disposition needs_human   (residual — NEVER a question)
   premise STALE/FALSE             → disposition needs_human   (retraction — re-run source skill)
   ↓
Write resolution-state sidecar           ({decisions:[{blast_radius, disposition, summary}]} — the authoritative outcome)
   ↓
Render solution list                     (per-decision blocks with Apply + Verification — audit trail in the result text)
   ↓
Auto-apply the auto_applied decisions    (dependency order; residuals & retractions are NOT applied)
```

There is **no user-question step** in this workflow — the interactive parent's up-front `AskUserQuestion` batch is replaced wholesale by the residual partition. A gap that research cannot close to ≥95% is recorded as a `needs_human` residual and escalated by the factory; it is never surfaced as a question inside this run. There is likewise no apply gate: the orchestrator routed here to apply the cleared fixes, so auto-apply is unconditional for the decisions that clear the bar. The sidecar is written **before** auto-apply, so the outcome is recorded even if an individual edit later fails (see "Auto-apply").

---

## Deep research per decision

This is the heart of the skill, and it is **identical to `/solve-blockers`** — read that skill's "Deep research per decision" section for the full mechanics. Each decision in `decisions: []` gets researched until its recommended resolution meets the ≥95% bar — or until the research identifies the specific gap that keeps it under the bar, at which point it becomes a `needs_human` residual (the headless analogue of the parent's "blocking question," escalated rather than asked).

### Per-decision research pass (conditions 1–4, 6)

Parallelize across decisions when their cited artifacts are independent (batch Read / grep calls in a single message). Serialize only when one decision's premise verification depends on another's outcome (rare).

For each decision:

1. **Read the cited artifact section(s).** Pull the relevant lines from the plan / brief / engineering plan / PR diff. Read enough to understand the blocker's framing — not just the cited range, but enough surrounding context to evaluate dominance among options.

2. **Verify the premise (condition 1).** Read the cited repo files at HEAD. Run `grep` for cited identifiers. **Running cheap gates locally is allowed and encouraged** when the blocker hinges on gate state — typecheck, lint, a single targeted test file (use whatever commands the project's `CLAUDE.md` / `package.json` / `Cargo.toml` defines), plus `git status` / `git diff <range>` for working-tree inspection. Anything that takes longer than ~60 seconds or has side effects (writes, network calls) should be skipped in favor of reading recent CI logs via `gh`. If premise is CONFIRMED, proceed. If STALE/FALSE, mark for the retraction cluster and skip research — the recommended "solution" for those is "re-run /<source-skill>; the situation has moved past this."

3. **Enumerate viable resolutions.** Per blocker-class research mandate (see `~/.claude/skills/_review-common/blocker-classes.md` and the per-class branch in `/explain-blockers` SKILL.md step 2a). Be liberal at this stage — better to consider an option and reject it cleanly than to miss the dominant path.

4. **Verify external-library assumptions (condition 3).** For each candidate resolution that touches a third-party library, identify the library's installed version (read `package.json` / `Cargo.toml` / `requirements.txt`) and verify the assumed behavior via `context7` MCP (`resolve-library-id` → `query-docs`) or by reading the library's source / type definitions. If verification surfaces a behavior gap that flips your preferred option, restart enumeration. Do **not** trust training-data recall on library behavior — it is the single biggest hallucination source at this layer.

5. **Apply dominance analysis (condition 2).** Score each viable resolution on: correctness, blast radius (files touched, public API impact, behavior change visibility), authority-order conformance (condition 4 — does it touch decisions.md / brief / engineering plan in a way that requires upper-authority amendment?), follow-on cost (does it create new TODOs, deferred work, or new blockers downstream?), and reviewer reaction (would the v2 prosecutor accept it, or would it just refile a different blocker?). One path must strictly dominate (or be the sole viable option) — otherwise the bar is not met.

6. **Draft the user-stake sentence (condition 6).** One sentence: "Accepting this commits you to X." If the sentence can't be written without hedging ("...probably...", "...in most cases..."), the recommendation is not at ≥95%.

After this pass, every decision has either a locked recommendation (conditions 1–4, 6 all clear) or a known gap.

### Build the sibling-dependency DAG (condition 5)

After per-decision research is complete, build the dependency DAG explicitly:

1. For each locked recommendation, ask: does it presuppose another decision's recommendation? (E.g., "rename X" presupposes "X gets the new name" decision is settled.) Edge from the dependent to the prerequisite.
2. Check for cycles. A cycle means at least one of the dependency edges is wrong (or the decisions are not actually separable — collapse them into a cluster).
3. Propagate confidence floor: a decision's confidence is bounded above by the minimum of (its own pass-result, its prerequisites' confidences). A decision with even one sub-95% prerequisite is itself sub-95% — no exceptions.

Most decision sets are trivially independent (every node a singleton). The DAG step is fast in that case. Build it anyway — the explicit check catches the cases where a "locked" recommendation silently depended on an unresolved sibling.

### Subagent escape hatch

The skill runs inline by default. Spawn an `Explore` agent for a single decision **only** when that decision's research genuinely requires reading >20 files spread across the codebase (e.g., a refactor proposal whose blast radius is the question), or when external-doc reading is unusually large.

When an `Explore` agent reports back, its summary describes what it *intended to do*, not necessarily what it found. Before counting agent-reported facts toward conditions 1–4, spot-check at least one cited file or grep result directly in the main thread. Subagent results are inputs to the confidence assessment, not authoritative confirmation.

### When research cannot reach ≥95% → a `needs_human` residual

Some gaps are not closable by Claude alone. Examples:
- The blocker hinges on a user preference not documented anywhere (e.g., naming convention, error-message tone, performance/clarity tradeoff).
- The blocker requires runtime evidence Claude can't gather (e.g., production traffic patterns, real-device behavior, third-party API live response).
- The blocker depends on an architectural intent the user has not articulated.
- External library behavior is genuinely ambiguous (docs missing, multiple plausible interpretations).

In the interactive parent these are batched into one up-front `AskUserQuestion`. **Here there is no operator to ask**, so each such gap is recorded as a residual instead of a question:

- **Identify the specific question anyway.** Frame it concretely — not "what do you want?" but "should the cart removal fire (a) only when the order commits, or (b) immediately when the user selects an item even if they abandon checkout?" That concrete question becomes the decision's residual `summary` in the sidecar, so the human gets an actionable escalation, not a vague "needs attention." The single most valuable thing this skill produces for a residual is a crisp, answerable question.
- **Set `disposition: needs_human`.** The decision is not applied; auto-apply touches only `auto_applied` decisions.
- **Propagate through the DAG (condition 5).** Any decision that depends on a `needs_human` sibling is itself `needs_human` — confidence never flows up through an unresolved dependency. A whole cluster headed by an unresolved decision escalates together.

**Never** invent a confident-sounding answer to clear the gap (that is the exact failure mode the bar exists to prevent), and **never** emit an `AskUserQuestion` or a plain-text question into the headless thread — there is no one to answer it; the call would hang or be silently discarded. The escalation happens one level up: the sidecar's residuals flow to the coordinator, which batches them for the human via the factory's own escalation path. One skill run produces one sidecar; there is no second pass and no second batch.

---

## Render the solution list

This render is the **audit trail**, not the outcome — it goes into the run's result text so a human reading an escalation (or a later debugging pass) can see what was resolved, what was applied, and what escalated. The authoritative outcome is the sidecar (above); the render must agree with it but the factory never parses the prose. Emit the header plus per-decision blocks in dependency order (clustering the `auto_applied` ones first, then the `needs_human` residuals, then the retraction block — so the escalations are easy to scan).

### Header

```
# Recommended solutions: <plain-language source identifier>

**N decisions resolved at ≥95% confidence.** <if any flagged residuals: "K decisions carry residual uncertainty — flagged inline."> <if any retraction candidates: "Plus M items the situation has moved past — re-run /<source-skill> to close them.">

---
```

The source identifier is the source state file's feature name / PR title (the plain-language form), not the state-file path. The "decisions resolved" count is the number that hit the ≥95% bar cleanly (the `auto_applied` ones); residuals are counted but separated.

### Per-decision block

Each decision is a self-contained block. The format extends `/explain-blockers`' per-decision template with two new lines: **Apply** (the concrete change to make) and **Verification** (the evidence trail justifying the ≥95% bar). The original `Options` and `Also resolves` lines carry over unchanged; `My pick` becomes `Why` (one-sentence dominance reasoning).

```
### Decision [N]: [one-line question, phrased as a choice — match /explain-blockers framing]

**Options:** [Option A — one short clause]; [Option B — one short clause]. (Or "Single call: [one short clause]" if there is no real second option.)

**Apply:** [the concrete change — the actual edit to make, in plain language. Director-language by default; canonical filenames OK here. One short paragraph or a tight bullet list, not prose.]

**Why:** [one sentence. Lead with what accepting this commits the user to (the user-stake sentence from condition 6). Add a single clause on the dominant axis if the stake doesn't carry it alone.]

**Verification:** [one line. Format: "Premise CONFIRMED at <basename>; <library facts checked, with installed version>; authority-order clean [or: requires <upstream artifact> amendment]; no sub-95% dependencies."]

**Also resolves:** [linked blockers, one short phrase each, comma-separated. Omit if the cluster is a singleton.]
```

**Worked example (illustrative — not real blockers):**

```
### Decision 2: Should the cart auto-clear fire on item-select or only on order commit?

**Options:** Fire on item-select (immediate); fire on commit (atomic with order).

**Apply:** In the cart-removal logic, move the trigger from the item-select handler to the order-commit transaction. Wrap removal and order-insert in the same database transaction so they succeed or fail together.

**Why:** Accepting this commits you to "abandoned checkout flows do not silently shrink the cart" — the spec already calls atomicity out as a hard requirement, so commit-time removal is the only path that doesn't contradict it.

**Verification:** Premise CONFIRMED at schema.sql + cartService; spec.md §Cart auto-remove cites atomicity ("order removes items from cart atomically"); no decisions.md entry conflicts; ORM transaction shape verified against installed version; no sub-95% dependencies.

**Also resolves:** "cart inconsistency on abandoned checkouts" prosecution; "missing transaction in item-select handler" finding.
```

For decisions that come out **`needs_human`** (the bar not met — escalated, not applied), render this variant so the audit trail shows exactly what is being escalated and why. Note the heading is **Escalate**, not Apply: nothing is edited for a `needs_human` decision.

```
### Decision [N]: [...]

**Options:** [...]

**Escalate (needs human — unmet: <the specific condition>):** [the leaning direction, framed as the concrete question the human must answer: "Leaning <X>; this holds only if <Y>, which I could not verify from <reason>. Need: <one-line answerable question>."]

**Why:** [one sentence naming the unmet condition — what blocks the ≥95% bar.]

**Verification:** [as normal, but stating the unmet condition explicitly.]

**Also resolves:** [...]
```

The "Need: …" question becomes this decision's sidecar `summary`, so the human's escalation is actionable. Unlike the interactive parent — where residuals are rare because an up-front batch pre-resolves most gaps — here **multiple residual blocks per report is normal**: there is no batch, so every gap that survives research is its own `needs_human` decision. Do not collapse or suppress them to make the report look cleaner; each one is a real escalation the factory must surface.

For **retraction-candidate** decisions (premise STALE/FALSE at HEAD), the situation has moved past the blocker — there is no fix to apply, and the resolution is "re-run the source skill." Group them at the end under a single "Items the situation has moved past" block (same shape as `/explain-blockers`; no `Apply` / `Verification` lines). In the sidecar, a retraction is `disposition: needs_human` with a `summary` of `retraction — premise stale at HEAD, re-run <source-skill>`: it is neither auto-applied (nothing to apply) nor silently looped (a stale premise means the world moved under the plan, which the human should see). It therefore escalates like any other residual.

### Director-language rules

Same baseline as `/explain-blockers` — the user is the director, not the implementer. They do not read source. File paths, line numbers, internal identifier names, `git` commands, and review-machinery vocabulary stay out of the rendered output **except** in two places where engineer-language compression is allowed:

- **The Verification line** — canonical filenames (`schema.sql`, `decisions.md`, `package.json`), package versions, gate names. Full paths and line numbers are still out. The Verification line is the evidence trail; naming files by their canonical basename is clearer than paraphrasing.
- **The Apply line, only when the change is a file/function-level edit** — canonical filenames and function/symbol names are allowed when the user can't act without them ("In `cartService.removeOnSelect`, …"). Director-language framing still dominates the sentence; the identifier is the anchor, not the whole line. Full paths and line numbers stay out.

Everywhere else (Options, Why, Also resolves, header, retraction block): plain language. Library names, framework names, features the user named themselves are fine. Internal identifiers only when the user already uses them.

---

## Write the resolution-state sidecar

This is the **machine-readable outcome the factory parses** — the authoritative result of the run. The rendered report above is only the audit trail; this file is what the coordinator reads to decide `RESOLVED` vs `RESIDUAL`. Write it **after** the full research pass and **before** auto-apply, so the outcome is durable even if an individual edit later fails to land.

**Path.** `~/.claude/cache/resolution-state/<slug>.json`, where `<slug>` is the basename (without `.json`) of the source state file this run resolved — the **same slug** the review/author skills use. A review-state file `data-import__dedup-filter.json` → resolution-state `data-import__dedup-filter.json`; a PR target → `<owner>__<name>__pr-<N>.json`. Create the `resolution-state/` directory if it does not exist. This is the only file this skill writes — the input review/author state files stay read-only.

**Shape.** One entry per decision in `decisions: []`, snake_case to match the other sidecars:

```json
{
  "decisions": [
    { "blast_radius": "chunk_local", "disposition": "auto_applied", "summary": "what was applied, one line" },
    { "blast_radius": "structural",  "disposition": "needs_human",  "summary": "Need: <one-line answerable question>" }
  ]
}
```

- **`disposition`** — exactly two values. `auto_applied` if the decision cleared all six conditions (and will be applied below). `needs_human` if it did not (a residual) **or** is a retraction candidate. Nothing else.
- **`blast_radius`** — `structural` if the decision's resolution touches an upper-authority artifact (the brief, `decisions.md`, or the engineering plan) — i.e. condition 4's authority-order analysis flagged an amendment — **or** if it could not be confidently classified (conservative default). `chunk_local` only when the blast radius is genuinely confined to the emitting chunk. This comes straight from the authority-order work already done per decision. (A single `structural` residual widens the factory's escalation scope to the whole feature, so do not under-classify.)
- **`summary`** — one line. For `auto_applied`, what was applied. For `needs_human`, the concrete `Need: …` question (or `retraction — premise stale at HEAD, re-run <source-skill>`).

The factory maps this file directly onto its `ResolutionOutcome`: **no** `needs_human` entries → `RESOLVED` (loop back to re-review); **any** `needs_human` entry → `RESIDUAL` (escalate; scope is `structural` if any residual is structural, else `chunk_local`). An empty `{"decisions": []}` (nothing was there to solve) reads as `RESOLVED`. Write the sidecar even when every decision is `auto_applied` — the factory needs the positive confirmation, not just an inferred absence.

---

## Auto-apply the cleared decisions

There is **no apply prompt** — the orchestrator routed here precisely to apply the cleared fixes, and that pre-authorization is the whole reason the headless skill exists. After the sidecar is written, work each **`auto_applied`** decision in dependency order (top of the DAG first), making the edits its **Apply** line describes.

- Edit only the plan / code / brief / PR. **State files stay read-only** — `~/.claude/cache/review-state/` and `~/.claude/cache/author-state/` are owned by the source-skill machinery; the resolution-state sidecar is the only file this skill writes.
- **Skip every `needs_human` decision** — residuals and retractions are escalations, not edits. Applying a leaning-but-unverified fix is exactly the failure the ≥95% bar exists to prevent; never fold a residual into the apply set.
- **Skip retraction items** — their resolution is "re-run the source skill," which the factory does by looping on `RESOLVED`; there is nothing to edit here.
- If an individual `auto_applied` edit cannot land cleanly (e.g. the cited code moved under you), do not force it: stop applying the rest of that decision's dependency subtree and note the failure in the result text. The factory's next re-review re-detects anything that didn't actually get fixed; a half-applied edit is worse than a re-detected blocker. Leave the sidecar entry as written — the outcome of record is what the research concluded, and the re-review is the backstop.

Do not re-invoke the source skill yourself (see Non-goals). Applying the fixes is the boundary where this skill's job ends; the coordinator loops back to the source review/author skill on `RESOLVED`, and that skill's round-memory / carry-forward machinery validates the applied edits on the next pass.

---

## Non-goals (explicit)

- **Never ask a question or wait for human input.** There is no operator in the headless thread. No `AskUserQuestion`, no plain-text question, no apply prompt, no "wait for the go-ahead." Every gap that would prompt the interactive parent to ask becomes a `needs_human` residual in the sidecar; the factory does the asking, one level up.
- **Do not edit during the research pass.** Verifying, scoring, and recommending stay read-only. Editing begins only after the sidecar is written, and only for `auto_applied` decisions. The ≥95% bar — not an operator yes — is the gate; it lowers but does not erase hallucination risk, which is why anything under the bar escalates instead of applying. Input state files stay read-only no matter what.
- **Do not invoke `/explain-blockers`, `/solve-blockers`, the v2 review skills, or the author skills.** This skill consumes their output; it does not call them. (It *reads* `/solve-blockers` and `/explain-blockers` SKILL.md for shared machinery — that is reference, not invocation.)
- **Do not modify input state files.** Both `~/.claude/cache/review-state/*.json` and `~/.claude/cache/author-state/*.json` are owned by their respective skill machineries. Read-only. The resolution-state sidecar is a separate file this skill owns and writes — that is not a violation of the read-only rule.
- **Do not relitigate the v2 / author classification.** If the source classified a blocker as `OPEN_QUESTION`, `STABLE_DISAGREEMENT`, etc., that class is fixed input. Research clarifies the resolution; it does not overturn the class. The single exception is the same as `/explain-blockers`: if verification finds the blocker's premise STALE/FALSE, the blocker becomes a retraction candidate.
- **Do not fabricate options.** When only one viable resolution exists, write "Single call: …" and stop. Padding with strawmen Option B/C is worse than naming one path cleanly.
- **Do not pull external docs speculatively.** Use `context7` only when condition 3 of the confidence bar actually requires it. Speculative library lookups inflate the work without raising confidence.
- **Do not weaken the bar to fit the research.** All six conditions are mandatory. If they can't be cleared, escalate the gap as a `needs_human` residual (or a retraction) — never round a sub-95% path up to `auto_applied`.
- **Do not run a second research pass to chase residuals.** One run produces one sidecar. A gap that survives the first pass is a residual, not a reason to loop — the factory escalates it, and a later coordinator round (after the human answers) re-runs this skill fresh.
- **Do not re-invoke the source review/author skills.** This skill does not call `/plan-review-v2`, `/engineering-plan-review-v2`, `/review-pr-v2`, or any author skill. The coordinator loops back to the source skill itself on `RESOLVED`; that is the factory's job, not this skill's.

## Failure modes to avoid

- **Auto-applying a sub-95% decision.** The single worst failure of the headless skill: research surfaces a 70%-confident path that is "probably right," and — because there is no operator yes to gate it — Claude applies it autonomously. The source skill then re-files a similar blocker next round, having now also churned the code. The bar is the *only* gate here. If a decision can't clear all six conditions, its disposition is `needs_human` and it is NOT applied. No exceptions.
- **Emitting a question into the headless thread.** `AskUserQuestion`, a plain-text "which do you prefer?", an apply prompt — any of these in a headless `claude -p` run hangs or is silently discarded, and either way the run produces no usable outcome. Every human-facing question is a `needs_human` residual instead.
- **Guessing a disposition or blast radius to avoid escalation.** Marking a genuine residual `auto_applied`, or a `structural` change `chunk_local`, to make the outcome look cleaner. The sidecar is the factory's only signal — a wrong disposition either applies an unverified fix or hides a feature-wide escalation. When unsure, the conservative call (`needs_human`, `structural`) is correct.
- **Engineer-language leakage outside Verification / Apply.** The Verification line and the Apply line are the only carve-outs for canonical filenames and identifier names. The Options / Why / Also-resolves lines stay director-language. (The audit-trail render still benefits from this discipline — a human reads it on escalation.)
- **Padding with strawmen.** Same as `/explain-blockers`. When only one option is viable, write "Single call: …"
- **Ignoring sibling dependencies.** Confidence does not propagate up through dependencies for free — a decision that presupposes another sub-95% decision is itself sub-95% (`needs_human`). Walking the dependency DAG is mandatory; a missed edge can auto-apply a fix whose premise is an unresolved sibling.
- **Forgetting to write the sidecar (or writing it after auto-apply).** No sidecar means the factory has no outcome to parse and must treat the run as a failed escalation — even if every fix applied cleanly. Write it after research, before apply, always — including the all-`auto_applied` and empty-`decisions` cases.
- **Spawning subagents for every blocker.** Inline execution is faster end-to-end at typical blocker counts (1–10) and preserves cross-blocker context for free. Use `Explore` agents only for individual blockers whose research is genuinely large (>20 files, extensive external-doc reading).
- **Premature output / partial sidecar.** Writing a per-decision block or the sidecar before the full research pass completes. Hold all output until research and the DAG are done — a decision's disposition can flip once a sibling dependency resolves, so an early-written entry can be wrong.

## Interaction with the round-memory / author-state machinery (do not break it)

This skill is a sibling, not a participant, of the v2 round-memory machinery or the author-side carry-forward machinery. It **reads** state files from `~/.claude/cache/review-state/` and `~/.claude/cache/author-state/` and never writes either; the one file it writes is its own `~/.claude/cache/resolution-state/<slug>.json` sidecar, which those machineries do not own. The auto-applied resolutions feed back into the source skill through the same channels as `/explain-blockers`: (a) plan/code/brief edits, (b) commit messages, (c) `decisions.md` entries, (d) the source skill's `recently_resolved_blockers` capture priority.

The skill closes by **auto-applying** the `auto_applied` decisions (see "Auto-apply the cleared decisions") and writing the resolution sidecar — that is the boundary where the read-only research pass ends and editing begins, gated by the ≥95% bar rather than an operator yes. It does not re-invoke the source skill; the coordinator does that when it loops back on `RESOLVED`, and the source skill's round-memory / carry-forward machinery validates the applied edits on that next pass. The input state files stay untouched throughout.

When the same artifact has BOTH a review-side state file and an author-side state file with unresolved blockers, the author-side blockers should generally resolve first (same dependency as in `/explain-blockers`). The orchestrator owns that ordering across lanes, but surface the dependency in the rendered report and resolve only the targeted side's blockers in this run — do not reach across to the other side's state file.
