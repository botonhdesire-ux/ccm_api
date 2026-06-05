# CCM Analyser — Frontend API-BENIN
## Guide d'intégration Backend

---

## Structure des fichiers

```
ccm-api-benin/
│
├── index.html          → Tableau de bord principal
├── analyse.html        → Import image + paramètres CCM
├── resultats.html      → Visualisation plaque + Rf + identifications
├── historique.html     → Historique des analyses avec filtres
├── rapport.html        → Génération et export rapports
│
├── css/
│   ├── style.css       → Design system global (variables, layout, composants de base)
│   └── components.css  → Composants spécifiques CCM (upload zone, spot markers, Rf cards…)
│
└── js/
    ├── main.js         → Utilitaires partagés (nav, toasts, localStorage, modals)
    ├── analyse.js      → Logique analyse : upload, steps, appel API traitement
    ├── resultats.js    → Affichage résultats, canvas plaque, tableau spots
    ├── historique.js   → Liste, recherche, filtres, suppression
    └── rapport.js      → Sélection, aperçu, export PDF/CSV/JSON
```

---

## Points d'intégration Backend (TODO)

### 1. Analyse d'image — `js/analyse.js`

**Fonction :** `runProcessingSimulation()` → à remplacer par :

```javascript
// POST /api/analyse
const formData = new FormData();
formData.append('image', AnalyseState.imageFile);
formData.append('params', JSON.stringify(AnalyseState.params));

const response = await fetch('/api/analyse', {
  method: 'POST',
  body: formData
});
const result = await response.json();
// result doit avoir la structure définie ci-dessous
CCM.saveAnalysisToHistory(result);
window.location.href = `resultats.html?id=${result.id}`;
```

**Structure attendue en réponse :**
```json
{
  "id": "CCM-XYZ-ABC",
  "date": "2024-01-15T10:30:00.000Z",
  "status": "done",
  "exported": false,
  "echantillon": "ECH-001",
  "phyto": "Extrait Neem",
  "solvantLabel": "Butanol / Acide acétique / Eau",
  "revelateurLabel": "Réactif de Dragendorff",
  "methodeLabel": "Automatique",
  "operateur": "Dr. Ahouansou",
  "frontY": 0.05,
  "depotY": 0.92,
  "spots": [
    {
      "id": 1,
      "x": 32,
      "y": 25,
      "rf": 0.742,
      "color": "#4fb3ff",
      "intensite": 87,
      "alcaloide": "Caféine",
      "confidence": 94,
      "statut": "confirmed"
    }
  ],
  "nbSpots": 1
}
```

---

### 2. Export PDF — `js/rapport.js`

**Fonction :** `exportPDF()` → à remplacer par :

```javascript
// POST /api/rapport/pdf
const payload = {
  analysis_id: selectedAnalysis.id,
  options: {
    title:           document.getElementById('field-report-title').value,
    lab:             document.getElementById('field-report-lab').value,
    responsable:     document.getElementById('field-report-resp').value,
    include_params:  document.getElementById('incl-params').checked,
    include_plate:   document.getElementById('incl-plate').checked,
    include_rf:      document.getElementById('incl-rf').checked,
    include_id:      document.getElementById('incl-id').checked,
    include_concl:   document.getElementById('incl-conclusion').checked,
    include_qr:      document.getElementById('incl-qr').checked,
    conclusion:      document.getElementById('field-report-conclusion').value
  }
};

const response = await fetch('/api/rapport/pdf', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload)
});
const blob = await response.blob();
const url  = URL.createObjectURL(blob);
window.open(url);
```

---

### 3. Suppression sécurisée — `js/historique.js`

Actuellement local (localStorage). Pour backend :

```javascript
// DELETE /api/analyse/:id
await fetch(`/api/analyse/${id}`, { method: 'DELETE' });
```

---

## Stockage actuel (Frontend only)

| Clé localStorage     | Contenu                                   |
|----------------------|-------------------------------------------|
| `ccm_history`        | Tableau JSON de toutes les analyses       |

Pour migrer vers base de données, remplacer les appels `CCM.Storage.get/set` dans `js/main.js` par des appels REST.

---

## Endpoints Backend suggérés

| Méthode | Route                  | Description                            |
|---------|------------------------|----------------------------------------|
| POST    | `/api/analyse`         | Traitement image CCM                   |
| GET     | `/api/analyses`        | Liste de toutes les analyses           |
| GET     | `/api/analyse/:id`     | Détail d'une analyse                   |
| DELETE  | `/api/analyse/:id`     | Supprimer une analyse                  |
| POST    | `/api/rapport/pdf`     | Générer le rapport PDF (reportlab)     |
| GET     | `/api/rapport/:id/csv` | Export CSV d'une analyse               |

---

## Dépendances Frontend

Aucune bibliothèque externe — HTML5, CSS3 natif et JavaScript vanilla uniquement.
Polices chargées via Google Fonts (Syne, DM Sans, DM Mono).


---

*API-BENIN — Laboratoire de Contrôle Qualité Phytomédicaments*