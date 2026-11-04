"""
Builds a page that shows the tracker benchmarks (test_tracker_scenarios and test_tracker_muddy)
for several tracking engines side by side: for every scenario, a player that steps through the
clip with the true ball position and each engine's position drawn on it, an error-over-time chart
(frames where the ball is hidden are shaded), and each engine's scores against the target.

    uv run python -m tests.benchmark_report                      # writes temp/benchmark_report.html
    uv run python -m tests.benchmark_report some/place.html
    uv run python -m tests.benchmark_report --engines nanotrack,trackpy --settings temp/tuned_blob_settings.json

The page is one file with the frames embedded, so it opens anywhere. Frames are every fourth one,
scaled down; the charts and scores use every frame.
"""

import argparse
import base64
import json
import os
from concurrent.futures import ProcessPoolExecutor

import cv2

from tests import harness as h
h.setup_env()

from tests import test_tracker_muddy as muddy  # noqa: E402
from tests import test_tracker_scenarios as clean  # noqa: E402

N = clean.N
STEP = 4                 # One frame in four is embedded
SHOT = (320, 240)        # Embedded frame size
ENGINE_NAMES = {"nanotrack": "NanoTrack", "vittrack": "ViTTrack", "trackpy": "trackpy blob tracker"}
BLURBS = {
    "white, clean": "A dark red ball loops across a white screen. Nothing else is in the picture.",
    "white, small and fast": "A small ball (7 px radius) bounces off the edges at 9 px per frame.",
    "white, still shapes": "Five coloured shapes stand on the white screen, and the ball passes by them.",
    "paper wall, moving shapes": "An off-white wall with shading and camera noise. Five shapes drift around.",
    "paper wall, look-alike ball": "The same wall, with two decoy balls of the same colour moving across the ball's path.",
    "noise background": "Random grey pixels everywhere, a dark ball, and shapes drifting past.",
    "camouflage background": "Green, brown and tan blobs. The ball is painted in the camouflage's own green.",
    "camouflage, fine pattern, look-alikes": "Small camouflage blobs about the ball's size, three same-coloured decoys, noise and flicker.",
    "camouflage, fast, occluders": "A fast ball (13 px per frame) on camouflage, two decoys, and large shapes that pass in front of it.",
    "dropped by a hand": "A small dark ball held by a hand, then dropped. It falls and bounces, and the hand moves away.",
}


def _scenario(group, i):
    return (muddy.build_scenarios() if group == "dirty or covered" else clean.build_scenarios())[i]


def _frames(arg):
    group, i = arg
    scn = _scenario(group, i)
    out = []
    for t in range(0, N, STEP):
        small = cv2.resize(scn.frame(t), SHOT, interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 50])
        out.append("data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode())
    return out


def _run(arg):
    group, i, engine, settings = arg
    import warnings
    warnings.filterwarnings("ignore")
    from experiments.rigid.blobtracker import BlobSettings
    scn = _scenario(group, i)
    tr = clean.trace(scn, engine, BlobSettings.from_dict(settings) if settings else None)
    res = muddy.analyse(scn, tr)
    target = scn.target
    limit = target[3] if len(target) > 3 else muddy.RECOVERY_LIMIT
    meets = (res.median <= target[0] and res.p95 <= target[1] and res.on_ball >= target[2]
             and (res.recovery is None or res.recovery <= limit))
    rec = None if res.recovery is None else (-1 if res.recovery == float("inf") else int(res.recovery))
    return {
        "centre": [[round(float(x), 1), round(float(y), 1)] for x, y in tr.centre],
        "lost": [bool(v) for v in tr.lost],
        "error": [round(float(e), 2) for e in tr.error],
        "stats": {"median": res.median, "p95": res.p95, "onBall": res.on_ball, "lost": res.lost,
                  "worst": res.worst, "firstMiss": res.first_miss, "recovery": rec,
                  "meets": bool(meets), "ms": tr.ms_per_frame},
    }


def collect(engines, settings, jobs) -> list:
    keys = [("dirty or covered", i) for i in range(len(muddy.build_scenarios()))] + \
           [("clean", i) for i in range(len(clean.build_scenarios()))]
    runs = [(g, i, e, settings if e == "trackpy" else None) for g, i in keys for e in engines]
    with ProcessPoolExecutor(jobs) as ex:
        frames = ex.map(_frames, keys)
        traced = ex.map(_run, runs)
        frames, traced = list(frames), list(traced)
    out = []
    for k, (group, i) in enumerate(keys):
        scn = _scenario(group, i)
        target = scn.target
        hidden = [scn.cover(t) >= 0.5 if hasattr(scn, "cover") else False for t in range(N)]
        out.append({
            "name": scn.name, "group": group, "tier": scn.tier, "radius": scn.radius,
            "blurb": getattr(scn, "blurb", "") or BLURBS.get(scn.name, ""),
            "target": {"median": target[0], "p95": target[1], "onBall": target[2],
                       "recovery": target[3] if len(target) > 3 else None},
            "truth": [[round(float(x), 1), round(float(y), 1)] for x, y in (scn.truth(t) for t in range(N))],
            "hidden": hidden, "frames": frames[k],
            "engines": {e: traced[k * len(engines) + j] for j, e in enumerate(engines)},
        })
        print(f"  {scn.name}: " + ", ".join(
            f"{e} {out[-1]['engines'][e]['stats']['onBall']:.0%}" for e in engines), flush=True)
    return out


PAGE = r"""<title>Tracker Benchmark</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600&family=JetBrains+Mono:wght@400;500&family=Source+Sans+3:wght@400;600&display=swap">
<style>
/* Layout: header with legend, one summary table (an engine per column group), then a grid of
   players, one per scenario. Overlay colours are fixed so they read on any footage. */
:root {
  --bg: #f2f4f1; --surface: #ffffff; --ink: #16201c; --muted: #58645e; --line: #d6dcd7;
  --accent: #2749c4; --good: #0b7a57; --good-bg: #dcf1e7; --warn: #a8480a; --warn-bg: #fbe6d3;
  --track: #e6ebe7; --hidden: rgba(90, 100, 96, .16);
  --display: "Barlow Condensed", "Arial Narrow", sans-serif;
  --body: "Source Sans 3", system-ui, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #0e1411; --surface: #161d19; --ink: #e6ece8; --muted: #98a49d; --line: #28322d;
  --accent: #86a4ff; --good: #55d4a5; --good-bg: #12342a; --warn: #f2a560; --warn-bg: #3b2615;
  --track: #222b26; --hidden: rgba(200, 210, 205, .10); color-scheme: dark; } }
:root[data-theme="dark"] {
  --bg: #0e1411; --surface: #161d19; --ink: #e6ece8; --muted: #98a49d; --line: #28322d;
  --accent: #86a4ff; --good: #55d4a5; --good-bg: #12342a; --warn: #f2a560; --warn-bg: #3b2615;
  --track: #222b26; --hidden: rgba(200, 210, 205, .10); color-scheme: dark; }
body { background: var(--bg); color: var(--ink); font-family: var(--body); font-size: 15px; line-height: 1.5;
  padding-block: 28px 56px; padding-left: max(16px, env(safe-area-inset-left, 0px));
  padding-right: max(16px, env(safe-area-inset-right, 0px)); margin: 0; }
.wrap { max-width: 1180px; margin: 0 auto; display: grid; gap: 28px; }
.eyebrow { font-family: var(--mono); font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }
h1 { font-family: var(--display); font-weight: 600; font-size: clamp(38px, 7vw, 60px); line-height: 1; margin: 6px 0 10px; text-wrap: balance; }
h3 { font-family: var(--display); font-weight: 600; font-size: 26px; margin: 8px 0 0; }
.lede { max-width: 66ch; color: var(--muted); margin: 0; }
.legend { display: flex; flex-wrap: wrap; gap: 8px 22px; margin-top: 16px; align-items: center; font-size: 14px; }
.legend span { display: inline-flex; gap: 8px; align-items: center; }
.sw { width: 14px; height: 14px; display: inline-block; box-shadow: 0 0 0 1.5px #000; }
.sw.ring { border-radius: 50%; border: 2px solid #7cff00; box-shadow: 0 0 0 1.5px #000; background: none; }
.sw.hid { background: var(--hidden); box-shadow: none; border: 1px solid var(--line); }
button { font: inherit; cursor: pointer; }
.btn { background: var(--ink); color: var(--bg); border: 0; border-radius: 6px; padding: 7px 14px; font-weight: 600; }
.btn:focus-visible, .slider:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.tablewrap { overflow-x: auto; background: var(--surface); border: 1px solid var(--line); border-radius: 8px; }
table { border-collapse: collapse; width: 100%; min-width: 720px; font-size: 14px; }
th { text-align: left; font-weight: 600; color: var(--muted); font-size: 12px; letter-spacing: .05em; text-transform: uppercase; padding: 9px 10px; border-bottom: 1px solid var(--line); white-space: nowrap; }
th.eng { text-align: center; border-left: 1px solid var(--line); }
td { padding: 8px 10px; border-bottom: 1px solid var(--line); }
td.first { border-left: 1px solid var(--line); }
tr.group td { font-family: var(--mono); font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); background: var(--bg); }
tr:last-child td { border-bottom: 0; }
td.num { text-align: right; font-family: var(--mono); font-variant-numeric: tabular-nums; white-space: nowrap; }
.bar { display: inline-block; vertical-align: middle; width: 54px; height: 7px; background: var(--track); border-radius: 4px; margin-right: 6px; overflow: hidden; }
.bar i { display: block; height: 100%; background: var(--good); }
.bar.bad i { background: var(--warn); }
.pct { font-family: var(--mono); font-variant-numeric: tabular-nums; }
.pill { display: inline-block; font-size: 12px; font-weight: 600; padding: 2px 9px; border-radius: 99px; white-space: nowrap; }
.pill.ok { background: var(--good-bg); color: var(--good); }
.pill.weak { background: var(--warn-bg); color: var(--warn); }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 460px), 1fr)); gap: 18px; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 14px; display: grid; gap: 10px; min-width: 0; }
.card header { display: flex; flex-wrap: wrap; gap: 6px 10px; align-items: baseline; justify-content: space-between; }
.card h2 { font-family: var(--display); font-weight: 600; font-size: 22px; line-height: 1.1; margin: 0; }
.blurb { color: var(--muted); font-size: 14px; margin: 0; }
canvas { display: block; width: 100%; height: auto; border-radius: 4px; }
canvas.view { background: #888; aspect-ratio: 4 / 3; }
.controls { display: flex; align-items: center; gap: 10px; }
.controls .btn { padding: 4px 12px; min-width: 66px; }
.slider { flex: 1; min-width: 0; accent-color: var(--accent); }
.now { font-family: var(--mono); font-size: 12px; color: var(--muted); white-space: nowrap; font-variant-numeric: tabular-nums; }
.estats { display: grid; gap: 4px; font-size: 13px; }
.estats div { display: flex; flex-wrap: wrap; gap: 4px 14px; align-items: baseline; }
.estats b { font-weight: 600; min-width: 10.5em; display: inline-flex; gap: 6px; align-items: center; }
.estats span { font-family: var(--mono); font-variant-numeric: tabular-nums; }
.over { color: var(--warn); }
.note { font-size: 13px; color: var(--muted); margin: 0; }
</style>
<div class="wrap">
  <header>
    <div class="eyebrow"><span id="count"></span> scenarios · 120 frames each · 640 × 480 · <span id="engines"></span></div>
    <h1>Tracker benchmark</h1>
    <p class="lede">Each clip is drawn with a known ball path. The ball is selected on the first frame with the circle tool's bounding square, then tracked. Each engine's centre is compared with the true centre on every frame. Scores count only frames where the ball can be seen (less than half covered); after a cover, "back after" is how many frames the engine needs to be on the ball again.</p>
    <div class="legend" id="legend"></div>
  </header>
  <section class="tablewrap"><table id="summary"></table></section>
  <h3>Every run</h3>
  <section class="cards" id="cards"></section>
</div>
<script>
const DATA = __DATA__;
const N = 120, STEP = 4, SRC_W = 640;
const ENGINES = Object.keys(DATA[0].engines);
const NAMES = {nanotrack: 'NanoTrack', vittrack: 'ViTTrack', trackpy: 'trackpy blob tracker'};
const COLOURS = {nanotrack: '#ff2bd6', vittrack: '#ffb000', trackpy: '#00c8ff'};
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const fmt = (v, d = 2) => v.toFixed(d);
const back = st => st.recovery === null ? '–' : st.recovery < 0 ? 'never' : st.recovery + ' fr';
document.getElementById('count').textContent = DATA.length;
document.getElementById('engines').textContent = ENGINES.map(e => NAMES[e]).join(' vs ');
document.getElementById('legend').innerHTML =
  '<span><i class="sw ring"></i> true ball position</span>' +
  ENGINES.map(e => '<span><i class="sw" style="background:' + COLOURS[e] + '"></i> ' + NAMES[e] + '</span>').join('') +
  '<span><i class="sw hid"></i> ball hidden (chart)</span>' +
  '<button class="btn" id="playall">Play all</button>';

// Summary table: per engine, on-ball, median, back after a cover, and whether it meets the target
const sum = document.getElementById('summary');
let html = '<thead><tr><th rowspan="2">Scenario</th>' + ENGINES.map(e =>
  '<th class="eng" colspan="4" style="color:' + COLOURS[e] + '">' + NAMES[e] + '</th>').join('') + '</tr><tr>' +
  ENGINES.map(() => '<th style="border-left:1px solid var(--line)">On ball</th><th class="num">Median</th><th class="num">Back</th><th class="num">ms/fr</th>').join('') +
  '</tr></thead><tbody>';
let group = null;
const totals = Object.fromEntries(ENGINES.map(e => [e, 0]));
DATA.forEach(s => {
  if (s.group !== group) { group = s.group; html += '<tr class="group"><td colspan="' + (1 + 4 * ENGINES.length) + '">' + group + '</td></tr>'; }
  html += '<tr><td>' + s.name + '</td>' + ENGINES.map(e => {
    const st = s.engines[e].stats, bad = st.onBall < s.target.onBall;
    if (st.meets) totals[e]++;
    return '<td class="first"><span class="bar' + (bad ? ' bad' : '') + '"><i style="width:' + (st.onBall * 100) + '%"></i></span>' +
      '<span class="pct">' + Math.round(st.onBall * 100) + '%</span>' + (st.meets ? ' ✓' : '') + '</td>' +
      '<td class="num' + (st.median > s.target.median ? ' over' : '') + '">' + fmt(st.median, 1) + '</td>' +
      '<td class="num' + (st.recovery !== null && (st.recovery < 0 || st.recovery > s.target.recovery) ? ' over' : '') + '">' + back(st) + '</td>' +
      '<td class="num">' + fmt(st.ms, 1) + '</td>';
  }).join('') + '</tr>';
});
html += '<tr class="group"><td>Meets its target (✓)</td>' + ENGINES.map(e => '<td colspan="4" style="text-align:center">' + totals[e] + ' / ' + DATA.length + '</td>').join('') + '</tr>';
sum.innerHTML = html + '</tbody>';

// Players
const cards = document.getElementById('cards');
const players = DATA.map(s => {
  s.imgs = s.frames.map(src => { const im = new Image(); im.onload = () => draw(p); im.src = src; return im; });
  const el = document.createElement('article');
  el.className = 'card';
  const pills = ENGINES.map(e => '<span class="pill ' + (s.engines[e].stats.meets ? 'ok' : 'weak') + '" style="border:1.5px solid ' + COLOURS[e] + '">' +
    NAMES[e].split(' ')[0] + (s.engines[e].stats.meets ? ' meets target' : ' below target') + '</span>').join(' ');
  el.innerHTML =
    '<header><h2>' + s.name + '</h2><div>' + pills + '</div></header>' +
    '<p class="blurb">' + s.blurb + '</p>' +
    '<canvas class="view" width="480" height="360" aria-label="' + s.name + ' tracking playback"></canvas>' +
    '<div class="controls"><button class="btn play">Play</button>' +
    '<input class="slider" type="range" min="0" max="' + (s.frames.length - 1) + '" value="0" aria-label="frame">' +
    '<span class="now"></span></div>' +
    '<canvas class="chart" width="460" height="120" aria-label="error over time"></canvas>' +
    '<div class="estats">' + ENGINES.map(e => {
      const st = s.engines[e].stats;
      return '<div><b><i class="sw" style="background:' + COLOURS[e] + '"></i>' + NAMES[e] + '</b>' +
        '<span class="' + (st.onBall < s.target.onBall ? 'over' : '') + '">on ball ' + Math.round(st.onBall * 100) + '%</span>' +
        '<span class="' + (st.median > s.target.median ? 'over' : '') + '">median ' + fmt(st.median, 1) + ' px</span>' +
        '<span class="' + (st.p95 > s.target.p95 ? 'over' : '') + '">95% ' + fmt(st.p95, 1) + ' px</span>' +
        (st.recovery !== null ? '<span class="' + (st.recovery < 0 || st.recovery > s.target.recovery ? 'over' : '') + '">back ' + back(st) + '</span>' : '') +
        '<span>' + fmt(st.ms, 1) + ' ms/frame</span></div>';
    }).join('') + '</div>' +
    '<p class="note">Target (' + s.tier + '): median ≤ ' + s.target.median + ' px, 95% ≤ ' + s.target.p95 +
      ' px, on the ball ≥ ' + Math.round(s.target.onBall * 100) + '%' +
      (s.target.recovery !== null && s.hidden.some(x => x) ? ', back within ' + s.target.recovery + ' frames of a cover' : '') + '.</p>';
  cards.appendChild(el);
  const p = { s, el, view: el.querySelector('.view'), chart: el.querySelector('.chart'), slider: el.querySelector('.slider'),
              now: el.querySelector('.now'), btn: el.querySelector('.play'), i: 0, playing: false };
  // Rest on the interesting moment: just after the first miss of any engine, or the middle
  const misses = ENGINES.map(e => s.engines[e].stats.firstMiss).filter(v => v !== null);
  const rest = misses.length ? Math.min(N - 1, Math.min(...misses) + 6) : 60;
  p.i = Math.round(rest / STEP);
  p.slider.value = p.i;
  p.slider.addEventListener('input', () => { p.i = +p.slider.value; draw(p); });
  p.btn.addEventListener('click', () => { p.playing = !p.playing; p.btn.textContent = p.playing ? 'Pause' : 'Play'; });
  return p;
});

function trail(ctx, pts, t, k, color, width) {
  ctx.beginPath();
  const from = Math.max(0, t - 14);
  for (let u = from; u <= t; u++) { const x = pts[u][0] * k, y = pts[u][1] * k; u === from ? ctx.moveTo(x, y) : ctx.lineTo(x, y); }
  ctx.lineWidth = width + 2; ctx.strokeStyle = '#000'; ctx.stroke();
  ctx.lineWidth = width; ctx.strokeStyle = color; ctx.stroke();
}

function marker(ctx, x, y, r, color, lost) {
  ctx.setLineDash(lost ? [3, 3] : []);
  ctx.lineWidth = 4; ctx.strokeStyle = '#000'; ctx.strokeRect(x - r, y - r, 2 * r, 2 * r);
  ctx.lineWidth = 2; ctx.strokeStyle = color; ctx.strokeRect(x - r, y - r, 2 * r, 2 * r);
  ctx.setLineDash([]);
}

function draw(p) {
  const { s, view } = p;
  const t = Math.min(N - 1, p.i * STEP);
  const ctx = view.getContext('2d'), k = view.width / SRC_W;
  const im = s.imgs[p.i];
  if (im.complete && im.naturalWidth) ctx.drawImage(im, 0, 0, view.width, view.height);
  trail(ctx, s.truth, t, k, '#7cff00', 1.5);
  ENGINES.forEach(e => trail(ctx, s.engines[e].centre, t, k, COLOURS[e], 1.5));
  ctx.beginPath(); ctx.arc(s.truth[t][0] * k, s.truth[t][1] * k, s.radius * k, 0, 6.2832);
  ctx.lineWidth = 4; ctx.strokeStyle = '#000'; ctx.stroke(); ctx.lineWidth = 2; ctx.strokeStyle = '#7cff00'; ctx.stroke();
  ENGINES.forEach(e => { const c = s.engines[e].centre[t]; marker(ctx, c[0] * k, c[1] * k, s.radius * k + 2, COLOURS[e], s.engines[e].lost[t]); });
  p.now.textContent = 'frame ' + t + (s.hidden[t] ? ' · hidden' : '') + ' · ' +
    ENGINES.map(e => NAMES[e].split(' ')[0] + ' ' + fmt(s.engines[e].error[t], 1)).join(' · ') + ' px';
  p.slider.value = p.i;
  drawChart(p, t);
}

function drawChart(p, t) {
  const { s, chart } = p, ctx = chart.getContext('2d');
  const dpr = Math.min(window.devicePixelRatio || 1, 3), cssW = chart.clientWidth || 460, cssH = 120;
  if (chart.width !== Math.round(cssW * dpr)) { chart.width = Math.round(cssW * dpr); chart.height = cssH * dpr; }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssW, cssH);
  const L = 34, R = 8, T = 16, B = 20, w = cssW - L - R, h = cssH - T - B;
  const maxErr = Math.max(...ENGINES.flatMap(e => s.engines[e].error));
  const cap = Math.max(1.6 * s.radius, Math.min(maxErr * 1.1, 3 * s.radius));
  const X = u => L + (u / (N - 1)) * w, Y = e => T + h - Math.min(e, cap) / cap * h;
  ctx.font = '10px ' + css('--mono'); ctx.fillStyle = css('--muted'); ctx.strokeStyle = css('--line'); ctx.lineWidth = 1;
  [0, s.radius, cap].forEach(v => {
    ctx.beginPath(); ctx.moveTo(L, Y(v)); ctx.lineTo(L + w, Y(v)); ctx.stroke();
    ctx.textAlign = 'right'; ctx.textBaseline = 'middle'; ctx.fillText(fmt(v, v < 10 ? 1 : 0), L - 5, Y(v));
  });
  ctx.textAlign = 'center'; ctx.textBaseline = 'top';
  [0, 30, 60, 90, 119].forEach(u => ctx.fillText(u, X(u), T + h + 5));
  // Frames where the ball is hidden
  ctx.fillStyle = css('--hidden');
  for (let u = 0; u < N; u++) if (s.hidden[u]) ctx.fillRect(X(u) - w / N / 2, T, w / N, h);
  ctx.setLineDash([4, 3]); ctx.strokeStyle = css('--muted'); ctx.beginPath(); ctx.moveTo(L, Y(s.radius)); ctx.lineTo(L + w, Y(s.radius)); ctx.stroke(); ctx.setLineDash([]);
  ENGINES.forEach(e => {
    ctx.beginPath(); s.engines[e].error.forEach((v, u) => u ? ctx.lineTo(X(u), Y(v)) : ctx.moveTo(X(u), Y(v)));
    ctx.strokeStyle = COLOURS[e]; ctx.lineWidth = 1.6; ctx.stroke();
  });
  ctx.strokeStyle = css('--ink'); ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(X(t), T); ctx.lineTo(X(t), T + h); ctx.stroke();
  ctx.fillStyle = css('--muted'); ctx.textAlign = 'left'; ctx.textBaseline = 'top';
  ctx.fillText('error (px) per frame · dashed: ball radius' + (maxErr > cap ? ' · clipped at ' + fmt(cap, 0) : ''), L + 2, 1);
}

let timer = setInterval(() => players.forEach(p => { if (p.playing) { p.i = (p.i + 1) % p.s.frames.length; draw(p); } }), 130);
const playall = document.getElementById('playall');
playall.addEventListener('click', () => {
  const on = playall.textContent === 'Play all';
  players.forEach(p => { p.playing = on; p.btn.textContent = on ? 'Pause' : 'Play'; });
  playall.textContent = on ? 'Pause all' : 'Play all';
});
const redraw = () => players.forEach(draw);
window.addEventListener('resize', redraw);
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', redraw);
new MutationObserver(redraw).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
redraw();
</script>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Tracker benchmark page")
    parser.add_argument("out", nargs="?", default=os.path.join(h.REPO, "temp", "benchmark_report.html"))
    parser.add_argument("--engines", default="nanotrack,trackpy")
    parser.add_argument("--settings", help="blob tracker settings (JSON) for the trackpy engine")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    args = parser.parse_args()
    settings = None
    if args.settings:
        with open(args.settings) as f:
            settings = json.load(f)
    data = collect(args.engines.split(","), settings, args.jobs)
    html = PAGE.replace("__DATA__", json.dumps(data, separators=(",", ":")))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"wrote {args.out} ({len(html) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
