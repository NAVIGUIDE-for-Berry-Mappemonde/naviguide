# Matrice PR Shreyas ↔ cible NavSecOps

Branche locale suivie : `pr-shreyas` (remote `origin`). Le commit `50c33130` (« Resolved merge conflict ») a laissé des marqueurs de conflit dans les sources et un `naviguide-api/venv/` versionné.

| Zone | État dans la PR / branche | Cible NavSecOps | Action |
|------|---------------------------|-----------------|--------|
| LLM | Conflit HEAD (Gemini) vs `f4d5b955` (Nova + Claude Bedrock) dans `llm_utils.py` | Gemini pour analyse GeoJSON (`/duo/validate`, `/duo/risk`) ; Claude (API Anthropic) pour synthèse (`/duo/briefing`, orchestrateur, agents streaming) | Fusion unique dans `naviguide_workspace/llm_utils.py` ; abandon Nova sur ces chemins |
| API | Pas de routes `/duo/*` | Exposer `/duo/validate`, `/duo/risk`, `/duo/briefing` sur `naviguide-api` | Ajouter router Duo |
| Dépendances | Conflit dans `naviguide_workspace/requirements.txt` | `google-generativeai` + `anthropic` (+ option Secret Manager GCP) | Résoudre le fichier |
| venv | `naviguide-api/venv/` tracké, fichiers corrompus | Aucun venv dans Git ; `.gitignore` | `git rm -r --cached naviguide-api/venv` |
| Doc | `README.md` en conflit | Sections Google (Gemini/GCP) + Anthropic (Claude), NavSecOps | Fusion README |
| Orchestrateur | `invoke_llm` cassé tant que conflit persiste | Briefing exécutif via Claude | Inchangé côté appel ; implémentation stable |

Intégration PR : le contenu utile de la branche Shreyas (orientation Gemini) est **fusionné** dans la stratégie dual-provider ci-dessus ; pas de merge Git supplémentaire requis tant que cette branche est la ligne de travail.

**Mise à jour implémentation (post-fix) :** `llm_utils.py` unifié, routes `/duo/*` dans `naviguide-api`, `venv` retiré de l’index Git, `README.md` sans conflits, script `scripts/gitlab_navsecops_chain.sh` pour la chaîne locale.
