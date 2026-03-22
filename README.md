# NAVIGUIDE

Assistant décisionnel pour la navigation maritime (projet **Berry-Mappemonde**). Ce dépôt contient l’API **FastAPI** (`naviguide-api`), le code partagé LLM (`naviguide_workspace`), le frontend React (`naviguide-app`), et la chaîne **NavSecOps** (analyse GeoJSON : Gemini + synthèse Claude).

---

## Périmètre : image Docker vs stack complète

| Mode | Contenu | Usage |
|------|---------|--------|
| **Image Docker** ([Dockerfile](Dockerfile) à la racine) | Copie uniquement `naviguide_workspace` + `naviguide-api`, lance `uvicorn main:app` | Cloud Run, test API isolée |
| **Stack locale complète** | React, proxy, supervisord, plusieurs services | Développement intégré — voir [docs/MANUAL.md](docs/MANUAL.md) |

L’image Docker **ne** démarre **pas** le frontend ni supervisord. Le port d’écoute est **`PORT`** (souvent **8080** en local, défini par Cloud Run en production).

---

## Prérequis

- **Python 3.12** (aligné sur le Dockerfile)
- **Docker** pour builder / exécuter l’API
- Sur **Mac Apple Silicon** : pour pousser une image vers **Cloud Run (linux/amd64)**, utiliser **`docker buildx`** avec `--platform linux/amd64` (le builder classique peut produire une image **arm64** incompatible → erreur `exec format error` sur GCP). Installer le plugin **buildx** si `docker buildx` est inconnu (`brew install docker-buildx` + lien dans `~/.docker/cli-plugins`).

---

## Configuration

1. Copier le modèle : `cp naviguide-api/.env.example naviguide-api/.env`
2. Renseigner au minimum (voir commentaires dans le fichier) :

| Groupe | Variables |
|--------|-----------|
| Copernicus | `COPERNICUS_USERNAME`, `COPERNICUS_PASSWORD` |
| Anthropic | `ANTHROPIC_API_KEY` — optionnel : `ANTHROPIC_MODEL` |
| Google Gemini | `GEMINI_API_KEY` — optionnel : `GEMINI_MODEL` (défaut : `gemini-2.5-pro`), `GEMINI_SECRET_RESOURCE` (Secret Manager GCP) |
| NavSecOps | `NAVSECOPS_INGEST_SECRET` (secret partagé pour le Bearer) |
| Optionnel | `STORMGLASS_API_KEY`, `PORT` |

Ne pas committer `naviguide-api/.env`.

---

## Comment tester (local, Docker)

Depuis la **racine du dépôt** (là où se trouve le `Dockerfile`) :

```bash
docker build -t naviguide-api:local .
docker run --rm -p 8080:8080 --env-file naviguide-api/.env -e PORT=8080 naviguide-api:local
```

Puis :

- **Swagger** : http://127.0.0.1:8080/docs  
- **Autorisation** : bouton *Authorize* — saisir la **valeur** du secret NavSecOps (souvent **sans** le préfixe `Bearer `, selon l’UI).

**Exemple `curl`** — `POST /api/v1/navsecops/analyze` :

```bash
curl -sS -X POST 'http://127.0.0.1:8080/api/v1/navsecops/analyze' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer VOTRE_NAVSECOPS_INGEST_SECRET' \
  -H 'Content-Type: application/json' \
  -d '{"geojson":{"type":"Feature","properties":{"name":"test"},"geometry":{"type":"LineString","coordinates":[[-1.15,46.15],[-4.5,48.4]]}},"language":"fr"}'
```

**Chaîne GitLab / script local** (API déjà démarrée ailleurs) : [scripts/gitlab_navsecops_chain.sh](scripts/gitlab_navsecops_chain.sh).

---

## Déploiement Google Cloud Run (checklist de redéploiement)

Chaque changement de **code ou dépendances** dans l’image impose : **rebuild → push → nouvelle révision Cloud Run**.

### Prérequis GCP

- Projet (ex.) : `naviguide-for-berry-mappemonde`
- **Artifact Registry** : dépôt Docker (ex. `naviguide-api` en `europe-west9`)
- **Secret Manager** : secrets montés en variables d’environnement sur le service, par ex.  
  `gemini-api-key`, `anthropic-api-key`, `navsecops-ingest-secret`, `copernicus-username`, `copernicus-password`
- Compte d’exécution Cloud Run : rôle **Secret Manager Secret Accessor** sur ces secrets
- Invocation **publique** (juges / Swagger sans compte Google) : `allUsers` → `roles/run.invoker` sur le service. Si l’organisation applique **Domain restricted sharing** (`iam.allowedPolicyMemberDomains`), prévoir une **exception au niveau du projet** pour autoriser `allUsers` sur ce service uniquement.

### 1. Authentification Docker vers Artifact Registry

```bash
gcloud auth configure-docker europe-west9-docker.pkg.dev
```

### 2. Build image **linux/amd64** (obligatoire depuis un Mac ARM)

```bash
docker buildx build --platform linux/amd64 -t naviguide-api:local --load .
```

Vérification :

```bash
docker image inspect naviguide-api:local --format '{{.Architecture}}'
```

Attendu : `amd64`.

### 3. Tag + push

Remplacer `vN` par un nouveau tag à chaque release (ex. `v5`, `v6`).

```bash
docker tag naviguide-api:local \
  europe-west9-docker.pkg.dev/naviguide-for-berry-mappemonde/naviguide-api/naviguide-api:vN

docker push europe-west9-docker.pkg.dev/naviguide-for-berry-mappemonde/naviguide-api/naviguide-api:vN
```

### 4. Déployer / mettre à jour le service

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

Si `--allow-unauthenticated` échoue (policy org), ajouter manuellement le binding `allUsers` / `roles/run.invoker` une fois la policy projet corrigée.

### 5. URL du service

```bash
gcloud run services describe naviguide-api \
  --region=europe-west9 \
  --project=naviguide-for-berry-mappemonde \
  --format='value(status.url)'
```

Smoke test : `GET …/docs` puis le même `curl` qu’en local en remplaçant l’hôte par l’URL Cloud Run.

---

## Endpoints API (aperçu)

| Chemin | Description |
|--------|-------------|
| `POST /api/v1/navsecops/analyze` | Chaîne validate (Gemini) → risk (Gemini) → briefing (Claude) — Bearer `NAVSECOPS_INGEST_SECRET` |
| `POST /duo/validate` | Validation GeoJSON (Gemini) |
| `POST /duo/risk` | Analyse de risque (Gemini) |
| `POST /duo/briefing` | Synthèse skipper (Claude) |

Détails NavSecOps : [docs/NAVSECOPS_PR_MATRIX.md](docs/NAVSECOPS_PR_MATRIX.md), [docs/NAVSECOPS_TECHNICAL_ROADMAP.md](docs/NAVSECOPS_TECHNICAL_ROADMAP.md).

---

## Structure du dépôt (extrait)

```
naviguide/
├── Dockerfile                 # Image API seule (workspace + naviguide-api)
├── naviguide-api/             # FastAPI — routing, Copernicus, agents, /duo, NavSecOps
├── naviguide_workspace/       # llm_utils (Gemini google-genai + Claude), orchestrateur, agents…
├── naviguide-app/             # Frontend React (Vite)
├── docs/                      # Manuel, NavSecOps, données…
├── scripts/                   # fetch_data, gitlab_navsecops_chain, etc.
├── supervisor/                # Stack multi-services locale
└── proxy_server.py            # Proxy de dev / déploiement classique
```

Données lourdes (GEBCO, etc.) : [docs/DATA.md](docs/DATA.md), [scripts/fetch_data.sh](scripts/fetch_data.sh) si présent.

---

## Stack technique (API)

- FastAPI, uvicorn  
- Gemini : SDK **`google-genai`** (Gemini Developer API)  
- Claude : `anthropic`  
- Optionnel : `google-cloud-secret-manager` pour `GEMINI_SECRET_RESOURCE`

---

## Limites connues

- L’API n’est **pas** un ECDIS ; pas de substitute aux cartes officielles.  
- Sans clés LLM, les routes concernées échouent ou dégradent (voir code / logs).  
- Disque Cloud Run : éphémère (fichiers SQLite locaux non persistants entre révisions).

---

## Licence

Projet privé — Berry-Mappemonde / NAVIGUIDE (voir [LICENSE](LICENSE) si présent).
