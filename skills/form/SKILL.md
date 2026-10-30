---
name: form
description: Form a project's role team by interviewing the owner and installing default roles. Use for "form a team", "set up the team", "/meerkit:form".
---

# /meerkit:form

Forms a project's team. A project role file is a hash-checked **Core** block (copy of a default in `${CLAUDE_PLUGIN_ROOT}/roles/`, never hand-edited) plus a **Project** section (interview answers, local rules; Project wins). Interview answers go in Project only.

Never edit the shared checkout. Create a task worktree first (`git worktree add ../wt/meerkit-form -b meerkit-form origin/<default>`), work there, and show the owner the diff before any commit. Stop at the PR gate: show it working, wait for an explicit OK, then open the PR.

Needs `uv`, `git`, `gh` and the tracker (`${CLAUDE_PLUGIN_ROOT}/trackers/beads.md`). Check them first; stop with a clear message if one is missing. Then run `bd init` if the project has no tracker (it edits CLAUDE.md and adds hooks; expect that) and the statuses line from the tracker doc.

## Steps

1. Read the project's CLAUDE.md and `.claude/skills/`. Do not ask what they answer. Stop and ask before touching an existing "Team sessions" heading.
2. Propose roles from what the project is (defaults: `${CLAUDE_PLUGIN_ROOT}/roles/`). One line each. The owner picks.
3. Interview. Ask only what changes a role file. At most four questions per round, options concrete, recommended first. Topics: product and stage; architecture (functional or procedural, monolith or services, where business rules live); testing; spend (what costs money, what agents never run); tracker and statuses; ship (who approves, who clicks merge, deploy, production check); owner contact; capacity (builder cap, shared resources); locations: where the out-of-repo folders live and on which volume, with the defaults shown (`settings.evidence_dir`, `settings.secrets_dir`; secrets folders mode 700), created after the answer; models per role and subagent kind (tiers strong, standard, fast, mapped to aliases once).
4. Install each role: `uv run ${CLAUDE_PLUGIN_ROOT}/scripts/role_file.py install <role> <worktree dir>`.
5. Write prose answers into each Project section (tool names go there, never in Core). Write numeric and named answers to `.claude/meerkit/settings.json`, only the keys that differ from `${CLAUDE_PLUGIN_ROOT}/defaults/settings.json`; check with `scripts/settings.py show`.
6. Add the "Team sessions" section to the project CLAUDE.md from `${CLAUDE_PLUGIN_ROOT}/templates/team-section.md`, filling the roster (25 lines max). Details go in role files.
7. `role_file.py check` every installed role. Show the diff.
