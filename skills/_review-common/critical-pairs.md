# Critical-pair policies — pre-resolved rule conflicts

These resolve known oscillation hazards. Persona agents apply silently. Findings that contradict an active policy are retracted by the orchestrator, not relitigated. The hosting skill names which subset is active for the review (PR / chunk plan / engineering plan).

---

## Universal (apply to all review types)

**P-CLASS-SCOPE — Class > line vs scope minimization.** Fix every instance in the *enumerated universe* the persona declared. Do not expand scope to "every defect that looks similar" beyond that universe. A finding that proposes a fix outside the declared universe is invalid; widen the universe at finding time or split into multiple findings. There are no Round-2 widens — the universe must be right the first time.

**P-FULL-FILE — Read full file vs line-level evidence.** Read the full file for context, but findings must cite specific lines. No "this whole file is bad" findings without line-level evidence.

---

## PR review (`/review-pr-v2`)

**P-PR-OWNERSHIP — Pre-existing not exempt vs out of scope.** Defects in files the PR touches are fair game (the PR owns the file). Defects in files the PR does NOT touch are out of scope unless they're in the *blast radius* of a touched identifier (e.g., a function the diff introduces is called from an untouched file that needs updating). Pre-existing defects in completely untouched files are not the PR's burden — note as `OPEN_QUESTION` if relevant.

**P-PR-COVERAGE — Tests pass vs coverage absent.** "Tests pass so it's fine" is invalid. "Tests don't cover this behavior change" is valid. Green gates do NOT exonerate the PR from a missing-test finding.

**P-PR-CLAIMS — Author description vs actual diff.** PR description claims X but diff does Y → valid `SCOPE` finding. Description silent about Y but Y is in diff and Y is benign → no finding.

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
