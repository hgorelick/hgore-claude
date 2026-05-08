# Blocker classes — shared registry

Used by all three v2 review skills to label remaining unresolved findings. Hosting skill names which subset is active. The verdict gate logic at the bottom is also shared.

---

## Universal blocker classes

| Class | Meaning | Resolution |
|---|---|---|
| `STABLE_DISAGREEMENT` | Two personas filed contradictory fixes on the same span. | User picks one option; orchestrator applies. |
| `OPEN_QUESTION` | Persona filed a question rather than a fix; OR a fix would weaken tests/types/intent. | User answers / decides; orchestrator does not auto-fix. |
| `FIX_INTRODUCED_PREMISE_INVERSION` | Orchestrator's applied fix rewrote prose (comment, docstring, schema directive, plan body, brief, decisions log) that asserts a claim about behavior, but the claim does not survive verification against the actual repo. The fix itself introduced the lie. Working tree left dirty. | User inspects, corrects the prose to match reality OR amends the underlying code/structure to match the claim. |
| `POLISH_PLATEAU` | Tier-2 weight non-zero but ≤ floor (4). | **Non-blocking** — surfaced for visibility only; ship is acceptable. |
| `REPO_STATE_DRIFT` | `git rev-parse HEAD` changed mid-review. | User re-runs the skill from scratch. |

## PR-only

| Class | Meaning | Resolution |
|---|---|---|
| `BASELINE_RED` | Stage 1 detected pre-existing gate failures on branch HEAD before review. Stage 2/3 were skipped. | User fixes failing gates (or carves them out with stable rationale) and re-invokes. |
| `FIX_INTRODUCED_REGRESSION` | Applied fix broke a gate. Working tree left dirty for inspection. | User inspects, fixes, re-invokes. |

## Plan-only (chunk + engineering)

| Class | Meaning | Resolution |
|---|---|---|
| `STRUCTURAL_LINT_FAILED` | `/plan-lint` short-circuited the review at Stage 0. | User fixes structural defects per `/plan-lint` output and re-invokes. |

## Brief-only (`/brief-review-v2`)

| Class | Meaning | Resolution |
|---|---|---|
| `STRUCTURAL_SHAPE_FAILED` | `/brief-review-v2`'s Stage 0 Structural Shape Check short-circuited the review because required sections are missing, banned content patterns appeared, frontmatter is malformed, or implementation creep (path:line, schema columns, SQL fragments) leaked into brief prose. Briefs do not run through `/plan-lint`, so this is the brief-layer equivalent of `STRUCTURAL_LINT_FAILED`. | User fixes the structural defects (typically: add missing sections, strip addendum / review-attribution / historical-comparison content, hoist implementation creep into the engineering plan) and re-invokes. |

## Engineering-plan-only

| Class | Meaning | Resolution |
|---|---|---|
| `BRIEF_AMENDMENT_NEEDED` | Chunk has no brief Goal AND infrastructure-subsection escape doesn't apply AND brief refused to grow. | User amends brief or drops chunk. |
| `IMPLEMENTABILITY_GAP` | Decision-Closure Audit cross-chunk-wiring deferral OR Imagined-Implementer undecided decision / missing identifier. | User binds the decision in the engineering plan body. **Gates `CLOSED` only; does NOT gate `APPROVED`.** |
| `UNCORROBORATED_RESET` | Single-persona RESET reclassified to CRITICAL HARD per the corroboration rule. RESETs have two subclasses with different corroboration thresholds: `repo-state` (requires 2 personas on the same span); `brief-environment` (requires either 2 personas OR 1 persona + a verbatim contradicting citation from `CLAUDE.md` / project memory / source-of-truth). Subclass appears in the verdict label. | User reads the claim, decides whether to re-scope or dismiss. |

## Plan-author-only (chunk-plan authoring)

These classes are filed by `/plan-author` at write time as the prevention-side mirror of `/plan-review-v2`. The reviewer-side equivalents (where they exist) usually fire as `STRUCTURAL_LINT_FAILED` because `/plan-lint` is the reviewer's deterministic floor; the author classes are stricter and named distinctly so the user-facing decomposition recommendation is precise.

| Class | Meaning | Resolution |
|---|---|---|
| `CONCERN_GATE_FAILED` | Chunk plan's H1, Goal sentence, OR engineering-plan chunk-index description matched a multi-concern refusal pattern: self-disclosure (`\bN-concern\b`, `bundle`), conjunctive AND, three+ comma-separated independent noun phrases, plus-separated bundle, OR ≥2 independent clauses in the Goal sentence. The author skill refused to proceed past the Concern gate (`/plan-author`) or Concern-lint gate (`/engineering-plan-author`) and the cross-side warm-mode carry-forward consultation found no applicable arbitration in the engineering-plan reviewer state, the engineering-plan-author state, or the engineering plan's `## Decisions closure` section. | One of: (a) decompose the chunk into one-concern siblings via `/engineering-plan-author --rewrite <feature>`; (b) rewrite the engineering-plan chunk-index row description to single-concern phrasing citing a `decisions.md` arbitration entry; (c) add an explicit `## Decisions closure` row arbitrating the bundle (`bound` status, includes a concern-family keyword like `bundle` / `mutually load-bearing` / `transactional invariant`); then re-invoke the author skill. |
| `BUDGET_EXCEEDED` | Chunk plan exceeded the 500-line / 40k-token hard cap. Almost always signals overscoping that the Concern Gate didn't catch via headers (a single-concern chunk rarely needs more than 300 lines). | User decomposes the chunk via engineering-plan amendment, OR overrides with `--bypass-byte-budget` (logged in the sidecar as a deliberate exception; reviewer treats with extra scrutiny). |

---

## Verdict gates

### PR review (`/review-pr-v2`)

- **APPROVED** when ALL of:
  - Tier-1 weight = 0
  - Tier-2 weight ≤ 4
  - All gates GREEN after fixes
  - No `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `FIX_INTRODUCED_REGRESSION`, `FIX_INTRODUCED_PREMISE_INVERSION`, `BASELINE_RED`, `REPO_STATE_DRIFT`
- **NEEDS USER INPUT** otherwise.

### Chunk plan review (`/plan-review-v2`)

- **APPROVED** when ALL of:
  - Stage 0 Structural Lint Gate exited 0
  - Tier-1 weight = 0
  - Tier-2 weight ≤ 4
  - No `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `FIX_INTRODUCED_PREMISE_INVERSION`, `REPO_STATE_DRIFT`
- **NEEDS USER INPUT** otherwise.

### Brief review (`/brief-review-v2`)

- **APPROVED** when ALL of:
  - Stage 0 Structural Shape Check exited clean (no `STRUCTURAL_SHAPE_FAILED`)
  - Tier-1 weight = 0
  - Tier-2 weight ≤ 4
  - No `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `FIX_INTRODUCED_PREMISE_INVERSION`, `REPO_STATE_DRIFT`
- **NEEDS USER INPUT** otherwise.

### Engineering plan review (`/engineering-plan-review-v2`)

Three-state verdict. Pick exactly one.

- **CLOSED** — plan is shape-correct AND every cross-chunk decision is bound. Per-chunk plan writing is unblocked. Required:
  - Tier-1 weight = 0
  - Tier-2 weight ≤ 4
  - No `BRIEF_AMENDMENT_NEEDED`, `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `IMPLEMENTABILITY_GAP`, `UNCORROBORATED_RESET`, `REPO_STATE_DRIFT`
  - `imagined_implementer_report.verdict == implementable`

- **APPROVED** — plan is shape-correct BUT cross-chunk decisions remain undecided. Per-chunk plan writing is **NOT** yet unblocked. Required:
  - Tier-1 weight = 0
  - Tier-2 weight ≤ 4
  - No `BRIEF_AMENDMENT_NEEDED`, `STABLE_DISAGREEMENT`, `OPEN_QUESTION`, `UNCORROBORATED_RESET`, `REPO_STATE_DRIFT`
  - One or more `IMPLEMENTABILITY_GAP` findings remain
  - `imagined_implementer_report.verdict == not_implementable`

- **NEEDS USER INPUT** — anything else (Tier-1 weight > 0, OR a non-`IMPLEMENTABILITY_GAP` blocker is present, OR a corroborated RESET fired).

The semantic difference: APPROVED says "the *shape* is right; remaining work is decision-making, not structure-fixing." CLOSED says "you can write the next per-chunk plan and have it cohere with the others."
