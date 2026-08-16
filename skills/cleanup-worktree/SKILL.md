---
name: cleanup-worktree
description: Fully tear down a git worktree after its work is merged — remove the worktree, its isolated dev-stack Docker containers, and its local branch, then sweep for orphaned worktree dirs and <project>-wt-* Docker stacks so nothing residual is left behind. For a plan-authoring worktree (`<slug>-plan`), also print the ready-to-paste `/execute-plan` command for the next session. Use after a PR from a worktree branch is merged and the user wants the worktree cleaned up (e.g. "pr merged, clean up the worktree").
user-invocable: true
---

# Cleanup Worktree

Full teardown of a git worktree and everything it owns, plus an orphan sweep. Built for a project's worktree setup (`worktree.sh` + per-worktree `<project>-wt-<name>` Docker stacks); degrades gracefully when `worktree.sh` is absent.

## Inputs

- `[<name>]` — the worktree to remove (its `.worktrees/<name>` directory name / branch). Optional:
  - **Given** → use it.
  - **Omitted, shell is inside a worktree** → target that worktree.
  - **Omitted, ambiguous** (in the main checkout with multiple worktrees) → `git worktree list` and ask which one via `AskUserQuestion`.

## Invoking this skill means the PR is merged — trust it, never re-verify (don't waste tokens)

**Invoking `/cleanup-worktree` IS the statement that the PR is merged.** With or without a `<name>`, the invocation itself asserts: *this worktree's PR has merged — tear it down.* That is what the command means. The user does not need to also type "it's merged" or "pr merged" — the invocation already said it. Treat the invocation exactly as the user telling you the PR has merged, and act on it.

**TRUST it and act — do not spend a single tool call verifying the merge.** Do **NOT** run `gh pr view`, `git fetch`, `git merge-base`, or any status poll to prove the merge landed. Re-checking a fact the invocation already asserted wastes tokens and reads as mistrust — the user has explicitly asked not to do this. Do not let anything you happen to know from earlier in the session (that the PR was open, that CI was running) override the invocation — the invocation is newer and authoritative. Two traps to preempt:

- A **squash merge** gives `git merge-base --is-ancestor` a FALSE NEGATIVE (the squashed commit has a new SHA). Do not let that tempt an escalation to GitHub — a clean tree plus a pushed branch already means there is no local work to lose.
- `gh pr view` to confirm a merge is **never** a "local data-loss check" — it is network re-verification of the exact fact stated. Skip it.

The only guard needed is the dirty-tree abort built into `git worktree remove` (Remove step below). Go straight to removal.

## Procedure

**`cd` to the repo root (main checkout) FIRST — this is required for a clean removal.** A worktree cannot be cleanly removed while the shell's cwd lives inside it: the shell gets stranded when the directory is deleted, and `git worktree remove` can abort. Every command below runs from `<main>` (the main checkout root), and each destructive command starts with `cd <main> && …` so it is unambiguous.

If cwd is the target worktree, resolve `<main>` first: `git worktree list` → the row tagged `[main]` (or the parent of `git rev-parse --path-format=absolute --git-common-dir`). Use that absolute path as `<main>` everywhere.

### Resolve target and main checkout

- `git worktree list` — capture the `<main>` checkout path; confirm `<name>` is a registered worktree.
- Record the target's on-disk path (`<main>/.worktrees/<name>`) and its branch.

### Remove the worktree

**When your project provides a worktree bootstrap script** — when `<main>/worktree.sh` exists:

```bash
cd <main> && ./worktree.sh remove <name>
```

This stops processes bound to the worktree's DB, runs `git worktree remove` (no `--force` — it **aborts on a dirty tree**, the intended data-loss guard), tears down the `<project>-wt-<name>` Docker stack with `down -v` (container + volume + network, scoped to that project only), and deletes the local branch.

- **If it aborts on a dirty tree:** surface the uncommitted changes and STOP. Do not add `--force` without an explicit ask — uncommitted work would be lost.

**Generic path** — when `worktree.sh` is absent:

```bash
cd <main> && git worktree remove <name>     # aborts on a dirty tree
git -C <main> branch -D <branch>            # -D: the user has confirmed the work is merged
```

Then tear down any per-worktree Docker stack the project spins up (`docker compose -p <project> down -v`).

### Verify the target is gone

- `test -e <main>/.worktrees/<name>` → must be **GONE**.
- `git worktree list` → `<name>` no longer listed.
- (when your project provides a worktree bootstrap script) `docker compose ls -a | grep <project>-wt-<name>` and `docker ps -a --filter name=<project>-wt-<name>` → both empty.

### Sweep orphans (the whole class, not just the target)

Past removes have left residual empty dirs and stray stacks — always sweep, even when the target removed cleanly.

- **Directory orphans:** diff `ls <main>/.worktrees/` against `git worktree list`. Any dir NOT registered is an orphan. Run `git -C <main> worktree prune`, then `rm -rf` any residual `.worktrees/*` dir that is unregistered AND empty (verify both before removing).
- **Docker-stack orphans:** list `<project>-wt-*` compose projects (`docker compose ls -a`) and containers (`docker ps -a --filter name=<project>-wt-`). Any `<project>-wt-<x>` whose `<x>` is not a currently-registered worktree → `docker compose -p <project>-wt-<x> down -v`. Leave stacks backing active worktrees untouched. Only touch `<project>-wt-*` projects under THIS repo's tree — never the project's main stack, never compose projects living under other directory trees.
  - A registered worktree that predates the isolated-DB change has NO `<project>-wt-*` stack (it rides the shared DB) — that is expected, not an orphan.

### Report

State what was removed (worktree dir, Docker stack, branch) and the orphan-sweep result (orphans found + cleared, or "none"). Keep it to a few lines.

**Never hedge about the merge.** The invocation already asserted the PR is merged, so do NOT append caveats implying otherwise — no "the PR is still open," no "CI is still running," no "the remote branch still lives on GitHub," no "this only removed your local copy." Those read as second-guessing the merge the invocation confirmed. Report only what was torn down and the sweep result, and stop.

### Print the `/execute-plan` command (plan-authoring worktrees only)

When the worktree you just removed was a **plan-authoring worktree** — a plain worktree (no `<project>-wt-<name>` Docker stack) whose name ends in `-plan`, where `/plan-author` wrote one chunk's plan on the `<slug>-plan` branch — print the ready-to-paste `/execute-plan` command as the **last thing** in your report. Print it only; do **not** invoke `/execute-plan` — the user runs it themselves in a fresh session (they always clear context first).

1. **Chunk slug** = the worktree name with the trailing `-plan` stripped (`detail-panel-state-plan` → `detail-panel-state`). If the removed worktree did NOT end in `-plan`, or it had a `<project>-wt-<name>` Docker stack (an implementation worktree, or any other worktree), print nothing extra — skip this step.
2. **Qualify the ref** the way `/execute-plan` resolves it — glob the merged plan on `main` from `<main>`: `features/*/implementation/{<slug>,[0-9]*-<slug>}.md` and `features/*/plans/*/implementation/{<slug>,[0-9]*-<slug>}.md`. Exactly one match → `<feature>/<chunk-slug>` (flat) or `<feature>/<track>/<chunk-slug>` (tracked). Zero or multiple matches → fall back to the bare `<chunk-slug>`.
3. **Print the command on its own line** so it copies cleanly:

   ```
   /execute-plan <feature>/<chunk-slug>
   ```

## Notes

- The removal (worktree + `down -v` + branch delete) is destructive and hard to reverse, but is the explicit purpose of this skill once the user has said the work is merged — no extra confirmation needed beyond a dirty-tree abort.
- Full worktree docs and the `<project>-wt-<name>` stack model live in the project `CLAUDE.md` (§Git Worktrees / §Database Protection).
