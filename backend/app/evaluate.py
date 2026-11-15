import difflib
import re

import cv2
import numpy as np

from . import config
from .preprocess import detect_faces, measure

_ocr_ready = None

# Starting values. Calibrate them with a few of your own sharp and blurry scans.
BLUR_LOG_LOW = 1.0   # log10(v + 1) at or below this counts as fully blurred (v about 9)
BLUR_LOG_HIGH = 2.5  # log10(v + 1) at or above this counts as sharp (v about 315)
RECAPTURE_BELOW = 0.25
REVIEW_BELOW = 0.50


def ocr_available() -> bool:
    global _ocr_ready
    if _ocr_ready is None:
        try:
            import pytesseract

            pytesseract.get_tesseract_version()
            _ocr_ready = True
        except Exception:
            _ocr_ready = False
    return _ocr_ready


def ocr_text(img: np.ndarray) -> str:
    import pytesseract

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    try:
        raw = pytesseract.image_to_string(gray, lang=config.OCR_LANG)
    except Exception:
        raw = pytesseract.image_to_string(gray, lang="eng")
    return re.sub(r"\s+", " ", raw).strip().lower()


def ocr_words(img: np.ndarray):
    """How many words Tesseract can read with good confidence. None if OCR is unavailable."""
    if not ocr_available():
        return None
    try:
        import pytesseract

        h, w = img.shape[:2]
        s = min(1.0, 1600 / max(h, w))
        if s < 1.0:
            img = cv2.resize(img, (max(1, round(w * s)), max(1, round(h * s))), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        try:
            data = pytesseract.image_to_data(gray, lang=config.OCR_LANG, output_type=pytesseract.Output.DICT)
        except Exception:
            data = pytesseract.image_to_data(gray, lang="eng", output_type=pytesseract.Output.DICT)
        confs = []
        good = 0
        for text, conf in zip(data["text"], data["conf"]):
            text = str(text).strip()
            try:
                conf = float(conf)
            except (TypeError, ValueError):
                continue
            if conf < 0 or len(text) < 2 or not re.search(r"[A-Za-z0-9]", text):
                continue
            confs.append(conf)
            if conf >= 60:
                good += 1
        return {"words_read": good, "words_seen": len(confs), "mean_confidence": round(float(np.mean(confs))) if confs else 0}
    except Exception:
        return None


def absolute_sharpness(img: np.ndarray):
    """Resolution-independent sharpness of an image on its own, 0 to 1, plus the raw value."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    s = min(1.0, 800 / max(h, w))
    if s < 1.0:
        gray = cv2.resize(gray, (max(1, round(w * s)), max(1, round(h * s))), interpolation=cv2.INTER_AREA)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    t = 32
    hh, ww = (lap.shape[0] // t) * t, (lap.shape[1] // t) * t
    if hh == 0 or ww == 0:
        v = float(lap.var())
    else:
        blocks = lap[:hh, :ww].reshape(hh // t, t, ww // t, t).var(axis=(1, 3))
        v = float(np.percentile(blocks, 90))
    score = (np.log10(v + 1.0) - BLUR_LOG_LOW) / (BLUR_LOG_HIGH - BLUR_LOG_LOW)
    return _clip01(score), v


def ssim(a: np.ndarray, b: np.ndarray) -> float:
    a = a.astype(np.float64)
    b = b.astype(np.float64)
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    k, s = (11, 11), 1.5
    mu1, mu2 = cv2.GaussianBlur(a, k, s), cv2.GaussianBlur(b, k, s)
    v1 = cv2.GaussianBlur(a * a, k, s) - mu1 ** 2
    v2 = cv2.GaussianBlur(b * b, k, s) - mu2 ** 2
    cov = cv2.GaussianBlur(a * b, k, s) - mu1 * mu2
    m = ((2 * mu1 * mu2 + c1) * (2 * cov + c2)) / ((mu1 ** 2 + mu2 ** 2 + c1) * (v1 + v2 + c2))
    return float(m.mean())


def _gray_lowpass(img: np.ndarray, size: tuple, sigma: float = 2.0) -> np.ndarray:
    g = cv2.cvtColor(cv2.resize(img, size, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
    return cv2.GaussianBlur(g, (0, 0), sigma)


def _edges(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    s = 400 / max(h, w)
    small = cv2.resize(img, (max(1, round(w * s)), max(1, round(h * s))), interpolation=cv2.INTER_AREA)
    g = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    med = float(np.median(g))
    return cv2.Canny(g, int(max(0, 0.66 * med)), int(min(255, 1.33 * med + 20)))


def _clip01(x: float) -> float:
    return float(np.clip(x, 0.0, 1.0))


def layout_score(original: np.ndarray, restored: np.ndarray) -> float:
    eo = _edges(original)
    er = _edges(cv2.resize(restored, (original.shape[1], original.shape[0]), interpolation=cv2.INTER_AREA))
    if eo.shape != er.shape:
        er = cv2.resize(er, (eo.shape[1], eo.shape[0]), interpolation=cv2.INTER_NEAREST)
    kernel = np.ones((5, 5), np.uint8)
    do, dr = cv2.dilate(eo, kernel), cv2.dilate(er, kernel)
    recall = float(np.count_nonzero((eo > 0) & (dr > 0)) / max(1, np.count_nonzero(eo)))
    precision = float(np.count_nonzero((er > 0) & (do > 0)) / max(1, np.count_nonzero(er)))
    return _clip01(0.65 * recall + 0.35 * precision)


def color_drift(original: np.ndarray, restored: np.ndarray) -> float:
    o = cv2.cvtColor(original.astype(np.float32) / 255.0, cv2.COLOR_BGR2LAB)
    r = cv2.cvtColor(
        cv2.resize(restored, (original.shape[1], original.shape[0]), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0,
        cv2.COLOR_BGR2LAB,
    )
    da = float(o[..., 1].mean() - r[..., 1].mean())
    db = float(o[..., 2].mean() - r[..., 2].mean())
    return float(np.hypot(da, db))


def face_similarity(baseline: np.ndarray, restored: np.ndarray, faces: list):
    if not faces:
        return None
    x, y, w, h = faces[0]
    sx = restored.shape[1] / baseline.shape[1]
    sy = restored.shape[0] / baseline.shape[0]
    ox0, oy0, ox1, oy1 = x, y, x + w, y + h
    rx0, ry0, rx1, ry1 = int(x * sx), int(y * sy), int((x + w) * sx), int((y + h) * sy)
    a = baseline[oy0:oy1, ox0:ox1]
    b = restored[ry0:ry1, rx0:rx1]
    if a.size == 0 or b.size == 0:
        return None
    return _clip01(ssim(_gray_lowpass(a, (96, 96), 1.5), _gray_lowpass(b, (96, 96), 1.5)))


def text_similarity(baseline: np.ndarray, restored: np.ndarray):
    if not ocr_available():
        return None, None
    before = ocr_text(baseline)
    after = ocr_text(restored)
    if len(before) < 8 and len(after) < 8:
        return None, {"chars_before": len(before), "chars_after": len(after)}
    ratio = difflib.SequenceMatcher(None, before, after).ratio()
    return _clip01(ratio), {"chars_before": len(before), "chars_after": len(after)}


def readability(original: np.ndarray, restored: np.ndarray, kind: str) -> dict:
    blur, raw = absolute_sharpness(original)
    ocr_before = ocr_words(original)
    ocr_after = ocr_words(restored)

    status = "ok"
    if blur < RECAPTURE_BELOW:
        status = "recapture"
    elif blur < REVIEW_BELOW:
        status = "review"
    if kind == "document" and ocr_after is not None and ocr_after["words_read"] == 0 and status == "ok":
        status = "review"

    messages = {
        "ok": "The source image is sharp enough to restore reliably.",
        "review": "The source image is soft. Check every field by eye before storing this as the record.",
        "recapture": "The source image is too blurry to recover reliably. Re-scan or re-photograph the original. "
                     "Do not store this output as the record, because fine text and faces would be guessed, not recovered.",
    }
    return {
        "status": status,
        "source_sharpness": round(blur * 100),
        "raw_value": round(raw, 1),
        "ocr_before": ocr_before,
        "ocr_after": ocr_after,
        "message": messages[status],
    }


def evaluate(original: np.ndarray, restored: np.ndarray, kind: str) -> dict:
    h, w = restored.shape[:2]
    baseline = cv2.resize(original, (w, h), interpolation=cv2.INTER_CUBIC)
    before = measure(baseline)
    after = measure(restored)

    gain = after["sharpness"] / max(before["sharpness"], 1e-6)
    if before["noise"] < 2.0:
        noise_s = 1.0
        noise_red = 0.0
    else:
        noise_red = (before["noise"] - after["noise"]) / before["noise"] * 100.0
        noise_s = _clip01(noise_red / 50.0)
    sharp_s = _clip01(np.log(max(gain, 1e-6)) / np.log(3.0))
    contrast_s = _clip01(after["contrast"] / 50.0)
    quality = 100.0 * (0.45 * sharp_s + 0.25 * noise_s + 0.30 * contrast_s)

    read = readability(original, restored, kind)
    # A blurry source cannot score high, however much the pipeline changed it.
    quality *= 0.2 + 0.8 * (read["source_sharpness"] / 100.0)

    small = (min(original.shape[1], 512), min(original.shape[0], 512))
    structure = _clip01(ssim(_gray_lowpass(original, small), _gray_lowpass(restored, small)))
    layout = layout_score(original, restored)
    drift = color_drift(original, restored)
    color = _clip01(1.0 - drift / 12.0)

    faces = detect_faces(baseline) if kind == "id_photo" else []
    face = face_similarity(baseline, restored, faces)
    text, text_info = (None, None)
    if kind == "document":
        text, text_info = text_similarity(baseline, restored)

    parts = [("structure", structure, 0.35), ("layout", layout, 0.20), ("color", color, 0.15)]
    if face is not None:
        parts.append(("face", face, 0.30))
    if text is not None:
        parts.append(("text", text, 0.30))
    total_w = sum(p[2] for p in parts)
    preservation = sum(p[1] * p[2] for p in parts) / total_w * 100.0
    verdict = "Faithful" if preservation >= 85 else "Review" if preservation >= 70 else "Altered"
    overall = 0.55 * quality + 0.45 * preservation
    if read["status"] == "recapture":
        overall = min(overall, 40.0)
    elif read["status"] == "review":
        overall = min(overall, 70.0)

    return {
        "quality": {
            "score": round(quality),
            "sharpness": {"before": before["sharpness"], "after": after["sharpness"], "gain": round(gain, 2)},
            "noise": {"before": before["noise"], "after": after["noise"], "reduction_pct": round(noise_red, 1)},
            "contrast": {"before": before["contrast"], "after": after["contrast"]},
            "brightness": {"before": before["brightness"], "after": after["brightness"]},
        },
        "preservation": {
            "score": round(preservation),
            "verdict": verdict,
            "checks": {
                "structure": round(structure * 100),
                "layout": round(layout * 100),
                "color": round(color * 100),
                "face": None if face is None else round(face * 100),
                "text": None if text is None else round(text * 100),
            },
            "text_info": text_info,
            "ocr_available": ocr_available(),
        },
        "readability": read,
        "overall": round(overall),
    }