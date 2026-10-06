"""Adds one edition to the GitHub Pages site and rebuilds the index.

    python3 tools/publish_site.py <public-pdf> <YYYY-MM-DD> [content.json]

Copies the public PDF into docs/editions/<date>/, renders a page-1 thumbnail, records the
edition in docs/editions.json and regenerates docs/index.html. Committing and pushing is left
to the caller (morning-run.sh), so a failed render never pushes a half-built site.
"""
import datetime, html, json, os, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paperconf import conf                      # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "docs")   # GitHub Pages serves / or /docs only
MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


def long_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{MONTHS[d.month - 1]} {d.day}, {d.year}"


def load_index():
    p = os.path.join(SITE, "editions.json")
    if os.path.exists(p):
        try:
            return json.load(open(p))
        except json.JSONDecodeError:
            pass
    return []


def add_edition(pdf, date, content=None):
    import pymupdf
    dest = os.path.join(SITE, "editions", date)
    os.makedirs(dest, exist_ok=True)
    name = f"daily-reconcile-{date}.pdf"
    target = os.path.join(dest, name)
    if os.path.abspath(pdf) != os.path.abspath(target):   # re-publishing the same date
        shutil.copy(pdf, target)
    doc = pymupdf.open(pdf)
    doc[0].get_pixmap(dpi=96).save(os.path.join(dest, "page-1.png"))
    pages = len(doc)

    entry = {"date": date, "pdf": f"editions/{date}/{name}",
             "thumb": f"editions/{date}/page-1.png", "pages": pages,
             "headline": "", "deck": "", "inside": []}
    if content and os.path.exists(content):
        c = json.load(open(content))
        entry["headline"] = (c.get("lead") or {}).get("headline", "")
        entry["deck"] = (c.get("lead") or {}).get("deck", "")
        entry["inside"] = [s.get("headline", "") for s in (c.get("stories") or [])][:4]

    idx = [e for e in load_index() if e.get("date") != date]
    idx.append(entry)
    idx.sort(key=lambda e: e["date"], reverse=True)
    json.dump(idx, open(os.path.join(SITE, "editions.json"), "w"), indent=1, ensure_ascii=False)
    return idx


def subscribe_block():
    """The sign-up form, or nothing at all when no newsletter is configured.

    Like the LinkedIn step, this is opt-in: without BUTTONDOWN_USERNAME the site stays exactly
    as it was, with no form and nothing to say on the privacy page. The form posts straight to
    Buttondown, so the site remains static and no address ever reaches this repository.

    The two checkboxes are Buttondown tags, which it only acts on with its tagging add-on. They
    cost nothing to collect meanwhile, and no one is worse off without it: every issue carries
    the PDF link and the print instructions regardless.
    """
    user = conf("BUTTONDOWN_USERNAME")
    if not user:
        return ""
    u = html.escape(user)
    return f"""
    <section class="subscribe">
      <h3>Get it in the morning</h3>
      <p class="sub-why">One email a day, at seven: the front page, the lead story, and what
      else is in the two pages. That is the whole list &mdash; no digest, no promotions, no
      &ldquo;we&rsquo;ve updated our newsletter&rdquo;.</p>
      <form class="embeddable-buttondown-form" method="post"
            action="https://buttondown.com/api/emails/embed-subscribe/{u}">
        <input type="hidden" name="embed" value="1">
        <div class="sub-field">
          <label class="vh" for="bd-email">Email address</label>
          <input id="bd-email" type="email" name="email" placeholder="you@example.com"
                 autocomplete="email" required>
          <button type="submit">Subscribe</button>
        </div>
        <fieldset class="sub-opts">
          <legend>Do you want to print it?</legend>
          <label class="opt">
            <input type="checkbox" name="tag" value="print">
            <span><b>Put the print-ready PDF at the top.</b>
            <i>A4, two pages, duplex on the long edge &mdash; the layout this paper was built
            for.</i></span>
          </label>
          <label class="opt">
            <input type="checkbox" name="tag" value="plaintext">
            <span><b>Send plain text instead.</b>
            <i>The text and the links, no images. Good in a terminal mail client.</i></span>
          </label>
        </fieldset>
        <p class="sub-fine">We keep your address and these two answers, and nothing else.
        Unsubscribe is one click in every email. <a href="privacy.html">What we do with
        it</a>.</p>
      </form>
    </section>"""


def render(idx):
    e = idx[0] if idx else None
    esc = lambda s: html.escape(s or "")
    latest = ""
    if e:
        inside = "".join(f"<li>{esc(h)}</li>" for h in e.get("inside", []) if h)
        latest = f"""
    <section class="latest">
      <a class="cover" href="{esc(e['pdf'])}"><img src="{esc(e['thumb'])}" alt="Front page of the edition of {esc(long_date(e['date']))}" loading="lazy"></a>
      <div class="lead">
        <p class="kicker">Latest edition &middot; {esc(long_date(e['date']))}</p>
        <h2>{esc(e['headline']) or 'Today&rsquo;s edition'}</h2>
        <p class="deck">{esc(e['deck'])}</p>
        {f'<p class="also">Also inside</p><ul>{inside}</ul>' if inside else ''}
        <p><a class="btn" href="{esc(e['pdf'])}">Read the PDF &middot; {e['pages']} pages</a></p>
      </div>
    </section>"""
    rows = "".join(
        f"""      <li><a href="{esc(x['pdf'])}"><span class="d">{esc(long_date(x['date']))}</span>"""
        f"""<span class="h">{esc(x['headline'])}</span></a></li>\n"""
        for x in idx[1:])
    archive = f"""
    <section class="archive">
      <h3>Archive</h3>
      <ul>
{rows}      </ul>
    </section>""" if rows else ""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Daily Reconcile</title>
<meta name="description" content="A two-page paper on Kubernetes, platform engineering and GitOps, written and printed every morning.">
<meta property="og:title" content="The Daily Reconcile">
<meta property="og:description" content="Kubernetes, platform engineering and GitOps - written and printed every morning.">
<meta property="og:image" content="assets/social-preview.png">
<link rel="icon" href="assets/mark.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header>
  <div class="plate">
    <img class="mark" src="assets/mark.svg" alt="">
    <h1>The Daily Reconcile.</h1>
  </div>
  <p class="motto">All the cloud native news that&rsquo;s fit to reconcile</p>
  <div class="rules"><span></span><span></span></div>
</header>
<main>{latest}{archive}{subscribe_block()}
</main>
<footer>
  <p>Researched, written and laid out by Claude Code. Every item links to its source; always check the original.</p>
  <p>Made by <a href="{esc(conf('OWNER_URL') or 'https://www.linkedin.com/in/diegobraga86/')}">{esc(conf('OWNER') or 'Diego Braga')}</a>, who decides what it covers.</p>
  <p><a href="privacy.html">Privacy</a> &middot; <a href="https://github.com/{esc(conf('SITE_REPO') or 'braghettos/thedailyreconcile')}">Source on GitHub</a></p>
</footer>
</body>
</html>
"""


def main():
    if len(sys.argv) < 3:
        print(__doc__.strip()); sys.exit(2)
    pdf, date = sys.argv[1], sys.argv[2]
    content = sys.argv[3] if len(sys.argv) > 3 else None
    if not os.path.exists(pdf):
        print(f"no such PDF: {pdf}"); sys.exit(1)
    os.makedirs(os.path.join(SITE, "assets"), exist_ok=True)
    idx = add_edition(pdf, date, content)
    open(os.path.join(SITE, "index.html"), "w").write(render(idx))
    print(f"site: {len(idx)} edition(s), latest {idx[0]['date']}")


if __name__ == "__main__":
    main()
