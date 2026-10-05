# Why it is built this way

Notes carried over from building the paper. They explain decisions that are not obvious from
the code, so the next change does not undo a deliberate choice.

## Editorial

- **One language.** The paper is in English, whatever language the owner talks to Claude in.
- **Topics.** Kubernetes and CNCF, platform engineering, GitOps (Argo CD, Crossplane, Backstage,
  Flux), AI on Kubernetes, HPC on Kubernetes (Slurm/Slinky, Kueue, Volcano), OpenStack, new LLM
  releases, cloud native security, observability, FinOps.
- **Excluded.** No politics, no general economics, no hardware.
- **Substance over headline.** A headline with no facts under it is rejected. "CNCF tells the
  journeys..." is exactly the kind of item that must not appear.
- **Blocked fetches are left blocked.** If a site cannot be fetched, the item is skipped. Never
  work around it with curl, Python or a mirror; the prompt says so and it is deliberate.
- **Repeats are the main failure mode.** Early cloud runs had no memory and printed the same
  release for days. `history.py` exists because of that, and the check is not optional.

## Layout

- **Four-column grid.** The lead spans three columns with a drop cap, next to a factbox.
- **Fonts.** Lora for body text at 8.5/11.4 pt, ragged right with hyphenation - Times at this
  size was tiring to read. Carlito for labels, Liberation Serif Bold for the nameplate. All
  bundled in `engine/fonts/`, so a run never depends on what the machine has installed.
- **No empty space.** Gaps at the foot of a column are a defect. The engine drops briefs for
  space and jumps stories to page 2 to avoid them.
- **The solution to the word search prints upside down**, as in the puzzle magazines the feature
  is modelled on.

## Printing

- **Two-sided on one sheet** via `lp -o media=A4 -o Duplex=DuplexNoTumble`. This is the reason
  for the print watcher: emailing the PDF to an HP ePrint address works from anywhere but prints
  single-sided, so it is only the fallback.
- **The PDF is not emailed.** The Gmail connector cannot reliably attach a ~100 KB PDF (it goes
  base64 inside the tool call). The morning email carries the LinkedIn text; the PDFs stay in
  `archive/YYYY-MM-DD/`.
- **The print watcher is a separate agent** from the morning run, so a slow or failed write
  never leaves a half-finished PDF at the printer. The move into `inbox/` is atomic.

## Running it locally rather than in the cloud

The paper first ran as a cloud scheduled task that printed through a linked Mac. Linking the
task to the machine never worked - it failed to confirm the computer's identity, and clearing
the Keychain items did not help. Running Claude Code locally from launchd replaced it entirely
and removed the whole class of problem: the Mac just has to be awake.

```sh
sudo pmset repeat wakeorpoweron MTWRFSU 06:45:00
```

## Publishing

- **The dedicated page comes first.** `tools/publish_site.py` adds the edition to `docs/` (GitHub Pages serves `/` or `/docs` only) and the
  commit is pushed to GitHub Pages, so the LinkedIn post has something to point at.
- **LinkedIn needs approval.** Posting to a Page requires the Community Management API approved
  for a verified app, plus a 60-day member token. `tools/linkedin_post.py` skips cleanly when the
  token is missing, so the rest of the morning never fails because of it.
