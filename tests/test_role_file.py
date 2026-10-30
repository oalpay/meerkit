import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import role_file

DEFAULT = "---\nname: pm\ndescription: d\n---\n\n# PM\n\nbody line\n"


def test_render_then_check_ok():
    out = role_file.render(DEFAULT, "pm", "0.1.0")
    assert role_file.check(out) == {"role": "pm", "version": "0.1.0", "ok": True}
    assert out.startswith("---\nname: pm")
    assert "dated lessons." in out


def test_hand_edit_of_core_is_detected():
    out = role_file.render(DEFAULT, "pm", "0.1.0").replace("body line", "edited")
    assert role_file.check(out)["ok"] is False


def test_project_section_edit_is_not_core_edit():
    out = role_file.render(DEFAULT, "pm", "0.1.0") + "\n- 2026-10-26 a lesson\n"
    assert role_file.check(out)["ok"] is True


def test_check_without_block_raises():
    with pytest.raises(ValueError):
        role_file.check("# nothing")


def test_install_and_remove_roundtrip(tmp_path):
    p = role_file.install("pm", tmp_path)
    assert role_file.check(p.read_text())["ok"]
    with pytest.raises(FileExistsError):
        role_file.install("pm", tmp_path)
    role_file.remove("pm", tmp_path)
    assert not p.parent.exists()


def test_bad_role_name_rejected(tmp_path):
    with pytest.raises(ValueError):
        role_file.remove("..", tmp_path)
    with pytest.raises(ValueError):
        role_file.install("a/b", tmp_path)


def test_remove_refuses_non_team_folder(tmp_path):
    d = tmp_path / ".claude" / "skills" / "mine"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("# hand-written")
    with pytest.raises(ValueError):
        role_file.remove("mine", tmp_path)
    assert d.exists()


def test_install_into_existing_empty_folder(tmp_path):
    (tmp_path / ".claude" / "skills" / "pm").mkdir(parents=True)
    assert role_file.install("pm", tmp_path).exists()


def test_cli_check_exit_codes(tmp_path):
    p = role_file.install("pm", tmp_path)
    assert role_file.main(["check", str(p)]) == 0
    p.write_text(p.read_text().replace("Hard nevers", "Hard NEVERS"))
    assert role_file.main(["check", str(p)]) == 1
    moved = tmp_path / ".claude" / "skills" / "tech-lead" / "SKILL.md"
    moved.parent.mkdir()
    moved.write_text(role_file.render(DEFAULT, "pm", "0.1.0"))
    assert role_file.main(["check", str(moved)]) == 1


def test_remove_refuses_when_project_section_has_content(tmp_path):
    p = role_file.install("pm", tmp_path)
    p.write_text(p.read_text() + "- 2026-10-26 a lesson\n")
    with pytest.raises(ValueError, match="Project section"):
        role_file.remove("pm", tmp_path)
    assert p.exists()
    role_file.remove("pm", tmp_path, discard_project=True)
    assert not p.parent.exists()


def test_remove_refuses_extra_files_in_role_folder(tmp_path):
    p = role_file.install("pm", tmp_path)
    (p.parent / "notes.md").write_text("x")
    with pytest.raises(ValueError, match="other files"):
        role_file.remove("pm", tmp_path)


def test_install_unknown_role_lists_available(tmp_path):
    with pytest.raises(ValueError, match="available: .*pm"):
        role_file.install("nope", tmp_path)


def test_install_writes_settings_command_into_project_section(tmp_path):
    p = role_file.install("pm", tmp_path)
    assert f"uv run {role_file.PLUGIN_ROOT}/scripts/settings.py get <key> ." in role_file.project_section(p.read_text())


def test_fresh_install_can_be_removed_even_if_plugin_root_moved(tmp_path):
    p = role_file.install("pm", tmp_path)
    p.write_text(p.read_text().replace(str(role_file.PLUGIN_ROOT), "/old/cache/0.0.9"))
    role_file.remove("pm", tmp_path)
    assert not p.parent.exists()


def test_remove_refuses_hand_edited_core(tmp_path):
    p = role_file.install("pm", tmp_path)
    p.write_text(p.read_text().replace("# PM", "# PM!"))
    with pytest.raises(ValueError, match="Core"):
        role_file.remove("pm", tmp_path)
    role_file.remove("pm", tmp_path, discard_project=True)


def test_remove_refuses_marker_for_another_role(tmp_path):
    p = role_file.install("pm", tmp_path)
    t = role_file.install("tech-lead", tmp_path)
    p.write_text(t.read_text())
    with pytest.raises(ValueError, match="marker"):
        role_file.remove("pm", tmp_path, discard_project=False)
