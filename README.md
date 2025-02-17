# donorlog

Aggregate online donations and both recognize top contributors and top developers/projects.

## Project Goals:

### Problem statement:

Open source projects play a critical role in driving innovation and providing valuable resources to other developers.
However, many of these projects struggle to secure adequate funding to sustain development, maintain quality, and
implement new features. Many users that are willing to donate to open source projects are unable to maximize financial
contributions to these projects.

### Objective:

This application will provide an easy way to showcase both users and the open source projects themselves. This
application will do the following:

1) Utilize open source donation platforms (GitHub, OpenCollective, etc.) to identify user contributions and projects
2) Publicly acknowledge and support users that donate to open source projects (tier badges, etc.)
3) Identify projects worthy of support (i.e. many users with small amounts or large amounts but few total users)
4) Determine a project to donate $X each month based on #3

### Roadmap:

- [ ] GitHub API to identify users and projects and the total monthly contributions
- [ ] Maintain database that stores references to users and projects and the monthly donation totals
- [ ] OpenCollective API to identify users and projects and the monthly contributions
- [ ] Public badge or identifier highlighting contribution tier
- [ ] Monthly rollup of users and projects
- [ ] Determine project selection for $X donation each month

### Ideal User Flow:

1) Users login to each respective platform in this application to update the projects and amounts they contribute
2) User receives a badge for total and monthly amounts contributed
3) User receives a rollup each month on their own and community projects receiving donations

### Requirements:

- Python 3.8+
- direnv and update `secrets` file with updated OAuth client IDs and secrets
- docker-compose for Postgres database
- Register a new [GitHub OAuth application](https://github.com/settings/applications/new)
  - Callback URL is `.../oauth/gh_token`
- Register a new [OpenCollective OAuth application](https://docs.opencollective.com/help/developers/oauth)
  - Callback URL is `.../oauth/oc_token`
- Add respective client IDs and secrets from `.envrc` to your `secrets` file
- View `/docs` for swagger documentation

### Running

- `pip install -r requirements.txt`
- `docker-compose up -d`
- `uvicorn app.main:app`

### Testing

- `pytest`
