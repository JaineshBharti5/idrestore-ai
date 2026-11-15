import threading

import cv2
import numpy as np

from . import config
from .enhance import clahe_luma, unsharp
from .preprocess import detect_faces


class FaceRestorer:
    def __init__(self):
        self.model = None
        self.name = "OpenCV face clean-up"
        self.error = None
        self._loaded = False
        self._lock = threading.Lock()

    def load(self):
        if self._loaded:
            return
        self._loaded = True
        if not config.GFPGAN_WEIGHTS.exists():
            self.error = "GFPGANv1.4.pth not found in models folder"
            return
        try:
            from gfpgan import GFPGANer

            self.model = GFPGANer(
                model_path=str(config.GFPGAN_WEIGHTS),
                upscale=1,
                arch="clean",
                channel_multiplier=2,
                bg_upsampler=None,
            )
            self.name = "GFPGAN v1.4"
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"

    @property
    def active(self) -> bool:
        self.load()
        return self.model is not None

    def _opencv_fallback(self, img: np.ndarray, faces: list) -> np.ndarray:
        out = img.copy()
        h, w = img.shape[:2]
        for x, y, fw, fh in faces:
            pad = int(0.2 * max(fw, fh))
            x0, y0 = max(0, x - pad), max(0, y - pad)
            x1, y1 = min(w, x + fw + pad), min(h, y + fh + pad)
            roi = out[y0:y1, x0:x1]
            if roi.size == 0:
                continue
            smooth = cv2.bilateralFilter(roi, 7, 40, 7)
            smooth = unsharp(smooth, 0.5, 1.0)
            smooth = clahe_luma(smooth, 1.2, 0.4)
            mask = np.zeros(roi.shape[:2], dtype=np.float32)
            cv2.ellipse(
                mask,
                (roi.shape[1] // 2, roi.shape[0] // 2),
                (max(1, roi.shape[1] // 2 - 2), max(1, roi.shape[0] // 2 - 2)),
                0, 0, 360, 1.0, -1,
            )
            mask = cv2.GaussianBlur(mask, (0, 0), max(2.0, roi.shape[1] / 12))[..., None]
            out[y0:y1, x0:x1] = (smooth * mask + roi * (1 - mask)).astype(np.uint8)
        return out

    def restore(self, img: np.ndarray, fidelity: float):
        faces = detect_faces(img)
        if not faces:
            return img, {"faces": 0, "method": "skipped, no face found"}
        self.load()
        if self.model is not None:
            try:
                with self._lock:
                    _, _, restored = self.model.enhance(
                        img, has_aligned=False, only_center_face=False, paste_back=True
                    )
                if restored is not None:
                    if restored.shape != img.shape:
                        restored = cv2.resize(restored, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_CUBIC)
                    blended = cv2.addWeighted(restored, fidelity, img, 1 - fidelity, 0)
                    return blended, {"faces": len(faces), "method": f"{self.name}, identity blend {int(fidelity * 100)}%"}
            except Exception as exc:
                self.error = f"{type(exc).__name__}: {exc}"
        return self._opencv_fallback(img, faces), {"faces": len(faces), "method": "OpenCV face clean-up"}
