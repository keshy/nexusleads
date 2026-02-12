---
name: plg-users-api
description: >
  Use when the user asks about user management or profile updates.
---

# PLG Users API Skill

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
- GET /api/users
- GET /api/users/me

## Write Endpoints
- POST /api/users
- PUT /api/users/me
- DELETE /api/users/{user_id}

## Example Commands

### Get my profile

```bash
curl -sS $AUTH "$BASE/api/users/me"
```

### Create user

```bash
curl -sS -X POST $AUTH -H "Content-Type: application/json"   -d "{\"username\":\"newuser\",\"email\":\"new@org.com\",\"password\":\"...\"}"   "$BASE/api/users"
```
