# How it is built and how to extend it

## Request flow

Client → request-ID/rate middleware → bearer token lookup → scope check → Pydantic validation → owner-scoped SQLite operation → JSON response.

`create_app()` creates an isolated application and database connection. It reads `resources.json`, creates a strict input model for each resource, and registers five routes. FastAPI derives interactive documentation and OpenAPI from those models. This is code-first: changing the resource configuration changes both routes and the contract at startup.

SQLite has `records(resource,id,owner,body)` and `retries(owner,resource,key,digest,body)`. SQL values are parameterized. Every item lookup is constrained by owner; another owner's ID yields 404. Read and write scopes are independent; create a read-only credential by granting only `read`. Tokens represent API clients, and clients with the same subject deliberately share records.

A creation and its idempotency record commit together. Retry keys are scoped to subject and resource; they persist indefinitely in this MVP. Replaying after deletion returns the original creation representation, not a newly created item. Define a retention policy and run cleanup before large deployments.

The application serializes requests within each process to protect the shared SQLite connection and transactions. This favors understandable local behavior over throughput. Use a connection pool, migrations, PostgreSQL, and distributed locks/constraints when scaling. Run only one worker for this MVP: rate buckets are in memory and are not shared across workers. For large collections replace the in-memory filtering and counting with indexed SQL queries and cursor pagination.

## Add rules

Add Pydantic constraints to generated models or define a dedicated model and route for richer resources. Add a service layer for business logic before growing the route handlers. Add explicit output models to stabilize client SDK types: current response bodies are runtime JSON and OpenAPI does not fully describe their response envelopes. Introduce migrations when fields or storage semantics evolve; old persisted JSON is not automatically migrated by editing resource definitions.

## Authentication evolution

The MVP uses opaque bearer API credentials from environment configuration, constant-time comparison, subject ownership, and scopes. It does not issue JWTs or implement OAuth. For production use an OIDC provider, verify issuer/audience/signature/expiry with maintained libraries, and map validated claims to the same subject/scope interface. Rotate static keys by briefly configuring old and new tokens for the same subject, then remove the old token. Restart after configuration changes.

CORS is disabled by default. Prefer same-origin clients. If a browser frontend runs on a separate origin, add CORSMiddleware with an exact allowlist; configure only the necessary methods/headers. Avoid wildcard credential policies.

## Deployment checklist

Terminate TLS at a reverse proxy. Enforce body-size and timeout limits there (the MVP only limits strings on POST, not full request size). Apply a distributed quota/rate limiter; the built-in bucket is per IP, per process, has no eviction, and may aggregate all users behind a proxy. Do not trust forwarded IP headers without configuring trusted proxies.

Provision backups, restore drills, a secret manager, non-root containers, dependency scanning, database migrations, and production error monitoring. Emit structured logs through your logging configuration; the middleware records path/status/duration/request ID without authorization headers or bodies. Add OpenTelemetry and external health checks for traces and uptime. Define SLOs from observed traffic, for example 99.9% successful valid requests over 30 days, with explicit exclusions.

The MVP has no distributed concurrency control, optimistic write preconditions, webhook worker, query federation, billing, or production identity provider. ETags support exact conditional reads only; If-Match, weak/list ETag parsing and content negotiation beyond normal JSON behavior are extension work.

## Suggested next builds

- Inventory: books/products resources plus stock transaction rules.
- Support: tickets plus dedicated assignment, status transition, and comment services.
- Job runner: jobs with 202 Accepted and polling URLs; add a queue and worker.
- Integrations: outbox events, durable webhook delivery, exponential backoff, HMAC timestamp verification, replay windows, and dead-letter handling. Restrict destinations to prevent SSRF.

## Standards

Errors use the core Problem Details fields with `application/problem+json`: https://www.rfc-editor.org/rfc/rfc9457.html . Validation adds an `errors` extension without echoing the submitted body. Interactive contracts use OpenAPI: https://spec.openapis.org/oas/v3.1.html . Pin and review dependency upgrades before adopting them.
