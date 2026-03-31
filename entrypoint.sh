#!/bin/bash

# Exit on unset variables, but NOT on errors — we handle them explicitly below
set -u

# ── Working directory ────────────────────────────────────────────────────────
cd /app
echo "=== Startup: $(date -u '+%Y-%m-%dT%H:%M:%SZ') ==="
echo "Working directory: $(pwd)"

# ── Sanity-check the migrations directory ───────────────────────────────────
echo ""
echo "--- Migration file check ---"
if [ ! -d "migrations" ]; then
    echo "ERROR: migrations/ directory not found in $(pwd)" >&2
    exit 1
fi

if [ ! -d "migrations/versions" ]; then
    echo "ERROR: migrations/versions/ directory not found" >&2
    exit 1
fi

if [ ! -f "alembic.ini" ]; then
    echo "ERROR: alembic.ini not found in $(pwd)" >&2
    exit 1
fi

echo "alembic.ini location : $(pwd)/alembic.ini"
echo "script_location      : $(grep '^script_location' alembic.ini || echo '(not found)')"
echo ""
echo "Migration files present:"
ls -1 migrations/versions/*.py 2>/dev/null || echo "  (none found)"
echo ""

# ── Show what Alembic sees before running ───────────────────────────────────
echo "--- Alembic heads (known to the codebase) ---"
alembic heads --verbose 2>&1 || true

echo ""
echo "--- Alembic current (recorded in the database) ---"
alembic current --verbose 2>&1 || true

echo ""

# ── Run migrations with retry on transient DB startup errors ────────────────
echo "--- Applying migrations (alembic upgrade head) ---"
MAX_RETRIES=5
RETRY_DELAY=5
ATTEMPT=0
MIGRATION_OK=false

while [ $ATTEMPT -lt $MAX_RETRIES ]; do
    ATTEMPT=$((ATTEMPT + 1))
    echo "Attempt $ATTEMPT / $MAX_RETRIES ..."

    # Capture both stdout and stderr; keep exit code
    MIGRATION_OUTPUT=$(alembic -v upgrade head 2>&1)
    MIGRATION_EXIT=$?

    echo "$MIGRATION_OUTPUT"

    if [ $MIGRATION_EXIT -eq 0 ]; then
        MIGRATION_OK=true
        echo "Migrations applied successfully."
        break
    fi

    # ── Diagnose the failure ─────────────────────────────────────────────────
    if echo "$MIGRATION_OUTPUT" | grep -q "Can't locate revision"; then
        # Extract the offending revision from the error message
        BAD_REV=$(echo "$MIGRATION_OUTPUT" | grep -oP "(?<=identified by ')([a-f0-9]+)" | head -1)
        echo ""
        echo "ERROR: Alembic cannot locate revision '${BAD_REV:-unknown}'." >&2
        echo "  This usually means the database's alembic_version table references a" >&2
        echo "  revision that is not present in migrations/versions/." >&2
        echo ""
        echo "  Available revisions on disk:" >&2
        grep -r "^revision" migrations/versions/*.py 2>/dev/null | sed 's/^/    /' >&2
        echo ""
        echo "  Current DB version (raw SQL may help):" >&2
        echo "  SELECT version_num FROM alembic_version;" >&2
        echo ""
        echo "  To recover, connect to the database and run:" >&2
        echo "    DELETE FROM alembic_version;" >&2
        echo "  Then redeploy — Alembic will re-apply all migrations from scratch." >&2
        echo ""
        echo "  Alternatively, if the schema is already correct, stamp the DB to head:" >&2
        echo "    alembic stamp head" >&2
        echo ""
        # Do not retry — this is a data/config problem, not a transient error
        break
    fi

    if echo "$MIGRATION_OUTPUT" | grep -qiE "database system is starting up|connection refused|could not connect"; then
        echo "Database not ready yet, retrying in ${RETRY_DELAY}s ..."
        sleep $RETRY_DELAY
        continue
    fi

    # Unknown error — print diagnostics and stop retrying
    echo "ERROR: Migration failed with an unexpected error (exit code $MIGRATION_EXIT)." >&2
    break
done

if [ "$MIGRATION_OK" = false ]; then
    echo ""
    echo "FATAL: Could not apply database migrations. Application will not start." >&2
    echo "Review the output above to diagnose the problem." >&2
    exit 1
fi

# ── Start the application ────────────────────────────────────────────────────
echo ""
echo "--- Starting application ---"
exec python main.py
