// AI Chat view: scrollable conversation history, scope selector, source note links.
// History is stored in memory and cleared on page reload.

import { registerView, esc, navigate } from '../app.js';
import { api } from '../api.js';

const messages = [];

async function render(container) {
  container.innerHTML = '';

  const chatWrap = document.createElement('div');
  chatWrap.className = 'chat-container';
  chatWrap.style.background = 'var(--bg-card)';
  chatWrap.style.border = '1px solid var(--border)';
  chatWrap.style.borderRadius = 'var(--radius)';

  // Messages area
  const messagesEl = document.createElement('div');
  messagesEl.className = 'chat-messages';

  if (messages.length === 0) {
    messagesEl.innerHTML = '<div class="empty-state">Ask a question about your vault</div>';
  } else {
    messages.forEach(msg => {
      messagesEl.appendChild(renderMessage(msg));
    });
  }

  chatWrap.appendChild(messagesEl);

  // Input row
  const inputRow = document.createElement('div');
  inputRow.className = 'chat-input-row';

  const scopeSelect = document.createElement('select');
  scopeSelect.innerHTML = '<option value="">All notes</option>';
  scopeSelect.style.maxWidth = '160px';

  // Load folders for scope selector
  try {
    const tree = await api.vaultStructure();
    flattenFolders(tree, '').forEach(f => {
      const opt = document.createElement('option');
      opt.value = f.path;
      opt.textContent = f.name;
      scopeSelect.appendChild(opt);
    });
  } catch (_) {
    // Scope selector is optional; if it fails, just show "All notes"
  }

  const input = document.createElement('input');
  input.type = 'text';
  input.placeholder = 'Ask about your vault...';

  const sendBtn = document.createElement('button');
  sendBtn.className = 'btn btn-primary';
  sendBtn.textContent = 'Send';

  const doSend = async () => {
    const question = input.value.trim();
    if (!question) return;

    // Add user message
    messages.push({ role: 'user', content: question });
    input.value = '';

    // Re-render messages
    messagesEl.innerHTML = '';
    messages.forEach(m => messagesEl.appendChild(renderMessage(m)));
    messagesEl.scrollTop = messagesEl.scrollHeight;

    // Show loading
    const loadingEl = document.createElement('div');
    loadingEl.className = 'chat-msg chat-msg-assistant';
    loadingEl.innerHTML = '<span class="spinner"></span> Thinking...';
    messagesEl.appendChild(loadingEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;

    sendBtn.disabled = true;
    input.disabled = true;

    try {
      const scope = scopeSelect.value || null;
      const result = await api.chat(question, scope);
      messages.push({
        role: 'assistant',
        content: result.answer,
        sources: result.sources || [],
        provider: result.llm_provider,
      });
    } catch (err) {
      messages.push({
        role: 'assistant',
        content: `Error: ${err.message}`,
        sources: [],
        provider: null,
      });
    }

    sendBtn.disabled = false;
    input.disabled = false;
    input.focus();

    // Re-render with response
    messagesEl.innerHTML = '';
    messages.forEach(m => messagesEl.appendChild(renderMessage(m)));
    messagesEl.scrollTop = messagesEl.scrollHeight;
  };

  sendBtn.addEventListener('click', doSend);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') doSend();
  });

  inputRow.append(scopeSelect, input, sendBtn);
  chatWrap.appendChild(inputRow);
  container.appendChild(chatWrap);

  // Scroll to bottom on load
  messagesEl.scrollTop = messagesEl.scrollHeight;
  input.focus();
}

function renderMessage(msg) {
  const el = document.createElement('div');
  el.className = `chat-msg ${msg.role === 'user' ? 'chat-msg-user' : 'chat-msg-assistant'}`;

  if (msg.role === 'user') {
    el.textContent = msg.content;
  } else {
    el.innerHTML = esc(msg.content).replace(/\n/g, '<br>');

    if (msg.sources && msg.sources.length > 0) {
      const sourcesEl = document.createElement('div');
      sourcesEl.className = 'chat-sources';
      sourcesEl.innerHTML = 'Sources: ' + msg.sources.map(s =>
        `<a href="#/notes" data-note="${esc(s)}">${esc(s)}</a>`
      ).join(', ');
      el.appendChild(sourcesEl);
    }

    if (msg.provider) {
      const provEl = document.createElement('div');
      provEl.style.fontSize = '0.75rem';
      provEl.style.color = 'var(--text-secondary)';
      provEl.style.marginTop = '4px';
      provEl.textContent = `via ${msg.provider}`;
      el.appendChild(provEl);
    }
  }

  return el;
}

function flattenFolders(node, prefix) {
  const results = [];
  if (node.path && node.path !== '/') {
    results.push({ name: prefix + node.name, path: node.path });
  }
  if (node.children) {
    const childPrefix = node.path === '/' ? '' : prefix + node.name + '/';
    node.children.forEach(c => {
      results.push(...flattenFolders(c, childPrefix));
    });
  }
  return results;
}

registerView('chat', { render });
