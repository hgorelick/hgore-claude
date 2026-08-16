# Project context-pack protocol — read the immutable sources once per project

Loaded by `/brief-author`, `/engineering-plan-author`, `/plan-author`. The hosting skill consults this protocol at the start of **Source ingest**, before the per-file reads.

The three author skills run consecutively on clean sessions (brief → `/clear` → engineering-plan → `/clear` → chunk plan), and every clean session re-Reads the same immutable project-level sources from scratch: `spec.md` (thousands of lines), `CLAUDE.md`, the project's schema file (if any), the project's API-operations file (if any), and the project-memory directory. Each skill then re-derives the same project-level invariants ledger and identifier inventory from byte-identical inputs. This protocol caches the **mechanical index + the project-level invariants** of those sources once per project, sha-keyed, so subsequent invocations (later stages, later skills, later features) skip the full-file ledger-building reads.

---

## The load-bearing correctness rule — AUGMENT, NEVER REPLACE

The context-pack is an **index** (what exists, and where) plus a **project-invariants ledger** (the rules identical for every feature). It is NOT a summary that stands in for a source file.

- The pack removes the **Source-ingest full-file reads** whose only purpose is to enumerate what exists (build the identifier ledger, build the project invariants list, locate spec sections).
- The pack does **NOT** remove any **Ground-truth audit** verification read. Every V1–V5 claim still earns a live `Read`/`grep`; the `ground_truth_log` evidence must still be a real grep hit or Read quote — **never** a citation of the cached inventory. The pack may *plan* the batches (it knows which file an identifier lives in) but the evidence is always live.
- When a skill needs a source file's **prose** (a spec section's wording for a brief Goal, a schema model's field types), it Reads that span — targeted via the pack's section map — and never trusts a cached digest of it.

This rule is what keeps the optimization correctness-neutral: the pack only ever saves a read whose result is "what exists," and only for ingest-time ledger building, never for claim verification.

---

## Location

`~/.claude/cache/author-state/<project-slug>__context-pack.json`

`<project-slug>` is the absolute project root with path separators replaced by `-` (the same convention as the project-memory directory name — e.g. project root `/path/to/your-project` → `-path-to-your-project`). One pack per project, shared by all three author skills and **all** features in that project (the cached sources are project-level, not feature-level).

The pack is a **separate file from the per-artifact sidecars** (`<feature>__brief.json`, `<feature>__engineering-plan.json`, `<feature>__<chunk-slug>.json`). It does not extend or alter their schema, so the reviewer skills and `/explain-blockers` / `/solve-blockers` (which parse the per-artifact sidecars) are entirely unaffected by it.

---

## Schema

```json
{
  "schema_version": 1,
  "project_slug": "<project-slug>",
  "built_at": "<ISO 8601 UTC>",
  "built_by": "brief-author | engineering-plan-author | plan-author",
  "source_shas": {
    "spec.md": "<sha256>",
    "CLAUDE.md": "<sha256>",
    "schema_file": "<sha256 or null if absent — the project's schema/data-model definition file>",
    "api_operations_file": "<sha256 or null if absent — the project's API-operations definition file>",
    "memory_set": "<sha256 of the sorted list of (memory-file-path, sha256) pairs>"
  },
  "project_invariants": [
    "<verbatim project-level invariant — identical for every feature (e.g. 'No writes without an authenticated session'; 'All monetary values stored in the smallest currency unit'; business rules from CLAUDE.md / spec.md)>"
  ],
  "spec_section_map": [
    {"heading": "<verbatim heading>", "level": <int>, "line_start": <int>, "line_end": <int>}
  ],
  "claude_md_rule_index": [
    {"rule": "<short label>", "line_start": <int>, "line_end": <int>}
  ],
  "identifier_inventory": {
    "schema_models": [{"model": "<name>", "fields": ["<field>", ...], "enums_used": ["<enum>", ...]}],
    "schema_enums": [{"enum": "<name>", "values": ["<value>", ...]}],
    "api_operations": [{"name": "<op-name>", "kind": "query | mutation | subscription | fragment"}]
  },
  "memory_index": [
    {"file": "<memory-file-name>.md", "description": "<one-line description from frontmatter>", "sha256": "<sha256>"}
  ]
}
```

Every cached field is either **mechanical** (section line-ranges, the model/field/enum/operation inventory, file shas) or **project-stable** (the invariants ledger that does not vary by feature). Nothing here is a lossy summary substituting for a source read.

---

## Procedure

Run at the start of Source ingest.

1. **Load.** Read the pack at the location above. If absent or unparseable → go to step 3 (cold build). This is graceful: a missing/corrupt pack never blocks; the skill simply behaves as it did before this protocol existed.

2. **Validate by sha (mandatory).** For each entry in `source_shas`, recompute the current sha of that source (`shasum -a 256 <path>`; for `memory_set`, recompute the sha of the sorted `(path, sha256)` list over the project-memory directory — this detects files added or removed, not just edited). Batch all the `shasum` calls into one Bash invocation.
   - **All match** → the pack is current. Use it; skip the full-file ledger reads in Source ingest (the reads the hosting skill marks `[pack-cached]`). Proceed to the targeted, feature-specific reads only.
   - **Any mismatch** (including a changed `memory_set`) → the pack is stale. Go to step 3 (rebuild the **entire** pack — no partial rebuild; full rebuild is simpler and provably correct, and the sources change rarely enough within an authoring window that a full rebuild is cheap relative to its amortization).

3. **Build (cold or rebuild).** Do exactly the full-file reads Source ingest would have done without the pack — Read `spec.md`, `CLAUDE.md`, the schema file, the API-operations file, and walk `MEMORY.md` + the project-memory directory — then:
   - Derive `spec_section_map` and `claude_md_rule_index` mechanically from the heading structure.
   - Derive `identifier_inventory` mechanically from the schema and operations files.
   - Derive `project_invariants` (the feature-independent invariants — the same list every author skill builds today; the feature-specific subset is layered on per-invocation in Source ingest, not cached here).
   - Compute and record `source_shas` (the same `shasum` batch as step 2).
   - Write the pack to its location (`mkdir -p ~/.claude/cache/author-state` first — Write does not create parents).
   The first author-skill invocation in a project (or the first after any source change) pays this cost — identical to today's Source ingest. Every subsequent invocation, every later stage, and every later feature amortizes it.

4. **Hand context to Source ingest and downstream stages.**
   - Source ingest uses `project_invariants` + `identifier_inventory` instead of re-deriving them, and uses `spec_section_map` / `claude_md_rule_index` to make its remaining reads targeted.
   - Ground-truth audit uses `identifier_inventory` only to **plan** its batches (which file each V2 identifier lives in); the evidence is still a live read per the AUGMENT-NEVER-REPLACE rule.
   - Self-prosecution passes `project_invariants` inline to persona subagents (see `self-prosecution-protocol.md` → `{project_invariants_digest}`) so personas have the project rules without each re-Reading `CLAUDE.md`.

---

## Interaction with the hosting skills

- **`--draft` mode.** The pack is still loaded/built in Source ingest (it speeds the draft too) and never conflicts with the Ground-truth / Self-prosecution skips — those stages simply don't run.
- **No-op invocation** (sidecar present, artifact sha matches, no new instruction). The pack load is additive and does not change the no-op short-circuit; the skill still prints "no changes" and exits.
- **Repo-state drift mid-authoring.** Unaffected. The pack governs Source-ingest ledger reads; the existing `REPO_STATE_DRIFT` detection (per-file sha captured at Source ingest, re-checked at Ground-truth audit) is unchanged and still authoritative for the chunk's read-set.

---

## What this protocol does NOT do

- **Cache feature-level state.** Briefs, engineering plans, chunk plans, decisions logs, and per-artifact ground-truth logs live in the per-artifact sidecars — never here. This pack is strictly the project-level immutable substrate.
- **Substitute for a verification read.** Restated because it is the whole correctness contract: the `ground_truth_log` evidence is always a live `Read`/`grep`, never a pack citation.
- **Survive a source change silently.** Any edit to a tracked source (or any add/remove in the memory directory) invalidates the whole pack on the next load; there is no stale-read window.
