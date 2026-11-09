import { prepareCurve, rankPool, henryBound } from "./numerics.mjs";

const get = (id) => document.getElementById(id);
const number = (value, digits = 3) =>
  Number(value).toLocaleString("en-US", { maximumFractionDigits: digits });
const accent = "#187f79",
  green = "#4b72ac",
  grid = "#e0e6ea";
const width = 590,
  height = 240,
  left = 56,
  right = 562,
  top = 22,
  bottom = 170;
let corpus, curves, nativeQueries, measurements, results, lastQuery;
function line(x1, y1, x2, y2, color = grid, weight = 1, dash = "") {
  return (
    '<line x1="' +
    x1 +
    '" y1="' +
    y1 +
    '" x2="' +
    x2 +
    '" y2="' +
    y2 +
    '" stroke="' +
    color +
    '" stroke-width="' +
    weight +
    '" stroke-dasharray="' +
    dash +
    '"/>'
  );
}
function label(x, y, value, anchor = "start", fill = "#40413a") {
  return (
    '<text x="' +
    x +
    '" y="' +
    y +
    '" text-anchor="' +
    anchor +
    '" fill="' +
    fill +
    '" font-size="14">' +
    value +
    "</text>"
  );
}
function point(x, y, color, radius = 5) {
  return (
    '<circle cx="' +
    x +
    '" cy="' +
    y +
    '" r="' +
    radius +
    '" fill="' +
    color +
    '"/>'
  );
}
function draw(id, title, content) {
  get(id).innerHTML =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' +
    width +
    " " +
    height +
    '" role="img" aria-label="' +
    title +
    '">' +
    content +
    "</svg>";
}
function showPair(row) {
  get("pair-title").textContent = "Isotherms for pair " + row.id;
  get("pair-meta").textContent =
    "Gas 1 · curve " + row.i + "   /   Gas 2 · curve " + row.j + "   /   Selectivity " + number(row.score, 4);
  for (const tr of get("ranks").rows) {
    const selected = Number(tr.dataset.id) === row.id;
    tr.classList.toggle("selected", selected);
    tr.querySelector("button").setAttribute("aria-pressed", String(selected));
  }
  const pair = [curves[row.i], curves[row.j]];
  const maxQ = Math.max(...pair.flatMap((c) => c.q));
  const x = (p) => left + ((Math.log10(p) + 3) / 5) * (right - left);
  const y = (q) => bottom - (q / maxQ) * (bottom - top);
  let chart = "";
  for (let n = 0; n <= 3; n++) {
    const q = (n * maxQ) / 3;
    chart +=
      line(left, y(q), right, y(q)) +
      label(left - 8, y(q) + 4, number(q, 2), "end");
  }
  for (const p of [0.001, 0.01, 0.1, 1, 10, 100]) {
    chart += label(x(p), bottom + 20, String(p), "middle");
  }
  for (const [index, c] of pair.entries()) {
    const points = c.p.map((p, i) => x(p) + "," + y(c.q[i])).join(" ");
    chart +=
      '<polyline fill="none" stroke="' +
      [accent, green][index] +
      '" stroke-width="2.5" points="' +
      points +
      '"/>';
    chart += c.p
      .filter((_, i) => i % 5 === 0)
      .map((p, i) => point(x(p), y(c.q[i * 5]), [accent, green][index], 2.8))
      .join("");
  }
  chart +=
    label(left, 15, "Uptake") +
    label(
      (left + right) / 2,
      215,
      "Pure pressure · logarithmic scale",
      "middle",
    );
  chart +=
    label(left, 237, "Gas 1", "start", accent) +
    label(left + 65, 237, "Gas 2", "start", green);
  draw(
    "curves",
    "Pure gas uptake against log pressure for pair " + row.id,
    chart,
  );
}
function runQuery(event) {
  event?.preventDefault();
  const form = get("query"),
    args = new FormData(form);
  const pressure = Number(args.get("pressure")),
    feed = Number(args.get("feed")),
    k = Number(args.get("k"));
  results = rankPool(curves, corpus.pairs, pressure, feed);
  lastQuery = { pressure, feed, k };
  get("export-results").disabled = results.length === 0;
  get("export-status").textContent = "";
  get("query-meta").textContent =
    results.length +
    " supported / " +
    corpus.pairs.length +
    " pairs · P = " +
    pressure +
    " · y = " +
    feed;
  const shown = results.slice(0, k);
  get("ranks").innerHTML = shown
    .map(
      (r, i) =>
        '<tr data-id="' +
        r.id +
        '"><td>' +
        String(i + 1).padStart(2, "0") +
        '</td><td><button type="button" aria-label="Inspect pair ' +
        r.id +
        '">' +
        r.id +
        "</button></td><td>" +
        number(r.score, 4) +
        "</td></tr>",
    )
    .join("");
  const ref = nativeQueries.find(
    (q) => q.pressure === pressure && q.feed === feed,
  );
  const match =
    ref &&
    ref.winner_ids.every(
      (id, i) =>
        results[i]?.id === id &&
        Math.abs(results[i].score - ref.scores[i]) <=
          1e-8 * Math.max(1, ref.scores[i]),
    );
  get("match").textContent = ref
    ? match
      ? "First five IDs and scores agree with the native reference."
      : "Native reference differs for this state."
    : "Computed in this browser using double-precision bisection.";
  get("query-summary").innerHTML = shown.length
    ? "<strong>Query complete.</strong> Showing top " + shown.length + " of " + results.length + " supported pairs. Highest selectivity: <strong>" + number(shown[0].score, 4) + "</strong> (pair " + shown[0].id + ")."
    : "No supported pairs at this condition. Try another pressure or feed fraction.";
  if (shown.length) showPair(shown[0]);
  else {
    get("pair-title").textContent = "Pure-gas isotherms";
    get("pair-meta").textContent = "No supported pairs at this state.";
    get("curves").replaceChildren();
  }
}
function exportResults() {
  if (!results?.length || !lastQuery) return;
  const shown = results.slice(0, lastQuery.k);
  const header = "rank,pair_id,gas1_curve,gas2_curve,selectivity,pressure,gas1_feed_fraction,dataset";
  const lines = shown.map((r, i) => [i + 1, r.id, r.i, r.j, r.score, lastQuery.pressure, lastQuery.feed, "synthetic_144_pairs"].join(","));
  const blob = new Blob([header + "\n" + lines.join("\n") + "\n"], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "adsorption-shortlist-P" + lastQuery.pressure + "-y" + lastQuery.feed + ".csv";
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  get("export-status").textContent = "CSV download started: " + shown.length + " pairs with their scores and query conditions.";
}
function updateBounds() {
  const pressure = Number(get("dest").value),
    cut = get("cut");
  get("dest-out").value = pressure.toFixed(2);
  if (!cut.checkValidity() || !cut.value) {
    get("verdict").textContent = "Enter a cutoff from 0.05 to 10.";
    get("bound-plot").replaceChildren();
    return;
  }
  const b = henryBound(pressure, Number(cut.value));
  const x = (n) => left + (right - left) * n;
  let chart = line(left, 145, right, 145);
  for (const n of [0, 0.25, 0.5, 0.75, 1])
    chart += line(x(n), 140, x(n), 151) + label(x(n), 172, String(n), "middle");
  chart +=
    line(x(b.low), 99, x(b.high), 99, green, 8) +
    point(x(b.low), 99, green) +
    point(x(b.high), 99, green);
  chart += label(
    (x(b.low) + x(b.high)) / 2,
    78,
    "[" + b.low.toFixed(3) + ", " + b.high.toFixed(3) + "]",
    "middle",
    green,
  );
  chart +=
    line(x(b.xCut), 55, x(b.xCut), 145, accent, 2, "5 4") +
    label(x(b.xCut), 42, "Cut " + b.xCut.toFixed(3), "middle", accent);
  chart +=
    point(x(1 / 3), 145, "#252622") +
    label((left + right) / 2, 215, "Adsorbed mole fraction", "middle");
  draw("bound-plot", "Transported enclosure and ranking cutoff", chart);
  get("verdict").dataset.outcome = b.excluded ? "exclude" : "refine";
  get("verdict").innerHTML =
    "<strong>" +
    (b.excluded ? "Exclude pair" : "Refine pair") +
    "</strong> · Score upper bound " +
    b.scoreUpper.toFixed(3) +
    (b.excluded ? " < " : " ≥ ") +
    number(Number(cut.value)) +
    ". " + (b.excluded ? "No fresh integral evaluation is needed for this exclusion." : "The bound cannot decide; a fresh numerical test is needed.");
}
function updateCosts() {
  const prefix = Number(get("prefix").value);
  const rows = measurements
    .filter(
      (r) =>
        r.dataset === get("relation").value &&
        r.regime === get("regime").value &&
        r.k === get("cost-k").value,
    )
    .sort((a, b) => a.queries - b.queries);
  const selected = rows.find((r) => Number(r.queries) === prefix);
  const values = [0, 1, 2].map((i) =>
    Number(selected["paid_ratio_block_" + i]),
  );
  get("blocks").innerHTML = values
    .map(
      (v, i) =>
        "<tr><td>" +
        String(i + 1).padStart(2, "0") +
        "</td><td>" +
        v.toFixed(3) +
        "</td></tr>",
    )
    .join("");
  get("cost-meta").textContent =
    number(Number(selected.pool_size)) +
    " pairs · " +
    prefix +
    " queries · 298 K";
  get("cost-note").textContent =
    "Median " +
    Number(selected.median_paid_ratio).toFixed(3) +
    " · Transport faster in " +
    selected.faster_blocks +
    " of 3 blocks.";
  const ratio = Number(selected.median_paid_ratio);
  get("cost-value").innerHTML = ratio < 1
    ? "<strong>At this horizon, reuse pays off.</strong> The median paired paid-time ratio is " + ratio.toFixed(3) + "; Transport uses about " + Math.round((1 - ratio) * 100) + "% less paid time than LeanCap. Inspect the three blocks above for variation."
    : "<strong>At this horizon, reuse does not reduce median paid time.</strong> The median paired ratio is " + ratio.toFixed(3) + ". Preparation and acquisition can outweigh the saved numerical work; try a longer horizon to inspect the trade-off.";
  const min =
    Math.floor(Math.min(1, ...rows.map((r) => Number(r.min_paid_ratio))) * 4) /
    4;
  const max =
    Math.ceil(Math.max(1, ...rows.map((r) => Number(r.max_paid_ratio))) * 4) /
    4;
  const y = (value) => bottom - ((value - min) / (max - min)) * (bottom - top);
  let chart = "";
  for (const tick of [...new Set([min, 1, max])])
    chart +=
      line(
        left,
        y(tick),
        right,
        y(tick),
        tick === 1 ? "#77786b" : grid,
        1,
        tick === 1 ? "5 3" : "",
      ) + label(left - 9, y(tick) + 5, tick.toFixed(2), "end");
  rows.forEach((r, i) => {
    const x = left + 24 + (i * (right - left - 48)) / 4,
      color = Number(r.queries) === prefix ? accent : "#697a70";
    const lo = y(Number(r.min_paid_ratio)),
      hi = y(Number(r.max_paid_ratio));
    chart +=
      line(x, lo, x, hi, color, 2) +
      line(x - 6, lo, x + 6, lo, color, 2) +
      line(x - 6, hi, x + 6, hi, color, 2) +
      point(
        x,
        y(Number(r.median_paid_ratio)),
        color,
        Number(r.queries) === prefix ? 7 : 4,
      );
    chart += label(x, bottom + 24, r.queries, "middle", color);
  });
  draw(
    "cost-plot",
    "Paid-time ratios at measured query prefixes",
    chart + label((left + right) / 2, 221, "Query prefix", "middle"),
  );
}
function selectView() {
  const hash = location.hash.slice(1);
  const view = ["ranking", "bounds", "cost"].includes(hash) ? hash : "ranking";
  for (const section of document.querySelectorAll("main > section"))
    section.hidden = section.id !== view;
  for (const a of document.querySelectorAll("nav a")) {
    if (a.hash === "#" + view) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  }
}
async function loadJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error("Could not load " + url);
  return response.json();
}
try {
  const [native, times] = await Promise.all([
    loadJson("../media/query-replay-data.json"),
    loadJson("measurements.json"),
  ]);
  corpus = native.corpus;
  nativeQueries = native.queries;
  measurements = times;
  curves = corpus.curves.map(prepareCurve);
  get("query").addEventListener("submit", runQuery);
  get("export-results").addEventListener("click", exportResults);
  get("ranks").addEventListener("click", (e) => {
    const button = e.target.closest("button");
    if (button)
      showPair(
        results.find((r) => r.id === Number(button.closest("tr").dataset.id)),
      );
  });
  for (const id of ["dest", "cut"])
    get(id).addEventListener("input", updateBounds);
  for (const id of ["relation", "regime", "cost-k", "prefix"])
    get(id).addEventListener("change", updateCosts);
  get("load").hidden = true;
  runQuery();
  updateBounds();
  updateCosts();
  selectView();
  window.addEventListener("hashchange", selectView);
} catch (error) {
  get("load").hidden = false;
  get("load").textContent =
    "The explorer could not load. Refresh the page to retry.";
  console.error(error);
}
