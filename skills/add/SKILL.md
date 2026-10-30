---
name: add
description: Add one role to a project's team. Use for "add a designer", "add oncall", "/meerkit:add <role>".
---

# /meerkit:add <role>

Same worktree and PR gate as `/meerkit:form`: never edit the shared checkout, show the diff, wait for the owner's OK.

1. `uv run ${CLAUDE_PLUGIN_ROOT}/scripts/role_file.py install <role> <worktree dir>` (fails if the role exists).
2. Run only the interview topics that role needs. Write the answers into its Project section.
3. Add the role to the "Team sessions" section of the project CLAUDE.md.
4. `role_file.py check` the new file. Show the diff.
