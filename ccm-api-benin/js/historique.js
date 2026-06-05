/* ============================================================
   API-BENIN CCM ANALYSER — historique.js
   Handles: history listing, search, filter, sort, delete
   ============================================================ */

'use strict';

let allHistory = [];
let filteredHistory = [];

/* ── Render table ─────────────────────────────────────────── */
function renderTable(data) {
  const tbody = document.getElementById('history-table-body');
  const empty = document.getElementById('history-empty');
  const wrap  = document.getElementById('history-table-wrap');

  if (!data.length) {
    wrap.style.display = 'none';
    empty.style.display = '';
    return;
  }

  wrap.style.display = '';
  empty.style.display = 'none';

  tbody.innerHTML = data.map(a => {
    const spots = a.spots || [];
    const confirmed = spots.filter(s => s.statut === 'confirmed').length;
    const alcaloides = spots.map(s => s.alcaloide).filter(Boolean).join(', ') || '—';
    const alcaloidesShort = alcaloides.length > 40 ? alcaloides.substring(0, 37) + '…' : alcaloides;

    const statusBadge = a.status === 'done'
      ? '<span class="tag tag-green">✓ Validé</span>'
      : '<span class="tag tag-amber">⏳ En attente</span>';

    const exportedBadge = a.exported
      ? '<span class="tag tag-blue">↓ Oui</span>'
      : '<span style="color:var(--text-muted);font-size:12px;">—</span>';

    return `
      <tr>
        <td>
          <a href="resultats.html?id=${a.id}" style="font-family:var(--font-mono);font-size:13px;color:var(--primary);text-decoration:none;font-weight:500;">
            ${a.id}
          </a>
        </td>
        <td class="td-mono">${CCM.formatDateTime(a.date)}</td>
        <td style="font-weight:500;color:var(--text-primary);">${a.echantillon || '—'}</td>
        <td style="color:var(--text-secondary);">${a.phyto || '—'}</td>
        <td>
          <span style="font-family:var(--font-mono);color:var(--primary);font-weight:600;">${spots.length}</span>
          <span style="font-size:12px;color:var(--text-muted);"> spot${spots.length > 1 ? 's' : ''}</span>
        </td>
        <td style="font-size:13px;color:var(--text-secondary);" title="${alcaloides}">${alcaloidesShort}</td>
        <td>${statusBadge}</td>
        <td>${exportedBadge}</td>
        <td>
          <div style="display:flex;gap:6px;">
            <a href="resultats.html?id=${a.id}" class="btn btn-ghost btn-sm" title="Voir résultats">👁</a>
            <a href="rapport.html?id=${a.id}"   class="btn btn-ghost btn-sm" title="Rapport">📄</a>
            <button class="btn btn-ghost btn-sm" onclick="deleteEntry('${a.id}')" title="Supprimer">🗑</button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

/* ── Update count label ───────────────────────────────────── */
function updateCountLabel() {
  const total = allHistory.length;
  const shown = filteredHistory.length;
  const label = document.getElementById('history-count-label');
  if (!label) return;
  if (total === 0) {
    label.textContent = 'Aucune analyse enregistrée';
  } else if (shown === total) {
    label.textContent = `${total} analyse${total > 1 ? 's' : ''} enregistrée${total > 1 ? 's' : ''}`;
  } else {
    label.textContent = `${shown} résultat${shown > 1 ? 's' : ''} sur ${total} analyse${total > 1 ? 's' : ''}`;
  }
}

/* ── Filter & sort ────────────────────────────────────────── */
function applyFilters() {
  const search = document.getElementById('search-input').value.toLowerCase().trim();
  const status = document.getElementById('filter-status').value;
  const sortBy = document.getElementById('sort-by').value;

  filteredHistory = allHistory.filter(a => {
    const matchSearch = !search ||
      (a.id             && a.id.toLowerCase().includes(search)) ||
      (a.echantillon    && a.echantillon.toLowerCase().includes(search)) ||
      (a.phyto          && a.phyto.toLowerCase().includes(search)) ||
      (a.spots && a.spots.some(s => s.alcaloide && s.alcaloide.toLowerCase().includes(search)));

    const matchStatus = !status || a.status === status;

    return matchSearch && matchStatus;
  });

  // Sort
  filteredHistory.sort((a, b) => {
    if (sortBy === 'date-asc')    return new Date(a.date) - new Date(b.date);
    if (sortBy === 'date-desc')   return new Date(b.date) - new Date(a.date);
    if (sortBy === 'spots-desc')  return (b.spots?.length || 0) - (a.spots?.length || 0);
    return 0;
  });

  renderTable(filteredHistory);
  updateCountLabel();
}

/* ── Delete single entry ──────────────────────────────────── */
window.deleteEntry = function(id) {
  CCM.confirmAction(
    `Supprimer l'analyse <strong>${id}</strong> ? Cette action est irréversible.`,
    () => {
      const updated = allHistory.filter(a => a.id !== id);
      CCM.Storage.set('ccm_history', updated);
      allHistory = updated;
      applyFilters();
      CCM.showToast('Analyse supprimée', 'success');
    }
  );
};

/* ── Clear all ────────────────────────────────────────────── */
function clearAll() {
  CCM.confirmAction(
    'Supprimer <strong>toutes les analyses</strong> de l\'historique ? Cette action est irréversible.',
    () => {
      CCM.Storage.remove('ccm_history');
      allHistory = [];
      filteredHistory = [];
      renderTable([]);
      updateCountLabel();
      CCM.showToast('Historique effacé', 'success');
    }
  );
}

/* ── Init ─────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  allHistory = CCM.getHistory();
  filteredHistory = [...allHistory];

  renderTable(filteredHistory);
  updateCountLabel();

  const debouncedFilter = CCM.debounce(applyFilters, 250);

  document.getElementById('search-input')?.addEventListener('input', debouncedFilter);
  document.getElementById('filter-status')?.addEventListener('change', applyFilters);
  document.getElementById('sort-by')?.addEventListener('change', applyFilters);

  document.getElementById('btn-reset-filters')?.addEventListener('click', () => {
    document.getElementById('search-input').value = '';
    document.getElementById('filter-status').value = '';
    document.getElementById('sort-by').value = 'date-desc';
    applyFilters();
  });

  document.getElementById('btn-clear-all')?.addEventListener('click', clearAll);
});