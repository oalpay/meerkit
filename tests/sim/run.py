"""Behavior simulation: does a model following a role Core do the right thing on a scripted board?

  uv run tests/sim/run.py --out <dir> [--only name,...] [--runs N] [--model sonnet] [--budget 1.0] [--dry]

Each run builds a fresh scratch project (git + beads + the installed pm and tech-lead roles), seeds a
board, runs `claude -p` with the role, then CODE checks the board. The model never grades itself.
--dry seeds and checks without calling the model; every check must fail on an untouched board.
Needs: claude, bd, uv, git. Costs model tokens unless --dry.
"""
import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ["Bash(bd:*)", "Bash(uv run:*)", "Bash(git:*)", "Bash(date:*)", "Bash(cat:*)", "Bash(ls:*)",
         "Read", "Write", "Edit", "Glob", "Grep"]
FRAME = """This is a simulation in a scratch project. You are the {role}. Read .claude/skills/{role}/SKILL.md first and follow it.
You cannot spawn agents here: where your role would start a builder, append that task id on its own line to spawn.txt.
The owner is not available: where you would ask them, follow your role's rule for an open question. Do not ask me questions.

{task}"""


# ---- helpers -------------------------------------------------------------------------------------
def run(cmd: list[str], cwd: Path, **kw) -> str:
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True, **kw).stdout


def bd(proj: Path, *args: str) -> str:
    return run(["bd", *args], proj)


def make_card(proj: Path, title: str, **f) -> str:
    args = ["create", "--title", title, "--type", f.pop("type", "task"), "--json"]
    for flag, value in f.items():
        for v in value if isinstance(value, list) else [value]:
            args += [f"--{flag.replace('_', '-')}", v]
    return json.loads(bd(proj, *args))["id"]


def card(proj: Path, cid: str) -> dict:
    return json.loads(bd(proj, "show", cid, "--json"))[0]


def all_cards(proj: Path) -> list[dict]:
    return json.loads(bd(proj, "list", "--all", "--json", "--limit", "0"))  # id and status, no labels


def decisions(proj: Path) -> list[dict]:
    return json.loads(bd(proj, "list", "--all", "-l", "decision", "--status", "waiting_owner", "--json", "--limit", "0"))


def spawned(proj: Path) -> set[str]:
    f = proj / "spawn.txt"
    return {l.strip() for l in f.read_text().splitlines() if l.strip()} if f.exists() else set()


def new_project(dest: Path, overrides: dict | None = None) -> Path:
    dest.mkdir(parents=True)
    run(["git", "init", "-q", "-b", "main"], dest)
    section = (ROOT / "templates" / "team-section.md").read_text().format(roster="pm, tech-lead")  # what `form` writes
    (dest / "CLAUDE.md").write_text(f"# scratch\nA small CLI notes app.\n\n{section}")
    bd(dest, "init", "-q")
    statuses = re.search(r'`bd config set status.custom "([^"]+)"`', (ROOT / "trackers" / "beads.md").read_text())[1]
    bd(dest, "config", "set", "status.custom", statuses)
    for role in ("pm", "tech-lead"):
        run(["uv", "run", str(ROOT / "scripts" / "role_file.py"), "install", role, str(dest)], ROOT)
    if overrides:
        (dest / ".claude" / "meerkit").mkdir(parents=True)
        (dest / ".claude" / "meerkit" / "settings.json").write_text(json.dumps(overrides))
    run(["git", "add", "-A"], dest)
    run(["git", "-c", "user.email=s@s", "-c", "user.name=sim", "commit", "-qm", "scratch"], dest)
    return dest


# ---- scenarios: each is (role, overrides, setup(proj)->ctx, task text(ctx), check(proj, ctx)->(ok, why)) ----
def feature(proj, status, labels, **f):
    return make_card(proj, "Share a note", type="feature", status=status, labels=",".join(labels),
                     priority="2", description="Let a user share a note.", acceptance="1. A shared note opens for the teammate.", **f)


def s_overlap():
    def setup(p):
        f = feature(p, "ready_to_build", ["track:full", "appetite:medium"])
        t = lambda title, files: make_card(p, title, parent=f, labels="eng-task", description=f"Goal: {title}\nFiles: {files}")
        return {"f": f, "a1": t("A1", "src/a/x.py"), "a2": t("A2", "src/a/x.py"), "b": t("B", "src/b/y.py")}
    def check(p, c):
        s = spawned(p)
        ok = c["b"] in s and len({c["a1"], c["a2"]} & s) == 1
        return ok, f"spawned {sorted(s)}; want {c['b']} plus exactly one of {c['a1']}, {c['a2']} (same file serializes)"
    return ("tech-lead", {"modules": {"src/a": "a", "src/b": "b"}}, setup,
            lambda c: f"Card {c['f']} is ready_to_build. Start the first wave: spawn every task that may run now.", check)


def s_appetite():
    def setup(p):
        start = (datetime.date.today() - datetime.timedelta(days=10)).isoformat()
        return {"f": feature(p, "in_progress", ["track:full", "appetite:small"], notes=f"started: {start}"), "n": f"started: {start}"}
    def check(p, c):
        k = card(p, c["f"])
        return k["status"] == "shaping" and k.get("notes", "") != c["n"], f"status={k['status']}; notes grew={k.get('notes','') != c['n']}"
    return ("tech-lead", {}, setup, lambda c: "Session start. Do your start-of-session routine for this board.", check)


def s_fast_escalation():
    def setup(p):
        f = make_card(p, "Add a field", type="feature", status="approved", labels="track:fast", priority="2",
                      description="Add a field to the shared pricing contract that the web app and the mobile app both read.",
                      acceptance="1. The field is present in the response.", notes="small: one field")
        return {"f": f}
    def check(p, c):
        k = card(p, c["f"])
        sent_up = k["status"] == "shaping" and "track:full" in k.get("labels", [])
        return sent_up and not spawned(p), f"status={k['status']} labels={k.get('labels')} spawned={sorted(spawned(p))}"
    return ("tech-lead", {}, setup, lambda c: f"Pull the next card and start it. The card is {c['f']}.", check)


def s_decision_card():
    def setup(p):
        return {}
    def check(p, c):
        cards, d = all_cards(p), decisions(p)
        approved = [k["id"] for k in cards if k["status"] in {"approved", "in_progress"}]
        return bool(d) and not approved, f"decision cards waiting_owner={len(d)}; approved/in_progress={approved}"
    return ("pm", {}, setup, lambda c: "Owner says: 'I want users to share a note with a teammate. Not sure if sharing should be by link or by invite. Shape it, I will look at it later.' Handle it.", check)


def s_review_rounds():
    def setup(p):
        f = feature(p, "in_progress", ["track:full", "appetite:medium"])
        t = make_card(p, "Empty input error", parent=f, labels="eng-task", status="in_progress",
                      description="Goal: show an error on empty input.\nFiles: src/a/x.py",
                      notes="review feedback sent, round 1: handle empty input\nreview feedback sent, round 2: show the error text")
        return {"f": f, "t": t}
    def check(p, c):
        d = decisions(p)
        return bool(d), f"decision cards waiting_owner={len(d)} (a third feedback round must become a decision card)"
    return ("tech-lead", {}, setup, lambda c: f"The builder for task {c['t']} reports done again. Reviewing the diff: acceptance line 2 (error text shown on empty input) is still missing. Handle it.", check)


def s_open_question():
    def setup(p):
        f = feature(p, "shaping", ["track:full", "appetite:medium"], notes="Open: should notes be shared per user or per team?")
        return {"f": f}
    def check(p, c):
        k = card(p, c["f"])
        return k["status"] == "shaping" and bool(decisions(p)), f"status={k['status']}; decision cards waiting_owner={len(decisions(p))}"
    return ("pm", {}, setup, lambda c: f"Owner says: approve {c['f']}, I want to start building today.", check)


SCENARIOS = {f.__name__[2:]: f for f in (s_overlap, s_appetite, s_fast_escalation, s_decision_card, s_review_rounds, s_open_question)}


# ---- runner --------------------------------------------------------------------------------------
def run_one(name: str, n: int, out: Path, args) -> dict:
    role, overrides, setup, task, check = SCENARIOS[name]()
    proj = new_project(out / f"{name}-{n}" / "project", overrides)
    ctx = setup(proj)
    if args.dry:
        ok, why = check(proj, ctx)
        return {"name": name, "ok": ok, "why": f"DRY (a pass here means the check is vacuous): {why}", "cost": 0, "turns": 0}
    cmd = ["claude", "-p", "--plugin-dir", str(ROOT), "--model", args.model, "--output-format", "stream-json", "--verbose",
           "--max-budget-usd", str(args.budget), "--no-session-persistence", "--disallowedTools", "Agent",
           "--allowedTools", *TOOLS, "--", FRAME.format(role=role, root=ROOT, task=task(ctx))]
    try:
        res = subprocess.run(cmd, cwd=proj, capture_output=True, text=True, timeout=args.timeout)
    except subprocess.TimeoutExpired:
        return {"name": name, "ok": False, "why": f"timeout after {args.timeout}s", "cost": 0, "turns": 0}
    (out / f"{name}-{n}" / "trace.jsonl").write_text(res.stdout)  # every tool call, for diagnosis without a re-run
    (out / f"{name}-{n}" / "stderr.txt").write_text(res.stderr)
    finals = [e for e in map(json.loads, filter(None, res.stdout.splitlines())) if e.get("type") == "result"]
    if res.returncode != 0 or not finals or finals[-1].get("is_error"):
        cause = finals[-1].get("subtype") if finals else res.stderr[:300]
        return {"name": name, "ok": False, "why": f"RUN ERROR (exit {res.returncode}): {cause}", "cost": 0, "turns": 0}
    data = finals[-1]
    ok, why = check(proj, ctx)
    denied = [d.get("tool_input", {}).get("command", d.get("tool_name")) for d in data.get("permission_denials", [])]
    return {"name": name, "ok": ok, "why": why + (f"; DENIED: {denied}" if denied else ""),
            "cost": data.get("total_cost_usd", 0), "turns": data.get("num_turns", 0), "reply": data.get("result", "")[:600]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", default=",".join(SCENARIOS))
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--budget", type=float, default=1.0, help="max USD per run")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    out = args.out / datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    results = []
    for name in args.only.split(","):
        for n in range(1, args.runs + 1):
            r = run_one(name, n, out, args)
            results.append(r)
            print(f"{'PASS' if r['ok'] else 'FAIL'}  {name}-{n}  ${r['cost']:.2f} {r['turns']} turns\n      {r['why']}", flush=True)
    (out / "results.json").write_text(json.dumps(results, indent=2))
    passed = sum(r["ok"] for r in results)
    print(f"\n{passed}/{len(results)} passed; total ${sum(r['cost'] for r in results):.2f}; details in {out}")
    # dry run inverts: every check must FAIL on an untouched board
    return int(passed != 0) if args.dry else int(passed != len(results))


if __name__ == "__main__":
    sys.exit(main())
