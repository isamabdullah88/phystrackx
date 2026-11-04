"""
Label the ball's centre in a stretch of a real video, for tests on real footage (real_clips.py).

    uv run python -m tests.label_real "Air Trial 1.mp4" --start 12 --seconds 10
    uv run python -m tests.label_real tests/real_labels/air_trial_1_12.0.json     # open an existing one

A page opens at http://127.0.0.1:8766:
- Click the ball's centre on frame 0 (the zoom on the right is 4x, for precise clicks). [ and ]
  change the ball's radius (the circle drawn).
- Track fills in every frame with the tracker's guess (orange). Step through and fix it: click
  where the ball is (green: your label), A takes the guess for this frame, Shift+A for the next ten,
  H marks the ball as hidden, Delete clears the frame. Arrows step one frame, Shift+arrows ten.
- Every change is saved at once to tests/real_labels/<video>_<start>.json (the video stays where
  it is; PHYSTRACK_REAL_FOOTAGE names its folder).

Labelling every fifth frame is enough for the tests; frames in between are not scored.
"""

import argparse
import http.server
import json
import os
import re
import threading
import webbrowser

import cv2
import numpy as np

from tests import harness as h
from tests import real_clips as rc

ENGINE = ("offline", {"background_mix": 1.0, "selection_offset": True, "physics": True})


def _new_spec(video: str, start: float, seconds: float, width: int) -> dict:
    path = rc.find_video(video)
    if path is None:
        raise SystemExit(f"{video} not found under {rc.REAL_FOOTAGE}")
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.release()
    stem = re.sub(r"[^a-z0-9]+", "_", os.path.splitext(os.path.basename(path))[0].lower()).strip("_")
    return {"path": os.path.join(rc.LABELS, f"{stem}_{start:.1f}.json"), "video": os.path.basename(path),
            "start": start, "frames": int(round(seconds * fps)), "fps": fps, "width": width,
            "radius": 5.0, "labels": {}, "note": ""}


class Labeller:
    def __init__(self, spec: dict):
        self.spec = spec
        self.lock = threading.Lock()
        print("decoding frames...", flush=True)
        self.frames = rc.load_frames(spec, colour=True)
        self.count = len(self.frames)
        self.busy = False

    def state(self) -> dict:
        s = self.spec
        return {k: s.get(k) for k in ("video", "start", "fps", "width", "radius", "labels",
                                      "predicted", "note")} | {"frames": self.count,
            "height": int(self.frames.shape[1]), "file": os.path.relpath(s["path"], h.REPO), "busy": self.busy}

    def jpeg(self, i: int) -> bytes:
        ok, buf = cv2.imencode(".jpg", np.asarray(self.frames[max(0, min(i, len(self.frames) - 1))]),
                               [cv2.IMWRITE_JPEG_QUALITY, 90])
        return buf.tobytes()

    def act(self, body: dict) -> None:
        with self.lock:
            labels = self.spec.setdefault("labels", {})
            if "frame" in body:
                key = str(int(body["frame"]))
                if body.get("clear"):
                    labels.pop(key, None)
                else:
                    labels[key] = None if body.get("pos") is None else [round(float(v), 2) for v in body["pos"]]
            if "frames" in body:   # Several at once: {"frames": {i: pos}}
                for k, v in body["frames"].items():
                    labels[str(int(k))] = None if v is None else [round(float(x), 2) for x in v]
            if "radius" in body:
                self.spec["radius"] = round(max(1.0, float(body["radius"])), 2)
            if "note" in body:
                self.spec["note"] = str(body["note"])
            rc.save_spec(self.spec)
        if body.get("track"):
            threading.Thread(target=self.track, daemon=True).start()

    def track(self) -> None:
        """The tracker's guess for every frame, from the frame-0 label."""
        from experiments.rigid.cliptrack import MEASURED, track_frames
        start = self.spec.get("labels", {}).get("0")
        if start is None or self.busy:
            return
        self.busy = True
        try:
            r = self.spec["radius"]
            angle = np.linspace(0, 2 * np.pi, 32, endpoint=False)
            outline = np.column_stack([start[0] + r * np.cos(angle), start[1] + r * np.sin(angle)])
            grey = np.stack([cv2.cvtColor(np.asarray(f), cv2.COLOR_BGR2GRAY) for f in self.frames])
            engine, values = ENGINE
            out = track_frames(grey, None, engine, values, outline=outline)
            with self.lock:
                self.spec["predicted"] = [[round(float(x), 2), round(float(y), 2), int(st)]
                                          for (x, y), st in zip(out.centre, out.status)]
                self.spec["predicted_by"] = f"{engine} {json.dumps(values)}"
                rc.save_spec(self.spec)
        finally:
            self.busy = False


def serve(lab: Labeller, port: int):
    page = PAGE.encode()

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, body: bytes, kind: str):
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.startswith("/state"):
                self._send(json.dumps(lab.state()).encode(), "application/json")
            elif self.path.startswith("/frame/"):
                self._send(lab.jpeg(int(self.path.rsplit("/", 1)[-1].split(".")[0])), "image/jpeg")
            else:
                self._send(page, "text/html; charset=utf-8")

        def do_POST(self):
            size = int(self.headers.get("Content-Length", 0))
            lab.act(json.loads(self.rfile.read(size) or b"{}"))
            self._send(b"{}", "application/json")

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("source", help="a video name (under PHYSTRACK_REAL_FOOTAGE) or a label file")
    parser.add_argument("--start", type=float, default=0.0, help="seconds into the video")
    parser.add_argument("--seconds", type=float, default=10.0)
    parser.add_argument("--width", type=int, default=540, help="frames are scaled to this width")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    h.setup_env()
    if args.source.endswith(".json"):
        spec = rc.load_spec(args.source)
    else:
        spec = _new_spec(args.source, args.start, args.seconds, args.width)
        if os.path.exists(spec["path"]):
            spec = rc.load_spec(spec["path"])
    lab = Labeller(spec)
    rc.save_spec(lab.spec)
    serve(lab, args.port)
    url = f"http://127.0.0.1:{args.port}"
    print(f"labelling {spec['video']} from {spec['start']} s ({lab.count} frames) at {url}; "
          f"labels in {os.path.relpath(spec['path'], h.REPO)} (Ctrl+C to stop)", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ball Labels</title>
<style>
:root { --bg: #f2f4f1; --surface: #fff; --ink: #18201b; --muted: #5d6861; --line: #d3dad4;
  --label: #0d9b5c; --guess: #e07b00; --hidden: #8a938d; --accent: #2d4fc8;
  --mono: ui-monospace, "SF Mono", Menlo, monospace; }
@media (prefers-color-scheme: dark) { :root { --bg: #101512; --surface: #171d19; --ink: #e4eae6; --muted: #9aa69f;
  --line: #2a332e; --label: #3fd58f; --guess: #ffa940; --hidden: #66706a; --accent: #8ba5ff; color-scheme: dark; } }
body { margin: 0; background: var(--bg); color: var(--ink); font: 14px/1.45 system-ui, -apple-system, sans-serif;
  padding: 14px max(16px, env(safe-area-inset-left, 0px)); }
.top { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: baseline; margin-bottom: 10px; }
h1 { font-size: 18px; margin: 0; }
.muted { color: var(--muted); font-size: 13px; }
.main { display: grid; grid-template-columns: minmax(0, auto) 260px; gap: 14px; align-items: start; }
@media (max-width: 760px) { .main { grid-template-columns: 1fr; } }
.view { position: relative; min-width: 0; }
canvas { display: block; background: #000; border-radius: 6px; cursor: crosshair; max-width: 100%; }
.side { display: grid; gap: 10px; }
.panel { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 10px; }
button { font: inherit; font-weight: 600; border: 1px solid var(--line); background: var(--surface); color: var(--ink);
  border-radius: 6px; padding: 5px 10px; cursor: pointer; }
button.primary { background: var(--ink); color: var(--bg); border-color: var(--ink); }
.row { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
#strip { width: 100%; height: 22px; display: block; margin-top: 8px; cursor: pointer; background: var(--surface); border-radius: 4px; }
input[type=range] { width: 100%; }
kbd { font-family: var(--mono); font-size: 12px; border: 1px solid var(--line); border-radius: 4px; padding: 0 4px; }
.keys { font-size: 12px; color: var(--muted); display: grid; gap: 3px; }
.dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 5px; }
</style></head><body>
<div class="top"><h1 id="title">Ball labels</h1><span class="muted" id="file"></span><span class="muted" id="count"></span></div>
<div class="main">
  <div class="view">
    <canvas id="c"></canvas>
    <input type="range" id="slider" min="0" value="0">
    <canvas id="strip" height="22"></canvas>
  </div>
  <div class="side">
    <div class="panel"><canvas id="zoom" width="240" height="240"></canvas>
      <div class="muted" id="where"></div></div>
    <div class="panel row">
      <button class="primary" id="track">Track</button>
      <button id="accept">Take guess (A)</button>
      <button id="hide">Hidden (H)</button>
      <button id="clear">Clear</button>
    </div>
    <div class="panel">
      <div class="muted"><span class="dot" style="background:var(--label)"></span>your label
        <span class="dot" style="background:var(--guess);margin-left:10px"></span>tracker's guess</div>
      <div class="keys" style="margin-top:6px">
        <div>Click: the ball's centre (here or in the zoom)</div>
        <div><kbd>←</kbd> <kbd>→</kbd> one frame, with <kbd>Shift</kbd> ten</div>
        <div><kbd>A</kbd> take the guess, <kbd>Shift</kbd>+<kbd>A</kbd> for the next ten</div>
        <div><kbd>H</kbd> hidden, <kbd>Delete</kbd> clear, <kbd>[</kbd> <kbd>]</kbd> radius</div>
      </div>
    </div>
  </div>
</div>
<script>
const $ = id => document.getElementById(id);
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
let S = null, f = 0, img = new Image(), scale = 1;
const post = b => fetch('/', {method: 'POST', body: JSON.stringify(b)}).then(load);
function load() { return fetch('/state').then(r => r.json()).then(s => { S = s; draw(); }); }
function show(i) { f = Math.max(0, Math.min(S.frames - 1, i)); $('slider').value = f; img.src = '/frame/' + f + '.jpg?' + f; }
img.onload = draw;
function guess(i) { return S.predicted && S.predicted[i] ? S.predicted[i] : null; }
function draw() {
  if (!S) return;
  const c = $('c'), ctx = c.getContext('2d');
  const maxH = window.innerHeight - 140, w = S.width, hh = S.height;
  scale = Math.min(1.6, maxH / hh, (c.parentElement.clientWidth || w) / w);
  c.width = Math.round(w * scale); c.height = Math.round(hh * scale);
  if (img.complete && img.naturalWidth) ctx.drawImage(img, 0, 0, c.width, c.height);
  const L = S.labels[String(f)], G = guess(f), r = S.radius;
  const ring = (p, col, dash) => { ctx.setLineDash(dash ? [3, 3] : []); ctx.strokeStyle = col; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.arc(p[0] * scale, p[1] * scale, Math.max(3, r * scale), 0, 6.3); ctx.stroke(); ctx.setLineDash([]); };
  if (G) ring(G, css('--guess'), G[2] !== 1);
  if (L) ring(L, css('--label'));
  // Zoom: 60x60 frame pixels around the label, the guess, or the last label
  const z = $('zoom'), zc = z.getContext('2d'), Z = 4, half = 30;
  const centre = L || G || [S.width / 2, S.height / 2];
  zc.imageSmoothingEnabled = false; zc.fillStyle = '#000'; zc.fillRect(0, 0, 240, 240);
  if (img.complete && img.naturalWidth) zc.drawImage(img, centre[0] - half, centre[1] - half, 2 * half, 2 * half, 0, 0, 240, 240);
  z.dataset.x0 = centre[0] - half; z.dataset.y0 = centre[1] - half;
  const zr = (p, col, dash) => { zc.setLineDash(dash ? [4, 4] : []); zc.strokeStyle = col; zc.lineWidth = 1.5; zc.beginPath();
    zc.arc((p[0] - centre[0] + half) * Z, (p[1] - centre[1] + half) * Z, r * Z, 0, 6.3); zc.stroke();
    zc.beginPath(); zc.moveTo((p[0] - centre[0] + half) * Z - 4, (p[1] - centre[1] + half) * Z); zc.lineTo((p[0] - centre[0] + half) * Z + 4, (p[1] - centre[1] + half) * Z); zc.stroke(); zc.setLineDash([]); };
  if (G) zr(G, css('--guess'), G[2] !== 1);
  if (L) zr(L, css('--label'));
  $('where').textContent = 'frame ' + f + ' / ' + (S.frames - 1) + (L === null ? ' · hidden' : L ? ' · label ' + L[0].toFixed(1) + ', ' + L[1].toFixed(1) : ' · not labelled') + ' · radius ' + r;
  $('title').textContent = S.video + ' from ' + S.start + ' s';
  $('file').textContent = S.file;
  const keys = Object.keys(S.labels);
  $('count').textContent = keys.length + ' frames labelled (' + keys.filter(k => S.labels[k] === null).length + ' hidden)' + (S.busy ? ' · tracking…' : '');
  $('slider').max = S.frames - 1;
  strip();
}
function strip() {
  const c = $('strip'), ctx = c.getContext('2d'), W = c.clientWidth; c.width = W;
  ctx.clearRect(0, 0, W, 22);
  for (const [k, v] of Object.entries(S.labels)) { ctx.fillStyle = v === null ? css('--hidden') : css('--label');
    ctx.fillRect(+k / S.frames * W, 2, Math.max(1, W / S.frames), 12); }
  if (S.predicted) S.predicted.forEach((p, i) => { if (p[2] !== 1) { ctx.fillStyle = css('--guess'); ctx.fillRect(i / S.frames * W, 16, Math.max(1, W / S.frames), 4); } });
  ctx.fillStyle = css('--accent'); ctx.fillRect(f / S.frames * W - 1, 0, 2, 22);
}
$('c').onclick = e => { const b = $('c').getBoundingClientRect();
  post({frame: f, pos: [(e.clientX - b.left) / scale, (e.clientY - b.top) / scale]}); };
$('zoom').onclick = e => { const b = $('zoom').getBoundingClientRect(), z = $('zoom');
  post({frame: f, pos: [+z.dataset.x0 + (e.clientX - b.left) / 4, +z.dataset.y0 + (e.clientY - b.top) / 4]}); };
$('strip').onclick = e => { const b = $('strip').getBoundingClientRect(); show(Math.round((e.clientX - b.left) / b.width * S.frames)); };
$('slider').oninput = e => show(+e.target.value);
$('track').onclick = () => post({track: true}).then(() => { const t = setInterval(() => load().then(() => { if (!S.busy) clearInterval(t); }), 1000); });
const accept = n => { const fr = {}; for (let i = f; i < Math.min(S.frames, f + n); i++) { const G = guess(i); if (G) fr[i] = [G[0], G[1]]; } return post({frames: fr}); };
$('accept').onclick = () => accept(1);
$('hide').onclick = () => post({frame: f, pos: null});
$('clear').onclick = () => post({frame: f, clear: true});
document.addEventListener('keydown', e => {
  if (e.key === 'ArrowRight') { show(f + (e.shiftKey ? 10 : 1)); e.preventDefault(); }
  else if (e.key === 'ArrowLeft') { show(f - (e.shiftKey ? 10 : 1)); e.preventDefault(); }
  else if (e.key === 'a' || e.key === 'A') accept(e.shiftKey ? 10 : 1);
  else if (e.key === 'h' || e.key === 'H') post({frame: f, pos: null});
  else if (e.key === 'Delete' || e.key === 'Backspace') post({frame: f, clear: true});
  else if (e.key === '[') post({radius: S.radius - 0.25});
  else if (e.key === ']') post({radius: S.radius + 0.25});
});
window.addEventListener('resize', draw);
load().then(() => show(0));
</script></body></html>
"""


if __name__ == "__main__":
    main()
