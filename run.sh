#!/bin/bash

# ----------------------------------------------------------------------
# This is the entrypoint for the pipeline container.
# It's called automatically when the container starts.
#
# - Waits for Postgres to become ready
# - Then runs main.py (which runs ingestion → cleaning → enrichment)
# - Then keeps the container alive for debugging
# ----------------------------------------------------------------------

echo "RUN.SH started"
which python      
python --version     # prints version & file path of Python executable (useful for debugging) 

echo "Waiting for Postgres..."

# pg_isready is a Postgres CLI tool that checks if db is up
until pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER"; do
  echo "Postgres is unavailable - sleeping"
  sleep 2
done

echo "Postgres is up - running main.py"
python src/main.py
echo "Done"

# Keep container alive for manual exec/debug
sleep infinity
