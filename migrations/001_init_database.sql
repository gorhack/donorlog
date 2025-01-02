CREATE TABLE IF NOT EXISTS users (
	id  serial primary key,
    email varchar(254) unique,
	github_username varchar(255),
    github_auth_token varchar(255)
);