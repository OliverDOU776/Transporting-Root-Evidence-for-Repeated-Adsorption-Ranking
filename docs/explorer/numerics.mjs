// Browser demonstrator for the released synthetic PWL corpus.
export function prepareCurve(curve) {
  const {p, q} = curve;
  const prefix = [q[0]];
  for (let i = 1; i < p.length; i++) {
    const delta = p[i] - p[i - 1];
    const slope = (q[i] - q[i - 1]) / delta;
    const intercept = q[i - 1] - slope * p[i - 1];
    prefix.push(prefix[i - 1] + slope * delta + intercept * Math.log1p(delta / p[i - 1]));
  }
  return {p, q, prefix};
}

function spreading(curve, pressure) {
  const {p, q, prefix} = curve;
  if (pressure <= p[0]) return pressure * q[0] / p[0];
  let low = 0;
  let high = p.length - 1;
  while (high - low > 1) {
    const mid = (low + high) >> 1;
    if (p[mid] <= pressure) low = mid;
    else high = mid;
  }
  const delta = pressure - p[low];
  const slope = (q[high] - q[low]) / (p[high] - p[low]);
  return prefix[low] + slope * delta + (q[low] - slope * p[low]) * Math.log1p(delta / p[low]);
}

export function rankPool(curves, pairs, pressure, feed) {
  if (!(pressure > 0 && Number.isFinite(pressure) && feed > 0 && feed < 1)) throw new Error('Enter a positive pressure and a feed fraction between 0 and 1.');
  const a = pressure * feed;
  const b = pressure * (1 - feed);
  const rows = [];
  pairs.forEach(([i, j], id) => {
    const first = curves[i], second = curves[j];
    let low = a / first.p.at(-1), high = 1 - b / second.p.at(-1);
    if (low > high) return;
    const residual = x => spreading(first, a / x) - spreading(second, b / (1 - x));
    if (residual(low) < 0 || residual(high) > 0) return;
    for (let step = 0; step < 64; step++) {
      const mid = (low + high) / 2;
      if (mid === low || mid === high) break;
      if (residual(mid) > 0) low = mid;
      else high = mid;
    }
    const x = (low + high) / 2;
    rows.push({id, i, j, score: (1 - feed) / feed * x / (1 - x)});
  });
  return rows.sort((u, v) => v.score - u.score || u.id - v.id);
}

export function henryBound(pressure, cut) {
  // Equal feed, P0 = 1, x0 = 1/3, finite upper support = 10 for both gases.
  const source = 1 / 3;
  const a = pressure * source, b = 1 - pressure * (1 - source);
  const low = Math.max(pressure / 20, Math.min(a, b));
  const high = Math.min(1 - pressure / 20, Math.max(a, b));
  const scoreUpper = high / (1 - high);
  return {low, high, scoreUpper, xCut: cut / (1 + cut), excluded: scoreUpper < cut - 1e-12};
}
