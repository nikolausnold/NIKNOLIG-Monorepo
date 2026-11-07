-- Device connection API schema (additive; 000 and 001 are unchanged).
-- Applied only with --approve-device-api-schema and only after 001.
BEGIN;

ALTER TABLE device_installations
    ADD COLUMN public_key BYTEA,
    ADD COLUMN display_name TEXT,
    ADD CONSTRAINT device_installations_public_key_length
        CHECK (public_key IS NULL OR octet_length(public_key) = 32),
    ADD CONSTRAINT device_installations_display_name_length
        CHECK (display_name IS NULL OR length(display_name) BETWEEN 1 AND 64);

-- At most one pending/active link per unordered device pair.
CREATE UNIQUE INDEX device_links_open_pair_unique
    ON device_links (LEAST(first_device_id, second_device_id),
                     GREATEST(first_device_id, second_device_id))
    WHERE state IN ('pending', 'active');

CREATE TABLE device_challenges (
    nonce_hash BYTEA PRIMARY KEY,
    device_id UUID NOT NULL REFERENCES device_installations (id) ON DELETE RESTRICT,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX device_challenges_expiry_idx ON device_challenges (expires_at);

CREATE TABLE device_sessions (
    id UUID PRIMARY KEY,
    device_id UUID NOT NULL REFERENCES device_installations (id) ON DELETE RESTRICT,
    refresh_hash BYTEA NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    rotated_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    revoke_reason TEXT,
    CONSTRAINT device_sessions_reason_requires_revocation
        CHECK ((revoked_at IS NULL) = (revoke_reason IS NULL))
);
CREATE INDEX device_sessions_device_idx ON device_sessions (device_id);

-- Every consumed refresh hash is kept for reuse detection (any older replay revokes).
CREATE TABLE device_refresh_history (
    refresh_hash BYTEA PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES device_sessions (id) ON DELETE RESTRICT,
    consumed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX device_refresh_history_session_idx ON device_refresh_history (session_id);

CREATE TABLE device_pairings (
    id UUID PRIMARY KEY,
    initiator_device_id UUID NOT NULL REFERENCES device_installations (id) ON DELETE RESTRICT,
    claimant_device_id UUID REFERENCES device_installations (id) ON DELETE RESTRICT,
    code_hash BYTEA NOT NULL,
    state TEXT NOT NULL DEFAULT 'open'
        CHECK (state IN ('open', 'claimed', 'confirmed', 'cancelled', 'expired')),
    initiator_confirmed_at TIMESTAMPTZ,
    claimant_confirmed_at TIMESTAMPTZ,
    link_id UUID REFERENCES device_links (id) ON DELETE RESTRICT,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT device_pairings_distinct_devices
        CHECK (claimant_device_id IS NULL OR claimant_device_id <> initiator_device_id)
);
CREATE UNIQUE INDEX device_pairings_live_code_unique
    ON device_pairings (code_hash) WHERE state IN ('open', 'claimed');
CREATE INDEX device_pairings_initiator_idx ON device_pairings (initiator_device_id);

CREATE TABLE device_grants (
    id UUID PRIMARY KEY,
    link_id UUID NOT NULL REFERENCES device_links (id) ON DELETE RESTRICT,
    grantor_device_id UUID NOT NULL REFERENCES device_installations (id) ON DELETE RESTRICT,
    grantee_device_id UUID NOT NULL REFERENCES device_installations (id) ON DELETE RESTRICT,
    scope TEXT NOT NULL CHECK (scope IN ('status:read', 'events:read', 'alerts:send')),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ,
    CONSTRAINT device_grants_distinct_devices CHECK (grantor_device_id <> grantee_device_id),
    CONSTRAINT device_grants_expiry_after_creation CHECK (expires_at > created_at)
);
CREATE INDEX device_grants_link_idx ON device_grants (link_id);

CREATE TABLE device_status (
    device_id UUID PRIMARY KEY REFERENCES device_installations (id) ON DELETE RESTRICT,
    state TEXT NOT NULL CHECK (state IN ('ok', 'warning', 'alert', 'unknown')),
    detail TEXT CHECK (detail IS NULL OR length(detail) <= 200),
    reported_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Audit trail: metadata only; never keys, tokens, pairing codes or user content.
CREATE TABLE device_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    device_id UUID NOT NULL REFERENCES device_installations (id) ON DELETE RESTRICT,
    source_device_id UUID REFERENCES device_installations (id) ON DELETE RESTRICT,
    link_id UUID REFERENCES device_links (id) ON DELETE RESTRICT,
    kind TEXT NOT NULL CHECK (kind ~ '^[a-z_]{1,48}$'),
    detail TEXT CHECK (detail IS NULL OR length(detail) <= 200),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX device_events_device_idx ON device_events (device_id, id DESC);

COMMIT;
