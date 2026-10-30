"""Build and verify a project role file: frontmatter + hash-checked Core + Project section.

  role_file.py install <role> <project_dir>   copy a default role into <project_dir>/.claude/skills/<role>/SKILL.md
  role_file.py check <role_file>              exit 1 if the Core block was edited by hand
  role_file.py remove <role> <project_dir>    delete the role folder; refuses if the Project section or folder holds the owner's content (--discard-project overrides)
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
MARKER = "<!-- meerkit:core role={role} version={version} sha256={sha} -->"
CORE_RE = re.compile(
    re.escape(MARKER).replace(r"\{role\}", r"(?P<role>\S+)").replace(r"\{version\}", r"(?P<version>\S+)")
    .replace(r"\{sha\}", r"(?P<sha>[0-9a-f]{64})")
    + r"\n(?P<body>.*?)\n<!-- /meerkit:core -->",
    re.DOTALL,
)
FRONTMATTER_RE = re.compile(r"\A(---\n.*?\n---\n)(.*)\Z", re.DOTALL)
ROLE_RE = re.compile(r"[a-z][a-z0-9-]*")
PROJECT_STUB = "## Project\n\nWins over Core. Interview answers, local rules, dated lessons.\n"
SETTINGS_PREFIX = "Settings command:"


def settings_line(plugin_root: Path) -> str:
    """A running role does not know where the plugin lives, so install writes the command into its Project section."""
    return f"{SETTINGS_PREFIX} `uv run {plugin_root}/scripts/settings.py get <key> .` (run from the project root)."


def core_hash(body: str) -> str:
    return hashlib.sha256(body.encode()).hexdigest()


def render(default_text: str, role: str, version: str, plugin_root: Path = PLUGIN_ROOT) -> str:
    m = FRONTMATTER_RE.match(default_text)
    if not m:
        raise ValueError("default role file has no frontmatter")
    frontmatter, body = m.group(1), m.group(2).strip("\n")
    opener = MARKER.format(role=role, version=version, sha=core_hash(body))
    return f"{frontmatter}\n{opener}\n{body}\n<!-- /meerkit:core -->\n\n{PROJECT_STUB}\n{settings_line(plugin_root)}\n"


def check(role_text: str) -> dict:
    """Return {role, version, ok}; raise if no Core block."""
    m = CORE_RE.search(role_text)
    if not m:
        raise ValueError("no meerkit:core block")
    return {"role": m["role"], "version": m["version"], "ok": core_hash(m["body"]) == m["sha"]}


def role_dir(project_dir: Path, role: str) -> Path:
    if not ROLE_RE.fullmatch(role):
        raise ValueError(f"bad role name {role!r}")
    return project_dir / ".claude" / "skills" / role


def available_roles() -> list[str]:
    return sorted(p.stem for p in (PLUGIN_ROOT / "roles").glob("*.md"))


def project_section(role_text: str) -> str:
    """Everything after the Core block: the owner's part of the file."""
    m = CORE_RE.search(role_text)
    if not m:
        raise ValueError("no meerkit:core block")
    return role_text[m.end():].strip()


def install(role: str, project_dir: Path) -> Path:
    target = role_dir(project_dir, role) / "SKILL.md"
    if target.exists():
        raise FileExistsError(f"{target} exists")
    default_path = PLUGIN_ROOT / "roles" / f"{role}.md"
    if not default_path.exists():
        raise ValueError(f"unknown role {role!r}; available: {', '.join(available_roles())}")
    default = default_path.read_text(encoding="utf-8")
    version = json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(default, role, version), encoding="utf-8")
    return target


def remove(role: str, project_dir: Path, discard_project: bool = False) -> Path:
    target = role_dir(project_dir, role)
    text = (target / "SKILL.md").read_text(encoding="utf-8")
    found = check(text)  # only a team-installed role is deleted
    if not discard_project:
        if found["role"] != role:
            raise ValueError(f"{role}: Core marker names {found['role']!r}; pass --discard-project to delete anyway")
        if not found["ok"]:
            raise ValueError(f"{role}: Core was hand-edited; pass --discard-project to delete anyway")
        owner_text = "\n".join(l for l in project_section(text).splitlines() if not l.startswith(SETTINGS_PREFIX)).strip()
        if owner_text != PROJECT_STUB.strip():
            raise ValueError(f"{role}: Project section holds rules or lessons; pass --discard-project to delete them")
        if {p.name for p in target.iterdir()} != {"SKILL.md"}:
            raise ValueError(f"{role}: folder has other files; pass --discard-project to delete them")
    shutil.rmtree(target)
    return target


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("install", "remove"):
        p = sub.add_parser(name)
        p.add_argument("role")
        p.add_argument("project_dir", type=Path)
        if name == "remove":
            p.add_argument("--discard-project", action="store_true")
    sub.add_parser("check").add_argument("role_file", type=Path)
    args = parser.parse_args(argv)
    if args.cmd == "check":
        result = check(args.role_file.read_text(encoding="utf-8"))
        # the marker must name the role whose folder it sits in
        result["ok"] = result["ok"] and result["role"] == args.role_file.resolve().parent.name
        print(result)
        return 0 if result["ok"] else 1
    if args.cmd == "remove":
        print(remove(args.role, args.project_dir, args.discard_project))
    else:
        print(install(args.role, args.project_dir))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except (ValueError, OSError) as e:  # boundary handler: message + exit 2, distinct from check's exit 1
        print(f"role_file.py: {e}", file=sys.stderr)
        sys.exit(2)
