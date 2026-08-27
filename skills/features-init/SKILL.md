---
name: features-init
description: Initialize the canonical features/ folder structure in a target project. Writes README.md and _template/{brief,engineering-plan,chunk,decisions}.md from the skill's bundled sources. Default target is the current working directory; pass a path argument to override. Refuses to overwrite existing files unless --force is passed. Use when bootstrapping the brief-author / engineering-plan-author / plan-author workflow in a new project.
---

# Features Init

Bootstraps `features/` in a target project: the `README.md` process doc and the four `_template/` files that brief-author / engineering-plan-author / plan-author consume.

## Inputs

- `[<path>]` — target directory. Defaults to `pwd`.
- `--force` — overwrite any of the target files that already exist. Without this flag the skill refuses if any target file is present.

## Workflow

1. Resolve target directory: arg if given, else `pwd`.
2. Probe each target path:
   - `<target>/features/README.md`
   - `<target>/features/_template/brief.md`
   - `<target>/features/_template/engineering-plan.md`
   - `<target>/features/_template/chunk.md`
   - `<target>/features/_template/decisions.md`
3. If any path exists AND `--force` not set: refuse. List which paths blocked it. Stop.
4. Otherwise: `mkdir -p <target>/features/_template`, then `cp` each bundled template from `~/.claude/skills/features-init/templates/` into the corresponding target path.
5. Report what was written and what was overwritten (when `--force`). Point at `/brief-author <feature-slug>` as the next step.

## Hard rules

- Default refuses to overwrite. `--force` is the only override; when used, warn the user that custom edits to those files will be lost.
- Write only the 5 files. Do NOT create feature folders, sample features, or `archive/`. Those belong to per-feature workflows downstream.
- Do NOT modify anything outside `<target>/features/`.
- Do NOT verify project preconditions (no git check, no CLAUDE.md check, no language/stack detection). Just write.
- Use `cp` from `~/.claude/skills/features-init/templates/`, not Read+Write round trips.

## Bundled templates

`~/.claude/skills/features-init/templates/`:
- `README.md` — process doc explaining stages, naming, lifecycle, decision-log format, and the brief roster: the `Brief | Parent spec | Status` table and the deferred-spec-surface list that are this tree's home for decomposition state, since a spec carries only what is permanently true about its briefs.
- `brief.md` — Stage 1 product brief, headed by the `Spec:` line naming its parent spec.
- `engineering-plan.md` — Stage 2 chunk graph + architecture contract.
- `chunk.md` — Stage 3 per-chunk implementation plan.
- `decisions.md` — append-only decision log; entries carry a `Status:` line (`bound` | `superseded by "<title>" (<date>)` | `obsolete`) and split into `## Active (bound)` / `## Archived (superseded / obsolete)` so scanners treat only Active bound entries as authoritative.

To update the canonical templates: edit the bundled files in place. Next invocation in any project picks up the changes.

## Edge cases

- **`<target>/features/` exists but is empty**: proceed; no files to refuse on.
- **`<target>/features/_template/` exists but `README.md` doesn't (or vice versa)**: refuse on whichever paths exist. `--force` overwrites only those that exist; the missing ones are still written.
- **`<target>` does not exist**: refuse with "target directory does not exist". Don't create the parent.
- **Target path is a file, not a directory**: refuse.
