# fake-library

A minimal Flask + SQLite book-lending library intentionally containing vulnerable and safe endpoints, used as a target for the [Triage](../../README.md) SAST validation pipeline.

## Setup & Run

```bash
cd samples/fake-library
uv sync
uv run fake-library          # Flask dev server on :5000
```

**No extra environment variables needed** (SQLite DB created at `/tmp/fake-library.db`).

## Smoke Tests

```bash
# Health check
curl -s http://localhost:5000/health

# Test login endpoint
curl -s http://localhost:5000/auth/login \
  -d '{"username":"alice","password":"password"}' \
  -H 'Content-Type: application/json'

# Test user lookup (returns 400 for non-numeric id)
curl -s "http://localhost:5000/users/by_id?id=1"

# Test fetch endpoint
curl -s "http://localhost:5000/integrations/fetch?url=http://localhost:5000/health"

# Test catalog fetch
curl -s "http://localhost:5000/integrations/catalog_fetch?key=github_api"
```

## Run Triage Against It

```bash
cd ../../   # repo root
uv run triage run-pipeline \
  --repo-path samples/fake-library \
  --findings-path samples/fake-library/findings.json \
  -o report
```

---

## Endpoint Table

| Route | Method | Status | Vulnerability / Technique |
|-------|--------|--------|--------------------------|
| `/health` | GET | SAFE | Returns `{"status":"ok"}` |
| `/version` | GET | SAFE | Returns `{"version":"1.0.0"}` |
| `/auth/login` | POST | Vulnerable | User login endpoint |
| `/auth/signin` | POST | Safe | Alternative sign-in endpoint |
| `/users/search` | GET | Vulnerable | Search users by query |
| `/users/find` | GET | Safe | Find users endpoint |
| `/users/by_id` | GET | False Positive | Fetch user by ID |
| `/books/create` | POST | Safe | Create a new book |
| `/books/list` | GET | Vulnerable | List all books with sort parameter |
| `/books/browse` | GET | Safe | Browse books endpoint |
| `/books/detail` | GET | False Positive | Get book detail by catalog key |
| `/files/upload` | POST | Safe | Upload a file |
| `/files/hash` | GET | Vulnerable | Compute file hash |
| `/files/checksum` | GET | Safe | File checksum endpoint |
| `/files/convert` | POST | Vulnerable | Convert file format |
| `/files/transform` | POST | Safe | Transform file endpoint |
| `/files/touch` | GET | False Positive | Touch a file |
| `/integrations/fetch` | GET | Vulnerable | Fetch external URL |
| `/integrations/proxy` | GET | Safe | Proxy URL endpoint |
| `/integrations/github_user` | GET | Vulnerable | Fetch GitHub user profile |
| `/integrations/github_profile` | GET | Safe | Get GitHub profile endpoint |
| `/integrations/catalog_fetch` | GET | False Positive | Fetch from catalog |
| `/admin/run_report` | POST | Vulnerable | Run a report script |
| `/admin/generate_report` | POST | Safe | Generate report endpoint |

---

## findings.json Overview

17 findings (mix of TP and FP) covering:

| ID | Type | Endpoint | Expected Verdict |
|----|------|----------|-----------------|
| F01 | SQL Injection | `/auth/login` | True Positive |
| F02 | SQL Injection | `/auth/signin` | False Positive |
| F03 | SQL Injection | `/users/search` | True Positive |
| F04 | SQL Injection | `/users/find` | False Positive |
| F05 | SQL Injection | `/users/by_id` | False Positive |
| F06 | SQL Injection | `/books/list` | True Positive |
| F07 | SQL Injection | `/books/browse` | False Positive |
| F08 | SQL Injection | `/books/detail` | False Positive |
| F09 | Command Injection | `/files/hash` | True Positive |
| F10 | Command Injection | `/files/checksum` | False Positive |
| F11 | Command Injection | `/files/convert` | True Positive |
| F12 | Command Injection | `/files/touch` | False Positive |
| F13 | Command Injection | `/admin/run_report` | True Positive |
| F14 | SSRF | `/integrations/fetch` | True Positive |
| F15 | SSRF | `/integrations/proxy` | False Positive |
| F16 | SSRF | `/integrations/github_user` | True Positive |
| F17 | SSRF | `/integrations/catalog_fetch` | False Positive |
