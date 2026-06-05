# CCM Analyser — Guide de démarrage complet
## API-BENIN — Laboratoire de Contrôle Qualité Phytomédicaments

---

## Structure du projet

```
projet-ccm/
│
├── backend/                     ← Serveur Python/Flask
│   ├── app.py                   ← Point d'entrée principal
│   ├── requirements.txt         ← Dépendances Python
│   │
│   ├── api/
│   │   └── routes.py            ← Tous les endpoints REST
│   │
│   ├── core/
│   │   ├── image_processor.py   ← Pipeline OpenCV complet
│   │   ├── pdf_generator.py     ← Générateur PDF ReportLab
│   │   └── export_utils.py      ← Export CSV & JSON
│   │
│   ├── models/
│   │   └── database.py          ← Modèles SQLAlchemy (SQLite)
│   │
│   ├── db/                      ← Base de données SQLite (auto-créé)
│   ├── uploads/                 ← Images uploadées (auto-créé)
│   └── exports/                 ← Fichiers exportés (auto-créé)
│
└── ccm-api-benin/               ← Frontend HTML/CSS/JS
    ├── index.html
    ├── analyse.html
    ├── resultats.html
    ├── historique.html
    ├── rapport.html
    ├── css/
    └── js/
```

---

## Installation

### Prérequis
- Python 3.10 ou supérieur
- pip

### Étapes

```bash
# 1. Se placer dans le dossier backend
cd backend

# 2. (Optionnel) Créer un environnement virtuel
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Lancer le serveur
python app.py
```

Le serveur démarre sur **http://localhost:5000**

---

## Lancement

```bash
# Mode développement (avec rechargement auto)
python app.py --debug

# Mode production (port personnalisé)
python app.py --host 0.0.0.0 --port 8080

# Avec Gunicorn (production)
gunicorn -w 2 -b 0.0.0.0:5000 "app:create_app()"
```

Ouvrir le navigateur sur : **http://localhost:5000**

---

## Endpoints API

### Santé du serveur
```
GET /api/health
```

### Analyser une plaque CCM
```
POST /api/analyse
Content-Type: multipart/form-data

Champs :
  image  : fichier image (PNG/JPG/TIFF/BMP, max 100 Mo)
  params : JSON string (voir structure ci-dessous)
```

**Structure params :**
```json
{
  "echantillon":    "ECH-2024-001",
  "phyto":          "Extrait de Neem",
  "origine":        "Cotonou",
  "lot":            "LOT-001",
  "operateur":      "Dr. Ahouansou",
  "solvant":        "BEA",
  "solvantLabel":   "Butanol / Acide acétique / Eau (4:1:5)",
  "revelateur":     "dragendorff",
  "revelateurLabel":"Réactif de Dragendorff",
  "plaque":         "silica60",
  "methode":        "auto",
  "methodeLabel":   "Automatique",
  "frontY":         5,
  "depotY":         92,
  "depots":         2,
  "ref":            "Caféine USP",
  "notes":          "Analyse de routine"
}
```

**Valeurs solvant :** `BEA` | `CM` | `EA` | `CEA` | `autre`

**Valeurs méthode :** `auto` | `threshold` | `contour` | `hough`

---

### Autres endpoints

| Méthode | Endpoint                        | Description               |
|---------|---------------------------------|---------------------------|
| GET     | `/api/analyses`                 | Liste toutes les analyses |
| GET     | `/api/analyse/<id>`             | Détail d'une analyse      |
| PUT     | `/api/analyse/<id>/valider`     | Valider une analyse       |
| DELETE  | `/api/analyse/<id>`             | Supprimer une analyse     |
| POST    | `/api/rapport/pdf`              | Générer rapport PDF       |
| GET     | `/api/rapport/<id>/csv`         | Exporter CSV              |
| GET     | `/api/rapport/<id>/json`        | Exporter JSON             |
| GET     | `/api/rapport/<id>/image`       | Image plaque annotée      |
| GET     | `/api/stats`                    | Statistiques globales     |
| GET     | `/api/alcaloides`               | Base de données Rf        |

---

## Base de données Rf intégrée

18 alcaloïdes référencés avec plages Rf pour 5 systèmes de solvants :

| Alcaloïde       | Rf (BEA)    | Rf (CM)     |
|-----------------|-------------|-------------|
| Caféine         | 0.62 – 0.78 | 0.55 – 0.72 |
| Théobromine     | 0.44 – 0.58 | 0.38 – 0.52 |
| Théophylline    | 0.26 – 0.38 | 0.22 – 0.35 |
| Quinine         | 0.70 – 0.82 | 0.65 – 0.78 |
| Morphine        | 0.12 – 0.22 | 0.10 – 0.20 |
| Codéine         | 0.30 – 0.42 | 0.28 – 0.40 |
| Atropine        | 0.45 – 0.58 | 0.42 – 0.55 |
| Scopolamine     | 0.52 – 0.64 | 0.48 – 0.61 |
| Berberine       | 0.33 – 0.47 | 0.30 – 0.44 |
| Strychnine      | 0.80 – 0.92 | 0.76 – 0.88 |
| … +8 autres     |             |             |

---

## Pipeline de traitement d'image

```
Image uploadée
    ↓
1. Prétraitement (débruitage NlMeans + CLAHE)
    ↓
2. Détection lignes (front solvant + ligne dépôt)
    ↓
3. Détection spots (seuillage adaptatif + contours)
    ↓
4. Calcul Rf = d_spot / d_front
    ↓
5. Identification alcaloïdes (comparaison base Rf)
    ↓
6. Annotation image (cercles + labels + lignes)
    ↓
Résultats JSON + Image annotée PNG
```

---

## Notes techniques

- **Base de données** : SQLite (fichier `db/ccm_apibenin.db`)
- **Images** : stockées dans `uploads/` avec nom unique
- **Exports PDF** : stockés dans `exports/`
- **CORS** : activé pour le développement front-end séparé
- **Mode démo** : si le backend est indisponible, le frontend bascule automatiquement en mode simulation locale

---

*API-BENIN — Contrôle Qualité Phytomédicaments*