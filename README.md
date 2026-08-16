# hgore-claude

An opinionated set of Claude Code skills, hooks, and shell helpers for a **spec-driven, review-heavy software development lifecycle**. Drop them into `~/.claude/` and they work in any repo that adopts the `features/` convention.

The pack turns a feature from an idea into merged code through a chain of small, verifiable artifacts — each one **authored** by a skill and then **prosecuted** by an adversarial review skill before the next layer descends from it. Plans are cheap; bad plans are expensive, so the review happens at every layer, not just at the code.

> This repo is a snapshot of the parts of my `~/.claude/` that are generic enough to share — no personal memory, no project transcripts, no machine-specific paths. Examples use a neutral placeholder domain; swap in your own.

## The lifecycle

```
spec.md ──/spec-author──▶ /spec-review
   │
   ▼
brief.md ──/brief-author──▶ /brief-review-v2      "what & why" for one feature
   │
   ├──/plan-alignment──▶ pick an architecture direction (recorded as a bound decision)
   ▼
engineering-plan.md ──/engineering-plan-author──▶ /engineering-plan-review-v2
   │                                               the chunk DAG between brief and code
   ▼
implementation/<chunk>.md ──/plan-author──▶ /plan-review-v2      one chunk = one PR
   │
   ▼
/execute-plan ──▶ (auto-opens the PR) ──▶ /review-pr-v2 ──▶ merge
```

Each **author** skill writes the artifact, grounding every claim against the repo and self-prosecuting before it emits. Each **review** skill convenes an adversarial tribunal of persona agents (correctness, security, architecture, testing, …) that attack the artifact, file findings with evidence, apply fixes, and return a verdict. `/plan-lint` is the deterministic structural floor the review skills assume has already passed.

## What's in here

```
skills/
  # Root spec
  spec-author/  spec-review/                  the project's source-of-truth spec.md

  # Feature brief — the "what & why"
  brief-author/  brief-review-v2/
  plan-alignment/                             choose an architecture direction, record the pick

  # Engineering plan — the chunk DAG
  engineering-plan-author/  engineering-plan-review-v2/

  # Per-chunk implementation plans
  plan-author/  plan-review-v2/
  plan-lint/                                  deterministic structural lint (briefs, EPs, chunk plans)

  # Execution & shipping
  execute-plan/                               TDD implementation of one chunk; auto-opens its PR
  open-pr/                                    commit in logical chunks, push, open a PR
  review-pr-v2/                               adversarial tribunal on the branch's PR
  cleanup-worktree/                           tear down a merged chunk's worktree

  # Blocker handling & scope
  explain-blockers/                           triage a review's blockers into decisions for you
  solve-blockers/  solve-blockers-headless/   research each blocker to a recommended fix
  scope-check/                                does the plan deliver each brief Goal in full?
  contract-review/                            cross-artifact contract consistency
  implementation-verify/                      independent re-proof of a finished chunk

  # Setup & shared internals
  features-init/                              scaffold the features/ folder in a new project
  _author-common/ _plan-common/               shared protocols the skills load
  _review-common/ _spec-common/
hooks/
  block-self-scheduling.sh                    ask before Claude self-invokes /open-pr, /execute-plan,
                                              /review-pr-v2, or a scheduler
statusline.sh                                 ctx-usage | dir | branch | model
settings.example.json                         wires up the hook + statusline
```

## Conventions the pack assumes

The skills operate on a `features/<feature>/` layout at your repo root:

```
features/<feature>/
  brief.md                 what the feature delivers and why
  engineering-plan.md      the chunk DAG (or plans/<track>/engineering-plan.md when large)
  decisions.md             the durable arbitration log
  implementation/<NN>-<chunk-slug>.md   one per-chunk plan; one chunk = one PR
```

Plus a project root that carries:

- `spec.md` — the product source of truth (business rules, formulas).
- `personas/*.md` — the reviewer lenses (`architecture.md`, `security.md`, `testing.md`, …). The review skills load these; **they must exist at your repo root** or the review stops rather than run under-calibrated.
- `CLAUDE.md` — your global rules (the skills read it for project conventions and business rules).

Run `/features-init` to scaffold the `features/` folder and its templates in a new project.

## Install

Symlinking is recommended — `git pull` then updates your live setup with no extra step.

### Option 1: Symlink (recommended)

```bash
git clone https://github.com/hgorelick/hgore-claude.git ~/src/hgore-claude
cd ~/.claude

# Skills — link the whole directory
mkdir -p skills
for d in ~/src/hgore-claude/skills/*/; do ln -s "$d" "skills/$(basename "$d")"; done

# Hook
mkdir -p hooks
ln -s ~/src/hgore-claude/hooks/block-self-scheduling.sh hooks/block-self-scheduling.sh

# Statusline
ln -s ~/src/hgore-claude/statusline.sh statusline.sh
```

### Option 2: Copy

```bash
git clone https://github.com/hgorelick/hgore-claude.git ~/src/hgore-claude
cp -R ~/src/hgore-claude/skills/*    ~/.claude/skills/
cp ~/src/hgore-claude/hooks/*        ~/.claude/hooks/
cp ~/src/hgore-claude/statusline.sh  ~/.claude/statusline.sh
chmod +x ~/.claude/hooks/*.sh ~/.claude/statusline.sh
```

### Wire up `settings.json`

If you don't have a `~/.claude/settings.json`, copy the example. If you do, merge the `statusLine` and `hooks` blocks from `settings.example.json` into it. The hook `command` paths resolve `~` at execution time, so they're portable across machines.

```bash
cp ~/src/hgore-claude/settings.example.json ~/.claude/settings.json   # only if you have none
```

### Verify

```bash
claude --version
# Then in any repo:
#   - statusline shows: ctx-usage | dir | branch | model
#   - /<skill-name> lists brief-author, plan-review-v2, execute-plan, …
#   - Claude self-invoking /open-pr surfaces a permission prompt (block-self-scheduling)
```

## How the flow runs in practice

1. `/brief-author <feature>` then `/brief-review-v2 <feature>` until the brief is APPROVED.
2. `/plan-alignment <feature>` to pick an architecture direction (bound in `decisions.md`).
3. `/engineering-plan-author <feature>` then `/engineering-plan-review-v2` until CLOSED.
4. Per chunk: `/plan-author <feature>/<chunk>` then `/plan-review-v2`. A second consecutive APPROVED auto-opens the plan's docs PR.
5. `/execute-plan <feature>/<chunk>` — TDD implementation inside an isolated worktree; on a clean (COMPLETE) verdict it auto-opens the chunk's PR into `main`.
6. `/review-pr-v2` on the PR (started fresh so the review is independent of the code-writing session), then merge, then `/cleanup-worktree`.

When a review returns **NEEDS USER INPUT**, `/explain-blockers` triages the blockers into plain-language decisions, or `/solve-blockers` researches each to a recommended fix.

## What the hook does

**`block-self-scheduling.sh`** — a `PreToolUse` matcher on `Bash`/`Skill`/scheduler tools that returns `ask` when Claude tries to **self-invoke** a hard-to-reverse workflow skill (`/open-pr`, `/execute-plan`, `/review-pr-v2`) or a scheduler. A slash command you type yourself doesn't route through the `Skill` tool, so it only fires on Claude's own programmatic chaining — the thing you want a human in the loop for.

## What the statusline does

`statusline.sh` reads the JSON Claude Code passes on stdin and prints:

```
<ctx-tokens>/<max> (PCT%) | <dir> | (<branch>*) | [<model>]
```

Context usage (color-shifting green→yellow→red toward the cap), working-dir basename, git branch (`*` + tint when dirty), and the short model name. Empty sections are skipped.

## Updating

```bash
cd ~/src/hgore-claude && git pull
```

Symlinked: that's it. Copied: re-run the relevant `cp` commands.

## License

MIT — do whatever you want with these. Attribution appreciated but not required.
