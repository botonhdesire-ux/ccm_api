/* ============================================================
   API-BENIN CCM ANALYSER — rapport.js (BACKEND INTÉGRÉ)
   ============================================================ */
'use strict';

const API_BASE = window.location.origin;
let selectedAnalysis = null;

function populateSelector() {
  const history = CCM.getHistory();
  const select  = document.getElementById('select-analysis');
  if (!history.length) { select.innerHTML = '<option value="">Aucune analyse disponible</option>'; return; }
  const urlId = new URLSearchParams(location.search).get('id');
  select.innerHTML = '<option value="">-- Sélectionner une analyse --</option>' +
    history.map(a => `<option value="${a.id}" ${a.id === urlId ? 'selected' : ''}>
      ${a.id} — ${a.echantillon || 'Sans nom'} (${CCM.formatDate(a.date)})</option>`).join('');
  if (urlId) {
    selectedAnalysis = history.find(a => a.id === urlId) || null;
    if (selectedAnalysis) onAnalysisSelected();
  }
}

function onAnalysisSelected() {
  const a = selectedAnalysis;
  if (!a) {
    document.getElementById('selected-analysis-info').style.display = 'none';
    document.getElementById('pdf-preview-area').style.display = '';
    document.getElementById('pdf-preview-content').style.display = 'none';
    setExportButtons(false); return;
  }
  document.getElementById('selected-analysis-info').style.display = '';
  setEl('sel-id',    a.id);
  setEl('sel-ech',   a.echantillon || '—');
  setEl('sel-date',  CCM.formatDateTime(a.date));
  setEl('sel-spots', `${a.spots?.length || 0} spot(s)`);
  const titleField = document.getElementById('field-report-title');
  if (!titleField.value) titleField.value = `Rapport CCM — ${a.echantillon || a.id} — ${CCM.formatDate(a.date)}`;
  updatePreview();
  setExportButtons(true);
}

function updatePreview() {
  const a = selectedAnalysis;
  if (!a) return;
  document.getElementById('pdf-preview-area').style.display = 'none';
  document.getElementById('pdf-preview-content').style.display = '';
  const lab   = document.getElementById('field-report-lab').value   || 'Laboratoire API-BENIN';
  const title = document.getElementById('field-report-title').value || `Rapport CCM — ${a.id}`;
  const resp  = document.getElementById('field-report-resp').value  || '—';
  setEl('prev-id', a.id); setEl('prev-date', CCM.formatDateTime(a.date));
  setEl('prev-lab', lab); setEl('prev-title', title);
  setEl('prev-operateur', a.operateur || '—'); setEl('prev-resp', resp);
  setEl('prev-valid-date', new Date().toLocaleDateString('fr-FR'));
  const spots = a.spots || [];
  const rfTable = document.getElementById('prev-rf-table');
  rfTable.innerHTML = spots.length ? `
    <table style="width:100%;font-size:11px;border-collapse:collapse;">
      <thead><tr style="background:var(--bg-card);">
        <th style="padding:6px 10px;text-align:left;color:var(--text-muted);border-bottom:1px solid var(--border);">#</th>
        <th style="padding:6px 10px;color:var(--text-muted);border-bottom:1px solid var(--border);">Rf</th>
        <th style="padding:6px 10px;color:var(--text-muted);border-bottom:1px solid var(--border);">Alcaloïde</th>
        <th style="padding:6px 10px;color:var(--text-muted);border-bottom:1px solid var(--border);">Statut</th>
      </tr></thead>
      <tbody>${spots.map(s => `<tr style="border-bottom:1px solid var(--border);">
        <td style="padding:5px 10px;color:var(--text-secondary);">${s.id}</td>
        <td style="padding:5px 10px;font-family:var(--font-mono);color:var(--primary);font-weight:600;">${s.rf.toFixed(4)}</td>
        <td style="padding:5px 10px;color:var(--text-primary);">${s.alcaloide || '—'}</td>
        <td style="padding:5px 10px;">
          <span style="font-size:10px;padding:2px 6px;border-radius:10px;${s.statut==='confirmed'
            ? 'background:rgba(63,255,162,.15);color:var(--accent-green);'
            : 'background:rgba(255,184,79,.15);color:var(--accent-amber);'}">
            ${s.statut === 'confirmed' ? '✓ Confirmé' : '~ Probable'}</span>
        </td></tr>`).join('')}
      </tbody>
    </table>` :
    '<div style="padding:12px;text-align:center;color:var(--text-muted);font-size:12px;">Aucun spot</div>';
}

function setExportButtons(enabled) {
  ['btn-export-pdf','btn-export-csv-main','btn-export-json'].forEach(id => {
    const btn = document.getElementById(id);
    if (btn) { btn.disabled = !enabled; btn.style.opacity = enabled ? '1' : '0.4'; }
  });
}

/* ── PDF via backend ──────────────────────────────────────── */
async function exportPDF() {
  const a = selectedAnalysis;
  if (!a) return;
  const payload = {
    analysis_id: a.id,
    options: {
      title:           document.getElementById('field-report-title').value,
      lab:             document.getElementById('field-report-lab').value,
      responsable:     document.getElementById('field-report-resp').value,
      conclusion:      document.getElementById('field-report-conclusion').value,
      include_params:  document.getElementById('incl-params').checked,
      include_plate:   document.getElementById('incl-plate').checked,
      include_rf:      document.getElementById('incl-rf').checked,
      include_id:      document.getElementById('incl-id').checked,
      include_concl:   document.getElementById('incl-conclusion').checked,
      include_qr:      document.getElementById('incl-qr').checked,
    }
  };
  const btn = document.getElementById('btn-export-pdf');
  btn.textContent = '⏳ Génération…'; btn.disabled = true;
  try {
    const response = await fetch(`${API_BASE}/api/rapport/pdf`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`Erreur ${response.status}`);
    const blob = await response.blob();
    const url  = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url; link.download = `CCM_${a.id}_rapport.pdf`;
    link.click(); URL.revokeObjectURL(url);
    markExported(a.id);
    CCM.showToast('Rapport PDF généré et téléchargé !', 'success');
  } catch (err) {
    console.warn('Backend indisponible, fallback print:', err);
    CCM.showToast('Backend indisponible — ouverture impression', 'warning');
    const win = window.open('', '_blank', 'width=800,height=700');
    if (win) { win.document.write(buildPrintHTML(a)); win.document.close(); setTimeout(() => win.print(), 500); }
  } finally {
    btn.textContent = '↓ PDF'; btn.disabled = false;
  }
}

/* ── CSV via backend ──────────────────────────────────────── */
async function exportCSV() {
  const a = selectedAnalysis;
  if (!a) return;
  try {
    const response = await fetch(`${API_BASE}/api/rapport/${a.id}/csv`);
    if (!response.ok) throw new Error(`Erreur ${response.status}`);
    const blob = await response.blob();
    const url  = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url; link.download = `CCM_${a.id}.csv`;
    link.click(); URL.revokeObjectURL(url);
    markExported(a.id);
    CCM.showToast('Fichier CSV exporté', 'success');
  } catch (err) {
    // Fallback local
    const spots = a.spots || [];
    const headers = ['Spot_ID','X_pct','Y_pct','Rf','Intensite','Alcaloide','Confiance','Statut'];
    const rows = spots.map(s => [s.id,s.x,s.y,s.rf.toFixed(6),s.intensite,s.alcaloide,s.confidence,s.statut].join(','));
    downloadFile(`CCM_${a.id}.csv`, [headers.join(','),...rows].join('\n'), 'text/csv');
    CCM.showToast('CSV exporté (mode local)', 'success');
  }
}

/* ── JSON via backend ─────────────────────────────────────── */
async function exportJSON() {
  const a = selectedAnalysis;
  if (!a) return;
  const resp  = document.getElementById('field-report-resp').value;
  const lab   = document.getElementById('field-report-lab').value;
  try {
    const response = await fetch(`${API_BASE}/api/rapport/${a.id}/json?responsable=${encodeURIComponent(resp)}&lab=${encodeURIComponent(lab)}`);
    if (!response.ok) throw new Error(`Erreur ${response.status}`);
    const blob = await response.blob();
    const url  = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url; link.download = `CCM_${a.id}.json`;
    link.click(); URL.revokeObjectURL(url);
    markExported(a.id);
    CCM.showToast('Fichier JSON exporté', 'success');
  } catch (err) {
    const content = JSON.stringify({analysis: a, meta: {lab, responsable: resp}}, null, 2);
    downloadFile(`CCM_${a.id}.json`, content, 'application/json');
    CCM.showToast('JSON exporté (mode local)', 'success');
  }
}

/* ── Helpers ──────────────────────────────────────────────── */
function markExported(id) {
  const history = CCM.getHistory();
  const idx = history.findIndex(a => a.id === id);
  if (idx > -1) { history[idx].exported = true; CCM.Storage.set('ccm_history', history); }
}
function setEl(id, text) { const e = document.getElementById(id); if (e) e.textContent = text; }
function downloadFile(name, content, mime) {
  const blob = new Blob([content], { type: mime });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url; a.download = name;
  document.body.appendChild(a); a.click();
  document.body.removeChild(a); URL.revokeObjectURL(url);
}
function buildPrintHTML(a) {
  const spots = a.spots || [];
  return `<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"/><title>Rapport CCM ${a.id}</title>
  <style>body{font-family:Arial,sans-serif;color:#1a1a2e;font-size:12px;padding:30px;}
  h1{font-size:16px;border-bottom:2px solid #2563eb;padding-bottom:8px;}
  table{width:100%;border-collapse:collapse;font-size:11px;margin-top:12px;}
  th{background:#f1f5f9;padding:7px 10px;border:1px solid #e2e8f0;font-size:10px;text-transform:uppercase;}
  td{padding:6px 10px;border:1px solid #e2e8f0;}</style></head><body>
  <h1>RAPPORT CCM — ${a.id}</h1>
  <p><b>Échantillon:</b> ${a.echantillon} &nbsp;|&nbsp; <b>Phytomédicament:</b> ${a.phyto}</p>
  <p><b>Date:</b> ${CCM.formatDateTime(a.date)} &nbsp;|&nbsp; <b>Opérateur:</b> ${a.operateur || '—'}</p>
  <p><b>Solvant:</b> ${a.solvantLabel || '—'} &nbsp;|&nbsp; <b>Révélateur:</b> ${a.revelateurLabel || '—'}</p>
  <table><thead><tr><th>#</th><th>Rf</th><th>Intensité</th><th>Alcaloïde</th><th>Confiance</th><th>Statut</th></tr></thead>
  <tbody>${spots.map(s => `<tr><td>${s.id}</td><td><b>${s.rf.toFixed(4)}</b></td><td>${s.intensite}%</td>
  <td>${s.alcaloide||'—'}</td><td>${s.confidence||0}%</td><td>${s.statut}</td></tr>`).join('')}</tbody></table>
  </body></html>`;
}

/* ── Init ─────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  populateSelector();
  document.getElementById('select-analysis')?.addEventListener('change', function () {
    selectedAnalysis = CCM.getHistory().find(a => a.id === this.value) || null;
    onAnalysisSelected();
  });
  ['field-report-title','field-report-lab','field-report-resp'].forEach(id => {
    document.getElementById(id)?.addEventListener('input', CCM.debounce(updatePreview, 400));
  });
  document.getElementById('btn-export-pdf')?.addEventListener('click', exportPDF);
  document.getElementById('btn-export-csv-main')?.addEventListener('click', exportCSV);
  document.getElementById('btn-export-json')?.addEventListener('click', exportJSON);
});