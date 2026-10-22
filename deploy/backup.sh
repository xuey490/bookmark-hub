#!/usr/bin/env bash
set -euo pipefail

# Usage: ./backup.sh [db_path] [backup_dir]
DB_PATH="${1:-/opt/bookmark-hub/backend/data/bookmarks.db}"
BACKUP_DIR="${2:-/opt/bookmark-hub/backup}"

if [[ ! -f "$DB_PATH" ]]; then
  echo "database not found: $DB_PATH" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%F)"
TARGET="$BACKUP_DIR/bookmarks-$STAMP.db"

sqlite3 "$DB_PATH" "VACUUM INTO '$TARGET'"
find "$BACKUP_DIR" -name 'bookmarks-*.db' -mtime +7 -delete

echo "backup written: $TARGET"
