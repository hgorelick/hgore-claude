# Ground-truth protocol — verifying claims at write time

Loaded by `/brief-author`, `/engineering-plan-author`, `/plan-author`. The hosting skill calls this protocol after the first-draft prose is in memory but BEFORE emission. Output is a fixed-up draft plus a sidecar artifact recording every claim verified, dropped, or softened.

The cost model: every verifiable claim costs one Read or grep call. A 500-line chunk plan with ~80 verifiable claims costs ~80 tool calls at write time. The reviewer skill, prosecuting the same plan with hallucinated anchors, costs ~5 rounds × 5 personas × ~30 calls = ~750 calls plus the user's arbitration time. Front-load the cost.

---

## Claim taxonomy — what to verify

A "claim" in the draft is any prose substring that asserts a fact about the repo, the brief, the engineering plan, the decisions log, an external API, or a project invariant. Five classes.

### Class V1 — Anchor claims

Substrings that name a specific location in existing code or docs.

| Pattern | Example | Verification |
|---|---|---|
| `path:line` | `backend/src/lib/personHydration.ts:215` | `Read` the file at that line; verify the cited construct matches the prose's description |
| `<path> §<heading>` | `engineering-plan.md §Zero-credit invariant` | `Read` the file; verify the heading exists verbatim |
| `<file>` (path only) | `backend/scripts/cleanupPersonNames.ts` | `ls` / `Bash test -f`; verify file exists |
| `<file>:<symbol>` | `personHydration.ts:hydratePersonCredits` | `Read` the file; verify the symbol is defined there |
| `<line range>` | `lines 154-246` | `Read` the file at that range; verify the cited construct spans it |

**Fail action (Class V1):**
- File missing → drop the prose that depended on it; OR replace with the closest existing referent the prose was trying to cite (decided by the author skill, not the user).
- Line drifted → replace numeric anchor with section-heading anchor (`§<heading>` form) or with a symbol-based anchor (`<file>:<symbol>`). Numeric line anchors are drift-fragile by class; prefer the symbolic form whenever the cited construct has a stable name.
- Heading absent → either the heading was renamed (use the new name) or never existed (drop the claim).

### Class V2 — Identifier claims

Substrings that name a function, type, constant, helper, GraphQL operation, schema field, or column that the draft asserts EXISTS.

| Pattern | Example | Verification |
|---|---|---|
| Function/helper name | `the existing captureStderr helper` | `grep -rn '\bcaptureStderr\b' backend/` |
| Type/interface name | `Prisma's generated PersonScalars type` | `grep -rn 'type PersonScalars\b\|interface PersonScalars\b' backend/` |
| Constant name | `WRITER_FENCE_STALE_AFTER_MS lives in lib/` | `grep -rn 'WRITER_FENCE_STALE_AFTER_MS' backend/src/lib/` |
| Schema field | `PersonAuditLog.runId` | `Read backend/prisma/schema.prisma`; locate the column in the model |
| GraphQL operation | `useFollowMutation` | `grep -n 'mutation Follow\b' mobile/src/graphql/operations.graphql` |
| Test helper | `the existing seedTestDb helper` | `grep -rn 'seedTestDb' backend/src/__tests__/` |
| Migration filename | `20260421000001_person_wikidata_audit` | `ls backend/prisma/migrations/ \| grep <id>` |

**Fail action (Class V2):**
- Identifier absent → if the draft's intent is to *introduce* it, move the claim into the §Owns / §Contracts changed / §Acceptance criteria section under the chunk's contract (so the introduction is visible to the reviewer); if the draft's intent is to *reference an existing thing*, drop the claim or substitute the closest existing analog the grep surfaced.
- Identifier exists in a different location than implied → update the path part of the claim.

### Class V3 — Constraint claims

Substrings that assert a structural fact about existing code: count of writes, presence of a constraint, ordering of statements.

| Pattern | Example | Verification |
|---|---|---|
| "N occurrences of X" | "two writer-fence ticks per hydration" | Read the file; count the actual write sites |
| "no @@unique constraint on Y" / "@@unique on Y" | "PersonAuditLog has @@unique(actionKey, runId)" | Read schema.prisma; verify the constraint block |
| "X happens before Y" | "the staleness-check fires before the fence-set" | Read the file; verify the source-order |
| "X is enforced by Y" | "the audit-row write is enforced by tx wrapper" | Read the file; verify the enforcement |
| "ZERO hits" / "no callers" | "no caller of `oldFn` exists post-refactor" | grep; verify the count |

**Fail action (Class V3):**
- Count wrong → substitute the verified count.
- Constraint absent / present (inverted) → rewrite the prose to match reality; if the rewrite invalidates the surrounding paragraph, drop or restructure.
- Ordering wrong → rewrite; cite the source-order verbatim.

### Class V4 — Cross-document claims

Substrings that assert a fact about a sibling document (brief, engineering-plan, decisions, spec, persona file, CLAUDE.md, project memory).

| Pattern | Example | Verification |
|---|---|---|
| `decisions.md <date> entry` | `2026-05-02 entry — confirms no Pothos type` | Read decisions.md; locate the date; verify the entry's content matches the citation |
| `brief Goal` reference | `Goal: "Zero wrong-human links across both starting cohorts"` | Read brief.md §Goals; verify the verbatim quote |
| `engineering-plan §<heading>` | `engineering-plan.md §Invariants §Zero-credit invariant` | Read engineering-plan.md; verify both nested headings |
| `CLAUDE.md` rule | `CLAUDE.md §Database Protection rule X` | Read CLAUDE.md; verify the rule exists at the cited section |
| Project memory | "per project memory `feedback_X.md`" | Read the memory file at `~/.claude/projects/<project>/memory/<file>.md` |
| Persona file | `personas/testing.md §<rule>` | Read the persona file; verify the rule |

**Fail action (Class V4):**
- Quote mismatched → fix the quote (verbatim, including punctuation).
- Date wrong → fix the date.
- Heading wrong → fix the heading.
- Cited content absent → drop the cross-reference; rewrite the surrounding prose to stand without it.

### Class V5 — External-API claims

Substrings that assert a fact about an external API the chunk integrates with.

| Pattern | Example | Verification |
|---|---|---|
| TMDB endpoint shape | `GET /person/{id}/combined_credits` | Verify against `developer.themoviedb.org` (web fetch if necessary) OR existing client code in `backend/src/lib/tmdb.ts` |
| Open Library endpoint | `/works/<key>.json` | Verify against `backend/src/lib/openLibrary.ts` (the project's wrapper is canonical) |
| Anthropic SDK call shape | `messages.create({ model: ..., system: [...] })` | Verify against `backend/src/lib/llm.ts` (the project's wrapper) and `claude-api` skill if available |
| Prisma client method | `prisma.$transaction(fn, { isolationLevel })` | Verify in node_modules typings or existing usage |

**Fail action (Class V5):**
- API shape wrong → fix to match the project's wrapper (project wrapper is the canonical contract; external docs are the secondary check).
- Method absent → drop the claim or substitute the existing project pattern.

---

## When to skip verification

Three carve-outs. Each requires the carve-out be explicit in the draft and recorded in the sidecar.

**Carve-out 1 — Identifiers the chunk introduces (A-VERIFY-vs-INVENT).** A chunk plan's §Owns / §Contracts changed / §Acceptance criteria sections describe identifiers the implementer will create. These need NOT exist at write time. The author skill marks them in the sidecar as `introduced_identifiers: [...]`. The reviewer reads this list and does not prosecute these as hallucinations. Any reference to an introduced identifier OUTSIDE the chunk's owns set (e.g., a sibling chunk's plan referencing it before this one ships) is a cross-chunk wiring issue and goes through the engineering-plan's decisions-closure.

**Carve-out 2 — Future-tense prescriptions.** Prose that says "the implementer SHALL emit a banner of byte-format X" doesn't claim X exists; it specifies X. The byte-format itself MAY be invented (the chunk owns the format) or MAY echo an existing format (verify if the latter — V2/V3). The author skill flags this distinction when scanning: future-tense modal verbs (`shall`, `must`, `will`, `MUST`) attached to constructs the chunk owns are prescriptions, not anchor claims.

**Carve-out 3 — Draft mode.** Per `A-DRAFT-vs-SHIP`, a quick exploration draft (invocation flag `--draft` or `--no-ground-truth`) skips the protocol entirely. Sidecar marks `authoring_mode: "draft"`. The user must re-invoke without the flag to harden before review.

---

## Procedure (deterministic)

The hosting skill runs this AFTER first-draft prose is in memory and BEFORE the self-prosecution phase.

1. **Tokenize the draft.** Walk the markdown. For each line, scan for the patterns in Classes V1–V5. Build a verification queue: `[(line_number, claim_text, class, verification_command), ...]`.

2. **Skip carve-outs.** For each entry, check whether the claim falls under Carve-out 1 (identifier appears in §Owns / §Contracts / §Acceptance), Carve-out 2 (future-tense prescription on a chunk-owned construct), or Carve-out 3 (draft mode). If yes, mark `verification_status: skipped_<carve_out_id>` and continue.

3. **Execute verification calls.** Run the verification command for each remaining claim. Batch by file: every Class V1-V5 claim referencing the same file gets ONE Read of that file, scanned in-context. (V5 claims about external APIs almost always resolve to the project's wrapper file in `backend/src/lib/`, so they batch with V2 claims that already touched that wrapper.) Cross-file Class V2 grep can be batched with `&&`-separated greps in one Bash call.

4. **Record outcomes.** For each claim:
   - `verified` — claim survives verification verbatim. No edit.
   - `verified_softened` — claim survives but the anchor was numeric and a symbolic anchor exists; replace the numeric form with the symbolic form (drift hardening).
   - `corrected` — claim's content was wrong; replace the prose with the verified content.
   - `dropped` — claim cannot be verified and the surrounding paragraph survives without it; remove the claim.
   - `restructured` — claim cannot be verified and the surrounding paragraph CANNOT survive without it; restructure or remove the paragraph.

5. **Apply edits to the in-memory draft.** All edits in one batch, deterministic order (top-to-bottom, biggest scope first to avoid line-number drift on subsequent edits).

6. **Emit the sidecar.** Write `~/.claude/cache/author-state/<slug>.json` with the audit log:

   ```json
   {
     "artifact_path": "<original path>",
     "authoring_mode": "ship | draft",
     "ground_truth_at": "<ISO 8601 UTC>",
     "claims_total": <int>,
     "claims_verified": <int>,
     "claims_verified_softened": <int>,
     "claims_corrected": <int>,
     "claims_dropped": <int>,
     "claims_restructured": <int>,
     "claims_skipped_carveout": <int>,
     "introduced_identifiers": ["<name>", ...],
     "ground_truth_log": [
       {"line": <int>, "claim": "<text>", "class": "V1|V2|V3|V4|V5", "outcome": "<one_of_outcomes>", "evidence": "<verbatim_grep_hit_or_read_quote>"},
       ...
     ]
   }
   ```

   The reviewer (`/plan-review-v2` etc.) reads `introduced_identifiers` and skips Hallucination findings on those names, and reads `ground_truth_log` to skip re-prosecuting Class V1–V5 claims the author already verified.

7. **Hand off to self-prosecution.** The hosting skill then calls the self-prosecution protocol on the now-fixed-up draft.

---

## What this protocol does NOT do

- **Stylistic critique.** Awkward sentences, redundant prose, unclear voice — that's self-prosecution territory, not ground-truth.
- **Scope/concern enforcement.** One-concern check is a separate gate run before this protocol; if the chunk fails one-concern, ground-truth doesn't run.
- **Inventing fixes for invented prose.** When a claim is dropped, the protocol drops; it does not invent a new claim to fill the gap. If the gap matters, that's an `OPEN_QUESTION` for the user to fill, surfaced in the sidecar.
- **Plan-lint.** `/plan-lint` is a separate deterministic gate run BEFORE ground-truth; structural defects don't reach ground-truth.

The contract is narrow and predictable: take a draft with hand-waved claims, return a draft where every claim is verified, dropped, or explicitly carved out.
