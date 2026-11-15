import io
import json
import re
import uuid
import zipfile
from typing import List

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import advisor, config, report
from .pipeline import InvalidImageError, Options, Pipeline

app = FastAPI(title="IDRestore AI", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = Pipeline()
ID_RE = re.compile(r"^[a-f0-9]{12}$")


def read_upload(file: UploadFile) -> bytes:
    name = file.filename or "upload"
    ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in config.ALLOWED_EXT:
        raise HTTPException(400, f"{name}: unsupported type. Use JPG, PNG, WEBP, BMP or TIFF.")
    data = file.file.read()
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"{name}: larger than {config.MAX_UPLOAD_MB} MB.")
    if not data:
        raise HTTPException(400, f"{name}: file is empty.")
    return data


def load_job(job_id: str) -> dict:
    if not ID_RE.match(job_id):
        raise HTTPException(404, "Job not found.")
    path = config.JOBS_DIR / job_id / "job.json"
    if not path.exists():
        raise HTTPException(404, "Job not found.")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/health")
def health():
    return pipeline.status()


@app.post("/api/restore")
def restore(
    file: UploadFile = File(...),
    mode: str = Form("auto"),
    scale: int = Form(0),
    denoise: bool = Form(True),
    sharpen: float = Form(0.5),
    contrast: float = Form(0.5),
    fidelity: float = Form(0.7),
):
    data = read_upload(file)
    opts = Options(mode, scale, denoise, sharpen, contrast, fidelity)
    try:
        return pipeline.run(data, file.filename or "upload", opts)
    except InvalidImageError as exc:
        raise HTTPException(400, str(exc))


@app.post("/api/batch")
def batch(
    files: List[UploadFile] = File(...),
    mode: str = Form("auto"),
    scale: int = Form(0),
    denoise: bool = Form(True),
    sharpen: float = Form(0.5),
    contrast: float = Form(0.5),
    fidelity: float = Form(0.7),
):
    if len(files) > config.MAX_BATCH_FILES:
        raise HTTPException(400, f"Batch is limited to {config.MAX_BATCH_FILES} files.")
    opts = Options(mode, scale, denoise, sharpen, contrast, fidelity)
    jobs, errors = [], []
    for f in files:
        name = f.filename or "upload"
        try:
            data = read_upload(f)
            jobs.append(pipeline.run(data, name, Options(**vars(opts))))
        except HTTPException as exc:
            errors.append({"filename": name, "error": exc.detail})
        except InvalidImageError as exc:
            errors.append({"filename": name, "error": str(exc)})
        except Exception as exc:
            errors.append({"filename": name, "error": f"Unexpected failure: {type(exc).__name__}"})

    batch_id = uuid.uuid4().hex[:12]
    folder = config.BATCHES_DIR / batch_id
    folder.mkdir(parents=True, exist_ok=True)
    csv_text = report.batch_csv(jobs, errors)
    (folder / "summary.csv").write_text(csv_text, encoding="utf-8")
    with zipfile.ZipFile(folder / "restored.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for j in jobs:
            stem = j["filename"].rsplit(".", 1)[0]
            z.write(config.JOBS_DIR / j["id"] / "restored.png", f"{stem}_restored.png")
        z.writestr("summary.csv", csv_text)
    summary = {
        "id": batch_id,
        "total": len(files),
        "ok": len(jobs),
        "failed": len(errors),
        "jobs": jobs,
        "errors": errors,
        "urls": {"zip": f"/files/batches/{batch_id}/restored.zip", "csv": f"/files/batches/{batch_id}/summary.csv"},
    }
    (folder / "batch.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    return JSONResponse(load_job(job_id))


@app.get("/api/jobs/{job_id}/report")
def get_report(job_id: str):
    job = load_job(job_id)
    return HTMLResponse(
        report.job_html(job),
        headers={"Content-Disposition": f'attachment; filename="restoration_report_{job_id}.html"'},
    )


@app.post("/api/jobs/{job_id}/advice")
def job_advice(job_id: str):
    job = load_job(job_id)
    path = config.JOBS_DIR / job_id / "advice.json"
    if path.exists():
        return JSONResponse(json.loads(path.read_text(encoding="utf-8")))
    if not advisor.is_configured():
        raise HTTPException(503, "AI advisor is off. Add GROQ_API_KEY to backend/.env and restart the server.")
    try:
        result = advisor.advise(job)
    except ValueError as exc:
        raise HTTPException(502, f"Failed to parse AI response: {exc}")
    except Exception as exc:
        raise HTTPException(502, f"AI advisor failed: {type(exc).__name__}")
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


app.mount("/files", StaticFiles(directory=str(config.OUTPUT_DIR)), name="files")

if config.FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(config.FRONTEND_DIST), html=True), name="frontend")
