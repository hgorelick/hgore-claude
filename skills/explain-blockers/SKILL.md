---
name: explain-blockers
description: Triages the open blockers from a review or author verdict into a short, ordered list of decisions for you to make — linked blockers collapsed into one call, ordered so the top decision unblocks the ones below, written in plain language with Claude's pick on each. Use when a skill returns NEEDS USER INPUT. Sister to `/solve-blockers`, which researches the answers instead.
user-invocable: true
---

# /explain-blockers

Every layer of the artifact chain emits verdicts that list blockers needing user input, from the vision map down to the PR — the reviewers (`/vision-review`, `/spec-review`, `/brief-review-v2`, `/engineering-plan-review-v2`, `/plan-review-v2`, `/review-pr-v2`) and the authors (`/vision-author`, `/spec-author`, `/brief-author`, `/engineering-plan-author`, `/plan-author`). Both halves write blockers in the same shape with the same blocker classes (registered in `~/.claude/skills/_review-common/blocker-classes.md`), persisted to parallel cache directories: `~/.claude/cache/review-state/` and `~/.claude/cache/author-state/`. This skill triages any of them, transparently.

The verdict prose itself is written by Claude for Claude — full of file paths, line numbers, internal class names, and review-machinery jargon. The user reading the verdict did not write the code or the plan; Claude did. The user is the **director**, not the implementer. They make decisions; they do not read source.

This skill is a **triage**, not a per-blocker briefing. The output is a short ordered list of *decisions*, not a per-blocker walkthrough. Linked blockers (where one user call resolves multiple items) collapse into a single decision. Decisions are ordered so the top one unblocks the ones below — the user works top-down and watches their open-item count fall faster than the number of calls they make.

Aggressive concision is a feature: each decision should fit in roughly five short lines. No effort estimates, no expository "Why it matters" paragraph, no labeled multi-bullet option structure, no per-blocker section per blocker. If something doesn't help the user pick faster, it doesn't go in. File paths, line numbers, identifier names, and other code-level shrapnel stay in Claude's working notes — out of the rendered report — except where they're load-bearing for the decision (e.g., naming an external library, a feature the user named themselves, or a concept they used in their own instructions).

The skill's **triage is read-only**: it researches, clusters, and recommends without touching the plan, the code, the PR, or any state file. Only *after* the decision list is rendered does it ask the operator whether to apply Claude's picks or hand off to `/solve-blockers` — editing happens solely on that explicit say-so, and state files stay read-only throughout. Blockers labeled `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `BRIEF_AMENDMENT_NEEDED`, `IMPLEMENTABILITY_GAP`, `UNCORROBORATED_RESET`, etc. are by construction the items the v2 machinery refused to auto-resolve — so during triage, pre-empting that adjudication would re-introduce the very "orchestrator decided for the user" failure mode the v2 skills are engineered to prevent; the apply step happens only when the operator chooses it.

The skill runs **in the main conversation thread** — no subagents. Blocker counts are small (typically 1–10), each blocker's research is a handful of Read / grep calls, and inline execution is faster than spawning agents and marshaling their reports back. Cross-blocker synthesis is free when everything is in the same context.

## Shared scaffolding (read on demand)

- `~/.claude/skills/_review-common/blocker-classes.md` — the registry of blocker classes, their meanings, and prescribed resolution shape. The per-class research mandate below is derived from it. Consult on any unfamiliar class.

## Inputs

`$ARGUMENTS` is matched against these shapes in priority order; the first that yields one or more parseable blockers wins:

1. **No arguments / `latest`** — list `~/.claude/cache/review-state/*.json` AND `~/.claude/cache/author-state/*.json` sorted by mtime (most-recent first across both directories). For each candidate, check `last_verdict`: skip files where the verdict is `APPROVED` (with empty `prior_blockers`) or `CLOSED` (the vision and engineering-plan layers, the two that emit it — also empty `prior_blockers`). `APPROVED` may legitimately carry blockers that do not gate it — `IMPLEMENTABILITY_GAP` on an engineering-plan or spec file, `SPEC_BOUNDARY_UNBOUND` on a vision file — and those DO need triage, so don't skip APPROVED unconditionally; check whether `prior_blockers` is empty. Pick the first remaining candidate. If two or more candidates were modified within the same hour, surface the candidate list and ask the user which to target — state files persist across rounds (review-side) and across authoring invocations (author-side), so the most recently *touched* file is not always the one the user means.
2. **Slug** — bare token matching `~/.claude/cache/review-state/<slug>.json` OR `~/.claude/cache/author-state/<slug>.json`. Check review-state first, then author-state. If both exist for the same slug (e.g., the user has authored AND reviewed the same engineering plan — common pattern), and both have unresolved blockers, ask the user which they meant; reviewer-side and author-side blockers are not necessarily the same set.
3. **State-file path** — absolute or `~`-relative path to a JSON state file. Load directly. The path's parent directory tells you which side it's from (`review-state` vs `author-state`).
4. **Author-side artifact reference** — `brief <feature>` resolves to `~/.claude/cache/author-state/<feature>__brief.json`; `eng-plan <feature>` to `<feature>__engineering-plan.json`; `chunk <feature>/<chunk-slug>` to `<feature>__<chunk-slug>.json`. These shortcuts let the user reference a specific authoring artifact without typing the full slug pattern. For a **tracked** feature (engineering plans under `features/<feature>/plans/<track>/` — see `~/.claude/skills/_plan-common/layout.md`), the track is a slug segment: `eng-plan <feature>/<track>` → `<feature>__<track>__engineering-plan.json`, `chunk <feature>/<track>/<chunk-slug>` → `<feature>__<track>__<chunk-slug>.json`. A bare `eng-plan <feature>` against a tracked feature matches more than one state file — list them and ask which.
5. **PR reference** — `pr <N>`, `pr #<N>`, `#<N>`, or `<owner>/<repo>#<N>`. Resolve via `gh pr view <N> --json reviews --jq '.reviews[] | select(.body | startswith("## Tribunal v2 — Verdict:"))'` to pull v2 verdict review comments (these are posted by `gh pr review --comment`, not as plain issue comments — `gh pr view --comments` would miss them). Take the most recent. Parse the `### Blockers` section for class + body lines. (PR-source blockers come only from `/review-pr-v2` — author skills don't post to PRs.)
6. **Pasted verdict text** — raw markdown containing `## Tribunal v2 — Verdict:` (PR), `### Plan Status:` (plan reviews), `### <Vision|Spec|Brief> Status:` (the upper-layer reviewers), or `# <Vision|Spec|Brief|Engineering plan|Chunk plan> authoring verdict —` (author skills, one alternative per authoring layer). Parse blocker lines from the `### Blockers` block.

If none yield blockers, stop and ask the user what they meant. Do not guess.

## Workflow

```
$ARGUMENTS
   ↓
Locate and parse blockers       (deterministic, no LLM judgment)
   ↓ produces normalized blocker[]
Research, cluster, triage       (inline, main thread)
   ↓ research each blocker enough to know what call resolves it,
   ↓ then cluster blockers under shared decisions, then order decisions
   ↓ by dependency
Render list, then apply or hand off  (short output, top-down ordered)
```

There is no inner loop and no re-invocation of the v2 skills. After the decision list renders, the operator chooses whether Claude applies the picks or hands off to `/solve-blockers`; either way, the next invocation of the reviewer that raised them — `/vision-review`, `/spec-review`, `/brief-review-v2`, `/engineering-plan-review-v2`, `/plan-review-v2`, or `/review-pr-v2` — picks up the resolutions through that skill's round-memory machinery.

---

## Locate and parse blockers (deterministic)

Resolve `$ARGUMENTS` to one of three sources. The first is preferred when available:

- **State file** — gives structured `blocker_class`, `path_or_section`, `summary`, `raised_in_round` (or `raised_in_invocation` for PR), `current_reclassification_justification` (when present), the `plan_path` / `artifact_path` or PR reference, and round/invocation metadata. Both review-state and author-state files share this schema; the parser is identical. The `state_kind` (review vs author) is derived from the parent directory.
- **PR review comment body** — less structured but contains every blocker line. Recover `blocker_class` from the bracketed tag at the start of each blocker line, `path_or_section` and `summary` from the body text. PR-source only — author skills don't post to PRs.
- **Inline pasted text** — least structured. Best-effort parse, no inferred metadata beyond what is in the text. Author-skill verdict text follows the same `[CLASS] <span> — <summary>` per-line shape under the `### Blockers (if NEEDS_USER_INPUT)` header, so the same parser works.

**Pre-flight check before parsing.** Read `last_verdict` (review-state) or `verdict` (author-state) from the file (or look for the verdict header line in PR/inline cases). Confirm at least one of:
- Verdict is `NEEDS_USER_INPUT` (any source skill, either side).
- Verdict is `APPROVED` AND `prior_blockers` contains entries with class `IMPLEMENTABILITY_GAP` — applies to BOTH `/engineering-plan-review-v2` / `/engineering-plan-author` (cross-chunk decisions remain undecided) AND `/spec-review` / `/spec-author` (the imagined-brief-author dry run left a brief unauthorable; the gap is keyed by brief slug and blocks `/brief-author` for that slug alone). Either side, either layer: `APPROVED` means shape-correct with decisions outstanding, which is exactly what these blockers triage.
- Verdict is `APPROVED` AND `prior_blockers` contains entries with class `SPEC_BOUNDARY_UNBOUND` — `/vision-review` / `/vision-author`, the same semantic one layer further up. That class gates `CLOSED` and not `APPROVED`, so an APPROVED vision map with unbound boundary calls is the normal state to triage, not an anomaly.

If none of these holds, surface the verdict status and the empty/closed blocker list back to the user, and stop. Do not invent work for a CLOSED plan or a clean APPROVED.

**DRAFT_EMITTED verdicts** (author-side only) do NOT have triage-worthy blockers — the author skill skipped its hardening stages (Plan-lint, Concern-lint where applicable, Ground-truth audit, Self-prosecution) because the user passed `--draft`. There are no findings, but there is also no APPROVED status. Surface this explicitly: "Verdict is `DRAFT_EMITTED` — the user opted out of the safety net by passing `--draft`. Re-invoke `/<author-skill> <feature>` without `--draft` to run ground-truth and self-prosecution, then triage the resulting blockers." Do NOT proceed to research — there is nothing to research.

Build a normalized array (one entry per blocker):

```
blockers: [
  {
    index: 1,
    blocker_class: "OPEN_QUESTION",
    path_or_section: "ir/ops.rs migration (lines 614-712) — multi-trigger CRUD evolution missing",
    summary: "<verbatim from source>",
    raised_in: "round 1" | "invocation 1",         // use the source's native vocabulary
    current_reclassification_justification: "<if present>",
    source_kind: "plan_state_file" | "pr_state_file" | "author_state_file" | "pr_review_comment" | "inline_text",
    source_path: "<absolute path or PR URL>",
    state_side: "review" | "author",               // derived from parent directory of source state file
    artifact_kind: "vision" | "spec" | "engineering_plan" | "chunk_plan" | "brief" | "pr_diff",
    artifact_root: "<plan file path | repo root + base..head sha>"
  },
  ...
]
```

Determine `artifact_kind` from the source-file shape:
- Slug ending in `__vision`, OR `artifact_path` ending in `vision.md` → `vision`.
- Slug ending in `__spec` (both the per-system `<project>__<spec-slug>__spec` and the single-root `<project>__spec` keying), OR `artifact_path` ending in `specs/<slug>/spec.md` or a root `spec.md` → `spec`.
- Author-state slug ending in `__brief` (e.g., `user-profile-sync__brief.json`) → `brief`.
- `plan_path` / `artifact_path` ending in `engineering-plan.md`, OR author-state slug ending in `__engineering-plan` → `engineering_plan`.
- `plan_path` / `artifact_path` ending in `implementation/<chunk-slug>.md` or `implementation/<NN>-<chunk-slug>.md` (or similar per-chunk file; strip any leading `NN-` creation-index prefix when extracting the slug), OR author-state slug of the form `<feature>__<chunk-slug>` / `<feature>__<track>__<chunk-slug>` (carrying none of the `__vision`, `__spec`, `__brief`, `__engineering-plan` suffixes) → `chunk_plan`.
- State-file slug containing `__pr-<N>` or no `plan_path` field → `pr_diff`.

Determine `state_side` from the source state file's parent directory:
- `~/.claude/cache/review-state/` → `review`.
- `~/.claude/cache/author-state/` → `author`.

`state_side` matters because the same blocker class can fire from either side (e.g., `OPEN_QUESTION` in `/plan-review-v2` vs `/plan-author`), but the resolution path is slightly different — author-side blockers fold into the next author invocation; reviewer-side blockers fold into commits + the next reviewer invocation. The `state_side` tag drives the resolution-path framing in the rendered decision list.

Echo a one-line confirmation to the user — count and source — so they know which verdict they're getting triaged. Do **not** list the blockers individually here. Listing them defeats the point: ten one-liners up front and then ten decisions down below is twice the reading. Just confirm the target.

```
Triaging N blockers from <plain source name — feature, PR, etc.>.
```

Keep the bracketed class tags and the original blocker text in your working notes — you'll need them for the per-blocker research branch — but they don't go on the screen.

State files persist across CLOSED/APPROVED rounds; an old file may be the wrong target. If the source you'd auto-pick is ambiguous (multiple recent files, or the user said "latest" but it's not obvious which feature they mean), ask before researching, not after.

---

## Research, cluster, triage (main thread)

Three steps, in order. **Do not write any user-facing output until step 3.** The temptation to write per-blocker prose as you research is strong; resist it. Premature output forecloses the clustering step, which is where most of the value is — it's how a 10-blocker list collapses into 4 decisions.

### 2a. Research each blocker (internal to Claude — user never sees this)

Inline execution; no subagents. Issue Read / grep calls in parallel within a single message when fetching independent files for one blocker. The goal is to gather *just enough* to know two things per blocker: **(1) what call resolves it**, and **(2) whether the call is shared with any other blocker.**

You do not need a thorough briefing on every blocker. You need the resolving question. If a blocker is a corollary of another — same call resolves both — researching it once at the level of the umbrella decision is enough.

For each blocker:

1. **Read the cited section.** Just enough of the artifact at the cited line range to know what the blocker is talking about. You don't need the full enclosing chunk if a few lines suffice — you're trying to identify the resolving question, not write a code review.

2. **Verify the blocker still holds.** Quick check: does the cited claim survive against the repo at HEAD? Internally tag CONFIRMED / STALE / FALSE. The user never sees the tags. They affect only one thing: a stale blocker becomes a retraction candidate (handled in clustering as "the situation has moved past this") rather than a live decision. Don't silently drop stale blockers — the v2 round-memory machinery retires them on the next invocation, but the user should still see them flagged so they know to re-run.

3. **Sample surrounding context** *only* if needed to know what call resolves the blocker. Sometimes the blocker is self-evident; sometimes you need the brief, the decisions log, prior conversation, or `CLAUDE.md` to understand the user's intent. Read narrowly — you're not synthesizing intent, you're identifying the resolving question.

4. **Branch your research strategy on the blocker class:**

   - **`OPEN_QUESTION`** — the reviewer filed a question rather than a fix. Identify the irreducible decision point. Enumerate the *full* set of viable resolutions (often 2–3, occasionally 1 if the answer is forced by repo state). Per option: what would change, expected effort, downstream effect, why someone might pick it.

   - **`STABLE_DISAGREEMENT`** — two personas filed contradictory fixes on the same span. The original persona reports are not persisted anywhere; reconstruct the disagreement from (a) the verdict's blocker line, which usually summarizes "Persona A: {fix A}; Persona B: {fix B}", and (b) the cited section's actual content. Identify what the personas actually disagree about — often a sub-question buried in the framing (e.g., "should this validate at parse-time or render-time?" framed as "the helper is wrong"). Lay out the tradeoff axis explicitly.

   - **`FIX_INTRODUCED_PREMISE_INVERSION`** — the v2 orchestrator's applied fix wrote prose (comment, docstring, plan body, brief, decisions log) that asserts something the repo does not support. The working tree is dirty. Find the lying prose, find the contradicting repo state, and propose either (a) the minimal prose rewrite to match reality, or (b) the minimal code change to make the prose true. Recommend a direction based on which is easier to land cleanly.

   - **`FIX_INTRODUCED_REGRESSION`** — a Stage 3 fix broke a gate. Identify which gate, the specific failure (run the gate locally if cheap; otherwise read recent CI logs via `gh`), and the minimal revert or follow-up fix. Bias toward the smallest diff that restores green.

   - **`BASELINE_RED`** — gates were red on the branch before review. Identify which gates fail and why. Run `git stash && <gate cmd>` against the base branch to confirm pre-existing if doubt remains. If failure is genuinely on `main`, that's a separate fix the user owes upstream — name it explicitly.

   - **`BRIEF_AMENDMENT_NEEDED`** (engineering-plan only) — the plan body decides something the brief should decide. Read the brief. Either (a) propose the brief amendment that closes the gap, or (b) identify which chunk should be dropped because no brief Goal supports it. Do **not** propose putting brief-level decisions in the plan body — that is the failure mode being prosecuted.

   - **`REPO_PREMISE_GAP`** (engineering-plan + chunk-plan) — the Repo Reality Sweep read the shipped code and the plan's premise about it did not survive. **Open the cited code yourself before triaging** — this class is the one whose blocker text is worth least second-hand, because the finding IS the code. Identify which axis fired: incumbent divergence (the plan drops something the shipped code does), caller closure (an existing caller is unaccounted for), or dependency guarantee (a primitive guarantees less than the plan's use assumes, at the plan's scale). The first two are usually a stated fix — the user's call is confirm-or-override, and the option list is short. The third is a genuine director decision with three shapes: strengthen the use, narrow the population, or disclose the shortfall. For that one, **get the blast radius as a number before presenting it** — a read-only query or grep usually settles it, and "3,354 of 7,128" versus "some" changes which option the user picks. Whatever the axis, before proposing a remedy that adds a check, filter, or fallback, grep for whether the repo already implements it; proposing a redefinition of something that ships adjacent is this class's characteristic mistake.
   - **`IMPLEMENTABILITY_GAP`** (engineering-plan + spec layers) — *Engineering plan:* a cross-chunk-wiring decision is undecided OR an identifier needed by ≥2 chunks is unbound. Identify the decision / identifier, propose a binding (the actual signature, name, ownership), and name which chunk should own it. *Spec:* the imagined-brief-author dry run could not answer a question from one brief's scope stub plus its roster entry alone, and the finding is **filed per brief slug** — it blocks `/brief-author` for that slug and leaves every other brief authorable. Read the stub and the spec section it draws on, then propose the sentence the spec is missing. The call is what that sentence says; "author the brief anyway" is not an option, because the brief author hits the same wall.

   - **`SPEC_BOUNDARY_UNBOUND`** (vision layer) — the same shape one layer up: two spec map entries claim one surface, or the imagined-spec-author dry run left a question the map could not answer. It gates `CLOSED` and not `APPROVED`, so it commonly arrives on an otherwise-clean verdict. Read both entries and, where a spec is already written, the file itself. The call is where the boundary sits, and it is a **design-ownership** question — present it as which system owns the rule, never as a formatting fix. Whichever way it lands, the answer is a binding the director makes once.

   - **`SEAM_PREDICATE_MISSING`** (vision + spec layers) — a boundary has a name but no test that decides which side the *next* rule falls on. Read the seam and the units already assigned by it. Three shapes, and naming which one fired is most of the research: the split line lists what is already assigned instead of stating a test; a neighbouring boundary accepts the same units, so neither decides; the boundary needs two tests to state, which means it is two boundaries. The first is usually a single-call rewrite. The third is a real decision — splitting the boundary splits what sits under it.

   - **`DECOMPOSITION_COVERAGE_GAP`** (spec layer) / **`VISION_COVERAGE_GAP`** (vision layer) — a unit of the upstream document is claimed by nothing and excluded by nothing, or a claimed invariant names nobody to prove it. Read the unit. Three resolutions, and which applies is usually forced: it belongs to a downstream artifact already in the set (single call, assign it); it belongs to a boundary's other side (single call, exclude it by that named boundary); or nobody has decided yet, which is the one real decision and lands in the state sidecar with its destination named. For a missing proof owner, propose the artifact whose checks would catch a violation, and reach for "the director checks this by hand" only when no authored artifact could.

   - **`MAP_CONFORMANCE_GAP`** (vision + spec layers) — a written spec defines a surface its map entry does not claim, or omits one the entry does. **Open the spec before triaging** — this class is falsifiable against a real file, and the blocker text is worth least second-hand. Then the call is which document is wrong: the entry describes an intent the spec drifted from (fix the spec), or the spec is right and the entry is stale (fix the entry). Name which, with the surface in plain language.

   - **`SPEC_NONGOAL_TRESPASS`** (spec layer) — a brief's scope stub does something the spec excludes, or something the project's cut list cut. Read the excluded item and the stub. Either the exclusion still holds and the scope drops, or the exclusion is out of date and the spec amends — the second is a director call about what the product is, and it is never resolved by quietly leaving both in place.

   - **`SPEC_AMENDMENT_NEEDED`** / **`VISION_AMENDMENT_NEEDED`** — the layer-above twins of `BRIEF_AMENDMENT_NEEDED`: a downstream unit needs a rule its upstream does not carry, or contradicts one it does. Read the upstream section. Propose either the amendment that closes the gap or the downstream scope that should be dropped for want of it. Do **not** propose leaving the rule in the downstream document — a document that contradicts its upstream is amending it, and the amendment lands in the contradicted section explicitly.

   - **`DECOMPOSITION_SURFACE_EXCESS`** (spec layer, numeric; vision layer, structural) — the decomposition is oversized. A **director decision** on the same terms as its sister size classes: propose the split, or size acceptance. Never apply a split yourself. Get the numbers before presenting it — how many downstream units, how deep the graph — because "eleven" and "large" pick different options.

   - **`HOIST_INCOMPLETE`** — something the roster was holding was supposed to move into a newly written artifact, and its substance is not there. Read both. Usually a single call: carry the missing substance across. It becomes a decision only when the substance no longer has an obvious home, which means the boundary moved under it.

   - **`DECOMPOSITION_STATUS_LEAK`** — the decomposition section picked up wording that will be wrong the day something ships. Almost always a single-call item: the content moves to the state sidecar (`features/README.md` at the spec layer, `specs/README.md` at the vision layer) and the section is rewritten as though the status had never been in it. Route it to the auto-fix set unless moving it would lose something nothing else records.

   - **`UNCORROBORATED_RESET`** (engineering-plan only) — single-persona RESET claim, escalated to CRITICAL HARD by the corroboration rule. The persona believes the plan's premise is broken at the repo-state or brief-environment layer. Read the claim verbatim. Verify against repo / project memory / `CLAUDE.md`. If verification corroborates, the user should re-scope; if it does not, recommend dismissal with a one-sentence rationale.

   - **`STRUCTURAL_LINT_FAILED`** (plan-only, fires from review-side AND author-side) — `/plan-lint` short-circuited the review or the author. The verdict should already name which lint rule fired; explain the rule plainly, show what about the plan trips it, and propose the rewrite.

   - **`CONCERN_GATE_FAILED`** (plan-author only) — the chunk plan's H1 / Goal sentence / engineering-plan chunk-index description triggered the multi-concern refusal pattern. Identify the exact phrase that triggered it (the verdict names it). Propose the engineering-plan amendment that decomposes the chunk into one-concern siblings — name the proposed siblings explicitly, and which existing concern lives in each. The user's call is "approve the decomposition" or "reject and override"; if rejected, flag that the override path requires a deliberate engineering-plan amendment removing the offending phrase, NOT bypassing the gate.

   - **`BUDGET_EXCEEDED`** (plan-author only) — chunk plan exceeded the 500-line / 40k-token hard cap. Almost always overscoping. Read the plan structurally (sections, paragraph counts) and propose a decomposition: which sections collapse into sibling chunks, and what one-concern Goal each sibling owns. The user's call is between accepting decomposition vs invoking `--bypass-byte-budget` — surface the cost of bypass (reviewer treats with extra scrutiny; carry-forward marks the bypass loudly).

   - **`POLISH_PLATEAU`** — explicitly non-blocking by definition. Acknowledge it; propose the polish if it is a 5-minute change, otherwise flag as "ship-acceptable; revisit if convenient."

   - **`REPO_STATE_DRIFT`** — `git rev-parse HEAD` changed mid-review. Recommend re-running the source skill from scratch; do not propose code-level resolutions.

   - **Unknown class** (any class not in the list above) — consult `~/.claude/skills/_review-common/blocker-classes.md`. If the class is not registered there either, treat as `OPEN_QUESTION`-equivalent (filed a question; user adjudicates) and call this out in the report.

5. **External docs only if the blocker actually hinges on a third-party library's behavior.** Use the `context7` MCP server (`resolve-library-id` → `query-docs`). Do not pull docs speculatively.

After researching all N blockers, you should have, in your working notes, for each blocker: the resolving question (one sentence), CONFIRMED/STALE/FALSE on the premise, and a sense of which other blockers (if any) share the resolving question.

### 2b. Cluster blockers under shared decisions (internal)

This is where 10 blockers becomes 4 decisions. Group blockers whose **resolving question is the same**, or whose answer **mechanically determines** the answer to another blocker's question. Two blockers belong in the same cluster when answering one of them collapses the other — not when they merely happen to share a file or topic.

Tests for "same cluster":
- Same yes/no or A/B question, asked from different angles. (e.g., "should the rename land?" — three blockers each prosecute a different consequence of the rename, but they all resolve the same call.)
- Cause and effect. (e.g., the plan predates a recent change in the system; multiple blockers are all symptoms of the same staleness; one decision — "rebase the plan or not" — resolves them all.)
- Mechanical entailment. (e.g., decision X commits the user to interface Y, which forecloses the option blocker M was prosecuting.)

Tests for "different cluster" — if any of these is true, blockers are NOT siblings:
- Different yes/no questions, even if scoped to the same area.
- One blocker is decidable in isolation; the other's outcome doesn't move with it.
- They merely share a file or feature name.

A cluster of one is fine and common. Aim for clusters that *reduce* the user's call count, not for visible grouping. Forced grouping is worse than ungrouped — if the user makes one call and the "linked" items don't actually fall out, they've been deceived about the cost of the decision.

For each cluster, write down (in working notes, not output yet):
- **The resolving question**, one sentence, framed as a choice the user makes.
- **The blockers it resolves**, by their working-note IDs.
- **Claude's pick** + one-or-two-sentence reasoning.
- **Dependencies** — does this cluster need to be decided *before* another cluster (because Cluster A's answer reframes Cluster B's question)? Most clusters are independent; flag only real dependencies.

### 2c. Order decisions and write the report (output begins here)

Order the clusters so the user's first call has the most leverage. Dependencies first; then by how many blockers each cluster collapses; then by whatever's left.

Then, and only then, write the report using the format defined under "Render the decision list" below.

### Director-language rules (apply to every line that goes on screen)

The user did not write a single line of the code or the plan. Claude wrote everything. They are the **director**: they tell Claude what to build, they decide between options, they approve or reject. They do not read source.

- **Plain language by default.** "The naming convention in the plan" — not internal identifier names, file paths, or line numbers.
- **User-facing names are fine.** Library/framework names (React, Postgres), features the user named themselves, third-party integrations they know about.
- **Internal identifiers only when the user already uses them.** Check the brief, decisions log, conversation memory. If only Claude's plan text uses a name, paraphrase it.
- **No file paths, line numbers, `path:line` citations, `git` commands, or review-machinery vocabulary** ("Stage 3", "round-memory", "premise inversion", "Tier-1 weight"). Self-test: would the user, who has not seen any code, recognize this? If no, paraphrase. The closing verdict banner is exempt — it is the pipeline's shared status line, rendered by its script, not report prose.
- **No "What the review flagged" prose.** The decision question carries the framing.
- **No effort estimates.** The user does not care about S/M/L.
- **No "Why it matters" paragraph.** If the consequence isn't obvious from the question, fold one short clause into Claude's pick. Don't dedicate a section to it.

### Per-decision output format

Each decision is a self-contained block. Aim for ~5 short lines including blank lines. Use the headings verbatim. **There is no per-blocker block** — blockers are mentioned only as "also resolves" footnotes inside their cluster's decision.

```
### Decision [N]: [one-line question, phrased as a choice]

**Options:** [Option A — one short clause]; [Option B — one short clause]. Every rendered decision carries a genuine choice — if there is no real second option, it is NOT a decision block; it goes in the auto-fix set (see "Single-call items — fix, don't raise" below).

**My pick:** [one option, one or two sentences of reasoning. Lead with the user's stake — what the call commits them to — not the implementation reason. Name the cost in one clause if it's real.]

**Also resolves:** [one short phrase per linked blocker, comma-separated. Omit this line if the cluster is a single blocker.]
```

For retraction-candidate blockers (premise FALSE/STALE such that the blocker no longer holds), don't make them their own decision. Group them at the end under a single "Items the situation has moved past" decision; the user's "call" there is just to re-run the source review after the live decisions are made.

**Single-call items — fix, don't raise.** A blocker whose resolution has no real director choice — one viable fix, where the user's only "call" would be to rubber-stamp Claude's obvious pick — does NOT get a decision block and is NOT raised as a decision. Collect these into an **auto-fix set**. The director's attention is reserved for genuine choices; a determined fix is Claude's to make. Auto-fix items are surfaced only as a compact "Fixing directly (no decision needed)" list beneath the decisions, one short phrase each, and applied as part of the apply step — never numbered, never counted in the decision total. Retraction candidates and single-call items are the two kinds of item that ride the apply step without consuming a decision. Do not manufacture a fake second option to promote a single-call item into a decision — that is the padding failure mode inverted.

---

## Render the decision list

The full output is the header (one or two lines) plus the per-decision blocks (already templated in 2c) in dependency order. **No "Big picture" prose. No "Decisions unlock others" cross-reference list. No per-blocker walkthrough.** The clustering and ordering already encode the structure; restating the structure as banner sections is exactly the bloat the user asked to cut.

The header identifies the source by what the user calls it (feature name, PR title), not by state-file path. The "items needing your call" line is a count of *decisions*, not blockers — that's the number that matters now.

```
# Decisions you need to make: <plain-language source identifier>

**N decisions** (covering M blockers from the last review).
<if any retraction candidates: "Plus K items the situation has moved past — re-run /<source-skill> after the live decisions to close them automatically.">

---

<per-decision blocks, in dependency order, separated by blank lines>

<if any single-call items:
**Fixing directly (no decision needed):** <one short phrase per auto-fix item, comma-separated>.
>
```

That's it. No closing `## What I'd do next` section — the decisions are *already* ordered by what to do first. Numbering them does the job.

If the entire triage is one decision, drop the count line and just emit the single block under the header.

---

## After rendering — apply or hand off

Do **not** offer to save the report. It's already in scrollback, and the operator asked for the *calls to make*, not a file to keep. Instead, after the decision list is rendered, ask the operator once which way to take it. Use `AskUserQuestion` with two options:

- **Apply my picks** — Claude makes the edits, working each decision's *My pick* in dependency order (top decision first). These are explain-blockers picks: fast triage judgment, not the ≥95%-confidence research `/solve-blockers` does — so this is the right call when the decisions are low-stakes or the picks are obvious.
- **Run `/solve-blockers`** — hand off for deeper research: each blocker gets driven to ≥95% confidence with an evidence trail before anything changes. The right call when the decisions are load-bearing.

There is no default — wait for the operator's answer.

**When the triage produced no genuine decisions — only single-call (auto-fix) items and/or retraction candidates — skip the apply-or-handoff question entirely.** There is nothing to hand off and nothing to choose: apply the auto-fix items directly (still never touching state files), then name the source skill to re-invoke. Raising an apply-or-handoff prompt over a set of no-brainers is the same director-attention tax the single-call rule exists to remove.

- If they pick **apply my picks**: make the edits for each live decision following its *My pick*, top-down, AND apply every auto-fix (single-call) item in the same pass. Only the plan / code / brief / PR change — **state files stay read-only** (`~/.claude/cache/review-state/` and `~/.claude/cache/author-state/` are owned by the source-skill machinery). Skip the retraction cluster — its "resolution" is "re-run the source skill", not an edit. When the edits land, name the source skill to re-invoke so its round-memory / carry-forward machinery validates the resolutions — the reviewer that raised them, or the matching author skill.
- If they pick **`/solve-blockers`**: invoke it via the Skill tool on the same target. It reads this rendered report from scrollback and skips its own clustering.

**Final line — verdict banner.** Every terminal path of this skill ends with the shared verdict-banner script's fenced stdout, emitted verbatim as the very last thing in the response (`~/.claude/skills/_review-common/blocker-classes.md` § Verdict banner, "The triage pair banners too"). `--skill` names the SOURCE skill to re-invoke; `<ROUND>` is the source verdict's round (`?` when the source carried none):

- Picks applied (including the auto-fix-only path) → `RESOLVED`, count = blockers the edits cover.
- Report rendered but nothing applied (operator declined, or picked neither option) → `DECISIONS PENDING`, count = open decisions.
- Refusal paths (e.g. a `DRAFT_EMITTED` source) → `DECISIONS PENDING`, count 1, `--skill` naming the author skill to re-run.
- Nothing to triage (clean `APPROVED` / `CLOSED`) → echo the source verdict's status, round, and blocker count.
- Hand-off to `/solve-blockers` → no banner here; that skill's terminal path banners.

---

## Non-goals (explicit)

- **Do not edit anything during triage.** The triage pass — research, cluster, recommend — is read-only. Editing happens *only* after the decision list is rendered and *only* when the operator picks "apply my picks" (see "After rendering — apply or hand off"). Never apply picks the operator declined, and never touch state files even then. Be especially deliberate applying author-side picks: a draft was withheld from disk because the author skill refused to ship a hallucination, so an approved apply writes plan/brief prose to disk — confirm the pick is right before the operator green-lights it.
- **Do not invoke the v2 review skills OR the author skills.** This skill consumes their output. The user re-invokes the source skill themselves once they have applied resolutions.
- **Do not modify state files.** `~/.claude/cache/review-state/*.json` is owned by the v2 round-memory machinery. `~/.claude/cache/author-state/*.json` is owned by the author skills' write-time machinery. Both directories are read-only from this skill's perspective; writing would corrupt convergence guarantees on either side.
- **Do not relitigate the v2 classification.** If the review said `OPEN_QUESTION`, treat it as an open question — research clarifies it, it does not overturn the class. Single exception: if verification finds the blocker's *premise* is false, flag as a retraction candidate (do not silently drop, and do not propose forcing a different class).
- **Do not fabricate options.** When only one viable resolution exists, name one. Padding to three with obvious strawmen buries the actual recommendation.
- **Do not pull external docs speculatively.** Use `context7` only when the blocker hinges on library behavior the repo does not document.
- **Do not spawn subagents for the per-blocker research.** Inline execution in the main thread is faster end-to-end at this scale and keeps cross-blocker context free. The only legitimate reason to spawn an agent is if a single blocker's research is unusually large (e.g., requires reading 30+ files spread across a monorepo) — then a one-off `Explore` or `general-purpose` agent for that *one* blocker is fine.

## Failure modes to avoid

- **Per-blocker output.** The single biggest failure mode for this skill. If the rendered report has one block per blocker, you've defeated the triage model — the user is back to reading ten things to figure out the four calls. Always cluster first; never emit a per-blocker walkthrough.
- **Premature output.** Writing user-facing prose during step 2a (research) instead of waiting for 2b (cluster) and 2c (order). If you draft a per-blocker block as you go, you'll resist regrouping it later. Hold output until clustering is done.
- **Forced clustering.** Grouping blockers that *don't actually share a resolving question* just to make the count smaller. If the user makes the call and the "linked" items don't fall out, the report lied about the cost of the decision. When clustering tests fail, leave it as a singleton.
- **Engineer-language leakage.** Every file path, line number, internal identifier, `git` invocation, or piece of review-machinery vocabulary that survives into the rendered output forces the user to translate Claude-talk. Self-test: would someone who has never opened a file in this repo follow this line? If no, paraphrase.
- **Bloat by section.** Sections you may *not* add: "Why it matters" (fold into Claude's pick), effort estimates (the user does not care), "What the review flagged" prose (the question carries it), "Big picture" / "Decisions unlock others" banners (already encoded in the order). Each rejected section was tried in earlier drafts; each one ate the user's attention budget.
- **Padding with strawmen.** When only one option is viable, write "Single call: ..." and stop. Inventing weak Option B/C to match a pattern is bloat dressed as fairness.
- **Skipping internal verification.** Verification (CONFIRMED / STALE / FALSE) is *internal* — the user never sees the tags — but skipping it means recommending a call on a problem that no longer exists. Verification stays mandatory; it just affects whether the blocker is a live decision or a retraction-cluster footnote.
- **Unverified provenance.** Targeting an old state file because it was the most recent on disk, when the user actually meant a different feature. The locate-and-parse confirmation step exists to catch this when the source is ambiguous.

## Interaction with the round-memory / author-state machinery (do not break it)

This skill is a sibling, not a participant, of either the v2 round-memory machinery or the author-side carry-forward machinery. It reads state files from both `~/.claude/cache/review-state/` and `~/.claude/cache/author-state/`; it never writes either. The user's eventual resolution of blockers feeds back into the next invocation of the source skill through (a) plan/code/brief edits, (b) commit messages, (c) `decisions.md` entries, and (d) the source skill's `recently_resolved_blockers` capture priority. None of those flow through this skill.

Applying the picks (when the operator chooses that at the end) edits only the plan / code / brief / PR — never the state files. After the edits land, the resolution feeds back into the next invocation of the source skill, which validates it through its round-memory / carry-forward machinery:
- Reviewer-side resolutions → re-invoke the reviewer that raised them: `/vision-review`, `/spec-review`, `/brief-review-v2`, `/engineering-plan-review-v2`, `/plan-review-v2`, or `/review-pr-v2`.
- Author-side resolutions → re-invoke `/vision-author`, `/spec-author`, `/brief-author`, `/engineering-plan-author`, or `/plan-author` (warm mode is automatic when the artifact already exists).

When the same artifact has BOTH a review-side state file and an author-side state file with unresolved blockers, the user should generally resolve the author-side blockers first (the author skill refuses to emit; the disk-state plan is stale until they do) and then re-run the reviewer afterwards. Surface this dependency in the report header when both sides have entries for the same artifact slug.
