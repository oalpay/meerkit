import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import settings

DEFAULTS = {"a": 1, "m": "owner", "t": {"x": 1}}


def test_override_wins_and_rest_stay_default():
    assert settings.merge({"a": 1, "b": 2}, {"a": 9}) == {"a": 9, "b": 2}


def test_unknown_key_is_an_error():
    with pytest.raises(ValueError, match="unknown"):
        settings.merge(DEFAULTS, {"typo": 1})


def test_wrong_type_is_an_error():
    with pytest.raises(ValueError, match="expected int"):
        settings.merge(DEFAULTS, {"a": "3"})


def test_merge_gate_enum():
    d = json.loads(settings.DEFAULTS_FILE.read_text())
    with pytest.raises(ValueError, match="one of"):
        settings.merge(d, {"merge_gate": "nobody"})


def test_load_reads_project_overrides(tmp_path):
    f = tmp_path / ".claude" / "meerkit" / "settings.json"
    f.parent.mkdir(parents=True)
    f.write_text('{"review_wip_limit": 2}')
    assert settings.load(tmp_path)["review_wip_limit"] == 2
    assert settings.load(tmp_path / "none")["review_wip_limit"] == 5


def test_every_key_a_core_names_exists():
    named = set()
    for f in [*(ROOT / "roles").glob("*.md"), *(ROOT / "skills").glob("*/SKILL.md")]:
        named |= set(re.findall(r"settings\.([a-z_]+)", f.read_text(encoding="utf-8")))
    named -= {"py", "json"}  # file names: scripts/settings.py, settings.json
    assert named <= settings.default_keys(), named - settings.default_keys()


def test_dict_setting_merges_by_key():
    d = json.loads(settings.DEFAULTS_FILE.read_text())
    out = settings.merge(d, {"tiers": {"fast": "sonnet"}})
    assert out["tiers"] == {"strong": "opus", "standard": "sonnet", "fast": "sonnet"}


# keys read by the launcher or hooks (slices 1b, 1c), not by a Core
SCRIPT_KEYS = {"remote_control", "tracker", "tiers", "role_tiers", "secrets_dir"}


def test_every_key_is_used_by_a_core_or_listed_as_script_key():
    named = set()
    for f in (ROOT / "roles").glob("*.md"):
        named |= set(re.findall(r"settings\.([a-z_]+)", f.read_text(encoding="utf-8")))
    orphans = settings.default_keys() - named - SCRIPT_KEYS
    assert not orphans, f"settings no Core or script reads: {orphans}"


D = json.loads(settings.DEFAULTS_FILE.read_text())


@pytest.mark.parametrize("override, why", [
    ({"appetite_days": {"smal": 2}}, "unknown"),
    ({"appetite_days": {"small": "2"}}, "expected int"),
    ({"builder_ceiling": 0}, ">= 1"),
    ({"lapse_days": -3}, ">= 1"),
    ({"tiers": {"fast": 5}}, "expected str"),
    ({"role_tiers": {"pm": "huge"}}, "tier"),
    ({"modules": {"src/a": 1}}, "expected str"),
    ({"shared_files": [1]}, "expected str"),
])
def test_nested_values_are_validated(override, why):
    with pytest.raises(ValueError, match=why):
        settings.merge(D, override)


def test_valid_nested_override_passes():
    out = settings.merge(D, {"modules": {"src/a": "a"}, "shared_files": ["uv.lock"], "role_tiers": {"builder": "fast"}})
    assert out["role_tiers"]["builder"] == "fast" and out["role_tiers"]["pm"] == "strong"
