#!/bin/bash
# The Daily Reconcile: print watcher for macOS.
# Creates ~/DailyReconcile (inbox, printed, failed, print.log, printer.conf) and a launchd agent
# that prints every PDF dropped into ~/DailyReconcile/inbox, either by emailing it from Mail.app
# to the HP ePrint address or by sending it straight to a printer with lp.
# Safe to run again: it keeps an existing printer.conf.
set -euo pipefail

BASE="$HOME/DailyReconcile"
LABEL="com.dailyreconcile.printwatcher"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

mkdir -p "$BASE/inbox" "$BASE/printed" "$BASE/failed" "$BASE/bin" "$HOME/Library/LaunchAgents"
touch "$BASE/print.log"

# ---------------------------------------------------------------- settings (kept if already present)
if [ ! -f "$BASE/printer.conf" ]; then
cat > "$BASE/printer.conf" <<'CONF'
# How the morning paper is printed.
#   MODE=email  emails the PDF from Mail.app to the HP ePrint address (works from anywhere;
#               usually single-sided; the sending address must be an allowed sender in HP Smart)
#   MODE=lp     prints directly to a printer installed on this Mac (same network; two-sided works)
MODE=email

# --- email mode
EPRINT_ADDRESS=""          # your HP ePrint address, if you use MODE=email
# The address Mail.app sends from. Leave empty to use Mail's default account.
MAIL_SENDER=""

# --- lp mode: printer name as shown by:  lpstat -p
LP_PRINTER=""
LP_OPTIONS="-o media=A4 -o sides=two-sided-long-edge"
CONF
fi

# ---------------------------------------------------------------- the watcher script
cat > "$BASE/bin/print-inbox.sh" <<'SCRIPT'
#!/bin/bash
# Prints every PDF in ~/DailyReconcile/inbox, then moves it to printed/ or failed/
# and appends one line to print.log:  <date time> PRINTED|FAILED <file> <details>
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
BASE="$HOME/DailyReconcile"
LOG="$BASE/print.log"
LOCK="$BASE/.lock"

LP_BIN="${LP_BIN:-/usr/bin/lp}"
OSASCRIPT_BIN="${OSASCRIPT_BIN:-/usr/bin/osascript}"
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"; }

# one run at a time (launchd fires again when files move out of inbox)
if ! mkdir "$LOCK" 2>/dev/null; then
  # stale lock older than 10 minutes: remove it
  if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +10 2>/dev/null)" ]; then rmdir "$LOCK" 2>/dev/null; mkdir "$LOCK" || exit 0; else exit 0; fi
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

MODE=email; EPRINT_ADDRESS=""; MAIL_SENDER=""; LP_PRINTER=""; LP_OPTIONS=""
# shellcheck disable=SC1091
[ -f "$BASE/printer.conf" ] && . "$BASE/printer.conf"

wait_until_complete() {           # the file may still be being written
  local f="$1" prev=-1 size i
  for i in $(seq 1 30); do
    size=$(wc -c < "$f" 2>/dev/null | tr -d ' ')
    [ -n "$size" ] && [ "$size" -gt 0 ] && [ "$size" = "$prev" ] && return 0
    prev="$size"; sleep 2
  done
  return 1
}

send_email() {                    # emails the PDF from Mail.app
  local f="$1" subject
  subject="The Daily Reconcile — $(basename "$f" .pdf | sed 's/^daily-reconcile-//')"
  "$OSASCRIPT_BIN" - "$f" "$EPRINT_ADDRESS" "$subject" "$MAIL_SENDER" <<'APPLESCRIPT'
on run argv
	set theFile to POSIX file (item 1 of argv) as alias
	set theAddress to item 2 of argv
	set theSubject to item 3 of argv
	set theSender to item 4 of argv
	tell application "Mail"
		set msg to make new outgoing message with properties {subject:theSubject, content:theSubject & return & return, visible:false}
		tell msg
			make new to recipient at end of to recipients with properties {address:theAddress}
			if theSender is not "" then set sender to theSender
			tell content to make new attachment with properties {file name:theFile} at after the last paragraph
		end tell
		delay 3
		send msg
	end tell
end run
APPLESCRIPT
}

shopt -s nullglob
for f in "$BASE"/inbox/*.pdf "$BASE"/inbox/*.PDF; do
  name=$(basename "$f")
  if ! wait_until_complete "$f"; then
    mv -f "$f" "$BASE/failed/$name"; log "FAILED $name file never finished downloading"; continue
  fi
  if [ "$MODE" = "lp" ]; then
    if [ -z "$LP_PRINTER" ]; then
      mv -f "$f" "$BASE/failed/$name"; log "FAILED $name LP_PRINTER is empty in printer.conf"; continue
    fi
    # shellcheck disable=SC2086
    if out=$("$LP_BIN" -d "$LP_PRINTER" $LP_OPTIONS "$f" 2>&1); then
      mv -f "$f" "$BASE/printed/$name"; log "PRINTED $name via lp on $LP_PRINTER ($out)"
    else
      mv -f "$f" "$BASE/failed/$name"; log "FAILED $name lp error: $(echo "$out" | tr '\n' ' ')"
    fi
  else
    if [ -z "$EPRINT_ADDRESS" ]; then
      mv -f "$f" "$BASE/failed/$name"; log "FAILED $name EPRINT_ADDRESS is empty in printer.conf"; continue
    fi
    if out=$(send_email "$f" 2>&1); then
      mv -f "$f" "$BASE/printed/$name"; log "PRINTED $name via email to $EPRINT_ADDRESS"
    else
      mv -f "$f" "$BASE/failed/$name"; log "FAILED $name Mail.app error: $(echo "$out" | tr '\n' ' ')"
    fi
  fi
done
SCRIPT
chmod +x "$BASE/bin/print-inbox.sh"

# ---------------------------------------------------------------- launchd agent
cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key><string>$LABEL</string>
	<key>ProgramArguments</key>
	<array><string>/bin/bash</string><string>$BASE/bin/print-inbox.sh</string></array>
	<key>WatchPaths</key>
	<array><string>$BASE/inbox</string></array>
	<key>StartInterval</key><integer>60</integer>
	<key>RunAtLoad</key><true/>
	<key>StandardOutPath</key><string>$BASE/watcher.out.log</string>
	<key>StandardErrorPath</key><string>$BASE/watcher.err.log</string>
</dict>
</plist>
PLISTEOF

launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl enable "gui/$(id -u)/$LABEL"

echo "Installed. Folder: $BASE"
echo "Settings:  $BASE/printer.conf"
echo "Log:       $BASE/print.log"
echo
echo "Next: run a test print (see the instructions), so macOS can ask for permission to control Mail."
