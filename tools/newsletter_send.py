"""Sends one edition to the Buttondown newsletter: the post text, the front page, the PDF link.

    python3 tools/newsletter_send.py <post.txt> <content.json> <YYYY-MM-DD> [--dry-run] [--out FILE]

Settings come from paper.conf (BUTTONDOWN_TOKEN_FILE, NEWSLETTER_STATUS, NEWSLETTER_FORMAT,
SITE_URL) or from the environment. Without a token the script exits 0 and says it skipped, so
an unconfigured newsletter never fails the morning run.

Two deliberate choices, both to keep a person between an unattended research run and a
stranger's inbox:

  - NEWSLETTER_STATUS defaults to "draft". The edition is composed and uploaded every morning,
    and you press send. This is the same reasoning DESIGN.md gives for publishing LinkedIn by
    hand. Set it to "about_to_send" once you trust it, and the morning run sends on its own.
  - The body is checked against the private newsroom slug and the owner's name before it
    leaves, mirroring the check the prompt already makes on the public PDF. A match is fatal:
    nothing is sent.

The PDF is linked, never attached: Buttondown bills attachments as an add-on, and a link keeps
the issue readable from the archive long after the mail client has forgotten it.
"""
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paperconf import conf, site_url               # noqa: E402

API = "https://api.buttondown.com/v1/emails"
PAPER, INK, ACCENT, MUTED = "#F6F0E1", "#111111", "#991717", "#5a5346"
SERIF = "Georgia,'Times New Roman',Times,serif"
SANS = "'Helvetica Neue',Helvetica,Arial,sans-serif"
MONO = "'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


def long_date(iso):
    d = date.fromisoformat(iso)
    return f"{WEEKDAYS[d.weekday()]}, {MONTHS[d.month - 1]} {d.day}, {d.year}"


def parse_post(text):
    """Pulls the parts of the LinkedIn post that belong in an email.

    The post is already written to be public, so it is the safest source for the prose. Three
    things in it are LinkedIn's and not email's: the hashtags, "Swipe through the PDF below",
    which points at a carousel that does not exist here, and the "Curated and summarised with
    Claude" sign-off, which the email footer says properly and at more length.
    """
    drop = (r"swipe through the pdf[^.]*\.?", r"curated and summarised with claude\.?")
    lines = [ln.rstrip() for ln in text.strip().splitlines()]
    out = {"lead": "", "also": [], "tip": "", "tip_code": ""}
    body = []
    for ln in lines[1:]:                                    # line 0 is the paper's own dateline
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("→"):
            out["also"].append(s.lstrip("→ ").strip())
        elif re.match(r"^(kubectl|helm) tip:", s, re.I):
            out["tip"], _, out["tip_code"] = (p.strip() for p in s.partition(":"))
        elif s.lower().startswith("also in today"):
            continue
        else:
            for pat in drop:
                s = re.sub(pat, "", s, flags=re.I).strip()
            if s:
                body.append(s)
    out["lead"] = " ".join(p for p in body if p)
    return out


def guard(body, parts):
    """Refuses to send anything carrying the private newsroom or the owner's name."""
    needles = [n.strip().lower() for n in parts if n and len(n.strip()) > 2]
    hay = body.lower()
    return [n for n in needles if n in hay]


# --------------------------------------------------------------------------- the HTML email
def btn(url, label, filled):
    bg, fg = (INK, PAPER) if filled else (PAPER, INK)
    return (
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        f'style="display:inline-block;margin:0 8px 8px 0"><tr>'
        f'<td bgcolor="{bg}" style="border:2px solid {INK};padding:11px 18px">'
        f'<a href="{html.escape(url)}" style="font-family:{SANS};font-size:14px;font-weight:bold;'
        f'color:{fg};text-decoration:none;display:inline-block">{html.escape(label)}</a>'
        f"</td></tr></table>")


def bars(factbox):
    items = [i for i in factbox.get("items", []) if isinstance(i.get("value"), int)]
    if not items:
        return ""
    top = max(i["value"] for i in items) or 1
    rows = ""
    for n, i in enumerate(items):
        pct = max(2, round(i["value"] * 100 / top))
        fill = ACCENT if i["value"] == top else INK
        rows += (
            f'<tr>'
            f'<td style="font-family:{SANS};font-size:11px;color:{MUTED};padding:0 8px 5px 0;'
            f'white-space:nowrap">{html.escape(i.get("label", ""))}</td>'
            f'<td width="100%" style="padding:0 8px 5px 0">'
            f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">'
            f'<tr><td bgcolor="#e2dac6" height="9" style="font-size:0;line-height:0">'
            f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
            f'width="{pct}%"><tr><td bgcolor="{fill}" height="9" '
            f'style="font-size:0;line-height:0">&nbsp;</td></tr></table>'
            f'</td></tr></table></td>'
            f'<td align="right" style="font-family:{SANS};font-size:11px;font-weight:bold;'
            f'color:{INK};padding:0 0 5px 0">{i["value"]}</td>'
            f"</tr>")
    return (
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
        f'style="border:1px solid {INK};margin:26px 0 0"><tr><td style="padding:14px 16px">'
        f'<p style="margin:0 0 10px;font-family:{SANS};font-size:11px;font-weight:bold;'
        f'letter-spacing:1px;text-transform:uppercase;color:{INK}">'
        f'{html.escape(factbox.get("title", "By the numbers"))}</p>'
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">'
        f'{rows}</table>'
        f'<p style="margin:8px 0 0;font-family:{SANS};font-size:10px;color:{MUTED}">'
        f'Bars to one scale, highest value {top}</p>'
        f"</td></tr></table>")


def rule(h, colour):
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">'
            f'<tr><td bgcolor="{colour}" height="{h}" '
            f'style="font-size:0;line-height:0">&nbsp;</td></tr></table>')


def build_html(c, post, urls, motto):
    lead = c.get("lead") or {}
    pdf, edition, privacy, source = urls["pdf"], urls["edition"], urls["privacy"], urls["source"]
    also = "".join(
        f'<tr><td valign="top" style="font-family:{SANS};font-size:15px;color:{ACCENT};'
        f'padding:0 8px 12px 0">&rarr;</td>'
        f'<td style="font-family:{SERIF};font-size:15px;line-height:1.55;color:{INK};'
        f'padding:0 0 12px"><span style="border-bottom:1px solid #d8d0bc;display:block;'
        f'padding-bottom:12px">{html.escape(a)}</span></td></tr>'
        for a in post["also"])
    tip = ""
    if post["tip_code"]:
        tip = (
            f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
            f'style="margin:24px 0 0"><tr>'
            f'<td width="3" bgcolor="{ACCENT}" style="font-size:0;line-height:0">&nbsp;</td>'
            f'<td style="padding:2px 0 2px 13px">'
            f'<p style="margin:0 0 4px;font-family:{SANS};font-size:11px;font-weight:bold;'
            f'letter-spacing:1px;text-transform:uppercase;color:{MUTED}">'
            f'{html.escape(post["tip"])}</p>'
            f'<code style="font-family:{MONO};font-size:14px;color:{INK};word-break:break-all">'
            f'{html.escape(post["tip_code"])}</code>'
            f"</td></tr></table>")
    # "naked" is Buttondown's raw-HTML mode. "fancy" is its WYSIWYG editor, which cannot
    # represent nested tables or inline styles and shows "some content couldn't be converted"
    # on every issue; the body is still stored and sent byte for byte, but opening it in that
    # editor and saving would rewrite it. Markdown mode is not an option either: this template
    # has blank lines between blocks, which a Markdown processor treats as paragraph breaks and
    # would wrap in <p> tags mid-table.
    return f"""<!-- buttondown-editor-mode: naked -->
<div style="display:none;font-size:0;line-height:0;max-height:0;overflow:hidden;opacity:0">{html.escape(lead.get('deck', ''))}</div>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" bgcolor="{PAPER}" style="background:{PAPER};margin:0;padding:0">
<tr><td align="center" style="padding:0">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600" style="width:600px;max-width:600px">
<tr><td style="padding:32px 36px 30px;font-family:{SERIF};color:{INK}">

  <p style="margin:0;text-align:center;font-family:{SERIF};font-size:34px;font-weight:bold;letter-spacing:-0.5px;color:{INK};line-height:1.05">The Daily Reconcile.</p>
  <p style="margin:8px 0 0;text-align:center;font-family:{SERIF};font-style:italic;font-size:13px;color:{MUTED}">{html.escape(motto)}</p>
  <div style="margin:14px 0 0">{rule(2, INK)}</div>
  <div style="margin:3px 0 0">{rule(1, INK)}</div>

  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:10px 0 22px">
    <tr>
      <td style="font-family:{SANS};font-size:11px;font-weight:bold;letter-spacing:1.4px;text-transform:uppercase;color:{MUTED}">{html.escape(long_date(c['date']))}</td>
      <td align="right" style="font-family:{SANS};font-size:11px;font-weight:bold;letter-spacing:1.4px;text-transform:uppercase;color:{MUTED}">Two pages</td>
    </tr>
  </table>

  <a href="{html.escape(pdf)}" style="text-decoration:none;display:block">
    <img src="{html.escape(urls['thumb'])}" width="596" alt="Front page of the edition of {html.escape(long_date(c['date']))}. Lead story: {html.escape(lead.get('headline',''))}" style="display:block;width:100%;max-width:596px;height:auto;border:1px solid {INK}">
  </a>
  <p style="margin:7px 0 0;text-align:center;font-family:{SANS};font-size:10px;letter-spacing:1px;text-transform:uppercase;color:{MUTED}">Front page &middot; tap to read the PDF</p>

  <p style="margin:26px 0 6px;font-family:{SANS};font-size:11px;font-weight:bold;letter-spacing:1.6px;text-transform:uppercase;color:{ACCENT}">{html.escape(lead.get('kicker',''))}</p>
  <h1 style="margin:0 0 10px;font-family:{SERIF};font-size:25px;line-height:1.22;font-weight:bold;letter-spacing:-0.3px;color:{INK}">
    <a href="{html.escape(edition)}" style="color:{INK};text-decoration:none">{html.escape(lead.get('headline',''))}</a>
  </h1>
  <p style="margin:0 0 18px;font-family:{SERIF};font-size:16px;line-height:1.62;color:{INK}">{html.escape(post['lead'])}</p>

  <div style="margin:0 0 4px">{btn(edition, 'Read this edition', True)}{btn(pdf, 'Download the PDF · 2 pages', False)}</div>

  {bars(c.get('factbox') or {})}

  <div style="margin:30px 0 0">{rule(2, INK)}</div>
  <p style="margin:12px 0 14px;font-family:{SANS};font-size:11px;font-weight:bold;letter-spacing:1.6px;text-transform:uppercase;color:{INK}">Also in today&rsquo;s two pages</p>
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">{also}</table>

  {tip}

  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" bgcolor="#efe8d6" style="margin:28px 0 0;border:1px dashed #8d8676">
    <tr><td style="padding:16px 17px">
      <p style="margin:0 0 6px;font-family:{SERIF};font-size:17px;font-weight:bold;color:{INK}">Want it on paper?</p>
      <p style="margin:0 0 8px;font-family:{SERIF};font-size:14px;line-height:1.55;color:#2c2820">The PDF is laid out for exactly this: A4, two pages, printed on one sheet. It is how this paper is read every morning.</p>
      <p style="margin:0;font-family:{MONO};font-size:12px;color:{MUTED}">A4 &middot; double-sided &middot; flip on the long edge</p>
    </td></tr>
  </table>

  <div style="margin:28px 0 0">{rule(2, INK)}</div>
  <p style="margin:14px 0 10px;font-family:{SERIF};font-style:italic;font-size:13px;line-height:1.6;color:{MUTED}">Researched, written and laid out by Claude Code. Every item links to its source; always check the original.</p>
    <p style="margin:0 0 10px;font-family:{SANS};font-size:11px;line-height:1.65;color:{MUTED}">Made by <a href="{html.escape(urls['owner'])}" style="color:{MUTED}">{html.escape(urls['owner_name'])}</a>, who decides what it covers.</p>
  <p style="margin:0 0 10px;font-family:{SANS};font-size:11px;line-height:1.65;color:{MUTED}">Sources today: {html.escape(c.get('sources_line',''))}</p>
  <p style="margin:0;font-family:{SANS};font-size:11px;line-height:1.65;color:{MUTED}">
    You get this because you asked for it, and for nothing else. We keep your address and your paper preference, and no other data.<br>
    <a href="{html.escape(privacy)}" style="color:{MUTED}">Privacy</a> &middot;
    <a href="{html.escape(source)}" style="color:{MUTED}">Source on GitHub</a>
  </p>

</td></tr></table>
</td></tr></table>"""


def build_text(c, post, urls):
    lead = c.get("lead") or {}
    out = [f"The Daily Reconcile · {long_date(c['date'])}", "",
           lead.get("headline", ""), "", post["lead"], "",
           f"Read this edition: {urls['edition']}",
           f"Download the PDF (2 pages): {urls['pdf']}", ""]
    if post["also"]:
        out += ["Also in today's two pages:"] + [f"- {a}" for a in post["also"]] + [""]
    if post["tip_code"]:
        out += [f"{post['tip']}: {post['tip_code']}", ""]
    out += ["Want it on paper? The PDF is A4, two pages, double-sided, flip on the long edge.",
            "", "Researched, written and laid out by Claude Code. Every item links to its",
            "source; always check the original.",
            f"Made by {urls['owner_name']}, who decides what it covers: {urls['owner']}",
            f"Privacy: {urls['privacy']}"]
    return "\n".join(out)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    out_file = ""
    if "--out" in sys.argv:
        i = sys.argv.index("--out")
        out_file = sys.argv[i + 1] if len(sys.argv) > i + 1 else ""
    if len(args) < 3:
        print(__doc__.strip())
        sys.exit(2)
    post_path, content_path, day = args[0], args[1], args[2]

    token_file = conf("BUTTONDOWN_TOKEN_FILE")
    token = os.environ.get("BUTTONDOWN_TOKEN", "")
    if not token and token_file and os.path.exists(os.path.expanduser(token_file)):
        token = open(os.path.expanduser(token_file)).read().strip()
    base = site_url()
    if not dry and not token:
        print("NEWSLETTER SKIPPED: BUTTONDOWN_TOKEN_FILE not set in paper.conf")
        return
    if not base:
        print("NEWSLETTER SKIPPED: neither SITE_URL nor SITE_REPO is set, so links would be broken")
        return
    for p in (post_path, content_path):
        if not os.path.exists(p):
            print(f"NEWSLETTER SKIPPED: {p} missing")
            return

    c = json.load(open(content_path))
    post = parse_post(open(post_path).read())
    urls = {
        "edition": f"{base}/",
        "pdf": f"{base}/editions/{day}/daily-reconcile-{day}.pdf",
        "thumb": f"{base}/editions/{day}/page-1.png",
        "privacy": f"{base}/privacy.html",
        "source": f"https://github.com/{conf('SITE_REPO')}",
        "owner": conf("OWNER_URL", "https://www.linkedin.com/in/diegobraga86/"),
        "owner_name": conf("OWNER", "Diego Braga"),
    }

    fmt = (conf("NEWSLETTER_FORMAT", "html") or "html").lower()
    body = (build_text(c, post, urls) if fmt == "text"
            else build_html(c, post, urls, c.get("motto", "")))

    # Only fields public_edition() leaves untouched are used above, and the krateo panel is
    # left out entirely. This is the belt to that braces.
    #
    # The guard reads the editorial source, not the rendered body: the footer deliberately
    # credits the owner by name, and scanning the finished email would trip on that every
    # morning. What must never leak is the owner's name arriving through the content - the post
    # text or content.json - which is what these inputs are. Only the fields the email actually
    # renders are listed: "edition" is the personal label ("... personal edition") and is never
    # used here, so including it would fail every morning for a string no subscriber can see.
    lead_ = c.get("lead") or {}
    editorial = "\n".join([
        open(post_path).read(),
        lead_.get("kicker", ""), lead_.get("headline", ""), lead_.get("deck", ""),
        c.get("sources_line", ""), c.get("motto", ""),
        json.dumps(c.get("factbox") or {}, ensure_ascii=False),
    ])
    hit = guard(editorial, [conf("NEWSROOM_PRIVATE_ORG"), conf("OWNER_FIRSTNAME"), "personal edition"])
    if hit:
        print(f"NEWSLETTER FAILED: body contains {', '.join(hit)} - nothing sent")
        sys.exit(1)

    subject = f"The Daily Reconcile · {long_date(day).rsplit(',', 1)[0]}: {(c.get('lead') or {}).get('headline','')}"
    status = conf("NEWSLETTER_STATUS", "draft") or "draft"
    payload = {"subject": subject[:200], "body": body, "status": status}

    if out_file:
        open(out_file, "w").write(body)
        print(f"NEWSLETTER wrote {out_file} ({len(body)} bytes, {fmt})")
    if dry:
        print(f"NEWSLETTER DRY RUN: {status}, {fmt}, {len(body)} bytes, subject: {subject[:90]}")
        return

    req = urllib.request.Request(
        API, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Token {token}", "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            got = json.loads(resp.read() or b"{}")
        where = "SENT" if status == "about_to_send" else f"{status.upper()} CREATED"
        print(f"NEWSLETTER {where} {got.get('id','(no id returned)')}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        hint = ""
        if e.code == 401:
            hint = "  (token rejected - check BUTTONDOWN_TOKEN_FILE)"
        elif e.code in (402, 403):
            hint = "  (plan does not allow this - the free tier may not send via API)"
        print(f"NEWSLETTER FAILED: HTTP {e.code} {detail}{hint}")
    except Exception as e:                                  # network, DNS, bad JSON
        print(f"NEWSLETTER FAILED: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
