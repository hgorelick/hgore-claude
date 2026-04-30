---
name: review-pr
description: Convene an adversarial tribunal on the current branch's PR. Ruthlessly prosecute every defect, cite evidence, fix them all, loop until clean. Use after opening a PR.
user-invocable: true
---

# Review PR — Adversarial Tribunal

This is not a collaborative review. It is a **tribunal**: the PR stands accused and must be proven correct under hostile scrutiny. Your job is to prosecute — find every defect, cite evidence, convict, then fix. Silence is not exoneration; it is suspicion. Approvals come only when a ruthless pass finds **zero** issues.

## Prosecutorial stance

**REPO REALITY IS LAW.** Every finding, every fix, every fact the tribunal asserts MUST be grounded in files that exist *right now, on this branch*. A tribunal that prosecutes fictional targets — invented test files, phantom CI jobs, hallucinated servers, fabricated line numbers — is worse than no tribunal: it manufactures confidence while the real defects walk free. **If you cannot produce a file path + line range + byte-for-byte quote, the finding does not exist.** If you cannot produce a `grep` hit or a `gh pr diff` slice, the target does not exist. Treat your own prior-round conclusions with the same suspicion — they may have been hallucinated too.

**Assume guilty until proven innocent — but prove the defendant is real first.** Every line of the diff is a hypothesis that must survive attack. If you can't explain why something is correct by reading the actual source files, it is suspect. If you can't *find* the source file you're arguing about, stop and fix your map of the repo before continuing.

**Cite or drop it.** Every finding states `path:line` (from the diff or source) and — where applicable — quotes the authority it violates (spec file, persona rule, project invariant, existing test). The cite must be a verbatim quote, not a summary. Vibes-based findings are inadmissible; so are vibes-based acquittals. "I think there's a test file that…" is inadmissible until you `ls` it.

**The diff is not the universe.** Read the files the diff touches *in full*. Read files the diff *calls into*. Read files the diff *claims to uphold*. Hallucinated fields, phantom APIs, and drift-from-pattern hide in the parts not shown in the hunk.

**Banned rationalizations.** Any round that ends with one of these is automatically not-clean:
- "minor", "nit only", "not worth fixing", "good enough", "acceptable residual"
- "it was already broken", "pre-existing", "not introduced by this PR"
- "out of scope" (for defects *in the diff*)
- "we can fix it later", "tracked elsewhere", "follow-up"
- "the tests pass so it's fine" (tests can be wrong; coverage can be absent)
- "the lines in the finding are fixed" (without proving every other instance of the same class is resolved)
- "I searched for the literal pattern" (without generalizing to case variants, plurals, alternate forms, derived names)

Either fix it in this PR or escalate to the user with a concrete question. There is no third door.

**Fix the root cause.** When you find a bug, ask what class of bug it is and whether siblings exist in the same PR. One broken callsite almost always has cousins.

**Class > line.** A finding names a *line*; a defect lives in a *class*. Fixing only the named lines and calling clean is how multi-round loops are born — the next round widens the search slightly and surfaces siblings the prior round didn't think to look for. Before declaring any finding fixed, identify the underlying class and prove every other instance of it is either resolved or carved out with a stable rationale.

**The procedure is single-pass. Multi-round loops are a procedural failure, not an inherent property of prosecution.** A round that ends with "I caught the literal text but might have missed siblings; the next round will widen" is not a clean round — it is a deferred-correctness round dressed up as progress. Execute the procedure below in full *before* declaring any class closed.

The work is in five steps, executed in one pass per class:

1. **Generalize the finding into a class.** What pattern is this an example of? A retired identifier? A stale file reference? A copy-pasted assertion? An obsolete invariant? Two prose sentences naming the same canonical set with disagreeing members? The class is what siblings share, not what the diff happens to expose. **Name the class precisely** — "the chunk-1 sub-commit set is named in multiple sentences with disagreeing membership" is precise; "stale plan references" is not. A vague class name produces a vague search.
2. **Enumerate the universe the class can hit.** Before grepping for instances, list every place the class *could* live. For canonical-set classes in prose: every section that names sets, every count claim, every scope statement, every per-element table, every cross-reference. For retired-identifier classes: every file under the protected tree + every doc surface. For copy-paste assertion classes: every callsite of the helper. **Write the universe down explicitly** so a future reviewer can verify you didn't narrow it. If you can't articulate the universe, the class definition (step 1) is too vague — go back.
3. **Search the entire universe in one pass.** Generalize the search pattern beyond the literal text: case variants, plurals, alternate forms, related identifiers, derived names, neighbouring directories, prose paraphrases. Don't grep for the prior round's exact phrasing — grep for the class's invariant property. Run the searches *before* picking up any tool to fix anything.
4. **Resolve every hit in one commit (or one stable rationale per hit).** Either fix it in this round, or pair it with a stable rationale that survives hostile re-prosecution (a documented carve-out, a guard test that requires the literal text, a cross-reference to where the design vocabulary belongs, a corpus artifact that must remain verbatim). "I'll catch it next round" is not resolution; it is the failure mode. **Fixing in passes ("first the easy ones, then the hard ones next round") re-creates the multi-round loop** — that's the same anti-pattern under a different name.
5. **Re-enumerate from scratch — do not just re-grep the literal patterns from step 3.** Re-run step 1 on the post-fix state as if you'd never seen the class before. Walk the prose / code top-to-bottom and ask: is there *any* canonical set / retired identifier / copy-pasted assertion that I haven't accounted for? If a new instance surfaces, the original step-1 class definition was too narrow — extend the class, fold the new instance into the same round's fix, and re-run step 5. The class is closed only when step 5 produces zero new instances *and* the carve-out audit table covers every step-3 hit with a stable rationale.

**The acceptance test for "class closed."** Before posting a verdict, write down the class name (step 1), the universe (step 2), and the carve-out audit table (step 4). A future reviewer with no context, running the same searches, must land on the same rationales — and a step-5 re-enumeration must produce zero new instances. If you cannot produce all three artifacts, the class is not closed.

If the class can't be enumerated and resolved in one pass, the scope of the round is wrong — escalate or split, don't paper over. **Splitting** means: tell the user "this PR contains two independent classes that need to be prosecuted separately"; do not silently scope the round to one class and CLEAN-verdict on the other.

## Workflow

### Find the PR

```bash
gh pr view --json number,title,url,headRefName,baseRefName
```

If no PR exists for the current branch, tell the user to run `/open-pr` first and stop.

### Prior-round intake — MANDATORY, BLOCKING

**Run this once at the start of every `/review-pr` invocation, before any other step.** A fresh invocation may be landing on a PR that prior tribunal rounds have already prosecuted. Skipping this step means you will re-raise resolved findings, re-prosecute retracted ones, miss decayed carve-outs, and number the round wrong.

Pull every tribunal artifact on the PR — both reviews (the round indictments are posted via `gh pr review --comment`) and issue-style comments (verdicts may land either way). Read each in full.

```bash
# Reviews (round indictments are posted via `gh pr review --comment`)
gh pr view --json reviews \
  --jq '.reviews[] | select(.body | startswith("## Tribunal")) | {author: .author.login, submittedAt, state, body}'

# Issue comments on the PR (verdicts sometimes land here instead)
gh pr view --json comments \
  --jq '.comments[] | select(.body | startswith("## Tribunal")) | {author: .author.login, createdAt, body}'

# Commits since the PR opened (so you can map claimed fixes to actual commits)
git log --oneline "$(gh pr view --json baseRefName --jq .baseRefName)..HEAD"
```

From the harvested artifacts, derive:

- **Round number for this invocation.** N+1 where N is the highest `## Tribunal — Round N` seen. If none, you are Round 1.
- **Open findings.** Anything raised in a prior round that has not been resolved by a subsequent commit. Carry these forward into this round's indictment — but re-verify each against the *current* files; do not paste prior-round text as if proven.
- **Claimed fixes.** Findings a prior round declared resolved. Read the current source and the commit(s) that claim the fix; confirm the fix actually landed *and* extended to the whole class (per "Class > line"). A claimed fix that didn't generalize is a re-opened finding, not a closed one.
- **Retractions.** Findings a prior round explicitly retracted (the target was fictional, the rationale was wrong). Do not re-raise them as if novel; if you believe a retraction was itself wrong, say so explicitly with new evidence.
- **Carve-out tables.** Generalized-search hits a prior verdict rationalized as keep-as-is (see **Execute the fixes**). Re-run the same generalized search now. If new hits appear that the prior table did not enumerate, the carve-out has decayed and the class re-opens this round.
- **Stale "CLEAN" verdicts.** If the PR carries a prior `Verdict: CLEAN` and the user is invoking `/review-pr` again, treat it with maximum suspicion. Either new commits arrived after the verdict (re-prosecute the new commits *and* re-verify the prior verdict's claims still hold) or the verdict was wrong (re-prosecute everything). Determine which from `git log` against the verdict's timestamp.

Prior-round conclusions are **hypotheses, not evidence**. The **Repo Reality Audit** and the banned-rationalizations list still apply — a previous round can be hallucinated too. Re-verify before propagating.

Record the intake in a block you will paste into this round's PR comment:

```
### Prior-round intake (entering Round N+1)
- Prior rounds: <list of round numbers + submitted_at; or "none — Round 1">
- Prior verdict: <CLEAN / not yet / N/A> (timestamp)
- Commits since last round: <sha range, count>
- Open findings carried forward (to re-verify this round): <count, classed by category>
- Claimed-fix verifications scheduled: <count>
- Carve-out searches to re-run: <count>
- Retractions noted (will not re-raise): <count>
```

If no tribunal artifacts exist, state explicitly: `Prior-round intake: none — Round 1` and proceed.

### Gather evidence

Read everything. Parallelize.

```bash
gh pr diff                                   # full unified diff
gh pr view --json files --jq '.files[].path' # changed paths (authoritative list)
gh pr view --json title,body                 # author's claims (to be tested)
git log --oneline $(gh pr view --json baseRefName --jq .baseRefName)..HEAD
git ls-files                                 # authoritative list of files on the branch
```

Then, before forming any opinion:
- **Read every changed file in full** (not just the hunks).
- **Read the source-of-truth files the project declares** (e.g., `CLAUDE.md`, `SPEC.md`, schema files, format guides, persona files).
- **Read callers and callees** of anything modified whose behavior could shift.

Missing context is a defect in *your* review. Do not proceed until you have it.

### Repo Reality Audit — MANDATORY, BLOCKING

**You do not get to skip this. Every round.** The purpose is to stop the tribunal from prosecuting files, tests, CI jobs, modules, or APIs that do not exist. Round-1 hallucinations poison every subsequent round's findings.

Before any persona runs, answer these on paper *from tool output*, not from memory:

1. **What is the actual repo layout?** List top-level dirs (`ls`) and the authoritative file list (`git ls-files | head -n 200` and total count). If the project claims a package/workspace structure, confirm it (`cat package.json` / `cat Cargo.toml` / `cat pyproject.toml`, list workspace members).
2. **What test infrastructure actually exists?** Find the real test files: `git ls-files | grep -E '(test|spec|__tests__|\.test\.|\.spec\.|tests/)'`. Don't assume `__tests__/`, `tests/`, `spec/`, or any convention — *look*.
3. **What CI actually runs?** `ls .github/workflows/ 2>/dev/null`, `cat .github/workflows/*.yml 2>/dev/null`, `ls .gitlab-ci.yml circle.yml .circleci 2>/dev/null`. Name the jobs that actually exist. If the PR claims it adds/changes a CI job, verify the file and the job name byte-for-byte.
4. **What entry points actually exist?** For each binary/service/module the PR references, confirm the file: `server.ts`, `main.rs`, `app.py`, etc. — **grep or ls, do not assume**.
5. **What commands actually work here?** Run the build and test commands *once* up front. Record their exact names and exit codes. Don't invoke commands that the project doesn't define.
6. **For each identifier the PR introduces or touches** (functions, types, fields, flags, CLI args, env vars, route paths, queue names, table/column names): grep for it in the current branch. Record: does it exist? how many hits? is the diff the only writer, or do other places reference it?

Record the audit as a short block you will paste into the round's PR comment:

```
### Repo Reality Audit (Round N)
- Tree: <top-level dirs>
- Test layout: <real test dirs/files>
- CI: <real workflow files and job names, or "none">
- Entry points referenced by PR: <path — exists/missing>
- Commands confirmed: <build cmd> OK/FAIL, <test cmd> OK/FAIL
- Identifiers verified: <list with grep hit counts>
```

**If the audit contradicts any assumption you were about to make, drop the assumption.** If it contradicts a finding from a previous round, *retract* the previous finding explicitly in this round's comment. Prior-round conclusions are not evidence — they are hypotheses until re-verified.

**Anti-hallucination rule:** when you catch yourself about to write a path, a test file name, a CI job name, or an API name from memory, STOP and grep for it. If it's not there, either the target is fictional (drop it) or your spelling is wrong (fix it from tool output, not guesswork).

### Empanel the tribunal

Convene multiple hostile experts and make each prosecute the diff from their angle. Use `personas/` files when present (e.g., `personas/code-reviewer.md`, `personas/architecture.md`, `personas/security.md`, `personas/testing.md`, and any project-specific ones like `personas/slice-and-dice-design.md`). If personas don't exist in the project, synthesize the equivalent roles yourself.

**Minimum panel** (every PR, every round):

1. **Correctness prosecutor** — Does it compile? Do tests pass? Are types honest? Is the happy path actually implemented, or just scaffolded?
2. **Hallucination prosecutor** — Every identifier (function, field, flag, path, CLI arg) referenced in the diff: does it exist *right now* in this repo, at the version the branch builds against? Grep for each. Invented APIs are CRITICAL.
3. **Invariant prosecutor** — Read the project's stated invariants (CLAUDE.md, SPEC.md, persona rules, test properties). For each invariant, try to construct a diff-introduced scenario that violates it. Roundtrip, idempotence, determinism, schema stability, etc.
4. **Security prosecutor** — Auth/authz bypass, injection surfaces, secret handling, unsafe blocks, deserialization, path traversal, privilege escalation. Even in "internal" tools.
5. **Drift prosecutor** — Does changed code follow existing patterns in the same directory? New abstractions where an existing one would serve? Parallel types alongside old ones (forbidden by "no deferred correctness")? Dead code left in "just in case"?
6. **Test prosecutor** — For every behavior change: is there a test that would have caught the *old* behavior failing? Were assertions weakened to make tests pass? Is a failing-and-fixed test actually testing the fix, or masking it? Are edge cases and error paths covered, or only the golden path?
7. **Scope prosecutor** — Does the diff do what the PR description claims, no more, no less? Unrequested refactors, sneaky behavior changes in unrelated files, speculative features, premature abstractions — all defects.
8. **Factoring prosecutor** — Is the change well-factored on its own merits, independent of whether it meets the spec? A change that satisfies the requirement but reads poorly is still a defect; the next reader pays the cost. Attack for:
    - **Self-pointers / circular references.** A comment in file `X` pointing at file `X` or the directory containing it. A doc that redirects the reader to the module they are already inside. A "see also" that loops.
    - **Orphaned clauses.** When an edit drops a reference but leaves a dependent clause that no longer has an anchor — `in the original plan`, `as mentioned above` with nothing above, `per the spec` after the spec cite was deleted, hand-waves like `originally` / `previously` whose subject was just removed.
    - **Prose duplicating an implementation enumeration.** When the canonical set lives in code (an enum, a config, a verification grep, a registry) and prose re-lists its members, the prose silently rots when the impl changes. Name the rule once, reference the impl as the authority — never re-enumerate.
    - **Rhythm breaks.** A one-liner that grows into a multi-sentence paragraph inside a list of one-liners. A terse style that suddenly turns verbose for one item. Stylistic drift inside a single section.
    - **Helper-shaped repetition.** N callsites with the same N-line incantation that should be one helper, or one correct line. Pasting the same pattern across many sites is asking the reader to encode a mistake N times.
    - **Half-finished refactors.** Old name + new name coexisting; behavior generalized in some callsites but not others; a parallel "alongside existing" representation when the right move is replacement (per "no deferred correctness").
    - **Comments that paraphrase the identifier.** A comment that just restates the function/variable name as English without explaining WHY. Well-named code is its own documentation; a comment that adds no information is noise.
    - **Vestigial vocabulary.** Terms / names / examples left over from a prior design vocabulary the current design no longer uses (e.g. a comment referencing `original X` after X was renamed/replaced).
   When a finding's fix is itself poorly factored, the Factoring prosecutor's re-attack on the post-fix state is what catches it — see step 4 of "Execute the fixes."

Run tool commands relevant to the project to validate:
- Compilation: `cargo check --all-targets`, `npx tsc --noEmit`, or equivalent.
- Tests: `cargo test`, `npm test`, or equivalent — all of them, not a subset.
- Project-specific correctness: e.g., for this repo, `cargo run --example roundtrip_diag` and verify all four `working-mods/*.txt` still roundtrip.
- Lints/formatters if the project gates on them.

Any red output is BLOCKING. "It was red before" does not exonerate the PR unless `git stash && <cmd>` on `main` reproduces the same failure byte-for-byte.

### File the indictment (PR review comment)

Post ONE comment per round with every finding. Every finding is structured, and **every field is mandatory**:

```
- **[path:line]** `CATEGORY` — What is wrong (one sentence)
  - Exists: <verbatim tool output proving the target exists — `ls path`, `git ls-files | grep path`, or a grep hit with line number. If you cannot produce this, DELETE THE FINDING.>
  - Evidence: <verbatim quote from the real file, with path:line, OR verbatim command output. Paraphrases are inadmissible.>
  - Impact: <concrete failure mode — not "could be bad", but "when X happens, Y breaks">
  - Fix: <specific change, not "add error handling">
```

A finding without an `Exists:` line that you personally produced from a tool call this round is a hallucination. Delete it. Do not ship it in the comment.

Categories: `CORRECTNESS`, `HALLUCINATION`, `INVARIANT`, `SECURITY`, `DRIFT`, `TEST`, `SCOPE`, `FACTORING`, `TYPE`, `PERF`.

Severity is a side-note, not a filter. Everything gets fixed. If you're tempted to mark something "LOW and skip," reread the banned-rationalizations list.

```bash
gh pr review --comment --body "$(cat <<'EOF'
## Tribunal — Round N

**Panel run:** correctness, hallucination, invariant, security, drift, test, scope
**Gates:** <compile command> = PASS/FAIL, <test command> = PASS/FAIL, <project-specific> = PASS/FAIL

### Findings

- **[path:line]** `CATEGORY` — …
  - Evidence: …
  - Impact: …
  - Fix: …

(If zero findings after genuinely hostile review: state that explicitly and list the gates that passed.)
EOF
)"
```

If a round produces no findings, *explain what you attacked* — which invariants you tried to break, which identifiers you grepped, which callers you read. "Looks good" is not a clean round.

### Execute the fixes

For every finding:

**Execute steps 1–5 from the "Class > line" procedure (Prosecutorial stance) for every finding in this round.** That procedure is the fix protocol — not a separate planning exercise. The summary below is operational; the authoritative wording lives at "Class > line" above.

1. **Identify the class** the finding belongs to. Name it precisely (the class's invariant property, not the literal text of the example).
2. **Enumerate the universe** the class can hit. Write it down explicitly so the carve-out audit table later can verify completeness. Examples: for canonical-set-in-prose classes, list every section that names sets, every count claim, every scope statement, every per-element table, every cross-reference. For retired-identifier classes, list every file under the protected tree + every doc surface. For copy-paste assertion classes, list every callsite of the helper.
3. **Search the entire universe in one pass.** Generalize the search pattern beyond the literal text — case variants, plurals, alternate forms, related identifiers, derived names, prose paraphrases. Don't restrict to files the diff touched; siblings hide in untouched files within the diff's blast radius. Don't grep for the prior round's exact phrasing — grep for the class's invariant property.
4. **Resolve every hit in *this* commit.** Each hit becomes either a fix or a documented carve-out with a stable rationale. Stable means: a future reviewer running the same generalized search lands on the same rationale and accepts without re-litigation. **Splitting the fix across passes ("first the easy ones, then the hard ones next round") re-creates the multi-round loop** — that is the failure mode this skill exists to prevent. If genuinely too many hits to fix in one commit, the *commits* can split (one logical chunk each) but the *round* must close every hit before a verdict; do not push partial fixes and CLEAN-verdict. **Re-attack each fix with the Factoring prosecutor *before* declaring the hit resolved.** A fix that drops a stale reference but leaves the orphaned clause behind, redirects a self-pointer to the directory the file lives in, or pastes the dropped citation's enumeration into prose nearby is itself a factoring defect — it satisfies the original finding while introducing a new one. Read the post-fix lines as if seeing them for the first time and ask: would I write this from scratch? If not, fix the fix in the same commit.
5. Re-run the full gate suite (compile + tests + project-specific).
6. **Re-enumerate from scratch — do not just re-grep step 3's literal patterns.** Walk the diff / prose / code top-to-bottom on the post-fix state as if you'd never seen the class before, and ask: is there *any* instance of the class I haven't accounted for? If a new instance surfaces, the original step-1 class definition was too narrow — extend the class, fold the new instance into the same round's fix (return to step 4), and re-run step 6. The class is closed only when step 6 produces zero new instances *and* step 4's resolutions all hold.
7. **Publish a carve-out audit table** in the verdict comment: the class name (step 1), the universe (step 2), every remaining hit with a stable rationale (step 4). The table is the artifact that lets the next round's reviewer re-run the same searches and verify each rationale is still load-bearing — no tail of "if I widen the search one more time, more siblings appear."
8. Add or strengthen a test that pins the fix. If the fix is "delete dead code," add a comment in the PR review explaining why no test was added.
9. Never weaken an assertion, loosen a type, widen a `catch`, or add an `expect(...)` to silence a failure. If a test is wrong, *fix the test's intent*, don't neuter it.

**The acceptance test for "ready to verdict":** before drafting the CLEAN comment, write down the class name, universe, and carve-out audit table for *every* finding raised this round. If you cannot produce all three artifacts for any finding, the round is not done — return to step 6.

Commit fixes in logical, reviewable chunks — not one megacommit:

```bash
git commit -m "fix: <one-line root-cause description>

<why this was wrong; evidence from the tribunal round>"
```

Push once all fixes for the round are committed and gates are green locally.

### Loop

Return to **Gather evidence** (not to *Find the PR* or *Prior-round intake* — those run once at invocation start). Re-read the *updated* diff from scratch. Do not trust that a previous round's fix is still correct — the next round's findings might invalidate it.

**The loop is an outer verification, not a sibling-search continuation.** If round N+1 surfaces a sibling that round N's fix should have caught, that is a *procedural failure* of round N's class enumeration (step 6 of "Execute the fixes"), not a normal property of prosecution. The proper response is to retroactively expand round N's class, fix the sibling, and document in round N+1's comment that round N's enumeration was incomplete — not to treat the sibling as "newly discovered" and accept that the loop will catch siblings round-by-round. Reactive grep widening across rounds is the failure mode the skill exists to prevent.

**The clean two-round pattern.** When the procedure is executed correctly, prosecution converges in **two rounds**:
- **Round 1**: enumerate every class, enumerate the universe per class, search exhaustively, fix every hit, push.
- **Round 2**: re-prosecute the post-fix state from scratch (re-execute "Class > line" steps 1–6 as if seeing the PR for the first time). If zero new instances surface across any class, post CLEAN.

If round 2 surfaces *any* finding, the round-1 enumeration was incomplete — fix in round 2, then a third round verifies. Three rounds is acceptable when round 2's finding is genuinely new (e.g. a fresh commit landed; a class neither the user nor the prosecution had seen before surfaces). Three rounds is **not** acceptable when round 2's finding is a sibling round 1 should have enumerated; in that case, retroactively own the round-1 procedural failure in round 2's comment.

**Termination:** a round produces **zero** findings across all prosecutors AND all gates are green AND the carve-out audit table covers every named class with stable rationales AND a step-6 re-enumeration of each class produces zero new instances. Not "zero blocking." Zero, audited, re-enumerated.

**Budget:** 5 rounds is a *ceiling*, not a target. The procedural goal is two rounds (one find-and-fix + one verify). If round 3 surfaces anything other than a fresh commit's content, the round-1 enumeration was the failure — own it explicitly. If round 5 still finds defects, stop and escalate — dump the remaining findings to the user with a recommendation (usually: the PR's scope is wrong and should be split, *or* the prosecution's class enumeration discipline broke down and the user should clear context and re-prosecute with stricter step-1/step-2 discipline). Do not silently accept residuals to end the loop, and do not treat budget consumption as inherent — it is a signal of procedural drift.

### Verdict

Post a final PR comment:

```
## Tribunal — Verdict: CLEAN

- Rounds: N
- Findings (total, by category): …
- Gates (final run): compile=PASS, tests=PASS, project-specific=PASS
- Files touched by fixes: …

No residual issues at any severity.
```

Then report the same to the user with the PR URL.

## Hard rules

- **Never** assert a file, test, CI job, function, or API exists without producing tool output *this round* that proves it. No exceptions. Not even "I just looked at it." Look again.
- **Never** approve a finding you don't understand. Escalate.
- **Never** weaken tests, types, or assertions to make gates green.
- **Never** skip gates "because the diff is small."
- **Never** skip the Repo Reality Audit, even on round 2+. Especially on round 2+ — that's when hallucinations compound.
- **Never** claim a round is clean without naming what you attacked *and* which audit checks passed this round.
- **Never** carry a finding forward from a previous round without re-verifying its target still exists and still exhibits the defect.
- **Never** accept "pre-existing" as a defense for a defect visible in the diff's blast radius — if the PR touches the file, the PR owns the file.
- **Always** read the full file, not just the hunk.
- **Always** grep every new identifier the diff introduces *and* every identifier it references, to verify both existence and uniqueness.
- **Always** prefer fixing in this PR over filing a follow-up. Follow-ups are where defects go to die.
- **Always** retract previous-round findings explicitly if the current-round audit shows they were based on fictional targets. Say so in the comment. Don't quietly drop them.
- **Always** generalize a finding into a class before declaring it fixed; search the whole repo with a generalized pattern (not the literal text) and resolve every instance in one round. Reactive grep-widening across rounds produces multi-round loops.
- **Always** publish a carve-out audit table in the verdict comment that pairs every remaining hit of the generalized search with a stable rationale. Without it, "verdict CLEAN" is reactive — the next round's reviewer can widen the search and surface siblings the verdict never accounted for.
- **Always** enumerate the universe before searching it (step 2 of "Class > line"). A class search that doesn't first declare its universe is a search that quietly narrows itself to whatever the prior round's text mentioned. The universe must be written down — explicitly — in the round's comment, so a future reviewer can verify it was complete.
- **Always** re-enumerate from scratch (step 6 of "Class > line") before declaring a class closed. Re-grepping the literal patterns from the original search proves only that those patterns are gone — it does not prove the class is closed. A fresh top-to-bottom walk of the relevant prose / code, asking *"is there any instance of the class I haven't accounted for?"*, is the only acceptable closure check. If a fresh walk surfaces a new instance, the original enumeration was too narrow — fold the new instance into the same round, do not defer to the next round.
- **Always** verify a prior round's claimed-fix at the *class* level, not the *line* level. If a prior round claimed "class CLOSED" and only its example sites are clean, that does not mean the class is closed — re-execute steps 1–6 of "Class > line" against the current branch state. If new sibling instances surface that the prior round didn't enumerate, the prior round's CLEAN verdict is overturned (note this explicitly in the new round's comment) and the prior round owns the procedural failure. Do not silently inherit a prior round's narrow enumeration.
