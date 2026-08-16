---
name: contract-review
description: Review contract documents (PR-stack breakdowns, migration runbooks, release plans, "do exactly this" handoffs) for ambiguity, scope creep, and redundant gates. Parent edits inline; editing bias is to delete and tighten, not add.
user-invocable: true
disable-model-invocation: true
---

# Contract Review

Review one or more **contract documents** — PR-stack breakdowns, migration runbooks, release plans, "do exactly this" handoffs — for ambiguity, scope creep, and redundant gates. The editing bias is the opposite of a plan review: contracts get tightened and trimmed, not enriched with rationale.

## When to use this skill

A document is a **contract** when:
- It is read by an implementer who has no context about how it was produced.
- Each row/section is a unit of work to be performed verbatim or with named mutations.
- Success and failure are decidable from the document alone (no judgment calls about "what was meant").
- The author explicitly calls it a contract, runbook, or breakdown.

A document is **not a contract** (do not use this skill) when:
- It explores design choices, tradeoffs, or sequencing.
- It is read by someone who will make decisions while implementing.
- Sections like "## Approach", "## Risks", "## Open questions" dominate.

If you are unsure, ask. Reviewing an exploratory plan with this skill will strip away rationale the implementer needs.

## Usage

```
/contract-review <contract-path-1> [contract-path-2] ...
```

Multiple contracts are reviewed in parallel — one analysis pass per document. There is no persona system; contracts have one voice and one job.

**Argument parsing.** Split `$ARGUMENTS` on whitespace; every token is a contract path. Path resolution:
- If the token starts with `/` or `./`, treat as-is.
- Otherwise, resolve relative to the repo root.
- If no arguments are provided, ask the user which file(s) to review — do not guess.

## The named-failure rule (non-negotiable)

**Every applied edit must do one of three things and nothing else:**

1. **Delete** words, gates, rationale, or guidance the contract does not need.
2. **Tighten** an ambiguous instruction so success/failure becomes decidable from the text.
3. **Fix a structural error** (most commonly: a row's Files column omitting a file the row mutates, breaking the post-PR `git status` invariant).

**The named-failure predicate (apply to every proposed edit before writing it):**

For every proposed edit, write — in the findings report, in one concrete sentence — *what specific reader, doing what specific action, would do the wrong thing without this edit*. If the sentence is generic ("might be confusing", "could be tighter", "explains the why", "marginal call"), **the edit is not applied**. No exceptions: not even at LOW severity, not even if it "feels cleaner."

Examples that pass the predicate:
- "STRUCT-FILES on `scan-ts-py`: an implementer running `git status --porcelain` and matching against the Files column would see `.github/workflows/security-scan-all.yml` (full path) but the column says `security-scan-all.yml`, the universal-rule check fails, implementer writes a handoff."
- "ANTI-PRESTATED on `automerge-gate` Gates: the line `located at line 101` will go stale if `vuln-automerge.yml` is reformatted; the surrounding `grep -c '^\s*sleep '` is already self-checking; line-number prestatement adds maintenance cost without catching anything."

Examples that fail (do not apply):
- "ANTI-RATIONALE: this parenthetical explains why the gate works — the implementer doesn't strictly need it." → generic; no named reader-failure.
- "ANTI-HEDGE: the word 'should' in cell X could be tightened." → generic; no behavior change named.
- "Could split this gate into two smaller gates for clarity." → no failure named.

**Default-keep on borderline.** Anti-pattern findings (RATIONALE, HEDGE, XREF, PRESTATED, BELT) carry no behavior-change risk from being kept. Default disposition is "report only, do not apply" unless the named-failure predicate produces a concrete sentence. STRUCT-* and ANTI-PREPOST/ANTI-ADVICE remain auto-apply because each has a measurable failure mode (broken `git status`, broken landing, stale line numbers, ambiguous "should also").

**Never:**
- Add a gate "just in case" or "for defense in depth."
- Add a gate that catches a failure another gate already catches.
- Add a gate that pre-states a constant the gate itself already computes.
- Add rationale, "why" notes, or implementer comfort to the table — those belong in the PR description template, not the contract body.
- Add per-row byte-equality assertions when the document already cites a Universal Rule (e.g., "SHA-pinned verbatim gate") that covers all verbatim files.
- Add suggestions, "consider also doing X", or hedges.

A short contract that is silent on an edge case is better than a long contract that contradicts itself trying to address one. **But silence is not deletion** — an existing word that has been read once and found to do no harm is stable; do not delete it just because deletion is available. Convergence requires that pass N+1 finds nothing if pass N applied every edit it could justify.

## What to look for

Every finding MUST be tagged with a class ID from the lists below. The class ID is what makes findings searchable across rows: once you find one `STRUCT-FILES` violation, sweep every row for the same class before moving on. Do not invent new class IDs; if a finding doesn't fit, escalate to the user.

### Structural classes (CRITICAL or HIGH; the only additions the parent applies without question)

- **`STRUCT-FILES`** — Files-column completeness. If a row's Mutation/Gates name a file path, that path must be in the row's Files column. The Universal Rule "after all mutations, `git status --porcelain` matches the row's Files column exactly" is the contract's spine; a missing file silently breaks every row that has it.
- **`STRUCT-MODE`** — Mode-column accuracy. `verbatim` means empty Mutation. `mutate` / `mixed` / `verbatim then mutate` rows must have a Mutation column that names the exact change by content, not by line number alone (line numbers shift; content does not).
- **`STRUCT-LINES`** — Line-range boundary correctness. Every `source lines N–M` reference must end at a content boundary verified at SRC_SHA: end-of-job, end-of-step, blank line before next section. Round numbers and "looks right" boundaries are a smell.
- **`STRUCT-WAVE`** — Cross-row file ordering. If row A modifies file F and row B also modifies file F, the wave map (or Base column) must serialize them. Two rows touching the same file in parallel is a contract bug.
- **`STRUCT-DRIFT`** — Behavior-change disguised as verbatim. A row marked `verbatim` from a source SHA is *not* a no-op against `main` if `main` and the source SHA differ for that file. The contract must call this out so the implementer surfaces it in the PR description.
- **`STRUCT-UNIVERSAL`** — Per-row gate restating a Universal Rule. If the document has a Universal Rules section ("SHA-pinned verbatim gate", "no `sleep`", etc.), per-row gates that restate those rules are redundant. Delete.

### Anti-pattern classes

These split into two dispositions. Auto-apply means delete on sight (each has a measurable downstream failure). Report-only means raise in the findings but do not edit the contract — borderline calls between reviewers on these classes are the dominant source of pass-to-pass thrash.

**Auto-apply (delete the offending text):**

- **`ANTI-PREPOST`** — Pre/post-check pair bracketing a single mutation. A pre-mutation count + a post-mutation empty-grep usually catches the same drift twice. Keep the post-check unless the pre-check guards a different drift dimension (e.g., "expected count = N before reword" catches an unenumerated reference that a post-empty-grep would silently let through). Failure mode: implementer wastes time satisfying both halves of a redundant pair.
- **`ANTI-ADVICE`** — "Implementer should also..." / "consider" / "ideally" / "for safety". Failure mode: implementer treats advice as required and adds work outside the contract, OR treats it as optional and skips a real gate next to it. Either way the row's success criteria become non-decidable.
- **`STRUCT-UNIVERSAL`** — Per-row gate restating a Universal Rule. Failure mode: when the Universal Rule changes, the per-row copy goes stale silently.

**Report-only (raise in findings, do not edit unless the named-failure predicate produces a concrete sentence):**

- **`ANTI-BELT`** — Belt-and-suspenders gates. A row asserting `wc -l = N` *and* byte-equality over the same range *and* a content spot-check is doing one job three times. Defensible if each layer catches a distinct failure class.
- **`ANTI-PRESTATED`** — Pre-stated constant for a self-checking gate. Apply only when the prestate names a specific shifting value (line numbers, file lengths) that will go stale; do not apply for prestated counts that are stable invariants of the contract (e.g., "the file has 5 jobs").
- **`ANTI-RATIONALE`** — "Why" notes inside table cells. Apply only when the prose contradicts the mechanical instruction or claims something the gate doesn't verify; otherwise an explanatory parenthetical is a stable cost.
- **`ANTI-HEDGE`** — "may", "should", "approximately", "if needed". Apply only when the hedge makes a gate non-decidable; "the implementer may also want to" near a real instruction is non-decidability and applies; "may take 30s" inside a fork-test description is descriptive and does not.
- **`ANTI-XREF`** — Cross-references that resolve no ambiguity beyond what the rule already covers. Apply only when the reference is circular or points to a section that has been removed.

### Forbidden review-archaeology patterns

A contract that has accumulated review archaeology is broken: the implementer cannot reconstruct review history before they can act. Strip any of the following on sight:

- **Addendum sections** ("Addendum A", "Architecture-review addenda", etc.) — integrate findings into the section they correct.
- **Review attribution** ("Architecture review found…", "Per addendum N…") — the contract states facts, not who supplied them.
- **Cross-references between fix locations** ("see addendum E", "binding per addendum N") — integrate or use one named subsection.
- **Conflict-resolution metadata** ("where X conflicts with Y, Y wins") — pre-resolve and state the resolved instruction.
- **Historical comparisons** ("the original contract said X but actually Y", "previous version said…") — just state the correct thing.
- **"Decisions resolved" catalogues** — decisions bake into the instructions, not separate sections.
- **Persona-attribution headers** ("from a backend lens") — one document, one voice.

## Workflow

**Architecture: parent edits inline.** Verification agents return structured findings; the parent reads all findings and applies every edit directly to the contract file. This gives the editor a whole-document view when applying fixes and avoids the addenda/cross-reference archaeology that parallel-write workflows produce.

The order of steps 3a–3c matters: each is a mechanical full-document sweep. Doing them out of order or skipping one is how reviews leak findings to a second pass.

1. **Load context.** Read the contract. If it cites a source SHA, branch, or external file, verify those exist before launching review agents.

2. **Verify factual claims in parallel.** Contracts make many specific factual claims (line ranges, file existence, test counts, `wc -l` values, SHA references). Launch verification agents (Explore subagent type) in parallel — one per claim cluster — to confirm. Cap at ~3 agents; this is verification, not exploration.

3. **Mechanical sweeps (do all three before any analysis).** These catch the structural classes that domain-reading misses. Each sweep is one pass over the whole document; do not stop at the first finding — collect every occurrence of the class.

   **3a. `STRUCT-FILES` sweep.** For each row: enumerate every file path mentioned anywhere in the Mutation column or the Gates column (including paths inside shell commands like `grep -n 'demo' security-remediate.yml` — that is `security-remediate.yml`). Diff against the Files column. Every path missing from Files is a `STRUCT-FILES` finding.

   **3b. `STRUCT-LINES` sweep.** For each `source lines N–M` reference in the document: open SRC_SHA at line M and line M+1 and confirm M is a content boundary (end of job, end of step, blank line before next banner, closing `}`/`fi`/`done`). If M lands mid-section or M+1 starts a new section without M closing the previous one, that is a `STRUCT-LINES` finding. Round numbers (M=100, M=200) get extra scrutiny.

   **Parent-direct re-verification rule for STRUCT-LINES.** Verification agents miscount line numbers regularly (cat -n display offset confusion, raw-string-spans-lines confusion, blank-line-vs-content confusion). Before applying *any* STRUCT-LINES edit — whether to fix a boundary or to "correct" off-by-one prose — the parent (not a verification agent) MUST run `git show SRC_SHA:<path> | sed -n 'N-2,N+2p' | cat -n` directly via Bash, paste the output into the findings report, and write the boundary determination from that paste. If the agent's claim and the parent-direct paste disagree, trust the paste; if both are unreliable, do not apply the edit and escalate. The cost of skipping this rule is the highest-thrash edit class: applying a "fix" that is itself wrong, which the next pass then re-fixes back.

   **3c. `STRUCT-DRIFT` sweep.** For every file marked `verbatim` from SRC_SHA: `diff <(git show SRC_SHA:<path>) <(git show origin/main:<path>)`. Any non-empty diff means importing SRC_SHA's version is a behavior change against `main`. If the row doesn't already call that out, it is a `STRUCT-DRIFT` finding.

4. **Analyze the rest inline.** With the mechanical sweeps banked, the parent reads each cell against the anti-pattern classes. The single question for every cell is: *does this row, alone, tell an implementer who has never seen this document exactly what to do and how to verify it landed?* Tag every finding with a class ID.

5. **Apply edits inline, governed by the named-failure rule.** For each finding, write the named-failure sentence in the findings report *before* writing the Edit tool call. If the sentence is generic, do not edit. Auto-apply classes (STRUCT-* except where the parent-direct re-verification rule blocks, ANTI-PREPOST, ANTI-ADVICE, STRUCT-UNIVERSAL) still require a named-failure sentence — the difference vs report-only classes is that auto-apply classes will reliably *produce* one, not that the requirement is waived.

6. **Convergence check.** Before declaring APPROVED, mentally simulate a fresh `/contract-review` pass starting from the current document. For every edit you applied, ask: would a different reviewer, given the same skill and the same document, definitely apply this same edit? If the answer is "probably not" or "depends on judgment," that edit is a thrash candidate and must be reverted. The criterion for APPROVED is not "I cannot find anything else to change" — it is "the next reviewer running this skill on this document will find nothing to change."

7. **Re-review.** One re-review pass is enough for contracts; this skill does not loop. If the first pass leaves remaining concerns, escalate to the user — do not iterate. Looping is how pass-to-pass thrash starts.

## Findings report (agent → parent contract)

Each verification agent returns a structured findings report tagged by class ID. **The agent does not edit the contract.** The parent reads all reports, applies the named-failure predicate to each finding, and writes the edits directly.

Severities:

- **CRITICAL** — the contract is ambiguous, internally contradictory, or has a Files column that breaks the `git status` invariant. The implementer cannot execute the row deterministically.
- **HIGH** — a behavior-change-disguised-as-no-op, a wave-map bug serializing two rows that touch the same file, or a Mode/Mutation mismatch.
- **MEDIUM** — a single genuinely loose corner (e.g., a count assertion missing where drift could go undetected). Apply only if the named-failure predicate yields a concrete sentence.
- **LOW** — report-only by default. The named-failure rule almost never produces a concrete sentence at this severity; if it did, the finding belongs at MEDIUM. Do not delete at LOW just because deletion is available.

## Final report

Group findings by class ID, not by row. Class grouping is what proves the sweep was exhaustive: if `STRUCT-FILES` lists only 1 of 5 occurrences, the sweep failed.

```
## Contract Review Complete: <filename>

### Structural fixes applied
- **STRUCT-FILES** (N occurrences): <list every row touched>
- **STRUCT-LINES** (N occurrences): <list every range fixed>
- **STRUCT-MODE** / **STRUCT-WAVE** / **STRUCT-DRIFT** / **STRUCT-UNIVERSAL**: <as applicable>

### Deletions
- **ANTI-PRESTATED** (N occurrences): <list every row>
- **ANTI-RATIONALE** (N occurrences): <list every cell>
- **ANTI-BELT** / **ANTI-ADVICE** / **ANTI-PREPOST** / **ANTI-HEDGE** / **ANTI-XREF**: <as applicable>

### Tightenings
- <each ambiguous instruction made decidable, tagged with the class that motivated it>

### Needs user input (if any)
- <design tradeoffs the reviewer cannot resolve alone>

### Contract Status: APPROVED / NEEDS USER INPUT
```

A contract is **APPROVED** when every row, read in isolation, tells the implementer exactly what to do and exactly how to know it landed — and contains no word that does not contribute to that goal.

## Edge cases

- **Document is actually an exploratory plan, not a contract.** Stop and say so. Tell the user this skill will strip rationale the implementer needs; they should review it as a plan instead.
- **Document mixes plan and contract sections** (common: a plan document with one "PR breakdown" appendix). Review only the contract sections; tell the user which sections you reviewed and which you skipped.
- **Source-of-truth verification fails.** A contract that cites a SHA, line range, or file that doesn't exist is broken at the foundation. Report CRITICAL and stop — do not try to patch around it.
- **Universal Rules section is missing.** Many contracts implicitly rely on universal rules they never state. Flag this once: "the contract relies on rule X without stating it; consider adding a Universal Rules section." Do not add it yourself unless the user asks.
