# API Foundry

A reusable, tangible API MVP from THEJANAIDU's API design roadmap. Turn a resource definition into authenticated, persistent REST endpoints and interactive documentation. Start with tasks; generate books, inventory, tickets, or other simple resources.

This is a foundation for building applications, not a promise to generate arbitrary software. Domain rules, relationships, payments, and advanced protocols require application code.

## Run in five minutes

Requires Python 3.9+ (Python 3.12 recommended).

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Generate a token; keep the output private.
python -c 'import secrets; print(secrets.token_urlsafe(32))'
# Replace REPLACE_ME with that token. Never commit this value.
export API_TOKENS='{"REPLACE_ME":{"subject":"alice","scopes":["read","write"]}}'
uvicorn app.main:create_app --factory --reload
```

Open http://127.0.0.1:8000/docs. Click **Authorize**, paste the token alone, and try `POST /v1/tasks` with:

```json
{"title":"Ship my first API","done":false}
```

Copy the returned `id`, list tasks, fetch the record, replace it with PUT, then DELETE it. `/redoc` is the reading view; `/openapi.json` is the machine-readable contract. `/health` checks database connectivity. Data persists in `foundry.db` across restarts.

For terminal examples, set `TOKEN` to the same private token:

```sh
curl -i http://127.0.0.1:8000/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: my-first-task' \
  -d '{"title":"Ship my first API","done":false}'
curl 'http://127.0.0.1:8000/v1/tasks?limit=10&offset=0&q=Ship&sort=-id' \
  -H "Authorization: Bearer $TOKEN"
```

Repeat the POST with the same key and body: it returns the original resource. A changed body with that key returns 409. GET a record and send its `ETag` back as `If-None-Match` to receive 304 when unchanged. Sorting supports `id` and `-id` only (UUID order, not creation time). Pagination uses offset/limit.

## Build your own application

```sh
python scripts/add_resource.py books title:str pages:int published:bool
# Restart uvicorn. /v1/books now has GET, POST, GET by ID, PUT, DELETE.
```

The generator edits `app/resources.json`. Supported field types: `str`, `int`, `float`, `bool`; all fields are required and unknown fields are rejected. PUT replaces the entire data object. Each response wraps fields inside `data` and includes `id` and navigation `links`. Owner is derived from the token, never supplied by clients.

1. Define the nouns and fields your app needs.
2. Generate resources, restart, and explore `/docs`.
3. Build a frontend/mobile client that calls `/v1/<resource>` with its user's bearer token.
4. Add domain-specific validation, relationships, and workflows in `app/main.py`; replace generic JSON storage with domain tables as complexity grows.
5. Add tests for the new rules and inspect `/openapi.json` for contract changes.
6. Read [the build guide](docs/BUILD_GUIDE.md) and [roadmap coverage](docs/ROADMAP.md) before deploying.

Do not embed these server-issued static tokens in a public frontend bundle. For a real multi-user product, replace them with an OIDC login flow and validated access tokens. The default configuration intentionally refuses to start without credentials.

## Test and package

```sh
python -m pytest -q
# Optional Docker deployment; set API_TOKENS in your shell first.
docker build -t api-foundry .
docker run --rm -p 8000:8000 -e API_TOKENS -v foundry-data:/data api-foundry
```

Docker and CI configuration are provided; local verification used Python 3.9.6. Docker execution and remote GitHub Actions were not run in this environment.

## Publish under THEJANAIDU

`https://github.com/THEJANAIDU` is an account, not a repository. Suggested repository name: `api-foundry`. This delivery includes a local initial Git commit. No remote repository has been created.

With GitHub CLI installed and authenticated as THEJANAIDU:

```sh
gh auth login
gh repo create THEJANAIDU/api-foundry --public --source=. --remote=origin --push
```

Or create an empty repository named `api-foundry` through GitHub, then run:

```sh
git remote add origin https://github.com/THEJANAIDU/api-foundry.git
git push -u origin main
```

Choose private visibility instead if preferred. Never commit tokens, `.env`, or database files. For future projects, enable **Template repository** in GitHub settings and select **Use this template**.
