# NAVIGUIDE — Manuel utilisateur

Guide d'utilisation de l'application NAVIGUIDE pour le tour du monde Berry-Mappemonde.

---

## Vue d'ensemble

NAVIGUIDE est un assistant de navigation maritime qui aide le skipper à planifier l'expédition Berry-Mappemonde (36 000+ milles nautiques, 45+ escales). Il fournit :

- **Carte interactive** — tracé de la route, évitement des zones de trafic commercial
- **Briefing d'expédition** — résumé exécutif généré par IA (Nova / Claude)
- **Mode simulation** — avancement étape par étape avec ETA, cap, VMG
- **Agents IA** — Météo, Sécurité, Ports, Cruisers — pour des questions par tronçon

---

## Utilisation

### 1. Charger le plan

À l'ouverture, l'app charge automatiquement le plan Berry-Mappemonde et génère le briefing. Si l'IA est indisponible, un briefing de secours structuré s'affiche.

### 2. Mode simulation

- Clique sur **Simulation** pour activer le mode pas à pas
- Utilise **Suivant** / **Précédent** pour naviguer entre les legs
- Le marqueur catamaran montre la position actuelle, le cap et le VMG

### 3. Agents IA (par leg)

En mode simulation, sélectionne un leg puis ouvre un onglet agent :

| Agent | Rôle |
|-------|------|
| **Ports** | Formalités, tarifs marina, entrée au port |
| **Sécurité** | Piraterie, GMDSS, trafic |
| **Météo** | Fenêtres de passage, cyclones, vents |
| **Cruisers** | Noonsite, forums, communautés |

Pose une question ; l'agent répond en streaming. Si l'IA est indisponible, des liens utiles sont proposés.

### 4. Couches maritimes

- **ZEE** — zones économiques exclusives
- **Ports WPI** — ports du monde
- **Balisage** — marques de navigation

### 5. Export

- **GeoJSON** — export de la route complète
- **KML** — pour Google Earth / logiciels de cartographie

---

## En cas de problème

- **Briefing vide ou "LLM unavailable"** — Le service IA est temporairement indisponible. Un briefing de secours structuré s'affiche. Réessaie plus tard.
- **Agents sans réponse** — Des liens vers Noonsite, Windy, IMB Piracy sont fournis en fallback.

---

*NAVIGUIDE — Berry-Mappemonde Expedition*
