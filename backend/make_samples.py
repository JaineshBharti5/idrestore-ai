import argparse
import random
from pathlib import Path

import cv2
import numpy as np


def degrade(img, rng):
    h, w = img.shape[:2]
    small = cv2.resize(img, (max(32, int(w * rng.uniform(0.25, 0.45))), max(32, int(h * rng.uniform(0.25, 0.45)))), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), rng.uniform(0.8, 2.0))
    noise = np.random.default_rng(rng.randint(0, 10_000)).normal(0, rng.uniform(6, 16), small.shape)
    small = np.clip(small.astype(np.float32) + noise, 0, 255)
    alpha = rng.uniform(0.6, 0.85)
    small = np.clip((small - 128) * alpha + 128 + rng.uniform(-25, 15), 0, 255).astype(np.uint8)
    ok, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, rng.randint(15, 35)])
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)


def synthetic_document(rng, idx):
    page = np.full((1100, 800, 3), 245, np.uint8)
    cv2.putText(page, f"EMPLOYEE RECORD {1000 + idx}", (60, 90), cv2.FONT_HERSHEY_DUPLEX, 1.1, (30, 30, 30), 2, cv2.LINE_AA)
    cv2.line(page, (60, 120), (740, 120), (60, 60, 60), 2)
    labels = ["Name", "Employee ID", "Department", "Joining date", "Manager", "Location", "Phone", "Email"]
    for i, label in enumerate(labels):
        y = 190 + i * 70
        cv2.putText(page, f"{label}:", (60, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (50, 50, 50), 2, cv2.LINE_AA)
        cv2.putText(page, f"Sample value {rng.randint(100, 999)}", (300, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2, cv2.LINE_AA)
        cv2.line(page, (60, y + 14), (740, y + 14), (170, 170, 170), 1)
    cv2.circle(page, (640, 900), 70, (60, 60, 190), 3)
    cv2.putText(page, "VERIFIED", (584, 908), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (60, 60, 190), 2, cv2.LINE_AA)
    return page


def main():
    ap = argparse.ArgumentParser(description="Build a degraded test dataset")
    ap.add_argument("--input", help="Folder of clean images such as ID photos")
    ap.add_argument("--out", default="samples")
    ap.add_argument("--documents", type=int, default=4, help="Synthetic document pages to add")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    out = Path(args.out)
    (out / "clean").mkdir(parents=True, exist_ok=True)
    (out / "degraded").mkdir(parents=True, exist_ok=True)

    sources = []
    if args.input:
        for p in sorted(Path(args.input).iterdir()):
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
                img = cv2.imread(str(p))
                if img is not None:
                    sources.append((p.stem, img))
    for i in range(args.documents):
        sources.append((f"document_{i + 1}", synthetic_document(rng, i)))

    for name, img in sources:
        cv2.imwrite(str(out / "clean" / f"{name}.png"), img)
        cv2.imwrite(str(out / "degraded" / f"{name}.jpg"), degrade(img, rng))
    print(f"Wrote {len(sources)} pairs to {out.resolve()}")


if __name__ == "__main__":
    main()
