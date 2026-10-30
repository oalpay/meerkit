# meerkit

A Claude Code plugin that forms, tailors and maintains a project's team of AI roles (pm, tech-lead, oncall, designer, marketing, seo, ...). An issue tracker is the shared record. This file is the design record for contributors.

## Layout

Plugin root: `.claude-plugin/plugin.json` (the version source), `skills/<mode>/` (`form`, `add`, `remove`, later `update`, `groom`, `audit`, `retro`), `roles/` (default role Cores), `defaults/settings.json`, `templates/`, `scripts/`, `trackers/`, `tests/`. Skills are invoked as `/meerkit:<mode>`. Installed copies are pinned to a released version.

## Design

- Each role file in a project = a versioned **Core** block (generic default, never hand-edited, hash-checked) + a **Project** section (interview answers, local rules, dated lessons; wins over Core). Interview answers go in Project only, so Core stays upgradable.
- Update is pull, never push: `/meerkit:update` shows the Core diff per project; the owner approves.
- `/meerkit:groom` runs after every update (scoped to changed Core sections) and weekly (full): conflicts, redundancy, stale references, cross-role overlap, line budget. It proposes diffs, commits first, never auto-deletes an owner rule, and needs evidence for each deletion.
- Role Cores stay tool-neutral ("task board"). `trackers/<tool>.md` maps each verb to commands; the Project section names the tracker. Beads is the only tracker for now; no wrapper code or second adapter until a second real caller exists.
- A tracker is required. `form` checks the tool is installed and initialises it if the project has none.
- Builders and researchers are plugin agent files (`agents/`), not pasted briefs. Roles are skills.
- Claude Code has no multi-session team feature, so a tmux launcher runs one session per project with Remote Control per pane and a model per role. Default sessions are pm and tech-lead; every other role is a subagent, and the owner can open any role as a pane.

## Build order (vertical slices)

1. Form, add, remove, with pm and tech-lead defaults.
2. Update, with scoped groom.
3. Audit and weekly full groom.
4. Daily retro.

## Project structure `form` scaffolds

`docs/adr/`, `docs/design/mocks/` (with `APPROVED.md`), `docs/retro/`, `docs/forum/`. No `docs/specs/`: the card (description, acceptance, design, notes) is the spec. A part too long or reused goes in a file under `docs/` that the card links by path. Evidence and secrets live outside the repo (see Locations).

## Context management: the top principle

Context is gold. Load only what the next step needs.

- **Root `CLAUDE.md` holds the philosophy every role must know**: roster, tracker and statuses, folder map, secrets convention, one-line architecture rules. Nothing role-specific. A new line passes only if every role needs it at every start.
- **Subfolders hold the details.** Each role's folder has its own `CLAUDE.md`, loaded only by a session working there. Role-only rules live in the role's Project section. Task specifics live on the card. Reasoning lives in ADRs.
- **Cards are queried by field.** Reports go to files; agents return a few lines plus a path. Briefs point to a card, never repeat it.
- **Budgets:** role Core 80 lines, `SKILL.md` 60 lines, skill description 1 line, team section 25 lines, Project section 100 lines. `tests/test_budgets.py` enforces the first three and the team-section template; `form` and `audit` enforce the rest. Add nothing without removing or measuring.

## Source of truth: the most important rule

Every role keeps its documents and the tracker up to date. The tracker and the docs are the record; chat is not. Enforced three ways: a "Keep the record current" section in every Core, the done gate (a subagent cannot finish without the card updated and evidence linked), and `audit`, which computes staleness by code.

Workflow (light Shape Up): an appetite on every card, stop at the appetite, lapse stale pitches, a WIP limit on `in_review`. No cycles, `pitched` status, betting skill or hill charts unless measurement shows a need.

## Tracks and owner questions

- Two tracks, `track:fast|full`, on every card. Take the heavier track when unsure; escalate one way only. A middle track is added only if audit shows cards stuck between the two.
- Owner questions are `decision` cards in `waiting_owner`, so the owner always sees one list that the agents see too.

## Concurrency, cadence, research defaults

- **Concurrency is computed, not a number.** The spawn gate compares each task's declared file scope with live worktrees and PRs: different repos run in parallel; same repo, different modules in parallel (shared interface first); same module serialized unless declared independent; same or shared file always serialized. The project supplies a module map and a shared-files list. A resource ceiling caps whatever overlap allows.
- **Cadence:** retro daily; skill grooming and hook grooming weekly or on demand as separate runs. A retro adds a lesson only with a cited signal.
- **Planned from research (slices 1c and 2):** four-field delegation brief; a "discoveries affecting other cards" report field; a clean-context reviewer that flags only correctness gaps; review rounds capped, then a decision card; a done gate that runs the tests and checks the diff; a destructive-command gate and no production credentials in panes; a per-card turn cap; read-only researchers; builders cannot spawn agents; worktree cleanup after merge; short, owner-confirmed Project sections; a small eval set rerun after role-file changes. Hook exit-code behavior is still unverified.

## Configurability

Nothing tunable is hardcoded in a Core. Every number, limit, mode or name is a key in `defaults/settings.json`; a project overrides only what differs in `.claude/meerkit/settings.json`; Cores say `settings.<key>`; hooks read the same file. `scripts/settings.py` merges and validates (unknown key or wrong type is an error, never a silent default). `tests/test_settings.py` fails if a Core names a key that does not exist, or a key is read by nothing. Changing a value is one line, with no Core edit and no hash change.

## Locations

`form` asks where the out-of-repo folders live, and on which volume, and shows the defaults: `settings.evidence_dir` (large recordings may belong on another volume) and `settings.secrets_dir` (folders mode 700, files mode 600, names only in the repo). `{project}` is replaced by the project name. The answer is stored as a settings override, so every role and hook resolves the same path.

## Logs are evidence

Verification must be replayable.
- **Product logs.** The tech lead names, in `design`, the log lines that prove each acceptance line; where none exist the task adds structured logs (ids, no secrets or personal data). The builder saves the excerpt plus the command or query that fetched it, and `report.md` maps each acceptance line to a file. A claim with no saved output is missing evidence.
- **Team log (planned, 1c).** The hook dispatcher appends one JSON line per event to `<evidence_dir>/_team/events.jsonl`: time, role, event, card id. Audit, retro and the behavior sims read it. A write error never blocks work.

## Testing

- `uv run pytest` runs the unit tests: role file install/check/remove, settings, budgets.
- `tests/sim/run.py` is a behavior simulation: scripted boards, a real `claude -p` run per scenario, outcomes checked by code, the full tool-call trace kept. `--dry` seeds and checks without the model; every check must fail on an untouched board. It costs tokens. Rerun it after any Core change and compare with the last pass rate.
