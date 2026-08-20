#!/bin/sh

echo "Waiting for database..."

# Wait until Postgres is reachable
# until pg_isready -h db -p 5432 -U "$POSTGRES_USER"
# do
#     sleep 2
# done

echo "Database is ready"

python scripts/seed_defaults.py

exec "$@"