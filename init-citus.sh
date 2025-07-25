#!/bin/bash
set -e

# Wait for Postgres to be fully available using the default socket check
until pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"; do
  echo "⏳ Waiting for PostgreSQL to start..."
  sleep 2
done

echo "✅ PostgreSQL is ready. Initializing Citus cluster and CDC setup..."

# Execute all SQL commands in a single transaction
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL

-- EXTENSIONS
CREATE EXTENSION IF NOT EXISTS citus;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ADD CITUS WORKER NODES
SELECT citus_add_node('citus-worker-1', 5432);
SELECT citus_add_node('citus-worker-2', 5432);

-- MAIN DISTRIBUTED TABLES
CREATE TABLE public.profiles (
    id UUID PRIMARY KEY,
    email VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE public.workspaces (
    id UUID NOT NULL,
    user_id UUID NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (user_id, id)
);

CREATE TABLE public.pages (
    id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    user_id UUID NOT NULL,
    title VARCHAR(255),
    content TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (user_id, id)
);

-- DISTRIBUTE TABLES
SELECT create_distributed_table('public.profiles', 'id');
SELECT create_distributed_table('public.workspaces', 'user_id', colocate_with => 'public.profiles');
SELECT create_distributed_table('public.pages', 'user_id', colocate_with => 'public.profiles');

-- LOCAL CDC MIRROR TABLES
CREATE TABLE public.profiles_cdc (LIKE public.profiles INCLUDING DEFAULTS);
ALTER TABLE public.profiles_cdc ADD PRIMARY KEY (id);

CREATE TABLE public.workspaces_cdc (LIKE public.workspaces INCLUDING DEFAULTS);
ALTER TABLE public.workspaces_cdc ADD PRIMARY KEY (user_id, id);

CREATE TABLE public.pages_cdc (LIKE public.pages INCLUDING DEFAULTS);
ALTER TABLE public.pages_cdc ADD PRIMARY KEY (user_id, id);


-- =================================================================
-- IDEMPOTENT DUAL-WRITE STORED FUNCTIONS
-- =================================================================

-- PROFILES TABLE FUNCTIONS
CREATE OR REPLACE FUNCTION public.handle_profile_upsert(p_id UUID, p_email VARCHAR(255))
RETURNS VOID AS \$\$
DECLARE
    v_now TIMESTAMPTZ := now();
BEGIN
    INSERT INTO public.profiles(id, email, created_at, updated_at)
    VALUES (p_id, p_email, v_now, v_now)
    ON CONFLICT (id) DO UPDATE SET
        email = EXCLUDED.email,
        updated_at = v_now;

    INSERT INTO public.profiles_cdc(id, email, created_at, updated_at)
    VALUES (p_id, p_email, v_now, v_now)
    ON CONFLICT (id) DO UPDATE SET
        email = EXCLUDED.email,
        updated_at = v_now;
END;
\$\$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION public.handle_profile_delete(p_id UUID)
RETURNS VOID AS \$\$
BEGIN
    DELETE FROM public.profiles WHERE id = p_id;
    DELETE FROM public.profiles_cdc WHERE id = p_id;
END;
\$\$ LANGUAGE plpgsql;

-- WORKSPACES TABLE FUNCTIONS
CREATE OR REPLACE FUNCTION public.handle_workspace_upsert(p_id UUID, p_user_id UUID, p_name VARCHAR(255))
RETURNS VOID AS \$\$
DECLARE
    v_now TIMESTAMPTZ := now();
BEGIN
    INSERT INTO public.workspaces(id, user_id, name, created_at, updated_at)
    VALUES (p_id, p_user_id, p_name, v_now, v_now)
    ON CONFLICT (user_id, id) DO UPDATE SET
        name = EXCLUDED.name,
        updated_at = v_now;

    INSERT INTO public.workspaces_cdc(id, user_id, name, created_at, updated_at)
    VALUES (p_id, p_user_id, p_name, v_now, v_now)
    ON CONFLICT (user_id, id) DO UPDATE SET
        name = EXCLUDED.name,
        updated_at = v_now;
END;
\$\$ LANGUAGE plpgsql;

-- PAGES TABLE FUNCTIONS
CREATE OR REPLACE FUNCTION public.handle_page_upsert(p_id UUID, p_workspace_id UUID, p_user_id UUID, p_title VARCHAR(255), p_content TEXT)
RETURNS VOID AS \$\$
DECLARE
    v_now TIMESTAMPTZ := now();
BEGIN
    INSERT INTO public.pages(id, workspace_id, user_id, title, content, created_at, updated_at)
    VALUES (p_id, p_workspace_id, p_user_id, p_title, p_content, v_now, v_now)
    ON CONFLICT (user_id, id) DO UPDATE SET
        title = EXCLUDED.title,
        content = EXCLUDED.content,
        updated_at = v_now;

    INSERT INTO public.pages_cdc(id, workspace_id, user_id, title, content, created_at, updated_at)
    VALUES (p_id, p_workspace_id, p_user_id, p_title, p_content, v_now, v_now)
    ON CONFLICT (user_id, id) DO UPDATE SET
        title = EXCLUDED.title,
        content = EXCLUDED.content,
        updated_at = v_now;
END;
\$\$ LANGUAGE plpgsql;


-- REPLICATION SETUP FOR DEBEZIUM
ALTER TABLE public.profiles_cdc REPLICA IDENTITY FULL;
ALTER TABLE public.workspaces_cdc REPLICA IDENTITY FULL;
ALTER TABLE public.pages_cdc REPLICA IDENTITY FULL;

-- Create a dedicated replication user
CREATE ROLE ${REPLICATOR_USER} WITH REPLICATION LOGIN PASSWORD '${REPLICATOR_PASSWORD}';
GRANT SELECT ON public.profiles_cdc, public.workspaces_cdc, public.pages_cdc TO ${REPLICATOR_USER};

-- Create a publication for all the CDC tables
CREATE PUBLICATION debezium_publication FOR TABLE public.profiles_cdc, public.workspaces_cdc, public.pages_cdc;

EOSQL

echo "🎉 Production-ready initialization complete."
