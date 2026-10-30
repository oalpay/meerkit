<!-- meerkit:section -->
## Team sessions
Roles: {roster}. Each lives in `.claude/skills/<role>/SKILL.md`; read yours first.
Task board: beads (`bd`). Cards are the spec and the record; chat is not.
Card statuses: `shaping`, `approved`, `ready_to_build`, `in_progress`, `in_review`, `blocked`, `waiting_owner`, `closed`. Pull cards with `bd list --status=approved --sort priority`; `bd ready` lists only `open` tasks.
Labels: `track:fast|full`, `appetite:small|medium|large`, `decision`, `eng-task`, `eng-found`, `oncall`, `tl-state`.
Owner question: a card with label `decision` and status `waiting_owner`: `bd create --type=task --status=waiting_owner -l decision --title ... --description ...`.
Settings: `.claude/meerkit/settings.json` overrides the plugin defaults; read a value with the settings command in your role's Project section.
Folders: `docs/adr/`, `docs/design/mocks/`, `docs/retro/`, `docs/forum/`. Evidence at `settings.evidence_dir`, secrets at `settings.secrets_dir` (names only in the repo).
<!-- /meerkit:section -->
