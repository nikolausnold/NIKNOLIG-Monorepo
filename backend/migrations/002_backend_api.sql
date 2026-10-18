-- Local reference implementation only; does not approve deployment or P0.
-- Apply explicitly after 001_initial_contract.sql, never from API startup.
BEGIN;

ALTER TABLE device_installations ADD COLUMN public_key TEXT;
-- Migration 001 has no stored verification key or proof provenance. Do not
-- inherit its verified label as evidence of this API's possession protocol.
UPDATE device_installations SET identity_state = 'pending', verified_at = NULL
    WHERE identity_state = 'verified' AND public_key IS NULL;
-- Fingerprint-only records cannot create a possession challenge until an
-- explicitly approved key-migration flow exists. Revocation remains terminal.
ALTER TABLE device_installations ADD CONSTRAINT device_public_key_size
    CHECK (public_key IS NULL OR length(public_key) <= 2048);

CREATE TABLE backend_schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE backend_token_revocations (
    token_hash CHAR(64) PRIMARY KEY,
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX backend_token_revocations_expiry_idx
    ON backend_token_revocations (expires_at);

CREATE TABLE backend_rate_limits (
    bucket_key CHAR(64) NOT NULL,
    window_start BIGINT NOT NULL,
    requests INTEGER NOT NULL CHECK (requests > 0),
    PRIMARY KEY (bucket_key, window_start)
);
CREATE INDEX backend_rate_limits_window_idx ON backend_rate_limits (window_start);

CREATE TABLE backend_device_challenges (
    id UUID PRIMARY KEY,
    device_id UUID NOT NULL REFERENCES device_installations (id),
    app_area app_area NOT NULL,
    principal_reference TEXT NOT NULL,
    key_fingerprint CHAR(64) NOT NULL,
    message TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (expires_at > created_at)
);
CREATE INDEX backend_device_challenges_device_idx
    ON backend_device_challenges (device_id);
CREATE INDEX backend_device_challenges_expiry_idx
    ON backend_device_challenges (expires_at);

INSERT INTO backend_schema_migrations (version) VALUES ('002_backend_api');
COMMIT;
