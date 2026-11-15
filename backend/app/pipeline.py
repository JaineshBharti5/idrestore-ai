import json
import time
import uuid
from dataclasses import asdict, dataclass

import cv2

from . import advisor, config, enhance, evaluate
from .face import FaceRestorer
from .preprocess import InvalidImageError, diagnose, limit_size, load_image
from .upscale import Upscaler, choose_scale


@dataclass
class Options:
    mode: str = "auto"
    scale: int = 0
    denoise: bool = True
    sharpen: float = 0.5
    contrast: float = 0.5
    fidelity: float = 0.7

    def clean(self) -> "Options":
        self.mode = self.mode if self.mode in ("auto", "id_photo", "document") else "auto"
        self.scale = self.scale if self.scale in (0, 1, 2, 4) else 0
        self.sharpen = min(1.0, max(0.0, float(self.sharpen)))
        self.contrast = min(1.0, max(0.0, float(self.contrast)))
        self.fidelity = min(1.0, max(0.0, float(self.fidelity)))
        return self


class Pipeline:
    def __init__(self):
        self.upscaler = Upscaler()
        self.faces = FaceRestorer()

    def status(self) -> dict:
        return {
            "status": "ok",
            "engines": {
                "upscale": {"active": self.upscaler.active, "name": self.upscaler.name, "note": self.upscaler.error},
                "face": {"active": self.faces.active, "name": self.faces.name, "note": self.faces.error},
                "ocr": {"active": evaluate.ocr_available(), "lang": config.OCR_LANG},
                "advisor": {"active": advisor.is_configured(), "name": config.GROQ_MODEL},
            },
            "limits": {"max_upload_mb": config.MAX_UPLOAD_MB, "max_batch_files": config.MAX_BATCH_FILES},
        }

    def run(self, data: bytes, filename: str, opts: Options) -> dict:
        opts = opts.clean()
        t0 = time.perf_counter()
        original = limit_size(load_image(data))
        diag = diagnose(original)
        kind = diag["kind"] if opts.mode == "auto" else opts.mode
        t1 = time.perf_counter()

        steps = []
        work, s = enhance.pre(original, kind, diag, opts, self.upscaler.active)
        steps += s
        scale = choose_scale(work, opts.scale)
        upscaled, up_method = self.upscaler.upscale(work, scale)
        steps.append({"name": "Upscale", "detail": f"{scale}x with {up_method}" if scale > 1 else "Skipped, resolution is already high"})
        t2 = time.perf_counter()

        face_info = {"faces": 0, "method": "skipped, document mode"}
        if kind == "id_photo":
            upscaled, face_info = self.faces.restore(upscaled, opts.fidelity)
            steps.append({"name": "Face restore", "detail": f"{face_info['faces']} face(s), {face_info['method']}"})
        t3 = time.perf_counter()

        final, s = enhance.post(upscaled, kind, diag, opts, model_sharp=up_method.startswith("Real-ESRGAN"))
        steps += s
        t4 = time.perf_counter()

        metrics = evaluate.evaluate(original, final, kind)
        t5 = time.perf_counter()

        job_id = uuid.uuid4().hex[:12]
        folder = config.JOBS_DIR / job_id
        folder.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(folder / "original.jpg"), original, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(str(folder / "restored.png"), final)
        cv2.imwrite(str(folder / "restored.jpg"), final, [cv2.IMWRITE_JPEG_QUALITY, 93])

        base = f"/files/jobs/{job_id}"
        job = {
            "id": job_id,
            "filename": filename,
            "kind": kind,
            "options": asdict(opts),
            "diagnosis": diag,
            "methods": {"upscale": up_method, "face": face_info["method"]},
            "steps": steps,
            "metrics": metrics,
            "size": {"before": [original.shape[1], original.shape[0]], "after": [final.shape[1], final.shape[0]]},
            "timings_ms": {
                "prepare": round((t1 - t0) * 1000),
                "upscale": round((t2 - t1) * 1000),
                "faces": round((t3 - t2) * 1000),
                "enhance": round((t4 - t3) * 1000),
                "evaluate": round((t5 - t4) * 1000),
                "total": round((t5 - t0) * 1000),
            },
            "urls": {
                "original": f"{base}/original.jpg",
                "restored": f"{base}/restored.jpg",
                "download": f"{base}/restored.png",
                "report": f"/api/jobs/{job_id}/report",
            },
        }
        (folder / "job.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
        return job


__all__ = ["Pipeline", "Options", "InvalidImageError"]
