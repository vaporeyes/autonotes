// Folder tree component with expand/collapse behavior.
// Input: VaultStructureNode tree. Output: DOM element with click callbacks.

import { esc } from '../app.js';

export function createFolderTree(node, onSelect) {
  const container = document.createElement('div');
  renderNode(container, node, onSelect, 0, true);
  return container;
}

function renderNode(parent, node, onSelect, depth, startOpen) {
  const hasChildren = node.children && node.children.length > 0;
  const item = document.createElement('div');
  item.className = 'tree-item';
  item.dataset.path = node.path;

  const toggle = document.createElement('span');
  toggle.className = 'tree-toggle';
  toggle.textContent = hasChildren ? (startOpen ? '\u25BE' : '\u25B8') : ' ';
  item.appendChild(toggle);

  const label = document.createElement('span');
  label.textContent = `${node.name} (${node.note_count})`;
  item.appendChild(label);

  item.addEventListener('click', (e) => {
    e.stopPropagation();
    // Toggle children visibility
    if (hasChildren) {
      const childEl = item.nextElementSibling;
      if (childEl && childEl.classList.contains('tree-children')) {
        const isOpen = childEl.style.display !== 'none';
        childEl.style.display = isOpen ? 'none' : 'block';
        toggle.textContent = isOpen ? '\u25B8' : '\u25BE';
      }
    }
    // Select this folder
    parent.querySelectorAll('.tree-item').forEach(i => i.classList.remove('active'));
    document.querySelectorAll('.tree-item').forEach(i => i.classList.remove('active'));
    item.classList.add('active');
    onSelect(node.path);
  });

  parent.appendChild(item);

  if (hasChildren) {
    const childContainer = document.createElement('div');
    childContainer.className = 'tree-children';
    childContainer.style.display = startOpen && depth < 1 ? 'block' : 'none';

    node.children.forEach(child => {
      renderNode(childContainer, child, onSelect, depth + 1, false);
    });
    parent.appendChild(childContainer);
  }
}
