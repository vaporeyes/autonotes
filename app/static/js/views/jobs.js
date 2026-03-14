// Jobs Monitor view: filterable job list, progress bars, cancel, detail expansion.
// Polls every 5 seconds when running jobs exist.

import { registerView, esc, fmtDate, badgeClass, confirm } from '../app.js';
import { api } from '../api.js';
import { createProgressBar } from '../components/progress-bar.js';

let pollTimer = null;
let currentFilters = { status: '', job_type: '' };

async function render(container) {
  container.innerHTML = '';

  // Filters
  const filters = document.createElement('div');
  filters.className = 'filters';
  filters.innerHTML = `
    <select id="job-status-filter">
      <option value="">All Statuses</option>
      <option value="pending">Pending</option>
      <option value="running">Running</option>
      <option value="completed">Completed</option>
      <option value="failed">Failed</option>
      <option value="cancelled">Cancelled</option>
    </select>
    <select id="job-type-filter">
      <option value="">All Types</option>
      <option value="vault_scan">Vault Scan</option>
      <option value="vault_cleanup">Cleanup</option>
      <option value="ai_analysis">AI Analysis</option>
      <option value="vault_health_scan">Health Scan</option>
      <option value="triage_scan">Triage</option>
      <option value="embed_notes">Embed Notes</option>
      <option value="cluster_notes">Cluster Notes</option>
      <option value="batch_patch">Batch Patch</option>
    </select>`;
  container.appendChild(filters);

  // Apply saved filter values
  const statusSel = filters.querySelector('#job-status-filter');
  const typeSel = filters.querySelector('#job-type-filter');
  statusSel.value = currentFilters.status;
  typeSel.value = currentFilters.job_type;

  const onChange = () => {
    currentFilters.status = statusSel.value;
    currentFilters.job_type = typeSel.value;
    loadJobs(container);
  };
  statusSel.addEventListener('change', onChange);
  typeSel.addEventListener('change', onChange);

  const listEl = document.createElement('div');
  listEl.id = 'jobs-list';
  container.appendChild(listEl);

  await loadJobs(container);
}

async function loadJobs(container) {
  const listEl = container.querySelector('#jobs-list');
  if (!listEl) return;

  try {
    const data = await api.jobs({
      status: currentFilters.status || undefined,
      job_type: currentFilters.job_type || undefined,
      limit: 100,
    });

    listEl.innerHTML = '';

    if (data.jobs.length === 0) {
      listEl.innerHTML = '<div class="empty-state">No jobs found</div>';
      stopPoll();
      return;
    }

    const table = document.createElement('table');
    table.innerHTML = `<thead><tr>
      <th>Type</th><th>Status</th><th>Progress</th><th>Created</th><th>Actions</th>
    </tr></thead>`;

    const tbody = document.createElement('tbody');
    let hasRunning = false;

    data.jobs.forEach(job => {
      if (job.status === 'running') hasRunning = true;

      const tr = document.createElement('tr');
      tr.style.cursor = 'pointer';

      const progressCell = document.createElement('td');
      if (job.progress && job.progress.total > 0) {
        progressCell.appendChild(createProgressBar(job.progress.current, job.progress.total));
      } else {
        progressCell.textContent = '-';
      }

      tr.innerHTML = `
        <td>${esc(job.job_type)}</td>
        <td><span class="badge ${badgeClass(job.status)}">${esc(job.status)}</span></td>`;
      tr.appendChild(progressCell);

      const timeCell = document.createElement('td');
      timeCell.style.fontSize = '0.8rem';
      timeCell.textContent = fmtDate(job.created_at);
      tr.appendChild(timeCell);

      const actionsCell = document.createElement('td');

      if (job.status === 'running' || job.status === 'pending') {
        const cancelBtn = document.createElement('button');
        cancelBtn.className = 'btn btn-danger btn-sm';
        cancelBtn.textContent = 'Cancel';
        cancelBtn.addEventListener('click', async (e) => {
          e.stopPropagation();
          const ok = await confirm('Cancel Job', `Cancel ${job.job_type} job?`);
          if (!ok) return;
          try {
            await api.cancelJob(job.job_id);
            loadJobs(container);
          } catch (err) {
            alert('Error: ' + err.message);
          }
        });
        actionsCell.appendChild(cancelBtn);
      }
      tr.appendChild(actionsCell);

      // Click row to show detail
      tr.addEventListener('click', () => toggleDetail(tr, job));

      tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    listEl.appendChild(table);

    // Poll if running jobs exist
    if (hasRunning) {
      startPoll(container);
    } else {
      stopPoll();
    }
  } catch (err) {
    listEl.innerHTML = `<div class="banner banner-error">${esc(err.message)}</div>`;
  }
}

function toggleDetail(tr, job) {
  const existing = tr.nextElementSibling;
  if (existing && existing.classList.contains('job-detail-row')) {
    existing.remove();
    return;
  }

  const detailRow = document.createElement('tr');
  detailRow.className = 'job-detail-row';
  const td = document.createElement('td');
  td.colSpan = 5;
  td.style.padding = '12px 16px';
  td.style.background = 'var(--bg-secondary)';

  let html = `<div style="font-size:0.85rem">
    <strong>Job ID:</strong> ${esc(job.job_id)}<br>
    <strong>Started:</strong> ${fmtDate(job.started_at)}<br>
    <strong>Completed:</strong> ${fmtDate(job.completed_at)}<br>`;

  if (job.error_message) {
    html += `<strong>Error:</strong> <span style="color:var(--error)">${esc(job.error_message)}</span><br>`;
  }

  if (job.result) {
    html += `<strong>Result:</strong> <pre class="mono" style="white-space:pre-wrap;font-size:0.8rem;margin-top:4px">${esc(JSON.stringify(job.result, null, 2))}</pre>`;
  }

  // Link to snapshot for health scan jobs
  if (job.job_type === 'vault_health_scan' && job.status === 'completed') {
    html += `<a href="#/dashboard" style="color:var(--accent)">View Dashboard</a>`;
  }

  html += '</div>';
  td.innerHTML = html;
  detailRow.appendChild(td);
  tr.after(detailRow);
}

function startPoll(container) {
  if (pollTimer) return;
  pollTimer = setInterval(() => loadJobs(container), 5000);
}

function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

function cleanup() {
  stopPoll();
  currentFilters = { status: '', job_type: '' };
}

registerView('jobs', { render, cleanup });
