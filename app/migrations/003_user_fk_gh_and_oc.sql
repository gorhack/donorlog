DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS github_users;
DROP TABLE IF EXISTS opencollective_users;

CREATE TABLE IF NOT EXISTS users
(
    user_id  SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE
--     open_collective_user_id INT REFERENCES opencollective_users (opencollective_user_id) ON DELETE CASCADE,
--     github_user_id          INT REFERENCES github_users (github_user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS github_users
(
    github_user_id    SERIAL PRIMARY KEY,
    github_username   VARCHAR(255),
    github_auth_token VARCHAR(255),
    user_id           INT NOT NULL REFERENCES users (user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS opencollective_users
(
    opencollective_user_id SERIAL PRIMARY KEY,
    opencollective_id      VARCHAR(255) UNIQUE NOT NULL,
    user_id                INT                 NOT NULL REFERENCES users (user_id) ON DELETE CASCADE
);

-- NEW
-- -- github new account
-- WITH X AS (
--     INSERT INTO users (username) VALUES ('mr 1') RETURNING user_id)
-- INSERT
-- INTO github_users (github_username, github_auth_token, user_id)
-- VALUES ('mr 1', 'gh_asdf', (SELECT user_id FROM X));
--
-- -- open collective new account
-- WITH X AS (
--     INSERT INTO users (username) VALUES ('mr 2') RETURNING user_id)
-- INSERT
-- INTO opencollective_users (opencollective_id, user_id)
-- VALUES ('oc_asdf', (SELECT user_id FROM X));
--
-- -- get user info from username
-- SELECT username, github_user_id, github_auth_token, opencollective_id
-- FROM users
--          LEFT JOIN github_users ON users.user_id = github_users.user_id
--          LEFT JOIN opencollective_users ON users.user_id = opencollective_users.user_id
-- WHERE users.username = 'mr 1';
--
-- -- open collective second
-- INSERT INTO opencollective_users (opencollective_id, user_id)
-- VALUES ('oc_qwer', (SELECT user_id from users WHERE username = 'mr 3'));
--
-- -- delete user
-- DELETE
-- FROM users
-- WHERE user_id = 4;
--
-- -- delete github user
-- DELETE
-- FROM github_users
-- WHERE github_username = 'mr 1';
--
-- -- delete github user 'mr 1' AND user if only github
-- WITH X AS (
--     DELETE FROM github_users WHERE github_username = 'mr 1' RETURNING user_id)
-- DELETE
-- FROM users
-- WHERE users.user_id = (SELECT user_id FROM X)
--   AND NOT EXISTS (SELECT users.user_id
--                   FROM users
--                            RIGHT JOIN opencollective_users ON users.user_id = opencollective_users.user_id
--                   WHERE opencollective_users.user_id = (SELECT user_id FROM X));


-- OLD
-- -- github new account
-- WITH X (id, username) AS (
--     INSERT INTO github_users (github_username, github_auth_token) VALUES ('mr 3', 'gh_asdf') RETURNING github_user_id, github_username
-- )
-- INSERT INTO users (github_user_id, username) VALUES ((SELECT id FROM X), (SELECT username FROM X));
--
-- -- open collective new account
-- WITH X AS (
--     INSERT INTO opencollective_users (opencollective_id) VALUES ('oc_asdf') RETURNING opencollective_user_id
-- )
-- INSERT INTO users (open_collective_user_id, username) VALUES ((SELECT opencollective_user_id FROM X), 'mr 2');
--
-- -- get user info from username
-- SELECT users.username, github_users.github_auth_token, opencollective_users.opencollective_id FROM users
--     LEFT JOIN github_users ON users.github_user_id = github_users.github_user_id
--     LEFT JOIN opencollective_users ON users.open_collective_user_id = opencollective_users.opencollective_user_id
-- WHERE users.username = 'mr 3';
--
-- -- open collective second
-- WITH X AS (
--     INSERT INTO opencollective_users (opencollective_id) VALUES ('oc_qwer') RETURNING opencollective_user_id
-- ) UPDATE users SET open_collective_user_id = (SELECT opencollective_user_id FROM X) WHERE users.username = 'mr 3';

