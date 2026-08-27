---
name: ep-close
description: Marks an engineering plan as implementation complete and CLOSED after every chunk in its DAG has shipped to main — writes the closed marker into the plan, binds the closure in decisions.md, and flags the state sidecars. A closed plan accepts no new chunks; later scope routes to an open sibling track, a new track, or a new feature (see `_plan-common/layout.md` § Closed engineering plans). Use when a plan's implementation is finished (e.g. "blend-core is done, close its EP").
user-invocable: true
---

# EP Close

Seals a finished engineering plan. After this runs, no author/review skill may add a chunk to the plan, re-author it, or propose it as the landing place for new scope — the routing rule lives in `~/.claude/skills/_plan-common/layout.md` § Closed engineering plans, which every plan-layer skill loads.

Closing is **implementation-lifecycle**, not review-lifecycle: it is unrelated to `/engineering-plan-review-v2`'s `CLOSED` verdict (all decisions bound, chunk authoring unblocked). A plan is closable regardless of what its last review verdict was, provided its chunks all shipped.

## Inputs

- `<feature>` or `<feature>/<track>` — resolved per `~/.claude/skills/_plan-common/layout.md` § Resolution. A bare `<feature>` resolving to two or more plan roots: list the tracks with their `Status:` and ask which (closing all tracks at once is valid if the user says so — close each in turn).

Already closed (marker present) → report the existing closure line and stop. No-op, no error.

## Invoking this skill means implementation is complete — trust it, never verify (don't waste tokens)

**Invoking `/ep-close` IS the statement that the plan's implementation is finished.** The invocation itself asserts: *every chunk in this plan shipped — seal it.* The user does not need to prove it, and this skill does not audit it. Treat the invocation exactly as the user telling you the implementation is complete, and act on it (`memory/feedback_trust_user_stated_facts.md`).

**Do NOT spend tool calls verifying shipment.** No `git log --grep` per chunk, no matching slugs to commit subjects, no `gh pr list`, no fetch, no checking that chunk plan files exist. Commit conventions paraphrase, chunks get re-scoped mid-flight, and a per-slug audit turns a one-minute seal into an archaeology session that ends by asking the user to confirm what the invocation already said. The only read of the plan is parsing the chunk index for the count and slugs the decisions entry lists — bookkeeping, not verification. If the user volunteers that something is unshipped, record it verbatim in the decisions entry and close anyway — the director call is theirs.

## Writes

All dates are today's, absolute.

1. **The plan file.** Insert the machine marker as the line immediately after the `#` title:
   `<!-- Status: closed — implementation complete YYYY-MM-DD -->`
   and add a human-visible line to the header metadata block (with `**Created:**` / `**Last updated:**`):
   `**Status:** Closed — implementation complete YYYY-MM-DD. No new chunks; new scope routes per layout.md § Closed engineering plans.`
   The comment is the canonical machine channel (the same `Status:` frontmatter channel the author/review skills already dispatch on); the bold line is informational. Never write `Status: closed` into a plan by any other route — this skill is the only writer.
2. **`features/<feature>/decisions.md`** — a bound entry, so review carry-forward machinery can retract any later "add a chunk to this plan" finding on decisions-log authority:

   ```markdown
   ## YYYY-MM-DD — <track or feature>: engineering plan closed — implementation complete (/ep-close)

   **Decision:** The <feature>/<track> engineering plan is implementation complete and closed. All <n> chunks in its index shipped to main (<slug>, <slug>, …). The plan accepts no new chunk rows and is not re-authored or amended. Scope that would have landed here routes to an open sibling track, a new track (`_plan-common/layout.md` § Adding a track), or a new feature — proposing a chunk addition to this plan is a defect, not a resolution path.

   **Status:** bound

   **Why:** Closure declared by the director via /ep-close; the invocation is the statement of completion and is not audited.{ user-volunteered exceptions: " Noted as unshipped/deferred at closure: <list, verbatim>."}

   **Where it lands:** `<plan-root>/engineering-plan.md` (Status marker).
   ```

   Cite PR numbers only when they are already known in-session — never go looking.
3. **State sidecars** — in `~/.claude/cache/author-state/<ep-slug>.json` and `~/.claude/cache/review-state/<ep-slug>.json` (slug per layout.md § State-slug derivation), when the file exists, add `"ep_closed": true, "ep_closed_date": "YYYY-MM-DD"`. Never create a sidecar just to hold the flag — the plan-file marker is canonical; the sidecar flag is a warm-cache convenience.

## Commit

The edits touch the project repo. Commit them immediately, without asking — invoking `/ep-close` IS the authorization for this commit, the same way it is the statement of completion; proposing the command and waiting re-asks what the invocation already answered. The commit: `docs(<feature>): close <track> engineering plan — implementation complete`, bundling the plan file + decisions.md. Administrative bookkeeping after all chunk PRs merged: commit direct to the current branch (normally `main`, mirroring the DAG-update convention); no PR, no Test plan section. The invocation's grant covers the commit only — never push without an explicit ask or a standing project convention covering docs pushes.

## Report

Short: chunk count sealed, the marker line written, the decisions entry title, sidecars flagged (or absent), and the commit hash (noting it is unpushed). One line each.
