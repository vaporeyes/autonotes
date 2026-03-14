// Notes Browser view: folder tree (left), note list (center), note detail (right).
// Supports AI analysis triggers from the detail panel.

import { registerView, esc, fmtDate } from '../app.js';
import { api } from '../api.js';
import { createFolderTree } from '../components/folder-tree.js';

async function render(container) {
  container.innerHTML = '';

  const layout = document.createElement('div');
  layout.className = 'panel-layout';

  const treePanel = document.createElement('div');
  treePanel.className = 'panel';
  treePanel.innerHTML = '<div class="spinner"></div> Loading folders...';

  const listPanel = document.createElement('div');
  listPanel.className = 'panel';
  listPanel.innerHTML = '<div class="empty-state">Select a folder</div>';

  const detailPanel = document.createElement('div');
  detailPanel.className = 'panel';
  detailPanel.innerHTML = '<div class="empty-state">Select a note</div>';

  layout.append(treePanel, listPanel, detailPanel);
  container.appendChild(layout);

  // Load folder tree
  try {
    const tree = await api.vaultStructure();
    treePanel.innerHTML = '';
    const treeEl = createFolderTree(tree, (path) => loadFolder(path, listPanel, detailPanel));
    treePanel.appendChild(treeEl);
  } catch (err) {
    treePanel.innerHTML = `<div class="banner banner-error">${esc(err.message)}</div>`;
  }
}

async function loadFolder(path, listPanel, detailPanel) {
  listPanel.innerHTML = '<div class="spinner"></div> Loading...';
  detailPanel.innerHTML = '<div class="empty-state">Select a note</div>';

  // Normalize path: remove trailing slash for the API call
  const apiPath = path.replace(/\/$/, '') || '/';

  try {
    const data = await api.folder(apiPath);
    listPanel.innerHTML = '';

    if (data.notes.length === 0) {
      listPanel.innerHTML = '<div class="empty-state">No notes in this folder</div>';
      return;
    }

    data.notes.forEach(note => {
      const item = document.createElement('div');
      item.className = 'note-item';
      item.innerHTML = `
        <div class="note-item-title">${esc(note.title || note.file_path)}</div>
        <div class="note-item-meta">
          ${note.tags.map(t => `<span class="tag">${esc(t)}</span>`).join('')}
          <span>${note.backlink_count} links</span> &middot;
          <span>${note.word_count} words</span>
        </div>`;
      item.addEventListener('click', () => {
        listPanel.querySelectorAll('.note-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        loadNote(note.file_path, detailPanel);
      });
      listPanel.appendChild(item);
    });
  } catch (err) {
    listPanel.innerHTML = `<div class="banner banner-error">${esc(err.message)}</div>`;
  }
}

async function loadNote(path, detailPanel) {
  detailPanel.innerHTML = '<div class="spinner"></div> Loading...';

  try {
    const note = await api.note(path);
    detailPanel.innerHTML = '';

    // Frontmatter
    const fmSection = document.createElement('div');
    fmSection.className = 'detail-section';
    fmSection.innerHTML = `<h4>Frontmatter</h4>
      <pre class="mono" style="white-space:pre-wrap;font-size:0.8rem;color:var(--text-secondary)">${esc(JSON.stringify(note.frontmatter, null, 2))}</pre>`;
    detailPanel.appendChild(fmSection);

    // Headings
    if (note.headings.length > 0) {
      const hSection = document.createElement('div');
      hSection.className = 'detail-section';
      hSection.innerHTML = `<h4>Headings</h4>
        ${note.headings.map(h => `<div style="padding-left:${(h.level - 1) * 12}px;font-size:0.85rem">${'#'.repeat(h.level)} ${esc(h.text)}</div>`).join('')}`;
      detailPanel.appendChild(hSection);
    }

    // Tags
    if (note.tags.length > 0) {
      const tSection = document.createElement('div');
      tSection.className = 'detail-section';
      tSection.innerHTML = `<h4>Tags</h4>
        ${note.tags.map(t => `<span class="tag">${esc(t)}</span>`).join('')}`;
      detailPanel.appendChild(tSection);
    }

    // Backlinks
    if (note.backlinks.length > 0) {
      const bSection = document.createElement('div');
      bSection.className = 'detail-section';
      bSection.innerHTML = `<h4>Backlinks</h4>
        ${note.backlinks.map(b => `<div style="font-size:0.85rem;color:var(--accent)">${esc(b)}</div>`).join('')}`;
      detailPanel.appendChild(bSection);
    }

    // Content hash and metadata
    const meta = document.createElement('div');
    meta.className = 'detail-section';
    meta.innerHTML = `<h4>Metadata</h4>
      <div class="mono" style="font-size:0.8rem">Hash: ${esc(note.content_hash)}</div>
      <div style="font-size:0.8rem;color:var(--text-secondary)">Words: ${note.word_count} | Modified: ${fmtDate(note.last_modified)}</div>`;
    detailPanel.appendChild(meta);

    // AI analysis buttons
    const aiSection = document.createElement('div');
    aiSection.className = 'detail-section';
    aiSection.innerHTML = '<h4>AI Analysis</h4>';

    const actions = ['suggest_tags', 'suggest_backlinks', 'generate_summary'];
    const actionLabels = { suggest_tags: 'Suggest Tags', suggest_backlinks: 'Suggest Backlinks', generate_summary: 'Generate Summary' };

    actions.forEach(action => {
      const btn = document.createElement('button');
      btn.className = 'btn btn-sm';
      btn.style.marginRight = '8px';
      btn.textContent = actionLabels[action];
      btn.addEventListener('click', async () => {
        btn.disabled = true;
        btn.textContent = 'Running...';
        try {
          const result = await api.analyze(path, action);
          btn.textContent = `Job ${result.job_id.slice(0, 8)}...`;
        } catch (err) {
          btn.textContent = 'Error';
          btn.title = err.message;
        }
      });
      aiSection.appendChild(btn);
    });

    detailPanel.appendChild(aiSection);
  } catch (err) {
    detailPanel.innerHTML = `<div class="banner banner-error">${esc(err.message)}</div>`;
  }
}

registerView('notes', { render });
