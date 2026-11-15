import io

import cv2
import numpy as np
from PIL import Image, ImageOps

from . import config


class InvalidImageError(ValueError):
    pass


def load_image(data: bytes) -> np.ndarray:
    try:
        pil = Image.open(io.BytesIO(data))
        pil = ImageOps.exif_transpose(pil)
        if pil.mode in ("RGBA", "LA", "P"):
            pil = pil.convert("RGBA")
            canvas = Image.new("RGBA", pil.size, (255, 255, 255, 255))
            canvas.alpha_composite(pil)
            pil = canvas
        pil = pil.convert("RGB")
    except Exception as exc:
        raise InvalidImageError("This file is not a readable image.") from exc
    arr = np.array(pil)[:, :, ::-1].copy()
    h, w = arr.shape[:2]
    if min(h, w) < 16:
        raise InvalidImageError("Image is too small to restore. Minimum side is 16 px.")
    return arr


def limit_size(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    longest = max(h, w)
    if longest <= config.MAX_INPUT_SIDE:
        return img
    s = config.MAX_INPUT_SIDE / longest
    return cv2.resize(img, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)


_cascade = None


def _get_cascade():
    global _cascade
    if _cascade is None:
        try:
            _cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            if _cascade.empty():
                _cascade = False
        except Exception:
            _cascade = False
    return _cascade


def detect_faces(img: np.ndarray) -> list:
    cascade = _get_cascade()
    if not cascade:
        return []
    h, w = img.shape[:2]
    scale = 1.0
    work = img
    if max(h, w) > 800:
        scale = 800 / max(h, w)
        work = cv2.resize(img, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)
    gray = cv2.equalizeHist(cv2.cvtColor(work, cv2.COLOR_BGR2GRAY))
    min_side = max(24, int(min(gray.shape[:2]) * 0.08))
    found = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(min_side, min_side))
    faces = [tuple(int(v / scale) for v in f) for f in found]
    faces.sort(key=lambda f: f[2] * f[3], reverse=True)
    return faces


def estimate_noise(gray: np.ndarray) -> float:
    h, w = gray.shape
    if h < 4 or w < 4:
        return 0.0
    kernel = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], dtype=np.float32)
    resp = cv2.filter2D(gray.astype(np.float32), -1, kernel)[1:-1, 1:-1]
    return float(np.sum(np.abs(resp)) * np.sqrt(0.5 * np.pi) / (6.0 * (w - 2) * (h - 2)))


def measure(img: np.ndarray, normalize: bool = False) -> dict:
    work = img
    if normalize:
        h, w = img.shape[:2]
        s = 512 / max(h, w)
        work = cv2.resize(img, (max(1, round(w * s)), max(1, round(h * s))), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(work, cv2.COLOR_BGR2GRAY)
    return {
        "sharpness": round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 2),
        "noise": round(estimate_noise(gray), 2),
        "brightness": round(float(gray.mean()), 1),
        "contrast": round(float(gray.std()), 1),
    }


def diagnose(img: np.ndarray) -> dict:
    h, w = img.shape[:2]
    m = measure(img, normalize=True)
    faces = detect_faces(img)
    face_share = (faces[0][2] * faces[0][3]) / (h * w) if faces else 0.0
    kind = "id_photo" if faces and face_share > 0.01 else "document"
    issues = []
    if max(h, w) < 640:
        issues.append("low resolution")
    if m["sharpness"] < 60:
        issues.append("blurry")
    if m["noise"] > 5:
        issues.append("noisy")
    if m["brightness"] < 90:
        issues.append("too dark")
    elif m["brightness"] > 205:
        issues.append("washed out")
    if m["contrast"] < 40:
        issues.append("low contrast")
    return {
        "width": w,
        "height": h,
        "kind": kind,
        "faces": len(faces),
        "face_boxes": [list(f) for f in faces[:3]],
        "issues": issues,
        **m,
    }
