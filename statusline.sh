#!/bin/bash
input=$(cat)

MODEL=$(echo "$input" | jq -r '.model.display_name' | sed -e 's/ context//g' -e 's/ //g')
MODEL_ID=$(echo "$input" | jq -r '.model.id // ""')
DIR=$(basename "$(echo "$input" | jq -r '.workspace.current_dir')")
TRANSCRIPT=$(echo "$input" | jq -r '.transcript_path // ""')

# Context window size (1M models use the [1m] suffix)
if [[ "$MODEL_ID" == *"[1m]"* ]]; then
  MAX_CTX=1000000
else
  MAX_CTX=200000
fi

# Current context usage from most recent assistant message
TOKENS=0
if [ -f "$TRANSCRIPT" ]; then
  TOKENS=$(tail -n 200 "$TRANSCRIPT" 2>/dev/null \
    | jq -r 'select(.message.usage != null) | (.message.usage.input_tokens // 0) + (.message.usage.cache_creation_input_tokens // 0) + (.message.usage.cache_read_input_tokens // 0)' 2>/dev/null \
    | tail -1)
  [ -z "$TOKENS" ] && TOKENS=0
fi

# ANSI colors
C_MODEL=$'\033[36m'   # cyan
C_DIR=$'\033[95m'     # bright magenta
C_BRANCH=$'\033[32m'  # green
C_DIRTY=$'\033[33m'   # yellow (dirty tree)
C_WARN=$'\033[31m'    # red
C_SEP=$'\033[90m'     # dim gray
C_RESET=$'\033[0m'

SEP="${C_SEP} | ${C_RESET}"

# Git branch + dirty indicator if in a repo (no leading separator — added at join time)
BRANCH=$(git branch --show-current 2>/dev/null)
GIT_INFO=""
if [ -n "$BRANCH" ]; then
  if [ -n "$(git status --porcelain 2>/dev/null | head -1)" ]; then
    GIT_INFO="${C_DIRTY}(${BRANCH}*)${C_RESET}"
  else
    GIT_INFO="${C_BRANCH}(${BRANCH})${C_RESET}"
  fi
fi

# Context usage: format + color by % of max (no leading separator — added at join time)
CTX_INFO=""
if [ "$TOKENS" -gt 0 ]; then
  PCT=$(( TOKENS * 100 / MAX_CTX ))
  if [ "$TOKENS" -ge 1000000 ]; then
    CTX_DISPLAY=$(awk "BEGIN { printf \"%.2fM\", $TOKENS/1000000 }")
  elif [ "$TOKENS" -ge 10000 ]; then
    CTX_DISPLAY=$(awk "BEGIN { printf \"%dk\", $TOKENS/1000 }")
  else
    CTX_DISPLAY="${TOKENS}"
  fi
  if [ "$MAX_CTX" -ge 1000000 ]; then
    MAX_DISPLAY="1M"
  else
    MAX_DISPLAY="200k"
  fi
  if [ "$TOKENS" -ge 250000 ]; then
    CTX_COLOR="$C_WARN"
  elif [ "$TOKENS" -ge 125000 ]; then
    CTX_COLOR="$C_DIRTY"
  else
    CTX_COLOR="$C_BRANCH"
  fi
  CTX_INFO="${CTX_COLOR}${CTX_DISPLAY}/${MAX_DISPLAY} (${PCT}%)${C_RESET}"
fi

DIR_INFO="${C_DIR}${DIR}${C_RESET}"
MODEL_INFO="${C_MODEL}[${MODEL}]${C_RESET}"

# Order: context usage | dir | branch | model
# Skip empty sections (no context tokens yet, or not in a git repo)
parts=()
[ -n "$CTX_INFO" ] && parts+=("$CTX_INFO")
parts+=("$DIR_INFO")
[ -n "$GIT_INFO" ] && parts+=("$GIT_INFO")
parts+=("$MODEL_INFO")

output=""
for i in "${!parts[@]}"; do
  if [ "$i" -eq 0 ]; then
    output="${parts[$i]}"
  else
    output="${output}${SEP}${parts[$i]}"
  fi
done
printf "%s\n" "$output"
