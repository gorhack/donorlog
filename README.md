# donorlog
Aggregate online donations

## Project Goals:
### Problem statement:
Open source projects play a critical role in driving innovation and providing valuable resources to other developers. 
However, many of these projects struggle to secure adequate funding to sustain development, maintain quality, and
implement new features. Many users that are willing to donate to open source projects are unable to maximize financial
contributions to these projects.

### Objective:
This application will provide an easy way to showcase both users and the open source projects themselves. This
application will do the following:
1) Utilize open source donation platforms (GitHub, OpenCollective, etc) to identify user contributions and projects
2) Publicly acknowledge and support users that donate to open source projects (tier badges, etc)
3) Identify projects worthy of support (i.e. many users with small amounts or large amounts but few total users)
4) Determine a project to donate $X each month based on #3

### Roadmap:
- [ ] GitHub API to identify users and projects and the monthly contributions
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
 - Python 3.8
 - direnv and update `secrets` file with updated OAuth client IDs and secrets
 - Register a new [Github OAuth application](https://github.com/settings/applications/new)
   - Callback URL is `/oauth/token`
   - Add respective client IDs and secrets from `.envrc` to your `secrets` file
   - Create a JWT secret (how to in `.envrc` file)
 - View `/docs` for documentation. Login with the `Authorize` button which will go through the GitHub OAuth
authorizationCode flow

### Running
 - `pip install -r requirements.txt`
 - `uvicorn main:app`

### Testing
 - `pytest`
