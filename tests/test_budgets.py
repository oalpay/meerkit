"""Context budgets from CLAUDE.md 'Context management'. Fail the merge when a file grows past its limit."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROLE_CORE_LINES = 80
SKILL_MD_LINES = 60


def lines(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def test_role_cores_within_budget():
    for role in (ROOT / "roles").glob("*.md"):
        assert lines(role) <= ROLE_CORE_LINES, f"{role.name}: {lines(role)} > {ROLE_CORE_LINES}"


def test_skill_md_within_budget():
    for f in (ROOT / "skills").glob("*/SKILL.md"):
        assert lines(f) <= SKILL_MD_LINES, f.parent.name


def test_descriptions_are_one_line():
    for f in [*(ROOT / "skills").glob("*/SKILL.md"), *(ROOT / "roles").glob("*.md")]:
        front = f.read_text(encoding="utf-8").split("---")[1]
        desc = [l for l in front.splitlines() if l.startswith("description:")]
        assert len(desc) == 1, f.name


def test_tracker_doc_sets_up_every_status_the_cores_use():
    doc = (Path(__file__).resolve().parent.parent / "trackers" / "beads.md").read_text(encoding="utf-8")
    line = next(l for l in doc.splitlines() if "status.custom" in l)
    for status in ("shaping", "approved", "ready_to_build", "in_review", "waiting_owner"):
        assert status in line, status


def test_team_section_template_fits_budget_and_names_every_status():
    text = (Path(__file__).resolve().parent.parent / "templates" / "team-section.md").read_text(encoding="utf-8")
    assert len(text.splitlines()) <= 25
    for status in ("shaping", "approved", "ready_to_build", "in_progress", "in_review", "blocked", "waiting_owner", "closed"):
        assert f"`{status}`" in text, status
