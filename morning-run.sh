#!/bin/bash
# Writes today's Daily Reconcile with Claude Code (headless), then hands the PDF to the print watcher.
#   morning-run.sh           normal run (does nothing if today's paper already exists)
#   morning-run.sh --force   run again even if today's paper exists
set -u
BASE="$HOME/DailyReconcile"
ENG="$BASE/engine"
LOG="$BASE/morning.log"
export PATH="__PATH__"
CLAUDE="__CLAUDE__"
TODAY="$(date +%F)"
FORCE=0; [ "${1:-}" = "--force" ] && FORCE=1

log()    { echo "$(date '+%F %T') $*" >> "$LOG"; }
notify() { osascript -e "display notification \"$1\" with title \"The Daily Reconcile\"" >/dev/null 2>&1 || true; }

[ "$FORCE" = 0 ] && [ -e "$BASE/archive/$TODAY/daily-reconcile-$TODAY.pdf" ] && exit 0

LOCK="$BASE/.morning.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +90 2>/dev/null)" ]; then rm -rf "$LOCK"; mkdir "$LOCK"
  else log "SKIP another run is in progress"; exit 0; fi
fi
trap 'rm -rf "$LOCK"' EXIT

cd "$ENG" || { log "FAILED engine folder missing"; exit 1; }
log "START $TODAY"
cp content.json content.prev.json
rm -f daily-reconcile-*.pdf linkedin-post-*.txt page-*.png

# Only the tools the paper needs: web research, files in this folder, python3, and the three
# Gmail tools found by the installer (search and read for the private newsroom, send for the morning email).
GMAIL_SEARCH=""; GMAIL_THREAD=""; GMAIL_SEND=""
[ -f "$BASE/gmail.conf" ] && . "$BASE/gmail.conf"
TOOLS=(WebSearch WebFetch Read Write Edit Glob Grep "Bash(python3:*)" "Bash(ls:*)")
for t in "$GMAIL_SEARCH" "$GMAIL_THREAD" "$GMAIL_SEND"; do [ -n "$t" ] && TOOLS+=("$t"); done
# Connector tools are deferred: their schemas load on demand, so ToolSearch must be allowed too.
[ -n "$GMAIL_SEND" ] && TOOLS+=(ToolSearch)

# PROMPT.md is generated from the template: the personal values live only in paper.conf.
OWNER=""; OWNER_FIRSTNAME=""; ORG=""; EMAIL_TO=""
NEWSROOM_NAME=""; NEWSROOM_ORG=""; NEWSROOM_REPOS=""
NEWSROOM_PRIVATE_NAME=""; NEWSROOM_PRIVATE_ORG=""
[ -f "$BASE/paper.conf" ] && . "$BASE/paper.conf"
if [ ! -f PROMPT.template.md ]; then log "FAILED engine/PROMPT.template.md missing"; exit 1; fi
sed -e "s|__OWNER__|${OWNER:-the owner}|g" \
    -e "s|__OWNER_FIRSTNAME__|${OWNER_FIRSTNAME:-the owner}|g" \
    -e "s|__ORG__|${ORG:-}|g" \
    -e "s|__NEWSROOM_NAME__|${NEWSROOM_NAME:-Newsroom}|g" \
    -e "s|__NEWSROOM_ORG__|${NEWSROOM_ORG:-}|g" \
    -e "s|__NEWSROOM_REPOS__|${NEWSROOM_REPOS:-}|g" \
    -e "s|__NEWSROOM_PRIVATE_NAME__|${NEWSROOM_PRIVATE_NAME:-}|g" \
    -e "s|__NEWSROOM_PRIVATE_ORG__|${NEWSROOM_PRIVATE_ORG:-}|g" \
    PROMPT.template.md > PROMPT.md
PROMPT="$(cat PROMPT.md)"
if [ -n "$GMAIL_SEND" ] && [ -n "$EMAIL_TO" ]; then
  PROMPT="$PROMPT

8. MORNING EMAIL (after step 6, before the DONE line)
The Gmail tools are deferred: if $GMAIL_SEND is not already in your tool list, load it first with ToolSearch (query \"select:$GMAIL_SEARCH,$GMAIL_THREAD,$GMAIL_SEND\"). Then call $GMAIL_SEND exactly once: to [\"$EMAIL_TO\"], subject \"The Daily Reconcile · <Weekday, Month D>: <lead headline>\", plain-text body = the full text of linkedin-post-YYYY-MM-DD.txt, then a blank line and \"PDFs: ~/DailyReconcile/archive/YYYY-MM-DD/\". No attachments. Never send to any other address and never send more than one email. Then print one line: \"EMAIL SENT\" or \"EMAIL FAILED: <error>\". If the LinkedIn post was skipped in step 5, send the same email with the body \"Public edition skipped: <reason>\" instead."
fi
"$CLAUDE" -p "$PROMPT" --allowedTools "${TOOLS[@]}" --max-turns 250 \
  > "$BASE/claude-last-run.log" 2>&1
rc=$?
summary="$(grep '^DONE ' "$BASE/claude-last-run.log" | tail -n 1)"
email="$(grep -E '^EMAIL (SENT|FAILED)' "$BASE/claude-last-run.log" | tail -n 1)"
[ -n "$GMAIL_SEND" ] && log "${email:-EMAIL no result reported}"

PDF="daily-reconcile-$TODAY.pdf"
pages="$(python3 -W ignore -c "import pymupdf,sys; print(len(pymupdf.open(sys.argv[1])))" "$PDF" 2>/dev/null | tail -n 1 || echo 0)"
if [ "$pages" != "2" ]; then
  cp content.prev.json content.json
  log "FAILED no 2-page PDF (claude exit $rc, pages $pages). See claude-last-run.log"
  notify "Not printed: Claude Code did not produce today's paper. See claude-last-run.log"
  exit 1
fi

# Archive, LinkedIn package, history
A="$BASE/archive/$TODAY"; mkdir -p "$A" "$BASE/linkedin"
cp "$PDF" content.json "$A/"
for f in "daily-reconcile-public-$TODAY.pdf" "linkedin-post-$TODAY.txt"; do
  [ -f "$f" ] && cp "$f" "$A/" && cp "$f" "$BASE/linkedin/"
done
python3 history.py add content.json >> "$LOG" 2>&1

# Publish: the dedicated page first (it is the link the LinkedIn post points at), then LinkedIn.
PUB="daily-reconcile-public-$TODAY.pdf"
POST="linkedin-post-$TODAY.txt"
SITE_REPO=""; SITE_BRANCH="main"; SITE_DIR="docs"
[ -f "$BASE/paper.conf" ] && . "$BASE/paper.conf"
if [ -f "$PUB" ] && [ -n "$SITE_REPO" ] && [ -d "$BASE/repo/.git" ]; then
  # The clone must be level with the remote BEFORE the site is rebuilt. Once publish_site.py has
  # written into docs/ the tree is dirty, and "git pull --rebase" refuses to run on a dirty tree:
  # the edition would then be committed on a stale base and the push rejected as non-fast-forward.
  # --autostash also recovers a tree left dirty by an earlier failed run. A pull that fails is
  # only a warning, never fatal: the edition is still committed locally, and the next run rebases
  # it onto the remote and pushes both. Every failure says what went wrong; a silenced pull is
  # what let a rejected push go unnoticed for a day.
  if ! pulled="$(git -C "$BASE/repo" pull --rebase --autostash -q origin "$SITE_BRANCH" 2>&1)"; then
    log "SITE WARNING pull failed, committing on the local base | ${pulled:-no message}"
  fi
  if ! built="$(cd "$BASE/repo" && python3 tools/publish_site.py "$ENG/$PUB" "$TODAY" "$ENG/content.json" 2>&1)"; then
    log "SITE FAILED build | $built"
  else
    git -C "$BASE/repo" add -A "$SITE_DIR" >/dev/null 2>&1
    if git -C "$BASE/repo" diff --cached --quiet; then
      log "SITE unchanged | $built"
    elif pushed="$(git -C "$BASE/repo" -c user.name="The Daily Reconcile" \
                       -c user.email="noreply@localhost" commit -q -m "Edition of $TODAY" 2>&1 &&
                   git -C "$BASE/repo" push -q origin "$SITE_BRANCH" 2>&1)"; then
      log "SITE PUBLISHED | $built"
    else
      log "SITE FAILED push, the edition is committed in $BASE/repo | ${pushed:-no message}"
    fi
  fi
elif [ -n "$SITE_REPO" ]; then
  log "SITE SKIPPED (no public PDF, or $BASE/repo is not a git clone)"
fi
# Newsletter: after the site push, so the links in the email already resolve, and only when the
# public PDF exists, so it never points at a page that was not published. Opt-in and silent when
# BUTTONDOWN_TOKEN_FILE is unset, and it composes a draft rather than sending unless
# NEWSLETTER_STATUS says otherwise.
if [ -n "${BUTTONDOWN_TOKEN_FILE:-}" ] && [ -f "$PUB" ] && [ -f "$POST" ] && [ -d "$BASE/repo" ]; then
  log "$(cd "$BASE/repo" && python3 tools/newsletter_send.py \
         "$ENG/$POST" "$ENG/content.json" "$TODAY" 2>&1 | tail -n 1)"
fi
# LinkedIn posting is opt-in and off by default: it needs API access LinkedIn only grants on
# review. Without a token file the post is simply prepared, archived and emailed, and published
# by hand. Nothing is logged here when it is not configured.
if [ -n "${LINKEDIN_TOKEN_FILE:-}" ] && [ -f "$PUB" ] && [ -f "$POST" ] && [ -d "$BASE/repo" ]; then
  log "$(cd "$BASE/repo" && python3 tools/linkedin_post.py "$ENG/$POST" "$ENG/$PUB" 2>&1 | tail -n 1)"
fi

# Hand over to the print watcher (same disk, so the move is atomic). PRINT="no" in paper.conf
# skips it: the paper is still written, published and emailed, it simply never reaches paper.
# Queueing with no watcher running would park the PDF in inbox/ and then report "not printed"
# every morning for something that was switched off on purpose.
lead="$(python3 -c "import json; print(json.load(open('content.json'))['lead']['headline'])" 2>/dev/null)"
if [ "${PRINT:-yes}" = "no" ]; then
  log "PRINT SKIPPED (PRINT=no) ${summary:+| $summary}"
  notify "Published: $lead"
else
  cp "$PDF" "$BASE/.incoming.pdf" && mv "$BASE/.incoming.pdf" "$BASE/inbox/$PDF"
  log "QUEUED $PDF ${summary:+| $summary}"

  result="still in inbox after 3 minutes"
  for _ in $(seq 1 36); do
    sleep 5
    if [ -e "$BASE/printed/$PDF" ]; then result="PRINTED"; break; fi
    if [ -e "$BASE/failed/$PDF" ];  then result="FAILED (see print.log)"; break; fi
  done
  log "PRINT $result"
  if [ "$result" = "PRINTED" ]; then
    notify "Printed: $lead"
  else
    notify "Not printed: $result. The PDF is in DailyReconcile/archive/$TODAY"
  fi
fi
