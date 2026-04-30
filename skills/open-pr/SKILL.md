---
name: open-pr
description: Commit changes in logical chunks, push branch, and open a PR into main. Use when the user has completed work and wants to ship it.
user-invocable: true
---

# Open PR

Commit all current changes in logical, atomic chunks and open a pull request into `main`.

## Workflow

### 1. Assess Current State

Run these in parallel:
- `git status` — see all changed/untracked files
- `git diff` — see unstaged changes
- `git diff --cached` — see staged changes
- `git log --oneline -5` — see recent commit style

### 2. Group Changes into Logical Commits

Analyze all changed files and group them by concern. Each commit should be a single logical unit:
- Schema/migration changes separate from resolver changes
- Backend separate from frontend (unless tightly coupled)
- Test files with their corresponding implementation
- Config/tooling changes separate from feature code

**Commit message format**: `type: description` (feat, fix, refactor, test, docs)
- Keep the first line under 72 characters
- Add a body paragraph if the change needs explanation
- NEVER add `Co-Authored-By` lines

### 3. Stage and Commit Each Group

For each logical group:
1. Stage only the files for that group: `git add <specific files>`
2. Commit with a descriptive message using a HEREDOC:
   ```bash
   git commit -m "$(cat <<'EOF'
   type: concise description of what and why
   EOF
   )"
   ```
3. Verify with `git status` before moving to the next group

### 4. Push Branch

```bash
git push -u origin HEAD
```

If the branch doesn't have an upstream yet, this sets it. If it does, a regular `git push` suffices.

### 5. Open the PR

Use `gh pr create` with a clear title and structured body:

```bash
gh pr create --title "type: concise PR title" --body "$(cat <<'EOF'
## Summary
- Bullet point summary of what changed and why (1-3 bullets)

## Changes
- List of specific changes grouped by area

## Test plan
- [ ] How to verify the changes work

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

**PR title rules**:
- Under 70 characters
- Same `type: description` format as commits
- Describes the overall change, not individual commits

**PR body rules**:
- Summary section: high-level what and why (1-3 bullets)
- Changes section: specific changes grouped by area
- Test plan: concrete verification steps

### 6. Report

Output the PR URL so the user can see it. Include a summary of:
- Number of commits created
- Brief description of each commit
- PR title and URL
