---
name: plan-alignment
description: Presents two or three architecture directions for an approved brief, with the tradeoff each commits you to, and records your pick as a bound decision. Run between `/brief-review-v2` and `/engineering-plan-author`, so the architecture call is yours rather than a side effect of a skill run. Sister to `/explain-blockers`, which triages review blockers the same way.
user-invocable: true
---

# /plan-alignment

Puts the architecture decision in front of you *before* the engineering plan is written, instead of after.

## Why this exists

`/engineering-plan-author` reads the brief and produces a chunk DAG. Somewhere inside that run it also picks the architecture — which layer owns the new state, whether the change is additive or a rewrite, where the seam between chunks falls. By the time you see the output, the call is made and everything downstream is built on it. Disagreeing then means discarding a reviewed plan.

The architecture call is the highest-leverage decision in the feature and the one most sensitive to context a brief cannot carry: what else is in flight, what you are willing to maintain, which direction you would rather not be locked into. That is your call, and this is where it gets made.

The cost is one message. There is no meeting, no document, and no artifact beyond a `decisions.md` entry.

## When to invoke

After `/brief-review-v2` returns APPROVED, before `/engineering-plan-author`.

**Skip it** when the approach follows an established pattern in the repo with no real alternative — a resolver that looks like six existing resolvers, a migration shaped like the last three. Record the skip and its reason in `decisions.md` so a later reader knows the direction was considered rather than defaulted into. Skipping to save time on a feature that *does* have alternatives is how the plan ends up carrying an unexamined commitment.

## Usage

```
/plan-alignment <feature>
```

Resolves `features/<feature>/brief.md` and `features/<feature>/decisions.md`.

## Procedure

1. **Read the brief and the ground.** `brief.md` (Goals with their `Measured by:` clauses, the `## Scope` buckets, User-facing changes), `decisions.md` (bound entries constrain every direction below), `spec.md`, `CLAUDE.md`, and project memory. Then read the actual source the feature touches — the resolvers, hooks, tables, and scripts the Goals imply. A direction proposed without reading the incumbent code is a guess dressed as an option.

2. **Refuse if the brief is mid-cycle.** A brief carrying `Status: needs-user-input` has unresolved blockers; aligning on an architecture for a scope that is still moving wastes the decision. Say so and stop.

3. **Construct two or three genuinely different directions.** Different in what they commit to, not in surface detail. Two real options beat three where one is padding — if only one approach survives contact with the repo, say that instead of inventing rivals.

   For each: one paragraph on the shape, then the tradeoff stated as **what it commits you to** — the thing that becomes expensive to reverse. Not a generic pros-and-cons list. "Puts the flag in the resolver, so every future consumer inherits it and removing it later means touching all of them" is a commitment. "More flexible" is not.

   Add a rough chunk shape per direction: how many chunks and roughly where the seams fall. **No slugs, no DAG, no plan** — that is `/engineering-plan-author`'s job and pre-empting it here produces a plan you will edit twice.

4. **Surface the open questions.** Three to five, drawn from what the brief left unresolved and what reading the code turned up. Questions whose answer changes which direction wins go first — those are the real decision, and the direction choice may follow from them rather than the other way around.

5. **Ask, with a pick.** End in `AskUserQuestion` with the directions as options. State your recommendation and one sentence of why, leading with what the call commits to. Cluster questions that share one answer into a single call.

6. **Record the decision.** Append to `features/<feature>/decisions.md`:

   ```markdown
   ## YYYY-MM-DD — Architecture direction: <short name>
   **Decision:** <the chosen direction, one or two sentences, concrete.>
   **Why:** <the reason it was chosen, including what it commits us to.>
   **Rejected:** <each other direction, one clause each, with why not.>
   ```

   `/engineering-plan-author` already ingests `decisions.md` at Source ingest and treats bound entries as constraints, so nothing else needs wiring. When alignment was skipped, the entry reads `**Decision:** Alignment skipped — <reason>.`

## Voice

`~/.claude/CLAUDE.md` § "Talking to the user" governs. Answer first, short sentences, no preamble. Options are one short clause each with a stated pick. Keep review-machinery vocabulary out entirely — the audience is deciding what to build, not reading a review.

Directions are named for what they do (`resolver-owned flag`, `client-side derivation`), never `Option A` / `Option B`. A named direction is referable in `decisions.md` months later; a letter is not.

## What this skill does not do

- **It does not write the engineering plan.** No chunk index, no slugs, no dependency graph.
- **It does not re-open scope.** Scope questions belong to the brief. If a direction only works by changing a Goal or moving something between Scope buckets, that is a brief amendment — say so and stop, rather than quietly choosing the direction that reshapes the scope.
- **It does not produce a document.** The `decisions.md` entry is the entire artifact. An alignment write-up is overhead nobody reads twice.

## Relationship to sister skills

- **`/brief-review-v2`** runs before. Its APPROVED verdict is the precondition.
- **`/engineering-plan-author`** runs after and consumes the recorded decision through `decisions.md`.
- **`/explain-blockers`** is the same voice applied to review blockers rather than architecture directions — one-line question, short options, a stated pick.
