// System Dashboard view: health status, vault metrics, sparklines, stale warning, scan trigger.
// Polls every 30 seconds for health data refresh.

import { registerView, html, esc, badgeClass } from '../app.js';
import { api } from '../api.js';
import { createSparkline } from '../components/sparkline.js';

let pollTimer = null;

const METRICS = ['health_score', 'orphan_count', 'backlink_density', 'cluster_count', 'unique_tag_count'];
const METRIC_LABELS = {
  health_score: 'Health Score',
  orphan_count: 'Orphans',
  backlink_density: 'Backlink Density',
  cluster_count: 'Clusters',
  unique_tag_count: 'Tags',
};

async function render(container) {
  container.innerHTML = '<div class="spinner"></div> Loading dashboard...';

  try {
    const [healthData, dashData] = await Promise.all([
      api.health(),
      api.vaultDashboard().catch(() => null),
    ]);

    container.innerHTML = '';

    // Service health status
    const services = ['obsidian_api', 'redis', 'postgres'];
    const healthHtml = services.map(s => {
      const status = healthData[s] || 'disconnected';
      return `<div class="card" style="text-align:center">
        <span class="status-dot ${status}"></span>
        <strong>${esc(s.replace('_', ' '))}</strong>
        <div><span class="badge ${badgeClass(status)}">${esc(status)}</span></div>
      </div>`;
    }).join('');

    const statusSection = document.createElement('div');
    statusSection.innerHTML = `
      <div class="card-title">Service Connectivity</div>
      <div class="grid-3">${healthHtml}</div>`;
    container.appendChild(statusSection);

    // Stale data warning
    if (dashData && dashData.stale_data) {
      const hours = dashData.last_scan_age_hours ? Math.round(dashData.last_scan_age_hours) : '?';
      const banner = document.createElement('div');
      banner.className = 'banner banner-warning';
      banner.textContent = `Stale data: last scan was ${hours} hours ago (threshold: ${dashData.stale_threshold_hours}h)`;
      container.appendChild(banner);
    }

    // Vault metrics
    if (dashData && dashData.latest_snapshot) {
      const snap = dashData.latest_snapshot;
      const metricsSection = document.createElement('div');
      metricsSection.innerHTML = `<div class="card-title" style="margin-top:16px">Vault Health</div>`;

      const grid = document.createElement('div');
      grid.className = 'grid-4';

      const metricData = [
        { label: 'Health Score', value: snap.health_score != null ? snap.health_score.toFixed(1) : '-' },
        { label: 'Total Notes', value: snap.total_notes },
        { label: 'Orphans', value: snap.orphan_count },
        { label: 'Backlink Density', value: snap.backlink_density != null ? snap.backlink_density.toFixed(2) : '-' },
        { label: 'Clusters', value: snap.cluster_count },
        { label: 'Tags', value: snap.unique_tag_count },
      ];

      metricData.forEach(m => {
        const card = document.createElement('div');
        card.className = 'card';
        card.innerHTML = `<div class="metric-value">${esc(String(m.value))}</div>
          <div class="metric-label">${esc(m.label)}</div>`;
        grid.appendChild(card);
      });

      metricsSection.appendChild(grid);
      container.appendChild(metricsSection);

      // Sparklines from trends
      const sparklinesSection = document.createElement('div');
      sparklinesSection.innerHTML = `<div class="card-title" style="margin-top:16px">Trends (30 days)</div>`;
      const sparkGrid = document.createElement('div');
      sparkGrid.className = 'grid-4';

      for (const metric of METRICS) {
        const card = document.createElement('div');
        card.className = 'card';
        card.innerHTML = `<div class="metric-label">${esc(METRIC_LABELS[metric])}</div>`;

        try {
          const trend = await api.vaultTrends(metric);
          const points = (trend.data_points || []).map(dp => dp.value);
          card.appendChild(createSparkline(points, { width: 160, height: 36 }));
          if (trend.delta != null) {
            const deltaEl = document.createElement('div');
            deltaEl.style.fontSize = '0.75rem';
            deltaEl.style.color = trend.delta >= 0 ? 'var(--success)' : 'var(--error)';
            deltaEl.textContent = `${trend.delta >= 0 ? '+' : ''}${trend.delta.toFixed(2)}`;
            card.appendChild(deltaEl);
          }
        } catch (_) {
          card.appendChild(createSparkline([], { width: 160, height: 36 }));
        }

        sparkGrid.appendChild(card);
      }

      sparklinesSection.appendChild(sparkGrid);
      container.appendChild(sparklinesSection);
    } else if (!dashData || dashData.message) {
      const noData = document.createElement('div');
      noData.className = 'empty-state';
      noData.innerHTML = `<p>No vault health data yet.</p><p>Run a health scan to see metrics.</p>`;
      container.appendChild(noData);
    }

    // Scan button
    const actions = document.createElement('div');
    actions.style.marginTop = '16px';
    const scanBtn = document.createElement('button');
    scanBtn.className = 'btn btn-primary';
    scanBtn.textContent = 'Run Health Scan';
    scanBtn.addEventListener('click', async () => {
      scanBtn.disabled = true;
      scanBtn.textContent = 'Starting...';
      try {
        const result = await api.createJob('vault_health_scan');
        scanBtn.textContent = `Scan started (Job ${result.job_id.slice(0, 8)}...)`;
      } catch (err) {
        scanBtn.textContent = 'Error: ' + err.message;
      }
    });
    actions.appendChild(scanBtn);
    container.appendChild(actions);

    // Start polling
    pollTimer = setInterval(() => render(container), 30000);

  } catch (err) {
    container.innerHTML = `<div class="banner banner-error">Failed to load dashboard: ${esc(err.message)}</div>`;
  }
}

function cleanup() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

registerView('dashboard', { render, cleanup });
