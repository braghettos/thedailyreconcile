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
and removed the whole class of problem: the Mac just has to be logged in.

Sleep is not fatal. launchd runs a missed `StartCalendarInterval` job when the machine next wakes,
and `morning-run.sh` exits immediately if today's issue already exists, so a sleeping Mac delays
the paper rather than losing it. Scheduling a wake-up is therefore optional, and only worth it if
you want the paper waiting for you at breakfast rather than whenever the lid opens:

```sh
sudo pmset repeat wakeorpoweron MTWRFSU 06:45:00
```

## Publishing

- **The dedicated page comes first.** `tools/publish_site.py` adds the edition to `docs/` (GitHub Pages serves `/` or `/docs` only) and the
  commit is pushed to GitHub Pages, so the LinkedIn post has something to point at.
- **LinkedIn is published by hand, on purpose.** Posting to a Page requires the Community
  Management API, which LinkedIn grants only after reviewing an application, plus a member token
  that expires every 60 days. That was judged not worth it: the morning email already delivers the
  post text, and publishing it yourself keeps a person between an unattended research run and your
  own name. `tools/linkedin_post.py` remains, and works, for anyone who does hold API access; it
  stays dormant unless `LINKEDIN_TOKEN_FILE` is set, so it costs nothing to leave in place.

- **The newsletter composes a draft, it does not send.** `NEWSLETTER_STATUS` defaults to
  `draft`, for the same reason LinkedIn is published by hand: a stranger's inbox deserves a
  person in the loop more than a Page does, not less. Set it to `about_to_send` once the shape
  of the email is boring.

- **Buttondown, because a daily is priced by subscriber and not by send.** Mailchimp allows
  10-15x the contact count per month and a daily needs 30x, so a daily paper pays overages
  permanently. Kit and beehiiv have far more generous free tiers - 10,000 and 2,500 subscribers,
  no send cap - but both gate the send API behind $39-43/month, which an unattended launchd job
  cannot do without. Buttondown is free to 100 subscribers with the API and a custom sending
  domain included, and $9/month after that.

- **The PDF is linked, never attached.** Buttondown bills attachments as an add-on, and a link
  keeps the issue readable from the archive long after a mail client has forgotten it.

- **The email is single-theme and almost image-free.** Mail clients handle dark mode by
  force-inverting, which would turn the front page into a negative and the red into pink, so the
  email stays on cream whatever the reader's system says. The nameplate is set as text rather
  than as the SVG mark, because clients strip SVG and blocked images should not cost the reader
  the masthead. The front page is the one image, and its alt text carries the headline.

- **The newsletter reuses the LinkedIn post rather than re-deriving the prose.** That text is
  already written to be public - step 6 of the prompt forbids links, PR numbers and repository
  names - so it is the safest source. `newsletter_send.py` strips the three LinkedIn-only
  things: the hashtags, "Swipe through the PDF below", and the "Curated and summarised with
  Claude" sign-off that the footer says at more length. It also checks the finished body against
  the private newsroom slug and the owner's name, and refuses to send on a match; the fields it
  reads from `content.json` are deliberately the ones `public_edition()` leaves untouched, and
  the newsroom panel is left out entirely.
