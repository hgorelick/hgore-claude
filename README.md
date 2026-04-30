# hgore-claude

A small, opinionated set of Claude Code skills, hooks, and shell helpers I use every day. Drop them into `~/.claude/` and they work anywhere Claude Code runs.

This repo is a snapshot of the parts of my `~/.claude/` that are generic enough to share — no personal memory, no project transcripts, no machine-specific paths in the files themselves.

## What's in here

```
skills/
  engineering-plan-review/SKILL.md   adversarial tribunal on a feature's engineering plan
  open-pr/SKILL.md                   commit in logical chunks, push, open a PR into main
  plan-review/SKILL.md               adversarial tribunal on per-chunk implementation plans
  review-pr/SKILL.md                 adversarial tribunal on the current branch's PR
hooks/
  block-banned-bash.sh               PreToolUse guard: nudge Claude to use Read/Edit/Write
                                     instead of cat/sed/echo>file/standalone-jq
statusline.sh                        custom status line: ctx-usage | dir | branch | model
settings.example.json                template wiring up the hook + statusline
CLAUDE.md.example                    the global rules the hook enforces (paste into ~/.claude/CLAUDE.md)
```

The skills are user-invocable as slash commands once they're under `~/.claude/skills/`. The hook is a `PreToolUse` matcher on `Bash` that returns `permissionDecision: "ask"` for banned patterns — Claude can still run them, but only after you confirm.

## Install

Two options. Symlinking is recommended — pulling new commits then updates your live setup with no extra step.

### Option 1: Symlink (recommended)

```bash
git clone https://github.com/hgorelick/hgore-claude.git ~/src/hgore-claude
cd ~/.claude

# Skills (each skill is its own dir at ~/.claude/skills/<name>/SKILL.md)
mkdir -p skills
ln -s ~/src/hgore-claude/skills/engineering-plan-review skills/engineering-plan-review
ln -s ~/src/hgore-claude/skills/open-pr               skills/open-pr
ln -s ~/src/hgore-claude/skills/plan-review           skills/plan-review
ln -s ~/src/hgore-claude/skills/review-pr             skills/review-pr

# Hook
mkdir -p hooks
ln -s ~/src/hgore-claude/hooks/block-banned-bash.sh hooks/block-banned-bash.sh

# Statusline
ln -s ~/src/hgore-claude/statusline.sh statusline.sh
```

### Option 2: Copy

```bash
git clone https://github.com/hgorelick/hgore-claude.git ~/src/hgore-claude
cp -R ~/src/hgore-claude/skills/*    ~/.claude/skills/
cp ~/src/hgore-claude/hooks/*        ~/.claude/hooks/
cp ~/src/hgore-claude/statusline.sh  ~/.claude/statusline.sh
chmod +x ~/.claude/hooks/block-banned-bash.sh ~/.claude/statusline.sh
```

### Wire up `settings.json`

If you don't have a `~/.claude/settings.json`, copy the example as a starting point:

```bash
cp ~/src/hgore-claude/settings.example.json ~/.claude/settings.json
```

If you already have one, merge the `statusLine` and `hooks` blocks from `settings.example.json` into it. The hook's `command` resolves `~` at hook-execution time, so the path is portable across machines.

### Wire up `CLAUDE.md`

The hook is a guard rail for a global rule that lives in your `~/.claude/CLAUDE.md`. The rule has to actually be there or Claude won't know how to comply when the guard fires.

```bash
# If you don't have a global CLAUDE.md yet:
cp ~/src/hgore-claude/CLAUDE.md.example ~/.claude/CLAUDE.md

# If you already have one, append the "Global rules" section from CLAUDE.md.example.
```

### Verify

```bash
claude --version
# Then start Claude Code in any directory and check:
#   - statusline shows: ctx-usage | dir | branch | model
#   - typing /<skill-name> lists engineering-plan-review, open-pr, plan-review, review-pr
#   - asking Claude to run `cat some_file.md` triggers a permission prompt
```

## What each skill does

### `/open-pr`
Stages your changes in logical chunks, makes one commit per concern, pushes the branch, opens a PR into `main` with a structured body. Use after you finish work and want to ship it.

### `/review-pr`
Convenes an adversarial tribunal on the current branch's PR. Multiple "prosecutor" personas (correctness, hallucination, invariant, security, drift, test, scope, factoring) attack the diff, file findings with file:line evidence, fix every defect, and loop until clean. Use after `/open-pr`.

### `/plan-review <plan-path-or-slug>`
Tribunal review for **per-chunk implementation plans** (`features/<feature>/implementation/<slug>.md`). Verifies every path, line number, identifier, and command in the plan against actual repo state, then prosecutes the plan from each persona's angle. N plans × M personas = N×M parallel review agents.

### `/engineering-plan-review <feature>`
Sister skill to `/plan-review`, but targets the **engineering plan** (`features/<feature>/engineering-plan.md`) — the layer between the brief and the per-chunk plans. Prosecutes chunk granularity, brief-trace audits, hidden cross-chunk dependencies, false parallelism, missing rollback paths, and implementation-detail leaks.

> Both review skills assume a `features/<feature>/` layout with a `brief.md` and (for engineering plans) an engineering-plan.md and per-chunk plans under `implementation/`. They are most useful in repos that adopt that convention; they will still run elsewhere but most of the brief-mapping/structural checks will report findings until you adapt the structure or skip them.

## What the hook does

`hooks/block-banned-bash.sh` is a `PreToolUse` matcher on the `Bash` tool. When Claude tries to run a banned form, the hook returns:

```json
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", ...}}
```

…which surfaces a permission prompt instead of letting the command run silently. Banned forms (with the dedicated alternative):

| Banned                                                | Use instead    |
|-------------------------------------------------------|----------------|
| `cat`, `head`, `tail`, `less`, `more` for viewing     | **Read**       |
| `sed`, `awk` for substitutions                        | **Edit**       |
| `echo > file`, `printf > file`, heredoc-to-file       | **Write**      |
| Standalone `jq` (the `--jq` flag inside `gh` is fine) | **Read** + parse |

The hook short-circuits and lets the call through if the leading command in the pipeline is one of: `gh`, `git`, `cargo`, `rustc`/`rustup`, `npm`/`npx`/`pnpm`/`yarn`/`bun`/`bunx`, `node`/`deno`, `python`/`python3`, `pip`/`pip3`, `uv`, `make`/`cmake`, `docker`, `ls`/`cd`/`wc`/`find`/`rg`/`cp`/`mv`. So `cargo test 2>&1 | head -20` and `gh pr view --json reviews --jq '.reviews'` work without prompting.

The rule pairs with the "Tool selection" / "Escape hatch" sections in `CLAUDE.md.example` — Claude reads those at session start and knows it has to state *what banned form, why no alternative, what outcome* before invoking one.

### Customizing the allowlist

Don't like that some tool is banned, or want a project-local CLI added to the allowlist? Just tell Claude in plain English — no need to point it at the file or describe the regex. Things like:

> "whitelist jq in the banned hook"
> "stop banning awk"
> "add mycli to the hook allowlist"

…are all enough. Claude will open `~/.claude/hooks/block-banned-bash.sh`, find the right regex (the allowlist is near the top; the banned-pattern blocks are below it), and edit it for you. The next Bash call picks up the change — no restart needed.

### Heads up: it's not foolproof

Even with the `CLAUDE.md` rule *and* the hook firing a permission prompt, Claude will still reach for `cat`/`sed`/`echo > file`/standalone `jq` more often than you'd expect — sometimes after explicitly acknowledging the rule in the same turn. The hook makes that harmless (you just deny the prompt) but it's annoying. When it happens, deny the call and remind Claude to use Read/Edit/Write. Treat the hook as a safety net for when the rule slips, not a guarantee Claude will follow the rule on its own.

## What the statusline does

`statusline.sh` reads the JSON Claude Code passes on stdin and prints:

```
<ctx-tokens>/<max> (PCT%) | <dir> | (<branch>*) | [<model>]
```

- **ctx-tokens / max**: tokens consumed in the most recent assistant turn, against the model's window (200k or 1M for `[1m]` models). Color shifts green → yellow → red as you approach the cap.
- **dir**: basename of the current working directory.
- **branch**: current git branch, with a `*` and yellow tint if the tree is dirty.
- **model**: short display name from Claude Code (e.g. `[Opus4.7]`).

Sections are skipped when empty (no git repo, no transcript yet).

## Updating

```bash
cd ~/src/hgore-claude && git pull
```

If you symlinked, that's it — your live setup picks up the new files. If you copied, re-run the relevant `cp` commands.

## License

MIT — do whatever you want with these. Attribution appreciated but not required.
