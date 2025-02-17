DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS github_users;
DROP TABLE IF EXISTS opencollective_users;

CREATE TABLE IF NOT EXISTS users
(
    user_id  SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS github_users
(
    github_user_id    SERIAL PRIMARY KEY,
    github_id         VARCHAR(255) UNIQUE NOT NULL, -- GitHub's GraphQL ID
    github_username   VARCHAR(255)        NOT NULL,
    github_auth_token VARCHAR(255),
    user_id           INT                 NOT NULL REFERENCES users (user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS opencollective_users
(
    opencollective_user_id  SERIAL PRIMARY KEY,
    opencollective_id       VARCHAR(255) UNIQUE NOT NULL, -- OpenCollective's GraphQL ID
    opencollective_username VARCHAR(255)        NOT NULL,
    user_id                 INT                 NOT NULL REFERENCES users (user_id) ON DELETE CASCADE
);
