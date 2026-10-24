# Troubleshooting

| Symptom | What to do |
|---|---|
| python3 is not found | Install Python from python.org, reopen your terminal; on Windows try `py start.py`. |
| Can't open start.py | Open a terminal in the extracted/cloned api-foundry folder. `start.py` must be visible there. |
| pip download/SSL error | Check internet access and your organization's proxy/certificate configuration. Do not disable certificate verification. Retry the launcher. |
| venv/ensurepip missing | Install your OS's Python venv package or use an official Python distribution. |
| Address already in use | Stop the other local server on port 8000, then rerun. |
| 401 Unauthorized | Copy the current launcher's token, without quotes or the word Bearer. Restarting changes it. In /docs click Authorize. |
| 403 Forbidden | The authenticated token lacks read or write scope. Check your manual API_TOKENS configuration. |
| 404 for another user's record | Ownership is enforced. Use the creating identity, or check that the ID still exists. |
| 422 validation error | Compare the request to /docs; use actual boolean/numeric values and only declared fields. |
| 429 Too Many Requests | Wait 60 seconds. The teaching limiter allows 120 requests per IP per minute, including docs requests. |
| New resource doesn't appear | Stop and restart the server after generating it. Reconnect with the new token. |
| Page is empty after creating | Click Refresh list. This preserves the POST response in the inspector until you choose the next request. |
| Tests can't import app | Run tests from the project root with `.venv/bin/python -m pytest -q`. |
| Need a fresh database | Stop the server and move foundry.db to a backup filename, then restart. The new database starts empty. |

The launcher binds only to 127.0.0.1, uses a temporary random token and keeps the same local subject between runs. It overrides API_TOKENS for its child server. For multiple identities or deployment, use the manual startup in README. Do not expose the teaching launcher on a public interface.
