#!/usr/bin/env python3
"""plan-lint: deterministic structural checks for engineering plans and chunk plans.

Usage:
  plan-lint <path>

  <path> is one of:
    - A feature directory (features/<name>/) — lints the engineering plan + every
      per-chunk plan under implementation/, and warns on chunks indexed in the
      engineering plan that have no per-chunk plan yet.
    - An engineering plan file (features/<name>/engineering-plan.md).
    - A per-chunk plan file (features/<name>/implementation/<slug>.md).
    - A lightweight ad-hoc plan (.scratch/*.md) — runs the chunk-plan checks on
      every "### Chunk: `<slug>`" block found.

Exit codes:
  0  — all checks passed
  1  — at least one check failed
  2  — usage / IO error

The lint is pure parsing — no LLM judgment, no external services. Output is one
finding per line, prefixed with FAIL or WARN. FAIL counts toward exit-1; WARN is
informational only (e.g. file not found in repo, but path looks plausible).
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# ---------------------------------------------------------------------------
# Lint rule definitions
# ---------------------------------------------------------------------------

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

# Heading regexes.
H2 = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
H3 = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)

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


def split_sections(text: str, level: int = 2) -> dict[str, str]:
    """Split markdown by H2 (level=2) or H3 (level=3) headings into a dict."""
    pattern = H2 if level == 2 else H3
    matches = list(pattern.finditer(text))
    sections: dict[str, str] = {}
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[title.lower()] = text[start:end]
    return sections


def find_section(sections: dict[str, str], *aliases: str) -> str | None:
    """Look up a section by any of its possible titles (lowercased)."""
    for a in aliases:
        if a.lower() in sections:
            return sections[a.lower()]
    return None


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
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(cells)
    return rows


def extract_paths_from_cell(cell: str) -> list[str]:
    """Pull markdown-backticked file paths out of a table cell or bullet line."""
    return [m.group(1) for m in PATH_TOKEN.finditer(cell)]


# ---------------------------------------------------------------------------
# Per-chunk plan linting
# ---------------------------------------------------------------------------


@dataclass
class ChunkData:
    """Parsed structure for one chunk plan."""

    slug: str
    file: str
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


def parse_chunk_plan(path: Path, text: str) -> ChunkData:
    """Parse a per-chunk plan into structured data for linting."""
    # Slug is the file basename (minus .md) for files in implementation/, or
    # the first H1's backticked slug for ad-hoc files.
    slug = path.stem
    h1 = re.search(r"^#\s+Chunk:\s+`([^`]+)`", text, re.MULTILINE)
    if h1:
        slug = h1.group(1)

    chunk = ChunkData(slug=slug, file=str(path))

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

    # Acceptance criteria — checkbox bullets.
    ac_body = find_section(sections, "Acceptance criteria", "Verification", "Self-Verification")
    if ac_body:
        for m in re.finditer(r"^-\s*\[\s*[ xX]?\s*\]\s*(.+)$", ac_body, re.MULTILINE):
            chunk.acceptance_criteria.append(m.group(1).strip())

    return chunk


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


# ---------------------------------------------------------------------------
# Engineering-plan linting
# ---------------------------------------------------------------------------


@dataclass
class EngineeringPlanData:
    file: str
    chunk_index: list[tuple[str, str, list[str]]] = field(default_factory=list)  # (slug, name, deps)
    decisions_present: bool = False
    decisions_unresolved: list[str] = field(default_factory=list)


def parse_engineering_plan(path: Path, text: str) -> EngineeringPlanData:
    plan = EngineeringPlanData(file=str(path))
    sections = split_sections(text, level=2)

    # Chunk index table.
    ci_body = find_section(sections, "Chunk index")
    if ci_body:
        rows = extract_table(ci_body)
        if rows and len(rows) > 1:
            for row in rows[1:]:
                if len(row) < 2:
                    continue
                slug_cell, name_cell = row[0], row[1]
                deps_cell = row[2] if len(row) > 2 else ""
                slug_match = re.search(r"`([^`]+)`", slug_cell)
                if not slug_match:
                    continue
                slug = slug_match.group(1)
                deps = [m.group(1) for m in re.finditer(r"`([^`]+)`", deps_cell)]
                plan.chunk_index.append((slug, name_cell.strip(), deps))

    # Decisions closure.
    dc_body = find_section(sections, "Decisions closure")
    if dc_body:
        plan.decisions_present = True
        rows = extract_table(dc_body)
        if rows and len(rows) > 1:
            for row in rows[1:]:
                if len(row) < 2:
                    continue
                resolution = row[1].strip().lower()
                if "tbd" in resolution or "figure out" in resolution or resolution in ("", "—", "-"):
                    plan.decisions_unresolved.append(row[0].strip())

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
    for slug in indexed_slugs:
        if slug not in chunk_by_slug:
            report.add(
                "WARN", f, "chunk-plan-missing",
                f"engineering plan lists `{slug}` but no implementation/<slug>.md exists yet",
            )


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def is_engineering_plan(path: Path) -> bool:
    return path.name == "engineering-plan.md"


def is_chunk_plan(path: Path) -> bool:
    return path.parent.name == "implementation" and path.suffix == ".md"


def lint_path(target: Path, report: LintReport) -> None:
    if target.is_dir():
        # Feature directory — find engineering plan + all chunk plans.
        eng_path = target / "engineering-plan.md"
        if not eng_path.exists():
            report.add("FAIL", str(target), "no-engineering-plan", "no engineering-plan.md in feature directory")
            return
        eplan = parse_engineering_plan(eng_path, eng_path.read_text())
        lint_engineering_plan(eplan, report)
        impl_dir = target / "implementation"
        chunks: list[ChunkData] = []
        if impl_dir.is_dir():
            for chunk_path in sorted(impl_dir.glob("*.md")):
                chunk = parse_chunk_plan(chunk_path, chunk_path.read_text())
                lint_chunk_plan(chunk, report)
                chunks.append(chunk)
        lint_cross_plan(eplan, chunks, report)
        return

    text = target.read_text()
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


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    target = Path(argv[1]).resolve()
    if not target.exists():
        print(f"error: path not found: {target}", file=sys.stderr)
        return 2
    report = LintReport()
    lint_path(target, report)
    report.print()
    return 0 if report.fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
