'use strict';
// Recorded original-study results, not a live benchmark. Full-precision source:
// evidence/published_results.json (source CSV and workload identities retained).
const measurements = {
  near: {
    '1': {one: 1.0974095601962073, final: 0.500094223305153, min: 0.4878196500799557, max: 0.5117892177282678},
    '50': {one: 1.094581100419828, final: 0.45614603738881077, min: 0.4466479835158537, max: 0.5028766850002995}
  },
  far: {
    '1': {one: 1.1743287247879834, final: 0.601268846773734, min: 0.60054891153859, max: 0.6887701078481634},
    '50': {one: 1.1206189854316284, final: 0.6550305413453632, min: 0.5863514693944004, max: 0.6672408443373675}
  }
};
const regime = document.getElementById('regime');
const topk = document.getElementById('topk');
function updateResults() {
  const m = measurements[regime.value][topk.value];
  document.getElementById('one-ratio').textContent = m.one.toFixed(3) + '×';
  document.getElementById('final-ratio').textContent = m.final.toFixed(3) + '×';
  document.getElementById('range').textContent = m.min.toFixed(3) + '–' + m.max.toFixed(3);
}
regime.addEventListener('change', updateResults);
topk.addEventListener('change', updateResults);
for (const button of document.querySelectorAll('[data-copy]')) {
  button.addEventListener('click', async () => {
    const value = document.getElementById(button.dataset.copy).textContent;
    const status = document.getElementById('copy-status');
    try {
      await navigator.clipboard.writeText(value);
      const original = button.textContent;
      button.textContent = 'Copied';
      status.textContent = 'Copied to clipboard.';
      setTimeout(() => { button.textContent = original; }, 1800);
    } catch (_) {
      status.textContent = 'Clipboard unavailable. Select and copy the text below.';
      button.textContent = 'Select text below';
    }
  });
}
