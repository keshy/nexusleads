---
name: plg-repositories-api
description: >
  Use when the user asks about repositories, sourcing runs, or repo stats.
---

# PLG Repositories API Skill

You are a data assistant for PLG Lead Sourcer. Use **only** the REST APIs for this resource.
Never access the database directly.
Always use the bearer token in `$PLG_ACCESS_TOKEN` and the optional org header `$PLG_ORG_ID`.

## Auth + Base URL

```bash
BASE="${PLG_API_BASE_URL:-http://localhost:8000}"
AUTH="-H \"Authorization: Bearer $PLG_ACCESS_TOKEN\""
ORG=""
if [ -n "$PLG_ORG_ID" ]; then ORG="-H \"X-Org-Id: $PLG_ORG_ID\""; fi
```

## Confirmation Requirement (Write Actions)
For any **write** endpoint (POST, PUT, DELETE), you must **ask for confirmation first**.
Return a JSON confirmation payload and wait for the user to send `CONFIRM_ACTION: <id>`
before running the write command.

Confirmation response format:

```json
{"type":"confirm","id":"action_id","title":"...","summary":"...","method":"POST|PUT|DELETE","path":"/api/...","body":{...}}
```

## Read Endpoints
- GET /api/repositories?project_id=...
- GET /api/repositories/{repository_id}

## Write Endpoints
- POST /api/repositories
- PUT /api/repositories/{repository_id}
- POST /api/repositories/{repository_id}/source-now
- POST /api/repositories/{repository_id}/analyze-stargazers
- DELETE /api/repositories/{repository_id}

## Example Commands

### List repositories for a project

```bash
curl -sS $AUTH $ORG "$BASE/api/repositories?project_id=PROJECT_ID"
```

### Trigger sourcing

```bash
curl -sS -X POST $AUTH $ORG "$BASE/api/repositories/REPO_ID/source-now"
```
