# Round Memory — cross-invocation convergence state

Loaded by `/brief-review-v2`, `/plan-review-v2`, `/engineering-plan-review-v2`, `/review-pr-v2`, `/spec-review`. This file defines the mechanism: where state lives, what it holds, how it loads, and how it persists. The hosting skill names its slug shape, its extra schema fields, and any extra sub-passes it runs on top.

Nothing here uses LLM judgment. It is bookkeeping that makes the *next* invocation cheaper and stops the reviewer from re-prosecuting settled ground.

## What this breaks

Three thrash patterns, all of which look like "the reviewer is churning" from the outside:

1. **Re-prosecution of resolved findings** — the user addresses prior-round blockers, re-invokes, and personas file the same finding under new framing.
2. **Prosecution of remediation artifacts** — the artifact grows each round as the user binds flagged decisions, and the next round files findings against the newly-added text.
3. **Orchestrator-introduced premise inversions** — the prior round's fixes rewrote prose in a way that flipped a claim, and the next round prosecutes the new, false text.

The durable arbitration record is `features/<feature>/decisions.md`, committed to the repo. The state file supplements it with recently-resolved-blocker context that decays after `carry_forward_until_round`. Neither is a substitute for the other: `decisions.md` records what the user decided and why; the state file records what the machinery did.

## State file location

`~/.claude/cache/review-state/<slug>.json` — never in the project, survives worktrees, never committed. Create the parent with `mkdir -p ~/.claude/cache/review-state` if missing.

For artifacts under `features/`, slug derivation follows `_plan-common/layout.md` § State-slug derivation — the path relative to `features/`, minus the `plans/` and `implementation/` segments, `/` replaced by `__`. The PR and spec layers are keyed differently, since neither artifact lives under `features/`:

| Layer | Slug |
|---|---|
| Brief | `<feature>__brief` |
| Engineering plan | `<feature>__engineering-plan`, or `<feature>__<track>__engineering-plan` when tracked |
| Chunk plan | `<feature>__<chunk-slug>`, or `<feature>__<track>__<chunk-slug>` when tracked |
| `.scratch/<name>.md` | `scratch__<name>` |
| `fixes/<name>.md` | `fixes__<name>` |
| PR | `<owner>__<name>__pr-<N>` — repo-keyed, not feature-keyed |
| Spec | `<project>__spec`, where `<project>` is the repo-root basename |
| Anything else | basename without `.md`, `/` → `__` |

**Strip any leading `NN-` creation-index prefix** from a chunk-plan filename before forming the slug. The prefix orders files on disk; it is not identity, and the slug must match `/plan-author`'s sidecar key or author and reviewer state diverge silently.

## State file schema

```json
{
  "slug": "<slug>",
  "artifact_path": "<path passed at invocation, or PR reference>",
  "last_review_at": "<ISO 8601 UTC>",
  "last_verdict": "CLOSED | APPROVED | NEEDS_USER_INPUT",
  "last_artifact_sha256": "<hex>",
  "round_number": 1,
  "prior_blockers": [
    {
      "blocker_class": "<see blocker-classes.md>",
      "path_or_section": "<section heading, chunk slug, or file:line>",
      "summary": "<one-line>",
      "raised_in_round": 1,
      "current_reclassification_justification": "<one sentence; present only when re-raised after a prior resolution>"
    }
  ],
  "recently_resolved_blockers": [
    {
      "blocker_class_when_resolved": "<class | RESOLVED>",
      "path_or_section": "<same shape as above>",
      "summary": "<one-line>",
      "resolved_in_round": 1,
      "user_decision": "<one-sentence rationale; see capture priority>",
      "carry_forward_until_round": 3
    }
  ],
  "open_blocker_history": [
    { "round": 1, "open_blocker_count": 0, "open_question_count": 0 }
  ],
  "per_round_metrics": {
    "round_1": {
      "fixes_applied": 0,
      "cross_file_edits": [{ "file": "<repo-relative path>", "summary": "<one-line>" }],
      "class_sweep": { },
      "re_pass_ran": false,
      "re_pass_diff_hunks_reviewed": 0,
      "re_pass_additional_fixes_applied": 0,
      "re_pass_findings_persisted_to_blockers": 0,
      "decisions_md_consultation": { "entries_matched": 0, "findings_dropped": 0 }
    }
  }
}
```

Treat absent `prior_blockers`, `recently_resolved_blockers`, `open_blocker_history`, and `per_round_metrics` as `[]` / `{}` when reading.

The `class_sweep` block's shape is owned by `class-sweep.md` § State recording, not by this file — write exactly what that file specifies, including `sweep_agents_spawned`, which the compliance self-check asserts on. `per_round_metrics` and `open_blocker_history` are **append-only** across invocations — older rounds stay visible so convergence trends are readable: `re_pass_findings_persisted_to_blockers` should trend to zero as the artifact stabilizes, and `decisions_md_consultation.findings_dropped` should rise once the user starts recording negative decisions.

`carry_forward_until_round` **defaults to `resolved_in_round + 2`** when an entry is created. That window is what downgrades a re-raised finding on a resolved span; it is a threshold that gates verdicts, not a formatting detail.

**Legacy field names — read both, write canonical.** These names predate the shared schema and are live in existing state files. On read, accept either name; on write, emit only the canonical one and drop the legacy key.

| Canonical | Legacy names still on disk |
|---|---|
| `slug` | `brief_slug`, `plan_slug`, `spec_slug`, `feature_slug`, `repo_slug` |
| `artifact_path` | `brief_path`, `plan_path`, `spec_path` |
| `last_artifact_sha256` | `last_brief_sha256`, `last_plan_sha256`, `last_spec_sha256` |
| `per_round_metrics.*.fixes_applied` | `stage_3_fixes_applied`, `stage_3d_fixes_applied` |

Skipping this is not cosmetic: § Load prior state case 2 compares the stored sha, so a loader that reads only the canonical name sees no match on an existing file and treats every re-invocation as "the user edited between rounds" — silently discarding the convergence this file exists to provide. The PR layer additionally keys on `last_head_sha`, not a content sha; see its own section.

**Host-specific fields.** A host may add fields its sub-passes need — `section_hashes` and `last_artifact_word_count` for the engineering-plan growth and section-diff passes, `gates_baseline` for the PR reviewer, `author_sidecar_consulted` for layers with an author sidecar. Hosts document their own additions; unknown fields are preserved on read/write, never dropped.

**Legacy slugs.** A host that historically wrote a different slug reads the canonical slug first, falls back to the legacy name, and on persist writes canonical and deletes the legacy file. Report the migration on the verdict's `State source` line.

## Load prior state

`Read` the state file:

1. **Missing** → cold start. `round_number = 1`, empty blocker arrays, skip every diff-based sub-pass, proceed.
2. **Present, artifact sha matches `last_artifact_sha256`** → re-invoked without edits. `round_number = stored + 1`. Carry blockers forward, dropping entries whose `carry_forward_until_round < round_number`.
3. **Present, artifact sha differs** → the user edited between rounds. `round_number = stored + 1`, same carry-forward. **The diff is the user's response to prior blockers** — expect fewer findings against modified spans, and treat findings against them with the scrutiny the host's diff-based gates prescribe.

## Capture priority for `user_decision`

When a prior blocker no longer appears in the current verdict, it becomes a `recently_resolved_blockers` entry. Populate `user_decision` from these sources in order, stopping at the first that yields a non-empty rationale:

1. User text in the current invocation's `$ARGUMENTS` — e.g. "round 2, I tightened the assertions"
2. The artifact diff since `last_artifact_sha256`, when the change is small (≤200 chars added) — the diff *is* the rationale; record it verbatim
3. A `features/<feature>/decisions.md` entry added since `last_review_at` whose subject matches the blocker's `path_or_section` — use its `Why:` paragraph
4. Commit message body since `last_review_at` (`git log <last_review_sha>..HEAD --format=%B`)
5. Commit message subject
6. `"No rationale recorded"`

Cap at ~200 chars, truncating with `…`.

## Persist on exit

After the verdict renders, write:

- `last_review_at` ← now (UTC)
- `last_verdict` ← the rendered verdict
- `last_artifact_sha256` ← sha of the **post-fix** artifact
- `round_number` ← incremented
- `prior_blockers` ← rebuilt from this round's open blockers
- `recently_resolved_blockers` ← extended per the capture priority; entries past their `carry_forward_until_round` dropped
- `open_blocker_history` ← append `{round, open_blocker_count, open_question_count}`, every round without exception (the non-convergence tripwire reads this array)
- `per_round_metrics["round_<N>"]` ← append this round's counts

Leave the file in place on `APPROVED` / `CLOSED`. A later invocation against the same artifact — after partial implementation, or a brief amendment — needs the history.

## Manual reset

The user deletes the state file to discard round memory. The skill never auto-detects "this was rewritten, forget the past": that judgment is wrong often enough that explicit deletion is the only safe lever.
