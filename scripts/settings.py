"""Team settings: plugin defaults + a project's overrides, validated.

  settings.py show <project_dir>          merged settings as JSON
  settings.py get <key> <project_dir>     one value (JSON)

A project's .claude/meerkit/settings.json holds only the keys that differ from defaults/settings.json.
Unknown keys and wrong types are errors, so a typo never becomes a silent default.
"""
import argparse
import json
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
DEFAULTS_FILE = PLUGIN_ROOT / "defaults" / "settings.json"
OVERRIDES_REL = Path(".claude") / "meerkit" / "settings.json"
ENUMS = {"merge_gate": {"owner", "pm"}}


def check_value(path: str, value, default) -> None:
    """Same type as the default, whole numbers >= 1, dict keys known. An empty default dict or list holds strings."""
    if type(value) is not type(default):
        raise ValueError(f"{path}: expected {type(default).__name__}, got {type(value).__name__}")
    if type(value) is int and value < 1:
        raise ValueError(f"{path}: must be >= 1")
    if isinstance(value, dict):
        unknown = sorted(set(value) - set(default)) if default else []
        if unknown:
            raise ValueError(f"{path}: unknown key(s): {', '.join(unknown)}")
        for k, v in value.items():
            check_value(f"{path}.{k}", v, default[k] if default else "")
    if isinstance(value, list):
        for i, v in enumerate(value):
            check_value(f"{path}[{i}]", v, "")


def merge(defaults: dict, overrides: dict) -> dict:
    """Pure: overrides win (dicts merge by key); every override is validated against its default."""
    unknown = sorted(set(overrides) - set(defaults))
    if unknown:
        raise ValueError(f"unknown setting(s): {', '.join(unknown)}")
    for key, value in overrides.items():
        check_value(key, value, defaults[key])
        if key in ENUMS and value not in ENUMS[key]:
            raise ValueError(f"{key}: must be one of {sorted(ENUMS[key])}")
    merged = _merged(defaults, overrides)
    if "role_tiers" in merged:
        bad = sorted(set(merged["role_tiers"].values()) - set(merged["tiers"]))
        if bad:
            raise ValueError(f"role_tiers: unknown tier(s): {', '.join(bad)}; tiers are {sorted(merged['tiers'])}")
    return merged


def _merged(defaults: dict, overrides: dict) -> dict:
    # a dict setting (tiers, appetite_days) overrides key by key, so one changed tier keeps the rest
    return {k: {**v, **overrides[k]} if isinstance(v, dict) and k in overrides else overrides.get(k, v) for k, v in defaults.items()}


def load(project_dir: Path) -> dict:
    defaults = json.loads(DEFAULTS_FILE.read_text(encoding="utf-8"))
    path = project_dir / OVERRIDES_REL
    overrides = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return merge(defaults, overrides)


def default_keys() -> set[str]:
    return set(json.loads(DEFAULTS_FILE.read_text(encoding="utf-8")))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show").add_argument("project_dir", type=Path)
    get = sub.add_parser("get")
    get.add_argument("key")
    get.add_argument("project_dir", type=Path)
    args = parser.parse_args(argv)
    settings = load(args.project_dir)
    if args.cmd == "show":
        print(json.dumps(settings, indent=2))
    else:
        print(json.dumps(settings[args.key]))  # KeyError on a typo is the right failure
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except (ValueError, OSError, KeyError) as e:
        print(f"settings.py: {e}", file=sys.stderr)
        sys.exit(2)
