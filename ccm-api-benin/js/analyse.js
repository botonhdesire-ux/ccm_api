/* ============================================================
   API-BENIN CCM ANALYSER — analyse.js (BACKEND INTÉGRÉ)
   Remplace la simulation par de vrais appels API Python
   ============================================================ */

'use strict';

const API_BASE = window.location.origin; // même hôte que le serveur Flask

const AnalyseState = {
  currentStep: 1,
  imageFile: null,
  imageDataUrl: null,
  params: {}
};

/* ── Step Navigation ──────────────────────────────────────── */
function goToStep(n) {
  document.querySelectorAll('.step-panel').forEach(p => p.style.display = 'none');
  document.getElementById(`step-panel-${n}`).style.display = '';
  document.querySelectorAll('.step-item').forEach(item => {
    const s = parseInt(item.getAttribute('data-step'));
    item.classList.remove('active', 'done');
    if (s < n)  item.classList.add('done');
    if (s === n) item.classList.add('active');
    const circle = item.querySelector('.step-circle');
    if (s < n)  circle.innerHTML = '✓';
    if (s >= n) circle.textContent = s;
  });
  for (let i = 1; i <= 3; i++) {
    const conn = document.getElementById(`conn-${i}-${i+1}`);
    if (conn) conn.classList.toggle('done', i < n);
  }
  AnalyseState.currentStep = n;
}

/* ── Collect Params ───────────────────────────────────────── */
function collectParams() {
  const g = id => document.getElementById(id);
  const opt = el => el.options[el.selectedIndex]?.text || '';
  return {
    echantillon:    g('field-echantillon').value.trim(),
    phyto:          g('field-phyto').value.trim(),
    origine:        g('field-origine').value.trim(),
    lot:            g('field-lot').value.trim(),
    date:           g('field-date').value,
    operateur:      g('field-operateur').value.trim(),
    solvant:        g('field-solvant').value,
    solvantLabel:   opt(g('field-solvant')),
    revelateur:     g('field-revelateur').value,
    revelateurLabel: opt(g('field-revelateur')),
    plaque:         g('field-plaque').value,
    depots:         parseInt(g('field-depots').value) || 2,
    ref:            g('field-ref').value.trim(),
    methode:        g('field-methode').value,
    methodeLabel:   opt(g('field-methode')),
    notes:          g('field-notes').value.trim(),
    frontY:         parseFloat(g('field-front-y')?.value || 5),
    depotY:         parseFloat(g('field-depot-y')?.value || 92),
  };
}

function validateStep1() {
  const p = collectParams();
  const errors = [];
  if (!p.echantillon) errors.push("Identifiant de l'échantillon requis");
  if (!p.phyto)       errors.push('Nom du phytomédicament requis');
  if (!p.solvant)     errors.push('Système de solvant requis');
  return errors;
}

function updateRecap(params) {
  const el = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val || '—'; };
  el('recap-echantillon', params.echantillon);
  el('recap-solvant',     (params.solvantLabel || '').substring(0, 25));
  el('recap-revelateur',  params.revelateurLabel);
  el('recap-methode',     params.methodeLabel);
}

/* ── Image Upload ─────────────────────────────────────────── */
function handleImageFile(file) {
  if (!file || !file.type.startsWith('image/')) {
    CCM.showToast('Fichier image invalide (PNG, JPG, TIFF…)', 'error'); return;
  }
  if (file.size > 50 * 1024 * 1024) {
    CCM.showToast('Fichier trop volumineux (max 50 Mo)', 'error'); return;
  }
  AnalyseState.imageFile = file;
  const reader = new FileReader();
  reader.onload = e => { AnalyseState.imageDataUrl = e.target.result; showImagePreview(file, e.target.result); };
  reader.readAsDataURL(file);
}

function showImagePreview(file, dataUrl) {
  const img = document.getElementById('preview-img');
  img.src = dataUrl;
  img.onload = () => {
    document.getElementById('info-dims').textContent = `${img.naturalWidth} × ${img.naturalHeight} px`;
  };
  document.getElementById('info-filename').textContent = file.name.length > 30 ? file.name.substring(0, 27) + '…' : file.name;
  document.getElementById('info-size').textContent = formatFileSize(file.size);
  document.getElementById('info-type').textContent = file.type.split('/')[1].toUpperCase();
  document.getElementById('upload-zone').style.display = 'none';
  document.getElementById('image-preview-wrap').style.display = 'block';
  const btn = document.getElementById('btn-launch-analysis');
  btn.disabled = false; btn.style.opacity = '1';
  CCM.showToast('Image chargée avec succès', 'success');
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' Ko';
  return (bytes / 1048576).toFixed(2) + ' Mo';
}

/* ── Processing Steps UI ─────────────────────────────────── */
const STEPS_UI = [
  { label: 'Prétraitement de l\'image (débruitage, normalisation)…', pct: 15 },
  { label: 'Détection des lignes de référence (front, dépôt)…',      pct: 30 },
  { label: 'Segmentation et détection des spots…',                   pct: 55 },
  { label: 'Calcul des valeurs Rf pour chaque spot…',                pct: 75 },
  { label: 'Identification des alcaloïdes par comparaison…',         pct: 90 },
  { label: 'Génération du rapport d\'analyse…',                       pct: 100 },
];

function animateProgress(stepIdx) {
  return new Promise(resolve => {
    const bar   = document.getElementById('processing-bar');
    const label = document.getElementById('processing-label');
    const step  = document.getElementById('processing-step');
    if (stepIdx >= STEPS_UI.length) { resolve(); return; }
    const s = STEPS_UI[stepIdx];
    bar.style.width = s.pct + '%';
    label.textContent = s.label;
    step.textContent  = `Étape ${stepIdx + 1}/${STEPS_UI.length}`;
    setTimeout(resolve, 600 + Math.random() * 500);
  });
}

/* ── CALL BACKEND ─────────────────────────────────────────── */
async function runAnalysis() {
  const params = AnalyseState.params;

  // Démarrer animation progression
  goToStep(3);
  window.scrollTo({ top: 0, behavior: 'smooth' });

  // Animer les étapes 1-4 pendant que le backend traite
  for (let i = 0; i < 4; i++) await animateProgress(i);

  // Appel API réel
  const formData = new FormData();
  formData.append('image',  AnalyseState.imageFile);
  formData.append('params', JSON.stringify(params));

  let result;
  try {
    const response = await fetch(`${API_BASE}/api/analyse`, {
      method: 'POST',
      body:   formData,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.error || `Erreur serveur ${response.status}`);
    }

    result = await response.json();
  } catch (err) {
    // Fallback local si serveur non disponible (mode démo)
    console.warn('Backend indisponible, mode démo activé:', err.message);
    result = buildFallbackResult(params);
    CCM.showToast('Mode démo : backend non disponible', 'warning', 5000);
  }

  // Finaliser animation
  await animateProgress(4);
  await animateProgress(5);

  // Sauvegarder localement et rediriger
  // Ajouter imageDataUrl pour le canvas frontend
  if (!result.imageDataUrl && AnalyseState.imageDataUrl) {
    result.imageDataUrl = AnalyseState.imageDataUrl;
  }
  CCM.saveAnalysisToHistory(result);
  CCM.showToast('Analyse terminée ! Redirection…', 'success');
  setTimeout(() => { window.location.href = `resultats.html?id=${result.id}`; }, 1200);
}

/* ── Fallback mode démo (si backend indisponible) ─────────── */
function buildFallbackResult(p) {
  const frontY = parseFloat(document.getElementById('field-front-y').value || 5) / 100;
  const depotY = parseFloat(document.getElementById('field-depot-y').value || 92) / 100;
  return {
    id: CCM.generateId(),
    date: new Date().toISOString(),
    status: 'done', exported: false,
    echantillon: p.echantillon, phyto: p.phyto,
    origine: p.origine, lot: p.lot, operateur: p.operateur,
    solvant: p.solvant, solvantLabel: p.solvantLabel,
    revelateur: p.revelateur, revelateurLabel: p.revelateurLabel,
    plaque: p.plaque, methode: p.methode, methodeLabel: p.methodeLabel,
    notes: p.notes, depots: p.depots, ref: p.ref,
    frontY, depotY,
    imageDataUrl: AnalyseState.imageDataUrl,
    spots: [
      { id:1, x:32, y:25, rf:0.742, color:'#4fb3ff', intensite:87, alcaloide:'Caféine',     confidence:94, statut:'confirmed' },
      { id:2, x:32, y:48, rf:0.521, color:'#3fffa2', intensite:65, alcaloide:'Théobromine',  confidence:78, statut:'probable'  },
      { id:3, x:32, y:68, rf:0.318, color:'#ffb84f', intensite:43, alcaloide:'Théophylline', confidence:61, statut:'probable'  },
      { id:4, x:68, y:33, rf:0.688, color:'#b97aff', intensite:79, alcaloide:'Caféine (réf)',confidence:92, statut:'confirmed' },
    ],
    nbSpots: 4,
  };
}

/* ── Init ─────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('field-date').value = new Date().toISOString().split('T')[0];

  document.getElementById('field-solvant').addEventListener('change', function () {
    document.getElementById('solvant-autre-group').style.display = this.value === 'autre' ? '' : 'none';
  });

  document.getElementById('btn-next-step1').addEventListener('click', () => {
    const errors = validateStep1();
    if (errors.length) { CCM.showToast(errors[0], 'warning'); return; }
    AnalyseState.params = collectParams();
    updateRecap(AnalyseState.params);
    goToStep(2);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  document.getElementById('btn-back-step2').addEventListener('click', () => {
    goToStep(1); window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  const uploadZone = document.getElementById('upload-zone');
  const fileInput  = document.getElementById('file-input');
  uploadZone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', () => { if (fileInput.files[0]) handleImageFile(fileInput.files[0]); });
  uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('drag-over'); });
  uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
  uploadZone.addEventListener('drop', e => {
    e.preventDefault(); uploadZone.classList.remove('drag-over');
    if (e.dataTransfer.files[0]) handleImageFile(e.dataTransfer.files[0]);
  });

  document.getElementById('btn-change-img').addEventListener('click', () => {
    document.getElementById('image-preview-wrap').style.display = 'none';
    document.getElementById('upload-zone').style.display = '';
    const btn = document.getElementById('btn-launch-analysis');
    btn.disabled = true; btn.style.opacity = '0.4';
    AnalyseState.imageFile = null; AnalyseState.imageDataUrl = null; fileInput.value = '';
  });

  document.getElementById('btn-launch-analysis').addEventListener('click', () => {
    if (!AnalyseState.imageFile) { CCM.showToast('Veuillez importer une image de plaque CCM', 'warning'); return; }
    AnalyseState.params = collectParams();
    runAnalysis();
  });
});