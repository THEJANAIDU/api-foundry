# Deployment verification — 2026-10-25

## Executed locally

Host: macOS on Apple silicon. Docker Engine 28.2.2 through Docker Desktop, Compose v5.1.3, Linux ARM64 containers, Python 3.12-slim application image, Caddy 2.10.2-alpine. Host helper scripts ran with Python 3.9.6. Application integration suite: **8 passed**.

Executed from the repository root:

```sh
python3 scripts/configure_deploy.py
docker compose -f compose.yaml -f deploy/compose.local.yaml config --quiet
docker compose -f compose.yaml -f deploy/compose.public.yaml config --quiet
docker compose -f compose.yaml -f deploy/compose.local.yaml up -d --build --wait
python3 scripts/verify_compose.py
```

The acceptance script creates a random Compose project with fresh volumes and removes only that project's containers/volumes at the end. The normal local deployment and Python learning server are independent.

| Check | Result |
|---|---|
| Build application image; start non-root API with named data volume | Passed |
| Merge local and public Compose files | Passed |
| Caddy validate for local and public Caddyfiles | Passed |
| Public health /health, missing bearer token → 401 | Passed |
| Request over proxy's 1 MB limit → 413 (payload would otherwise fail application schema validation) | Passed |
| POST → 201, retry key returns same ID, GET → 200, ETag → 304 | Passed |
| PUT → 200, invalid boolean → 422, DELETE → 204, subsequent GET → 404 | Passed |
| API restart preserves a uniquely named record | Passed |
| SQLite live backup; export snapshot; integrity verification | Passed |
| Delete test record, stop API, import exported snapshot as API user, restore, restart | Passed; original record readable again |
| Run actual public Caddyfile with localhost's local CA | Passed |
| Export local CA; verify HTTPS hostname/chain using that CA, with no insecure TLS bypass | Passed |
| Repeat authenticated smoke checks over HTTPS | Passed |
| Configuration helper refuses to overwrite existing credentials | Passed |
| .env and .deploy-token ignored by Git and excluded from build context | Checked |

The full test ends with:

```text
PASS: health, auth, proxy body limit, create, retry, read, ETag, update, validation, delete
PASS: container CRUD, restart persistence, SQLite backup/export/restore, HTTP proxy, verified local HTTPS using public Caddyfile
```

The smoke script creates and deletes a test task. Its retry key remains in the retries table by the MVP's documented retention semantics; the disposable test removes its database afterward. Operator smoke runs against a real deployment will accumulate a small retry record per run until you implement a retention policy.

## Automated regression checks

`.github/workflows/deployment.yml` runs the same disposable acceptance script on an Ubuntu GitHub runner for pushes and pull requests. `.github/workflows/ci.yml` retains the ordinary API integration suite. Consult the [Actions page](https://github.com/THEJANAIDU/api-foundry/actions) for results against the exact commit you plan to deploy; a local pass is not a claim that every future CI run passes.

## Not executed here

No cloud server was provisioned, no domain DNS was changed, and no live public ACME certificate was issued. Ubuntu host package installation, external firewall routing, off-host backup transport, host reboot recovery and Windows execution were not tested on a target machine. Public DNS/ACME acceptance requires your domain and server; follow section 5 of [DEPLOYMENT.md](DEPLOYMENT.md) and record the external health/auth/smoke checks there.

This is a tested single-server reference, not a high-availability or load-capacity certification. OIDC login, multi-node storage, migrations, distributed quotas and monitoring still require product-specific implementation. Static tokens and the shared per-proxy rate bucket are explicitly documented limitations.
