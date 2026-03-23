# NAVIGUIDE

Decision-support assistant for maritime navigation (**Berry-Mappemonde** project). This repository contains the **FastAPI** API (`naviguide-api`), the shared LLM code (`naviguide_workspace`), the React frontend (`naviguide-app`), and the **NavSecOps** pipeline (GeoJSON analysis: Gemini + Claude synthesis).

---

## Scope: Docker image vs full stack

| Mode | Contents | Usage |
|------|----------|-------|
| **Docker image** ([Dockerfile](Dockerfile) at root) | Copies only `naviguide_workspace` + `naviguide-api`, runs `uvicorn main:app` | Cloud Run, isolated API testing |
| **Full local stack** | React, proxy, supervisord, multiple services | Integrated development — see [docs/MANUAL.md](docs/MANUAL.md) |

The Docker image does **not** start the frontend or supervisord. The listening port is **`PORT`** (typically **8080** locally, set by Cloud Run in production).

---

## Prerequisites

- **Python 3.12** (aligned with the Dockerfile)
- **Docker** to build / run the API
- On **Mac Apple Silicon**: to push an image to **Cloud Run (linux/amd64)**, use **`docker buildx`** with `--platform linux/amd64` (the classic builder may produce an **arm64** image incompatible with GCP → `exec format error`). Install the **buildx** plugin if `docker buildx` is unknown (`brew install docker-buildx` + symlink in `~/.docker/cli-plugins`).

---

## Configuration

1. Copy the template: `cp naviguide-api/.env.example naviguide-api/.env`
2. Fill in at minimum (see comments in the file):

| Group | Variables |
|-------|-----------|
| Copernicus | `COPERNICUS_USERNAME`, `COPERNICUS_PASSWORD` |
| Anthropic | `ANTHROPIC_API_KEY` — optional: `ANTHROPIC_MODEL` |
| Google Gemini | `GEMINI_API_KEY` — optional: `GEMINI_MODEL` (default: `gemini-2.5-pro`), `GEMINI_SECRET_RESOURCE` (GCP Secret Manager) |
| NavSecOps | `NAVSECOPS_INGEST_SECRET` (shared secret for Bearer auth) |
| Optional | `STORMGLASS_API_KEY`, `PORT` |

Do not commit `naviguide-api/.env`.

---

## How to test (local, Docker)

From the **repository root** (where the `Dockerfile` is located):

```bash
docker build -t naviguide-api:local .
docker run --rm -p 8080:8080 --env-file naviguide-api/.env -e PORT=8080 naviguide-api:local
```

Then:

- **Swagger**: http://127.0.0.1:8080/docs
- **Authorization**: click *Authorize* — enter the NavSecOps secret **value** (usually **without** the `Bearer ` prefix, depending on the UI).

**`curl` example** — `POST /api/v1/navsecops/analyze`:

```bash
curl -sS -X POST 'http://127.0.0.1:8080/api/v1/navsecops/analyze' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer YOUR_NAVSECOPS_INGEST_SECRET' \
  -H 'Content-Type: application/json' \
  -d '{"geojson":{"type":"Feature","properties":{"name":"test"},"geometry":{"type":"LineString","coordinates":[[-1.15,46.15],[-4.5,48.4]]}},"language":"en"}'
```

**GitLab chain / local script** (API already running elsewhere): [scripts/gitlab_navsecops_chain.sh](scripts/gitlab_navsecops_chain.sh).

---

## Google Cloud Run deployment (redeployment checklist)

Every change to **code or dependencies** in the image requires: **rebuild → push → new Cloud Run revision**.

### GCP prerequisites

- Project (e.g.): `naviguide-for-berry-mappemonde`
- **Artifact Registry**: Docker repository (e.g. `naviguide-api` in `europe-west9`)
- **Secret Manager**: secrets mounted as environment variables on the service, e.g.
  `gemini-api-key`, `anthropic-api-key`, `navsecops-ingest-secret`, `copernicus-username`, `copernicus-password`
- Cloud Run service account: **Secret Manager Secret Accessor** role on these secrets
- **Public** invocation (judges / Swagger without a Google account): `allUsers` → `roles/run.invoker` on the service. If the organization enforces **Domain restricted sharing** (`iam.allowedPolicyMemberDomains`), set up a **project-level exception** to allow `allUsers` on this service only.

### 1. Authenticate Docker to Artifact Registry

```bash
gcloud auth configure-docker europe-west9-docker.pkg.dev
```

### 2. Build **linux/amd64** image (required from a Mac ARM)

```bash
docker buildx build --platform linux/amd64 -t naviguide-api:local --load .
```

Verification:

```bash
docker image inspect naviguide-api:local --format '{{.Architecture}}'
```

Expected: `amd64`.

### 3. Tag + push

Replace `vN` with a new tag for each release (e.g. `v5`, `v6`).

```bash
docker tag naviguide-api:local \
  europe-west9-docker.pkg.dev/naviguide-for-berry-mappemonde/naviguide-api/naviguide-api:vN

docker push europe-west9-docker.pkg.dev/naviguide-for-berry-mappemonde/naviguide-api/naviguide-api:vN
```

### 4. Deploy / update the service

```bash
gcloud run deploy naviguide-api \
  --region=europe-west9 \
  --project=naviguide-for-berry-mappemonde \
  --image=europe-west9-docker.pkg.dev/naviguide-for-berry-mappemonde/naviguide-api/naviguide-api:vN \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --memory=2Gi \
  --timeout=300 \
  --set-secrets=GEMINI_API_KEY=gemini-api-key:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest,NAVSECOPS_INGEST_SECRET=navsecops-ingest-secret:latest,COPERNICUS_USERNAME=copernicus-username:latest,COPERNICUS_PASSWORD=copernicus-password:latest \
  --set-env-vars=GEMINI_MODEL=gemini-2.5-pro
```

If `--allow-unauthenticated` fails (org policy), manually add the `allUsers` / `roles/run.invoker` binding after fixing the project policy.

### 5. Service URL

```bash
gcloud run services describe naviguide-api \
  --region=europe-west9 \
  --project=naviguide-for-berry-mappemonde \
  --format='value(status.url)'
```

Smoke test: `GET .../docs` then the same `curl` as locally, replacing the host with the Cloud Run URL.

---

## API endpoints (overview)

| Path | Description |
|------|-------------|
| `POST /api/v1/navsecops/analyze` | Chain: validate (Gemini) → risk (Gemini) → briefing (Claude) — Bearer `NAVSECOPS_INGEST_SECRET` |
| `POST /duo/validate` | GeoJSON validation (Gemini) |
| `POST /duo/risk` | Risk assessment (Gemini) |
| `POST /duo/briefing` | Skipper synthesis (Claude) |

NavSecOps details: [docs/NAVSECOPS_PR_MATRIX.md](docs/NAVSECOPS_PR_MATRIX.md), [docs/NAVSECOPS_TECHNICAL_ROADMAP.md](docs/NAVSECOPS_TECHNICAL_ROADMAP.md).

---

## Repository structure (excerpt)

```
naviguide/
├── Dockerfile                 # API-only image (workspace + naviguide-api)
├── naviguide-api/             # FastAPI — routing, Copernicus, agents, /duo, NavSecOps
├── naviguide_workspace/       # llm_utils (Gemini google-genai + Claude), orchestrator, agents...
├── naviguide-app/             # React frontend (Vite)
├── docs/                      # Manual, NavSecOps, data...
├── scripts/                   # fetch_data, gitlab_navsecops_chain, etc.
├── supervisor/                # Local multi-service stack
└── proxy_server.py            # Dev proxy / classic deployment
```

Large data files (GEBCO, etc.): [docs/DATA.md](docs/DATA.md), [scripts/fetch_data.sh](scripts/fetch_data.sh) if present.

---

## Tech stack (API)

- FastAPI, uvicorn
- Gemini: **`google-genai`** SDK (Gemini Developer API)
- Claude: `anthropic`
- Optional: `google-cloud-secret-manager` for `GEMINI_SECRET_RESOURCE`

---

## Known limitations

- The API is **not** an ECDIS; it does not replace official charts.
- Without LLM keys, affected routes will fail or degrade (see code / logs).
- Cloud Run disk: ephemeral (local SQLite files do not persist across revisions).

---

## License

Private project — Berry-Mappemonde / NAVIGUIDE (see [LICENSE](LICENSE) if present).
