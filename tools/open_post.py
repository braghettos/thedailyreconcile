"""Opens a Chrome tab with the day's post already written, ready to publish.

    python3 tools/open_post.py <post.txt> <YYYY-MM-DD> [--url-only]

LinkedIn pre-fills its composer from /feed/?shareActive=true&text=..., so the morning run can
leave the post waiting rather than leaving you to paste it. What it cannot do is choose who
posts: the composer always opens as the member and resets to them every time, so publishing as
the page is three clicks - the identity dropdown, The Daily Reconcile, then Publish. That was
measured against the live composer, not assumed.

The tab is made with AppleScript and then looked for, rather than handed to "open". "open" exits
0 whether or not the browser ever receives the URL, and on this machine it receives nothing: a
morning run logged POST TAB OPENED for a tab that was never there, and Chrome's own history had
no visit to show for it. Anything this script claims is now checked before it is printed.

The front page is revealed in Finder alongside the tab. LinkedIn will not take an image from a
URL, so the picture has to be dragged in; a post carrying the masthead travels further than a
wall of text, and one drag is cheaper than hunting for the file. That reveal is read back out of
Finder's selection for the same reason.

Two edits are made to the text on the way:

  - "Swipe through the PDF below" is dropped. It is written for a document carousel, and this
    is a text post with no PDF attached; left in, it points at something that is not there.
  - the edition link is appended, because the post otherwise describes a paper the reader has
    no way to reach.

The post is already written to be public - step 6 of the prompt forbids links, PR numbers and
repository names - but it is checked once more before a tab opens, with the same guard the
newsletter uses.
"""
import os
import re
import subprocess
import time
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paperconf import conf, site_url                      # noqa: E402
from newsletter_send import guard                         # noqa: E402

COMPOSER = "https://www.linkedin.com/feed/?shareActive=true&text="
DROP = r"\s*Swipe through the PDF below\.?"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Makes the tab, remembers its id, then goes looking for that id: a tab that was refused, or
# closed again by a browser that did not like the URL, reports "gone" instead of success. A
# window is created first if Chrome is running with none open, which is where "make new tab at
# front window" would otherwise fail.
TAB_SCRIPT = """tell application "Google Chrome"
	if (count of windows) is 0 then
		set w to make new window
	else
		set w to front window
	end if
	set t to make new tab at end of tabs of w with properties {URL:"__URL__"}
	set wanted to id of t
	delay 1
	repeat with ww in windows
		repeat with tt in tabs of ww
			if (id of tt) is wanted then return "ok"
		end repeat
	end repeat
	return "gone"
end tell"""


def osa(script):
    """Runs an AppleScript, returning (stdout, reason-it-failed)."""
    p = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    out = (p.stdout or "").strip()
    if p.returncode == 0:
        return out, ""
    why = (p.stderr or "").strip().splitlines()
    return out, (why[-1] if why else f"osascript exit {p.returncode}")


def open_tab(url):
    """Puts the URL in a Chrome tab. Returns the reason it did not, or "" on success."""
    script = TAB_SCRIPT.replace("__URL__", url.replace("\\", "\\\\").replace('"', '\\"'))
    out, why = osa(script)
    if why:
        return why
    return "" if out == "ok" else f"Chrome did not keep the tab ({out or 'no answer'})"


def reveal_front_page(day):
    """Selects the day's front page in Finder, ready to drag into the composer."""
    png = os.path.join(ROOT, "docs", "editions", day, "page-1.png")
    if not os.path.exists(png):
        return ""
    if subprocess.call(["open", "-R", png],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
        return ""
    # "open -R" returns before Finder has finished moving, so the selection is read back with a
    # little patience: a claim about what Finder is showing should be a claim about what Finder
    # is showing. Unproven, the line is simply left off; the tab is the part that matters.
    for _ in range(10):
        sel, _ = osa('tell application "Finder" to get selection as string')
        if "page-1.png" in sel and day in sel:
            return ", front page ready to drag"
        time.sleep(0.3)
    return ""


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        print(__doc__.strip())
        sys.exit(2)
    post_path, day = args[0], args[1]
    if not os.path.exists(post_path):
        print(f"POST SKIPPED: {post_path} missing")
        return

    text = re.sub(DROP, "", open(post_path).read().strip())
    base = site_url()
    if base:
        text += f"\n\nRead today's edition: {base}/"

    hit = guard(text, [conf("NEWSROOM_PRIVATE_ORG"), conf("OWNER_FIRSTNAME"), "personal edition"])
    if hit:
        print(f"POST FAILED: text contains {', '.join(hit)} - no tab opened")
        sys.exit(1)

    url = COMPOSER + urllib.parse.quote(text, safe="")
    if "--url-only" in sys.argv:
        print(url)
        return

    why = open_tab(url)
    if why:
        # The post itself is already archived; what is expensive to rebuild by hand is the
        # composer link, so it is left somewhere clickable instead of only in a log line.
        spare = os.path.join(os.path.dirname(os.path.abspath(post_path)), f"post-url-{day}.txt")
        try:
            open(spare, "w").write(url + "\n")
            where = f"; the link is in {spare}"
        except OSError:
            where = ""
        print(f"POST FAILED: no tab opened - {why}{where}")
        sys.exit(1)

    extra = reveal_front_page(day)
    print(f"POST TAB OPENED ({len(text)} chars, publish as the page: 3 clicks{extra})")


if __name__ == "__main__":
    main()
