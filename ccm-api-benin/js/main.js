/* ============================================================
   API-BENIN CCM ANALYSER — main.js
   Shared logic: navigation, sidebar, toasts, utilities
   ============================================================ */

'use strict';

/* ── Active nav highlight ─────────────────────────────────── */
function setActiveNav() {
  const page = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.remove('active');
    if (el.getAttribute('href') === page) el.classList.add('active');
  });
}

/* ── Sidebar mobile toggle ────────────────────────────────── */
function initSidebar() {
  const sidebar  = document.querySelector('.sidebar');
  const overlay  = document.querySelector('.sidebar-overlay');
  const toggle   = document.querySelector('.menu-toggle');

  if (!sidebar || !toggle) return;

  toggle.addEventListener('click', () => {
    sidebar.classList.toggle('open');
    overlay.classList.toggle('visible');
  });

  overlay?.addEventListener('click', () => {
    sidebar.classList.remove('open');
    overlay.classList.remove('visible');
  });

  // Close on nav click (mobile)
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      sidebar.classList.remove('open');
      overlay?.classList.remove('visible');
    });
  });
}

/* ── Toast Notifications ──────────────────────────────────── */
const toastIcons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };

function showToast(message, type = 'info', duration = 3500) {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${toastIcons[type] || 'ℹ️'}</span>
    <span class="toast-msg">${message}</span>
    <button class="toast-close" aria-label="Fermer">×</button>
  `;

  container.appendChild(toast);

  const remove = () => {
    toast.classList.add('removing');
    toast.addEventListener('animationend', () => toast.remove(), { once: true });
  };

  toast.querySelector('.toast-close').addEventListener('click', remove);
  setTimeout(remove, duration);
}

/* ── Format date ──────────────────────────────────────────── */
function formatDate(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  return d.toLocaleDateString('fr-FR', {
    day: '2-digit', month: '2-digit', year: 'numeric'
  });
}

function formatDateTime(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  return d.toLocaleString('fr-FR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });
}

/* ── Format Rf value ──────────────────────────────────────── */
function formatRf(val) {
  return (typeof val === 'number') ? val.toFixed(3) : '—';
}

/* ── Generate analysis ID ─────────────────────────────────── */
function generateId() {
  const prefix = 'CCM';
  const ts = Date.now().toString(36).toUpperCase();
  const rand = Math.random().toString(36).substring(2, 5).toUpperCase();
  return `${prefix}-${ts}-${rand}`;
}

/* ── LocalStorage helpers ─────────────────────────────────── */
const Storage = {
  get(key, fallback = null) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch { return fallback; }
  },
  set(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); return true; }
    catch { return false; }
  },
  remove(key) { localStorage.removeItem(key); }
};

/* ── Save analysis to history ─────────────────────────────── */
function saveAnalysisToHistory(analysisData) {
  const history = Storage.get('ccm_history', []);
  history.unshift(analysisData);
  // Keep max 100 entries
  if (history.length > 100) history.splice(100);
  Storage.set('ccm_history', history);
}

/* ── Get history ──────────────────────────────────────────── */
function getHistory() {
  return Storage.get('ccm_history', []);
}

/* ── Modal helper ─────────────────────────────────────────── */
function openModal(id) {
  const backdrop = document.getElementById(id);
  if (!backdrop) return;
  backdrop.style.display = 'flex';
  requestAnimationFrame(() => backdrop.classList.add('visible'));
}

function closeModal(id) {
  const backdrop = document.getElementById(id);
  if (!backdrop) return;
  backdrop.classList.remove('visible');
  backdrop.addEventListener('transitionend', () => {
    backdrop.style.display = 'none';
  }, { once: true });
}

/* ── Confirm dialog (custom) ──────────────────────────────── */
function confirmAction(message, onConfirm) {
  const existing = document.getElementById('confirm-modal');
  if (existing) existing.remove();

  const backdrop = document.createElement('div');
  backdrop.id = 'confirm-modal';
  backdrop.className = 'modal-backdrop';
  backdrop.style.display = 'flex';
  backdrop.innerHTML = `
    <div class="modal" style="max-width:420px">
      <div class="modal-header">
        <span class="modal-title">⚠️ Confirmation</span>
      </div>
      <div class="modal-body">
        <p style="color:var(--text-secondary);font-size:14px;">${message}</p>
      </div>
      <div class="modal-footer">
        <button class="btn btn-ghost" id="confirm-cancel">Annuler</button>
        <button class="btn btn-danger" id="confirm-ok">Confirmer</button>
      </div>
    </div>
  `;

  document.body.appendChild(backdrop);
  requestAnimationFrame(() => backdrop.classList.add('visible'));

  const close = () => {
    backdrop.classList.remove('visible');
    backdrop.addEventListener('transitionend', () => backdrop.remove(), { once: true });
  };

  backdrop.querySelector('#confirm-cancel').addEventListener('click', close);
  backdrop.querySelector('#confirm-ok').addEventListener('click', () => {
    close();
    onConfirm?.();
  });
}

/* ── Debounce ─────────────────────────────────────────────── */
function debounce(fn, delay = 300) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), delay); };
}

/* ── Stat counter animation ───────────────────────────────── */
function animateCounter(el, from, to, duration = 800) {
  const start = performance.now();
  const update = (now) => {
    const progress = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3); // ease-out cubic
    const value = Math.round(from + (to - from) * ease);
    el.textContent = value;
    if (progress < 1) requestAnimationFrame(update);
  };
  requestAnimationFrame(update);
}

/* ── Animate all stat counters on page ───────────────────────*/
function initCounters() {
  document.querySelectorAll('[data-count]').forEach(el => {
    const target = parseInt(el.getAttribute('data-count'), 10);
    animateCounter(el, 0, target, 900);
  });
}

/* ── Copy to clipboard ────────────────────────────────────── */
function copyToClipboard(text) {
  navigator.clipboard.writeText(text)
    .then(() => showToast('Copié dans le presse-papier', 'success'))
    .catch(() => showToast('Impossible de copier', 'error'));
}

/* ── Init on DOM ready ────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  setActiveNav();
  initSidebar();
  initCounters();

  // Close modals on backdrop click
  document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
    backdrop.addEventListener('click', e => {
      if (e.target === backdrop) {
        backdrop.classList.remove('visible');
        setTimeout(() => { backdrop.style.display = 'none'; }, 250);
      }
    });
  });

  // Close buttons inside modals
  document.querySelectorAll('[data-close-modal]').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-close-modal');
      closeModal(id);
    });
  });
});

/* ── Gestion du thème Dark / Light ───────────────────────── */
// ← LES FONCTIONS SONT DEHORS, AVANT l'objet window.CCM

function initTheme() {
  const saved = localStorage.getItem('ccm_theme') || 'dark';
  applyTheme(saved);
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('ccm_theme', theme);
  document.querySelectorAll('.theme-toggle').forEach(btn => {
    btn.textContent = theme === 'dark' ? '☀️' : '🌙';
    btn.title       = theme === 'dark' ? 'Passer en thème clair' : 'Passer en thème sombre';
    btn.setAttribute('aria-label', btn.title);
  });
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  applyTheme(current === 'dark' ? 'light' : 'dark');
}

/* ── Expose globally ──────────────────────────────────────── */
// ← L'OBJET window.CCM EST APRÈS, il référence les fonctions déjà définies

window.CCM = {
  showToast,
  openModal,
  closeModal,
  confirmAction,
  saveAnalysisToHistory,
  getHistory,
  formatDate,
  formatDateTime,
  formatRf,
  generateId,
  Storage,
  debounce,
  copyToClipboard,
  animateCounter,
  initTheme,    // ← référence la fonction définie au-dessus
  applyTheme,
  toggleTheme,
};