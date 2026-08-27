---
name: solve-blockers
description: Researches each open blocker from a review or author verdict until it can recommend a concrete resolution at high confidence, with an evidence trail — then applies the fixes on your say-so. Use after `/explain-blockers` when you want answers rather than decisions to make, or directly on a state file or PR to skip triage.
user-invocable: true
---

# /solve-blockers

`/explain-blockers` answers *"what calls do I need to make?"* — a short ordered list of decisions, framed as choices the user makes.

`/solve-blockers` answers *"give me the answers, not just the questions."* — deeper per-blocker research, with a hard ≥95%-confidence floor, producing a concrete recommended resolution for every blocker. Same inputs, same stance (research read-only, then offer to apply on the operator's go-ahead), much heavier work.

The two skills are siblings, not a pipeline. You can:
- Run them back-to-back: `/explain-blockers` first to see the shape, then `/solve-blockers` to get answers. /solve-blockers reads the rendered /explain-blockers report from the conversation history and skips its own clustering.
- Skip the triage entirely and invoke `/solve-blockers` directly on a state file / PR / pasted verdict. /solve-blockers does its own clustering in that case.

The 95% confidence bar is the load-bearing discipline. It is what distinguishes a solve-blockers recommendation from an explain-blockers "Claude's pick." Below the bar, the skill does not invent a confident-sounding answer — it identifies the specific blocking question, batches it with any other unknowns across all blockers, and asks the user *once* up-front. Only after those questions are answered does the report render. This pre-empts the failure mode where Claude ships a low-confidence solution under high-confidence framing, which is the failure mode the v2 machinery exists to prevent in the first place.

The skill's **research pass is read-only**: it verifies, scores, and recommends without touching the plan, the code, the PR, or any state file. After the solution list is rendered, the skill asks the operator whether to go ahead and apply the fixes; on an explicit yes, Claude applies them (state files always stay read-only). This is the same shape as `/explain-blockers`: the v2 machinery classified these blockers as "user must adjudicate", so nothing changes until the operator gives the go-ahead. The ≥95% bar raises confidence but does not eliminate the hallucination / authority-bypass risk, which is exactly why applying is gated on that explicit yes rather than done silently.

The skill runs **in the main conversation thread** by default. Per-blocker research is heavier than `/explain-blockers` — typically 10–30 Read/grep calls per blocker, plus `context7` lookups when third-party library behavior matters — but is still tractable inline at typical blocker counts (1–10). For unusually heavy single-blocker research (>20 files spread across a monorepo, or extensive external-doc reading), spawn one `Explore` agent for that blocker; cross-blocker context stays in the main thread.

## Shared scaffolding (read on demand)

- `~/.claude/skills/_review-common/blocker-classes.md` — the registry of blocker classes, their meanings, and prescribed resolution shape. Consult on any unfamiliar class.
- `~/.claude/skills/explain-blockers/SKILL.md` — sibling skill. Its **Locate and parse blockers** section defines the deterministic input-parsing logic that this skill reuses; its **Render the decision list** section defines the output format for the per-decision blocks (this skill extends that format with `Apply` and `Verification` lines). Consult when input parsing or output format details are unclear.

## When to use vs `/explain-blockers`

| Question the user is asking | Skill |
|---|---|
| What decisions do I need to make? Just show me the shape. | `/explain-blockers` |
| Decide for me — research it and tell me what to do. | `/solve-blockers` |
| I ran explain-blockers, now go deep on the calls it surfaced. | `/solve-blockers` (reads explain-blockers report from history) |

Both skills research read-only and recommend, then close by offering to apply (`/explain-blockers` also offers to hand off to `/solve-blockers`); neither touches state files. The difference is research depth and the ≥95% bar — not which one can edit.

## Inputs

`$ARGUMENTS` is matched against these shapes in priority order; the first that yields a parseable target wins.

1. **No arguments** — check the current conversation history (scrollback in the active session) for a recently rendered `/explain-blockers` report (look for the header `# Decisions you need to make:` near a recent assistant turn). If present, treat it as the canonical decision scaffold and re-derive the underlying state file from the source identifier in the report's header (feature name, PR reference). If no /explain-blockers report is visible in history, fall back to the **latest** state-file logic from `/explain-blockers` (`~/.claude/cache/review-state/*.json` ∪ `~/.claude/cache/author-state/*.json` sorted by mtime, skipping CLOSED / clean APPROVED). The conversation-history case is the most common usage pattern — the user runs the two skills back-to-back. If both signals exist *and* point to different artifacts (e.g., a /explain-blockers report in scrollback for feature A AND a newer state file on disk for feature B), surface the candidates and ask which the user meant — do not silently pick one.

2. **`from-explain`** (literal) — explicit instruction to consume the most recent `/explain-blockers` report from conversation history. Errors out if no such report is visible in scrollback. Use this when conversation history has multiple state-file references and you want to be explicit about which the user means.

3. **`latest`** — explicit fall-through to the state-file `latest` logic, bypassing any conversation-history `/explain-blockers` report. Use when the user wants to re-research even though they just ran /explain-blockers.

4. **Slug / state-file path / author-artifact reference / PR reference / pasted verdict text** — same shapes and resolution rules as `/explain-blockers`. Read its **Inputs** section for the exact match logic and priority among these five; they share the same parsing branch verbatim.

5. **`/explain-blockers` report path** — absolute or `~`-relative path to a saved `/explain-blockers` report (typically `~/.claude/cache/explain-blockers/<slug>__<timestamp>.md`). Parse the decision blocks and re-derive the underlying state file from the report header. Use for cross-session work where the conversation history doesn't carry the prior report.

6. **Pasted `/explain-blockers` report text** — raw markdown beginning with `# Decisions you need to make:`. Parse the same way as input 5.

If none yield a target, stop and ask the user what they meant. Do not guess.

### Decision scaffold from an /explain-blockers report

When the resolved input is an `/explain-blockers` report (from history, path, or pasted text — inputs 1 when history-found, 2, 5, 6), parse the rendered decision blocks into a structured `decisions: []` array:

```
decisions: [
  {
    index: 1,
    question: "<one-line question from the heading>",
    options: ["Option A — ...", "Option B — ..."]  | "single",
    pick: "<Claude's pick text>",
    resolves_blockers: ["<also-resolves phrase 1>", "<also-resolves phrase 2>", ...]
  },
  ...
]
```

Cross-reference the rendered "resolves" phrases back to the raw blocker entries in the source state file. The state file gives `blocker_class`, `path_or_section`, `summary`, `raised_in`, etc. — the per-class research mandate below keys off `blocker_class`, so this cross-reference is mandatory. If the state-file source is ambiguous (multiple recent files, no clear header identifier in the report), ask the user before proceeding.

### Decision scaffold from raw blockers

When the resolved input is a raw state file / PR / pasted verdict (no /explain-blockers report involved — inputs 1 when history-not-found, 3, 4), the skill does its own clustering, identical to `/explain-blockers` step 2b. Read `/explain-blockers` SKILL.md for the clustering tests ("same cluster" vs "different cluster"). The resulting cluster set becomes the `decisions: []` array, formatted the same way as the /explain-blockers-derived version.

Either way, the rest of the skill operates on `decisions: []` — the source path is invisible after this step.

### Pre-flight verdict-status check (raw-blocker path only)

When the input resolved to a raw state file / PR / pasted verdict, apply the same pre-flight as `/explain-blockers` before any clustering or research:

- Verdict is `NEEDS_USER_INPUT` (any source skill, either side), **OR**
- Verdict is `APPROVED` and `prior_blockers` contains `IMPLEMENTABILITY_GAP` entries (engineering-plan or spec layer, either review or author side), **OR** `SPEC_BOUNDARY_UNBOUND` entries (vision layer, either side). None of those gates the `APPROVED` it arrives on — at the engineering-plan and vision layers they gate `CLOSED`, and at the spec layer the gap blocks only `/brief-author` for the brief slug it names — so an APPROVED verdict carrying them is the normal shape at those layers, not an anomaly.

If neither holds (CLOSED, clean APPROVED, etc.), surface the status to the user and stop — there is nothing to solve.

If the verdict is `DRAFT_EMITTED` (author-side only), refuse the same way `/explain-blockers` does: the author skill skipped its hardening stages. Tell the user to re-invoke the author skill without `--draft` and then re-invoke /solve-blockers on the resulting state file. Do **not** research a draft — its blockers are not the real blockers.

When the input is an /explain-blockers report (history / path / text), this pre-flight is implicit — /explain-blockers wouldn't have rendered a decision list for a CLOSED / clean-APPROVED / DRAFT_EMITTED state. Skip the check; the report is sufficient evidence.

Echo a one-line confirmation to the user:

```
Researching N decisions (covering M blockers) from <plain source name>.
```

Do not list the decisions individually here. The user will see them rendered in full once research completes.

---

## The 95%-confidence bar (explicit calibration)

A recommended solution qualifies as ≥95% confidence only when **all six** of these conditions hold. Each condition must be checkable mechanically or by direct observation — none rely on Claude's self-rating of certainty.

1. **Premise CONFIRMED against repo HEAD.** The blocker's factual claims about repo state (file contents, function signatures, schema fields, dependencies, lint/test status) have been verified against the current working tree. If the blocker cites `foo.ts:42 calls bar()`, the verification reads `foo.ts` at HEAD and confirms the call. If the blocker's premise is STALE or FALSE, the solution path changes — surface the retraction explicitly rather than recommending a fix for a problem that no longer exists.

2. **Single viable resolution OR clear dominance.** Either only one resolution makes sense given the constraints, or one resolution strictly dominates alternatives on every relevant axis: correctness, blast radius, alignment with brief Goals / Non-goals, conformance to `decisions.md` bindings, follow-on cost, reviewer reaction. "Slightly cleaner" is not dominance — every relevant axis must favor (or be neutral on) the recommended path.

3. **No unverified external-library assumptions.** If the solution depends on third-party library behavior (API shape, default config, version-specific quirk, error semantics), that behavior has been verified via the `context7` MCP server (`resolve-library-id` → `query-docs`) or by reading the library's source / type definitions in `node_modules` or equivalent. "I remember React works this way" does not count. Verification must cite the library version actually installed (`package.json` / `Cargo.toml` / `requirements.txt`).

4. **Authority order respected.** The solution does not contradict a bound entry in `decisions.md` for the feature (when feature-scoped — only Active-section `Status: bound` entries are authoritative; a `superseded`/`obsolete` entry in the `## Archived` tail is not a bound entry to contradict, per `~/.claude/skills/_review-common/principles.md` § What counts as a bound entry), the brief's Goals / Non-goals / User-facing changes (Class A), the engineering plan's chunk-DAG decisions (Class B), or `~/.claude/CLAUDE.md` / project `CLAUDE.md` rules. The class-aware authority order in `~/.claude/skills/_review-common/principles.md` § Cross-artifact authority order is binding: brief > decisions.md > engineering plan (Class A); decisions.md > engineering plan (Class B). If the recommended solution would require amending an upper-authority artifact, that becomes a downstream call (flag explicitly in the verification line) — not a reason to weaken the recommendation.

5. **No open dependency on a sub-95% sibling blocker.** If two blockers are linked such that solution X for blocker A presupposes solution Y for blocker B, then Y must also be at ≥95% within this same pass before X can be confirmed at ≥95%. Cascading low confidence through dependencies is a forbidden short-circuit — each cluster head must clear the bar on its own merits OR the entire cluster gets the unknown-question treatment.

6. **User stake articulable in one sentence.** Claude must be able to write, in a single concrete sentence, what the user is committing to by accepting this solution. Not the implementation reason ("uses the existing helper") — the user-visible commitment ("the watchlist auto-remove will fire even when the ranking is created via the import path, not just the rate-a-thing flow"). If the stake can't be articulated cleanly, the framing isn't tight enough, which means the research isn't deep enough, which means the bar isn't met.

**All six are mandatory.** If any one fails, the recommendation does not qualify as ≥95%. Either continue research to close the gap, or escalate to the up-front user-question batch (next section). Do not weaken the bar to fit the available research.

---

## Workflow

```
$ARGUMENTS
   ↓
Locate and parse → decisions: []        (deterministic; reuses /explain-blockers logic)
   ↓
Pre-flight verdict-status check          (skipped when input is an /explain-blockers report)
   ↓
Per-decision research pass               (each decision researched individually against conditions 1–4, 6)
   ↓
Build sibling-dependency DAG             (condition 5 — verify acyclic, propagate confidence floor)
   ↓
Identify decisions still under the bar   (any condition unmet after research)
   ↓
If any: batch ALL unknowns → AskUserQuestion (one round, never two) → resume affected decisions
   ↓
Render solution list                     (per-decision blocks with Apply + Verification lines)
   ↓
Ask whether to apply the fixes           (no default — wait for the go-ahead)
```

There is no inner loop after the user-question batch. If a second pass of research reveals new unknowns after the user has already been asked once, surface them as flagged residuals on the specific affected decisions — do not loop the user a second time. Two-step questioning erodes trust in the skill; one batched ask, then the report, is the contract.

---

## Deep research per decision

This is the heart of the skill. Each decision in `decisions: []` gets researched until its recommended resolution meets the ≥95% bar — or until the research identifies a specific blocking question that has to be asked.

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

### When research cannot reach ≥95%

Some gaps are not closable by Claude alone. Examples:
- The blocker hinges on a user preference not documented anywhere (e.g., naming convention, error-message tone, performance/clarity tradeoff).
- The blocker requires runtime evidence Claude can't gather (e.g., production traffic patterns, real-device behavior, third-party API live response).
- The blocker depends on an architectural intent the user has not articulated.
- External library behavior is genuinely ambiguous (docs missing, multiple plausible interpretations).

For each such gap, identify the **specific question** that, when answered, would let research resume. Frame the question concretely — not "what do you want?" but "should the watchlist removal fire (a) only when the ranking commits, or (b) immediately when the user picks a tier even if they abandon comparisons?"

After researching all decisions, gather all such questions into a single up-front batch. Surface them to the user **before** rendering any solutions:

```
I need answers to N questions before I can recommend solutions at ≥95% confidence on every decision.

1. [Decision <index>] <concrete question>?
   Options: <A>, <B>, <C> (if discrete) — or open-ended if not.

2. ...
```

Use the `AskUserQuestion` tool for discrete-choice questions (≤4 options). Use a plain text prompt for open-ended ones. After the user answers, resume the per-decision research pass for the affected decisions with the new constraints, then render the final report.

**One batched ask, not multiple rounds.** If the user's answers reveal new unknowns during the second research pass, flag them in the final report as residual uncertainty for that specific decision — do not loop the user again. Two-step questioning erodes trust; one ask, then results.

---

## Render the solution list

The output is the header plus per-decision blocks in dependency order (or in the order /explain-blockers already laid out, if that's the input source — the user has already mentally mapped the decision indices, so don't reshuffle).

### Header

```
# Recommended solutions: <plain-language source identifier>

**N decisions settled.** <if any flagged residuals: "K aren't fully settled — each says below what's still open."> <if any retraction candidates: "Plus M items the situation has moved past — re-run /<source-skill> to clear them.">

---
```

The source identifier matches what `/explain-blockers` used (feature name, PR title) — not the state-file path. "Settled" means the decision hit the ≥95% bar cleanly — the bar stays internal; the report never renders percentages except on a not-fully-settled block.

### Per-decision block

Each decision is a self-contained block. The format extends `/explain-blockers`' per-decision template with two new lines: **Apply** (the concrete change to make) and **Verification** (the evidence trail justifying the ≥95% bar). The original `Options` and `Also resolves` lines carry over unchanged; `My pick` becomes `Why` (one-sentence dominance reasoning).

```
### Decision [N]: [one-line question, phrased as a choice — verbatim from /explain-blockers if input was a report; otherwise match /explain-blockers framing]

**Options:** [Option A — one short clause]; [Option B — one short clause]. (Or "Single call: [one short clause]" if there is no real second option.)

**Apply:** [the concrete change — the actual edit to make, in plain language. Director-language by default; canonical filenames OK here. One short paragraph or a tight bullet list, not prose.]

**Why:** [one sentence. Lead with what accepting this commits the user to (the user-stake sentence from condition 6). Add a single clause on the dominant axis if the stake doesn't carry it alone.]

**Verification:** [one line, plain language: what was checked and what it showed. Say "I confirmed X is still true in the code / the spec says Y / the decision log has nothing against it / the installed version of <library> does Z". The six confidence conditions are the internal checklist — never render their names. If the fix needs an upstream doc changed first, say which doc in plain words.]

**Also resolves:** [linked blockers, one short phrase each, comma-separated. Omit if the cluster is a singleton.]
```

**Worked example (illustrative — not real blockers):**

```
### Decision 2: Should the watchlist auto-remove fire on tier-pick or only on ranking commit?

**Options:** Fire on tier-pick (immediate); fire on commit (atomic with ranking).

**Apply:** In the watchlist-removal logic, move the trigger from the tier-pick handler to the ranking-commit transaction. Wrap removal and ranking-insert in the same Prisma transaction so they succeed or fail together.

**Why:** Accepting this commits you to "abandoned comparison flows do not silently shrink the watchlist" — the spec already calls atomicity out as a hard requirement, so commit-time removal is the only path that doesn't contradict it.

**Verification:** I confirmed the trigger really lives in the tier-pick handler today; the spec says ranking removes from the watchlist atomically; nothing in the decision log conflicts; the installed Prisma version supports the transaction shape.

**Also resolves:** the related worry that abandoned comparisons leave the watchlist out of sync.
```

For decisions that carry residual uncertainty (the bar not fully met even after the user-question batch — rare by design), use this variant:

```
### Decision [N]: [...]

**Options:** [...]

**Apply (not fully settled — ~XX% sure):** [the leaning concrete change, with one explicit clause naming the unresolved condition: "Apply <X>; this holds if <Y> is true — I could not verify <Y> from <reason>."]

**Why:** [as normal, but call out the unmet condition.]

**Verification:** [as normal, but with the unmet condition stated.]

**Also resolves:** [...]
```

Residual-uncertainty blocks exist only for the case where the user's answer to the up-front batch still leaves a smaller gap that doesn't merit a second round trip. If you find yourself writing more than one residual block per report, the up-front batch was probably underspecified — go back to that step.

For retraction-candidate decisions (premise STALE/FALSE), group at the end under a single "Items the situation has moved past" block — same shape as `/explain-blockers`. No `Apply` or `Verification` lines needed; the resolution is "re-run /<source-skill>".

### Director-language rules

Same baseline as `/explain-blockers` — the user is the director, not the implementer. They do not read source. File paths, line numbers, internal identifier names, `git` commands, and review-machinery vocabulary stay out of the rendered output **except** in two places where engineer-language compression is allowed:

- **The Verification line** — canonical filenames (`schema.prisma`, `decisions.md`, `package.json`), package versions, gate names. Full paths and line numbers are still out. The Verification line is the evidence trail; naming files by their canonical basename is clearer than paraphrasing.
- **The Apply line, only when the change is a file/function-level edit** — canonical filenames and function/symbol names are allowed when the user can't act without them ("In `watchlistService.removeOnTierPick`, …"). Director-language framing still dominates the sentence; the identifier is the anchor, not the whole line. Full paths and line numbers stay out.

Everywhere else (Options, Why, Also resolves, header, retraction block): plain language. Library names, framework names, features the user named themselves are fine. Internal identifiers only when the user already uses them.

**Banned vocabulary — nowhere in the rendered report, including Verification and Apply.** The review machinery's own words mean nothing to the user and read as noise. Never render: blocker-class labels (`OPEN_QUESTION`, `SURFACE_PARITY_GAP`, any ALL-CAPS class), "blocker class", "premise", "prosecution", "prosecutor", "persona", "carry-forward", "round-memory", "round N", "tier", "HARD"/"SOFT", "sidecar", "state file", "authority order", "verdict", "finding", "retraction", "residual". Say what happened instead: "the review flagged…" not "the persona filed a finding"; "I checked the claim is still true" not "premise CONFIRMED"; "this one's moved past — the code already changed" not "retraction candidate"; "not fully settled" not "residual". A machinery word is allowed only when the user typed it first in this conversation.

**Last pass before rendering.** Reread the whole report as the user: short sentences (about twenty words), one idea each, no abbreviation the report didn't spell out first, no term that needs this skill's definitions to parse. Any sentence that fails gets rewritten in plain words — not deleted, the content stays; only the register changes.

---

## After rendering — offer to apply

Do **not** offer to save the report — it's already in scrollback, and the operator wanted answers, not a file. Instead, after the solution list is rendered, ask the operator once whether to go ahead and apply the fixes. Use `AskUserQuestion` (apply / don't apply). There is no default — wait for the answer.

- If **yes**: work each decision in dependency order (top first), making the edits its **Apply** line describes. Only the plan / code / brief / PR change — **state files stay read-only** (`~/.claude/cache/review-state/` and `~/.claude/cache/author-state/` are owned by the source-skill machinery). Skip retraction-cluster items — their resolution is "re-run the source skill", not an edit. For a residual-uncertainty decision, apply its leaning fix only if the operator confirms that specific one; the residual flag means the ≥95% bar wasn't fully met, so don't fold it silently into a blanket "apply all". When the edits land, name the source skill to re-invoke so its round-memory / carry-forward machinery validates them.
- If **no**: stop. The recommendations stand in scrollback — the operator can ask Claude to apply any of them in a later turn, or re-run the source skill once they're applied.

**Final line — verdict banner.** Every terminal path of this skill ends with the shared verdict-banner script's fenced stdout, emitted verbatim as the very last thing in the response (`~/.claude/skills/_review-common/blocker-classes.md` § Verdict banner, "The triage pair banners too"). `--skill` names the SOURCE skill to re-invoke; `<ROUND>` is the source verdict's round (`?` when the source carried none):

- **Yes** (fixes applied) → `RESOLVED`, count = blockers the applied decisions cover. Decisions the operator excluded (declined residuals, retraction clusters) stay out of the count.
- **No** (recommendations stand) → `DECISIONS PENDING`, count = decisions rendered.
- Refusal paths (e.g. a `DRAFT_EMITTED` source) → `DECISIONS PENDING`, count 1, `--skill` naming the author skill to re-run.
- Nothing to research (clean `APPROVED` / `CLOSED`) → echo the source verdict's status, round, and blocker count.

The banner's machine vocabulary (`VERDICT`, blocker counts) is exempt from the banned-vocabulary rule — it is the pipeline's shared status line, not report prose.

---

## Non-goals (explicit)

- **Do not edit during the research pass.** Verifying, scoring, and recommending are read-only. Editing begins only after the solution list is rendered and only on the operator's explicit yes to the apply prompt (see "After rendering — offer to apply"); the ≥95% bar lowers but does not erase hallucination risk, so applying is always gated on that go-ahead. State files stay read-only no matter what.
- **Do not invoke `/explain-blockers`, the v2 review skills, or the author skills.** This skill consumes their output. If the user wants triage instead of solutions, they invoke `/explain-blockers` separately.
- **Do not modify state files.** Both `~/.claude/cache/review-state/*.json` and `~/.claude/cache/author-state/*.json` are owned by their respective skill machineries. Read-only.
- **Do not relitigate the v2 / author classification.** If the source classified a blocker as `OPEN_QUESTION`, `STABLE_DISAGREEMENT`, etc., that class is fixed input. Research clarifies the resolution; it does not overturn the class. The single exception is the same as `/explain-blockers`: if verification finds the blocker's premise STALE/FALSE, the blocker becomes a retraction candidate.
- **Do not fabricate options.** When only one viable resolution exists, write "Single call: …" and stop. Padding with strawmen Option B/C is worse than naming one path cleanly.
- **Do not pull external docs speculatively.** Use `context7` only when condition 3 of the confidence bar actually requires it. Speculative library lookups inflate the work without raising confidence.
- **Do not weaken the bar to fit the research.** All six conditions are mandatory. If they can't be cleared, surface the gap — through the user-question batch, through a flagged residual, or through retraction — rather than rounding up.
- **Do not multi-round the user-question batch.** One ask, then the report. New unknowns surfaced during the second research pass become flagged residuals on their specific decisions, not a second round of questions.
- **Do not loop the source review skills.** This skill does not re-invoke `/plan-review-v2`, `/engineering-plan-review-v2`, `/review-pr-v2`, or any author skill. The user re-invokes the source skill themselves after applying resolutions.

## Failure modes to avoid

- **Settling for "good enough" instead of ≥95%.** The most common failure: research surfaces a 70%-confident path that is "probably right," Claude writes the report, the user applies it, the source skill re-files a similar blocker next round. The whole point of the skill is the bar. If you can't clear it, escalate (user-question batch or residual flag) — do not ship a confidently-framed low-confidence recommendation.
- **Skipping the up-front question batch.** Writing residual-uncertainty blocks for things the user could have answered in one question. Residuals are for gaps that survive a question (e.g., library behavior is genuinely ambiguous even after user clarifies intent) — not for "I didn't bother asking."
- **Asking the user mid-rendering.** All user questions are batched up-front, **before** any solution block is rendered. Interrupting the report to ask a clarifying question forces the user to re-load context twice and erodes trust in the skill's planning.
- **Two-round user questions.** First batch surfaces N questions, user answers, second pass surfaces M more. Don't. New gaps that emerge after the user has answered are residuals, not a second batch.
- **Engineer-language leakage outside Verification / Apply.** The Verification line and the Apply line are the only carve-outs for canonical filenames and identifier names. The Options / Why / Also-resolves lines stay director-language. Cross-contamination ("file paths everywhere") undoes the rendering discipline.
- **Machinery vocabulary anywhere in the report.** The filename carve-out above is not a jargon carve-out: "premise CONFIRMED", class labels, "prosecution", "residual" and the rest of the banned list are out even on Verification/Apply lines. If a line only makes sense to someone who has read this skill, it isn't done.
- **Padding with strawmen.** Same as `/explain-blockers`. When only one option is viable, write "Single call: …"
- **Ignoring sibling dependencies.** Confidence does not propagate up through dependencies for free — a recommendation that presupposes another sub-95% recommendation is itself sub-95%. Walking the dependency DAG is mandatory.
- **Reshuffling the decision order when input was an /explain-blockers report.** The user has already mentally mapped the indices. Keep the order /explain-blockers used. Reordering forces them to re-read.
- **Spawning subagents for every blocker.** Inline execution in the main thread is faster end-to-end at typical blocker counts (1–10) and preserves cross-blocker context for free. Use `Explore` agents only for individual blockers whose research is genuinely large (>20 files, extensive external-doc reading).
- **Premature output.** Writing a per-decision block as you research instead of waiting for the full pass to complete. Premature output forecloses the question-batching step — if you've already rendered Decision 1 and now Decision 3 needs a user clarification, you've already committed to a flow that breaks. Hold all output until the full research pass (or two passes, around the question batch) is done.

## Interaction with the round-memory / author-state machinery (do not break it)

This skill is a sibling, not a participant, of the v2 round-memory machinery or the author-side carry-forward machinery. It reads state files from `~/.claude/cache/review-state/` and `~/.claude/cache/author-state/`; it never writes either. The user's eventual application of the recommended solutions feeds back into the source skill through the same channels as `/explain-blockers`: (a) plan/code/brief edits, (b) commit messages, (c) `decisions.md` entries, (d) the source skill's `recently_resolved_blockers` capture priority.

The skill now closes by asking whether to apply (see "After rendering — offer to apply"). On a yes, Claude applies the fixes following each decision's `Apply` line — this is the boundary where the read-only research pass ends and editing begins. On a no, the operator can still ask Claude to apply any decision in a later turn. Either way state files stay untouched, and the resolutions feed back into the next source-skill invocation, not through this skill.

When the same artifact has BOTH a review-side state file and an author-side state file with unresolved blockers, the user should generally resolve the author-side blockers first (same dependency as in `/explain-blockers`). Surface this dependency in the report header when both sides have entries for the same artifact slug.
