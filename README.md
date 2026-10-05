<p align="center">
  <img src="brand/mark.svg" width="96" alt="">
</p>
<h1 align="center">The Daily Reconcile.</h1>
<p align="center"><em>All the cloud native news that&rsquo;s fit to reconcile</em></p>

A personal two-page A4 newspaper about Kubernetes, platform engineering and GitOps.
Every morning a launchd job starts Claude Code in headless mode on a Mac. Claude researches
the last 48 hours, writes the issue, lays it out as a PDF, renders a public edition, and the
script prints it on one sheet, two-sided, before breakfast.

No cloud service runs this. It is a prompt, a layout engine and two shell scripts.

---

## What it produces

| | |
|---|---|
| **Page 1** | Nameplate with ears (motto, countdown to the next CFP), an "Inside today" strip, a lead story with drop cap and a by-the-numbers factbox, three more stories, a pull quote and a stat box |
| **Page 2** | The newsroom press-release panel, news in brief across four columns, small fillers (number of the day, a verified kubectl tip), an original cartoon and a word search with the solution printed upside down |
| **Public edition** | The same issue with the personal label and any private links removed, for sharing |
| **LinkedIn post** | Plain text, at most 1,300 characters, written from the issue, emailed to you each morning to publish by hand |

## How it works

```
launchd 06:50  ->  morning-run.sh  ->  claude -p "$(PROMPT.md)"  ->  content.json
                                                                 -> build_pdf.py -> PDF (2 pages)
                                                                 -> public PDF + LinkedIn text
                   morning-run.sh  ->  history.py add        (so nothing repeats)
                                   ->  publish_site.py       (the GitHub Pages edition page, docs/)
                                   ->  linkedin_post.py      (opt-in; off unless a token is set)
                                   ->  inbox/ -> print watcher -> printer
```

Claude runs with a deliberately short leash: web search and fetch, files in the engine folder,
`python3`, and the three Gmail tools the installer finds. It cannot run anything else.

### The editorial rules, enforced in the prompt

- Every item needs concrete facts: versions, numbers, dates, CVE IDs, prices, what to do.
- Nothing is ever invented. If a source cannot be read, the paper says so.
- Nothing is reported twice. `history.py` keeps 60 days of stories, briefs and releases, and
  the run fails the check if a story repeats. A repeat is allowed only when there is genuinely
  new news on it, and then the headline has to say what is new.
- Every article ends with its full link in the footer. No QR codes.
- The cartoon is original, unrelated to the news, and never uses known characters or logos.

## Run your own

This is a working system, not a demo: clone it, fill in one config file, and you have your own
paper. Nothing about the content is hardcoded - the owner, the organisation and the newsroom
panel's repositories all come from `paper.conf`.

**You need** a Mac, Claude Code installed and signed in, python3, and a printer. Roughly ten
minutes, most of it waiting for the installer.

```sh
git clone https://github.com/braghettos/thedailyreconcile.git
cd thedailyreconcile
cp paper.conf.example paper.conf
$EDITOR paper.conf                 # owner, organisation, newsroom repos, email
bash install.sh
```

The installer creates `~/DailyReconcile`, installs the Python libraries into a private venv,
copies in your `paper.conf`, test-renders an issue, checks that Claude Code answers without a
terminal, finds the Gmail connector, clones your site repository and loads the two launchd
agents. It stops if `paper.conf` still holds the example values, rather than printing a paper
addressed to "Your Name".

Two things it cannot work out for you:

```sh
lpstat -p                          # find your printer's name
$EDITOR ~/DailyReconcile/printer.conf    # set LP_PRINTER (or MODE=email for HP ePrint)
```

and, if you want the published edition page, enable GitHub Pages on your fork:
**Settings → Pages → Deploy from a branch → `main` / `docs`**, then set `SITE_REPO="you/yourfork"`
in `paper.conf`. Leave `SITE_REPO` empty and the paper simply prints without publishing.

Then test the whole thing end to end, which takes five to ten minutes:

```sh
~/DailyReconcile/bin/morning-run.sh --force
tail -f ~/DailyReconcile/morning.log
```

It ends with `PRINT PRINTED` and a notification. From then on it runs itself at 06:50.

`paper.conf` is the only file holding anything personal, and it is git-ignored.

Full notes: **[SETUP.md](SETUP.md)**. Layout and editorial reference: **[engine/README.md](engine/README.md)**.
Why it is built this way: **[DESIGN.md](DESIGN.md)**.

## The mark

One piece of geometry in [`engine/brand.py`](engine/brand.py) draws a reconciliation loop -
two arrows chasing each other inside a printer's seal - for the GitOps idea the paper is named
after: desired state and actual state, converging. The same code draws the printed nameplate,
the page avatar and the social preview, so they cannot drift apart.

```sh
python3 brand/make_brand_assets.py brand            # mark, avatars, social preview
python3 brand/make_banner.py <issue.pdf>            # LinkedIn cover, from a real issue
```

The cover is not a blind crop of the front page: a 1128x191 banner is 5.9:1, and every
horizontal cut at that ratio runs through a line of type, so `make_banner.py` lifts the
masthead block whole - ears, nameplate, folio rule and the "Inside today" strip - and centres
it instead.

## Licence

MIT, except the bundled fonts in `engine/fonts/`, which keep their own licences
(see `engine/fonts/LICENSES.txt`).
