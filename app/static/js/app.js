// SPA router and navigation controller.
// Hash-based routing with view-scoped cleanup for polling intervals.

const appEl = document.getElementById('app');
const routes = {};
let currentCleanup = null;

// Register a view: { render(container), cleanup?() }
export function registerView(name, view) {
  routes[name] = view;
}

// Navigate to a route programmatically
export function navigate(route) {
  window.location.hash = route;
}

// Utility: create DOM elements from HTML string
export function html(str) {
  const t = document.createElement('template');
  t.innerHTML = str.trim();
  return t.content;
}

// Utility: escape HTML to prevent XSS
export function esc(s) {
  const d = document.createElement('div');
  d.textContent = s == null ? '' : String(s);
  return d.innerHTML;
}

// Utility: format a date string for display
export function fmtDate(isoStr) {
  if (!isoStr) return '-';
  const d = new Date(isoStr);
  return d.toLocaleString();
}

// Utility: get appropriate badge class for a status string
export function badgeClass(status) {
  const map = {
    pending_approval: 'badge-pending',
    pending: 'badge-pending',
    applied: 'badge-applied',
    running: 'badge-running',
    completed: 'badge-completed',
    failed: 'badge-failed',
    cancelled: 'badge-cancelled',
    skipped: 'badge-skipped',
    reverted: 'badge-reverted',
    high: 'badge-high',
    low: 'badge-low',
    connected: 'badge-applied',
    disconnected: 'badge-failed',
    degraded: 'badge-pending',
    healthy: 'badge-applied',
  };
  return map[status] || '';
}

// Utility: show a confirmation dialog, returns a promise
export function confirm(title, message) {
  return new Promise((resolve) => {
    const overlay = document.createElement('div');
    overlay.className = 'dialog-overlay';
    overlay.innerHTML = `
      <div class="dialog">
        <div class="dialog-title">${esc(title)}</div>
        <div>${esc(message)}</div>
        <div class="dialog-actions">
          <button class="btn" data-action="cancel">Cancel</button>
          <button class="btn btn-primary" data-action="ok">Confirm</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    overlay.addEventListener('click', (e) => {
      const action = e.target.dataset.action;
      if (action) {
        overlay.remove();
        resolve(action === 'ok');
      }
    });
  });
}

function updateNav(route) {
  document.querySelectorAll('.nav-link').forEach((link) => {
    link.classList.toggle('active', link.dataset.route === route);
  });
}

async function handleRoute() {
  // Clean up previous view's polling/state
  if (currentCleanup) {
    currentCleanup();
    currentCleanup = null;
  }

  const hash = window.location.hash.slice(2) || 'dashboard';
  const route = hash.split('/')[0];
  updateNav(route);

  const view = routes[route];
  if (!view) {
    appEl.innerHTML = '<div class="empty-state">Unknown page. Redirecting...</div>';
    window.location.hash = '#/dashboard';
    return;
  }

  appEl.innerHTML = '';
  try {
    await view.render(appEl);
    if (view.cleanup) currentCleanup = view.cleanup;
  } catch (err) {
    appEl.innerHTML = `<div class="banner banner-error">Error loading view: ${esc(err.message)}</div>`;
    console.error('View render error:', err);
  }
}

window.addEventListener('hashchange', handleRoute);

// Import and register all views after DOM is ready
async function init() {
  const modules = await Promise.all([
    import('./views/dashboard.js'),
    import('./views/notes.js'),
    import('./views/patches.js'),
    import('./views/jobs.js'),
    import('./views/chat.js'),
    import('./views/logs.js'),
  ]);
  // Each module self-registers via registerView; trigger initial route
  handleRoute();
}

// Set default route if none specified
if (!window.location.hash) window.location.hash = '#/dashboard';

init();
