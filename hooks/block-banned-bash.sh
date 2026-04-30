#!/bin/bash
# PreToolUse hook for the Bash tool: enforce the global "prefer Read/Edit/Write"
# rule from ~/.claude/CLAUDE.md. Returns permissionDecision:"ask" (not deny) so
# the user can approve case-by-case when there is genuinely no alternative.
#
# Banned patterns: cat/head/tail/less/more for file viewing, sed/awk for edits,
# echo/printf with > or >> for file writes, heredoc-to-file (cat <<EOF >file),
# and standalone jq invocations. The --jq flag inside `gh ... --jq ...` and
# similar wrapping CLIs is allowed (word-boundary-anchored pattern).

set -e

input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""')

# Allowlist: dev CLIs that are always permitted, even when piped through
# head/tail/etc. Match the leading command in the pipeline (after optional
# leading whitespace). Add tools here as needed.
if printf '%s' "$cmd" | grep -qE '^[[:space:]]*(~/\.cargo/bin/cargo|/Users/[^/]+/\.cargo/bin/cargo|/home/[^/]+/\.cargo/bin/cargo|gh|git|cargo|rustc|rustup|npm|npx|pnpm|yarn|bun|bunx|node|deno|python|python3|pip|pip3|uv|make|cmake|docker|ls|cd|wc|find|rg|cp|mv)([[:space:]]|$)'; then
  exit 0
fi

reason=""

# File viewing: cat / head / tail / less / more (start of command or after pipe/&&/;)
if printf '%s' "$cmd" | grep -qE '(^|[|;&]+[[:space:]]*)(cat|head|tail|less|more)([[:space:]]|$)'; then
  reason="Use Read for file viewing, not cat/head/tail/less/more."
fi

# Substitutions: sed / awk
if [ -z "$reason" ] && printf '%s' "$cmd" | grep -qE '(^|[|;&]+[[:space:]]*)(sed|awk)[[:space:]]'; then
  reason="Use Edit for substitutions, not sed/awk."
fi

# Heredoc to file: cat <<EOF > file (covers `cat <<'EOF' >file`, `cat <<-EOF >> file`, etc.)
if [ -z "$reason" ] && printf '%s' "$cmd" | grep -qE 'cat[[:space:]]*<<[-]?[[:space:]]*'\''*[A-Za-z_]+'\''*.*>'; then
  reason="Use Write for file creation, not heredoc redirection."
fi

# Echo/printf with redirection to a file
if [ -z "$reason" ] && printf '%s' "$cmd" | grep -qE '(^|[|;&]+[[:space:]]*)(echo|printf)[[:space:]].*[^&0-9]>{1,2}[[:space:]]*[^&]'; then
  reason="Use Write/Edit for file output, not echo/printf redirection."
fi

# Standalone jq (word-boundary-anchored: skips --jq flags inside other CLIs)
if [ -z "$reason" ] && printf '%s' "$cmd" | grep -qE '(^|[|;&]+[[:space:]]*)jq([[:space:]]|$)'; then
  reason="Use Read for JSON inspection. The --jq flag inside gh/curl is fine; standalone jq is banned."
fi

if [ -n "$reason" ]; then
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"%s Ask the user for explicit permission if no Read/Edit/Write equivalent fits."}}\n' "$reason"
fi

exit 0
