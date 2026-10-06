# The Daily Reconcile, written by Claude Code on your Mac

Every morning at 06:50 a launchd job starts Claude Code in headless mode (`claude -p`) in `~/DailyReconcile/engine`. Claude researches the news, writes `content.json`, checks it against what was already printed, renders the PDF and the public edition, and writes the LinkedIn post. The script then drops the PDF into `inbox/`, where the print watcher prints it on both sides of one sheet. If 06:50 fails, the job retries at 07:15.

## Install

```
cd ~/Downloads && unzip -o DailyReconcile-ClaudeCode.zip
bash ~/Downloads/DailyReconcile-ClaudeCode/install.sh
```

What you need:

- Claude Code installed and signed in. Run `claude` once in Terminal if you haven't.
- python3. If macOS offers to install the developer tools, accept.

The installer checks both, installs the Python libraries in `~/DailyReconcile/venv`, test-renders a paper and checks that Claude Code answers without a terminal.

## Test

```
~/DailyReconcile/bin/morning-run.sh --force
tail -f ~/DailyReconcile/morning.log
```

A run takes about 5 to 10 minutes and ends with `PRINT PRINTED` and a macOS notification.

## No repeated news

`history.json` keeps every story, brief and newsroom release printed in the last 60 days. Before writing, Claude reads the last 10 days. After writing, `history.py check` must pass: any story with the same link or the same subject as one already printed is replaced. The only exception is a real update, such as a fix or a new version. Newsroom releases and pull requests appear once, not every day for a week.

## The custom domain

The site is served by GitHub Pages from `docs/` on `main`. To put it on your own domain, do the
DNS first: a `CNAME` file is not a reservation, and Pages starts redirecting the `github.io` URL
to the custom domain the moment that file lands. Add it before DNS resolves and the live site
redirects to nothing.

In GoDaddy, open the domain, then **DNS → Records**, and **delete the parked records first** —
the `A` record on `@` pointing at GoDaddy's parking IP, and the `CNAME` on `www`. Then add:

| Type | Name | Value | TTL |
|---|---|---|---|
| A | @ | `185.199.108.153` | 600 |
| A | @ | `185.199.109.153` | 600 |
| A | @ | `185.199.110.153` | 600 |
| A | @ | `185.199.111.153` | 600 |
| AAAA | @ | `2606:50c0:8000::153` | 600 |
| AAAA | @ | `2606:50c0:8001::153` | 600 |
| AAAA | @ | `2606:50c0:8002::153` | 600 |
| AAAA | @ | `2606:50c0:8003::153` | 600 |
| CNAME | www | `<your-github-user>.github.io` | 600 |

All four `A` records are needed; they are GitHub's anycast front ends, not alternatives. The
apex has to be `A`/`AAAA` because a `CNAME` is not allowed on a zone apex, which is also why
`www` is the one name that gets a `CNAME`. 600 is GoDaddy's minimum TTL.

Then wait for it to resolve, and only then claim it:

```
dig +short thedailyreconcile.news A          # expect the four GitHub addresses
echo thedailyreconcile.news > docs/CNAME     # from the repo clone
git add docs/CNAME && git commit -m "Claim the domain" && git push
```

Finally, in the repository, **Settings → Pages**, wait for the certificate to be issued and tick
**Enforce HTTPS**. That can take up to an hour; until then the domain serves over HTTP only.

Set `SITE_URL="https://thedailyreconcile.news"` in `paper.conf` at the same time. The site's own
pages link to each other relatively and do not care, but the newsletter builds absolute links and
would otherwise keep pointing at `github.io`.

## The newsletter

Off by default. The morning run composes the public edition as an email — front page, lead
story, the "also inside" lines, and links to read or download the PDF — and sends it through
[Buttondown](https://buttondown.com), which is free to 100 subscribers and whose API and custom
sending domain are included at every tier.

1. Create the newsletter, and put its username in `BUTTONDOWN_USERNAME`. That alone adds the
   sign-up form to the edition page.
2. Create an API key under **Settings → Programming** and save it so only you can read it:
   ```
   mkdir -p ~/.config && umask 077 && pbpaste > ~/.config/buttondown.token
   ```
   Point `BUTTONDOWN_TOKEN_FILE` at it.
3. Check what it will send without sending anything:
   ```
   cd ~/DailyReconcile/repo
   python3 tools/newsletter_send.py ~/DailyReconcile/linkedin/linkedin-post-$(date +%F).txt \
       ~/DailyReconcile/engine/content.json $(date +%F) --dry-run --out /tmp/mail.html
   open /tmp/mail.html
   ```

`NEWSLETTER_STATUS` defaults to `draft`: every morning the issue is uploaded to Buttondown and
waits for you to press send. Set it to `about_to_send` once you trust it and the run sends on its
own. `morning.log` records `NEWSLETTER DRAFT CREATED`, `NEWSLETTER SENT`, `NEWSLETTER SKIPPED` or
`NEWSLETTER FAILED` with the reason.

Before relying on it, send one real issue to yourself. Buttondown's free tier is documented as
including API access, but whether it permits sending via API is worth proving on your own
account rather than discovering at 06:50.

## Files

| Path | What |
|---|---|
| `morning.log` | One line per step: START, QUEUED, PRINT, FAILED |
| `claude-last-run.log` | Full output of the last Claude Code run |
| `archive/YYYY-MM-DD/` | Personal PDF, public PDF, LinkedIn post, content.json |
| `linkedin/` | Today's public PDF and post, ready to publish by hand |
| `history.json` | What has been printed (used to avoid repeats) |

## Notes

- **Gmail connector.** Claude Code uses the Gmail connector from your claude.ai account for two things: reading GitHub notifications for the private half of the newsroom, and sending one morning email to the address in paper.conf with the LinkedIn post. The installer finds the connector's exact tool names, saves them in `gmail.conf` and sends a test email. If it can't find the connector, run `claude` in Terminal, type `/mcp`, check that "claude.ai Gmail" is connected, then run the installer again. To send to another address: `EMAIL_TO=you@example.com bash install.sh`.
- **Email.** The morning email has no attachments: the PDFs stay in `archive/YYYY-MM-DD/`. `morning.log` records `EMAIL SENT` or `EMAIL FAILED` with the reason.
- **Tools** are limited to web search and fetch, files in the engine folder, `python3`, and three Gmail tools: search, read a thread, and send. The prompt allows exactly one email per run, only to the address in `gmail.conf`. Claude can't run other commands.
- **Wake-up.** The Mac has to be logged in; the screen can be locked. If it is asleep at 06:50, launchd runs the job when it next wakes, so the paper arrives late rather than not at all - the run checks whether today's issue already exists and exits if it does. To have it printed on time regardless, schedule a wake-up once: `sudo pmset repeat wakeorpoweron MTWRFSU 06:45:00`.
- **Remove:** `bash uninstall.sh` stops the morning run and keeps the print watcher and your files.
