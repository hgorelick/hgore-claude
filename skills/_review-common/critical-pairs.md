# Critical-pair policies — pre-resolved rule conflicts

These resolve known oscillation hazards. Persona agents apply silently. Findings that contradict an active policy are retracted by the orchestrator, not relitigated. The hosting skill names which subset is active for the review (PR / chunk plan / engineering plan / brief / spec / vision).

**Not every active pair is defined here.** The brief-layer pairs (`P-BRIEF-*`), spec-layer pairs (`P-SPEC-*`), and vision-layer pairs (`P-VISION-*`) are defined in `/brief-review-v2`, `/spec-review`, and `/vision-review` respectively, and reach the persona through the `{active_critical_pair_subset}` slot in its prompt — which is authoritative. Apply the pairs named in your prompt whether or not they appear in this file.

---

## Universal (apply to all review types)

**P-CLASS-SCOPE — Class > line vs scope minimization.** Fix every instance in the *enumerated universe* — where the universe is the seed finding plus every sibling the same-round **class sweep** (`~/.claude/skills/_review-common/class-sweep.md`) surfaces for that class. Getting the universe right rests on the sweep, not on the persona guessing every location: the dedicated sweep stage walks the peer-set exhaustively before fixes are applied, so widening happens *within the round*, deterministically, rather than by a persona over-reaching. The guardrail runs the other direction too — a sweep widens only to genuine siblings of the *same* invariant property, each carrying its own verbatim evidence; it does NOT expand to "every defect that looks similar," and a candidate instance without its own evidence is not an instance. A different defect class the sweep notices in passing is a new persona finding, not a sibling. Round-2 widens do not exist: the sweep is what makes the universe right the first time.

**P-FULL-FILE — Read full file vs line-level evidence.** Read the full file for context, but findings must cite specific lines. No "this whole file is bad" findings without line-level evidence.

---

## PR review (`/review-pr-v2`)

**P-PR-OWNERSHIP — Pre-existing not exempt vs out of scope.** Defects in files the PR touches are fair game (the PR owns the file). Defects in files the PR does NOT touch are out of scope unless they're in the *blast radius* of a touched identifier (e.g., a function the diff introduces is called from an untouched file that needs updating). Pre-existing defects in completely untouched files are not the PR's burden — note as `OPEN_QUESTION` if relevant.

**P-PR-COVERAGE — Tests pass vs coverage absent.** "Tests pass so it's fine" is invalid. "Tests don't cover this behavior change" is valid. Green gates do NOT exonerate the PR from a missing-test finding.

**P-PR-CLAIMS — Author description vs actual diff.** PR description claims X but diff does Y → valid `SCOPE` finding. Description silent about Y but Y is in diff and Y is benign → no finding.

**P-PR-BRIEF-PARITY — Delivered-code parity vs bound-decision acquittal.** On a feature-scoped PR, a Stage 1.5 `SURFACE_PARITY_GAP` / `BRIEF_NONGOAL_TRESPASS` / `BRIEF_GOAL_UNDELIVERED` is **Class A** (per `principles.md` § Cross-artifact authority order) — it is NOT retracted by a `Status: bound` `decisions.md` entry. A persona must not acquit a delivered-code parity gap by citing a bound decision, and the orchestrator's Priority-1 carry-forward must not drop it: only a brief amendment, or an **Active** bound entry that *explicitly scoped the residual as launch-acceptable*, clears a parity finding. Read the diff for the Goal's *intended outcome*, not the PR description's mechanism wording — code that performs the Goal's named mechanism on one surface does not satisfy a Goal whose outcome must hold across the domain. Conversely, a parity finding whose "gap" is a domain member a *different* chunk owns (per the EP Brief-mapping) is invalid — scope the finding to the slice this PR's chunk claims.

---

## Chunk plan review (`/plan-review-v2`)

**P-CHUNK-TEST-PATHS — Enumerate test cases vs don't pre-commit to test paths.** Test cases in the plan are described by *behavior + assertion shape*. Actual test file paths come from the test layout the audit recorded — never invented in the plan body. A finding requesting a specific test path is invalid; a finding requesting more behavior/assertion specificity is valid.

**P-CHUNK-COMMANDS — Concrete commands vs flexibility.** Verification commands come from `package.json` / `Cargo.toml` / `Makefile` that the audit confirmed exist. A finding requesting a command that doesn't exist is invalid; the fix is to use the existing command.

**P-CHUNK-SINGLE-CONCERN — Single concern vs scope completeness.** A chunk does ONE thing. "You should also do X" is valid only if X is *required* for the chunk's stated concern. Otherwise the right move is a separate chunk in the engineering plan, not bolting X on.

**P-CHUNK-READ-FIRST — Read first vs full-file ownership.** "Read first" names files the implementer must understand to complete the chunk. It does NOT enumerate every tangentially-touched file. A finding requesting an exhaustive read-list is invalid; a finding requesting a missing critical file is valid.

---

## Engineering plan review (`/engineering-plan-review-v2`)

**P-EP-IMPL-DETAIL — Implementation-detail vs vague noun.** Concrete identifiers ARE permitted when they name *cross-chunk contracts*: interface names, table names, flag names, enum values, file paths of shared modules. Concrete identifiers are NOT permitted for *chunk-internal* targets: test names, single-file function names, internal phase splits, files-to-create lists, exact log strings, SQL queries, regex patterns. A finding demanding more detail on a chunk-internal target is invalid; a finding flagging chunk-internal detail leaking into the engineering plan is valid.

**P-EP-BRIEF-GOALS — Brief Trace vs do-not-invent-Goals.** Chunks delivering cross-cutting infrastructure (rate limiters, error helpers, shared clients, observability) map to a single `### Supporting infrastructure` subsection of Brief Mapping. They do not require a dedicated brief Goal. A finding insisting an infrastructure chunk needs a brief Goal is invalid; one insisting a *user-facing* chunk needs a brief Goal is valid.

**P-EP-VERIFIED-BY — Verified-by entries.** A user-facing change's `Verified by` cell names a chunk slug whose plan owns the test, OR `"Manual review"`. It never names a test file or test case directly. A finding requesting more specificity on `Verified by` is invalid.

**P-EP-RISK-DEPTH — Risk depth.** The Risks section names risks, mitigations, and rollback path. It does not enumerate every possible failure mode. A finding requesting "more risks" without naming a specific unaddressed failure mode is invalid.

**P-EP-DECISION-LOC — Decision locus.** Cross-chunk-wiring decisions belong in the engineering plan. Chunk-internal decisions belong in the chunk plan. Brief-layer decisions (residual gaps, scope tradeoffs, non-goals) belong in `brief.md`. The Decision-Closure Audit classifies; personas apply the classification.

**P-EP-SIBLING-CODELIVERY — Co-delivered tracks vs independent shipping.** A feature's engineering plans are tracks of one feature, delivered together and deployed as a whole; nothing goes live on a merge (`principles.md` § Sibling-plan co-delivery). A finding that treats a track as independently shippable is invalid: a track delivering no brief Goal on its own, a chunk/export/column/seam consumed only by a sibling track, and cross-track consumption or wiring left to the sibling's own implementation are the feature's structure — not orphan, integration, go-live, or undelivered-Goal defects — and need no separate task, issue, DAG node, flag, or gate. A finding is valid when it names a brief Goal **no** sibling track delivers, a clause **every** sibling disclaims, or a cross-track **contract** (a shared type / constant / predicate) whose export and import have drifted.
