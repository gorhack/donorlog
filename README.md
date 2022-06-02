# donorlog
Aggregate online donations

### Requirements:
 - Python 3.8
 - direnv and update `secrets` file with updated OAuth client IDs and secrets
 - Register a new [Github OAuth application](https://github.com/settings/applications/new)
   - Callback URL is `/authenticate/github`
   - Add respective client IDs and secrets from `.envrc` to your `secrets` file

### Running
 - `pip install -r requirements.txt`
 - `uvicorn main:app`

### Testing
 - `pytest`
