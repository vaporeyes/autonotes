// Progress bar component.
// Usage: createProgressBar(current, total) returns a DOM element.

export function createProgressBar(current, total) {
  const pct = total > 0 ? Math.round((current / total) * 100) : 0;

  const wrap = document.createElement('div');
  wrap.style.display = 'flex';
  wrap.style.alignItems = 'center';
  wrap.style.gap = '8px';

  const bar = document.createElement('div');
  bar.className = 'progress-bar';
  bar.style.flex = '1';

  const fill = document.createElement('div');
  fill.className = 'progress-fill';
  fill.style.width = `${pct}%`;
  bar.appendChild(fill);

  const label = document.createElement('span');
  label.style.fontSize = '0.8rem';
  label.style.color = 'var(--text-secondary)';
  label.style.minWidth = '48px';
  label.textContent = `${current}/${total}`;

  wrap.append(bar, label);
  return wrap;
}
