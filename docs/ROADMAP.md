# Roadmap: implemented versus extension work

The roadmap is a learning path. This scaffold implements a useful REST slice; it does not claim every protocol is running.

| Roadmap | Working MVP | Next exercise / production extension |
|---|---|---|
| 01 Foundations | HTTP methods/status/headers, JSON, stateless credentials, OpenAPI contract | Compare RPC command endpoints and GraphQL queries; implement Accept negotiation |
| 02 REST | Plural resource URLs, safe reads, replace/delete semantics, filter/sort/offset pagination, navigation links, Problem Details | Rich hypermedia relations, cursor pagination, optimistic writes |
| 03 Specs/docs | Generated OpenAPI, Swagger UI, ReDoc, request schemas and examples in README | Explicit response schemas, SDK generation, mock server, schema-first review |
| 04 Auth | Opaque bearer credentials, read/write scopes, subject ownership | OIDC/OAuth authorization code + PKCE, JWT verification, service mTLS |
| 05 Evolution | `/v1` namespace | Deprecation/Sunset headers, release policy, OpenAPI diff, consumer contracts |
| 06 Protection | Local rate limiting/429, ETag/304, persistent create retry keys | Gateway quotas, gzip, body limits, distributed retry policy, atomic bulk endpoints |
| 07 GraphQL | Not implemented | Add a separate schema/resolver layer using the same services; DataLoader, cost/depth budgets; federation only when needed |
| 08 gRPC/realtime | Not implemented | Protobuf service + generated stubs; SSE/WebSocket auth and backpressure; tRPC only for a TypeScript stack |
| 09 Webhooks/async | Not implemented | Transactional outbox, signed events, durable retries, AsyncAPI and 202/polling jobs |
| 10 Security | Owner-scoped SQL, strict fields, scopes, parameterized values, secrets outside Git, CORS disabled | OWASP API review, secret manager, request limits, OIDC, audit trails |
| 11 Tests/observability | Integration/security tests, OpenAPI smoke test, request IDs, log instrumentation, GitHub CI config | Consumer contracts, Bruno collection, load tests, tracing, dashboards/SLO alerts |
| 12 Platform/scale | Generator, beginner UI, guided lesson, one-command launcher, docs, container and template-ready layout | Gateway/BFF when needed; billing ledger and durable quotas; partner onboarding |

## Evolution policy to adopt

Add optional fields before requiring them; preserve existing meanings and status codes. Require a new major URL version for removed fields or incompatible semantics. Publish dated changelogs, give consumers an announced migration window, and monitor old-version usage before sunset. The repository currently has only v1 and no scheduled retirement.

## Learning sequence

1. Run the tasks demo and observe headers with `curl -i`.
2. Generate books and exercise ownership with two credentials.
3. Read the generated contract and add an explicit response model.
4. Build a client, add a meaningful business rule, and test it.
5. Add a database migration and contract-diff CI gate.
6. Choose one advanced protocol only when your use case requires it.
