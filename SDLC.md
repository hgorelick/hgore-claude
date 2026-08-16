# The SDLC behind the pack

This is the methodology the skills encode. The [README](./README.md) tells you what each skill is and how to install them; this doc explains *why* they're shaped the way they are, so you can use them well — or steal the ideas and build your own.

## The core idea

Software fails at the seams between what someone meant, what got planned, and what got built. Most of that failure is invisible until the code exists, at which point it's the most expensive time to find it.

So the pack refuses to let intent jump straight to code. It forces a feature down a chain of small, written artifacts:

```
spec.md  →  brief.md  →  engineering-plan.md  →  implementation/<chunk>.md  →  code
```

Each artifact **descends** from the one above it — a brief realizes part of the spec, an engineering plan decomposes one brief, a chunk plan implements one node of that plan, code implements one chunk. Each is small enough to hold in your head and cheap enough to throw away.

And each one is **authored** by a skill, then **prosecuted** by a separate adversarial review skill before anything descends from it. Plans are cheap; wrong plans are expensive, so the scrutiny lives at every layer, not just at the code.

## Author, then prosecute

Every layer is a pair: an author skill and a review skill.

- The **author** (`/brief-author`, `/engineering-plan-author`, `/plan-author`, `/spec-author`) writes the artifact. It grounds every claim against the actual repo — a field, a caller, an endpoint that isn't in the code doesn't get to exist in the plan — and self-prosecutes before it emits, so what lands is already a clean draft, not a first draft.

- The **review** (`/brief-review-v2`, `/engineering-plan-review-v2`, `/plan-review-v2`, `/spec-review`, `/review-pr-v2`) convenes an adversarial tribunal of persona agents — correctness, security, architecture, testing, and more — that *attack* the artifact. Each files findings backed by evidence, the parent applies the fixes inline, and the skill returns a verdict.

The reviewer is adversarial on purpose. Its job is not to bless the author's work; it's to try to break it and report what survived. That only works if the reviewer isn't the author — which is where context hygiene comes in (below).

### Verdicts and convergence

Reviews don't pass or fail once. They **converge** across re-invocations:

- **APPROVED** — nothing left to attack; the artifact is ready for the next layer to descend from it.
- **CLOSED** — (engineering-plan layer) every open thread is resolved and the plan is sealed.
- **NEEDS USER INPUT** — the tribunal hit a question only you can answer. It stops and hands you labeled **blockers** rather than guessing.

You re-run a review until it stops finding things. A clean pass means a clean pass; two clean passes in a row means it's genuinely done. The verdict and round print at the very end of every review, in a byte-identical format across all of them, so you never scroll to find where you stand.

### Blockers become decisions, decisions become durable

When a review returns NEEDS USER INPUT, two skills turn its blockers into forward motion, and they run **in sequence — always explain first, then solve**:

- **`/explain-blockers`** goes first. It triages the open blockers into a short, ordered list of plain-language decisions — linked ones collapsed into a single call, ordered so the top decision unblocks the ones under it, each with a recommended pick. Now you can see the whole decision landscape before committing to anything.
- **`/solve-blockers`** goes second. It chases each of those blockers to a concrete, high-confidence recommendation with an evidence trail, then applies the fix on your say-so. It's the research pass, not a substitute for the triage — you run it after `/explain-blockers`, not instead of it.

Both write their resolution to the feature's `decisions.md` — the durable arbitration log. A decision made once stays made. Later layers (and later review rounds) read `decisions.md` and don't re-litigate a `bound` call. That's what stops the pipeline from churning on the same question every time context resets.

`/plan-alignment` is the same move applied *before* the engineering plan exists: it lays out two or three architecture directions for an approved brief, each with the tradeoff it commits you to, and records your pick as a bound decision — so the architecture is a choice you made, not a side effect of whichever way a skill happened to draft.

## The layers, top to bottom

| Artifact | Author | Reviewer | What it fixes in place |
|---|---|---|---|
| `spec.md` | `/spec-author` | `/spec-review` | the product source of truth — business rules, formulas, invariants |
| `brief.md` | `/brief-author` | `/brief-review-v2` | one feature's "what & why" — Goals, non-goals, signals |
| architecture | `/plan-alignment` | — | the direction, bound as a decision |
| `engineering-plan.md` | `/engineering-plan-author` | `/engineering-plan-review-v2` | the chunk DAG between brief and code |
| `implementation/<chunk>.md` | `/plan-author` | `/plan-review-v2` | one chunk = one PR |
| the code | `/execute-plan` | `/review-pr-v2` | the branch's PR |

A large feature can carry more than one engineering plan — call them **tracks**, under `plans/<track>/`. The tracks of one feature **co-deliver**: none ships alone, and merging one to `main` deploys nothing on its own, so the reviewers deliberately don't flag "orphaned" or "half-integrated" states between sibling tracks. They still check that the union of the tracks covers the brief, and that shared contracts between tracks stay consistent.

## The scope gate

An engineering plan can pass its own review — internally sound, well-factored, every chunk clean — and still quietly under-deliver the brief: narrowing a Goal to a subset, a weaker signal, or an action taken before its basis exists. `/engineering-plan-review-v2` prosecutes the plan on its own terms; it doesn't independently re-derive the brief's full intent.

So once the engineering plan returns **CLOSED**, always run **`/scope-check`**. It reads each brief Goal and asks whether the plan delivers it *in full*. Every narrowing it finds comes back as an explicit decision for you: accept the cut — recorded in `decisions.md` — or widen the plan to cover it.

Scope-check closes a loop rather than ending one. If resolving what it finds changes the brief or the engineering plan, the review that previously blessed that artifact no longer holds — so re-run it. A changed brief goes back through `/brief-review-v2`; a changed engineering plan goes back through `/engineering-plan-review-v2`. You drop down to chunk plans only when scope-check comes back clean *and* every artifact it forced a change to has been re-reviewed to a clean verdict.

## The deterministic floor

Before any LLM-judgment review runs, `/plan-lint` runs. It parses the markdown and applies mechanical checks — DAG cycles, "and"-chunks that smuggle two units into one, vague exit criteria, premature abstractions, position-encoded slugs (`01-`, `02-`), review-budget overflow, deferrals with no destination, invariants with no falsifier. No model judgment, milliseconds to run, same answer every time.

This is the floor the review skills *assume has already passed*. It catches the structural defects cheaply and deterministically so the expensive adversarial pass spends its attention on judgment, not on catching a cycle a parser could have found.

## Execution and shipping

Once a chunk plan is APPROVED, `/execute-plan` implements it:

- in an **isolated worktree**, one per chunk, so parallel chunks never collide;
- **test-first** — the test that proves the behavior comes before the code that satisfies it;
- **one chunk = one PR** — the unit of review stays small enough to actually review.

On a clean **COMPLETE** verdict, `/execute-plan` opens the chunk's PR into `main` for you. It does this *inline* — a direct commit / push / `gh pr create`, not by invoking `/open-pr` — so the self-scheduling guard never has to fire on the pack's own automation. If execution ends BLOCKED, it opens nothing and tells you why.

Then `/review-pr-v2` runs the adversarial tribunal on the actual PR — the same author-then-prosecute pattern, now against the diff and the passing gates. It applies fixes, re-runs the gates, commits, and posts the verdict to the PR. After merge, `/cleanup-worktree` tears the chunk's worktree down.

There's a matching automation at the plan layer: when `/plan-review-v2` returns APPROVED **twice in a row**, it opens the plan-doc PR inline, the same way and for the same reason.

## Context hygiene — the practice that makes the reviews honest

**Clear your context before every author and every review skill.**

This is not housekeeping. The whole pack rests on the reviewer being independent of the author. If you write a brief and then review it in the same context, the "reviewer" already believes the brief — it inherits the author's assumptions, remembers why each choice was made, and quietly declines to attack the things it just argued for. That's a rubber stamp with extra steps.

A fresh context per heavy skill restores the adversarial gap:

- the **author** starts clean, grounding against the repo rather than against a conversation that's been drifting for an hour;
- the **reviewer** meets the artifact cold, with no memory of the intent behind it, and prosecutes what's actually on the page.

So the rhythm is: clear, author, clear, review, clear, next author, and so on. The artifacts on disk (`brief.md`, `decisions.md`, the plan) are the only handoff between contexts — which is exactly why they have to be self-contained, and why the pack works so hard to keep them that way.

**Two exceptions — do *not* clear before these:**

- **`/explain-blockers`** and then **`/solve-blockers`** run *right after* a review that returned NEEDS USER INPUT, in that order and in the same context. They consume that review's verdict and blocker state *in context* to triage it and then research it. Clear first and you've thrown away the very thing they operate on.

The rule of thumb: clear before anything that **produces or prosecutes an artifact**; stay in context for anything that **acts on the review you just got**.

## Why this shape

- **Errors caught early are cheap.** A wrong assumption in a brief costs a sentence to fix. The same assumption discovered in a merged PR costs a revert, a re-plan, and everything built on top of it. The chain front-loads the scrutiny to where fixing is cheapest.
- **Small artifacts are reviewable.** A 2000-line PR gets a rubber stamp; a one-chunk PR gets read. Every layer is sized to actually fit in a reviewer's head — human or model.
- **Adversarial beats affirmative.** "Find what's wrong with this" surfaces defects that "does this look ok?" never will. Separating author from reviewer is what keeps that adversarial edge from dulling into agreement.
- **Decisions compound instead of repeating.** Writing every arbitration to `decisions.md` means the pipeline gets *more* settled as it runs, not less. Context resets don't reopen closed questions.
- **Determinism where determinism is free.** `plan-lint` proves that anything a parser can check, a parser *should* check — leaving the expensive judgment for the things that genuinely need judgment.

None of this is sacred. It's the shape that fell out of shipping real features and getting burned at each seam. Take the parts that map to how you work, and rewire the rest.
