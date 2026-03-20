# Plan de développement — Hackathon Amazon Nova AI

**Deadline hackathon : 17 mars 2026**

Bedrock est actuellement bloqué (ValidationException: Operation not allowed). Ce plan prépare le code pour quand l'accès sera rétabli.

---

## État actuel

### ✅ Déjà fait

| Composant | Nova 2 Lite | Fallback Claude | Fallback statique |
|-----------|------------|-----------------|-------------------|
| `llm_utils.py` | ✅ | ✅ | — |
| Orchestrator (briefing) | ✅ | ✅ | ✅ `_build_fallback_briefing` |
| Agent 1 (route intelligence) | ✅ | ✅ | ✅ message manuel |
| Agent 3 (risk assessment) | ✅ | ✅ | ✅ message manuel |
| naviguide-api agents (meteo, pirate, guard, custom) | ✅ via deploy_ai | ✅ | ✅ degrade gracefully |
| polar_api chat | ✅ | ✅ | ✅ |
| polar_agent | ✅ | ✅ | ✅ |

**Modèle principal :** `us.amazon.nova-2-lite-v1:0` (US region)  
**Fallback :** `us.anthropic.claude-3-5-sonnet-20241022-v2:0`

---

## Tâches à faire (en attendant Bedrock)

### 1. Documentation & README
- [ ] Mettre à jour README : remplacer Claude par Nova + hackathon
- [ ] Mettre à jour le schéma AI Pipeline (Nova → Claude fallback)
- [ ] Ajouter section hackathon Nova dans README

### 2. Vérifier le fallback statique
- [x] **Orchestrator** : si Agent 1 échoue → `degraded_plan_node` retourne un plan avec `_build_fallback_briefing` (au lieu de rien)
- [x] Lancer le pipeline : le briefing fallback s'affiche correctement
- [x] Agents (meteo, pirate, guard, custom) : fallback "LLM service temporarily unavailable" + liens utiles

### 3. Script de smoke test Bedrock
- [x] Créer `scripts/test_bedrock.py`
- [ ] À lancer dès que Bedrock est débloqué : `cd naviguide_workspace && python3 ../scripts/test_bedrock.py`

### 4. Build & déploiement
- [x] Build frontend : `npm run build` OK
- [ ] Vérifier supervisord (orchestrator, api, polar, proxy)
- [ ] S'assurer que `.env` est chargé correctement (naviguide_workspace)

### 5. Hackathon submission
- [x] Soumission déjà faite

---

## Quand Bedrock sera débloqué

1. **Tester immédiatement** : `scripts/test_bedrock.py`
2. **Vérifier credentials** : `.env` avec `AWS_ACCESS_KEY_ID` ou `AWS_BEARER_TOKEN_BEDROCK`
3. **Lancer le pipeline** : POST `/api/v1/expedition/plan/berry-mappemonde`
4. **Vérifier les logs** : `[llm] Nova 2 Lite OK` ou `[llm] Claude fallback OK`

---

## Structure des appels LLM

```
llm_utils.invoke_llm(prompt, system, fallback_msg)
    ├─ 1. boto3 bedrock-runtime.converse(NOVA_MODEL)
    ├─ 2. si échec → ChatBedrock(CLAUDE_MODEL)
    └─ 3. si échec → return None (caller utilise fallback_msg ou _build_fallback_*)
```

Tous les callers gèrent déjà `None` avec un fallback structuré.

---

## Chemin dégradé (Agent 1 échoue)

Quand Agent 1 lève une exception (searoute, etc.), le graph va maintenant vers `degraded_plan` au lieu de `END`. Le nœud `degraded_plan_node` construit un plan minimal avec `_build_fallback_briefing`, garantissant que le frontend reçoit toujours un briefing exploitable.
