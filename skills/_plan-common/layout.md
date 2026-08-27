# Feature layout and artifact resolution

Normative for every skill that resolves a feature name to an engineering plan, a chunk plan,
or a state-file slug: `/brief-author`, `/brief-review-v2`, `/engineering-plan-author`,
`/engineering-plan-review-v2`, `/plan-author`, `/plan-review-v2`, `/execute-plan`,
`/explain-blockers`, `/solve-blockers`, `/review-pr-v2`, `/scope-check`, `/features-init`.

One feature has exactly one brief. It may have **more than one engineering plan**. A feature
whose delivery splits across independently-sequenced tracks (a backend contract track and a
group-behavior track, say) gets one engineering plan per track, all tracing to the same brief.

## The two layouts

**Flat** — one engineering plan. The default; most features stay here forever.

```
features/<feature>/
  brief.md
  decisions.md
  engineering-plan.md
  implementation/<NN>-<chunk-slug>.md
```

**Tracked** — two or more engineering plans under one brief.

```
features/<feature>/
  brief.md
  decisions.md
  plans/
    <track>/
      engineering-plan.md
      implementation/<NN>-<chunk-slug>.md
    <other-track>/
      engineering-plan.md
      implementation/<NN>-<chunk-slug>.md
```

## Feature-level vs plan-level

| Artifact | Scope | Location in both layouts |
|---|---|---|
| `brief.md` | **Feature** — one per feature, never per track | `features/<feature>/brief.md` |
| `decisions.md` | **Feature** — one arbitration record shared by every track | `features/<feature>/decisions.md` |
| `engineering-plan.md` | **Plan** — one per track | the plan root |
| `implementation/` | **Plan** — chunks belong to the track that sequences them | the plan root |

`decisions.md` stays feature-level under the tracked layout **by design**. Tracks that split
delivery still share invariants, constants, and contract types; a per-track decisions log
would recreate exactly the cross-track drift the log exists to prevent. A decision that binds
only one track is still recorded once, in the shared log, and names the track it binds.

## Tracks are co-delivered, not independently shipped

The tracks **decompose one feature for implementation; they are not independent releases.** The
feature is delivered by implementing **all** of its plans and reaches users only through a
deliberate whole-feature deploy — nothing goes live on a merge to `main`. So a track may deliver
**no brief Goal on its own** (it ships shared infrastructure its siblings consume), and a chunk
whose only consumer is a sibling track is **not** orphaned — the consumer lives in a plan not
under review. Cross-track consumption is inherent in the siblings being built, verified in each
sibling's own review/execute cycle; it is never a separate task, issue, DAG node, flag, or gate,
and its absence is correct by design. Authors and reviewers must not raise orphan, integration,
go-live, or undelivered-Goal concerns **between** sibling tracks — see
`~/.claude/skills/_review-common/principles.md` § Sibling-plan co-delivery. Coverage still binds:
delivered scope is the union of the tracks, and a Goal **no** track delivers is a real gap.

## Resolution (deterministic — no LLM judgment)

Given `<feature>`, compute its **plan roots**:

1. If `features/<feature>/engineering-plan.md` exists → flat layout; the single plan root is
   `features/<feature>/`, and the track is `null`.
2. Else glob `features/<feature>/plans/*/engineering-plan.md` → tracked layout; one plan root
   per match, track = the directory name under `plans/`.
3. Neither → the feature has no engineering plan yet. Brief-layer skills proceed; every
   engineering-plan-layer and chunk-layer skill stops and reports.

**Both 1 and 2 matching is malformed.** Stop and report — do not guess which is canonical.
A half-finished migration reads as "flat" under rule 1 and silently ignores every track.

A **plan root** is the directory holding `engineering-plan.md` and `implementation/`. Every
path a skill builds below the engineering-plan layer is relative to the plan root, never to
`features/<feature>/`. Every path to `brief.md` or `decisions.md` is relative to the feature
root. In the flat layout the two coincide, which is why the distinction was invisible until
the first feature grew a second track.

### When a track is needed but not supplied

An engineering-plan-layer or chunk-layer skill invoked with a bare `<feature>` that resolves
to **two or more** plan roots stops and lists the tracks with each plan's `Status:` field, and
asks which. It does not pick the first, the newest, or the largest. Chunk-layer skills may
skip the question when the chunk slug itself disambiguates — see chunk references below.

## Reference syntax

| Form | Means | Example |
|---|---|---|
| `<feature>` | flat layout, or "ask which track" | `user-profile-sync` |
| `<feature>/<track>` | one specific engineering plan | `team-chat/chat-core` |
| `<feature>/<chunk-slug>` | a chunk in a flat-layout feature | `team-chat/retry-limit-unify` |
| `<feature>/<track>/<chunk-slug>` | a chunk in a tracked feature | `team-chat/chat-core/chat-vocabulary` |
| `<chunk-slug>` | bare shorthand; glob to disambiguate | `chat-vocabulary` |

**Two-token ambiguity.** `<feature>/<x>` is a track reference if
`features/<feature>/plans/<x>/engineering-plan.md` exists, and a chunk reference otherwise.
Check the track form first; it is the cheaper and more specific test.

**Argument parsers that classify a `/`-containing token as a filesystem path must test these
forms first.** A path token is one that ends in `.md`, starts with `./` or `/`, or starts with
a known root directory (`.scratch/`, `fixes/`, `context/`, `features/`). `team-chat/chat-core`
is none of those.

**Bare chunk-slug shorthand** globs both layouts:
`features/*/implementation/{<slug>,[0-9]*-<slug>}.md` and
`features/*/plans/*/implementation/{<slug>,[0-9]*-<slug>}.md`. Exactly one combined match →
use it. Ambiguous → list the matches with their feature and track, and ask.

## State-slug derivation

One rule covers every layer and both layouts:

> **The slug is the artifact's path relative to `features/`, with the `plans/` and
> `implementation/` path segments dropped, `/` replaced by `__`, and the `.md` suffix removed.**

| Artifact path | Slug |
|---|---|
| `features/<f>/brief.md` | `<f>__brief` |
| `features/<f>/engineering-plan.md` | `<f>__engineering-plan` |
| `features/<f>/implementation/<NN>-<c>.md` | `<f>__<c>` |
| `features/<f>/plans/<t>/engineering-plan.md` | `<f>__<t>__engineering-plan` |
| `features/<f>/plans/<t>/implementation/<NN>-<c>.md` | `<f>__<t>__<c>` |

The `<NN>-` creation-index prefix is a filesystem-ordering affordance, not identity: strip it
before forming the slug. The same slug names the file in **both** cache directories —
`~/.claude/cache/author-state/<slug>.json` and `~/.claude/cache/review-state/<slug>.json` — so
an author skill and its sister reviewer address the same artifact by the same name. That
symmetry is what makes warm carry-forward work in both directions.

### Migration note — the engineering-plan review slug

`/engineering-plan-review-v2` historically wrote its state to
`~/.claude/cache/review-state/<feature>.json` — a bare feature slug, with no layer suffix.
Every author skill that consults engineering-plan review state
(`/brief-author`, `/engineering-plan-author`, `/plan-author`) reads
`<feature>__engineering-plan.json`, so the warm carry-forward silently read a file that never
existed. The rule above is now canonical: the reviewer writes `<feature>__engineering-plan`
(flat) or `<feature>__<track>__engineering-plan` (tracked).

When loading engineering-plan review state, read the canonical slug first; if absent, fall
back to the legacy bare `<feature>.json`, and on the next persist write the canonical name
and delete the legacy file. Log the migration in the verdict's state-source line.

## Closed engineering plans

`/ep-close` marks a plan implementation complete: a `<!-- Status: closed — implementation
complete YYYY-MM-DD -->` frontmatter marker in `engineering-plan.md` (plus a visible
`**Status:** Closed …` header line), a bound closure entry in the feature's `decisions.md`,
and `ep_closed: true` in the plan's state sidecars. The frontmatter marker is canonical;
`/ep-close` is its only writer.

A closed plan is a **sealed contract**:

- **No new chunk rows, ever.** Later scope — including scope that naturally belongs to the
  closed plan's concern — routes to an open sibling track, a new track (§ Adding a track),
  or a new feature. Any skill or agent about to propose "add a chunk to `<plan>`" must check
  the marker first; when closed, proposing the addition is a defect — propose the routing
  alternative instead, naming where the scope goes.
- **Not re-authored, re-reviewed, or amended.** `/engineering-plan-author`,
  `/engineering-plan-review-v2`, and `/plan-author` (for new chunks under it) refuse a
  closed target and point here. Reopening is a director-only act: the user removes the
  marker and supersedes the closure entry in `decisions.md`.
- **Still read normally.** A closed plan remains the authoritative contract for what it
  shipped — sibling plans, reviewers, and implementers consult it as reference exactly as
  before. Track listings show it as `closed`.

## Adding a track to an existing feature

Moving a flat feature to the tracked layout is a **director-level decision**, not something a
skill does on its own initiative. `git mv` `engineering-plan.md` and `implementation/` into
`plans/<track>/`, leave `brief.md` and `decisions.md` at the feature root, and rename the
affected state files per the slug rule (or delete them to review cold). Relative links inside
the moved files gain one `../` level — the chunk-plan header's links to `../brief.md` and
`../engineering-plan.md` become `../../../brief.md` and `../engineering-plan.md`.

The brief does **not** split. Splitting delivery is a sequencing decision; splitting scope is
a product decision. Conflating them re-litigates settled scope every time a plan gets large.
