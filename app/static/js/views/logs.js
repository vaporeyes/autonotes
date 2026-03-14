// Audit Logs view: filterable, paginated log table.
// Supports filtering by target path and operation name.

import { registerView, esc, fmtDate, badgeClass } from '../app.js';
import { api } from '../api.js';

const PAGE_SIZE = 50;
let currentPage = 0;
let currentFilters = { target_path: '', operation_name: '' };

async function render(container) {
  container.innerHTML = '';

  // Filters
  const filters = document.createElement('div');
  filters.className = 'filters';

  const pathInput = document.createElement('input');
  pathInput.placeholder = 'Filter by target path...';
  pathInput.value = currentFilters.target_path;
  pathInput.style.minWidth = '200px';

  const opInput = document.createElement('input');
  opInput.placeholder = 'Filter by operation...';
  opInput.value = currentFilters.operation_name;
  opInput.style.minWidth = '200px';

  const filterBtn = document.createElement('button');
  filterBtn.className = 'btn';
  filterBtn.textContent = 'Filter';
  filterBtn.addEventListener('click', () => {
    currentFilters.target_path = pathInput.value.trim();
    currentFilters.operation_name = opInput.value.trim();
    currentPage = 0;
    loadLogs(container);
  });

  // Allow Enter key to trigger filter
  [pathInput, opInput].forEach(el => {
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') filterBtn.click();
    });
  });

  filters.append(pathInput, opInput, filterBtn);
  container.appendChild(filters);

  const tableWrap = document.createElement('div');
  tableWrap.id = 'logs-table';
  container.appendChild(tableWrap);

  const paginationEl = document.createElement('div');
  paginationEl.id = 'logs-pagination';
  paginationEl.className = 'pagination';
  container.appendChild(paginationEl);

  await loadLogs(container);
}

async function loadLogs(container) {
  const tableWrap = container.querySelector('#logs-table');
  const paginationEl = container.querySelector('#logs-pagination');
  if (!tableWrap) return;

  tableWrap.innerHTML = '<div class="spinner"></div> Loading...';
  paginationEl.innerHTML = '';

  try {
    const params = { limit: PAGE_SIZE };
    if (currentFilters.target_path) params.target_path = currentFilters.target_path;
    if (currentFilters.operation_name) params.operation_name = currentFilters.operation_name;

    const data = await api.logs(params);
    tableWrap.innerHTML = '';

    if (data.logs.length === 0) {
      tableWrap.innerHTML = '<div class="empty-state">No log entries found</div>';
      return;
    }

    const table = document.createElement('table');
    table.innerHTML = `<thead><tr>
      <th>Target Path</th>
      <th>Operation</th>
      <th>Status</th>
      <th>Timestamp</th>
    </tr></thead>`;

    const tbody = document.createElement('tbody');
    // Slice for current page
    const start = currentPage * PAGE_SIZE;
    const pageItems = data.logs.slice(start, start + PAGE_SIZE);

    pageItems.forEach(log => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="mono" style="font-size:0.8rem">${esc(log.target_path || '-')}</td>
        <td>${esc(log.operation_name)}</td>
        <td><span class="badge ${badgeClass(log.status)}">${esc(log.status)}</span></td>
        <td style="font-size:0.8rem">${fmtDate(log.created_at)}</td>`;
      tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    tableWrap.appendChild(table);

    // Pagination
    const totalPages = Math.ceil(data.total / PAGE_SIZE);
    if (totalPages > 1) {
      const prevBtn = document.createElement('button');
      prevBtn.className = 'btn btn-sm';
      prevBtn.textContent = 'Previous';
      prevBtn.disabled = currentPage === 0;
      prevBtn.addEventListener('click', () => {
        currentPage = Math.max(0, currentPage - 1);
        loadLogs(container);
      });

      const pageInfo = document.createElement('span');
      pageInfo.textContent = `Page ${currentPage + 1} of ${totalPages} (${data.total} total)`;

      const nextBtn = document.createElement('button');
      nextBtn.className = 'btn btn-sm';
      nextBtn.textContent = 'Next';
      nextBtn.disabled = currentPage >= totalPages - 1;
      nextBtn.addEventListener('click', () => {
        currentPage = Math.min(totalPages - 1, currentPage + 1);
        loadLogs(container);
      });

      paginationEl.append(prevBtn, pageInfo, nextBtn);
    }
  } catch (err) {
    tableWrap.innerHTML = `<div class="banner banner-error">${esc(err.message)}</div>`;
  }
}

function cleanup() {
  currentPage = 0;
  currentFilters = { target_path: '', operation_name: '' };
}

registerView('logs', { render, cleanup });
