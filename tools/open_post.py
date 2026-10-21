"""Opens a Chrome tab with the day's post already written, ready to publish.

    python3 tools/open_post.py <post.txt> <YYYY-MM-DD> [--url-only]

LinkedIn pre-fills its composer from /feed/?shareActive=true&text=..., so the morning run can
leave the post waiting rather than leaving you to paste it. What it cannot do is choose who
posts: the composer always opens as the member and resets to them every time, so publishing as
the page is three clicks - the identity dropdown, The Daily Reconcile, then Publish. That was
measured against the live composer, not assumed.

Getting a URL into Chrome is the awkward part, and two of the three ways do not work here:

  - "open" exits 0 whether or not the browser ever receives the URL, and on this machine it
    receives nothing, in every form - open -a, open -b, plain open, from a shell and from
    launchd. A morning run logged a tab that was never there, and Chrome's history had no visit
    to show for it. The exit code was never evidence.
  - AppleScript does work, and can be asked afterwards whether the tab exists, which is why it
    is still the first thing tried. But Chrome does not always answer: a run at 07:01 sat for
    the full two-minute AppleEvent timeout and gave up with -1712, having been asked moments
    after a heavy unattended job. So each attempt is given a short timeout instead of a long
    one, and a browser that is merely busy is asked again rather than written off.
  - Chrome's own executable takes a URL and hands it to the running instance through neither
    LaunchServices nor AppleEvents. It is the fallback, for the case where Chrome is awake
    enough to take a tab but not to answer questions about it.

Nothing is claimed that was not checked. A tab made by AppleScript is looked for by id; one
handed to the executable is looked for by URL, and if Chrome will not say, the line says that
rather than implying a tab nobody has seen. Either way the composer link is also written to a
file, so a failed morning costs a click rather than the post.

The front page is revealed in Finder alongside the tab. LinkedIn will not take an image from a
URL, so the picture has to be dragged in; a post carrying the masthead travels further than a
wall of text, and one drag is cheaper than hunting for the file. That reveal is read back out of
Finder's selection for the same reason as everything else here.

Two edits are made to the text on the way:

  - "Swipe through the PDF below" is dropped. It is written for a document carousel, and this
    is a text post with no PDF attached; left in, it points at something that is not there.
  - "Curated and summarised with Claude." is dropped, because the owner does not want it on
    LinkedIn. The paper still says who wrote it, on page two and on the site.
  - the edition link is appended, because the post otherwise describes a paper the reader has
    no way to reach.

The post is already written to be public - step 6 of the prompt forbids links, PR numbers and
repository names - but it is checked once more before a tab opens, with the same guard the
newsletter uses.
"""
import os
import re
import subprocess
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paperconf import conf, site_url                      # noqa: E402
from newsletter_send import guard                         # noqa: E402

COMPOSER = "https://www.linkedin.com/feed/?shareActive=true&text="
# Taken out of the post on the way to the composer: the carousel line, which points at a PDF
# that is not attached to a text post, and the Claude credit, which the owner does not want on
# LinkedIn. The prompt no longer asks for either, so these are a second line of defence for a
# day when the model writes one anyway.
DROP = (r"\s*Curated and summarised with Claude\.?", r"\s*Swipe through the PDF below\.?")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# LinkedIn rewrites the composer URL the moment it loads, so a tab that was opened at
# /feed/?shareActive=... is sitting at /sharing/compose by the time anyone looks for it.
COMPOSER_MARKS = ("shareActive", "sharing/compose")

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

FIND_SCRIPT = """tell application "Google Chrome"
	repeat with ww in windows
		repeat with tt in tabs of ww
			set u to (URL of tt)
			if u is not missing value then
				if u contains "__MARK__" then return "ok"
			end if
		end repeat
	end repeat
	return "gone"
end tell"""


def osa(script, seconds=20):
    """Runs an AppleScript under a timeout, returning (stdout, reason-it-failed).

    The timeout is the point: AppleEvents default to two minutes, and a browser that is not
    going to answer should cost seconds, not the best part of the morning run.
    """
    wrapped = f"with timeout of {seconds} seconds\n{script}\nend timeout"
    try:
        p = subprocess.run(["osascript", "-e", wrapped], capture_output=True, text=True,
                           timeout=seconds + 15)
    except subprocess.TimeoutExpired:
        return "", f"osascript did not return within {seconds + 15}s"
    out = (p.stdout or "").strip()
    if p.returncode == 0:
        return out, ""
    why = (p.stderr or "").strip().splitlines()
    return out, (why[-1] if why else f"osascript exit {p.returncode}")


def composer_tab_exists():
    """Asks Chrome whether a composer tab is open. Returns (yes/no, reason-it-could-not-say)."""
    last = ""
    for mark in COMPOSER_MARKS:
        out, why = osa(FIND_SCRIPT.replace("__MARK__", mark))
        if why:
            last = why
            continue
        if out == "ok":
            return True, ""
    return False, last


def make_tab(url):
    """Asks Chrome for a tab and checks it arrived. Returns the reason it did not, or ""."""
    script = TAB_SCRIPT.replace("__URL__", url.replace("\\", "\\\\").replace('"', '\\"'))
    out, why = osa(script)
    if why:
        return why
    return "" if out == "ok" else f"Chrome did not keep the tab ({out or 'no answer'})"


def hand_off(url):
    """Gives the URL to Chrome's executable, which neither LaunchServices nor AppleEvents touch.

    A running Chrome takes the URL and the process exits straight away. A Chrome that was not
    running becomes that running Chrome instead, so the process stays up: it is left alone, with
    its output detached, and the tab is confirmed the same way as any other.
    """
    if not os.path.exists(CHROME_BIN):
        return f"{CHROME_BIN} is not there"
    try:
        p = subprocess.Popen([CHROME_BIN, url],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
    except OSError as e:
        return f"could not run Chrome directly ({e})"
    for _ in range(20):
        if p.poll() is not None:
            break
        time.sleep(0.5)
    return ""


def open_tab(url):
    """Puts the URL in a Chrome tab. Returns (what-to-say-about-it, reason-it-failed).

    AppleScript first, because it can prove what it did. A browser that is busy rather than
    broken is asked again, with a little more patience each time, before the executable is
    tried instead.
    """
    why = ""
    for wait in (0, 5, 15, 30):
        if wait:
            time.sleep(wait)
        why = make_tab(url)
        if not why:
            return "", ""

    handed = hand_off(url)
    if handed:
        return "", f"{why}; and {handed}"
    there, blind = composer_tab_exists()
    if there:
        return " (opened the long way round)", ""
    if blind:
        # Chrome took the URL and will not discuss it. Saying "opened" would be a guess, and
        # saying "failed" would send someone looking for a tab that is probably sitting there.
        return " (handed to Chrome, which would not confirm it)", ""
    return "", f"{why}; Chrome took the URL but no composer tab appeared"


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


def keep_link(post_path, day, url):
    """Leaves the composer link somewhere clickable. Returns what to say about where."""
    spare = os.path.join(os.path.dirname(os.path.abspath(post_path)), f"post-url-{day}.txt")
    try:
        open(spare, "w").write(url + "\n")
        return f"; the link is in {spare}"
    except OSError:
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

    text = open(post_path).read().strip()
    for pattern in DROP:
        text = re.sub(pattern, "", text)
    text = text.strip()
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

    # The post itself is archived either way; what is expensive to rebuild by hand is the
    # composer link, so it is kept whatever happens next.
    where = keep_link(post_path, day, url)

    how, why = open_tab(url)
    if why:
        print(f"POST FAILED: no tab opened - {why}{where}")
        sys.exit(1)

    extra = reveal_front_page(day)
    print(f"POST TAB OPENED ({len(text)} chars, publish as the page: 3 clicks{extra}){how}")


if __name__ == "__main__":
    main()
