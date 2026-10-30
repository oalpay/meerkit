# Tracker: beads

The tracker is the shared record; roles use these verbs. Confirm each command with `bd --help` on first use.

| Verb | Command |
|---|---|
| set up statuses (once, `form` runs it) | `bd config set status.custom "shaping:active,approved:active,ready_to_build:active,in_review:wip,waiting_owner:frozen"` |
| search cards | `bd search <text>` |
| show one card | `bd show <id>` |
| create card | `bd create --type=<feature\|task\|bug> --status=<s> -l <label> --priority=<0-4> --title --description --acceptance --design` |
| update status or notes | `bd update <id> --status=<s>` |
| list by status, label, parent | `bd list --status=<s> -l <label> --sort priority` |
| ready tasks of a card (status `open` only) | `bd ready --parent <id>` |
| add dependency | `bd dep add <task> <depends-on>` |
| open a decision card (label `decision`, status `waiting_owner`) | `bd create --type=task --status=waiting_owner -l decision --title --description` |
| close | `bd close <id> --reason <why>` |

Fields: description, acceptance (numbered, observable), design, notes. Parent-child via `--parent`. Reserved labels: `kanban`, `eng-task`, `eng-found`, `track:fast|full`, `decision`, `oncall`, `tl-state`.
Appetite: label `appetite:small|medium|large`. A lapsed card closes with `bd close <id> --reason lapsed`.

A fresh project rejects `shaping`, `approved`, `ready_to_build`, `in_review` and `waiting_owner` until the statuses line above runs. `bd ready` skips custom statuses: cards are pulled with `bd list --status=approved --sort priority`; `bd ready` is for `eng-task` children, which stay `open`.
