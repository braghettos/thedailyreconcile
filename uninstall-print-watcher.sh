#!/bin/bash
# Removes the print watcher. Keeps ~/DailyReconcile and its files.
LABEL="com.dailyreconcile.printwatcher"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
rm -f "$PLIST"
echo "Print watcher removed. ~/DailyReconcile was kept."
