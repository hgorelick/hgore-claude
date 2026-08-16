---
name: implementation-verify
description: The feature factory's verifying station — independently re-proves a finished chunk against its own plan from a clean state, so it reaches a PR on an external verdict rather than the implementer's self-attestation. Re-runs the gates itself, observes every acceptance criterion, checks contract and diff scope, returns VERIFIED or VERIFY_FAILED. Invoked headlessly by the factory orchestrator; not a step in the interactive `/execute-plan` → `/open-pr` pipeline.
user-invocable: true
---

# /implementation-verify — Independent chunk verification

The VERIFYING station of the feature factory. It sits on the `IMPLEMENTED → PR_OPEN` edge: a chunk that `/execute-plan` reports `COMPLETE` does **not** open a PR on that self-report — this skill re-proves the finished implementation against its own chunk plan, from a clean state, and emits a machine-readable verdict the coordinator branches on. Only a `VERIFIED` verdict admits a chunk to `PR_OPEN`; a `VERIFY_FAILED` routes back to `IMPLEMENTING` for a bounded retry.

The premise is distrust of the implementer's certification. `/execute-plan` runs its own gates and marks itself `COMPLETE`; the run-record-contract dogfood showed a chunk can pass its gates and still ship tests that don't actually catch a broken implementation. This skill re-runs the gates itself (never trusting the report), checks the artifact literally against the plan's acceptance criteria and Factoring Contract, and — best-effort — injects faults to confirm the tests are load-bearing. It is the independent evaluator `/execute-plan` is deliberately **not**.

This is a hand-authored skill on the throwaway POC substrate's factory, sister to `/execute-plan` (the implementer it re-proves) and `/solve-blockers-headless` (the other headless, sidecar-emitting, factory-invoked station). It is invoked by the merged `runVerify` seam (`poc/src/skillStation.ts`) as `claude -p "/implementation-verify <feature>__<chunk>"`, and is also runnable manually and by the `poc/proof/prove-verify.ts` proof harness.

**Model policy.** Per `~/.claude/skills/_review-common/principles.md` § Station model policy, this is a `sonnet`-tier station: the four gating checks are mechanical (re-run gates, observe criteria literally, diff the file set) and mutation sampling never gates the verdict. The factory's `runVerify` invocation should pass `--model sonnet` on the `claude -p` call. `/solve-blockers-headless` — the factory's *judgment* station — is the deliberate exception and stays on the session/opus tier.

## Shared scaffolding (read on demand)

- `~/.claude/skills/_review-common/principles.md` — REPO REALITY IS LAW; banned rationalizations. The same stance applies at verify time: a claim is verified by running it, not by trusting the plan or the implementer.
- The chunk's `features/<feature>/decisions.md` — bound arbitration. Only Active-section `Status: bound` entries are authoritative — a `superseded`/`obsolete` entry in the `## Archived` tail does not bind (per `~/.claude/skills/_review-common/principles.md` § What counts as a bound entry). "Verify depth" (the four gating checks; mutation advisory) and "Verify-loop thrash is coarse/best-effort" (the failed-check set is the coarse 4-member id set, by design) live here for the verify-station feature; a customer feature's own decisions.md is its authority.
- The project's `CLAUDE.md` — gate commands, package-management rules, zero-tolerance discipline.
- `poc/src/verdict.ts` / `poc/src/sidecar.ts` — the sidecar contract this skill writes to (the enums, the `VERIFIED ⟺ failed_checks empty` invariant enforced at parse). Read them if unsure of an exact string; **never invent a check-id or mutation value.**

## The contract this skill writes (do not drift from it)

The one file this skill owns is `~/.claude/cache/verify-state/<feature>__<chunk>.json`, **snake_case**, parsed by `parseVerifySidecar`:

```json
{
  "verdict": "VERIFIED" | "VERIFY_FAILED",
  "failed_checks": ["gate_rerun" | "acceptance_criteria" | "contract_conformance" | "diff_scope", ...],
  "mutation": "catch" | "inconclusive" | "skipped"
}
```

- `verdict` and `failed_checks` are locked to each other: **`VERIFIED` requires `failed_checks` empty; `VERIFY_FAILED` requires it non-empty.** The parser THROWS on a mismatch, which the factory reads as a station error — so a violated invariant is worse than a wrong-but-consistent verdict. Get the pairing right.
- `failed_checks` members must be exact — only the four ids above; order preserved is fine, duplicates are tolerated by the parser but avoid them.
- `mutation` must be exactly one of `catch` / `inconclusive` / `skipped`. It is **validated but never gates** — the verdict is a function of `failed_checks` alone.
- Extra keys are allowed (the parser ignores unknown fields). This skill writes diagnostic fields (`slug`, `verified_at`, `plan_path`, `head_sha`, `base_ref`, `checks`, `mutation_detail`) for the operator and the proof harness; they never affect the machine verdict.
- The key is the **exact composite slug handed to the skill** (see Target resolution). A bare or wrong key makes the seam's `assertSidecarFresh` throw on a fresh path or read a foreign verdict.
- **Rewrite the sidecar on every run** (overwrite via `Write`). A `VERIFY_FAILED → IMPLEMENTING → VERIFYING` retry, and the manual gate's two-round re-verification, both reach this same path; the seam requires the mtime to advance each round, so always write, even when the verdict is unchanged.

## Inputs

`$ARGUMENTS`:

- `<feature>__<chunk>` — the composite slug (REQUIRED, positional). Exactly the shape `compositeChunkSlug(feature, chunkSlug)` builds (`${feature}__${chunkSlug}`), matching `/plan-author`'s and `/plan-review-v2`'s sidecar key. This is what the seam passes.
- `--base <ref>` — OPTIONAL. The base ref the built diff is computed against. Defaults to `git merge-base HEAD <default-branch>` (`main`, falling back to `master`). The seam never passes it (its prompt is fixed `/implementation-verify <slug>`); it exists for manual runs and multi-chunk integration branches where the fork point isn't `main`.

The skill runs in the **cwd it is spawned in** — the lane's repo / worktree, which holds both the chunk plan (`features/…`) and the built code. `cwd` is load-bearing: the plan and the diff are resolved relative to it. A wrong cwd verifies the wrong artifact.

## Workflow

```
Target resolution                     (deterministic, hard short-circuit)
  ↓ resolve the chunk PLAN from the slug (glob + planSlug inverse); ambiguous/absent → REFUSE (no sidecar)
  ↓ resolve the BUILT DIFF (git changed-file set vs base); not a git repo → REFUSE (no sidecar)
Four gating checks, IN ORDER, COLLECT ALL failures   (deterministic; each appends its id on failure)
  ↓ gate_rerun          re-run the project's test/typecheck/lint gates myself
  ↓ acceptance_criteria each plan Acceptance-criteria item literally observed
  ↓ contract_conformance no Forbidden touched, no Reads written, declared signatures present
  ↓ diff_scope          no unplanned files (test-for-Owns + this feature's docs count as in-scope)
Mutation sampling                     (advisory, best-effort, NEVER gates → catch | inconclusive | skipped)
  ↓ inject ≤3 faults from the plan's behaviors into Owns source; confirm tests catch; restore exact bytes
Write the verify-state sidecar        (ALWAYS; freshness-guarded; VERIFIED ⟺ failed_checks empty)
  ↓
Render the verdict prose              (audit trail; must AGREE with the sidecar — the factory parses the sidecar, not the prose)
```

There is no inner loop and no human in this thread. The factory drives the retry loop (`VERIFY_FAILED → IMPLEMENTING → VERIFYING`) and the escalation; this skill produces exactly one sidecar per invocation. Never emit an `AskUserQuestion`, a confirmation prompt, or an apply gate — there is no operator watching a `claude -p` thread.

---

## Target resolution (MANDATORY, DETERMINISTIC, HARD SHORT-CIRCUIT)

### Resolve the chunk plan

The slug is a composite `<feature>__<chunk>`, but `__` is ambiguous (a feature or chunk could in principle contain it — see the composite-slug-collision follow-up). So resolve by **inverting `/plan-author`'s slug rule over the real files**, not by splitting the string:

1. Glob `features/*/implementation/*.md` **and** `features/*/plans/*/implementation/*.md` under cwd — a feature is either flat or tracked (delivery split across tracks), per `~/.claude/skills/_plan-common/layout.md`.
2. For each file, derive its slug the way `planSlug` does: take the path relative to `features/`, drop the `plans/` and `implementation/` path segments, drop the `.md` suffix and any leading `NN-` creation-index prefix (`/^\d+-/`) from the filename, and join what remains with `__`. Flat → `<feature>__<chunk>`; tracked → `<feature>__<track>__<chunk>`.
3. Match against the input slug.

- **Exactly one match** → that is the plan path. Proceed.
- **Zero matches** → **REFUSE** (write no sidecar): `REFUSED: no chunk plan resolves to slug <slug> under features/*/implementation/ or features/*/plans/*/implementation/` . An unresolvable target is an orchestration error, not a chunk verdict — the factory escalates.
- **Multiple matches** → **REFUSE**: `REFUSED: slug <slug> is ambiguous (matched <paths>)`. Never guess.

`Read` the resolved plan in full. Extract: the `Acceptance criteria` list, the `Factoring Contract` (`Owns (writes)`, `Reads (no writes)`, `Forbidden`), the `Contracts / types changed` section (declared exported symbols), and the `Tests to add` / behavior descriptions (for mutation synthesis).

**Status frontmatter guard:** if the plan's frontmatter has `Status: needs-user-input`, REFUSE — a chunk whose plan is mid-cycle authoring state was never validly implemented. `REFUSED: plan is in mid-cycle authoring state (Status: needs-user-input)`.

### Resolve the built diff

The chunk's built diff is the changed-file set this verification checks against the Factoring Contract and diff-scope. Compute it with git (cwd is the lane's worktree):

1. Confirm cwd is a git repo (`git rev-parse --is-inside-work-tree`). Not a repo → **REFUSE**: `REFUSED: cwd is not a git work tree (<cwd>)`.
2. Record `head_sha = git rev-parse HEAD`.
3. Determine `base_ref`: the `--base` arg if given, else `git merge-base HEAD main` (fall back to `master` if `main` is absent). If no base can be computed, REFUSE (`REFUSED: cannot compute a diff base (no --base and no main/master)`).
4. The **changed set** = the union of:
   - committed since base: `git diff --name-only <base>...HEAD`
   - tracked working-tree edits: `git diff --name-only HEAD`
   - new untracked files: `git ls-files --others --exclude-standard`
   minus recognized non-chunk scaffolding: paths under `personas/`, `.scratch/`, `.worktrees/`, and the cache itself. (Scaffolding is review/process detritus that lands on a branch and is not part of the implementation.)

The changed set is what `contract_conformance` and `diff_scope` reason over. It's a snapshot of what the implementer produced for this chunk, independent of the implementer's word for it.

**Clean state.** "From a clean state" means the gates are **re-executed** in this tree, not that a fresh clone is made — the seam hands us the built tree and we distrust the self-report by running the gates ourselves, not by re-provisioning. Do not reuse any cached green from `/execute-plan`.

---

## The four gating checks

Run all four **in order**, and **collect every failing check-id** into `failed_checks` (do not short-circuit on the first failure — `failed_checks` is a set, and a fuller set is a better retry and thrash-fingerprint signal). The verdict is `VERIFIED` iff `failed_checks` ends empty, else `VERIFY_FAILED`.

### Check `gate_rerun`

Re-execute the project's acceptance gates yourself — the "don't trust the self-report" re-run.

- Derive the gate commands from: the plan's `Acceptance criteria` (which name specific commands, e.g. `cd poc && npm test`, `npm run typecheck`), supplemented by the project's `package.json` scripts (`test`, `typecheck`, `lint`) for the sub-project(s) the `Owns` paths live under (scope like `/execute-plan`: all-`poc/` → run `poc`'s gates; mixed → run each affected sub-project's).
- Run each. **All must exit 0.** Any non-zero exit → append `gate_rerun` to `failed_checks`.
- Capture each command's exit status and a one-line failure summary into the sidecar's `checks` diagnostic field.

### Check `acceptance_criteria`

Walk the plan's `Acceptance criteria` list. Each item names an observable condition — a command to run, a grep to satisfy, a `git diff --name-only` assertion, a file-existence check, or a behavior.

- For each item: identify the verification mechanism, run/observe it, compare to what the plan says "passing" looks like.
- A command already run under `gate_rerun` (identical invocation) may reuse that result rather than re-running — note the reuse.
- Any item not observably satisfied → append `acceptance_criteria` to `failed_checks` (once; the id is coarse). Record the per-item PASS/FAIL table in the `checks` diagnostic field.

### Check `contract_conformance`

Enforce the Factoring Contract against the changed set and the built code:

- **No Forbidden file touched:** the changed set ∩ `Forbidden` must be empty. Any overlap → fail.
- **No Reads file written:** the changed set ∩ `Reads (no writes)` must be empty. Any overlap → fail.
- **Declared signatures present:** for each exported symbol named in `Contracts / types changed`, grep its `Owns` file and confirm a declaration exists with the stated shape (name + kind: function / type / const / field). A named-but-absent symbol → fail. (This is a presence-and-shape check, not a full type-check — the type-checker already ran under `gate_rerun`.)
- Any of the above → append `contract_conformance` to `failed_checks`, with the specific violations in the `checks` diagnostic field.

### Check `diff_scope`

No unplanned files. Compute the **expected set** and flag anything in the changed set outside it.

- **Expected set** = `Owns (writes)` ∪ (test files corresponding to `Owns` modules, per the project's test layout — e.g. `poc/test/<mod>.test.ts` or a sibling `<mod>.test.ts` for an owned `poc/src/<mod>.ts`) ∪ this feature's own planning docs (`features/<feature>/**`, including the chunk's own plan file, engineering-plan, brief, decisions).
- Rationale (operator-bound this session): a chunk's test file is squarely in-scope even when the plan's `Owns` list omits it, and the feature's planning docs ride on the branch by construction — failing verification on either punishes the implementation for a plan-completeness gap. Genuinely unplanned files (stray artifacts, edits to unrelated modules, another feature's docs) are what this check exists to catch.
- `changed set − expected set` non-empty → append `diff_scope` to `failed_checks`; list the unexpected files in the `checks` diagnostic field. (A Forbidden file in the changed set trips both this and `contract_conformance` — that's fine; the coarse set carries both.)

---

## Mutation sampling (advisory; NEVER gates)

Best-effort fault injection to test whether the chunk's tests are load-bearing — the signal the run-record-contract dogfood needed a hand-run to get. **It strengthens the verdict but never gates it** (brief Non-goal "Mutation sampling never gates the verdict"): its outcome lands only in the `mutation` field, never in `failed_checks` or `verdict`.

**Skip conditions (→ `mutation: "skipped"`):**
- `gate_rerun` failed (tests are already RED — a fault can't be distinguished from the pre-existing failure).
- No meaningful fault can be synthesized from the plan's behaviors (a pure re-export, a schema/type-only contract, an I/O-wiring chunk with no branching logic).
- The working tree can't be safely mutated-and-restored (see restore discipline) — err to `skipped` rather than risk corruption.

**Procedure (only if not skipped):**
1. From the plan's stated behaviors / `Tests to add`, pick ≤3 targeted faults in **`Owns` source files** (never a test file, never a `Reads`/`Forbidden` file): invert a guard or boolean, change a return value, drop a branch, break a mapping — a fault a correct test should catch.
2. For each fault, in turn:
   - `Read` the file and **keep its exact original bytes**.
   - `Edit` in the single fault.
   - Run ONLY the test(s) covering that module (not the full suite). Expect **RED = the fault was caught**.
   - **Restore the exact original bytes** (`Write` the captured content back). Then verify restoration: `git diff -- <file>` must match the file's pre-mutation state (for a clean-committed file, `git diff --quiet -- <file>` passes). If restoration can't be confirmed, attempt `git checkout -- <file>` (tracked + committed only); if the tree still isn't restored, **abort mutation sampling, record `inconclusive`, and warn loudly** — the gating verdict already stands on the deterministic checks; never leave a corrupted tree.

**Outcome mapping:**
- **`catch`** — at least one fault was applied and every applied fault was caught (test went RED, then restored clean).
- **`inconclusive`** — a fault was applied but **escaped** (tests stayed GREEN with the fault in place — the vacuous-test signal), OR the result was ambiguous, OR restoration was uncertain. The contract has no "escaped" member and cannot gate, so this is the honest bucket. **An escape is the single most valuable thing this skill can find** — surface it prominently in the verdict prose and in `mutation_detail`, even though (by bound design) it does not block the PR.
- **`skipped`** — per the skip conditions above.

Record which files were mutated, which faults, and each fault's catch/escape into the `mutation_detail` diagnostic field.

---

## Write the verify-state sidecar (MANDATORY, ALWAYS, LAST GATED STEP)

After the four checks and mutation sampling, write the sidecar — the authoritative outcome.

- **Path:** `~/.claude/cache/verify-state/<feature>__<chunk>.json`, where `<feature>__<chunk>` is the **exact input slug**. Create the `verify-state/` directory if it doesn't exist (`mkdir -p`).
- **Verdict:** `VERIFIED` iff `failed_checks` is empty, else `VERIFY_FAILED`. Re-check the invariant before writing — `failed_checks` empty and verdict `VERIFY_FAILED`, or non-empty and `VERIFIED`, will make the factory's parser throw. They must agree.
- **Write it always**, overwriting any prior round's file, so the mtime advances and the seam's freshness guard reads this round fresh (the `VERIFY_FAILED` retry and the two-round manual-gate case both depend on this).
- **Shape** (contract fields + diagnostics):

```json
{
  "verdict": "VERIFY_FAILED",
  "failed_checks": ["gate_rerun", "diff_scope"],
  "mutation": "inconclusive",
  "slug": "<feature>__<chunk>",
  "plan_path": "<plan-root>/implementation/<NN>-<chunk>.md",
  "head_sha": "<sha>",
  "base_ref": "<sha or ref>",
  "verified_at": "<ISO 8601 UTC>",
  "checks": {
    "gate_rerun": { "pass": false, "detail": "npm test: 2 failing" },
    "acceptance_criteria": { "pass": true, "detail": "6/6 observed" },
    "contract_conformance": { "pass": true, "detail": "no Forbidden/Reads touched; signatures present" },
    "diff_scope": { "pass": false, "detail": "unexpected: poc/src/coordinator.ts" }
  },
  "mutation_detail": "1 fault injected in runRecord.ts; ESCAPED (tests stayed green) — tests may be vacuous"
}
```

The `checks` / `mutation_detail` fields are for the human reading an escalation and for the proof harness; the factory parses only `verdict` / `failed_checks` / `mutation`.

## Render the verdict prose

After the sidecar is written, emit the audit-trail verdict. It must **agree with the sidecar** (the factory never parses it, but a human debugging an escalation reads it):

```
## Implementation Verify: <feature>__<chunk>

**Plan:** <plan_path>
**Built diff base:** <base_ref>   **HEAD:** <head_sha>
**Changed files (chunk):** <N> — <list, minus scaffolding>

### Gating checks
| Check | Result | Detail |
|---|---|---|
| gate_rerun          | PASS/FAIL | <one line> |
| acceptance_criteria | PASS/FAIL | <one line> |
| contract_conformance| PASS/FAIL | <one line> |
| diff_scope          | PASS/FAIL | <one line> |

### Mutation sampling (advisory — does NOT gate)
<catch | inconclusive | skipped> — <detail; if a fault ESCAPED, say so loudly>

### Verdict: VERIFIED / VERIFY_FAILED
failed_checks: [<ids or "none">]
Sidecar: ~/.claude/cache/verify-state/<slug>.json
```

For a refusal, emit only the single `REFUSED: <reason>` line and write **no** sidecar.

---

## Hard rules

- **Distrust the self-report.** `gate_rerun` re-executes the gates itself; a `/execute-plan` `COMPLETE` is never evidence. The whole station exists because the implementer is not trusted to certify its own work.
- **Deterministic checks gate; mutation is advisory.** `verdict` and `failed_checks` are a function of the four checks alone. Mutation sampling lands only in `mutation`; it never sets `VERIFY_FAILED`, never adds to `failed_checks` — not even a clear escape. (Bound: decisions.md "Verify depth"; brief Non-goal.)
- **The `VERIFIED ⟺ failed_checks empty` invariant is absolute.** Re-check before writing; a violated invariant makes the factory parser throw (a station error), which is worse than a consistent wrong verdict.
- **Always write the sidecar on a real verdict; overwrite every run; key on the exact composite slug.** A missing sidecar, a stale (un-refreshed) sidecar, or a wrong key all break the seam's freshness guard. A refusal is the ONE case that writes no sidecar — and it's deliberate (the factory escalates on the resulting freshness throw).
- **Refuse, never guess, on an unresolvable target.** Zero/multiple plan matches, a non-git cwd, an uncomputable base, or a mid-cycle plan → one `REFUSED:` line, no sidecar. Do not fall back to a partial verdict.
- **Restore the tree after mutation.** Capture exact bytes, restore exact bytes, verify restoration; on any doubt, abort mutation to `inconclusive` and never leave the worktree corrupted. Mutation is best-effort — its safety outranks its signal.
- **No human in the thread.** Never `AskUserQuestion`, never a confirmation prompt, never wait for input. One run → one sidecar (or one refusal).
- **Read-only except the sidecar and transient mutations.** The skill does not edit the plan, the code (beyond inject-then-restore during mutation), decisions.md, or any other cache state file. The verify-state sidecar is the only durable write it owns.
- **Prefer Read / Edit / Write over Bash for file I/O** (global CLAUDE.md); Bash is for git / npm / grep only.

## Failure modes to avoid

- **Trusting a plan claim instead of running it.** REPO REALITY IS LAW — a criterion is satisfied by observing it, not by the plan asserting it.
- **Inventing a check-id or mutation value.** Only `gate_rerun` / `acceptance_criteria` / `contract_conformance` / `diff_scope` and `catch` / `inconclusive` / `skipped`. Anything else makes the parser throw. When unsure, re-read `poc/src/verdict.ts`.
- **Letting mutation gate.** A vacuous-test escape is a WARNING, not a `VERIFY_FAILED`. Recording it as a failed check reverses a bound decision.
- **Writing `VERIFIED` with a non-empty `failed_checks` (or vice-versa).** The most common way to break the parser. The verdict is derived from the set — derive it, don't set it independently.
- **Keying the sidecar on a bare `<chunk>` instead of `<feature>__<chunk>`.** Self-consistently fresh at the WRONG key: no freshness throw fires, but the verdict persists feature-uncorrelatable and collides across features sharing a chunk slug. Always use the exact slug handed in.
- **Not overwriting on a retry round.** A `VERIFY_FAILED → IMPLEMENTING → VERIFYING` re-entry that reads the prior round's stale `VERIFIED` would admit an unverified chunk to a PR. Always rewrite.
- **Leaving the tree dirty after mutation.** A half-applied fault corrupts the very artifact under verification. Restore-and-verify, or abort to `inconclusive`.
- **False-failing on in-scope files.** A test file for an owned module and this feature's planning docs are expected (operator-bound); flagging them is a false `diff_scope` failure that blocks a correctly-built chunk.

## Edge cases

- **Multi-chunk integration branch** (the branch carries prior merged chunks' files, not just this chunk's): pass `--base <integration-branch>` so the diff is this chunk's alone. With the `main` default, prior chunks' files would read as unexpected `diff_scope` violations. The seam's main-line path is a per-chunk lane branch off `main`, where the default is correct.
- **Live lane before `/open-pr` commits** (changed files are uncommitted in the working tree): the changed set includes tracked working-tree edits and untracked new source files, so an uncommitted implementation still verifies. Mutation sampling on a dirty tree is riskier to restore — prefer `git`-clean-file faults, else skip.
- **No test command in the project** (rare for a factory customer): `gate_rerun` can only run what exists; if the plan's acceptance criteria name no runnable gate and the project defines none, record `gate_rerun` as inconclusive-but-passing in the diagnostic and lean on `acceptance_criteria` — but a chunk with no executable gate at all is a plan defect worth surfacing in the prose.
- **Plan `Owns` lists the test file explicitly** (some plans do): then it's in `Owns` and the expected-set union is a no-op for it — no special handling needed; the leniency only matters when `Owns` omits it.
- **Second round (manual gate / retry):** the skill re-runs end to end and rewrites the sidecar; the freshness guard reads the new mtime. Nothing special is required beyond always-overwrite. `prove-verify.ts --rounds 2` exercises exactly this.
