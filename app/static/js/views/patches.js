// Patches & Approvals view: pending patches with approve/reject, collapsible history.
// Uses confirmation dialogs before approve/reject actions.

import { registerView, esc, fmtDate, badgeClass, confirm } from '../app.js';
import { api } from '../api.js';

async function render(container) {
  container.innerHTML = '<div class="spinner"></div> Loading patches...';

  try {
    const [pendingData, allData] = await Promise.all([
      api.patches({ status: 'pending_approval', limit: 100 }),
      api.patches({ limit: 200 }),
    ]);

    container.innerHTML = '';

    // Pending patches section
    const pendingSection = document.createElement('div');
    pendingSection.innerHTML = `<h3 style="margin-bottom:12px">Pending Approval (${pendingData.total})</h3>`;

    if (pendingData.patches.length === 0) {
      pendingSection.innerHTML += '<div class="empty-state">No patches pending approval</div>';
    } else {
      const table = createPatchTable(pendingData.patches, true, container);
      pendingSection.appendChild(table);
    }
    container.appendChild(pendingSection);

    // History section (collapsible)
    const historyPatches = allData.patches.filter(p => p.status !== 'pending_approval');
    const historySection = document.createElement('div');
    historySection.style.marginTop = '24px';

    const header = document.createElement('div');
    header.className = 'collapsible-header';
    header.textContent = `\u25B8 History (${historyPatches.length} patches)`;
    header.addEventListener('click', () => {
      const body = historySection.querySelector('.collapsible-body');
      const isOpen = body.classList.toggle('open');
      header.textContent = `${isOpen ? '\u25BE' : '\u25B8'} History (${historyPatches.length} patches)`;
    });
    historySection.appendChild(header);

    const body = document.createElement('div');
    body.className = 'collapsible-body';
    if (historyPatches.length === 0) {
      body.innerHTML = '<div class="empty-state">No patch history</div>';
    } else {
      body.appendChild(createPatchTable(historyPatches, false, container));
    }
    historySection.appendChild(body);
    container.appendChild(historySection);

  } catch (err) {
    container.innerHTML = `<div class="banner banner-error">Failed to load patches: ${esc(err.message)}</div>`;
  }
}

function createPatchTable(patches, showActions, rootContainer) {
  const wrap = document.createElement('div');
  wrap.className = 'table-wrap';

  const table = document.createElement('table');
  table.innerHTML = `<thead><tr>
    <th>Target</th>
    <th>Operation</th>
    <th>Payload</th>
    <th>Status</th>
    <th>Risk</th>
    <th>Created</th>
    ${showActions ? '<th>Actions</th>' : ''}
  </tr></thead>`;

  const tbody = document.createElement('tbody');
  patches.forEach(p => {
    const tr = document.createElement('tr');
    const payloadStr = JSON.stringify(p.payload);
    const shortPayload = payloadStr.length > 60 ? payloadStr.slice(0, 60) + '...' : payloadStr;

    tr.innerHTML = `
      <td class="mono" style="font-size:0.8rem">${esc(p.target_path)}</td>
      <td>${esc(p.operation_type)}</td>
      <td class="mono" style="font-size:0.8rem" title="${esc(payloadStr)}">${esc(shortPayload)}</td>
      <td><span class="badge ${badgeClass(p.status)}">${esc(p.status)}</span></td>
      <td><span class="badge ${badgeClass(p.risk_level)}">${esc(p.risk_level)}</span></td>
      <td style="font-size:0.8rem">${fmtDate(p.created_at)}</td>`;

    if (showActions) {
      const td = document.createElement('td');
      const approveBtn = document.createElement('button');
      approveBtn.className = 'btn btn-success btn-sm';
      approveBtn.textContent = 'Approve';
      approveBtn.style.marginRight = '4px';
      approveBtn.addEventListener('click', async () => {
        const ok = await confirm('Approve Patch', `Approve ${p.operation_type} on ${p.target_path}?`);
        if (!ok) return;
        approveBtn.disabled = true;
        try {
          await api.approvePatch(p.patch_id);
          render(rootContainer);
        } catch (err) {
          alert('Error: ' + err.message);
          approveBtn.disabled = false;
        }
      });

      const rejectBtn = document.createElement('button');
      rejectBtn.className = 'btn btn-danger btn-sm';
      rejectBtn.textContent = 'Reject';
      rejectBtn.addEventListener('click', async () => {
        const ok = await confirm('Reject Patch', `Reject ${p.operation_type} on ${p.target_path}?`);
        if (!ok) return;
        rejectBtn.disabled = true;
        try {
          await api.rejectPatch(p.patch_id);
          render(rootContainer);
        } catch (err) {
          alert('Error: ' + err.message);
          rejectBtn.disabled = false;
        }
      });

      td.append(approveBtn, rejectBtn);
      tr.appendChild(td);
    }

    tbody.appendChild(tr);
  });

  table.appendChild(tbody);
  wrap.appendChild(table);
  return wrap;
}

registerView('patches', { render });
