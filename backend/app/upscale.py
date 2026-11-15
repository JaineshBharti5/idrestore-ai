import threading

import cv2
import numpy as np

from . import config
from .enhance import unsharp


def choose_scale(img: np.ndarray, requested: int) -> int:
    longest = max(img.shape[:2])
    if requested in (1, 2, 4):
        scale = requested
    elif longest < 600:
        scale = 4
    elif longest < 1400:
        scale = 2
    else:
        scale = 1
    while scale > 1 and longest * scale > config.MAX_OUTPUT_SIDE:
        scale //= 2
    return scale


class Upscaler:
    def __init__(self):
        self.model = None
        self.name = "OpenCV Lanczos + unsharp"
        self.error = None
        self._loaded = False
        self._lock = threading.Lock()

    def load(self):
        if self._loaded:
            return
        self._loaded = True
        if not config.REALESRGAN_WEIGHTS.exists():
            self.error = "RealESRGAN_x4plus.pth not found in models folder"
            return
        try:
            import torch
            from basicsr.archs.rrdbnet_arch import RRDBNet
            from realesrgan import RealESRGANer

            net = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
            self.model = RealESRGANer(
                scale=4,
                model_path=str(config.REALESRGAN_WEIGHTS),
                model=net,
                tile=256,
                tile_pad=10,
                pre_pad=0,
                half=torch.cuda.is_available(),
            )
            self.name = "Real-ESRGAN x4plus"
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"

    @property
    def active(self) -> bool:
        self.load()
        return self.model is not None

    def upscale(self, img: np.ndarray, scale: int):
        if scale <= 1:
            return img, "none"
        self.load()
        if self.model is not None:
            try:
                with self._lock:
                    out, _ = self.model.enhance(img, outscale=scale)
                return out, self.name
            except Exception as exc:
                self.error = f"{type(exc).__name__}: {exc}"
        h, w = img.shape[:2]
        out = cv2.resize(img, (w * scale, h * scale), interpolation=cv2.INTER_LANCZOS4)
        return unsharp(out, 0.4, 1.0), "OpenCV Lanczos + unsharp"
