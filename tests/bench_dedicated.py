"""
Scores dedicated trackers (OpenCV CSRT, YOLO 'sports ball') against the app's cliptrack engine on the
labelled real clips (tests/real_clips.py), with the same metric (median px error, share of labelled
frames within the ball radius). Each tracker starts from the first label's box.

    PHYSTRACK_REAL_FOOTAGE=... uv run --with opencv-contrib-python-headless --with ultralytics \
        python -m tests.bench_dedicated [--engine offline] [--yolo yolov8n.pt]
"""
import argparse
import time

import numpy as np


def box_of(spec):
    x, y = spec["labels"]["0"]
    r = spec["radius"]
    return int(round(x - r)), int(round(y - r)), int(round(2 * r)), int(round(2 * r))


def track_csrt(frames, spec):
    import cv2
    x, y, w, h = box_of(spec)
    mk = getattr(cv2, "TrackerCSRT_create", None) or cv2.legacy.TrackerCSRT_create
    t = mk()
    t.init(np.ascontiguousarray(frames[0]), (x, y, w, h))
    c = np.full((len(frames), 2), np.nan)
    c[0] = spec["labels"]["0"]
    last = c[0].copy()
    for i in range(1, len(frames)):
        ok, b = t.update(np.ascontiguousarray(frames[i]))
        if ok:
            last = np.array([b[0] + b[2] / 2, b[1] + b[3] / 2])
        c[i] = last
    return c


def track_yolo(frames, spec, weights, device):
    from ultralytics import YOLO
    import cv2
    m = YOLO(weights)
    c = np.full((len(frames), 2), np.nan)
    c[0] = spec["labels"]["0"]
    last = c[0].copy()
    stats = {"full": 0, "crop": 0, "miss": 0}

    def detect(img, conf):
        r = m.predict(img, classes=[32], conf=conf, verbose=False, device=device, imgsz=max(img.shape[:2]) // 32 * 32)[0]
        return [((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) for b in r.boxes.xyxy.cpu().numpy()]

    for i in range(1, len(frames)):
        f = np.ascontiguousarray(frames[i])
        cands = detect(f, 0.05)
        src = "full"
        if not cands:
            # upscaled crop (x6) around the last position
            half = 60
            x0, y0 = int(max(last[0] - half, 0)), int(max(last[1] - half, 0))
            x1, y1 = int(min(last[0] + half, f.shape[1])), int(min(last[1] + half, f.shape[0]))
            crop = cv2.resize(f[y0:y1, x0:x1], None, fx=6, fy=6, interpolation=cv2.INTER_CUBIC)
            cands = [(x0 + u / 6, y0 + v / 6) for u, v in detect(crop, 0.02)]
            src = "crop"
        if cands:
            last = np.array(min(cands, key=lambda p: np.hypot(p[0] - last[0], p[1] - last[1])))
            stats[src] += 1
        else:
            stats["miss"] += 1
        c[i] = last
    return c, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="offline")
    ap.add_argument("--yolo", default="yolov8n.pt")
    ap.add_argument("--device", default="0")
    a = ap.parse_args()
    from tests import harness as h
    h.setup_env()
    from tests import real_clips as rc
    rows = []
    for p in rc.label_files():
        spec = rc.load_spec(p)
        col = rc.load_frames(spec, colour=True)
        if col is None or spec["labels"].get("0") is None:
            continue
        name = p.split("/")[-1][:-5]
        res = {}
        t = time.time(); c = track_csrt(col, spec); ms = (time.time() - t) / len(col) * 1000
        res["csrt"] = (rc.score(spec, c), ms, "")
        t = time.time(); c, st = track_yolo(col, spec, a.yolo, a.device); ms = (time.time() - t) / len(col) * 1000
        res["yolo"] = (rc.score(spec, c), ms, str(st))
        try:
            from experiments.rigid.cliptrack import track_frames
            g = rc.load_frames(spec)
            r = spec["radius"]; ang = np.linspace(0, 2 * np.pi, 32, endpoint=False)
            s0 = spec["labels"]["0"]
            outline = np.column_stack([s0[0] + r * np.cos(ang), s0[1] + r * np.sin(ang)])
            o = track_frames(g, None, a.engine, {}, outline=outline)
            res[a.engine] = (rc.score(spec, o.centre), o.ms_per_frame, "")
        except Exception as e:
            print("engine failed:", e)
        for k, (s, ms, extra) in res.items():
            if s:
                print(f"{name:24s} {k:8s} med={s['median']:6.2f}px  on={s['on_ball']*100:5.1f}%  {ms:7.1f} ms/f {extra}", flush=True)
                rows.append((k, s["median"], s["on_ball"], ms))
    for k in sorted({r[0] for r in rows}):
        v = [r for r in rows if r[0] == k]
        print(f"MEAN {k:8s} med={np.mean([x[1] for x in v]):6.2f}  on={np.mean([x[2] for x in v])*100:5.1f}%  {np.mean([x[3] for x in v]):7.1f} ms/f")


if __name__ == "__main__":
    main()
