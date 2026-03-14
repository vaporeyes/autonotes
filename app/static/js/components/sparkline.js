// Renders an SVG sparkline from an array of data points.
// Usage: createSparkline(dataPoints, { width, height })

export function createSparkline(points, opts = {}) {
  const { width = 120, height = 32 } = opts;

  if (!points || points.length < 2) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', width);
    svg.setAttribute('height', height);
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('x', width / 2);
    text.setAttribute('y', height / 2 + 4);
    text.setAttribute('text-anchor', 'middle');
    text.setAttribute('fill', '#a0a0a0');
    text.setAttribute('font-size', '10');
    text.textContent = 'No data';
    svg.appendChild(text);
    return svg;
  }

  const values = points.map(p => typeof p === 'number' ? p : p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const pad = 2;

  const coords = values.map((v, i) => {
    const x = pad + (i / (values.length - 1)) * (width - 2 * pad);
    const y = pad + (1 - (v - min) / range) * (height - 2 * pad);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', width);
  svg.setAttribute('height', height);
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);

  const polyline = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
  polyline.setAttribute('points', coords.join(' '));
  polyline.setAttribute('fill', 'none');
  polyline.setAttribute('stroke', '#4fc3f7');
  polyline.setAttribute('stroke-width', '1.5');
  polyline.setAttribute('stroke-linecap', 'round');
  polyline.setAttribute('stroke-linejoin', 'round');
  svg.appendChild(polyline);

  // Dot on the last point
  const lastCoord = coords[coords.length - 1].split(',');
  const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  dot.setAttribute('cx', lastCoord[0]);
  dot.setAttribute('cy', lastCoord[1]);
  dot.setAttribute('r', '2.5');
  dot.setAttribute('fill', '#4fc3f7');
  svg.appendChild(dot);

  return svg;
}
