#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 -d $DB_NAME <<-EOSQL
    create extension if not exists "uuid-ossp" with schema actual_state;
    create extension if not exists "btree_gist" with schema actual_state;
    create extension if not exists "pg_trgm" with schema actual_state;
EOSQL
