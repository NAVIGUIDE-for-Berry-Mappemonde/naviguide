# Matrice PR Shreyas <-> cible NavSecOps

Branche locale suivie : `pr-shreyas` (remote `origin`). Le commit `50c33130` (" Resolved merge conflict ") a laisse des marqueurs de conflit dans les sources et un `naviguide-api/venv/` versionne.

| Zone | Etat dans la PR / branche | Cible NavSecOps | Action |
|------|---------------------------|-----------------|--------|
| LLM | Conflit HEAD (Gemini) vs `f4d5b955` (Nova + Claude Bedrock) dans `llm_utils.py` | Gemini pour analyse GeoJSON (`/duo/validate`, `/duo/risk`) ; Claude (API Anthropic) pour synthese (`/duo/briefing`, orchestrateur, agents streaming) | Fusion unique dans `naviguide_workspace/llm_utils.py` ; abandon Nova sur ces chemins |
| API | Pas de routes `/duo/*` | Exposer `/duo/validate`, `/duo/risk`, `/duo/briefing` sur `naviguide-api` | Ajouter router Duo |
| Dependances | Conflit dans `naviguide_workspace/requirements.txt` | `google-genai` + `anthropic` (+ option Secret Manager GCP) | Resoudre le fichier |
| venv | `naviguide-api/venv/` tracke, fichiers corrompus | Aucun venv dans Git ; `.gitignore` | `git rm -r --cached naviguide-api/venv` |
| Doc | `README.md` en conflit | Sections Google (Gemini/GCP) + Anthropic (Claude), NavSecOps | Fusion README |
| Orchestrateur | `invoke_llm` casse tant que conflit persiste | Briefing executif via Claude | Inchange cote appel ; implementation stable |

**Mise a jour implementation (post-fix) :** `llm_utils.py` unifie, routes `/duo/*` dans `naviguide-api`, `venv` retire de l'index Git, `README.md` sans conflits, script `scripts/gitlab_navsecops_chain.sh` pour la chaine locale.

---

## Phase 1 — `POST /api/v1/navsecops/analyze`

Single-pass endpoint that chains `validate` (Gemini) -> `risk` (Gemini) -> `briefing` (Claude) server-side and returns a unified JSON response.

### Authentication

```
Authorization: Bearer <NAVSECOPS_INGEST_SECRET>
```

The secret is read from the `NAVSECOPS_INGEST_SECRET` environment variable. Returns `401` if the token is missing or wrong, `500` if the env var is not configured.

### Request

```json
POST /api/v1/navsecops/analyze
Content-Type: application/json

{
  "geojson": {
    "type": "Feature",
    "properties": { "name": "test-leg" },
    "geometry": {
      "type": "LineString",
      "coordinates": [[-1.15, 46.15], [-4.5, 48.4], [-5.0, 36.0]]
    }
  },
  "language": "fr"
}
```

### Response

```json
{
  "status": "complete | partial | failed",
  "validation": { "valid": true, "..." : "..." },
  "risk": { "overall_risk": "MODERATE", "..." : "..." },
  "briefing": "## EXECUTIVE SUMMARY\n...",
  "errors": [],
  "meta": {
    "request_id": "uuid",
    "duration_ms": 8420,
    "models": ["gemini-2.0-flash", "claude-sonnet-4-20250514"],
    "stages_ok": 3,
    "stages_failed": 0
  }
}
```

**`status` semantics:**
- `complete` — all 3 stages succeeded.
- `partial` — validate succeeded but risk and/or briefing failed. Fields may be `null`.
- `failed` — validate itself failed. `risk` and `briefing` are `null`.

### curl example (recommended timeout: 90s)

```bash
curl -s -X POST http://127.0.0.1:8001/api/v1/navsecops/analyze \
  -H "Authorization: Bearer $NAVSECOPS_INGEST_SECRET" \
  -H "Content-Type: application/json" \
  --max-time 90 \
  -d '{
    "geojson": {
      "type": "Feature",
      "properties": {"name": "test-leg"},
      "geometry": {
        "type": "LineString",
        "coordinates": [[-1.15,46.15],[-4.5,48.4],[-5.0,36.0]]
      }
    },
    "language": "fr"
  }' | python3 -m json.tool
```

### Error codes

| HTTP | Meaning |
|------|---------|
| 200  | Analysis completed (check `status` for partial/failed) |
| 401  | Missing or invalid Bearer token |
| 422  | Invalid request body (Pydantic validation) |
| 500  | `NAVSECOPS_INGEST_SECRET` not configured on server |

### Risks noted (out of scope for Phase 1)

- **Cloud Run + SQLite:** ephemeral disk means SQLite storage (Phase 3) won't persist across revisions/scale-to-zero. Acceptable for hackathon demo (read-after-write in same instance). Production options: Cloud SQL, Firestore, or Cloud Storage FUSE mount.
- **LLM timeouts:** Gemini + Claude combined can take 30-60s. CI jobs calling this endpoint should use `--max-time 90` and `allow_failure: false` only for technical errors (Decision 3).

---

## Phase 3 — Persist reports (`sync-report`, `GET /reports`)

SQLite file: `naviguide-api/var/navsecops.db` (gitignored). Rows are upserted on `(project_id, merge_request_iid, source_commit_sha)`.

### Authentication

Same as Phase 1: `Authorization: Bearer <NAVSECOPS_INGEST_SECRET>` on all Phase 3 routes below.

### `POST /api/v1/navsecops/sync-report`

**Request body (JSON):**

| Field | Type | Required |
|-------|------|----------|
| `project_id` | integer | yes |
| `merge_request_iid` | integer | yes |
| `source_commit_sha` | string (7–64 chars) | yes |
| `route_file` | string | yes |
| `report_markdown` | string | yes |
| `raw_analysis` | object (JSON) | no — full `analyze` response when available |

**Response (200):** `{ "id": <int>, "project_id", "merge_request_iid", "source_commit_sha", "status": "stored" }`

**curl (direct API, port 8001):**

```bash
curl -sS -X POST "http://127.0.0.1:8001/api/v1/navsecops/sync-report" \
  -H "Authorization: Bearer $NAVSECOPS_INGEST_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 35535537,
    "merge_request_iid": 1,
    "source_commit_sha": "abcdef1234567890abcdef1234567890abcd",
    "route_file": "routes/naviguide-berry-mappemonde.geojson",
    "report_markdown": "## NavSecOps\n\nBriefing text…",
    "raw_analysis": {"status": "complete", "validation": {}}
  }' | python3 -m json.tool
```

| HTTP | Meaning |
|------|---------|
| 200 | Row inserted or updated |
| 401 | Invalid Bearer |
| 422 | Validation error |
| 500 | Secret not configured, or DB error |

### `GET /api/v1/navsecops/reports`

Query parameters: `project_id` (optional), `limit` (1–200, default 50), `offset` (default 0).

**Response:** `{ "items": [ { "id", "project_id", "merge_request_iid", "source_commit_sha", "route_file", "report_markdown", "created_at", "updated_at" } ], "limit", "offset" }`

No secrets are returned in the JSON.

```bash
curl -sS "http://127.0.0.1:8001/api/v1/navsecops/reports?limit=10" \
  -H "Authorization: Bearer $NAVSECOPS_INGEST_SECRET" | python3 -m json.tool
```

### `GET /api/v1/navsecops/reports/{report_id}`

Returns one report including `raw_analysis` as parsed JSON when stored.

| HTTP | Meaning |
|------|---------|
| 200 | Body is the report object |
| 401 | Invalid Bearer |
| 404 | Unknown id |

### GitLab CI — optional sync

After the MR note is posted, `scripts/gitlab_mr_navsecops.sh` calls `sync-report` **only** when `NAVSECOPS_SYNC_ENABLED=1` (string). If unset or not `1`, behavior is unchanged from Phase 2A.

Requires the same `NAVSECOPS_BASE_URL` and `NAVSECOPS_INGEST_SECRET` as analyze. On failure (non-2xx), the job **exits 1** when sync is enabled.

Artifact `navsecops-sync-response.json` is collected when present (placeholder file created in CI so the path always exists).

---

## Phase 4 — Unified proxy (`proxy_server.py`)

When the proxy runs (default `PORT=3014`), these prefixes forward to **naviguide-api** (`API_BACKEND`, default `http://localhost:8001`) **before** the orchestrator catch-all:

- `/api/v1/navsecops/*`
- `/duo/*`

### curl via proxy (reports list)

```bash
curl -sS "http://127.0.0.1:3014/api/v1/navsecops/reports?limit=5" \
  -H "Authorization: Bearer $NAVSECOPS_INGEST_SECRET" | python3 -m json.tool
```

Replace host/port if `PORT` or deployment URL differs.
