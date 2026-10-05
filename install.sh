#!/bin/bash
# The Daily Reconcile, local edition: Claude Code on this Mac writes the paper every morning,
# and the existing print watcher prints it. No cloud task and no "Require this computer" needed.
#
#   bash ~/Downloads/DailyReconcile-ClaudeCode/install.sh
#
# Creates ~/DailyReconcile/engine (layout engine, prompt, fonts), ~/DailyReconcile/venv (Python
# libraries), ~/DailyReconcile/bin/morning-run.sh and a launchd agent that runs it at 06:50 and,
# if that run did not produce a paper, again at 07:15.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
BASE="$HOME/DailyReconcile"
LABEL="com.dailyreconcile.morning"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

say() { printf '\n==> %s\n' "$*"; }

# 1. Print watcher (inbox -> printer). Install it if it is not there yet.
if [ ! -x "$BASE/bin/print-inbox.sh" ]; then
  say "Installing the print watcher first"
  bash "$HERE/install-print-watcher.sh"
fi

# 2. Claude Code
CLAUDE="$(command -v claude || true)"
for c in "$HOME/.claude/local/claude" "/opt/homebrew/bin/claude" "/usr/local/bin/claude" "$HOME/.local/bin/claude"; do
  [ -z "$CLAUDE" ] && [ -x "$c" ] && CLAUDE="$c"
done
if [ -z "$CLAUDE" ]; then
  echo "Claude Code was not found. Install it (https://docs.claude.com/en/docs/claude-code), run 'claude' once to sign in, then run this script again."
  exit 1
fi
say "Claude Code: $CLAUDE ($("$CLAUDE" --version 2>/dev/null || echo 'version unknown'))"

# 3. Python libraries in a private virtual environment
PY="$(command -v python3 || true)"
[ -z "$PY" ] && { echo "python3 not found. Run 'xcode-select --install' (or install Python from python.org) and try again."; exit 1; }
say "Python: $PY ($("$PY" --version 2>&1))"
[ -x "$BASE/venv/bin/python3" ] || "$PY" -m venv "$BASE/venv"
"$BASE/venv/bin/python3" -m pip install -q --upgrade pip
"$BASE/venv/bin/python3" -m pip install -q reportlab svglib pymupdf pyphen fonttools
"$BASE/venv/bin/python3" -c "import reportlab, svglib, pymupdf, pyphen, fontTools; print('    libraries OK')"

# 4. Engine. Code, prompt and fonts are replaced; today's content.json and the history are kept.
mkdir -p "$BASE/engine/fonts" "$BASE/archive" "$BASE/linkedin" "$BASE/bin"
cp "$HERE/engine/build_pdf.py" "$HERE/engine/history.py" "$HERE/engine/brand.py" \
   "$HERE/engine/PROMPT.template.md" "$HERE/engine/README.md" "$BASE/engine/"
cp "$HERE/paper.conf.example" "$BASE/paper.conf.example"
if [ -f "$HERE/paper.conf" ]; then
  cp "$HERE/paper.conf" "$BASE/paper.conf"          # the one you edited in the clone wins
  chmod 600 "$BASE/paper.conf"
  say "Using the paper.conf from $HERE"
elif [ ! -f "$BASE/paper.conf" ]; then
  cp "$HERE/paper.conf.example" "$BASE/paper.conf"
  chmod 600 "$BASE/paper.conf"
  say "Edit $BASE/paper.conf (owner, organisation, newsroom, email) before the first run"
fi
# Refuse to run with the example values still in place: they would silently produce a paper
# addressed to "Your Name" and a newsroom pointed at a repository that does not exist.
if grep -q '^OWNER="Your Name"' "$BASE/paper.conf" 2>/dev/null; then
  say "paper.conf still holds the example values"
  echo "    Edit $BASE/paper.conf, then run this installer again."
  exit 1
fi
cp "$HERE/engine/fonts/"*.ttf "$BASE/engine/fonts/"
cp "$HERE/HANDOFF.md" "$HERE/SETUP.md" "$BASE/"
[ -f "$BASE/engine/content.json" ] || cp "$HERE/engine/content.json" "$BASE/engine/content.json"
say "Test render of the reference issue"
( cd "$BASE/engine" && "$BASE/venv/bin/python3" build_pdf.py content.json "$BASE/engine/test-render.pdf" >/dev/null && echo "    render OK" )
rm -f "$BASE/engine/test-render.pdf"

# 5. The morning script
sed -e "s|__CLAUDE__|$CLAUDE|" -e "s|__PATH__|$BASE/venv/bin:$(dirname "$CLAUDE"):$PATH|" \
    "$HERE/morning-run.sh" > "$BASE/bin/morning-run.sh"
chmod +x "$BASE/bin/morning-run.sh"

# 6. Check that Claude Code can run without a terminal (sign-in works headless)
say "Checking that Claude Code answers in headless mode"
if out="$(cd "$BASE/engine" && "$CLAUDE" -p "Reply with the single word READY." --max-turns 1 2>&1)" && echo "$out" | grep -q READY; then
  echo "    Claude Code OK"
else
  echo "    Claude Code did not answer: $out"
  echo "    Run 'claude' once in Terminal, sign in, then run this installer again."
  exit 1
fi

# 6b. Gmail connector: find its exact tool names in Claude Code, then send one test email
# personal values come from paper.conf; EMAIL_TO=... in the environment still wins
PAPER_EMAIL_TO=""
if [ -f "$BASE/paper.conf" ]; then
  # shellcheck disable=SC1091
  PAPER_EMAIL_TO="$(. "$BASE/paper.conf"; echo "${EMAIL_TO:-}")"
fi
EMAIL_TO="${EMAIL_TO:-$PAPER_EMAIL_TO}"
say "Looking for the Gmail connector in Claude Code"
# Ask the MCP layer, not the model: connector tools are usually deferred (their schemas load on
# demand via ToolSearch), so a model asked to list its tools truthfully reports none even when the
# connector is connected. "claude mcp list" shows the server; its tool names follow from its
# display name, e.g. "claude.ai Gmail" -> mcp__claude_ai_Gmail__send_message.
G_SEARCH=""; G_THREAD=""; G_SEND=""
mcp_out="$(cd "$BASE/engine" && "$CLAUDE" mcp list 2>&1 || true)"
gmail_line="$(echo "$mcp_out" | grep -i 'gmail' | head -n 1 || true)"
echo "    Claude Code reported:"; echo "${gmail_line:-  (no Gmail server listed)}" | sed "s/^/      /"
if echo "$gmail_line" | grep -qiE 'connected'; then
  prefix="mcp__$(echo "$gmail_line" | sed 's/:.*//' | sed 's/[^A-Za-z0-9]/_/g')__"
  G_SEARCH="${prefix}search_threads"; G_THREAD="${prefix}get_thread"; G_SEND="${prefix}send_message"
fi
if [ -z "$G_SEND" ]; then
  echo "    The Gmail connector is not connected for Claude Code."
  echo "    1. At claude.ai > Settings > Connectors, check that Gmail is connected for your account."
  echo "    2. In Terminal run 'claude', type /mcp and check that 'claude.ai Gmail' is listed and connected"
  echo "       (if it asks you to authenticate, do it there)."
  echo "    3. Run this installer again. Until then the paper prints, but no email is sent."
  printf 'GMAIL_SEARCH=""\nGMAIL_THREAD=""\nGMAIL_SEND=""\nEMAIL_TO="%s"\n' "$EMAIL_TO" > "$BASE/gmail.conf"
else
  echo "    found: $G_SEND"
  printf 'GMAIL_SEARCH="%s"\nGMAIL_THREAD="%s"\nGMAIL_SEND="%s"\nEMAIL_TO="%s"\n' "$G_SEARCH" "$G_THREAD" "$G_SEND" "$EMAIL_TO" > "$BASE/gmail.conf"
  say "Sending a test email to $EMAIL_TO through the Gmail connector"
  send_out="$(cd "$BASE/engine" && "$CLAUDE" -p "Call $G_SEND exactly once to send a plain-text email to $EMAIL_TO with subject 'The Daily Reconcile: Gmail test' and body 'Claude Code on your Mac can send email through the Gmail connector. Each morning you will get the LinkedIn post here.'. Then print SENT if it succeeded, or FAILED: followed by the error." --allowedTools "$G_SEND" --max-turns 3 2>&1 || true)"
  if echo "$send_out" | grep -q '^SENT\|SENT$'; then
    echo "    Test email sent. Check your inbox."
  else
    echo "    The test email was not sent: $(echo "$send_out" | tail -n 3)"
    echo "    The paper will still print. Fix the connector and run the installer again."
  fi
fi

# 6c. The clone the morning run publishes the edition from. Kept separate from your working
# copy so an automated commit can never land on top of whatever you have checked out.
SITE_REPO="$(. "$BASE/paper.conf"; echo "${SITE_REPO:-}")"
if [ -n "$SITE_REPO" ] && [ ! -d "$BASE/repo/.git" ]; then
  say "Cloning $SITE_REPO for publishing the edition page"
  if git clone -q "https://github.com/$SITE_REPO.git" "$BASE/repo" 2>/dev/null; then
    echo "    $BASE/repo"
    echo "    Enable GitHub Pages for it: Settings > Pages > Deploy from a branch > main / docs"
  else
    echo "    Could not clone it. The paper still prints; the edition page will be skipped."
    echo "    Fix it with:  git clone https://github.com/$SITE_REPO.git $BASE/repo"
  fi
fi

# 7. launchd agent: 06:50, retry at 07:15 (the script exits at once if today's paper is done)
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key><string>$LABEL</string>
	<key>ProgramArguments</key>
	<array><string>/bin/bash</string><string>$BASE/bin/morning-run.sh</string></array>
	<key>StartCalendarInterval</key>
	<array>
		<dict><key>Hour</key><integer>6</integer><key>Minute</key><integer>50</integer></dict>
		<dict><key>Hour</key><integer>7</integer><key>Minute</key><integer>15</integer></dict>
	</array>
	<key>StandardOutPath</key><string>$BASE/morning-launchd.log</string>
	<key>StandardErrorPath</key><string>$BASE/morning-launchd.log</string>
</dict>
</plist>
PL
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

say "Installed. The paper is written and printed every day at 06:50."
cat <<TXT
    Test it now (takes about 5-10 minutes):   ~/DailyReconcile/bin/morning-run.sh --force
    Follow progress:                          tail -f ~/DailyReconcile/morning.log
    Keep the Mac awake at 06:45:              sudo pmset repeat wakeorpoweron MTWRFSU 06:45:00
TXT
