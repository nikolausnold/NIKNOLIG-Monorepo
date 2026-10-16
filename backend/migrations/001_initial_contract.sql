-- Proposed schema only. Do not apply until the SecurityChain-P0 and data-model
-- decisions documented in backend/README.md have been approved.
BEGIN;

CREATE TYPE app_area AS ENUM ('niknolig', 'niknolig-defense');
CREATE TYPE device_identity_state AS ENUM ('pending', 'verified', 'revoked');
CREATE TYPE device_link_state AS ENUM ('pending', 'active', 'revoked', 'expired');

CREATE TABLE device_installations (
    id UUID PRIMARY KEY,
    app_area app_area NOT NULL,
    principal_reference TEXT NOT NULL,
    installation_reference UUID NOT NULL,
    public_key_fingerprint CHAR(64),
    identity_state device_identity_state NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    verified_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    CONSTRAINT device_installations_area_installation_unique
        UNIQUE (app_area, installation_reference),
    CONSTRAINT device_installations_fingerprint_format
        CHECK (
            public_key_fingerprint IS NULL
            OR public_key_fingerprint ~ '^[0-9a-f]{64}$'
        ),
    CONSTRAINT device_installations_verified_requires_key
        CHECK (identity_state <> 'verified' OR public_key_fingerprint IS NOT NULL),
    CONSTRAINT device_installations_verified_timestamp
        CHECK ((identity_state = 'verified') = (verified_at IS NOT NULL)),
    CONSTRAINT device_installations_revoked_timestamp
        CHECK ((identity_state = 'revoked') = (revoked_at IS NOT NULL))
);

CREATE UNIQUE INDEX device_installations_area_fingerprint_unique
    ON device_installations (app_area, public_key_fingerprint)
    WHERE public_key_fingerprint IS NOT NULL;

CREATE TABLE device_links (
    id UUID PRIMARY KEY,
    first_device_id UUID NOT NULL
        REFERENCES device_installations (id) ON DELETE RESTRICT,
    second_device_id UUID NOT NULL
        REFERENCES device_installations (id) ON DELETE RESTRICT,
    state device_link_state NOT NULL DEFAULT 'pending',
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    activated_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    CONSTRAINT device_links_distinct_devices
        CHECK (first_device_id <> second_device_id),
    CONSTRAINT device_links_activation_timestamp
        CHECK ((state = 'active') = (activated_at IS NOT NULL)),
    CONSTRAINT device_links_revocation_timestamp
        CHECK ((state = 'revoked') = (revoked_at IS NOT NULL))
);

CREATE INDEX device_links_first_device_idx ON device_links (first_device_id);
CREATE INDEX device_links_second_device_idx ON device_links (second_device_id);

-- A link row records relationship lifecycle only. It grants no action or
-- cross-app authorization; future grants require a separately approved model.
COMMIT;
