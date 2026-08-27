# Orchestrator — the shared Stage 3 spine

Loaded by `/brief-review-v2`, `/plan-review-v2`, `/engineering-plan-review-v2`, `/review-pr-v2`, `/spec-review`. Stage 3 runs in the **main thread**: the orchestrator owns every edit, so it owns every consequence of an edit. Personas produce fix lists; they never write.

The hosting skill inserts its layer-specific steps (convention extraction, RESET corroboration, gates re-run, commit, PR post) and names its artifact. Everything below is identical across layers — implement it here, not four times.

## Step order

This order is load-bearing. Each step consumes the previous step's output, and two of the orderings were chosen to avoid paying for work that is about to be thrown away.

1. **Apply Stage 1 mechanical fixes** — already applied at the end of Stage 1; confirm the artifact matches that post-fix state.
2. **Filter against round-memory tags** (round 2+ only).
3. **Filter against critical-pair policies.**
4. **Class Sweep** — per `class-sweep.md`, in the four reviewers that host it (`/brief-review-v2`, `/plan-review-v2`, `/engineering-plan-review-v2`, `/review-pr-v2`). It runs *after* retraction so a category whose only seed just died is not swept, and *before* consolidation so swept siblings are fixed in the same editing pass as their seeds — and before disagreement detection, so a contradictory fix on a swept sibling becomes `STABLE_DISAGREEMENT` instead of being auto-applied. `/spec-review` has no sweep stage; it skips this step.
5. **Detect cross-persona disagreement** — contradictory fixes on one span become `STABLE_DISAGREEMENT`; never auto-apply either side.
6. **Consolidate and apply** the surviving fixes.
7. **Post-fix premise verification.**
8. **Same-round focused re-prosecution** — bounded to one pass.
9. **Classify remaining findings**, consulting carry-forward.
10. **Compliance self-check**, then render the verdict and persist state.

## Filter against round-memory tags

**Only in hosts that run a diff-based gate** — today `/engineering-plan-review-v2` (section-diff + plan-growth) and `/review-pr-v2` (file-hash diff). A host with no such gate emits no tags, so there is nothing to filter and this step is skipped; do not invent tags to satisfy it.

Round 2+ only. The Round Memory pass tagged the artifact's unchanged regions and, where the host runs a growth gate, the regions added in response to prior blockers.

- A finding against an **unchanged** region survives only if the persona named both (a) a specific defect prior personas missed and (b) why the prior round's lens did not catch it. Missing either → auto-retract, and record it as a retraction in the verdict.
- A finding tagged `regression_risk: yes` (it cites text added since the last round) drops one severity tier — CRITICAL → HIGH → MEDIUM → LOW — unless the persona named a specific failure mode the added text *creates*. "The added text is imprecise" is not a failure mode. Apply the downgrade mechanically; the persona's job was to tag honestly, not to adjudicate.

## Filter against critical-pair policies

For every surviving finding:

- Contradicts an active critical-pair policy → **retract**, and note it in the verdict's Retractions block.
- Duplicates a Stage 1 hard finding already mechanically fixed → **retract**.
- Otherwise → keep.

Class A findings — the brief-conformance and scope-parity classes (`BRIEF_NONGOAL_TRESPASS`, `BRIEF_GOAL_UNDELIVERED`, `SURFACE_PARITY_GAP`, `GOAL_VERIFICATION_GAP`) — are exempt from **decisions-log carry-forward retraction**, per `blocker-classes.md` § Brief-conformance. That exemption does not extend to critical-pair retraction: a Class A finding that contradicts an active critical-pair policy is retracted like any other. Class A findings escalate to the user rather than being auto-fixed. See `principles.md` § Cross-artifact authority order.

## Post-fix premise verification

Main thread, LLM judgment, **never a sub-agent spawn**. The orchestrator made the edits; it knows what it wrote, and delegating verification loses that.

Fixes rewrite prose, and a mechanical rewrite can flip a true claim into a false one — "the handler returns `Result`", "this chunk only touches files matching `<glob>`", "matches the existing pattern in `<file>`". The next round would then prosecute the new, false text, and the user would watch the reviewer argue with its own writing.

1. **Identify added or rewritten prose** by comparing against the pre-fix version held in memory.
2. **Identify verifiable claims** — behavior ("X returns Y when Z"), scope, constraint (a type signature), cross-reference ("matches the pattern in `<file>`"). Skip stylistic edits, section headers, aspirational language ("aim to", "ideally"), and open-ended commentary that asserts no current fact ("future work may consider…").
3. **Verify each** with the cheapest falsifying check available: `Read` the cited file, grep for the identifier, run the one command that settles it.
4. **File each falsified claim** as `FIX_INTRODUCED_PREMISE_INVERSION`. Leave the working tree dirty for the user to inspect — do not "fix the fix" silently.

Record `verification_attempts / verified / falsified / new_blockers_filed` for the verdict.

## Same-round focused re-prosecution

Runs after post-fix premise verification, before classification. **Exactly one pass. Never an inner loop.**

Fix prose is prose, and it has not been prosecuted. Without this pass the round exits and the *next* round finds the defects — a convention added with no test enforcing it, a new accessor with no contract test, a corrected claim that introduced a second wrong one. Catching that inside the round is far cheaper than re-prosecuting the whole artifact next round.

1. **Capture the diff hunks** written during fix application and claim correction, as (file, before, after) tuples. Cross-file edits to `decisions.md` or the engineering plan are included.
2. **Spawn one focused agent per persona** that reviewed in Stage 2, using `agent-prompt.md` with the **same substitutions Stage 2 used**, overriding only these:
   - **The slot carrying the diff hunks.** Each host names its own — `{target_locator}` (artifact path plus the hunks as before/after blocks) or `{audit_report_bullets}` (a "Diff hunks under review" block listing each path, line range, and verbatim added text). Either is fine; the host's choice is authoritative.
   - `{skill_specific_extensions}` — *Review ONLY the diff hunks below. The whole artifact was prosecuted in Stage 2; this pass exists to catch defects introduced by the orchestrator's own edits. File findings on the rewritten prose's internal consistency, test-coverage gaps for newly-added conventions or contracts, cross-reference correctness, unverified claims, and discipline gaps where a convention was added but nothing enforces it. HIGH and MEDIUM only — LOW-severity polish on fresh prose is next round's territory.*
   - `{skill_specific_preamble}`, where the host marks the pass (`re_pass: focused_diff_hunks; round_number: <N>; original_pass_completed: yes`).

   Every other substitution carries over verbatim. Omitting them produces a malformed prompt that under-constrains the persona.
3. **Filter the re-pass findings** through critical-pair retraction, same as the originals.
4. **Detect disagreement** on diff-hunk spans; contradictions become `STABLE_DISAGREEMENT` and are not auto-applied.
5. **Apply survivors** as additional edits, severity-ordered, under the same forbidden-fix rules.
6. **Re-run post-fix premise verification** scoped to the re-pass edits only.
7. **Stop.** Anything still standing becomes a blocker in the verdict. The user re-invokes; that *is* the next round.

**Skip** the re-pass (record `re_pass_ran=false`) only when all three hold: zero fixes applied, zero falsified claims, and zero on the host's third signal. That third signal is layer-specific and the host names it — cross-file edits at the plan layers, cross-file *escalations* at the spec layer (which escalates rather than editing), HEAD unchanged at the PR layer (where fixes become commits). No new prose surface means nothing to re-prosecute.

Record `re_pass_ran / re_pass_diff_hunks_reviewed / re_pass_additional_fixes_applied / re_pass_findings_persisted_to_blockers`.

## Carry-forward consultation

Durable record first, ephemeral cache second:

1. **`features/<feature>/decisions.md`** — read only Active bound entries. A finding the user already arbitrated against is dropped, and the drop is recorded in `decisions_md_consultation.findings_dropped`.
2. **`recently_resolved_blockers`** in the state file — a finding re-raised on a recently-resolved span must surface the prior `user_decision` verbatim in the verdict, so the user sees what they already decided rather than being asked twice.

Class A findings are exempt from both. A brief Goal is not un-committed by a decisions-log row.

## Compliance self-check

Before rendering, confirm each of these and state the result in the verdict. A failed check is reported, never silently skipped:

- Every mandatory stage ran, or was skipped with its skip condition recorded.
- Every applied fix is attributable to a surviving finding.
- Every retraction names the policy that retracted it.
- Post-fix premise verification ran on every rewritten span.
- The re-pass ran, or its three skip conditions all held.
- The state file was written before the verdict was rendered.
- The verdict banner script ran (with `--skill`) and its fenced stdout ends the response, with nothing after it — on every terminal path, refusals and aborts included.

## Forbidden fixes

Never auto-apply, in any layer. Each escalates as `OPEN_QUESTION` instead:

- Weakening the artifact to make a finding go away — dropping an invariant, softening an acceptance criterion, deleting a Non-goal that blocks something.
- Editing `CLAUDE.md`, project memory, or a design doc.
- Deferring a defect downstream ("the next layer will catch it"). It will not; it will inherit it.
- Resolving a Class A finding by narrowing the Goal it fails to deliver.
