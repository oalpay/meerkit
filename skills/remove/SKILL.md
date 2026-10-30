---
name: remove
description: Remove a role from a project's team. Use for "remove the designer", "/meerkit:remove <role>".
---

# /meerkit:remove <role>

Same worktree and PR gate as `/meerkit:form`.

1. Tell the owner what the role's Project section holds (rules, lessons) and that the folder is deleted; git keeps the history. Wait for the OK.
2. `uv run ${CLAUDE_PLUGIN_ROOT}/scripts/role_file.py remove <role> <worktree dir>`. It refuses when the Project section or folder holds the owner's content. Show that content, get an explicit OK to discard it, then add `--discard-project`.
3. Remove it from "Team sessions" in the project CLAUDE.md. Leave the role's work folders; say so.
4. List other roles and files that mention it. Do not edit them unasked.
