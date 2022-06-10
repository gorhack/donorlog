# donorlog
Aggregate online donations

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
