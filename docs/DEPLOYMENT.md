# Deploy API Foundry: from a clone to an available API

This walkthrough takes you from local development to a persistent single-server deployment. It includes repeatable acceptance tests, HTTPS, credentials, DNS, backups, restore, updates and rollback. Start with the local container rehearsal before publishing anything.

## What has actually been tested

See [deployment verification](DEPLOYMENT_VERIFICATION.md) for the executed checks and environment. The repository's **Deployment acceptance** workflow repeats the disposable Docker rehearsal on Ubuntu. A local CA test exercises HTTPS using the actual public Caddyfile; it does not prove your domain's DNS or a public certificate authority will work. Those are verified on your server in step 5.

| Mode | Address | Who can reach it? | What must keep running? |
|---|---|---|---|
| Python learning launcher | http://127.0.0.1:8000 | This computer | Python process and computer |
| Local Docker rehearsal | http://127.0.0.1:8080 | This computer | Docker Engine/Desktop and containers |
| SSH tunnel | http://127.0.0.1:8080 on the connecting computer | Authorized SSH user | Server, containers and tunnel |
| Public server | https://YOUR_DOMAIN | Internet clients with valid API credentials for data routes | Server, Docker and containers |

GitHub stores the code and runs checks. It does not keep this Python application running. GitHub Pages and Cloudflare Pages static hosting alone cannot run this SQLite/FastAPI container.

## 1. Prerequisites and first local API

For Python development: Python 3.9+ (3.12 recommended), Git, a terminal, a browser and internet access for installation. On macOS install Python from [python.org](https://www.python.org/downloads/macos/) if needed. On Windows use `py` in place of `python3`.

```sh
git clone https://github.com/THEJANAIDU/api-foundry.git
cd api-foundry
python3 start.py
```

Open http://127.0.0.1:8000, paste the printed token and click Connect. Create a task, refresh, read it, toggle it, delete it. Expected statuses: 201, 200, 200, 200, 204. Read [the guided lesson](FIRST_API.md) before changing schemas or adding business rules. Ctrl+C stops the server; this is expected. Each clone has its own local database.

## 2. Rehearse the deployed architecture locally

Install and start [Docker Desktop](https://docs.docker.com/desktop/) on macOS/Windows, or Docker Engine with the Compose plugin on Linux. Python 3 and Git are still needed for helper commands. Windows users can run helper scripts with `py`. The container image supplies the API's Python environment.

```sh
docker version
docker compose version
python3 scripts/configure_deploy.py
docker compose -f compose.yaml -f deploy/compose.local.yaml config --quiet
docker compose -f compose.yaml -f deploy/compose.local.yaml up -d --build --wait
python3 scripts/smoke_deploy.py
```

Expected: healthy API/gateway services, then `PASS: health, auth, proxy body limit, create, retry, read, ETag, update, validation, delete`. Open http://127.0.0.1:8080. Read `.deploy-token` privately in your editor and paste it into Connect (or use `/docs` → Authorize). The helper creates `.env` and `.deploy-token` with restrictive permissions on POSIX systems; review file ACLs on Windows. Both are ignored by Git and Docker's build context. Never publish them.

The deployment subject is `deployment-owner`; the learning launcher uses `local-learner`. These modes intentionally have different data and credentials. `configure_deploy.py` refuses to overwrite existing credentials. The deployment token stays stable until you rotate it.

```sh
# Run the full automated rehearsal in its own random project and fresh volumes.
python3 scripts/verify_compose.py
```

This checks CRUD/auth, restart persistence, backup/export/restore, HTTP routing, public configuration validation, and verified local HTTPS. It uses ports 18080 and 18443. Set `VERIFY_PORT` and `TLS_TEST_PORT` to other free ports if needed. It deletes only its own random test project's volumes in cleanup. Do not replace its project name with a production project.

The normal rehearsal runs detached: closing the terminal does not stop the containers. Restart policies recover containers after a crash or Docker restart. On a Mac, Docker Desktop and the Mac must remain awake/running. Health checks report failure; an unhealthy but running process is not automatically restarted by Docker.

```sh
# Observe, stop, restart; data is retained.
docker compose -f compose.yaml -f deploy/compose.local.yaml ps
docker compose -f compose.yaml -f deploy/compose.local.yaml logs --tail=100
docker compose -f compose.yaml -f deploy/compose.local.yaml down
docker compose -f compose.yaml -f deploy/compose.local.yaml up -d --wait
```

Do not add `--volumes` to your real deployment's down command: that removes the persistent database and certificate volumes. If 8080 is occupied, put `LOCAL_PORT=8081` in `.env` and use `--url http://127.0.0.1:8081` with the smoke script.

## 3. Make it available to one other computer

For a private demonstration, keep the local Docker configuration on a machine that already accepts SSH connections. On the connecting computer:

```sh
ssh -N -L 8080:127.0.0.1:8080 YOUR_USER@YOUR_SERVER
```

Open http://127.0.0.1:8080 on that connecting computer. The traffic crosses the network inside SSH. Obtain the deployment token from the owner through your normal private credential-sharing process. The tunnel must stay open. This needs an existing authorized SSH account and reachable SSH service; enabling remote login is outside this command. Do not port-forward raw HTTP from your home router as a substitute for HTTPS.

## 4. Prepare a public server and domain

Target: a fresh Ubuntu 24.04 LTS server with a persistent disk, SSH access, Python 3, Git and Docker Engine/Compose. A small VM with roughly 1–2 GB RAM is a starting point to measure, not a capacity guarantee. Use your chosen hosting account; server/domain fees depend on the provider. This guide does not create or purchase infrastructure.

1. Provision the server and retain its public IP. Use SSH keys and your provider's supported administrator account.
2. In the provider's network firewall allow TCP 80/443 publicly and TCP 22 only from your administration IP/range. Do not expose 8000, 8080, 18080, 18443 or the database. Docker-published ports can bypass UFW rules; use the provider firewall as well. Only Caddy publishes ports in the public configuration.
3. Create an A record for a subdomain such as `api.yourdomain.com` pointing to the server IPv4 address. Create an AAAA record only when IPv6 is correctly configured/reachable. Remove stale AAAA records. Initially use a direct DNS record rather than another CDN proxy to simplify certificate troubleshooting.
4. Install Docker Engine/Compose using [Docker's Ubuntu installation instructions](https://docs.docker.com/engine/install/ubuntu/), which cover supported OS versions, repository setup, package conflicts and service startup. This OS provisioning procedure is an external prerequisite, not part of the executed local test. Install `git`, `python3` and `curl` from Ubuntu's package manager if missing.
5. Verify `sudo docker version` and `sudo docker compose version`. For the commands below use `sudo docker` wherever `docker` appears if your authorized admin account requires it. Docker control is privileged; follow your host's access policy instead of granting broad access just to omit sudo.

On the server, clone into a persistent directory owned by your deployment administrator:

```sh
git clone https://github.com/THEJANAIDU/api-foundry.git
cd api-foundry
python3 scripts/configure_deploy.py --domain api.yourdomain.com
```

Replace `api.yourdomain.com` with your real DNS hostname, without a scheme or path. `.env` must remain in the repository root; it contains `API_DOMAIN` and `API_TOKENS`. `.deploy-token` holds the same secret for operator smoke tests. Never put either in a public web directory or repository. If you copied an existing local `.env`, edit only API_DOMAIN and preserve tokens; do not rerun the refusing configuration helper.

## 5. Start public HTTPS and verify it from outside

The following Bash function abbreviates the exact public Compose files. Define it again whenever you open a new shell in the repository root:

```sh
deploy() { docker compose -f compose.yaml -f deploy/compose.public.yaml "$@"; }
deploy config --quiet
deploy up -d --build --wait
deploy ps
deploy logs --tail=100 gateway api
curl --fail --show-error https://api.yourdomain.com/health
python3 scripts/smoke_deploy.py --url https://api.yourdomain.com
```

Expected health body: `{"status":"ok"}`; expected smoke result: PASS. Caddy obtains/renews the public certificate automatically when DNS and inbound 80/443 are correct, and redirects HTTP to HTTPS. Do not use `curl -k` or disable TLS verification to declare success. `--wait` checks container health; it does not by itself confirm DNS, public reachability or certificate issuance.

From a second computer/network (for example a laptop on mobile tethering), repeat:

```sh
curl --fail --show-error https://api.yourdomain.com/health
curl -i https://api.yourdomain.com/v1/tasks
```

Expected: health 200, unauthenticated tasks 401. Open the HTTPS site and use a privately provided token to create/read/delete a task. Record the date, commit (`git rev-parse HEAD`), hostname and smoke result in your deployment log. Do not record credentials. Until these external checks pass, the public deployment has not been accepted.

This is a single-node deployment for controlled use. Static bearer credentials are not a complete public user-login system. Before a multi-user product, add OIDC identity, appropriate scopes/ownership, distributed quotas and production monitoring. The proxy limits requests to 1 MB and provides gzip/TLS, but it is not an API gateway or WAF. Requests share the proxy IP in the MVP rate limiter (120/minute across that instance); do not blindly trust forwarded IP headers to change that behavior. There is one API worker and SQLite volume; do not scale replicas against this file.

## 6. Persistence, backups and a restore drill

The `api_data` named volume holds `/data/foundry.db`; Caddy has separate certificate/config volumes. Rebuilding containers does not remove them. Changing the Compose project name changes which volumes you use: keep the same directory/project name between updates.

Run these on the server from the repository root, with the `deploy` function defined as above:

```sh
mkdir -p backups
chmod 700 backups
SNAPSHOT="foundry-$(date -u +%Y%m%dT%H%M%SZ).sqlite3"
deploy exec -T api python scripts/manage_db.py backup "/data/$SNAPSHOT"
deploy exec -T api cat "/data/$SNAPSHOT" > "backups/$SNAPSHOT"
python3 scripts/manage_db.py check "backups/$SNAPSHOT"
chmod 600 "backups/$SNAPSHOT"
```

The helper uses SQLite's backup API for a consistent live snapshot and verifies integrity. It includes records and retry keys, not the `.env` identity configuration or TLS certificates. Back up the secret configuration separately to your approved encrypted secret store; restoring records without the same subject mapping can make them appear inaccessible. Copy database snapshots to encrypted off-host storage on a schedule, apply retention, and test recovery. A backup on the same disk is only a staging copy, not disaster recovery. Old snapshots also occupy volume space; remove expired copies according to your retention policy.

First run the automated disposable restore test. For a real restore, announce a maintenance window, take a fresh backup, and ensure every process using the database is stopped. Restore intentionally replaces data:

```sh
# Use an actual verified backup filename, not the placeholder below.
SNAPSHOT="foundry-YYYYMMDDTHHMMSSZ.sqlite3"
python3 scripts/manage_db.py check "backups/$SNAPSHOT"
deploy stop api
# Import as the API user so file ownership is correct. Do not start a second server.
deploy run --rm -T --no-deps api python -c "import os,sys; from pathlib import Path; p=Path('/data/restore.sqlite3'); p.write_bytes(sys.stdin.buffer.read()); os.chmod(p,0o600)" < "backups/$SNAPSHOT"
deploy run --rm --no-deps api python scripts/manage_db.py restore /data/restore.sqlite3 --replace
deploy up -d --wait
python3 scripts/smoke_deploy.py --url https://api.yourdomain.com
```

For a fresh disaster-recovery server, configure the same subject mapping, run `deploy create --build api` to initialize its container/volume, then import and restore the snapshot before bringing services up. Restore refuses leftover SQLite journal/WAL sidecars; investigate/recover those with SQLite first rather than deleting files blindly. Confirm a known pre-backup record is readable after restore. The smoke script creates/deletes its own record and cannot prove your business data was restored.

## 7. Update and roll back without losing data

```sh
PREVIOUS_COMMIT="$(git rev-parse HEAD)"
# Take/export a snapshot with section 6 before updating.
git pull --ff-only
# Review CHANGELOG, dependencies and any schema changes before starting.
deploy up -d --build --wait
python3 scripts/smoke_deploy.py --url https://api.yourdomain.com
```

Keep PREVIOUS_COMMIT in your private deployment log. The generic resources have no automatic migration engine. Adding required fields or changing stored meanings needs an explicit migration plan, backup, test and rollback strategy; changing resources.json alone does not migrate old data.

For a code-only rollback compatible with the existing database:

```sh
git switch --detach "$PREVIOUS_COMMIT"
deploy up -d --build --wait
python3 scripts/smoke_deploy.py --url https://api.yourdomain.com
```

For an incompatible data migration, restore the matching snapshot during a maintenance window as well. Do not pull while detached; return to `main` before the next planned release. Image/dependency tags may change upstream; capture image IDs/digests and lock transitive dependencies before requiring byte-for-byte reproducible production releases.

## 8. Rotate credentials and operate the service

Create a new random token with `python3 -c 'import secrets; print(secrets.token_urlsafe(32))'`. Privately edit the single-quoted JSON value in `.env` so API_TOKENS temporarily contains both old and new tokens mapped to the same subject/scopes. Run `deploy up -d --force-recreate api`. Update clients and `.deploy-token` privately, verify the smoke test with the new credential, remove the old entry, and recreate the API again. Confirm the retired token receives 401. Keep the subject unchanged to retain access to existing records. The deployment helper deliberately does not overwrite or rotate credentials for you.

Configure an external HTTPS /health monitor, alerts for sustained errors/unhealthy containers and disk space, and scheduled off-host backups. Docker log rotation is configured for API logs; avoid writing credentials/bodies into logs. Review and install OS/container/dependency updates routinely. A health response is not an uptime SLA. Keep one API worker until storage/concurrency and quotas are redesigned.

| Failure | Check |
|---|---|
| Docker daemon unavailable | Start Docker Desktop locally; check `systemctl status docker` on Linux. |
| Missing .env or API_TOKENS | Run configuration once from the root; preserve existing secrets. |
| Port already in use | Stop the conflicting service or change LOCAL_PORT for the local rehearsal. |
| Container cannot write /data | Use the named volume; check UID/permissions if you substituted a host bind mount. |
| Public TLS not issued | Check A/AAAA records, open inbound 80/443, gateway logs, DNS proxy mode and certificate authority rate limits. |
| 502 from Caddy | Check API health, API logs and Docker network; API should not need a published host port. |
| 401 or missing data | Check token, scopes, subject mapping and selected Compose project/database volume. |
| 429 | Wait 60 seconds; the MVP rate bucket is shared behind the proxy. |
| Data disappears after rebuild | Check whether you changed the project name, mounted another volume or used down --volumes. |

References: [Docker Compose volumes](https://docs.docker.com/reference/compose-file/volumes/), [Docker Ubuntu installation/firewalls](https://docs.docker.com/engine/install/ubuntu/), [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https), [Caddy body-size limits](https://caddyserver.com/docs/caddyfile/directives/request_body).
