#!/usr/bin/env python3
"""SDD board: file-based kanban over .claude/sdd/board/{FEATURE}/*.md task files.

Stdlib only, Python 3.7+. Task files are the source of truth; nothing else is stored.

  board.py list
  board.py show  FEATURE
  board.py next  FEATURE
  board.py move  FEATURE ID STATUS [--force] [--note TEXT]
  board.py check FEATURE
  board.py html  FEATURE
"""
import argparse
import datetime
import html
import json
import re
import sys
from pathlib import Path

STATUSES = ["backlog", "ready", "in-progress", "review", "done", "blocked"]
TRANSITIONS = {
    "backlog": {"ready", "blocked"},
    "ready": {"backlog", "in-progress", "blocked"},
    "in-progress": {"ready", "review", "blocked"},
    "review": {"in-progress", "done", "blocked"},
    "done": {"review"},
    "blocked": {"backlog", "ready", "in-progress"},
}
FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.S)
DEFAULT_ROOT = Path(__file__).resolve().parents[2] / "sdd" / "board"


class Task:
    def __init__(self, path):
        self.path = path
        text = path.read_text(encoding="utf-8")
        m = FM_RE.match(text)
        if not m:
            raise ValueError("%s: missing frontmatter" % path.name)
        self.body = text[m.end():]
        self.meta = {}
        for line in m.group(1).splitlines():
            if ":" in line and not line.startswith(" "):
                k, v = line.split(":", 1)
                self.meta[k.strip()] = v.strip()

    @property
    def id(self):
        return self.meta.get("id", "")

    @property
    def status(self):
        return self.meta.get("status", "")

    @property
    def title(self):
        return self.meta.get("title", "").strip("\"'")

    @property
    def agent(self):
        return self.meta.get("agent", "")

    @property
    def files(self):
        raw = self.meta.get("files", "[]").strip("[]")
        return [f.strip().strip("\"'") for f in raw.split(",") if f.strip()]

    @property
    def deps(self):
        raw = self.meta.get("depends_on", "[]").strip("[]")
        return [d.strip().strip("\"'") for d in raw.split(",") if d.strip()]

    def set(self, key, value):
        text = self.path.read_text(encoding="utf-8")
        m = FM_RE.match(text)
        fm = m.group(1)
        pat = re.compile(r"^%s:.*$" % re.escape(key), re.M)
        line = "%s: %s" % (key, value)
        fm = pat.sub(line, fm) if pat.search(fm) else fm + "\n" + line
        self.path.write_text("---\n%s\n---\n%s" % (fm, text[m.end():]), encoding="utf-8")
        self.meta[key] = str(value)


def feature_dir(root, feature):
    d = root / feature
    if not d.is_dir():
        sys.exit("no board for %s (looked in %s)" % (feature, d))
    return d


def load(root, feature):
    tasks = []
    for p in sorted(feature_dir(root, feature).glob("*.md")):
        if p.name.startswith("_"):
            continue
        tasks.append(Task(p))
    return tasks


def by_id(tasks):
    return {t.id: t for t in tasks}


def deps_done(t, ids):
    return all(d in ids and ids[d].status == "done" for d in t.deps)


def problems(tasks):
    out = []
    ids = by_id(tasks)
    seen = set()
    for t in tasks:
        if t.id in seen:
            out.append("duplicate id %s" % t.id)
        seen.add(t.id)
        if t.status not in STATUSES:
            out.append("%s: invalid status '%s'" % (t.id, t.status))
        for d in t.deps:
            if d not in ids:
                out.append("%s: depends_on unknown id %s" % (t.id, d))
            elif d == t.id:
                out.append("%s: depends on itself" % t.id)
        if t.status in ("in-progress", "review", "done"):
            open_deps = [d for d in t.deps if d in ids and ids[d].status != "done"]
            if open_deps:
                out.append("%s: %s but deps not done: %s" % (t.id, t.status, ", ".join(open_deps)))
    color = {}

    def visit(n, stack):
        color[n] = 1
        for d in ids[n].deps:
            if d not in ids:
                continue
            if color.get(d) == 1:
                out.append("cycle: " + " -> ".join(stack + [n, d]))
            elif d not in color:
                visit(d, stack + [n])
        color[n] = 2

    for t in tasks:
        if t.id not in color:
            visit(t.id, [])
    return out


def log_line(root, feature, text):
    log = feature_dir(root, feature) / "_log.md"
    new = not log.exists()
    with log.open("a", encoding="utf-8") as f:
        if new:
            f.write("# Board log\n\n")
        f.write("- %s  %s\n" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), text))


def cmd_list(root, _a):
    if not root.is_dir():
        print("no boards")
        return
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        tasks = load(root, d.name)
        counts = ["%s=%d" % (s, sum(1 for t in tasks if t.status == s)) for s in STATUSES]
        print("%s  %s" % (d.name, "  ".join(c for c in counts if not c.endswith("=0"))))


def cmd_show(root, a):
    tasks = load(root, a.feature)
    ids = by_id(tasks)
    print("BOARD %s  (%d/%d done)" % (a.feature, sum(t.status == "done" for t in tasks), len(tasks)))
    for s in STATUSES:
        col = [t for t in tasks if t.status == s]
        print("\n== %s (%d)" % (s.upper(), len(col)))
        for t in col:
            dep = ""
            if t.deps:
                dep = "  <- " + ",".join(t.deps)
                if s in ("backlog", "ready") and not deps_done(t, ids):
                    dep += " (waiting)"
            print("  %s  %s%s%s" % (t.id, t.title, "  @" + t.agent if t.agent else "", dep))


def cmd_next(root, a):
    tasks = load(root, a.feature)
    ids = by_id(tasks)
    busy = [t for t in tasks if t.status == "in-progress"]
    ready = [t for t in tasks if t.status in ("backlog", "ready") and deps_done(t, ids)]
    if busy:
        print("in-progress: " + ", ".join(t.id for t in busy))
    if ready:
        print("next: " + ", ".join("%s %s" % (t.id, t.title) for t in ready))
        if len(ready) > 1:
            print("(all listed are unblocked and independent)")
    elif not busy:
        pending = [t for t in tasks if t.status != "done"]
        print("board complete" if not pending else "nothing unblocked; check blocked/review tasks")


def cmd_move(root, a):
    tasks = load(root, a.feature)
    ids = by_id(tasks)
    if a.id not in ids:
        sys.exit("unknown id %s" % a.id)
    if a.status not in STATUSES:
        sys.exit("status must be one of: " + ", ".join(STATUSES))
    t = ids[a.id]
    old = t.status
    if not a.force:
        if a.status not in TRANSITIONS.get(old, set()):
            sys.exit("illegal move %s -> %s (allowed: %s)" % (old, a.status, ", ".join(sorted(TRANSITIONS.get(old, [])))))
        if a.status in ("ready", "in-progress") and not deps_done(t, ids):
            waiting = [d for d in t.deps if d not in ids or ids[d].status != "done"]
            sys.exit("%s waiting on: %s" % (t.id, ", ".join(waiting)))
        if a.status == "blocked" and not a.note:
            sys.exit("--note required when blocking")
    today = datetime.date.today().isoformat()
    t.set("status", a.status)
    t.set("updated", today)
    log_line(root, a.feature, "%s  %s -> %s%s" % (t.id, old, a.status, "  (%s)" % a.note if a.note else ""))
    print("%s: %s -> %s" % (t.id, old, a.status))
    if a.status == "done":
        for u in tasks:
            if u.status == "backlog" and deps_done(u, ids):
                u.set("status", "ready")
                u.set("updated", today)
                log_line(root, a.feature, "%s  backlog -> ready  (auto, deps done)" % u.id)
                print("%s: backlog -> ready (unblocked)" % u.id)


def cmd_check(root, a):
    errs = problems(load(root, a.feature))
    if errs:
        print("\n".join(errs))
        sys.exit(1)
    print("ok")


def read_log(root, feature):
    log = feature_dir(root, feature) / "_log.md"
    entries = []
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^- (\d{4}-\d\d-\d\d \d\d:\d\d)\s+(S\d+)\s+(.*)$", line)
            if m:
                entries.append({"id": m.group(2), "text": "%s  %s" % (m.group(1), m.group(3))})
    return entries


def cmd_html(root, a):
    tasks = load(root, a.feature)
    data = {
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "agent": t.agent,
                "deps": t.deps,
                "files": t.files,
                "updated": t.meta.get("updated", ""),
                "path": t.path.name,
                "body": t.body,
            }
            for t in tasks
        ],
        "log": read_log(root, a.feature),
    }
    payload = json.dumps(data).replace("</", "<\/")
    tpl = (Path(__file__).with_name("board.html.tpl")).read_text(encoding="utf-8")
    page = tpl.replace("__FEATURE__", html.escape(a.feature)).replace("__DATA__", payload)
    out = feature_dir(root, a.feature) / "BOARD.html"
    out.write_text(page, encoding="utf-8")
    print(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    sub = ap.add_subparsers(dest="cmd")
    sub.required = True
    sub.add_parser("list")
    for name in ("show", "next", "check", "html"):
        sub.add_parser(name).add_argument("feature")
    mv = sub.add_parser("move")
    mv.add_argument("feature")
    mv.add_argument("id")
    mv.add_argument("status")
    mv.add_argument("--force", action="store_true")
    mv.add_argument("--note", default="")
    a = ap.parse_args()
    handlers = {"list": cmd_list, "show": cmd_show, "next": cmd_next, "move": cmd_move, "check": cmd_check, "html": cmd_html}
    handlers[a.cmd](a.root, a)


if __name__ == "__main__":
    main()
