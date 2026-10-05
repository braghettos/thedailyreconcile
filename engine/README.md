# The Daily Reconcile.

A personal two-page A4 newspaper about Kubernetes, platform engineering, AI and HPC on Kubernetes, OpenStack and new LLMs. It is printed every morning.

## Layout

The design follows professional newspaper conventions:

- **Front page header.** A centred nameplate with a full stop, after the WSJ. Two NYT-style ears flank it: the motto on the left, and on the right a live countdown to the next CFP deadline. Below it, a folio line (volume, number, date, edition) between a thin rule and a thick-and-thin double rule.
- **"Inside today" strip.** A WSJ "What's News"-style strip on a champagne tint, with diamond bullets pointing to page 2.
- **Lead story.** A headline across the page, a deck, a byline and a red drop cap. The body runs on three columns, next to a "by the numbers" factbox that replaces a photo.
- **Below the lead.** A second lead with its headline across two columns, single-column stories in column 3, and column 4 with the cartoon of the day (joke explained) and "Dates to watch" (online and in-person events, CFP deadlines).
- **Jumps.** Stories that don't fit end with "Continued on page 2 ▸" and pick up on page 2 under a short jump head. A story never jumps for just a few lines: it drops its deck instead.
- **Fillers.** If a column would end with a hole, a pull quote or a stat box fills it on page 1. On page 2, small fillers (a number of the day, a kubectl or helm tip) drop into whichever column end they fit best. A brief that doesn't fit whole can enter shortened at a sentence boundary, never mid-sentence. The newsroom panel balances its content across two columns, and "Dates to watch" spreads its entries over the whole box.
- **Newsroom.** A press-release panel at the top of page 2 with a headline, a dated intro and one column per product. Each column names its source and lists component, version, date, changes and link. When nothing is new, it says so.
- **Page 2.** A slim running head, continued stories, then "News in brief" on four columns. A boxed word search sits in the bottom right with the solution upside down. Briefs are kept in priority order. Those that don't fit are dropped whole, never truncated, and the build reports them.
- **Typography.** Body text in Lora at a fixed 8.5/11.4 pt, ragged right with hyphenation, for long reading without fatigue. Labels are in Carlito, and the nameplate is in Liberation Serif Bold. A single dark-red accent turns into dark grey in black and white.
- **Links.** Every article ends with its full link, readable on paper and clickable in the PDF.

## Files

- `build_pdf.py`: the layout engine (reportlab, svglib, pyphen, fontTools). On the first run it creates `fonts/` with static Lora instances built from the Google Fonts variable files.
- `content.json`: the day's content. The keys are `title`, `motto`, `edition`, `tagline`, `lead` (with `jump_head`), `factbox`, `stories` (the first is the second lead), `statbox`, `pullquote`, `briefs` (in priority order), `teasers` (indexes into `briefs`), `dates` (`date`, `when`, `tag`: online/event/CFP, `short` for CFPs), `cartoon`, `game`, `fillers` (`type`: number or tip, `title`, `value` or `code`, `label`, `source`) and `krateo` (`headline`, `intro`, `source_label`, `products`: `name`, `subtitle`, `note`, `quiet`, `releases`: `component`, `version`, `date`, `notes`, `url`). Every item has `url` or `urls`.
- `daily-reconcile.pdf`: issue for October 2, 2026.

## Usage

```
pip install reportlab svglib pymupdf pyphen fonttools
python3 build_pdf.py content.json daily-reconcile.pdf
```

## Public edition (LinkedIn)

`python3 build_pdf.py content.json daily-reconcile-public.pdf --public` builds the copy shared on LinkedIn. It replaces the personal edition label with `public_edition`. Newsroom products marked `"private": true` (the private source) stay in, but their links are removed, because private pull requests can't be opened from outside the organisation, and their subtitle becomes `public_subtitle`. The LinkedIn post text is written separately each morning. Nothing is posted automatically.

## Editorial line

- **Topics:** Kubernetes and CNCF, platform engineering, GitOps (Argo CD, Crossplane, Backstage), AI on Kubernetes, HPC on Kubernetes (Slurm, Kueue, Volcano), OpenStack, new LLMs, cloud native security, observability, FinOps.
- **Excluded:** politics, general economics, hardware.
- **Sourcing:** every item carries concrete facts (versions, numbers, CVEs, prices, what to do), taken from the full article, not just the headline. Flag disagreements between sources and vendor-run content.
- **Sources:** kubernetes.io, CNCF, InfoQ, The New Stack, OpenStack, StackHPC, GitHub releases, kubernetes-security-announce, Linux Foundation events calendar, kube.events, Medium (platform-engineering, gitops and kubernetes tags). Only use articles from the last 48 hours, or state their date.
- **Newsroom.** The panel uses two sources. Public half: the GitHub releases pages of the organisation's public repositories, read with WebFetch. Private half: repositories that cannot be read directly, so the panel lists pull requests merged into main in the last 7 days, taken from GitHub notification emails in Gmail. Never invent releases.
- **Cartoon:** original, unrelated to the news, always with the joke explained.

## Printing

- **How:** a launchd agent runs `morning-run.sh` at 06:50 local time; Claude Code builds both editions on the Mac and the script drops the personal PDF into `~/DailyReconcile/inbox`.
- **Print watcher:** a launchd agent (`com.dailyreconcile.printwatcher`, installed by `install-print-watcher.sh`) sends each new PDF to the printer with `lp -o media=A4 -o Duplex=DuplexNoTumble` on the printer named in `printer.conf`: one sheet, printed on both sides. Each paper is then moved to `printed/` or `failed/`, and one line is written to `print.log`.
- **Fallback:** `MODE=email` in `printer.conf` emails the PDF from Mail.app to HP ePrint (`your-eprint-address@hpeprint.com`), which prints single-sided.
- **LinkedIn:** the public PDF and the post text go to `~/DailyReconcile/linkedin/`. They are never posted automatically.
- **Requirements:** the task must be linked to the Mac ("Require this computer"), with the `DailyReconcile` folder connected. The Mac must be awake (`sudo pmset repeat wakeorpoweron MTWRFSU 06:45:00`) with the Claude desktop app running.
