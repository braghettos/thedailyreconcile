"""Reads one setting from paper.conf, the way the morning run does.

paper.conf is shell, not INI: the installer sources it and so does morning-run.sh. These
scripts are run from the repo clone, so they cannot source it; they read the one line they
need. The environment wins, so a value can always be overridden for a single run.
"""
import os
import re

PATHS = (
    os.path.join(os.path.expanduser("~"), "DailyReconcile", "paper.conf"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "paper.conf"),
)


def conf(name, default=""):
    if os.environ.get(name):
        return os.environ[name]
    for p in PATHS:
        if os.path.exists(p):
            for line in open(p):
                m = re.match(rf'\s*{name}\s*=\s*"?([^"#\n]*)"?', line)
                if m:
                    return m.group(1).strip()
    return default


def site_url():
    """Base URL of the published site, without a trailing slash.

    SITE_URL wins, so a custom domain needs no other change. Otherwise it is derived from
    SITE_REPO, which is what GitHub Pages serves before a CNAME exists.
    """
    url = conf("SITE_URL")
    if not url:
        repo = conf("SITE_REPO")
        if not repo or "/" not in repo:
            return ""
        owner, name = repo.split("/", 1)
        url = f"https://{owner}.github.io/{name}"
    return url.rstrip("/")
