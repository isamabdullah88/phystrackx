"""
Scores a tracking engine on every cached benchmark clip (the tuner's clips: training, and the
holdout parts), and compares it with earlier results.

    uv run python -m tests.bench_tracker blob                                  # the blob tracker's defaults
    uv run python -m tests.bench_tracker blob@temp/tuned_blob_settings.json --label tuned
    uv run python -m tests.bench_tracker blob,background_mix=0.7 --label background
    uv run python -m tests.bench_tracker --compare                             # every saved result
    uv run python -m tests.bench_tracker --compare blob tuned background       # ...or these

An engine is written ENGINE[@SETTINGS.json][,name=value...]: a cliptrack engine
(experiments/rigid/cliptrack.py), settings from a file, then single settings. Each result goes
to temp/bench/<label>.json (the label is the spec unless --label gives one), and the comparison
table lists them in the order given, with the clips that changed most against the first.

The clips are the tuner's (tests/tune_tracker.py, drawn into temp/tracker_frames on first use),
plus the labelled real clips (tests/real_clips.py; part "real, labelled": tracked forward from
the first label, scored on the labelled frames); scores are the tuner's per-clip scores (1.05 is
perfect; a real clip meets its target with a median error of 2 px and 95% of frames on the ball). The ball is selected with an automatic
outline, as in the Qt app (--selection box: the circle tool's square).
"""

import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from tests import harness as h
from tests import tune_tracker as tune

OUT = os.path.join(h.REPO, "temp", "bench")
PART_ORDER = ["train", "draw", "kind", "real", "labelled"]
PART_NAMES = {"train": "training", "draw": "unseen draws", "kind": "held-out kinds",
              "real": "real backgrounds", "labelled": "real, labelled"}


def parse_spec(spec: str) -> tuple[str, dict]:
    """ENGINE[@SETTINGS.json][,name=value...] -> (engine, settings)."""
    head, *pairs = spec.split(",")
    engine, _, path = head.partition("@")
    values = {}
    if path:
        with open(path) as f:
            values.update(json.load(f))
    for pair in pairs:
        name, _, text = pair.partition("=")
        try:
            values[name] = json.loads(text)
        except ValueError:
            values[name] = text
    return engine, values


REAL_TARGET = (2.0, 0.95)  # Real labelled clips: median error (px) and on-ball share to meet


def run_labelled(arg) -> dict | None:
    """Tracks one labelled real clip (real_clips.py) forward from its frame-0 label, selected with an
    outline of the ball's circle, and scores it on the labelled frames, plus label-free checks."""
    path, values, engine = arg
    h.setup_env()
    import cv2
    cv2.setNumThreads(1)
    from experiments.rigid.cliptrack import track_frames
    from experiments.rigid.physics import quality
    from tests import real_clips as rc
    spec = rc.load_spec(path)
    frames = rc.load_frames(spec)
    start = spec["labels"].get("0")
    if frames is None or start is None:
        return None
    r = spec["radius"]
    angle = np.linspace(0, 2 * np.pi, 32, endpoint=False)
    outline = np.column_stack([start[0] + r * np.cos(angle), start[1] + r * np.sin(angle)])
    out = track_frames(frames, None, engine, values, outline=outline)
    res = rc.score(spec, out.centre)
    if res is None:
        return None
    meets = res["median"] <= REAL_TARGET[0] and res["on_ball"] >= REAL_TARGET[1]
    q = quality(out.centre, out.status, r)
    name = f"{spec['video']} from {spec['start'] + spec.get('range', [0])[0] / spec.get('fps', 30):.1f} s"
    return {"name": name, "clip": os.path.basename(path)[:-5], "part": "labelled", "kind": "real",
            "score": res["on_ball"] - 0.02 * min(res["median"] / r, 1.0) + 0.05 * meets,
            "on_ball": res["on_ball"], "median": res["median"], "recovery": None, "meets": bool(meets),
            "ms": out.ms_per_frame, "labelled": res["labelled"], "jitter": q.jitter, "measured": q.measured}


def bench(spec: str, label: str, jobs: int, selection: str = "outline", only=None) -> dict:
    """Scores an engine on every part (or the parts in `only`), saves and returns the result."""
    engine, values = parse_spec(spec)
    parts = tune.ensure_frames(jobs) if only != ["labelled"] else {}
    paths = [(part, p) for part in PART_ORDER for p in parts.get(part, []) if not only or part in only]
    start = time.time()
    from tests import real_clips as rc
    with ProcessPoolExecutor(jobs) as pool:
        rows = list(pool.map(tune.run_one, [(p, values, None, engine, selection) for _, p in paths]))
        if not only or "labelled" in only:
            rows += [r for r in pool.map(run_labelled, [(p, values, engine) for p in rc.label_files()]) if r]
    if only and os.path.exists(os.path.join(OUT, _file(label))):
        # Only some parts were scored: keep the saved result's other parts
        rows = [r for r in load(label)["rows"] if r["part"] not in only] + rows
    summary = {}
    for part in PART_ORDER:
        mine = [r for r in rows if r["part"] == part]
        if mine:
            summary[part] = {"score": float(np.mean([r["score"] for r in mine])),
                             "on_ball": float(np.mean([r["on_ball"] for r in mine])),
                             "meets": int(sum(r["meets"] for r in mine)), "count": len(mine),
                             "ms": float(np.mean([r["ms"] for r in mine]))}
    result = {"label": label, "spec": spec, "engine": engine, "values": values, "selection": selection,
              "when": time.time(),
              "seconds": time.time() - start, "summary": summary, "rows": rows}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, _file(label)), "w") as f:
        json.dump(result, f, indent=1)
    return result


def _file(label: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in label) + ".json"


def load(label: str) -> dict:
    with open(os.path.join(OUT, _file(label))) as f:
        return json.load(f)


def compare(labels: list[str], changed: int = 12) -> str:
    """A table of the results' scores per part, and the clips that changed most against the first."""
    results = [load(x) for x in labels]
    parts = [p for p in PART_ORDER if any(p in r["summary"] for r in results)]
    width = max(len(x) for x in labels) + 2
    head = f"{'':{width}}" + "".join(f"{PART_NAMES[p]:>20}" for p in parts) + f"{'meets':>10}{'ms/frame':>10}"
    lines = [head]
    for r in results:
        s = r["summary"]
        cells = "".join(f"{s[p]['score']:>14.3f} ({s[p]['meets']:>2}/{s[p]['count']:<2})" if p in s else f"{'':>20}"
                        for p in parts)
        meets = sum(v["meets"] for v in s.values())
        total = sum(v["count"] for v in s.values())
        ms = np.mean([row["ms"] for row in r["rows"]])
        lines.append(f"{r['label']:{width}}{cells}{f'{meets}/{total}':>10}{ms:>10.1f}")
    lines.append("score per part: mean per-clip score (1.05 is perfect); (meets / clips)")
    if len(results) > 1:
        base = {row["clip"]: row for row in results[0]["rows"]}
        for r in results[1:]:
            diffs = sorted(((row["score"] - base[row["clip"]]["score"], row) for row in r["rows"]
                            if row["clip"] in base), key=lambda d: -abs(d[0]))
            lines.append(f"\nlargest changes, {results[0]['label']} -> {r['label']}:")
            for d, row in diffs[:changed]:
                if abs(d) < 0.02:
                    break
                b = base[row["clip"]]
                lines.append(f"  {d:+.2f}  {row['part']:5} {row['name'][:52]:52} on-ball "
                             f"{b['on_ball']:4.0%} -> {row['on_ball']:4.0%}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("spec", nargs="*", help="engines to score (or, with --compare, labels to compare)")
    parser.add_argument("--label", help="name for the result (one engine only)")
    parser.add_argument("--compare", action="store_true", help="only compare saved results")
    parser.add_argument("--selection", choices=["outline", "box"], default="outline",
                        help="how the ball is selected: an automatic outline (Qt app) or the circle's square")
    parser.add_argument("--parts", help="only these parts, comma-separated (train, draw, kind, real, labelled)")
    parser.add_argument("--jobs", type=int, default=tune.physical_cores())
    args = parser.parse_args()
    h.setup_env()
    if args.compare:
        labels = args.spec or [r["label"] for r in sorted(
            (json.load(open(os.path.join(OUT, f))) for f in os.listdir(OUT) if f.endswith(".json")),
            key=lambda r: r["when"])]
        print(compare(labels))
        return
    labels = []
    for spec in args.spec:
        label = args.label if args.label and len(args.spec) == 1 else spec
        r = bench(spec, label, args.jobs, args.selection, args.parts.split(",") if args.parts else None)
        labels.append(label)
        print(f"{label}: " + ", ".join(f"{PART_NAMES[p]} {v['score']:.3f}" for p, v in r["summary"].items())
              + f" ({r['seconds']:.0f} s)", flush=True)
    print(compare(labels))


if __name__ == "__main__":
    main()
