#!/usr/bin/env python3
"""Memory of what The Daily Reconcile already printed, so the same news is not reported twice.

  history.py show  [days]          list items printed in the last N days (default 10)
  history.py check content.json    exit 1 and list every item that repeats a recent one
  history.py add   content.json    record today's issue (run after it is printed)

History lives in ../history.json (next to inbox/), one entry per issue date.
"""
import difflib, json, os, re, sys
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
HIST = os.path.join(os.path.dirname(HERE), "history.json")
STOP = set("a an the and or of to in on for with from by is are be as at its it new now this that how why what".split())


def load():
    try:
        return json.load(open(HIST))
    except (OSError, ValueError):
        return []


def norm_url(u):
    u = re.sub(r"^https?://(www\.)?", "", u.strip().lower())
    return u.split("#")[0].split("?")[0].rstrip("/")


def words(t):
    return {w for w in re.findall(r"[a-z0-9][a-z0-9.\-]+", t.lower()) if w not in STOP}


def items(c):
    """News items of an issue: (kind, headline, urls). Newsroom releases are keyed by component and version."""
    out = []
    for kind, it in [("lead", c.get("lead", {}))] + [("story", s) for s in c.get("stories", [])] + \
                    [("brief", b) for b in c.get("briefs", [])]:
        urls = it.get("urls") or ([it["url"]] if it.get("url") else [])
        out.append({"kind": kind, "headline": it.get("headline", ""), "urls": [norm_url(u) for u in urls]})
    for p in (c.get("krateo") or {}).get("products", []):
        for r in p.get("releases", []):
            out.append({"kind": "release", "headline": f"{r.get('component', '')} {r.get('version', '')}".strip(),
                        "urls": []})
    return out


def recent(days):
    since = (date.today() - timedelta(days=days)).isoformat()
    return [e for e in load() if e.get("date", "") >= since and e.get("date") != date.today().isoformat()]


def similar(a, b):
    if a["kind"] == "release" or b["kind"] == "release":
        return a["kind"] == b["kind"] == "release" and a["headline"].lower() == b["headline"].lower()
    if set(a["urls"]) & set(b["urls"]):
        return True
    wa, wb = words(a["headline"]), words(b["headline"])
    overlap = len(wa & wb) / max(1, min(len(wa), len(wb)))
    ratio = difflib.SequenceMatcher(None, a["headline"].lower(), b["headline"].lower()).ratio()
    return overlap >= 0.6 or ratio >= 0.72


def check(path, days=10):
    today = items(json.load(open(path)))
    problems = []
    for e in recent(days):
        for old in e["items"]:
            for new in today:
                if similar(new, old):
                    problems.append(f"REPEAT {new['kind']}: \"{new['headline']}\" ~ {e['date']} {old['kind']}: \"{old['headline']}\"")
    for i, a in enumerate(today):            # the same story twice in one issue
        for b in today[i + 1:]:
            if a["kind"] != "release" and similar(a, b):
                problems.append(f"DUPLICATE in today's issue: \"{a['headline']}\" ~ \"{b['headline']}\"")
    print("\n".join(problems) if problems else "OK: nothing repeats the last %d days" % days)
    return 1 if problems else 0


def add(path):
    c = json.load(open(path))
    d = c.get("date") or date.today().isoformat()
    d = d if re.match(r"\d{4}-\d{2}-\d{2}$", d) else date.today().isoformat()
    h = [e for e in load() if e.get("date") != d]
    h.append({"date": d, "items": items(c)})
    h = sorted(h, key=lambda e: e["date"])[-60:]
    json.dump(h, open(HIST, "w"), indent=1)
    print(f"recorded {len(items(c))} items for {d}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    if cmd == "check":
        sys.exit(check(sys.argv[2]))
    elif cmd == "add":
        add(sys.argv[2])
    else:
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        for e in recent(n):
            for it in e["items"]:
                print(f"{e['date']}  {it['kind']:<7} {it['headline']}  {' '.join(it['urls'][:1])}")
