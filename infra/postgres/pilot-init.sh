#!/bin/sh
set -eu

: "${PLACEMENTOS_APP_DB_PASSWORD:?application database password is required}"
: "${PLACEMENTOS_WORKFLOW_DB_PASSWORD:?workflow database password is required}"

psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=app_password="$PLACEMENTOS_APP_DB_PASSWORD" \
  --set=workflow_password="$PLACEMENTOS_WORKFLOW_DB_PASSWORD" <<'SQL'
CREATE ROLE placementos_app LOGIN PASSWORD :'app_password' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
CREATE ROLE placementos_workflow LOGIN PASSWORD :'workflow_password' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
CREATE SCHEMA IF NOT EXISTS workflow_checkpoints AUTHORIZATION placementos_workflow;
GRANT CONNECT ON DATABASE placementos TO placementos_app, placementos_workflow;
GRANT USAGE ON SCHEMA public TO placementos_app;
GRANT USAGE, CREATE ON SCHEMA workflow_checkpoints TO placementos_workflow;
ALTER ROLE placementos_app SET row_security = on;
SQL
