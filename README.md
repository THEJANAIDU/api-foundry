# API Foundry · Beginner Edition

A reusable, tangible API MVP from THEJANAIDU's API design roadmap. Turn a resource definition into authenticated, persistent REST endpoints and interactive documentation. Start with tasks; generate books, inventory, tickets, or other simple resources.

This is a foundation for building applications, not a promise to generate arbitrary software. Domain rules, relationships, payments, and advanced protocols require application code.

## Start here — no API experience required

Clone this repository (or download and extract its source), then open a terminal in the project folder:

```sh
git clone https://github.com/THEJANAIDU/api-foundry.git
cd api-foundry
python3 start.py
# Windows: py start.py
```

If Git is unavailable, use GitHub’s **Code → Download ZIP**, extract it, open a terminal in that folder, and run `python3 start.py`.

Requires Python 3.9+ (3.12 recommended) and internet access on first run. The launcher creates `.venv`, installs dependencies, and prints a random local token. Open **http://127.0.0.1:8000**, paste the token into Connect, and create a task. Every action shows its HTTP request and response. The token is held only in the page's memory and is redacted from the inspector.

Read [Your first API](docs/FIRST_API.md) alongside the working task tracker. It covers requests, JSON, status codes, authentication, persistence, code walkthroughs and six exercises with acceptance checks. [Troubleshooting](docs/TROUBLESHOOTING.md) covers common setup failures. The lesson is also available at `/learn` while the server runs.

The launcher binds to localhost, generates a new credential each run, and preserves the `local-learner` identity so your tasks remain available. Stop it with Ctrl+C. Restart after changing resource definitions. Generated resources appear in `/docs`; the example UI specifically demonstrates tasks.

## Make your API available

Follow the [complete deployment walkthrough](docs/DEPLOYMENT.md): local Docker rehearsal, private SSH access, a public Ubuntu server with DNS/HTTPS, persistent storage, smoke tests, backups/restore, updates and rollback. Read the [executed verification report](docs/DEPLOYMENT_VERIFICATION.md) to distinguish tested container/TLS behavior from public DNS and certificate checks you must perform on your own server.

Quick local deployment rehearsal (Docker must be running):

```sh
python3 scripts/configure_deploy.py
docker compose -f compose.yaml -f deploy/compose.local.yaml up -d --build --wait
python3 scripts/smoke_deploy.py
```

Open `http://127.0.0.1:8080` and use the private token in `.deploy-token`. Unlike the learning launcher, this runs detached and keeps a stable deployment credential. Run `python3 scripts/verify_compose.py` for the isolated persistence/backup/restore/HTTPS acceptance test.

## Manual startup and multiple identities

Use this path when learning ownership/scopes or preparing your own server configuration:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -c 'import secrets; print(secrets.token_urlsafe(32))'
# Replace ALICE_KEY and BOB_KEY with distinct random private values.
export API_TOKENS='{"ALICE_KEY":{"subject":"alice","scopes":["read","write"]},"BOB_KEY":{"subject":"bob","scopes":["read"]}}'
uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

In `/docs` click Authorize and enter the token alone. Alice can create a task with `{"title":"Ship my first API","done":false}`. Bob cannot read Alice's records, and Bob's read-only scope forbids creating records. Use distinct tokens for each identity.

For terminal examples set TOKEN to your private token:

```sh
curl -i http://127.0.0.1:8000/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: my-first-task' \
  -d '{"title":"Ship my first API","done":false}'
curl 'http://127.0.0.1:8000/v1/tasks?limit=10&offset=0&q=Ship&sort=-id' \
  -H "Authorization: Bearer $TOKEN"
```

Repeat POST with the same key/body to receive the same resource; a different body with that key returns 409. GET a record and return its ETag as If-None-Match to receive 304 when unchanged. Sort supports id/-id (UUID order, not creation time). Pagination uses offset/limit.

## Build your own application

```sh
python3 scripts/add_resource.py books title:str pages:int published:bool
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
.venv/bin/python -m pytest -q
# Windows: .venv\Scripts\python -m pytest -q
# Optional Docker deployment; set API_TOKENS in your shell first.
docker build -t api-foundry .
docker run --rm -p 8000:8000 -e API_TOKENS -v foundry-data:/data api-foundry
```

Local verification: 8 tests pass on Python 3.9.6, plus a fresh launcher setup and browser CRUD/validation checks. GitHub Actions runs the integration suite on Python 3.12; see the Actions tab for its latest result. Container deployment, proxy routing, HTTPS with a local CA, persistence and backup/restore are covered by the deployment acceptance test. Windows execution and live public DNS/ACME issuance have not been verified in this environment.

## Repository and reuse

Project home: https://github.com/THEJANAIDU/api-foundry . The source folders are intended to run directly from a clone; the ZIP is a convenience snapshot, not the runtime source. Use this repository as a starting point for your own project, configure your own remote, and never commit tokens, `.env` or databases.

## Local learning versus production

Working today: task UI, request inspector, guided lesson, resource generation, owner-isolated REST CRUD, scopes, SQLite, OpenAPI, Problem Details, ETags, persistent retry keys, local rate limits and integration tests.

Before public deployment: replace static credentials with real user authentication, review dependencies, set TLS/body-size/timeouts at a proxy, add migrations/backups and appropriate database concurrency, distributed quotas, and monitoring. See [architecture and limitations](docs/BUILD_GUIDE.md) and [roadmap coverage](docs/ROADMAP.md). GraphQL, gRPC, webhook workers and billing are extension work.
