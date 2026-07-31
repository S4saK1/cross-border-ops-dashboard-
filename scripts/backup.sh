#!/bin/bash
# backup.sh — Database backup script supporting SQLite and PostgreSQL
# Usage: ./backup.sh
# Env vars: DATABASE_URL (required), BACKUP_DIR (optional)

set -euo pipefail

# ── Configuration ──────────────────────────────────────────
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

# ── Validate DATABASE_URL ──────────────────────────────────
if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: DATABASE_URL is not set. Cannot determine database type or connection." >&2
    exit 1
fi

# ── Create backup directory ────────────────────────────────
mkdir -p "$BACKUP_DIR"

# ── Determine database type from URL scheme ────────────────
BACKUP_FILE="${BACKUP_DIR}/bilingual_cms_${TIMESTAMP}"

case "$DATABASE_URL" in
    postgresql://*|postgres://*)
        # PostgreSQL: use pg_dump
        echo "Detected PostgreSQL database."

        # Extract connection components from DATABASE_URL
        # Format: postgresql://user:pass@host:port/dbname
        PG_URL="${DATABASE_URL#*://}"
        PG_USER="${PG_URL%%:*}"
        PG_REST="${PG_URL#*:}"
        PG_PASS="${PG_REST%%@*}"
        PG_HOST_PORT="${PG_REST#*@}"
        PG_HOST="${PG_HOST_PORT%%:*}"
        PG_REST2="${PG_HOST_PORT#*:}"
        PG_PORT="${PG_REST2%%/*}"
        PG_DB="${PG_REST2#*/}"
        # Strip query params from PG_DB if present
        PG_DB="${PG_DB%%\?*}"

        BACKUP_FILE="${BACKUP_FILE}.sql.gz"

        echo "Backing up PostgreSQL database '$PG_DB' on $PG_HOST:$PG_PORT ..."
        export PGPASSWORD="$PG_PASS"
        if pg_dump \
            -h "$PG_HOST" \
            -p "$PG_PORT" \
            -U "$PG_USER" \
            -d "$PG_DB" \
            --clean --if-exists 2>/dev/null | gzip > "$BACKUP_FILE"; then
            unset PGPASSWORD
        else
            RC=$?
            unset PGPASSWORD
            echo "ERROR: pg_dump failed with exit code $RC" >&2
            rm -f "$BACKUP_FILE"
            exit 1
        fi
        ;;

    sqlite:///*|sqlite:///*)
        # SQLite: extract path from DATABASE_URL and use .backup
        echo "Detected SQLite database."

        SQLITE_PATH="${DATABASE_URL#sqlite:///}"
        # Handle relative paths (e.g. sqlite:///./data.db → ./data.db)
        SQLITE_PATH="${SQLITE_PATH#./}"

        if [ ! -f "$SQLITE_PATH" ]; then
            echo "ERROR: SQLite database file not found: $SQLITE_PATH" >&2
            exit 1
        fi

        BACKUP_FILE="${BACKUP_FILE}.db"

        echo "Backing up SQLite database: $SQLITE_PATH ..."
        if sqlite3 "$SQLITE_PATH" ".backup '$BACKUP_FILE'"; then
            :
        else
            echo "ERROR: sqlite3 .backup failed" >&2
            rm -f "$BACKUP_FILE"
            exit 1
        fi
        ;;

    *)
        echo "ERROR: Unsupported DATABASE_URL scheme. Expected 'postgresql://' or 'sqlite:///'." >&2
        exit 1
        ;;
esac

# ── Verify backup was created ──────────────────────────────
if [ ! -f "$BACKUP_FILE" ] || [ ! -s "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file was not created or is empty: $BACKUP_FILE" >&2
    exit 1
fi

BACKUP_SIZE=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || stat -f%z "$BACKUP_FILE" 2>/dev/null || echo "0")
echo "Backup created successfully: $BACKUP_FILE (${BACKUP_SIZE} bytes)"
exit 0
