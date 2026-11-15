import base64
import csv
import html
import io

import cv2

from . import config


def _thumb(path, width=520) -> str:
    img = cv2.imread(str(path))
    if img is None:
        return ""
    h, w = img.shape[:2]
    s = min(1.0, width / w)
    img = cv2.resize(img, (max(1, round(w * s)), max(1, round(h * s))), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode() if ok else ""


def _row(label, a, b):
    return f"<tr><td>{html.escape(label)}</td><td>{a}</td><td>{b}</td></tr>"


def job_html(job: dict) -> str:
    folder = config.JOBS_DIR / job["id"]
    q, p = job["metrics"]["quality"], job["metrics"]["preservation"]
    checks = "".join(
        f"<li>{html.escape(k.title())}: {v}%</li>" for k, v in p["checks"].items() if v is not None
    )
    steps = "".join(f"<li><b>{html.escape(s['name'])}</b>: {html.escape(s['detail'])}</li>" for s in job["steps"])
    rows = "".join(
        [
            _row("Resolution", f"{job['size']['before'][0]} x {job['size']['before'][1]}", f"{job['size']['after'][0]} x {job['size']['after'][1]}"),
            _row("Sharpness", q["sharpness"]["before"], q["sharpness"]["after"]),
            _row("Noise", q["noise"]["before"], q["noise"]["after"]),
            _row("Contrast", q["contrast"]["before"], q["contrast"]["after"]),
            _row("Brightness", q["brightness"]["before"], q["brightness"]["after"]),
        ]
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Restoration report {html.escape(job['filename'])}</title>
<style>body{{font-family:Inter,Arial,sans-serif;background:#efe7d8;color:#2b251d;margin:0;padding:40px}}main{{max-width:960px;margin:0 auto}}
h1{{letter-spacing:-.04em;font-weight:900;margin:0 0 4px}}.muted{{color:#5c5346}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:24px 0}}
figure{{margin:0;background:#f6f1e7;border:1px solid rgba(43,37,29,.1);border-radius:16px;padding:12px}}img{{width:100%;border-radius:10px}}
.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:24px 0}}.card{{background:#f6f1e7;border:1px solid rgba(43,37,29,.1);border-radius:16px;padding:18px}}
.card b{{font-size:34px;color:#c4633f;display:block}}table{{width:100%;border-collapse:collapse;background:#f6f1e7;border-radius:12px;overflow:hidden}}
td,th{{padding:10px 14px;text-align:left;border-bottom:1px solid rgba(43,37,29,.08)}}</style></head><body><main>
<h1>Restoration report</h1><p class="muted">{html.escape(job['filename'])} &middot; {html.escape(job['kind'].replace('_', ' '))} &middot; job {job['id']}</p>
<div class="grid"><figure><img src="{_thumb(folder / 'original.jpg')}" alt="Before"><figcaption>Before</figcaption></figure>
<figure><img src="{_thumb(folder / 'restored.jpg')}" alt="After"><figcaption>After</figcaption></figure></div>
<div class="cards"><div class="card"><b>{q['score']}</b>Restoration quality</div><div class="card"><b>{p['score']}</b>Preservation ({html.escape(p['verdict'])})</div><div class="card"><b>{job['metrics']['overall']}</b>Overall</div></div>
<h2>Measurements</h2><table><tr><th></th><th>Before</th><th>After</th></tr>{rows}</table>
<h2>Preservation checks</h2><ul>{checks}</ul>
<h2>Pipeline</h2><ul><li><b>Upscale</b>: {html.escape(job['methods']['upscale'])}</li><li><b>Faces</b>: {html.escape(job['methods']['face'])}</li>{steps}</ul>
<p class="muted">Scores are heuristic. Quality rewards sharpness gain, noise reduction and contrast. Preservation compares structure, edges, colour, face and text against the original.</p>
</main></body></html>"""


def batch_csv(jobs: list, errors: list) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["file", "status", "type", "quality", "preservation", "verdict", "overall", "upscale", "faces", "seconds", "error"])
    for j in jobs:
        w.writerow([
            j["filename"], "ok", j["kind"], j["metrics"]["quality"]["score"], j["metrics"]["preservation"]["score"],
            j["metrics"]["preservation"]["verdict"], j["metrics"]["overall"], j["methods"]["upscale"],
            j["diagnosis"]["faces"], round(j["timings_ms"]["total"] / 1000, 1), "",
        ])
    for e in errors:
        w.writerow([e["filename"], "failed", "", "", "", "", "", "", "", "", e["error"]])
    return buf.getvalue()
