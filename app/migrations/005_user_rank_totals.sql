-- speeds up materialized view refresh
CREATE INDEX idx_user_id_username ON users (user_id, username);

-- Materialized view of the total and month rankings.
-- Could be out of date when queried against; will need to refresh periodically, but exact "rankings" don't need to be
-- precise.
-- Over 3,000 times faster than querying every time the page loads...
CREATE MATERIALIZED VIEW ranked_users_view AS
(
SELECT RANK() OVER (ORDER BY t.total_cents DESC) total_rank,
       RANK() OVER (ORDER BY t.month_cents DESC) month_rank,
       t.*
FROM (SELECT username,
             COALESCE(github_users.total_cents, 0) + COALESCE(opencollective_users.total_cents, 0) as total_cents,
             COALESCE(github_users.month_cents, 0) + COALESCE(opencollective_users.month_cents, 0) as month_cents
      FROM users
               LEFT JOIN github_users ON users.user_id = github_users.user_id
               LEFT JOIN opencollective_users ON users.user_id = opencollective_users.user_id) t
ORDER BY total_rank, username);

-- Must have a unique index for concurrent refresh
CREATE UNIQUE INDEX ranked_users_idx
    ON ranked_users_view (username);