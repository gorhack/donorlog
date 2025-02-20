ALTER TABLE github_users
    ADD total_cents  INT         NOT NULL DEFAULT 0,
    ADD month_cents  INT         NOT NULL DEFAULT 0,
    ADD last_checked TIMESTAMPTZ NOT NULL DEFAULT '2025-01-01 00:00:0+00:00';

ALTER TABLE opencollective_users
    ADD total_cents  INT         NOT NULL DEFAULT 0,
    ADD month_cents  INT         NOT NULL DEFAULT 0,
    ADD last_checked TIMESTAMPTZ NOT NULL DEFAULT '2025-01-01 00:00:0+00:00';
