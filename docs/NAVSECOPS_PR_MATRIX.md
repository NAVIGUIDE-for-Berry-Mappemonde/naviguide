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
