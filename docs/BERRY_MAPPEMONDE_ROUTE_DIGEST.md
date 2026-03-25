# Berry-Mappemonde — route digest (agent grounding)

**Source of truth:** `routes/naviguide-berry-mappemonde.geojson` (`FeatureCollection` name: *NAVIGUIDE - Berry-Mappemonde Expedition*).  
**Companion order (UI / app):** `naviguide-app/src/constants/itineraryPoints.ts` — same stop sequence for named points.

**Purpose:** Give Duo and human operators a **short, ordered model** of the canon circumnavigation before answering captain messages or editing geometry. Do not infer ocean routing from chat alone when this file defines the sequence.

---

## 1. Ordered port escales (`point_type: escale` in GeoJSON)

| # | Name |
|---|------|
| 1 | Saint-Maur (Berry, Indre) |
| 2 | La Rochelle |
| 3 | Ajaccio (Corse) |
| 4 | Fort-de-France (Martinique) |
| 5 | Pointe-à-Pitre (Guadeloupe) |
| 6 | Gustavia (Saint-Barthélemy) |
| 7 | Marigot (Saint-Martin) |
| 8 | Cayenne (Guyane) |
| 9 | Saint-Pierre (Saint-Pierre-et-Miquelon) |
| 10 | Papeete (Polynésie française) |
| 11 | Mata-Utu (Wallis-et-Futuna) |
| 12 | Nouméa (Nouvelle-Calédonie) |
| 13 | Dzaoudzi (Mayotte) |
| 14 | Tromelin (TAAF) |
| 15 | Saint-Gilles (La Réunion) |
| 16 | Europa (TAAF) |
| 17 | La Rochelle (closure / return — same label as #2 in data) |

**Intermediate waypoint (not an escale):** *Halifax (Nouvelle-Écosse)* — anchors the **decoupled** Saint-Pierre-et-Miquelon round trip (see §3).

---

## 2. High-level basin narrative (canon)

1. **France → Mediterranean / Atlantic approach:** overland Saint-Maur → La Rochelle; then maritime toward Corsica and west into Atlantic.
2. **Atlantic (east–west segment):** via Canaries and Cape Verde approach into the **Caribbean arc** (Sainte Lucie as routing point → Martinique → Guadeloupe → Saint-Barth → Saint-Martin).
3. **South American Atlantic coast:** Marigot → **Cayenne** (Guyane).
4. **Decoupled north-west Atlantic leg:** Halifax ↔ Saint-Pierre (return) — **geographically separate** from the Marigot–Cayenne–Pacific thread but part of the same expedition dataset.
5. **Pacific & Oceania:** Cayenne → **Papeete** → Wallis-et-Futuna → New Caledonia; then northern Australia routing points, Indian Ocean (Sri Lanka, Maldives, Seychelles), **Scattered Islands / Indian Ocean TAAF** (Mayotte, Tromelin, La Réunion, Europa).
6. **Southern Atlantic return:** Cape of Good Hope routing points → St Helena → Ascension → Atlantic return toward **La Rochelle**.

---

## 3. Decoupled SPM / Halifax block (critical for Q&A)

- In the **waypoint list**, the order is: … **Marigot → Cayenne → Halifax (intermediate) → Saint-Pierre → Papeete** …
- In the **LineString feature array**, segments **Marigot → Cayenne** and **Cayenne → Papeete** bracket the **Halifax → Saint-Pierre → Halifax** pair (feature order differs from strict geographic chronology; both belong to one canon `FeatureCollection`).

**Agent rule of thumb:** “Skip Guyane / Cayenne” means **remove that escale** and **splice** adjacent legs per minimal-edit policy — **not** “pick another Caribbean island instead,” because the **Caribbean escales already occur before Cayenne** in this canon, or "an entirely different route".

---

## 4. Full maritime / overland leg chain (`from` → `to`, file order)

Overland first, then all LineString legs in sequence:

| Leg | Type |
|-----|------|
| Saint-Maur (Berry, Indre) → La Rochelle | overland |
| La Rochelle → Point intermédiaire Avant Corse | maritime |
| Point intermédiaire Avant Corse → Ajaccio (Corse) | maritime |
| Ajaccio (Corse) → Point intermédiaire Après Corse | maritime |
| Point intermédiaire Après Corse → Point intermédiaire Après Corse | maritime |
| Point intermédiaire Après Corse → Iles Canari | maritime |
| Iles Canari → Point intermédiaire Cap Verde | maritime |
| Point intermédiaire Cap Verde → Sainte Lucie | maritime |
| Sainte Lucie → Fort-de-France (Martinique) | maritime |
| Fort-de-France (Martinique) → Pointe-à-Pitre (Guadeloupe) | maritime |
| Pointe-à-Pitre (Guadeloupe) → Gustavia (Saint-Barthélemy) | maritime |
| Gustavia (Saint-Barthélemy) → Marigot (Saint-Martin) | maritime |
| Marigot (Saint-Martin) → Cayenne (Guyane) | maritime |
| Halifax (Nouvelle-Écosse) → Saint-Pierre (Saint-Pierre-et-Miquelon) | maritime |
| Saint-Pierre (Saint-Pierre-et-Miquelon) → Halifax (Nouvelle-Écosse) | maritime |
| Cayenne (Guyane) → Papeete (Polynésie française) | maritime |
| Papeete (Polynésie française) → Mata-Utu (Wallis-et-Futuna) | maritime |
| Mata-Utu (Wallis-et-Futuna) → Nouméa (Nouvelle-Calédonie) | maritime |
| Nouméa (Nouvelle-Calédonie) → Point intermédiaire détroit de Torres | maritime |
| Point intermédiaire détroit de Torres → Point intermédiaire haut Australie | maritime |
| Point intermédiaire haut Australie → Point intermédiaire haut Australie | maritime |
| Point intermédiaire haut Australie → Point intermédiaire haut Australie | maritime |
| Point intermédiaire haut Australie → Sri Lanka | maritime |
| Sri Lanka → Maldives | maritime |
| Maldives → Seichelles | maritime |
| Seichelles → Dzaoudzi (Mayotte) | maritime |
| Dzaoudzi (Mayotte) → Tromelin (TAAF) | maritime |
| Tromelin (TAAF) → Saint-Gilles (La Réunion) | maritime |
| Saint-Gilles (La Réunion) → Europa (TAAF) | maritime |
| Europa (TAAF) → Point intermédiaire Cap de la Bonne Espérance | maritime |
| Point intermédiaire Cap de la Bonne Espérance → Point intermédiaire Sainte Hélène | maritime |
| Point intermédiaire Sainte Hélène → Point intermédiaire Ascension | maritime |
| Point intermédiaire Ascension → Point intermédiaire Ascension - Cap Verde | maritime |
| Point intermédiaire Ascension - Cap Verde → Point intermédiaire Cap Verde | maritime |
| Point intermédiaire Cap Verde → La Rochelle | maritime |

---

## 5. Maintenance

When `routes/naviguide-berry-mappemonde.geojson` changes:

1. **Update this markdown** (`docs/BERRY_MAPPEMONDE_ROUTE_DIGEST.md`) in the same MR so it stays aligned with the canon.
2. **Regenerate the machine-readable order file** (required for CI):

   ```bash
   python3 scripts/validate_berry_route_order.py --write
   ```

   Commit `routes/berry-mappemonde-route-order.json` together with the GeoJSON.

3. **CI:** On merge requests, GitLab job **`berry_route_order_validate`** runs `python3 scripts/validate_berry_route_order.py` (compare mode). If the JSON was not regenerated after a GeoJSON edit, the pipeline **fails**.
