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
