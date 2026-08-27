#!/usr/bin/env python3
"""plan-lint: deterministic structural checks for the artifact chain.

Usage:
  plan-lint [--type <kind>] <path>

  <path> is one of:
    - A vision document (vision.md) — lints the spec map.
    - A spec (specs/<slug>/spec.md, or a root spec.md) — lints the Decomposition
      section.
    - A feature directory (features/<name>/) — lints the brief, the engineering
      plan + every per-chunk plan under implementation/, and warns on chunks
      indexed in the engineering plan that have no per-chunk plan yet.
    - A brief (features/<name>/brief.md).
    - An engineering plan file (features/<name>/engineering-plan.md).
    - A per-chunk plan file (features/<name>/implementation/<slug>.md).
    - A lightweight ad-hoc plan (.scratch/*.md) — runs the chunk-plan checks on
      every "### Chunk: `<slug>`" block found.

  --type forces the document kind, for linting a draft whose filename does not
  carry its identity: vision | spec | brief | engineering-plan | chunk.

  --strict exits 1 when any finding is raised, WARN included. The author skills'
  ship-mode gates run the lint this way, so a legacy-shape WARN blocks a ship-mode
  draft; the reporting run (and --draft) leaves WARN informational.

  Both flags precede the path.

Project-specific rules (the review-complexity budget's subsystem map, the
invariant-class vocabulary, the thresholds) load from features/lint-config.json.
When that file is absent those checks skip — this lint runs against more than one
project and a guessed subsystem map produces confident nonsense.

Exit codes:
  0  — all checks passed (under --strict, no findings at all)
  1  — at least one check failed (under --strict, at least one finding)
  2  — usage / IO error

The lint is pure parsing — no LLM judgment, no external services. Output is one
finding per line, prefixed with FAIL or WARN. FAIL counts toward exit-1; WARN is
informational only (e.g. file not found in repo, but path looks plausible).
"""

from __future__ import annotations

import fnmatch
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable

# ---------------------------------------------------------------------------
# Project config (features/lint-config.json)
# ---------------------------------------------------------------------------

# The lint runs against more than one project, so nothing project-specific may
# live in this file. The subsystem map, the invariant-class vocabulary, and the
# budget thresholds are the project's; they load from features/lint-config.json.
# When the file is absent, every check that depends on it is skipped rather than
# guessed at — a wrong subsystem map produces confident nonsense.

CONFIG_FILENAME = "lint-config.json"


@lru_cache(maxsize=32)
def load_config(start: Path) -> dict | None:
    """Walk up from an artifact path to the nearest features/lint-config.json."""
    for parent in [start, *start.parents]:
        candidate = parent / CONFIG_FILENAME
        if candidate.is_file() and parent.name == "features":
            try:
                return json.loads(candidate.read_text(encoding="utf-8", errors="replace"))
            except (ValueError, OSError):
                return None
    return None


def _glob_match(path: str, pattern: str) -> bool:
    """fnmatch with a `**/`-prefixed pattern also matching at depth zero.

    `**/*.test.ts` should match `x.test.ts`, not just `a/b/x.test.ts`; plain
    fnmatch requires the literal slash the `**/` implies.
    """
    if fnmatch.fnmatch(path, pattern):
        return True
    if pattern.startswith("**/"):
        return fnmatch.fnmatch(path, pattern[3:])
    return False


def _matches_any(path: str, patterns: Iterable[str]) -> bool:
    return any(_glob_match(path, p) for p in patterns)


def _looks_like_repo_path(token: str) -> bool:
    """Is this backticked token a repo-relative file path?

    Owns bullets quote plenty of things that are not files: bare symbols
    (`ctx.loaders`), relative import specifiers copied out of source
    (`../../lib/tokenFamilies.js`), and pinned CI action refs
    (`actions/checkout@v4`). Reporting those as misfiled paths is noise that
    trains the reader to skip the finding that matters.
    """
    if "/" not in token:
        return False
    if token.startswith((".", "/", "~", "@")):
        return False
    if "@" in token:  # actions/checkout@v4, @scope/pkg
        return False
    return True


def classify_paths(paths: Iterable[str], config: dict) -> tuple[float, set[str], list[str]]:
    """Score an Owns set against the project's subsystem map.

    Returns (weighted file count, distinct subsystems touched, unclassified paths).
    Docs weigh nothing; tests weigh half — they are reviewed in full for coverage
    but are parallel and non-cross-cutting, so they do not compound review
    difficulty the way production files do.
    """
    subsystems: dict[str, list[str]] = config.get("subsystems", {})
    zero = config.get("zero_weight", [])
    half = config.get("half_weight", [])

    weighted = 0.0
    touched: set[str] = set()
    unclassified: list[str] = []

    for path in paths:
        if _matches_any(path, zero):
            continue
        if _matches_any(path, half):
            # Tests count toward the file axis at half weight but never add a
            # subsystem: a test living beside the code it exercises is not a second
            # layer to reason about, and counting it as one would push every
            # well-tested chunk over the no-exemption cap.
            weighted += 0.5
            continue
        weighted += 1.0
        for name, globs in subsystems.items():
            if _matches_any(path, globs):
                touched.add(name)
                break
        else:
            if _looks_like_repo_path(path):
                unclassified.append(path)

    return weighted, touched, unclassified


# ---------------------------------------------------------------------------
# Lint rule definitions
# ---------------------------------------------------------------------------

# The four chunk intents. Foundation carries a structural obligation the others
# do not: it changes no behavior, so a Foundation chunk nothing depends on has no
# consumer at all and is scaffolding by definition.
CHUNK_INTENTS = {"foundation", "behavior", "hardening", "migration"}

# A deferral's destination: a GitHub issue reference or a feature slug. An
# `Intentionally deferred` item without one is indistinguishable from a silent
# narrowing, which is the failure the four-bucket Scope exists to prevent.
DEFERRAL_DESTINATION_RE = re.compile(r"#\d+|`[a-z][a-z0-9]*(?:-[a-z0-9]+){1,3}`")

# Invariant mechanism vocabulary. `doc` is valid but unenforcing — flagged when
# the invariant sits in one of the project's high-risk classes.
INVARIANT_FORMS = {"test", "assert", "gate", "doc"}

# Vague verbs that, when followed by no measurable predicate, fail the
# "objectively verifiable exit criterion" rule. We accept the verb if a colon,
# specific command, file path, test name, or symbol name follows it on the same
# line — that means a measurable predicate IS being named.
VAGUE_VERBS = {"implement", "complete", "works", "ensure", "handle", "support"}

# Tokens that count as "measurable predicate present" when they appear after a
# vague verb on the same line.
MEASURABLE_TOKENS = re.compile(
    r"(`[^`]+`|exits?\s+\d+|passes?\b|green\b|exists?\b|equals?\b|returns?\b|"
    r"contains?\b|matches?\b|`?\d+`?|test::|\.test\.|\.spec\.|::|/|\bfile\b|\bgate\b)"
)

# Slug shape — kebab-case, 2–4 words. Same rule the project already enforces.
SLUG_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+){1,3}$")

# Forbidden slug shapes (position-encoded).
FORBIDDEN_SLUG_PATTERNS = [
    re.compile(r"^phase-\d+"),
    re.compile(r"^step-\d+"),
    re.compile(r"^wave-\d+"),
    re.compile(r"^chunk-\d+"),
    re.compile(r"^\d+-"),
    re.compile(r"-\d+[a-z]$"),  # cascade-1a, cascade-1b
]

# A leading creation-index prefix on the FILENAME (e.g. `03-cascade-rewrite.md`)
# is a glance-ordering affordance that /plan-author assigns in authoring order so
# the files sort by creation order in a directory listing. It is NOT part of the
# slug identity: it is stripped before the slug is derived, so FORBIDDEN_SLUG_PATTERNS
# above still reject a genuinely position-encoded slug wherever the identity lives —
# the H1, the `**Slug:**` line, or the engineering-plan chunk index. Only the
# filename stem may carry this prefix.
CREATION_INDEX_PREFIX_RE = re.compile(r"^\d+-")

# Heading regexes.
H2 = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
H3 = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)

# --- Decomposition-layer vocabulary (vision spec map, spec Decomposition) ----

# A spec slug and a brief slug are concern-named kebab-case, 1–4 words. One word
# is legal here where it is not at the chunk layer: `terrain` names a whole
# domain, and padding it to two words to satisfy a chunk-layer rule is noise. The
# position-encoded shapes above are rejected at every layer.
DECOMP_SLUG_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+){0,3}$")

# The four brief intents. Foundation carries the same structural obligation its
# chunk-layer namesake does — it binds vocabulary or structure other briefs
# consume, so one nothing depends on has no consumer at all.
BRIEF_INTENTS = {"foundation", "content", "instrument", "conformance"}

# The four map-entry fields, in the order the format states them.
MAP_ENTRY_FIELDS = ("Owns", "Split line", "Depends on", "Covers")

# The four Decomposition subsections, in fixed order.
DECOMPOSITION_SUBSECTIONS = ("seams", "briefs", "scope stubs", "coverage")

# Advisory ceiling for a brief's on-disk size. Past this a brief is almost
# always re-narrating itself (Solution restating Goals, Scope restating both)
# or carrying detail that belongs in decisions.md or the engineering plan.
BRIEF_SIZE_ADVISORY_BYTES = 15 * 1024

# The universal core of a spec, per `_spec-common/spec-format.md` § Section template.
# Matched on the heading's opening words, so a project that lengthens a title keeps
# passing. The optional sections (Roadmap, Analytics, External integrations, Open
# questions) are absent by default and never checked for.
SPEC_REQUIRED_SECTIONS = (
    "overview",
    "domain model",
    "invariants",
    "feature areas",
    "non-goals",
    "decomposition",
    "glossary",
)

# A vision section heading carries its number: `## 17. The spec map`.
NUMBERED_HEADING_RE = re.compile(r"^\d+\.\s*")

# Lifecycle vocabulary banned from a decomposition section. The section states
# what is permanently true about a boundary; anything that flips the day a
# downstream unit lands is state and belongs in the sidecar (specs/README.md at
# the vision layer, features/README.md at the spec layer).
DECOMP_STATUS_TOKENS_I = re.compile(
    r"\bshipped\b|\bin[-\s]flight\b|\bparked\b|\bon[-\s]loan\b", re.IGNORECASE
)
# Case-sensitive: TODO and WIP are markers, not words, and `Status:` is the
# decision-log field name leaking out of the log.
DECOMP_STATUS_TOKENS_CS = re.compile(r"\bTODO\b|\bWIP\b|\bStatus:")
DATE_TOKEN = re.compile(r"\b\d{4}-\d{2}(?:-\d{2})?\b")
# Vision-layer only. `owed` is roster vocabulary there, but at the spec layer
# "outcomes owed" is a Scope-stub field name and carries no lifecycle claim.
# `next` is scoped to its lifecycle shapes — a split line legitimately reasons
# about "the next rule".
VISION_STATUS_TOKENS = re.compile(
    r"\bowed\b|\bnext\s+(?:spec|up|to\s+author)\b|"
    r"\b(?:is|comes|authored|written)\s+next\b|\bup\s+next\b",
    re.IGNORECASE,
)

# A split line is a predicate: one sentence deciding, for any rule not yet
# written, which side of the seam it lands on. Two mechanical tells give away an
# enumeration wearing a predicate's clothes — an itemized series, and an example
# marker. Either one with no decisional construction anywhere in the line is the
# defect; whether a predicate that IS decisional decides the RIGHT side stays
# with /vision-review and /spec-review.
SPLIT_LINE_ENUMERATION_RE = re.compile(
    r"\b[\w-]+,\s+[^,;]{1,60},\s+(?:and|or)\s+"
    r"|\bsuch as\b|\be\.g\.|\bfor example\b|\bincluding\b",
    re.IGNORECASE,
)
SPLIT_LINE_PREDICATE_RE = re.compile(
    r"\bvs\.?\b|\bversus\b|\bwhether\b|\bany rule\b|\ba rule\b"
    r"|\brules?\s+(?:that|about|naming|touching)\b"
    r"|\bbelongs?\s+to\b|\blands?\b|\bstays?\b|\bdecides?\b|\bgoes?\s+\w"
    r"|\bif\b|;",
    re.IGNORECASE,
)

# Path token in markdown: backticked path with at least one slash or a dot
# followed by an extension.
PATH_TOKEN = re.compile(r"`([^`\s]+\.[a-zA-Z0-9]+|[^`\s]+/[^`\s]+)`")


# ---------------------------------------------------------------------------
# Result reporting
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    severity: str  # "FAIL" or "WARN"
    file: str
    rule: str
    message: str

    def render(self) -> str:
        return f"{self.severity}  [{self.rule}]  {self.file}: {self.message}"


@dataclass
class LintReport:
    findings: list[Finding] = field(default_factory=list)

    def add(self, severity: str, file: str, rule: str, message: str) -> None:
        self.findings.append(Finding(severity=severity, file=file, rule=rule, message=message))

    @property
    def fail_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "FAIL")

    @property
    def warn_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "WARN")

    def print(self) -> None:
        for f in self.findings:
            print(f.render())
        print()
        print(f"Summary: {self.fail_count} FAIL, {self.warn_count} WARN")


# ---------------------------------------------------------------------------
# Section splitting helpers
# ---------------------------------------------------------------------------


HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def read_text(path: Path) -> str:
    """Read an artifact as UTF-8, substituting for anything that is not.

    A byte the codec cannot decode is a defect in the file, and the finding that
    names it is worth more than a traceback: undecodable bytes become U+FFFD and
    every structural check still runs on the rest of the document.
    """
    return path.read_text(encoding="utf-8", errors="replace")


def strip_html_comments(text: str) -> str:
    """Remove HTML comments before any structural parsing.

    Authoring guidance lives in comments, and that guidance routinely contains
    illustrative tables, example bullets, and banned-pattern samples. Parsed as
    content they are indistinguishable from the real thing — an example chunk-index
    table inside a comment shadows the actual one below it.
    """
    return HTML_COMMENT_RE.sub("", text)


def iter_sections(text: str, level: int = 2) -> list[tuple[str, str]]:
    """Split markdown by H2 (level=2) or H3 (level=3) headings, positionally.

    Titles keep their original case and every occurrence survives. Two sections
    under the same heading are two sections: keying them by title would let the
    second silently replace the first, and the fields of the replaced one would
    never be linted at all.
    """
    pattern = H2 if level == 2 else H3
    matches = list(pattern.finditer(text))
    out: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out.append((title, text[start:end]))
    return out


def split_sections(text: str, level: int = 2) -> dict[str, str]:
    """Split markdown by H2 (level=2) or H3 (level=3) headings into a dict.

    Lowercased keys, for the lookups that only ask whether a section is there.
    Anything that lints per-entry uses `iter_sections` instead.
    """
    return {title.lower(): body for title, body in iter_sections(text, level)}


def find_section(sections: dict[str, str], *aliases: str) -> str | None:
    """Look up a section by any of its possible titles (lowercased)."""
    for a in aliases:
        if a.lower() in sections:
            return sections[a.lower()]
    return None


CELL_SPLIT_RE = re.compile(r"(?<!\\)\|")


def split_table_row(line: str) -> list[str]:
    """Split one markdown table row into cells, honouring `\\|`.

    An escaped pipe is content — the spec template itself writes alternatives that
    way (`Foundation \\| Content \\| …`, `0.5 \\| 1.0 \\| 2.0`). Splitting on it
    shifts every cell right of the escape, so the Intent column reads a fragment of
    the Scope prose and the Brief column reads a fragment of the unit name.
    """
    core = line.strip()
    if core.startswith("|"):
        core = core[1:]
    if core.endswith("|") and not core.endswith("\\|"):
        core = core[:-1]
    return [c.strip().replace("\\|", "|") for c in CELL_SPLIT_RE.split(core)]


def extract_table(section_body: str) -> list[list[str]]:
    """Extract the first markdown table from a section body. Returns rows as
    list-of-cells, with the header row first and the separator row dropped."""
    rows: list[list[str]] = []
    for line in section_body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            if rows:  # table ended
                break
            continue
        if re.match(r"^\|[\s:|-]+\|$", line):
            continue  # separator row
        rows.append(split_table_row(line))
    return rows


def extract_paths_from_cell(cell: str) -> list[str]:
    """Pull markdown-backticked file paths out of a table cell or bullet line."""
    return [m.group(1) for m in PATH_TOKEN.finditer(cell)]


# ---------------------------------------------------------------------------
# Brief linting
# ---------------------------------------------------------------------------


@dataclass
class BriefData:
    file: str
    size_bytes: int = 0
    goals: list[str] = field(default_factory=list)          # one entry per bullet block
    scope_section_present: bool = False
    legacy_non_goals: bool = False
    deferred_items: list[str] = field(default_factory=list)


def _bullet_blocks(body: str) -> list[str]:
    """Group each top-level `- ` bullet with its indented continuation lines.

    A Goal is two lines — the outcome, then its `Measured by:` clause — so the
    lint has to read the bullet as a block, not a line.
    """
    blocks: list[str] = []
    current: list[str] = []
    for raw in body.splitlines():
        if re.match(r"^-\s+", raw):
            if current:
                blocks.append("\n".join(current))
            current = [raw]
        elif current and (raw.startswith(" ") or raw.startswith("\t")) and raw.strip():
            current.append(raw)
        elif current and not raw.strip():
            continue
        elif current:
            blocks.append("\n".join(current))
            current = []
    if current:
        blocks.append("\n".join(current))
    return [b for b in blocks if not b.lstrip("- ").startswith("<")]


def parse_brief(path: Path, text: str) -> BriefData:
    brief = BriefData(file=str(path), size_bytes=len(text.encode("utf-8")))
    text = strip_html_comments(text)
    sections = split_sections(text, level=2)

    goals_body = find_section(sections, "Goals")
    if goals_body:
        brief.goals = _bullet_blocks(goals_body)

    scope_body = find_section(sections, "Scope")
    if scope_body is not None:
        brief.scope_section_present = True
        subs = split_sections(scope_body, level=3)
        deferred = find_section(subs, "Intentionally deferred")
        if deferred:
            brief.deferred_items = _bullet_blocks(deferred)
    elif find_section(sections, "Non-goals") is not None:
        brief.legacy_non_goals = True

    return brief


def lint_brief(brief: BriefData, report: LintReport) -> None:
    f = brief.file

    # Advisory only — length proves nothing about any specific sentence, so this
    # never FAILs; it flags the re-narration pattern for the author to cut.
    if brief.size_bytes > BRIEF_SIZE_ADVISORY_BYTES:
        report.add(
            "WARN", f, "brief-oversize",
            f"brief is {brief.size_bytes:,} bytes; advisory max is "
            f"{BRIEF_SIZE_ADVISORY_BYTES:,}. Cut cross-section repetition and "
            "narration — each fact once, in the section that owns it; "
            "commitments and Measured-by checks stay.",
        )

    # Every Goal needs the check that answers "did this ship whole?". WARN, not
    # FAIL: a brief is prose and this reads it heuristically. The authoritative
    # gate is /brief-review-v2, which can tell a real domain from a plausible one.
    if not brief.goals:
        report.add("WARN", f, "goals-empty", "no Goals bullets found")
    for goal in brief.goals:
        if not re.search(r"\*\*Measured by:\*\*|Measured by:", goal):
            first = goal.splitlines()[0].strip()
            report.add(
                "WARN", f, "goal-no-measure",
                f"Goal has no `Measured by:` clause: {first!r}. Name the query, test, "
                "gate, or counted set that proves it shipped whole — without one, a "
                "subset delivery reviews clean.",
            )

    if brief.legacy_non_goals:
        report.add(
            "WARN", f, "scope-legacy-non-goals",
            "uses a bare `## Non-goals` section; the current shape is `## Scope` with "
            "four buckets (In scope / Intentionally deferred / Not in scope (this "
            "release) / Not planned). Read as `Not planned`; migrate on the next touch.",
        )
    elif not brief.scope_section_present:
        report.add("WARN", f, "scope-section-missing", "no `## Scope` or `## Non-goals` section")

    # A deferral with no destination is indistinguishable from a silent narrowing,
    # which is exactly what the bucket exists to make visible.
    for item in brief.deferred_items:
        if not DEFERRAL_DESTINATION_RE.search(item):
            first = item.splitlines()[0].strip()
            report.add(
                "FAIL", f, "deferral-no-destination",
                f"Intentionally-deferred item names no destination: {first!r}. Give it "
                "an issue (`#123`) or a follow-on feature slug — an undestined deferral "
                "is a silent narrowing. If you cannot name one, it belongs in "
                "`Not in scope (this release)` or `Not planned`.",
            )


# ---------------------------------------------------------------------------
# Per-chunk plan linting
# ---------------------------------------------------------------------------


@dataclass
class ChunkData:
    """Parsed structure for one chunk plan."""

    slug: str
    file: str
    stem_slug: str | None = None   # filename stem with any NN- creation-index prefix stripped
    in_impl_dir: bool = False      # True when the file lives in an implementation/ directory
    goal: str | None = None
    owns: list[str] = field(default_factory=list)
    reads: list[str] = field(default_factory=list)
    forbidden: list[str] = field(default_factory=list)
    single_concern: str | None = None
    no_scaffolding_present: bool = False
    abstraction_block_present: bool = False
    abstraction_consumers: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    # None -> the field is absent (a defect); [] -> declared `none` (valid).
    invariant_classes: list[str] | None = None
    kill_criteria: list[str] = field(default_factory=list)
    kill_criteria_section_present: bool = False


def parse_chunk_plan(path: Path, text: str) -> ChunkData:
    """Parse a per-chunk plan into structured data for linting."""
    text = strip_html_comments(text)
    # Slug is the chunk's stable identity: the first H1's backticked slug when
    # present, else the file basename (minus .md). A leading creation-index prefix
    # (NN-) on the filename is stripped first — it orders files for a glance, it is
    # not part of the slug.
    stem_slug = CREATION_INDEX_PREFIX_RE.sub("", path.stem, count=1)
    slug = stem_slug
    h1 = re.search(r"^#\s+Chunk:\s+`([^`]+)`", text, re.MULTILINE)
    if h1:
        slug = h1.group(1)

    chunk = ChunkData(
        slug=slug,
        file=str(path),
        stem_slug=stem_slug,
        in_impl_dir=path.parent.name == "implementation",
    )

    # Depends on (header line).
    deps_line = re.search(r"^\*\*Depends on:\*\*\s*(.+)$", text, re.MULTILINE)
    if deps_line:
        raw = deps_line.group(1)
        chunk.depends_on = [m.group(1) for m in re.finditer(r"`([^`]+)`", raw)]

    sections = split_sections(text, level=2)

    # Goal section.
    goal_body = find_section(sections, "Goal")
    if goal_body:
        # First non-empty, non-comment line.
        for ln in goal_body.strip().splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("<") and not ln.startswith(">"):
                chunk.goal = ln
                break

    # Factoring Contract section — bullet-extracted fields.
    fc_body = find_section(sections, "Factoring Contract")
    if fc_body:
        chunk.owns = _extract_field_paths(fc_body, "Owns")
        chunk.reads = _extract_field_paths(fc_body, "Reads")
        chunk.forbidden = _extract_field_paths(fc_body, "Forbidden")
        # Single concern blockquote — the first "> " line after the header.
        sc_match = re.search(
            r"\*\*Single concern\*\*.*?\n\n>\s*(.+?)(?:\n|$)", fc_body, re.DOTALL
        )
        if sc_match:
            chunk.single_concern = sc_match.group(1).strip()
        chunk.no_scaffolding_present = "No scaffolding" in fc_body
        chunk.abstraction_block_present = "Abstraction earns its place" in fc_body
        # If the abstraction block does NOT say "N/A", harvest declared
        # consumers from `Consumer N (already merged): ...` bullets.
        if chunk.abstraction_block_present and "N/A" not in fc_body:
            for m in re.finditer(r"Consumer\s+\d+\s*\([^)]*\):\s*`([^`]+)`", fc_body):
                chunk.abstraction_consumers.append(m.group(1))
        chunk.invariant_classes = _extract_invariant_classes(fc_body)

    # Acceptance criteria — checkbox bullets.
    ac_body = find_section(sections, "Acceptance criteria", "Verification", "Self-Verification")
    if ac_body:
        for m in re.finditer(r"^-\s*\[\s*[ xX]?\s*\]\s*(.+)$", ac_body, re.MULTILINE):
            chunk.acceptance_criteria.append(m.group(1).strip())

    # Kill criteria — checkbox bullets, same shape as acceptance criteria.
    kc_body = find_section(sections, "Kill criteria")
    if kc_body is not None:
        chunk.kill_criteria_section_present = True
        for m in re.finditer(r"^-\s*\[\s*[ xX]?\s*\]\s*(.+)$", kc_body, re.MULTILINE):
            item = m.group(1).strip()
            if not item.startswith("<"):  # skip unfilled template placeholders
                chunk.kill_criteria.append(item)

    return chunk


def _extract_invariant_classes(fc_body: str) -> list[str] | None:
    """Read the Factoring Contract's `Invariant classes touched` field.

    None means the field is absent — a defect, because silence and `none` are not
    the same claim. A declared `none` returns [].
    """
    m = re.search(
        r"\*\*Invariant classes touched\*\*(.+?)(?=\n\*\*[A-Z]|\Z)", fc_body, re.DOTALL
    )
    if not m:
        return None
    body = m.group(1)
    classes: list[str] = []
    for ln in body.splitlines():
        ln = ln.strip()
        if not ln.startswith("-"):
            continue
        token = re.search(r"`([^`]+)`", ln)
        value = (token.group(1) if token else ln.lstrip("- ").split("—")[0]).strip().lower()
        if not value or value.startswith("<"):
            continue
        if value == "none":
            return []
        classes.append(value)
    return classes


def _extract_field_paths(fc_body: str, field_name: str) -> list[str]:
    """Pull paths out of a Factoring Contract field (Owns / Reads / Forbidden)."""
    # Match: **Owns (writes)** ... up to the next **field** or end-of-section.
    pattern = re.compile(
        rf"\*\*{re.escape(field_name)}[^*]*\*\*(.+?)(?=\n\*\*[A-Z]|\Z)", re.DOTALL
    )
    m = pattern.search(fc_body)
    if not m:
        return []
    body = m.group(1)
    paths: list[str] = []
    for ln in body.splitlines():
        ln = ln.strip()
        if not ln.startswith("-"):
            continue
        paths.extend(extract_paths_from_cell(ln))
    return paths


def lint_chunk_plan(chunk: ChunkData, report: LintReport) -> None:
    """Run all per-chunk lint rules."""
    f = chunk.file

    # Slug shape.
    if not SLUG_RE.match(chunk.slug):
        report.add("FAIL", f, "slug-shape", f"slug `{chunk.slug}` is not kebab-case 2–4 words")
    for pat in FORBIDDEN_SLUG_PATTERNS:
        if pat.search(chunk.slug):
            report.add(
                "FAIL", f, "slug-position-encoded",
                f"slug `{chunk.slug}` encodes position-in-graph (matches /{pat.pattern}/); "
                "rename after the work it does",
            )

    # The filename's slug-part (after stripping the NN- creation-index prefix) must
    # match the slug identity. A mismatch means the file is misnamed and will not
    # resolve when a sister skill globs `*-<slug>.md`. (Suppressed for ad-hoc files
    # outside an implementation/ directory, whose stem is not expected to be a slug.)
    if chunk.in_impl_dir and chunk.stem_slug and chunk.stem_slug != chunk.slug:
        report.add(
            "WARN", f, "slug-filename-mismatch",
            f"filename slug-part `{chunk.stem_slug}` does not match the chunk slug "
            f"`{chunk.slug}` (from the H1); rename the file to `<NN>-{chunk.slug}.md`",
        )

    # Goal must exist and not contain " and ".
    if not chunk.goal:
        report.add("FAIL", f, "goal-missing", "no Goal section content found")
    elif re.search(r"\band\b", chunk.goal, re.IGNORECASE):
        report.add(
            "FAIL", f, "goal-and",
            f"Goal contains ' and ' — split into two chunks: {chunk.goal!r}",
        )

    # Factoring Contract checks.
    if not chunk.owns:
        report.add("FAIL", f, "owns-empty", "Factoring Contract missing or has empty Owns set")
    if not chunk.single_concern:
        report.add("FAIL", f, "single-concern-missing", "Factoring Contract missing Single concern blockquote")
    elif re.search(r"\band\b", chunk.single_concern, re.IGNORECASE):
        report.add(
            "FAIL", f, "single-concern-and",
            f"Single concern contains ' and ' — split the chunk: {chunk.single_concern!r}",
        )
    if not chunk.no_scaffolding_present:
        report.add("FAIL", f, "no-scaffolding-missing", "Factoring Contract missing No scaffolding assertion")
    if not chunk.abstraction_block_present:
        report.add(
            "FAIL", f, "abstraction-block-missing",
            "Factoring Contract missing Abstraction earns its place block (use 'N/A' if no new abstraction)",
        )
    elif chunk.abstraction_consumers and len(chunk.abstraction_consumers) < 2:
        report.add(
            "FAIL", f, "abstraction-too-few-consumers",
            f"Abstraction declared with only {len(chunk.abstraction_consumers)} consumer; "
            "need ≥2 already-merged consumers, or defer the abstraction",
        )

    # Acceptance criteria — each item must contain a measurable predicate.
    if not chunk.acceptance_criteria:
        report.add("FAIL", f, "ac-empty", "Acceptance criteria section is empty")
    for item in chunk.acceptance_criteria:
        # Strip checkbox prefix already done; check vague verbs.
        lower = item.lower()
        for verb in VAGUE_VERBS:
            if re.search(rf"\b{verb}\b", lower) and not MEASURABLE_TOKENS.search(item):
                report.add(
                    "FAIL", f, "ac-vague",
                    f"acceptance criterion uses vague verb '{verb}' with no measurable predicate: {item!r}",
                )
                break

    # A chunk plan carrying NEITHER new-convention field predates the convention.
    # Warn once and skip both rules — the alternative is failing every plan written
    # before the template changed, which trains you to ignore the lint. A plan
    # carrying one of the two is new-shape, and the missing one is a real defect.
    legacy_shape = (
        not chunk.kill_criteria_section_present and chunk.invariant_classes is None
    )
    if legacy_shape:
        report.add(
            "WARN", f, "chunk-plan-legacy-shape",
            "neither `Kill criteria` nor `Invariant classes touched` is present. Both "
            "are required. A chunk plan carrying neither warns rather than failing, and "
            "both field rules are skipped; migrate on the next touch — see "
            "features/README.md § Migrating older features.",
        )

    # Kill criteria — the pre-stated conditions under which the chunk stops and
    # returns to planning. Acceptance criteria say when it is done; these say when
    # it was wrong, and they only work if written before sunk cost accumulates.
    if legacy_shape:
        pass
    elif not chunk.kill_criteria_section_present:
        report.add(
            "FAIL", f, "kill-criteria-missing",
            "no Kill criteria section — state at least one falsifiable condition "
            "under which this chunk stops and returns to planning",
        )
    elif not chunk.kill_criteria:
        report.add(
            "FAIL", f, "kill-criteria-empty",
            "Kill criteria section has no filled-in items",
        )
    else:
        for item in chunk.kill_criteria:
            if not MEASURABLE_TOKENS.search(item):
                report.add(
                    "FAIL", f, "kill-criteria-vague",
                    f"kill criterion names no checkable condition: {item!r}. It must be "
                    "falsifiable before the chunk is half-built — a threshold, a named "
                    "test, a gate, a command.",
                )

    _lint_chunk_budget(chunk, report, legacy_shape=legacy_shape)


def _lint_chunk_budget(
    chunk: ChunkData, report: LintReport, legacy_shape: bool = False
) -> None:
    """Review-complexity budget: files, subsystems crossed, invariant classes.

    Files and subsystems are computed from the Factoring Contract's Owns set;
    invariant classes are declared, because touching a file in an auth directory
    is not the same claim as changing an auth invariant.

    Subsystems and invariant classes have no exemption path. Their overflows are
    correctness signals, not capacity ones: crossing four subsystems means the
    chunk carries a cross-layer contract the engineering plan never wrote down,
    and carrying three invariant classes means it is about to introduce a
    cross-domain interaction nobody enumerated.
    """
    f = chunk.file
    config = load_config(Path(chunk.file).resolve().parent)
    if config is None:
        return  # No project config — the budget is not this lint's to guess at.

    budget = config.get("budget", {})
    known_classes = {c.lower() for c in config.get("invariant_classes", [])}
    # A chunk written before the budget existed cannot be re-split — it may already
    # be merged. Report the overflow so the number is visible, but the cap only
    # binds on plans authored under the convention.
    cap_severity = "WARN" if legacy_shape else "FAIL"

    # --- Invariant classes (declared) ---
    if chunk.invariant_classes is None:
        if not legacy_shape:
            report.add(
                "FAIL", f, "invariant-classes-missing",
                "Factoring Contract has no `Invariant classes touched` field. `none` is "
                "a valid answer; silence is not — it makes the no-exemption cap "
                "uncheckable.",
            )
    else:
        unknown = [c for c in chunk.invariant_classes if c not in known_classes]
        if unknown:
            report.add(
                "FAIL", f, "invariant-class-unknown",
                f"declares invariant class(es) not in features/{CONFIG_FILENAME}: "
                f"{unknown}. Known: {sorted(known_classes)}.",
            )
        n = len(chunk.invariant_classes)
        cap = budget.get("invariant_classes_cap")
        target = budget.get("invariant_classes_target")
        if cap is not None and n > cap:
            report.add(
                cap_severity, f, "invariant-classes-over-cap",
                f"{n} invariant classes touched, cap is {cap}. No exemption exists on "
                "this axis — split the chunk. Carrying this many means a cross-domain "
                "interaction the engineering plan did not enumerate.",
            )
        elif target is not None and n > target:
            report.add(
                "WARN", f, "invariant-classes-over-target",
                f"{n} invariant classes touched, target is {target}. One class per chunk "
                "keeps the blast radius reviewable.",
            )

    # --- Files and subsystems (computed from Owns) ---
    if not chunk.owns:
        return
    weighted, touched, unclassified = classify_paths(chunk.owns, config)

    if unclassified:
        report.add(
            "WARN", f, "owns-path-unclassified",
            f"{len(unclassified)} Owns path(s) match no subsystem glob and no weight "
            f"rule: {unclassified[:3]}. Either the path is wrong or "
            f"features/{CONFIG_FILENAME} needs the subsystem.",
        )

    files_cap, files_target = budget.get("files_cap"), budget.get("files_target")
    if files_cap is not None and weighted > files_cap:
        report.add(
            cap_severity, f, "budget-files-over-cap",
            f"Owns weighs {weighted:g} files (cap {files_cap}); docs count 0 and tests "
            "count 0.5. Split the chunk, or move a concern into its own slug.",
        )
    elif files_target is not None and weighted > files_target:
        report.add(
            "WARN", f, "budget-files-over-target",
            f"Owns weighs {weighted:g} files (target {files_target}). Reviewable in one "
            "sitting is the bar; check whether a second concern crept in.",
        )

    subs_cap, subs_target = budget.get("subsystems_cap"), budget.get("subsystems_target")
    if subs_cap is not None and len(touched) > subs_cap:
        report.add(
            cap_severity, f, "budget-subsystems-over-cap",
            f"crosses {len(touched)} subsystems (cap {subs_cap}): {sorted(touched)}. "
            "No exemption exists on this axis — the chunk must split. Crossing this "
            "many is a sign it carries an undocumented cross-layer contract.",
        )
    elif subs_target is not None and len(touched) > subs_target:
        report.add(
            "WARN", f, "budget-subsystems-over-target",
            f"crosses {len(touched)} subsystems (target {subs_target}): {sorted(touched)}.",
        )


# ---------------------------------------------------------------------------
# Engineering-plan linting
# ---------------------------------------------------------------------------


@dataclass
class EngineeringPlanData:
    file: str
    chunk_index: list[tuple[str, str, list[str]]] = field(default_factory=list)  # (slug, name, deps)
    decisions_present: bool = False
    decisions_unresolved: list[str] = field(default_factory=list)
    brief_mapping_present: bool = False
    goals_has_verified_by: bool = False
    non_goals_has_kind: bool = False
    # Chunk intent. `chunk_intents` maps slug -> lowercased label; the column is
    # absent on plans written before the convention, which is a legacy WARN.
    intent_column_present: bool = False
    chunk_intents: dict[str, str] = field(default_factory=dict)
    # Invariants and Threat model: both required sections, both permitted to carry
    # an explicit disclaimer instead of content.
    invariants_present: bool = False
    invariants_disclaimer: bool = False
    invariant_entries: list[tuple[str, str | None, str | None]] = field(default_factory=list)
    threat_model_present: bool = False
    threat_model_disclaimer: bool = False
    threat_model_rows: int = 0
    threat_model_cites_invariants: bool = False
    # Drift checks. Each targets a defect class that only surfaced after several
    # LLM review rounds had already passed the plan; all four are mechanical, so
    # they belong on the deterministic floor rather than in reviewer judgment.
    decisions_has_bound_chunks_column: bool = False
    decisions_rows: int = 0
    decisions_rows_naming_chunks: int = 0
    decisions_rows_citing_log: int = 0
    decisions_citations: list[str] = field(default_factory=list)  # dates cited from decisions.md
    count_claims: list[tuple[str, int, str]] = field(default_factory=list)  # (phrase, n, kind)
    section_words: dict[str, int] = field(default_factory=dict)
    lineage_mentions: list[str] = field(default_factory=list)


NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}

# "this plan's four chunks" / "its four chunks" -> must equal the chunk-index row count.
CHUNK_COUNT_TOTAL_RE = re.compile(
    r"(?:this plan's|the plan's|its|all)\s+(" + "|".join(NUMBER_WORDS) + r"|\d+)\s+chunks?\b",
    re.IGNORECASE,
)
# "the other three chunks" -> must equal the row count minus one.
CHUNK_COUNT_OTHER_RE = re.compile(
    r"the other\s+(" + "|".join(NUMBER_WORDS) + r"|\d+)\s+chunks?\b", re.IGNORECASE
)
# A decisions.md citation carrying a date: `decisions.md`) 2026-07-30 ...
DECISIONS_CITE_RE = re.compile(r"decisions\.md[^)\n]*\)\s*(\d{4}-\d{2}(?:-\d{2})?)")
# Round-N narration NOT attached to a decisions.md citation (template bans lineage
# in the plan body; a citation to a bound entry is legitimate and is excluded).
LINEAGE_RE = re.compile(r"\bround[- ]\d+\b", re.IGNORECASE)


def _number(token: str) -> int | None:
    token = token.strip().lower()
    if token.isdigit():
        return int(token)
    return NUMBER_WORDS.get(token)


def _find_decisions_log(plan_file: str) -> Path | None:
    """decisions.md is feature-level: plan-root (flat) or two levels up (tracked)."""
    p = Path(plan_file).parent
    for candidate in (p / "decisions.md", p.parent / "decisions.md", p.parent.parent / "decisions.md"):
        if candidate.is_file():
            return candidate
    return None


def _active_decision_dates(log: Path) -> set[str]:
    """Dates of `## <date> — ...` headings in the Active (bound) section only."""
    text = read_text(log)
    active = text.split("## Archived")[0]
    dates: set[str] = set()
    for line in active.splitlines():
        m = re.match(r"##\s+(\d{4}-\d{2}(?:-\d{2})?)", line)
        if m:
            dates.add(m.group(1))
    return dates


# Chunk-index name/description of the dedicated acceptance chunk (the contract-
# verification DAG sink). Heuristic, used only for a WARN — the authoritative
# Goal-verification gate lives in /engineering-plan-author and -review-v2, which
# read the brief. Kept broad so a reasonably-named acceptance chunk matches.
ACCEPTANCE_CHUNK_RE = re.compile(
    r"accept|verif|conformance|prove.*(goal|brief|contract)", re.IGNORECASE
)


def parse_engineering_plan(path: Path, text: str) -> EngineeringPlanData:
    plan = EngineeringPlanData(file=str(path))
    text = strip_html_comments(text)
    sections = split_sections(text, level=2)

    # Chunk index table. Columns are Slug | Chunk | Intent | Code deps; plans
    # written before the Intent convention have three columns, and the deps cell
    # is then wherever the header says it is rather than at a fixed offset.
    ci_body = find_section(sections, "Chunk index")
    if ci_body:
        rows = extract_table(ci_body)
        if rows and len(rows) > 1:
            header = [c.strip().lower() for c in rows[0]]
            intent_col = next((i for i, c in enumerate(header) if "intent" in c), None)
            deps_col = next(
                (i for i, c in enumerate(header) if "dep" in c),
                3 if intent_col is not None else 2,
            )
            plan.intent_column_present = intent_col is not None
            for row in rows[1:]:
                if len(row) < 2:
                    continue
                slug_cell, name_cell = row[0], row[1]
                deps_cell = row[deps_col] if len(row) > deps_col else ""
                slug_match = re.search(r"`([^`]+)`", slug_cell)
                if not slug_match:
                    continue
                slug = slug_match.group(1)
                deps = [m.group(1) for m in re.finditer(r"`([^`]+)`", deps_cell)]
                plan.chunk_index.append((slug, name_cell.strip(), deps))
                if intent_col is not None and len(row) > intent_col:
                    plan.chunk_intents[slug] = row[intent_col].strip().strip("`*").lower()

    # Brief mapping: presence of the Goal-verification columns (Goals `Verified by`,
    # Non-goals `Kind`). Structural only — coverage-vs-brief is the review's job.
    bm_body = find_section(sections, "Brief mapping")
    if bm_body:
        plan.brief_mapping_present = True
        subs = split_sections(bm_body, level=3)
        goals_body = find_section(subs, "Goals")
        if goals_body:
            grows = extract_table(goals_body)
            if grows:
                header = " ".join(grows[0]).lower()
                plan.goals_has_verified_by = "verified by" in header
        ng_body = find_section(subs, "Scope enforcement", "Non-goals enforcement", "Non-goals")
        if ng_body:
            ngrows = extract_table(ng_body)
            if ngrows:
                header = " ".join(ngrows[0]).lower()
                plan.non_goals_has_kind = "kind" in header

    # Invariants — required section, disclaimer permitted in place of content.
    inv_body = find_section(sections, "Invariants")
    if inv_body is not None:
        plan.invariants_present = True
        plan.invariants_disclaimer = bool(
            re.search(r"no cross-chunk invariants", inv_body, re.IGNORECASE)
        )
        for name, body in split_sections(inv_body, level=3).items():
            if name.startswith("<"):
                continue  # unfilled template placeholder
            form = re.search(r"\*\*Form:\*\*\s*(.+)", body)
            fals = re.search(r"\*\*Falsifier:\*\*\s*(.+)", body)
            plan.invariant_entries.append(
                (
                    name,
                    form.group(1).strip() if form else None,
                    fals.group(1).strip() if fals else None,
                )
            )

    # Threat model — required section, disclaimer permitted in place of content.
    tm_body = find_section(sections, "Threat model")
    if tm_body is not None:
        plan.threat_model_present = True
        plan.threat_model_disclaimer = bool(
            re.search(r"no threat[- ]model surface", tm_body, re.IGNORECASE)
        )
        tm_rows = extract_table(tm_body)
        filled = [
            r for r in tm_rows[1:]
            if r and not r[0].strip().startswith("<") and r[0].strip() not in ("", "—", "-")
        ]
        plan.threat_model_rows = len(filled)
        plan.threat_model_cites_invariants = bool(
            re.search(r"\bINV[- ]?\d|invariant", tm_body, re.IGNORECASE)
        )

    # Decisions closure.
    dc_body = find_section(sections, "Decisions closure")
    if dc_body:
        plan.decisions_present = True
        rows = extract_table(dc_body)
        if rows and len(rows) > 1:
            header = " ".join(rows[0]).lower()
            plan.decisions_has_bound_chunks_column = (
                "chunks bound" in header or "bound by" in header or "owned by" in header
            )
            for row in rows[1:]:
                if len(row) < 2:
                    continue
                resolution = row[1].strip().lower()
                if "tbd" in resolution or "figure out" in resolution or resolution in ("", "—", "-"):
                    plan.decisions_unresolved.append(row[0].strip())
                plan.decisions_rows += 1
                # Older plans carry no bound-chunks column and instead name the
                # bound slugs inline in the resolution prose. Less scannable, same
                # information — track it so the check can tell "stated differently"
                # from "not stated".
                rest = " ".join(row[1:])
                if any(SLUG_RE.match(m.group(1)) for m in re.finditer(r"`([^`]+)`", rest)):
                    plan.decisions_rows_naming_chunks += 1
                # A third shape delegates entirely: Decision | Status | Citation,
                # with the resolution and its bound chunks living in decisions.md.
                # The sweep list is reachable, one hop away.
                if "decisions.md" in rest:
                    plan.decisions_rows_citing_log += 1

    # --- Drift checks over the whole body ---
    plan.decisions_citations = DECISIONS_CITE_RE.findall(text)

    for m in CHUNK_COUNT_TOTAL_RE.finditer(text):
        n = _number(m.group(1))
        if n is not None:
            plan.count_claims.append((m.group(0), n, "total"))
    for m in CHUNK_COUNT_OTHER_RE.finditer(text):
        n = _number(m.group(1))
        if n is not None:
            plan.count_claims.append((m.group(0), n, "other"))

    for name, body in sections.items():
        plan.section_words[name] = len(body.split())

    # A line that cites decisions.md is a citation line; its round-N tokens are
    # legitimate references, not narration. Only unattached mentions count.
    for line in text.splitlines():
        if "decisions.md" in line:
            continue
        for m in LINEAGE_RE.finditer(line):
            plan.lineage_mentions.append(line[max(0, m.start() - 60):m.end()].strip())

    return plan


def lint_engineering_plan(plan: EngineeringPlanData, report: LintReport) -> None:
    f = plan.file
    if not plan.chunk_index:
        report.add("FAIL", f, "chunk-index-missing", "no Chunk index table found")
        return

    chunk_slugs = [s for s, _, _ in plan.chunk_index]

    # Slug shape.
    for slug in chunk_slugs:
        if not SLUG_RE.match(slug):
            report.add("FAIL", f, "slug-shape", f"slug `{slug}` is not kebab-case 2–4 words")
        for pat in FORBIDDEN_SLUG_PATTERNS:
            if pat.search(slug):
                report.add(
                    "FAIL", f, "slug-position-encoded",
                    f"slug `{slug}` encodes position-in-graph (matches /{pat.pattern}/)",
                )

    # Decisions closure.
    if not plan.decisions_present:
        report.add(
            "WARN", f, "decisions-closure-missing",
            "no Decisions closure section — confirm there are no cross-chunk decisions to bind",
        )
    for dec in plan.decisions_unresolved:
        report.add(
            "FAIL", f, "decision-unresolved",
            f"decision left unresolved at engineering-plan level: {dec!r}",
        )

    # Dependency graph: cycle detection (Kahn's algorithm) over chunk index deps.
    deps_map = {slug: set(deps) for slug, _, deps in plan.chunk_index}
    in_degree = {slug: 0 for slug in chunk_slugs}
    edges: dict[str, set[str]] = defaultdict(set)
    for slug, deps in deps_map.items():
        for dep in deps:
            if dep not in deps_map:
                report.add(
                    "FAIL", f, "dep-unknown",
                    f"chunk `{slug}` depends on unknown slug `{dep}` (not in Chunk index)",
                )
                continue
            edges[dep].add(slug)
            in_degree[slug] += 1

    queue = [s for s in chunk_slugs if in_degree[s] == 0]
    visited: list[str] = []
    while queue:
        s = queue.pop(0)
        visited.append(s)
        for nxt in edges[s]:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)
    if len(visited) != len(chunk_slugs):
        cyclic = [s for s in chunk_slugs if s not in visited]
        report.add(
            "FAIL", f, "dep-cycle",
            f"dependency graph has a cycle involving: {cyclic}",
        )

    # Goal-verification structural floor (WARN only — the authoritative gate that
    # checks coverage against the brief lives in /engineering-plan-author and
    # /engineering-plan-review-v2, which read brief.md; plan-lint has no brief).
    if plan.brief_mapping_present and not plan.goals_has_verified_by:
        report.add(
            "WARN", f, "goals-verified-by-missing",
            "Brief mapping → Goals table has no `Verified by` column; every Goal "
            "needs an acceptance proof (or `Manual review — <reason>`). "
            "See GOAL_VERIFICATION_GAP.",
        )
    if plan.brief_mapping_present and not plan.non_goals_has_kind:
        report.add(
            "WARN", f, "non-goals-kind-missing",
            "Brief mapping → Scope enforcement table has no `Kind` column "
            "(testable-absence | scope-boundary | deferred-tracked); testable scope "
            "items need an assert-absence test. See GOAL_VERIFICATION_GAP.",
        )

    _lint_chunk_intents(plan, edges, report)
    _lint_invariants(plan, report)
    _lint_threat_model(plan, report)
    # Dedicated acceptance chunk: a DAG sink whose concern is the contract-level
    # acceptance suite. `edges[s]` holds the chunks that depend on `s`, so a sink
    # is a chunk nothing depends on.
    acceptance_candidates = [
        s for s, name, _ in plan.chunk_index
        if ACCEPTANCE_CHUNK_RE.search(name) or ACCEPTANCE_CHUNK_RE.search(s)
    ]
    if not acceptance_candidates:
        report.add(
            "WARN", f, "acceptance-chunk-missing",
            "no dedicated acceptance chunk found in the Chunk index (a DAG sink "
            "whose concern is proving brief Goals honored / testable Non-goals "
            "excluded). See GOAL_VERIFICATION_GAP.",
        )
    elif not any(len(edges[s]) == 0 for s in acceptance_candidates):
        report.add(
            "WARN", f, "acceptance-chunk-not-sink",
            f"acceptance chunk(s) {acceptance_candidates} are depended on by other "
            "chunks; the acceptance suite must be a DAG sink that runs against the "
            "assembled feature.",
        )

    # --- Drift checks ------------------------------------------------------
    # Each of these fired on a plan that had already passed multiple LLM review
    # rounds. They are mechanical, so they belong here rather than in judgment.

    # 1. Every decisions.md citation must resolve to a heading that exists.
    #    A citation to a nonexistent entry means an arbitration was never recorded,
    #    which no carry-forward rule can retract — so it re-litigates every round.
    if plan.decisions_citations:
        log = _find_decisions_log(f)
        if log is None:
            report.add(
                "WARN", f, "decisions-log-missing",
                f"plan makes {len(plan.decisions_citations)} dated `decisions.md` "
                "citation(s) but no decisions.md was found at the feature root.",
            )
        else:
            known = _active_decision_dates(log)
            unresolved = sorted({d for d in plan.decisions_citations if d not in known})
            if unresolved:
                report.add(
                    "FAIL", f, "decisions-citation-unresolved",
                    f"cites decisions.md entries that do not exist in its Active "
                    f"(bound) section: {', '.join(unresolved)}. Write the entry, or "
                    "correct the citation — an unrecorded arbitration cannot be "
                    "honored by carry-forward and will be re-prosecuted every round.",
                )

    # 2. Count claims about the plan's own chunks must match the chunk index.
    n_chunks = len(plan.chunk_index)
    for phrase, claimed, kind in plan.count_claims:
        expected = n_chunks if kind == "total" else n_chunks - 1
        if claimed != expected:
            report.add(
                "FAIL", f, "count-claim-drift",
                f'"{phrase.strip()}" claims {claimed} but the Chunk index has '
                f"{n_chunks} rows (expected {expected}). A count restated in prose "
                "goes stale the moment a chunk is added.",
            )

    # 3. Decisions closure must carry the bound-chunks column — it is the sweep
    #    list for any later amendment, and its absence is why remediation misses
    #    coupled sites.
    if plan.decisions_present and not plan.decisions_has_bound_chunks_column:
        # The column exists so a later amendment can find what to re-sweep. A plan
        # that names the bound slugs inline in every resolution serves that purpose
        # already, just less scannably — that is a migration, not a defect.
        # Any substantial inline use answers the question "is this plan on the old
        # convention?". Demanding every row name a slug would fail a plan for one
        # decision whose resolution genuinely binds no chunk.
        stated_inline = (
            plan.decisions_rows_naming_chunks > 0
            or plan.decisions_rows_citing_log > 0
        )
        report.add(
            "WARN" if stated_inline else "FAIL",
            f, "decisions-closure-missing-bound-chunks",
            "Decisions closure table has no `Chunks bound by it` column. That column "
            "is what tells a later amendment which chunks must be re-swept; without "
            "it, a decision changes and nothing names what else must change."
            + (
                " Every resolution names its bound chunks inline, so the information "
                "is present — move it to a column on the next touch."
                if stated_inline
                else ""
            ),
        )

    # 4. Round-N narration in the plan body (template bans lineage here; a
    #    citation attached to a decisions.md reference is exempt and not counted).
    if len(plan.lineage_mentions) > 3:
        sample = "; ".join(plan.lineage_mentions[:3])
        report.add(
            "WARN", f, "round-lineage-in-body",
            f"{len(plan.lineage_mentions)} round-N narration mention(s) not attached "
            f"to a decisions.md citation (e.g. {sample}). Lineage belongs in "
            "decisions.md; the plan states what is bound, not how it got there.",
        )

    # 5. Section mass — a section far larger than its peers is where restatement
    #    accumulates, and restatement is what drifts.
    total = sum(plan.section_words.values())
    if total > 2000:
        for name, words in sorted(plan.section_words.items(), key=lambda kv: -kv[1])[:1]:
            share = words / total
            if share > 0.15:
                report.add(
                    "WARN", f, "section-mass-outlier",
                    f'section "{name}" is {words:,} words, {share:.0%} of the plan. '
                    "Check it is not restating a fact another section or decisions.md "
                    "already owns — that is where drift accumulates.",
                )


def _lint_chunk_intents(
    plan: EngineeringPlanData, edges: dict[str, set[str]], report: LintReport
) -> None:
    """Chunk intent labels, and the structural obligation Foundation carries."""
    f = plan.file
    if not plan.intent_column_present:
        report.add(
            "WARN", f, "chunk-intent-column-missing",
            "Chunk index has no `Intent` column. It is required — one of Foundation | "
            "Behavior | Hardening | Migration per chunk. A plan without the column "
            "warns rather than failing, and every other intent rule is skipped; "
            "migrate on the next touch.",
        )
        return

    for slug, intent in plan.chunk_intents.items():
        if intent not in CHUNK_INTENTS:
            report.add(
                "FAIL", f, "chunk-intent-invalid",
                f"chunk `{slug}` has intent {intent!r}; must be one of "
                f"{sorted(CHUNK_INTENTS)}.",
            )
            continue
        # A Foundation chunk changes no behavior, so its only justification is a
        # later chunk consuming it. Nothing depending on it means it ships dead
        # code — the Factoring Contract's No-scaffolding rule, one layer up.
        if intent == "foundation" and not edges.get(slug):
            report.add(
                "FAIL", f, "foundation-chunk-orphaned",
                f"chunk `{slug}` is Foundation but no other chunk depends on it. "
                "Foundation changes no behavior, so with no consumer it ships dead "
                "scaffolding — fold it into the chunk that consumes it, or relabel.",
            )


def _lint_invariants(plan: EngineeringPlanData, report: LintReport) -> None:
    """Invariants: required section, Form and Falsifier on every entry."""
    f = plan.file
    if not plan.invariants_present:
        report.add(
            "WARN", f, "invariants-section-missing",
            "no `## Invariants` section. It is required — state the cross-chunk rules, "
            "or write `No cross-chunk invariants — <reason>.` Plans predating the "
            "convention warn here; migrate on the next touch.",
        )
        return

    if not plan.invariant_entries and not plan.invariants_disclaimer:
        report.add(
            "FAIL", f, "invariants-empty",
            "`## Invariants` has neither an invariant nor the disclaimer. Write the "
            "invariants, or `No cross-chunk invariants — <reason>.` — an empty section "
            "and a missing one read identically, and neither is an answer.",
        )
        return

    config = load_config(Path(f).resolve().parent) or {}
    high_risk = {c.lower() for c in config.get("invariant_classes", [])}

    # An Invariants section where NO entry carries either field predates the
    # convention. Warn once rather than failing every entry — a plan authored under
    # the convention has at least one, and a missing field there is a real defect.
    if plan.invariant_entries and not any(
        form or falsifier for _, form, falsifier in plan.invariant_entries
    ):
        report.add(
            "WARN", f, "invariants-legacy-shape",
            f"{len(plan.invariant_entries)} invariant(s), none carrying **Form:** or "
            "**Falsifier:**. Both are required on every invariant. A section where no "
            "entry carries either warns rather than failing, and the per-entry rules "
            "are skipped; migrate on the next touch.",
        )
        return

    for name, form, falsifier in plan.invariant_entries:
        if form is None:
            report.add(
                "FAIL", f, "invariant-form-missing",
                f'invariant "{name}" has no **Form:** line (test | assert | gate | doc).',
            )
        elif form.split()[0].lower().strip("`") not in INVARIANT_FORMS:
            report.add(
                "FAIL", f, "invariant-form-invalid",
                f'invariant "{name}" has Form {form!r}; must be one of '
                f"{sorted(INVARIANT_FORMS)}.",
            )
        elif form.split()[0].lower().strip("`") == "doc" and any(
            cls in name.lower() or cls.replace("-", " ") in name.lower() for cls in high_risk
        ):
            report.add(
                "WARN", f, "invariant-doc-only-high-risk",
                f'invariant "{name}" is enforced by doc alone but names a high-risk '
                "class. A doc-form invariant in auth, score math, or data integrity is "
                "unenforced by construction — give it a test, assert, or gate.",
            )
        if falsifier is None:
            report.add(
                "FAIL", f, "invariant-falsifier-missing",
                f'invariant "{name}" has no **Falsifier:** line. Without the one check '
                "that would disprove it, what is written is prose, not a rule.",
            )

    # A populated threat model whose detections reference invariants contradicts a
    # claim that the feature has none.
    if (
        plan.invariants_disclaimer
        and not plan.invariant_entries
        and plan.threat_model_rows > 0
        and plan.threat_model_cites_invariants
    ):
        report.add(
            "FAIL", f, "invariants-disclaimer-contradicted",
            "declares `No cross-chunk invariants` while the Threat model names "
            f"{plan.threat_model_rows} threat(s) whose detection cites invariants. One "
            "of the two is wrong: either write the invariants the detections rely on, "
            "or drop the citation.",
        )


def _lint_threat_model(plan: EngineeringPlanData, report: LintReport) -> None:
    """Threat model: required section, populated or explicitly disclaimed.

    Which surfaces trigger population is judgment, so it belongs to
    /engineering-plan-review-v2. The mechanical part is that the decision was
    articulated at all.
    """
    f = plan.file
    if not plan.threat_model_present:
        report.add(
            "WARN", f, "threat-model-section-missing",
            "no `## Threat model` section. It is required — populate it for auth, "
            "session, block/follow, user-data writes, the score-lock boundary, "
            "external-data ingestion, or LLM-mediated paths; otherwise write "
            "`No threat-model surface — <reason>.`",
        )
        return
    if plan.threat_model_rows == 0 and not plan.threat_model_disclaimer:
        report.add(
            "FAIL", f, "threat-model-empty",
            "`## Threat model` is present but has neither a populated row nor the "
            "disclaimer. State `No threat-model surface — <reason>.` if that is the "
            "answer — the articulated decision is the deliverable.",
        )


# ---------------------------------------------------------------------------
# Cross-plan checks (engineering plan vs per-chunk plans)
# ---------------------------------------------------------------------------


def lint_cross_plan(
    eplan: EngineeringPlanData, chunks: list[ChunkData], report: LintReport
) -> None:
    """Cross-checks: chunk plans against the engineering plan's chunk index."""
    f = eplan.file
    chunk_by_slug = {c.slug: c for c in chunks}
    indexed_slugs = {s for s, _, _ in eplan.chunk_index}

    # Every indexed slug should have a per-chunk plan once the chunk is being
    # written (we just warn — chunk plans are written just-in-time, not upfront).
    # Sorted, because a set's iteration order varies run to run and a lint that
    # advertises determinism should not reorder its own output.
    for slug in sorted(indexed_slugs):
        if slug not in chunk_by_slug:
            report.add(
                "WARN", f, "chunk-plan-missing",
                f"engineering plan lists `{slug}` but no implementation/<slug>.md exists yet",
            )


# ---------------------------------------------------------------------------
# Decomposition helpers (shared by the vision and spec document types)
# ---------------------------------------------------------------------------

# Both layers carve their decomposition into the document it decomposes: vision
# carries the spec map, a spec carries `## Decomposition`. The parsing below is
# shared because the two shapes are the same shape one layer apart — named
# entries, a split-line predicate per seam, and a coverage claim that has to be
# falsifiable. See ~/.claude/skills/_decompose-common/decomposition-principles.md.


def normalize_heading(title: str) -> str:
    """Strip a section number, decoration, and case off a heading title."""
    return NUMBERED_HEADING_RE.sub("", title.strip()).strip().strip("`*_ ").lower()


def _bold_field(body: str, label: str) -> str | None:
    """Pull a `**Label**` / `**Label:**` field body out of an entry block.

    None means the label is absent; "" means present with nothing under it. The
    two are different claims, exactly as they are in the Factoring Contract.
    """
    # The field ends at the next field label, and a label is capitalized. The
    # case-insensitivity is for the label being looked up, so the terminator's
    # `[A-Z]` opts out of it explicitly — under the outer flag it would also match
    # a lowercase bold emphasis mid-paragraph and truncate the field there.
    pattern = re.compile(
        rf"\*\*{re.escape(label)}\*\*\s*:?\s*(.*?)"
        rf"(?=\n\s*(?:[-*+]\s+)?\*\*(?-i:[A-Z])|\n#{{1,6}}\s|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    m = pattern.search(body)
    if not m:
        return None
    # Drop the separator glyph a one-line field opens with (`**Owns** — text`).
    # An ASCII hyphen is left alone: on a multi-line field it is the first
    # bullet's marker, and stripping it would hide that bullet from every
    # per-bullet rule below.
    return re.sub(r"^[—–:]\s*", "", m.group(1).strip()).strip()


def _backticked(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"`([^`]+)`", text)]


# The empty-dependency sentinel, backticked or bare. Both formats' own templates
# write it both ways — the vision entry writes `none`, the Briefs table writes —
# and the slug-backticking rule puts ticks around the word wherever it appears.
DEPS_SENTINEL_RE = re.compile(r"[—–\-]|none|n/?a", re.IGNORECASE)
# A parenthetical says what the dependency is FOR, and an em-dash clause carries
# the reverse-edge assumption. Both routinely name a third slug that is not itself
# a dependency, so the edges come from the list and not from the commentary.
DEPS_PARENTHETICAL_RE = re.compile(r"\([^()]*\)")
DEPS_TRAILING_CLAUSE_RE = re.compile(r"\s[—–]\s")


def _slug_list(text: str | None) -> list[str]:
    """Slugs named in a `Depends on` field. `—` / `none` reads as no edges."""
    if not text:
        return []
    body = text.strip()
    if DEPS_SENTINEL_RE.fullmatch(body) or DEPS_SENTINEL_RE.fullmatch(body.strip("`").strip()):
        return []
    body = DEPS_PARENTHETICAL_RE.sub(" ", body)
    body = DEPS_TRAILING_CLAUSE_RE.split(body, maxsplit=1)[0]
    return [s for s in _backticked(body) if DECOMP_SLUG_RE.match(s)]


def scan_status_tokens(
    body: str,
    extra: re.Pattern | None = None,
    date_mask: "Callable[[str], str] | None" = None,
) -> list[tuple[str, str]]:
    """Return (token, line) for every lifecycle token in a decomposition section.

    One hit per line at most — a status-heavy paragraph should read as one defect
    per sentence, not one per word.

    `date_mask` blanks the part of a line the date check must not read. A coverage
    row quotes its spec unit verbatim, and a unit can legitimately be named for a
    date range; the lifecycle words still apply to the whole line.
    """
    hits: list[tuple[str, str]] = []
    patterns: list[tuple[re.Pattern, bool]] = [
        (DECOMP_STATUS_TOKENS_I, False),
        (DECOMP_STATUS_TOKENS_CS, False),
        (DATE_TOKEN, True),
    ]
    if extra is not None:
        patterns.append((extra, False))
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        for pat, maskable in patterns:
            target = date_mask(line) if (maskable and date_mask) else line
            m = pat.search(target)
            if m:
                hits.append((m.group(0), line))
                break
    return hits


def lint_decomp_slug(slug: str, file: str, rule: str, kind: str, report: LintReport) -> None:
    """Slug shape + the position-encoded shapes, for a spec or a brief slug."""
    if not DECOMP_SLUG_RE.match(slug):
        report.add(
            "FAIL", file, rule,
            f"{kind} slug `{slug}` is not concern-named kebab-case (1–4 words)",
        )
    for pat in FORBIDDEN_SLUG_PATTERNS:
        if pat.search(slug):
            report.add(
                "FAIL", file, rule,
                f"{kind} slug `{slug}` encodes position (matches /{pat.pattern}/); "
                "numbering is never a naming scheme here — order is read off the "
                "dependency edges. Rename after the concern it owns.",
            )
            break


def acyclic_check(
    nodes: list[str], deps: dict[str, list[str]]
) -> list[str]:
    """Kahn's algorithm. Returns the nodes left in a cycle, empty when acyclic."""
    in_degree = {n: 0 for n in nodes}
    edges: dict[str, set[str]] = defaultdict(set)
    for node, node_deps in deps.items():
        for dep in node_deps:
            if dep not in in_degree:
                continue
            edges[dep].add(node)
            in_degree[node] += 1
    queue = [n for n in nodes if in_degree[n] == 0]
    visited: list[str] = []
    while queue:
        n = queue.pop(0)
        visited.append(n)
        for nxt in edges[n]:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)
    return [n for n in nodes if n not in visited]


def lint_split_lines(
    file: str,
    owner: str,
    raw: str | None,
    pairs: list[tuple[str | None, str]],
    mentioned: list[str],
    depends_on: list[str],
    known: set[str],
    report: LintReport,
) -> None:
    """The split-line rules, shared shape at both layers.

    A split line is one predicate per neighbor, naming the neighbor. Two
    predicates against one neighbor means two seams and the entry they split is
    two units, so `exactly one` is enforced in both directions.
    """
    declared = [n for n, _ in pairs if n]
    # A paragraph-form field states one predicate, so its neighbours are the map
    # slugs it names. A bulleted field declares its neighbours outright, and a slug
    # that only appears inside another bullet's prose is a mention, not a seam.
    mentioned_known = [s for s in dict.fromkeys(mentioned) if s in known and s != owner]
    if not declared and len(mentioned_known) > 1:
        report.add(
            "FAIL", file, "vision-split-line-unbulleted",
            f"entry `{owner}` states one paragraph-form split line naming "
            f"{', '.join('`' + s + '`' for s in mentioned_known)}. One predicate covering "
            "several neighbours cannot be read as exactly one per neighbour in "
            "either direction — write one bullet per neighbour, each leading with "
            "that neighbour's backticked slug.",
        )

    for neighbor, text in pairs:
        label = f"`{owner}` → `{neighbor}`" if neighbor else f"`{owner}`"
        if not text.strip():
            report.add(
                "FAIL", file, "vision-split-line-enumerated",
                f"split line {label} has no predicate text.",
            )
            continue
        if SPLIT_LINE_ENUMERATION_RE.search(text) and not SPLIT_LINE_PREDICATE_RE.search(text):
            report.add(
                "FAIL", file, "vision-split-line-enumerated",
                f"split line {label} enumerates instead of deciding: {text.strip()[:120]!r}. "
                "A list classifies only what is already assigned. Write the one "
                "sentence that hands back a side for a rule the document does not "
                "yet contain.",
            )

    dupes = sorted({n for n in declared if declared.count(n) > 1})
    for neighbor in dupes:
        report.add(
            "FAIL", file, "vision-split-line-doubled",
            f"entry `{owner}` states {declared.count(neighbor)} split lines against "
            f"`{neighbor}`. A seam needing two predicates is two seams, and the entry "
            "they split is two specs — split it, or merge the predicates into one.",
        )

    named = set(declared) if declared else set(mentioned_known)
    for dep in depends_on:
        if dep not in named:
            report.add(
                "FAIL", file, "vision-split-line-unpaired",
                f"entry `{owner}` depends on `{dep}` but states no split line against "
                "it. A dependency with no seam is an unbounded claim on the "
                "neighbour's surface.",
            )

    for neighbor in declared:
        if neighbor not in known:
            report.add(
                "FAIL", file, "vision-dangling-slug",
                f"entry `{owner}` names `{neighbor}` in a split line, but no map entry "
                "owns that slug.",
            )

    if raw is not None and not pairs:
        report.add(
            "FAIL", file, "vision-split-line-enumerated",
            f"entry `{owner}` has an empty Split line field.",
        )


# ---------------------------------------------------------------------------
# Vision linting — the spec map
# ---------------------------------------------------------------------------


@dataclass
class VisionMapEntry:
    slug: str
    heading: str
    fields: dict[str, str | None] = field(default_factory=dict)
    split_pairs: list[tuple[str | None, str]] = field(default_factory=list)
    split_mentioned: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)


@dataclass
class VisionData:
    file: str
    map_present: bool = False
    map_heading: str | None = None
    map_body: str = ""
    section_after_map: str | None = None
    entries: list[VisionMapEntry] = field(default_factory=list)
    unowned_present: bool = False
    unowned_body: str = ""


# The mid-cycle flag, in either shape it is written in — a bare sidecar line or the
# HTML-comment form the template carries. The bolded product `**Status:**` line is a
# different field and never sets it.
MIDCYCLE_FLAG_RE = re.compile(r"^\s*(?:<!--\s*)?Status:\s*needs-user-input\b", re.MULTILINE)

# Mid-cycle scaffolding: the pending-blocker block /vision-author leaves behind while
# the document waits on a director call.
PENDING_BLOCKERS_RE = re.compile(r"blocker", re.IGNORECASE)


def _parse_split_field(text: str | None) -> tuple[list[tuple[str | None, str]], list[str]]:
    """Read a Split line field into (neighbor, predicate) pairs.

    Two shapes are accepted. A bulleted field states one neighbor per bullet,
    leading with the neighbour's backticked slug. A single-paragraph field states
    one predicate, and its neighbours are whatever map slugs it names.
    """
    if text is None:
        return [], []
    mentioned = [s for s in _backticked(text) if DECOMP_SLUG_RE.match(s)]
    pairs: list[tuple[str | None, str]] = []
    for line in text.splitlines():
        m = re.match(r"^\s*[-*+]\s+`([^`]+)`\s*[—–:-]?\s*(.*)$", line)
        if m:
            pairs.append((m.group(1).strip(), m.group(2).strip()))
    if pairs:
        return pairs, mentioned
    if text.strip():
        return [(None, text.strip())], mentioned
    return [], mentioned


def parse_vision(path: Path, text: str) -> VisionData:
    vision = VisionData(file=str(path))
    midcycle = bool(MIDCYCLE_FLAG_RE.search(text))
    text = strip_html_comments(text)
    sections = iter_sections(text, level=2)

    map_index = next(
        (i for i, (t, _) in enumerate(sections) if "spec map" in normalize_heading(t)),
        None,
    )
    if map_index is None:
        return vision

    map_title, map_body = sections[map_index]
    vision.map_present = True
    vision.map_heading = map_title
    vision.map_body = map_body

    # The map appends as vision's last section: anything below it renumbers every
    # section under an inserted one and orphans every `vision §N` reference in the
    # specs, the decision logs, and CLAUDE.md. Mid-cycle blocker scaffolding is the
    # one tolerated follower, and only while the document carries the mid-cycle flag
    # that says the scaffolding is about to be cleared.
    for later, _ in sections[map_index + 1:]:
        if midcycle and PENDING_BLOCKERS_RE.search(normalize_heading(later)):
            continue
        vision.section_after_map = later
        break

    for heading, body in iter_sections(vision.map_body, level=3):
        norm = normalize_heading(heading)
        if "unowned" in norm:
            vision.unowned_present = True
            vision.unowned_body = body.strip()
            continue
        if norm.startswith("<"):
            continue  # unfilled template placeholder
        ticked = _backticked(heading)
        # The heading's own case, so a capitalized slug fails the shape rule here
        # exactly as it does in a Briefs table. Only the fallback path — a heading
        # with no backticked slug at all — reads the normalized form.
        slug = ticked[0] if ticked else re.split(r"\s+[—–-]\s+", norm)[0].replace(" ", "-")
        entry = VisionMapEntry(slug=slug.strip(), heading=heading)
        for label in MAP_ENTRY_FIELDS:
            entry.fields[label] = _bold_field(body, label)
        entry.split_pairs, entry.split_mentioned = _parse_split_field(
            entry.fields.get("Split line")
        )
        entry.depends_on = _slug_list(entry.fields.get("Depends on"))
        vision.entries.append(entry)

    # The unowned block is map-level, so a format that states it as a bold lead-in
    # rather than its own heading satisfies the same obligation.
    if not vision.unowned_present:
        m = re.search(r"^\s*(?:[-*+]\s+)?\*\*unowned[^*]*\*\*\s*:?\s*(.*)$",
                      vision.map_body, re.IGNORECASE | re.MULTILINE)
        if m:
            vision.unowned_present = True
            vision.unowned_body = vision.map_body[m.start():].strip()

    return vision


def lint_vision(vision: VisionData, report: LintReport) -> None:
    f = vision.file

    # A vision in a shape with no spec map warns once rather than failing — a rule
    # that fails every document written to an earlier shape trains you to ignore the
    # lint. A map that exists but is malformed fails.
    if not vision.map_present:
        report.add(
            "WARN", f, "vision-map-missing",
            "no spec map section. It is required — one entry per spec (Owns, Split "
            "line, Depends on, Covers) plus the unowned block, appended as vision's "
            "last section. A vision without one warns rather than failing, and every "
            "other vision rule is skipped; run /vision-author to seed the map.",
        )
        return

    if vision.section_after_map:
        report.add(
            "FAIL", f, "vision-map-not-last",
            f"the spec map is followed by section \"{vision.section_after_map}\". "
            "The map appends last — inserting it mid-document renumbers every section "
            "below and orphans every `vision §N` reference in the specs, the decision "
            "logs, and CLAUDE.md. Mid-cycle blocker scaffolding is the one section "
            "tolerated below it, and only while `Status: needs-user-input` is set.",
        )

    if not vision.entries:
        report.add(
            "FAIL", f, "vision-map-empty",
            "the spec map has no entries. An empty map and a missing one read "
            "identically, and neither states which spec owns what.",
        )

    known = {e.slug for e in vision.entries}
    slugs = [e.slug for e in vision.entries]
    for slug in sorted({s for s in slugs if slugs.count(s) > 1}):
        report.add(
            "FAIL", f, "vision-slug-duplicate",
            f"slug `{slug}` heads {slugs.count(slug)} map entries. One entry per "
            "spec: two entries under one slug make every reference to it ambiguous, "
            "and the fields of all but one are never read.",
        )

    for entry in vision.entries:
        lint_decomp_slug(entry.slug, f, "vision-slug-shape", "spec", report)

        missing = [
            label for label in MAP_ENTRY_FIELDS
            if not (entry.fields.get(label) or "").strip()
        ]
        if missing:
            report.add(
                "FAIL", f, "vision-map-entry-shape",
                f"map entry `{entry.slug}` is missing {', '.join(missing)}. Every entry "
                "states all four: what the spec owns, the predicate against each "
                "neighbour, the specs it must cite, and the vision sections and terms "
                "it is the definition site for.",
            )

        lint_split_lines(
            f, entry.slug,
            entry.fields.get("Split line"),
            entry.split_pairs, entry.split_mentioned, entry.depends_on,
            known, report,
        )

        for dep in entry.depends_on:
            if dep not in known:
                report.add(
                    "FAIL", f, "vision-dangling-slug",
                    f"map entry `{entry.slug}` depends on `{dep}`, which no map entry "
                    "owns. Add the entry, or correct the reference — a dependency on "
                    "an unmapped spec is a claim nothing can be checked against.",
                )
            elif dep == entry.slug:
                report.add(
                    "FAIL", f, "vision-dangling-slug",
                    f"map entry `{entry.slug}` depends on itself.",
                )

    if not vision.unowned_present:
        report.add(
            "FAIL", f, "vision-unowned-block-missing",
            "the spec map has no unowned block. Vision material no spec owns is named "
            "explicitly so silence is never mistaken for coverage; without it the "
            "coverage claim is unfalsifiable.",
        )
    elif not vision.unowned_body.strip():
        report.add(
            "FAIL", f, "vision-unowned-block-empty",
            "the unowned block is empty. Name the vision material no spec owns, or "
            "state that every section, term, and ledger item is owned — the "
            "articulated answer is the deliverable.",
        )

    # Truth versus state, enforced mechanically. Nothing in the map changes when a
    # spec ships; status lives in specs/README.md.
    for token, line in scan_status_tokens(vision.map_body, VISION_STATUS_TOKENS):
        report.add(
            "FAIL", f, "vision-status-token",
            f"status token {token!r} in the spec map: {line[:120]!r}. The map states "
            "what is permanently true about the decomposition; where the work stands "
            "belongs in specs/README.md.",
        )


# ---------------------------------------------------------------------------
# Spec linting — the Decomposition section
# ---------------------------------------------------------------------------


@dataclass
class SpecBriefRow:
    slug: str
    scope: str = ""
    intent: str | None = None
    depends_on: list[str] = field(default_factory=list)


@dataclass
class SpecData:
    file: str
    section_titles: list[str] = field(default_factory=list)
    decomposition_present: bool = False
    decomposition_index: int | None = None
    decomposition_body: str = ""
    subsections_found: list[tuple[str, int]] = field(default_factory=list)
    briefs_table_rows: int = 0
    brief_rows: list[SpecBriefRow] = field(default_factory=list)
    intent_column_present: bool = False
    coverage_table_rows: int = 0
    coverage_briefs: list[str] = field(default_factory=list)
    coverage_row_lines: set[str] = field(default_factory=set)
    stubs_present: bool = False
    stub_slugs: list[str] = field(default_factory=list)


def _coverage_brief_slugs(cell: str) -> list[str]:
    """Brief slugs named in a Coverage row's disposition cell.

    The cell is two-state: a brief slug, or `excluded by <seam name>`. An
    exclusion names a seam rather than a brief, so it contributes no slug.
    """
    text = cell.strip()
    if not text or text in ("—", "–", "-"):
        return []
    if re.search(r"excluded by|structural|director review", text, re.IGNORECASE):
        return []
    ticked = [s for s in _backticked(text) if DECOMP_SLUG_RE.match(s)]
    if ticked:
        return ticked
    token = text.split()[0].strip("`*.,;")
    return [token] if DECOMP_SLUG_RE.match(token) else []


def _stub_slugs(body: str) -> list[str]:
    """Slugs of the Scope-stub blocks — one short block per brief."""
    slugs: list[str] = []
    for line in body.splitlines():
        m = (
            re.match(r"^#{3,6}\s+.*?`([^`]+)`", line)
            or re.match(r"^\s*(?:[-*+]\s+)?\*\*\s*`?([^`*]+?)`?\s*\*\*", line)
            or re.match(r"^\s*[-*+]\s+`([^`]+)`", line)
        )
        if m:
            candidate = m.group(1).strip()
            if DECOMP_SLUG_RE.match(candidate) and candidate not in slugs:
                slugs.append(candidate)
    return slugs


def parse_spec(path: Path, text: str) -> SpecData:
    spec = SpecData(file=str(path))
    text = strip_html_comments(text)
    sections = split_sections(text, level=2)
    spec.section_titles = [normalize_heading(t) for t in sections.keys()]

    decomp_title = next(
        (t for t in sections if normalize_heading(t).startswith("decomposition")), None
    )
    if decomp_title is None:
        return spec

    spec.decomposition_present = True
    spec.decomposition_index = list(sections.keys()).index(decomp_title)
    spec.decomposition_body = sections[decomp_title]

    subs = split_sections(spec.decomposition_body, level=3)
    sub_titles = list(subs.keys())
    for name in DECOMPOSITION_SUBSECTIONS:
        idx = next(
            (i for i, t in enumerate(sub_titles) if normalize_heading(t).startswith(name)),
            None,
        )
        if idx is not None:
            spec.subsections_found.append((name, idx))

    briefs_body = next(
        (b for t, b in subs.items() if normalize_heading(t).startswith("briefs")), None
    )
    if briefs_body:
        rows = extract_table(briefs_body)
        if rows and len(rows) > 1:
            header = [c.strip().lower() for c in rows[0]]
            intent_col = next((i for i, c in enumerate(header) if "intent" in c), None)
            deps_col = next((i for i, c in enumerate(header) if "depend" in c), None)
            spec.intent_column_present = intent_col is not None
            for row in rows[1:]:
                if not row or not row[0].strip():
                    continue
                ticked = _backticked(row[0])
                slug = ticked[0] if ticked else row[0].strip().strip("`*")
                if not slug or slug.startswith("<"):
                    continue
                spec.briefs_table_rows += 1
                brief = SpecBriefRow(slug=slug, scope=row[1].strip() if len(row) > 1 else "")
                if intent_col is not None and len(row) > intent_col:
                    brief.intent = row[intent_col].strip().strip("`*").lower()
                if deps_col is not None and len(row) > deps_col:
                    brief.depends_on = _slug_list(row[deps_col])
                spec.brief_rows.append(brief)

    stubs_body = next(
        (b for t, b in subs.items() if normalize_heading(t).startswith("scope stubs")), None
    )
    if stubs_body is not None:
        spec.stubs_present = True
        spec.stub_slugs = _stub_slugs(stubs_body)

    coverage_body = next(
        (b for t, b in subs.items() if normalize_heading(t).startswith("coverage")), None
    )
    if coverage_body:
        # The unit column quotes a spec unit verbatim, so the date check is told to
        # look past it; the rows are recorded by their source line to find again.
        spec.coverage_row_lines = {
            ln.strip() for ln in coverage_body.splitlines()
            if ln.strip().startswith("|") and not re.match(r"^\|[\s:|-]+\|$", ln.strip())
        }
        rows = extract_table(coverage_body)
        if rows and len(rows) > 1:
            header = [c.strip().lower() for c in rows[0]]
            brief_col = next((i for i, c in enumerate(header) if "brief" in c), 1)
            for row in rows[1:]:
                if not row or not row[0].strip() or row[0].strip().startswith("<"):
                    continue
                spec.coverage_table_rows += 1
                if len(row) > brief_col:
                    for slug in _coverage_brief_slugs(row[brief_col]):
                        if slug not in spec.coverage_briefs:
                            spec.coverage_briefs.append(slug)

    return spec


def _lint_spec_required_sections(spec: SpecData, report: LintReport) -> None:
    """The universal core of `_spec-common/spec-format.md` § Section template.

    A spec written to an older shape is missing sections the Decomposition rules
    reference by name — the placement check needs Non-goals and Glossary to be on
    the page to check anything at all — so this warns rather than failing, the same
    way a vision with no map does.
    """
    missing = [
        name for name in SPEC_REQUIRED_SECTIONS
        if not any(t.startswith(name) for t in spec.section_titles)
    ]
    if missing:
        report.add(
            "WARN", spec.file, "spec-required-section-missing",
            f"missing required section(s): {', '.join(missing)}. The universal core "
            "is Overview, Domain model & core concepts, Invariants & business rules, "
            "Feature areas, Non-goals & scope bounds, Decomposition, Glossary, in that "
            "order. A spec in a shape that omits one warns here; the rules that read a "
            "missing neighbour skip rather than fire.",
        )


def lint_spec(spec: SpecData, report: LintReport) -> None:
    f = spec.file

    _lint_spec_required_sections(spec, report)

    # A spec in a shape with no Decomposition section warns once and skips the rest
    # of the spec rules — the same convention every other shape rule here follows.
    if not spec.decomposition_present:
        report.add(
            "WARN", f, "spec-decomposition-missing",
            "no `## Decomposition` section. It is required — Seams, Briefs, Scope "
            "stubs, Coverage, between Non-goals and Glossary. A spec without one warns "
            "here and skips every other spec rule; run /spec-author to derive it.",
        )
        return

    _lint_decomposition_placement(spec, report)
    _lint_decomposition_subsections(spec, report)
    _lint_brief_graph(spec, report)
    _lint_coverage_agreement(spec, report)

    def date_mask(line: str) -> str:
        if line not in spec.coverage_row_lines:
            return line
        cells = split_table_row(line)
        return " | ".join(cells[1:])

    for token, line in scan_status_tokens(spec.decomposition_body, date_mask=date_mask):
        report.add(
            "FAIL", f, "spec-decomposition-status-token",
            f"status token {token!r} in `## Decomposition`: {line[:120]!r}. The section "
            "states which side of a boundary a unit sits on; where that unit is in the "
            "pipeline belongs in features/README.md.",
        )


def _lint_decomposition_placement(spec: SpecData, report: LintReport) -> None:
    """`## Decomposition` sits between Non-goals and Glossary.

    Stubs name their inherited exclusions by reference, so the exclusions have to
    already be on the page; the glossary follows because a stub may mint nothing.
    Both neighbours are checked only when present — which sections a spec must
    carry is `_spec-common/spec-format.md`'s rule, not this lint's.
    """
    f = spec.file
    idx = spec.decomposition_index
    if idx is None:
        return
    non_goals = next(
        (i for i, t in enumerate(spec.section_titles) if t.startswith("non-goals")), None
    )
    glossary = next(
        (i for i, t in enumerate(spec.section_titles) if t.startswith("glossary")), None
    )
    if non_goals is not None and idx < non_goals:
        report.add(
            "FAIL", f, "spec-decomposition-misplaced",
            "`## Decomposition` precedes `## Non-goals & scope bounds`. It sits after "
            "the exclusions, because every Scope stub names its inherited exclusions "
            "by reference.",
        )
    if glossary is not None and idx > glossary:
        report.add(
            "FAIL", f, "spec-decomposition-misplaced",
            "`## Decomposition` follows `## Glossary`. It sits between Non-goals and "
            "Glossary.",
        )


def _lint_decomposition_subsections(spec: SpecData, report: LintReport) -> None:
    """The four subsections, present and in fixed order."""
    f = spec.file
    found = dict(spec.subsections_found)
    missing = [n for n in DECOMPOSITION_SUBSECTIONS if n not in found]
    if missing:
        report.add(
            "FAIL", f, "spec-decomposition-subsection-missing",
            f"`## Decomposition` is missing {', '.join(missing)}. All four are "
            "required: Seams names each boundary with its split-line predicate, "
            "Briefs cuts the units, Scope stubs is what /brief-author consumes, and "
            "Coverage is the proof nothing fell through.",
        )
    present = [(n, found[n]) for n in DECOMPOSITION_SUBSECTIONS if n in found]
    if len(present) > 1:
        order = [i for _, i in present]
        if order != sorted(order):
            report.add(
                "FAIL", f, "spec-decomposition-subsection-order",
                "the Decomposition subsections are out of order. Fixed order is Seams, "
                "Briefs, Scope stubs, Coverage — map before you cut, and enumerating "
                "after cutting hides an unclaimed unit behind the seam that hardened "
                "around it. Found: "
                + ", ".join(n for n, _ in sorted(present, key=lambda kv: kv[1])),
            )


def _lint_brief_graph(spec: SpecData, report: LintReport) -> None:
    """Slug shapes, intents, the dependency graph, and the conformance sink."""
    f = spec.file
    if not spec.brief_rows:
        report.add(
            "FAIL", f, "spec-briefs-table-missing",
            "the Briefs subsection has no rows. One row per brief: slug, one-line "
            "scope, intent, depends on.",
        )
        return

    slugs = [b.slug for b in spec.brief_rows]
    known = set(slugs)
    for brief in spec.brief_rows:
        lint_decomp_slug(brief.slug, f, "spec-brief-slug-shape", "brief", report)

    for slug in sorted({s for s in slugs if slugs.count(s) > 1}):
        report.add("FAIL", f, "spec-brief-slug-duplicate",
                   f"brief slug `{slug}` appears in {slugs.count(slug)} Briefs rows")

    if not spec.intent_column_present:
        report.add(
            "WARN", f, "spec-brief-intent-column-missing",
            "the Briefs table has no `Intent` column (Foundation | Content | "
            "Instrument | Conformance). Without it the conformance sink and the "
            "Foundation obligation are uncheckable.",
        )

    # A self-edge is reported as itself and then dropped from the graph. Left in, it
    # blocks the topological sort and the whole-graph check echoes every brief
    # downstream of it as though they were a cycle of their own.
    deps = {b.slug: [d for d in b.depends_on if d != b.slug] for b in spec.brief_rows}
    for brief in spec.brief_rows:
        for dep in brief.depends_on:
            if dep not in known:
                report.add(
                    "FAIL", f, "spec-brief-dep-unknown",
                    f"brief `{brief.slug}` depends on `{dep}`, which is not a row in "
                    "the Briefs table.",
                )
            elif dep == brief.slug:
                report.add("FAIL", f, "spec-brief-dep-cycle",
                           f"brief `{brief.slug}` depends on itself")

    cyclic = acyclic_check(slugs, deps)
    if cyclic:
        report.add(
            "FAIL", f, "spec-brief-dep-cycle",
            f"the Briefs dependency graph has a cycle involving: {cyclic}. A "
            "dependency means one brief's scope reads a rule the other binds; a cycle "
            "means neither can be authored first.",
        )

    dependents: dict[str, set[str]] = defaultdict(set)
    for brief in spec.brief_rows:
        for dep in brief.depends_on:
            dependents[dep].add(brief.slug)

    for brief in spec.brief_rows:
        if brief.intent is None:
            continue
        if brief.intent not in BRIEF_INTENTS:
            report.add(
                "FAIL", f, "spec-brief-intent-invalid",
                f"brief `{brief.slug}` has intent {brief.intent!r}; must be one of "
                f"{sorted(BRIEF_INTENTS)}.",
            )
            continue
        # A Foundation brief binds vocabulary or structure other briefs consume.
        # Nothing depending on it means it binds nothing — fold it in.
        if brief.intent == "foundation" and not dependents[brief.slug]:
            report.add(
                "FAIL", f, "spec-foundation-brief-orphaned",
                f"brief `{brief.slug}` is Foundation but no other brief depends on it. "
                "Foundation exists to bind what its consumers read, so with no "
                "consumer it is dead — fold it into the brief that consumes it, or "
                "relabel it.",
            )

    _lint_conformance_sink(spec, dependents, report)


def _lint_conformance_sink(
    spec: SpecData, dependents: dict[str, set[str]], report: LintReport
) -> None:
    """The conformance brief: the DAG sink that proves cross-brief invariants.

    Required whenever an invariant's falsifier ranges over more than one brief.
    Whether this spec has such an invariant is the reviewer's read, so absence
    warns; a brief that IS labelled Conformance is fully checkable and fails.
    """
    f = spec.file
    sinks = [b for b in spec.brief_rows if b.intent == "conformance"]
    if not sinks:
        if spec.intent_column_present:
            report.add(
                "WARN", f, "spec-conformance-sink-missing",
                "no brief carries the Conformance intent. An invariant whose falsifier "
                "ranges over more than one brief needs a sink that depends on every "
                "delivering brief — the acceptance-chunk analog, one concern however "
                "many invariants it covers.",
            )
        return

    for sink in sinks:
        if dependents[sink.slug]:
            report.add(
                "FAIL", f, "spec-conformance-sink-not-sink",
                f"Conformance brief `{sink.slug}` is depended on by "
                f"{sorted(dependents[sink.slug])}. The conformance suite is a DAG sink "
                "— it runs against the assembled surface, so nothing may read it.",
            )

    deps_by_slug = {b.slug: b.depends_on for b in spec.brief_rows}
    reachable: set[str] = set()
    stack = [d for sink in sinks for d in sink.depends_on]
    while stack:
        slug = stack.pop()
        if slug in reachable:
            continue
        reachable.add(slug)
        stack.extend(deps_by_slug.get(slug, []))

    unreached = [
        b.slug for b in spec.brief_rows
        if b.intent != "conformance" and b.slug not in reachable
    ]
    if unreached:
        report.add(
            "WARN", f, "spec-conformance-sink-incomplete",
            f"the conformance sink does not reach {unreached}. A delivering brief no "
            "sink depends on is outside the cross-brief proof, so an invariant "
            "spanning it has no falsifier owner.",
        )


def _lint_coverage_agreement(spec: SpecData, report: LintReport) -> None:
    """Briefs, Scope stubs, and Coverage agree in every direction.

    A brief the coverage table never names claims nothing; a coverage row naming
    a brief the table does not cut assigns work to nobody; a brief with no stub
    sends /brief-author back to re-derive the slice this section exists to hand it.
    """
    f = spec.file
    if not spec.brief_rows:
        return
    known = {b.slug for b in spec.brief_rows}

    if spec.coverage_table_rows == 0:
        report.add(
            "FAIL", f, "spec-coverage-table-missing",
            "the Coverage subsection has no rows. Every spec unit maps to the brief "
            "that claims it or the seam that excludes it — coverage is a table, not "
            "prose, because silent narrowing is what it exists to prevent.",
        )
    else:
        for slug in spec.coverage_briefs:
            if slug not in known:
                report.add(
                    "FAIL", f, "spec-coverage-brief-unknown",
                    f"Coverage assigns a unit to `{slug}`, which is not a row in the "
                    "Briefs table.",
                )
        for slug in sorted(known - set(spec.coverage_briefs)):
            report.add(
                "FAIL", f, "spec-brief-uncovered",
                f"brief `{slug}` claims no spec unit in the Coverage table. A brief "
                "that covers nothing is either unnecessary or its claims were never "
                "written down.",
            )

    if spec.stub_slugs:
        for slug in spec.stub_slugs:
            if slug not in known:
                report.add(
                    "FAIL", f, "spec-stub-unknown",
                    f"Scope stubs carries a block for `{slug}`, which is not a row in "
                    "the Briefs table.",
                )
        for slug in sorted(known - set(spec.stub_slugs)):
            report.add(
                "FAIL", f, "spec-stub-missing",
                f"brief `{slug}` has no Scope stub. The stub is what /brief-author "
                "consumes — outcomes owed, exclusions inherited, spec units claimed.",
            )
    elif spec.stubs_present:
        # Zero parsed stubs under a Scope stubs heading would otherwise disable the
        # check that every brief has one: no stub reads as nothing to disagree with,
        # and a section with no stub in it lints cleaner than one with a stub missing.
        report.add(
            "FAIL", f, "spec-stub-missing",
            f"Scope stubs holds no recognizable stub block, so none of "
            f"{sorted(known)} has one. Each brief gets a block headed by its "
            "backticked slug (a `**`slug`**` lead-in or an H4), carrying outcomes "
            "owed, exclusions inherited, and spec units claimed.",
        )


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def is_vision(path: Path) -> bool:
    return path.name == "vision.md"


def is_spec(path: Path) -> bool:
    return path.name == "spec.md"


def is_engineering_plan(path: Path) -> bool:
    return path.name == "engineering-plan.md"


def is_chunk_plan(path: Path) -> bool:
    return path.parent.name == "implementation" and path.suffix == ".md"


def plan_roots(target: Path) -> list[Path]:
    """Resolve a directory to its plan roots (dirs holding engineering-plan.md).

    Flat layout   -> [features/<f>/]
    Tracked layout-> [features/<f>/plans/<t>/, ...]  (one engineering plan per track)

    See ~/.claude/skills/_plan-common/layout.md. A directory that is itself a plan
    root resolves to itself, so pointing the lint at a single track still works.
    """
    if (target / "engineering-plan.md").exists():
        return [target]
    return [p.parent for p in sorted(target.glob("plans/*/engineering-plan.md"))]


def lint_plan_root(root: Path, report: LintReport) -> None:
    eng_path = root / "engineering-plan.md"
    eplan = parse_engineering_plan(eng_path, read_text(eng_path))
    lint_engineering_plan(eplan, report)
    impl_dir = root / "implementation"
    chunks: list[ChunkData] = []
    if impl_dir.is_dir():
        for chunk_path in sorted(impl_dir.glob("*.md")):
            chunk = parse_chunk_plan(chunk_path, read_text(chunk_path))
            lint_chunk_plan(chunk, report)
            chunks.append(chunk)
    lint_cross_plan(eplan, chunks, report)


def lint_feature_brief(feature_dir: Path, report: LintReport) -> None:
    """Lint the feature-level brief, if one exists. Always at the feature root —
    a tracked feature has one brief and several plans."""
    brief_path = feature_dir / "brief.md"
    if brief_path.is_file():
        lint_brief(parse_brief(brief_path, read_text(brief_path)), report)


def lint_typed(kind: str, target: Path, report: LintReport) -> None:
    """Lint one file as an explicitly named document kind (`--type`)."""
    text = read_text(target)
    if kind == "vision":
        lint_vision(parse_vision(target, text), report)
    elif kind == "spec":
        lint_spec(parse_spec(target, text), report)
    elif kind == "brief":
        lint_brief(parse_brief(target, text), report)
    elif kind == "engineering-plan":
        lint_engineering_plan(parse_engineering_plan(target, text), report)
    elif kind == "chunk":
        lint_chunk_plan(parse_chunk_plan(target, text), report)


def lint_path(target: Path, report: LintReport) -> None:
    if target.is_file() and is_vision(target):
        lint_vision(parse_vision(target, read_text(target)), report)
        return

    if target.is_file() and is_spec(target):
        lint_spec(parse_spec(target, read_text(target)), report)
        return

    if target.is_file() and target.name == "brief.md":
        lint_brief(parse_brief(target, read_text(target)), report)
        return

    if target.is_dir():
        # A repo root or a specs/<slug>/ folder resolves to the document that
        # carries the decomposition. Guarded on the feature-layout markers being
        # absent, so a feature directory still resolves exactly as it always has.
        if not any(
            (target / n).exists() for n in ("brief.md", "engineering-plan.md")
        ) and not list(target.glob("plans/*/engineering-plan.md")):
            for name, linter in (("vision.md", "vision"), ("spec.md", "spec")):
                if (target / name).is_file():
                    lint_typed(linter, target / name, report)
                    return

        lint_feature_brief(target, report)
        # Feature directory (either layout) or a single plan root.
        roots = plan_roots(target)
        if not roots:
            # A feature with a brief and no engineering plan is the Proposed
            # lifecycle state, not a defect.
            if (target / "brief.md").is_file():
                report.add(
                    "WARN", str(target), "no-engineering-plan",
                    "brief only, no engineering plan yet (Proposed); linted the brief",
                )
            else:
                report.add(
                    "FAIL", str(target), "no-engineering-plan",
                    "no engineering-plan.md in feature directory, and no plans/*/engineering-plan.md",
                )
            return
        # A tracked feature must not also carry a top-level plan: that reads as flat
        # under the first resolution rule and silently ignores every track.
        if (target / "engineering-plan.md").exists() and list(target.glob("plans/*/engineering-plan.md")):
            report.add(
                "FAIL", str(target), "ambiguous-layout",
                "both engineering-plan.md and plans/*/engineering-plan.md exist; "
                "a feature is flat or tracked, not both",
            )
            return
        for root in roots:
            lint_plan_root(root, report)
        return

    text = read_text(target)
    if is_engineering_plan(target):
        eplan = parse_engineering_plan(target, text)
        lint_engineering_plan(eplan, report)
        return
    if is_chunk_plan(target):
        chunk = parse_chunk_plan(target, text)
        lint_chunk_plan(chunk, report)
        return

    # Fallback: ad-hoc plan with one or more "### Chunk: `<slug>`" blocks.
    blocks = re.split(r"^###\s+Chunk:\s+", text, flags=re.MULTILINE)
    if len(blocks) > 1:
        for block in blocks[1:]:
            block = "## Goal\n\n" + block  # synthesize so parse_chunk_plan finds Goal
            slug_match = re.match(r"`([^`]+)`", block)
            slug = slug_match.group(1) if slug_match else "unknown"
            chunk = parse_chunk_plan(target.with_name(f"{slug}.md"), block)
            chunk.file = f"{target}#{slug}"
            lint_chunk_plan(chunk, report)
    else:
        # Treat as a single chunk plan even though it's not in implementation/.
        chunk = parse_chunk_plan(target, text)
        lint_chunk_plan(chunk, report)


DOCUMENT_TYPES = ("vision", "spec", "brief", "engineering-plan", "chunk")


def main(argv: list[str]) -> int:
    args = argv[1:]
    kind: str | None = None
    strict = False
    while args and args[0].startswith("--"):
        if args[0] == "--type":
            if len(args) < 2 or args[1] not in DOCUMENT_TYPES:
                print(
                    f"error: --type takes one of {', '.join(DOCUMENT_TYPES)}",
                    file=sys.stderr,
                )
                return 2
            kind = args[1]
            args = args[2:]
        elif args[0] == "--strict":
            strict = True
            args = args[1:]
        else:
            print(f"error: unknown option {args[0]}", file=sys.stderr)
            return 2
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    target = Path(args[0]).resolve()
    if not target.exists():
        print(f"error: path not found: {target}", file=sys.stderr)
        return 2
    report = LintReport()
    if kind is None:
        lint_path(target, report)
    elif target.is_dir():
        print(f"error: --type {kind} needs a file, not a directory", file=sys.stderr)
        return 2
    else:
        lint_typed(kind, target, report)
    report.print()
    if strict and report.warn_count:
        print(
            f"--strict: {report.warn_count} WARN counted as blocking "
            "(a ship-mode gate takes the legacy-shape warnings as failures)."
        )
    if report.fail_count or (strict and report.warn_count):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
