-- Infrastructure only. This does not approve or apply the proposed product model.
CREATE TABLE IF NOT EXISTS public.backend_schema_migrations (
    version TEXT PRIMARY KEY,
    checksum CHAR(64) NOT NULL CHECK (checksum ~ '^[0-9a-f]{64}$'),
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
