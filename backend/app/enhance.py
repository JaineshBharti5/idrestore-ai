import cv2
import numpy as np


def unsharp(img: np.ndarray, amount: float, sigma: float = 1.2) -> np.ndarray:
    if amount <= 0:
        return img
    blur = cv2.GaussianBlur(img, (0, 0), sigma)
    return cv2.addWeighted(img, 1 + amount, blur, -amount, 0)


def denoise(img: np.ndarray, noise: float) -> np.ndarray:
    h = float(np.clip(noise * 0.9, 2.5, 9))
    return cv2.fastNlMeansDenoisingColored(img, None, h, h * 1.2, 7, 21)


def clahe_luma(img: np.ndarray, clip: float, blend: float) -> np.ndarray:
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    boosted = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8)).apply(l)
    l = cv2.addWeighted(boosted, blend, l, 1 - blend, 0)
    return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)


def adjust_brightness(img: np.ndarray, target: float = 125.0):
    mean = float(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).mean())
    if abs(mean - target) < 12 or mean < 1:
        return img, None
    gamma = float(np.clip(np.log(target / 255.0) / np.log(max(mean, 1.0) / 255.0), 0.6, 1.6))
    lut = (np.power(np.arange(256) / 255.0, gamma) * 255).clip(0, 255).astype(np.uint8)
    return cv2.LUT(img, lut), round(gamma, 2)


def auto_levels(img: np.ndarray, low: float = 0.5, high: float = 99.5):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    lo, hi = np.percentile(gray, [low, high])
    if hi - lo < 20 or hi >= 215:
        return img, False
    out = (img.astype(np.float32) - lo) * (255.0 / (hi - lo))
    return np.clip(out, 0, 255).astype(np.uint8), True


def flatten_background(img: np.ndarray, strength: float = 0.6):
    h, w = img.shape[:2]
    s = min(1.0, 800 / max(h, w))
    small = cv2.resize(img, (max(1, round(w * s)), max(1, round(h * s))), interpolation=cv2.INTER_AREA)
    k = max(15, (min(small.shape[:2]) // 25) | 1)
    k = k if k % 2 == 1 else k + 1
    bg = cv2.morphologyEx(small, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    bg = cv2.medianBlur(bg, min(k, 255))
    bg_gray = cv2.cvtColor(bg, cv2.COLOR_BGR2GRAY)
    paper = bg_gray > 120
    sat = float(cv2.cvtColor(small, cv2.COLOR_BGR2HSV)[..., 1].mean())
    if paper.mean() < 0.7 or sat > 35:
        return img, False
    spread = float(np.percentile(bg_gray[paper], 90) - np.percentile(bg_gray[paper], 10))
    if spread < 35:
        return img, False
    bg = cv2.resize(bg, (w, h), interpolation=cv2.INTER_LINEAR)
    flat = cv2.divide(img, np.maximum(bg, 1), scale=255)
    return cv2.addWeighted(flat, strength, img, 1 - strength, 0), True


def _psf(sx: float, sy: float) -> np.ndarray:
    kx = int(2 * np.ceil(3 * max(sx, 0.3)) + 1)
    ky = int(2 * np.ceil(3 * max(sy, 0.3)) + 1)
    gx = cv2.getGaussianKernel(kx, max(sx, 0.3))
    gy = cv2.getGaussianKernel(ky, max(sy, 0.3))
    return (gy @ gx.T).astype(np.float32)


def _rl_tv(y: np.ndarray, k: np.ndarray, iters: int, lam: float) -> np.ndarray:
    est = y.copy()
    kf = np.ascontiguousarray(k[::-1, ::-1])
    for _ in range(iters):
        conv = cv2.filter2D(est, -1, k, borderType=cv2.BORDER_REFLECT)
        corr = cv2.filter2D(y / np.maximum(conv, 1e-3), -1, kf, borderType=cv2.BORDER_REFLECT)
        gy, gx = np.gradient(est)
        mag = np.sqrt(gx * gx + gy * gy + 1e-6)
        div = np.gradient(gx / mag, axis=1) + np.gradient(gy / mag, axis=0)
        est = np.clip(est * corr / np.maximum(1.0 - lam * div, 0.5), 0, 1.5)
    return np.clip(est, 0, 1).astype(np.float32)


def _lapvar(a: np.ndarray) -> float:
    return float(cv2.Laplacian(a, cv2.CV_32F).var()) + 1e-9


def _noise(a: np.ndarray) -> float:
    kernel = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], dtype=np.float32)
    r = cv2.filter2D(a * 255.0, -1, kernel)[1:-1, 1:-1]
    h, w = a.shape
    return float(np.sum(np.abs(r)) * np.sqrt(0.5 * np.pi) / (6.0 * max(1, (w - 2) * (h - 2))))


def estimate_blur(y: np.ndarray):
    gx = cv2.Sobel(y, cv2.CV_32F, 1, 0, ksize=1) / 2
    gy = cv2.Sobel(y, cv2.CV_32F, 0, 1, ksize=1) / 2
    found = []
    for g, k in ((gx, (15, 1)), (gy, (1, 15))):
        ag = np.abs(g)
        thr = max(0.02, float(np.percentile(ag, 99)))
        ker = np.ones(k, np.uint8)
        contrast = cv2.dilate(y, ker) - cv2.erode(y, ker)
        peak = cv2.dilate(ag, np.ones((3, 3), np.uint8)) == ag
        mask = (ag >= thr) & peak & (contrast > 0.25)
        if int(mask.sum()) < 20:
            return None
        found.append(float(np.median(contrast[mask] / (ag[mask] * 2.5066))))
    sx, sy = found
    if min(sx, sy) / max(sx, sy) < 0.35:
        return sx * 1.1, sy * 1.1
    sigma = max(sx, sy) * 1.15
    return sigma, sigma


def deblur(img: np.ndarray, strength: float = 1.0):
    ycc = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    y = ycc[..., 0].astype(np.float32) / 255.0
    est = estimate_blur(y)
    if est is None:
        return img, None
    sx, sy = min(est[0], 4.0) * strength, min(est[1], 4.0) * strength
    if max(sx, sy) < 0.8:
        return img, None
    out = _rl_tv(y, _psf(sx, sy), 20, 0.006)
    ycc[..., 0] = np.clip(out * 255.0, 0, 255).astype(np.uint8)
    return cv2.cvtColor(ycc, cv2.COLOR_YCrCb2BGR), (round(sx, 2), round(sy, 2))


def pre(img: np.ndarray, kind: str, diag: dict, opts, model_active: bool):
    steps = []
    if opts.denoise and (diag["noise"] > 2.5 or "noisy" in diag["issues"]):
        img = denoise(img, diag["noise"])
        steps.append({"name": "Denoise", "detail": f"Non-local means, estimated sigma {diag['noise']}"})
    else:
        steps.append({"name": "Denoise", "detail": "Skipped, image is already clean" if opts.denoise else "Turned off"})
    if model_active:
        steps.append({"name": "Deblur", "detail": "Left to Real-ESRGAN"})
    elif opts.sharpen <= 0:
        steps.append({"name": "Deblur", "detail": "Turned off"})
    else:
        img, psf = deblur(img, 0.7 + 0.3 * opts.sharpen)
        steps.append({"name": "Deblur", "detail": f"Richardson-Lucy with TV, blur sigma {psf[0]} x {psf[1]}" if psf else "Skipped, no blur detected"})
    return img, steps


def post(img: np.ndarray, kind: str, diag: dict, opts, model_sharp: bool):
    steps = []
    if kind == "document":
        img, flattened = flatten_background(img)
        steps.append({"name": "Background", "detail": "Flattened uneven paper tint" if flattened else "Already even"})
        img, stretched = auto_levels(img)
        steps.append({"name": "Levels", "detail": "Stretched 0.5 to 99.5 percentile" if stretched else "Already full range"})
    else:
        img, gamma = adjust_brightness(img)
        steps.append({"name": "Brightness", "detail": f"Gamma {gamma}" if gamma else "Already balanced"})
    if opts.contrast > 0 and kind != "document":
        clip = round(0.8 + 1.6 * opts.contrast, 2)
        img = clahe_luma(img, clip, 0.35)
        steps.append({"name": "Contrast", "detail": f"CLAHE clip {clip}, blended 35%"})
    amount = round(float((0.1 + 0.5 * opts.sharpen) * (0.5 if model_sharp else 1.0)), 2)
    img = unsharp(img, amount, 1.0)
    steps.append({"name": "Sharpen", "detail": f"Unsharp mask amount {amount}"})
    return img, steps
