---
name: verifying-apis
description: Verifies API behavior by comparing a target API against a source API or a defined contract. Use when migrating backends, switching providers, or regression testing endpoints.
---

# API Verification Skill

You are verifying that a Target API behaves identically to a Source API (or meets a defined contract). Use this when switching API providers, migrating backends, or performing regression tests.

## When to use this skill
- Switching email providers (e.g., SendGrid → Resend)
- Migrating payment providers (e.g., Stripe → Paddle)
- Testing a refactored backend before flipping production traffic
- Webhook verification after changing endpoints

## Workflow

### 1. Create a Verification Manifest
Create a `verification_manifest.json` file defining the endpoints to test. See [examples/verification_manifest.json](examples/verification_manifest.json).

```json
[
  {
    "name": "Get User",
    "endpoint": "/api/users/1",
    "method": "GET",
    "headers": { "Authorization": "Bearer {{TOKEN}}" },
    "expected_status": 200,
    "expected_body_contains": ["id", "email"]
  }
]
```

### 2. Run the Verification Script
```bash
python3 .agent/skills/verifying-apis/scripts/verify_api_parity.py \
  --source "https://old-api.example.com" \
  --target "https://new-api.example.com" \
  --manifest ./verification_manifest.json
```

**Options:**
- `--source`: Base URL of the original API (optional if only testing against expected values)
- `--target`: Base URL of the new API (required)
- `--manifest`: Path to the JSON manifest file
- `--env-file`: Optional `.env` file for variable substitution (e.g., `{{TOKEN}}`)

### 3. Analyze Results
The script outputs a markdown summary:
- ✅ **PASS**: Status code and body match expectations
- ⚠️ **DIFF**: Response differs between source and target
- ❌ **FAIL**: Request failed or status code mismatch

## Manifest Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Human-readable test name |
| `endpoint` | string | ✅ | API path (appended to base URL) |
| `method` | string | ✅ | HTTP method (GET, POST, PUT, DELETE, PATCH) |
| `headers` | object | ❌ | Request headers (supports `{{VAR}}` substitution) |
| `body` | object | ❌ | Request body for POST/PUT/PATCH |
| `expected_status` | number | ❌ | Expected HTTP status code |
| `expected_body_contains` | array | ❌ | Keys that must exist in response body |

## Resources
- [verify_api_parity.py](scripts/verify_api_parity.py) - Main verification script
- [verification_manifest.json](examples/verification_manifest.json) - Example manifest
