/* ============================================================
   API-BENIN CCM ANALYSER — resultats.js
   Handles: loading analysis, canvas rendering, Rf display, table
   ============================================================ */

'use strict';

let currentAnalysis = null;
let zoomLevel = 1;

/* ── Load analysis from URL param or last in history ─────── */
function loadAnalysis() {
  const params = new URLSearchParams(location.search);
  const id = params.get('id');
  const history = CCM.getHistory();

  if (id) {
    currentAnalysis = history.find(a => a.id === id) || null;
  } else if (history.length > 0) {
    currentAnalysis = history[0];
  }

  if (!currentAnalysis) {
    document.getElementById('no-result-state').style.display = '';
    document.getElementById('result-content').style.display = 'none';
    return;
  }

  document.getElementById('no-result-state').style.display = 'none';
  document.getElementById('result-content').style.display = '';

  renderResults(currentAnalysis);
}

/* ── Render all result sections ───────────────────────────── */
function renderResults(a) {
  // Header
  document.getElementById('result-id-title').textContent = a.id;
  document.title = `Résultats ${a.id} — CCM Analyser | API-BENIN`;
  document.getElementById('result-subtitle').textContent =
    `${a.echantillon || '—'} · ${a.phyto || '—'} · ${CCM.formatDateTime(a.date)}`;

  // Export link carries the ID
  const rapportLink = document.getElementById('btn-go-rapport');
  if (rapportLink) rapportLink.href = `rapport.html?id=${a.id}`;

  // Stat cards
  const spots = a.spots || [];
  const confirmed = spots.filter(s => s.statut === 'confirmed').length;
  const rfVals = spots.map(s => s.rf).filter(Boolean).sort((x, y) => x - y);
  const avgConf = spots.length ? Math.round(spots.reduce((s, sp) => s + (sp.confidence || 0), 0) / spots.length) : 0;

  animateStatValue('res-stat-spots', spots.length);
  animateStatValue('res-stat-identified', confirmed);
  document.getElementById('res-stat-rf-range').textContent =
    rfVals.length ? `${rfVals[0].toFixed(3)} – ${rfVals[rfVals.length - 1].toFixed(3)}` : '—';
  document.getElementById('res-stat-conf').textContent = spots.length ? `${avgConf}%` : '—';

  // Plate canvas
  renderPlateCanvas(a);

  // Rf cards
  renderRfCards(spots);

  // Identification results
  renderIdResults(spots);

  // Table
  renderSpotsTable(spots);

  // Params recap
  renderParamsRecap(a);
}

/* ── Animate a stat value ─────────────────────────────────── */
function animateStatValue(id, target) {
  const el = document.getElementById(id);
  if (!el) return;
  CCM.animateCounter(el, 0, target, 700);
}

/* ── Canvas plate rendering ───────────────────────────────── */
function renderPlateCanvas(a) {
  const canvas  = document.getElementById('plate-canvas');
  const ctx     = canvas.getContext('2d');
  const viewer  = document.getElementById('plate-viewer');

  const W = viewer.clientWidth || 500;
  const H = Math.round(W * 1.5); // CCM plate aspect ratio

  canvas.width  = W;
  canvas.height = H;
  canvas.style.height = H + 'px';

  // Draw background
  ctx.fillStyle = '#0a0c0f';
  ctx.fillRect(0, 0, W, H);

  // If image is available, draw it
  if (a.imageDataUrl) {
    const img = new Image();
    img.onload = () => {
      ctx.drawImage(img, 0, 0, W, H);
      drawPlateOverlays(ctx, W, H, a);
    };
    img.src = a.imageDataUrl;
  } else {
    // Draw placeholder grid
    drawPlaceholderPlate(ctx, W, H);
    drawPlateOverlays(ctx, W, H, a);
  }
}

function drawPlaceholderPlate(ctx, W, H) {
  // Gradient bg simulating TLC plate
  const grad = ctx.createLinearGradient(0, 0, 0, H);
  grad.addColorStop(0,   '#1a1f2e');
  grad.addColorStop(0.5, '#141820');
  grad.addColorStop(1,   '#0f1218');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, W, H);

  // Subtle grid texture
  ctx.strokeStyle = 'rgba(79,179,255,0.04)';
  ctx.lineWidth = 1;
  for (let x = 0; x <= W; x += 20) {
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
  }
  for (let y = 0; y <= H; y += 20) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
  }

  // Label
  ctx.fillStyle = 'rgba(141,164,196,0.2)';
  ctx.font = '12px DM Mono, monospace';
  ctx.textAlign = 'center';
  ctx.fillText('IMAGE NON DISPONIBLE', W / 2, H / 2 - 10);
  ctx.fillText('(Rendu de démonstration)', W / 2, H / 2 + 10);
}

function drawPlateOverlays(ctx, W, H, a) {
  const frontPct = a.frontY || 0.05;
  const depotPct = a.depotY || 0.92;
  const frontY   = H * frontPct;
  const depotY   = H * depotPct;

  // Solvent front line
  ctx.setLineDash([6, 4]);
  ctx.strokeStyle = 'rgba(255,184,79,0.8)';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(12, frontY); ctx.lineTo(W - 12, frontY);
  ctx.stroke();

  // Label front
  ctx.setLineDash([]);
  ctx.fillStyle = 'rgba(10,13,18,0.85)';
  ctx.roundRect(W - 90, frontY - 11, 82, 20, 3);
  ctx.fill();
  ctx.fillStyle = '#ffb84f';
  ctx.font = '10px DM Mono, monospace';
  ctx.textAlign = 'right';
  ctx.fillText('Front solvant', W - 6, frontY + 4);

  // Depot line
  ctx.setLineDash([6, 4]);
  ctx.strokeStyle = 'rgba(79,179,255,0.8)';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(12, depotY); ctx.lineTo(W - 12, depotY);
  ctx.stroke();

  // Label depot
  ctx.setLineDash([]);
  ctx.fillStyle = 'rgba(10,13,18,0.85)';
  ctx.roundRect(W - 90, depotY - 11, 82, 20, 3);
  ctx.fill();
  ctx.fillStyle = '#4fb3ff';
  ctx.font = '10px DM Mono, monospace';
  ctx.textAlign = 'right';
  ctx.fillText('Ligne dépôt', W - 6, depotY + 4);

  ctx.setLineDash([]);

  // Spots
  const spots = a.spots || [];
  spots.forEach((spot, i) => {
    const sx = (spot.x / 100) * W;
    const sy = (spot.y / 100) * H;
    const r  = 14;

    // Spot glow
    const grd = ctx.createRadialGradient(sx, sy, 0, sx, sy, r * 2);
    grd.addColorStop(0, (spot.color || '#4fb3ff') + '55');
    grd.addColorStop(1, 'transparent');
    ctx.fillStyle = grd;
    ctx.beginPath();
    ctx.arc(sx, sy, r * 2, 0, Math.PI * 2);
    ctx.fill();

    // Spot ring
    ctx.strokeStyle = spot.color || '#3fffa2';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(sx, sy, r, 0, Math.PI * 2);
    ctx.stroke();

    // Spot inner dot
    ctx.fillStyle = (spot.color || '#3fffa2') + 'aa';
    ctx.beginPath();
    ctx.arc(sx, sy, 5, 0, Math.PI * 2);
    ctx.fill();

    // Spot label
    const label = `Rf ${spot.rf.toFixed(3)}`;
    ctx.fillStyle = 'rgba(10,13,18,0.9)';
    ctx.roundRect(sx - 28, sy - r - 22, 56, 18, 3);
    ctx.fill();
    ctx.fillStyle = spot.color || '#4fb3ff';
    ctx.font = '10px DM Mono, monospace';
    ctx.textAlign = 'center';
    ctx.fillText(label, sx, sy - r - 9);

    // Vertical Rf line from spot to depot
    ctx.strokeStyle = (spot.color || '#3fffa2') + '33';
    ctx.lineWidth = 1;
    ctx.setLineDash([3, 5]);
    ctx.beginPath();
    ctx.moveTo(sx, sy + r); ctx.lineTo(sx, depotY);
    ctx.stroke();
    ctx.setLineDash([]);
  });
}

/* ── Rf Cards ─────────────────────────────────────────────── */
function renderRfCards(spots) {
  const container = document.getElementById('rf-cards-list');
  if (!spots.length) {
    container.innerHTML = '<div class="empty-state" style="padding:30px 0;"><div class="empty-icon">📐</div><div class="empty-title">Aucun spot détecté</div></div>';
    return;
  }

  container.innerHTML = spots.map(s => `
    <div class="rf-card">
      <div class="rf-color-dot" style="background:${s.color || '#4fb3ff'};box-shadow:0 0 8px ${s.color || '#4fb3ff'}66;"></div>
      <div class="rf-info">
        <div class="rf-name">Spot #${s.id} — ${s.alcaloide || 'Non identifié'}</div>
        <div class="rf-coords">X: ${s.x}% · Y: ${s.y}% · Intensité: ${s.intensite}%</div>
      </div>
      <div class="rf-value-wrap">
        <div class="rf-value">${s.rf.toFixed(3)}</div>
        <div class="rf-label">Rf</div>
      </div>
    </div>
  `).join('');
}

/* ── Identification Results ───────────────────────────────── */
function renderIdResults(spots) {
  const container = document.getElementById('id-results-list');
  if (!spots.length) {
    container.innerHTML = '<div class="empty-state" style="padding:30px 0;"><div class="empty-icon">🧬</div><div class="empty-title">Aucune identification</div></div>';
    return;
  }

  container.innerHTML = spots.map(s => {
    const icons = { confirmed: '✅', probable: '⚠️', absent: '❌' };
    return `
      <div class="id-result ${s.statut || 'probable'}">
        <span class="id-icon">${icons[s.statut] || '⚠️'}</span>
        <div class="id-content">
          <div class="id-compound">${s.alcaloide || 'Inconnu'}</div>
          <div class="id-detail">Spot #${s.id} · Rf = ${s.rf.toFixed(3)}</div>
        </div>
        <div class="id-confidence">
          <div class="id-percent">${s.confidence || 0}%</div>
          <div class="id-percent-label">confiance</div>
        </div>
      </div>
    `;
  }).join('');
}

/* ── Spots Table ──────────────────────────────────────────── */
function renderSpotsTable(spots) {
  const tbody = document.getElementById('spots-table-body');
  if (!spots.length) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;padding:30px;color:var(--text-muted);">Aucun spot détecté</td></tr>`;
    return;
  }

  const statutMap = {
    confirmed: '<span class="tag tag-green">✓ Confirmé</span>',
    probable:  '<span class="tag tag-amber">~ Probable</span>',
    absent:    '<span class="tag tag-red">✗ Absent</span>'
  };

  tbody.innerHTML = spots.map(s => `
    <tr>
      <td><strong style="color:var(--text-primary);">#${s.id}</strong></td>
      <td class="td-mono">${s.x}%</td>
      <td class="td-mono">${s.y}%</td>
      <td>
        <strong style="color:var(--primary);font-family:var(--font-mono);">${s.rf.toFixed(3)}</strong>
      </td>
      <td>
        <div style="display:flex;align-items:center;gap:8px;">
          <div class="progress-bar" style="width:60px;">
            <div class="progress-fill" style="width:${s.intensite}%;background:${s.color};"></div>
          </div>
          <span class="td-mono">${s.intensite}%</span>
        </div>
      </td>
      <td>
        <div style="display:flex;align-items:center;gap:8px;">
          <div style="width:10px;height:10px;border-radius:50%;background:${s.color};flex-shrink:0;"></div>
          ${s.alcaloide || '—'}
        </div>
      </td>
      <td class="td-mono">${s.confidence || 0}%</td>
      <td>${statutMap[s.statut] || '—'}</td>
      <td>
        <button class="btn btn-ghost btn-sm" onclick="editSpot(${s.id})">✏️ Éditer</button>
      </td>
    </tr>
  `).join('');
}

/* ── Params Recap ─────────────────────────────────────────── */
function renderParamsRecap(a) {
  const grid = document.getElementById('params-recap-grid');
  const items = [
    { label: 'Échantillon',   value: a.echantillon },
    { label: 'Phytomédicament', value: a.phyto },
    { label: 'Origine',       value: a.origine },
    { label: 'Numéro de lot', value: a.lot },
    { label: 'Date analyse',  value: CCM.formatDate(a.date) },
    { label: 'Opérateur',     value: a.operateur },
    { label: 'Solvant',       value: a.solvantLabel },
    { label: 'Révélateur',    value: a.revelateurLabel },
    { label: 'Méthode',       value: a.methodeLabel },
  ];

  grid.innerHTML = items.filter(i => i.value).map(i => `
    <div class="params-panel" style="background:var(--bg-elevated);">
      <div class="params-title">${i.label}</div>
      <div style="font-size:14px;color:var(--text-primary);font-weight:500;">${i.value || '—'}</div>
    </div>
  `).join('');

  // Notes
  if (a.notes) {
    document.getElementById('notes-section').style.display = '';
    document.getElementById('notes-content').textContent = a.notes;
  }
}

/* ── Edit spot (stub for backend) ─────────────────────────── */
window.editSpot = function(id) {
  // TODO: open modal for manual correction of spot identification
  CCM.showToast(`Édition du spot #${id} — fonctionnalité backend requise`, 'info');
};

/* ── Export CSV ───────────────────────────────────────────── */
function exportCSV() {
  if (!currentAnalysis) return;
  const spots = currentAnalysis.spots || [];
  const headers = ['Spot', 'X (%)', 'Y (%)', 'Rf', 'Intensite (%)', 'Alcaloide', 'Confiance (%)', 'Statut'];
  const rows = spots.map(s =>
    [s.id, s.x, s.y, s.rf.toFixed(4), s.intensite, s.alcaloide, s.confidence, s.statut].join(',')
  );
  const csv = [headers.join(','), ...rows].join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `CCM_${currentAnalysis.id}_resultats.csv`;
  a.click();
  URL.revokeObjectURL(url);
  CCM.showToast('Fichier CSV exporté', 'success');
}

/* ── Copy Rf to clipboard ─────────────────────────────────── */
function copyRfValues() {
  if (!currentAnalysis) return;
  const spots = currentAnalysis.spots || [];
  const text = spots.map(s => `Spot #${s.id} (${s.alcaloide}): Rf = ${s.rf.toFixed(4)}`).join('\n');
  CCM.copyToClipboard(text);
}

/* ── Zoom ─────────────────────────────────────────────────── */
function applyZoom() {
  const canvas = document.getElementById('plate-canvas');
  canvas.style.transform = `scale(${zoomLevel})`;
  canvas.style.transformOrigin = 'top center';
}

/* ── Validate result ──────────────────────────────────────── */
function validateResult() {
  if (!currentAnalysis) return;
  const history = CCM.getHistory();
  const idx = history.findIndex(a => a.id === currentAnalysis.id);
  if (idx > -1) {
    history[idx].status = 'done';
    history[idx].validatedAt = new Date().toISOString();
    CCM.Storage.set('ccm_history', history);
    CCM.showToast('Analyse validée avec succès !', 'success');
  }
}

/* ── Init ─────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  loadAnalysis();

  document.getElementById('btn-export-csv')?.addEventListener('click', exportCSV);
  document.getElementById('btn-copy-rf')?.addEventListener('click', copyRfValues);
  document.getElementById('btn-validate-result')?.addEventListener('click', validateResult);

  document.getElementById('btn-zoom-in')?.addEventListener('click', () => {
    zoomLevel = Math.min(zoomLevel + 0.2, 2.5);
    applyZoom();
  });
  document.getElementById('btn-zoom-out')?.addEventListener('click', () => {
    zoomLevel = Math.max(zoomLevel - 0.2, 0.5);
    applyZoom();
  });
  document.getElementById('btn-zoom-reset')?.addEventListener('click', () => {
    zoomLevel = 1;
    applyZoom();
  });
});