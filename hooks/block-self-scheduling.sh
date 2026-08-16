#!/bin/bash
# PreToolUse hook: prompt before any tool you've banned Claude from
# self-invoking. Catches ScheduleWakeup / CronCreate directly, and the /loop,
# /schedule, /open-pr, /execute-plan, and /review-pr-v2 skills via the Skill
# tool. Uses "ask" (not "deny") so you can still approve when you explicitly
# invoked the skill. A slash command you TYPE is injected as a command and does
# not route through the Skill tool, so this hook only fires on Claude's own
# programmatic Skill-tool invocations (the auto-chain).
#
# The intent: hard-to-reverse, outward-facing actions (opening a PR) and
# recurring/deferred work (schedulers) should have a human in the loop, even
# when a skill's own instructions tell Claude to chain into them.

set -e

input=$(cat)
tool_name=$(printf '%s' "$input" | jq -r '.tool_name // ""')
skill_name=$(printf '%s' "$input" | jq -r '.tool_input.skill // ""')

reason=""

case "$tool_name" in
  ScheduleWakeup)
    reason="ScheduleWakeup is a self-scheduling tool. Do not self-invoke. Only allowed when the user has explicitly invoked /loop or /schedule in this turn."
    ;;
  CronCreate)
    reason="CronCreate sets up a recurring remote agent. Do not self-invoke. Only allowed when the user has explicitly invoked /schedule in this turn."
    ;;
  Skill)
    case "$skill_name" in
      loop|schedule)
        reason="The /$skill_name skill sets up recurring/deferred work. Only invoke when the user explicitly typed /$skill_name in their most recent message."
        ;;
      open-pr)
        reason="The /open-pr skill commits, pushes, and opens a PR — a hard-to-reverse action visible to others. NEVER self-invoke. Only allowed when the user explicitly typed /open-pr in their most recent message."
        ;;
      execute-plan)
        reason="The /execute-plan skill implements a chunk end-to-end (TDD, commits, opens a PR). NEVER auto-invoke or auto-chain it — the user ALWAYS clears context first and starts it themselves. Only allowed when the user explicitly typed /execute-plan in their most recent message."
        ;;
      review-pr-v2)
        reason="The /review-pr-v2 skill runs the adversarial PR review and posts a verdict to the PR. NEVER auto-chain it after /open-pr or /execute-plan — the user ALWAYS clears context first so the review runs independent of the session that wrote the code. Stop after the PR is open and let the user start the review themselves. Only allowed when the user explicitly typed /review-pr-v2 in their most recent message."
        ;;
    esac
    ;;
esac

if [ -n "$reason" ]; then
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"%s"}}\n' "$reason"
fi

exit 0
