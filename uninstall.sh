#!/bin/bash
# Stops the morning Claude Code run. Keeps ~/DailyReconcile, the archive and the print watcher.
LABEL="com.dailyreconcile.morning"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
echo "Morning run removed. The print watcher is still installed (uninstall-print-watcher.sh removes it)."
