"""Opens a Chrome tab with the day's post already written, ready to publish.

    python3 tools/open_post.py <post.txt> <YYYY-MM-DD> [--url-only]

LinkedIn pre-fills its composer from /feed/?shareActive=true&text=..., so the morning run can
leave the post waiting rather than leaving you to paste it. What it cannot do is choose who
posts: the composer always opens as the member and resets to them every time, so publishing as
the page is three clicks - the identity dropdown, The Daily Reconcile, then Publish. That was
measured against the live composer, not assumed.

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
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paperconf import conf, site_url                      # noqa: E402
from newsletter_send import guard                         # noqa: E402

COMPOSER = "https://www.linkedin.com/feed/?shareActive=true&text="
DROP = r"\s*Swipe through the PDF below\.?"


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

    # open -a keeps it in Chrome specifically; the composer needs the session that is signed in
    # as a page admin, and the default browser may not be that one.
    for cmd in (["open", "-a", "Google Chrome", url], ["open", url]):
        if subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
            print(f"POST TAB OPENED ({len(text)} chars, publish as the page: 3 clicks)")
            return
    print("POST FAILED: could not open a browser tab")
    sys.exit(1)


if __name__ == "__main__":
    main()
