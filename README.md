# IDRestore AI: Employee Document Restorer

Restores degraded employee ID photos and scanned HR documents for HRMS migration, then checks that faces, text and layout stayed faithful to the original.

Stack: FastAPI, OpenCV, Real-ESRGAN, GFPGAN, Tesseract (optional), Vite vanilla JS.

## Run it (Windows, VS Code)

Full project document for submission: `docs/PROJECT_DOCUMENT.md`.

Backend, from the `backend` folder:

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend, from the `frontend` folder:

```
npm install
npm run dev
```

Open http://localhost:5173.

## AI advisor (Groq) and Ngrok

Copy `backend/.env.example` to `backend/.env` and fill in `GROQ_API_KEY` (from console.groq.com) and `NGROK_AUTHTOKEN` (from the Ngrok dashboard). Never commit `.env`. Restart uvicorn after editing it. The Studio then shows an AI advisor card for every result.

Public URL: run `npm run build` in `frontend`, then `python run_public.py` in `backend`. To serve everything from the backend instead, run `npm run build` once and open http://127.0.0.1:8000.

## Turn on the AI models (optional but recommended)

Without models the app still works using OpenCV (Lanczos upscale, bilateral face clean-up). The studio shows which engine is active.

1. Use Python 3.10 or 3.11 for this step. PyTorch wheels usually are not available for the newest Python versions.
2. `pip install -r requirements-ai.txt`
3. If `basicsr` fails with `functional_tensor`, open `basicsr/data/degradations.py` in your venv and change `from torchvision.transforms.functional_tensor import rgb_to_grayscale` to `from torchvision.transforms.functional import rgb_to_grayscale`.
4. Download these weights into `backend/models`:
   - RealESRGAN_x4plus.pth from the Real-ESRGAN releases page
   - GFPGANv1.4.pth from the GFPGAN releases page
5. Restart uvicorn. GFPGAN also downloads its face detector the first time it runs, so the first request needs internet.

## OCR text check (optional)

Install Tesseract for Windows, add it to PATH, then `pip install pytesseract`. For Hindi text set `IDRESTORE_OCR_LANG=eng+hin` before starting uvicorn.

## Test data and batch command

```
python make_samples.py --input path\to\clean_photos --out samples
python run_batch.py samples\degraded --out restored
```

`make_samples.py` degrades images (downscale, blur, noise, low contrast, heavy JPEG) and adds synthetic HR pages, so you get clean/degraded pairs. `run_batch.py` restores a folder and writes `summary.csv`.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | /api/health | Engine status (Real-ESRGAN, GFPGAN, OCR) and limits |
| POST | /api/restore | One file. Form fields: file, mode, scale, denoise, sharpen, contrast, fidelity |
| POST | /api/batch | Up to 20 files. Returns per-file results, errors, ZIP and CSV links |
| GET | /api/jobs/{id} | Stored result JSON |
| GET | /api/jobs/{id}/report | Downloadable HTML quality report |

Interactive docs at `/docs`.

## How it maps to the project objectives

| Objective | Where |
| --- | --- |
| Employee document data preparation | `preprocess.py`, `make_samples.py` |
| Employee image upscaling (Real-ESRGAN) | `upscale.py` |
| ID photo facial restoration (GFPGAN) | `face.py` |
| Document quality enhancement (OpenCV) | `enhance.py` |
| Record preservation evaluation | `evaluate.py` |
| Automated pipeline and testing | `pipeline.py`, `main.py` batch endpoint, `run_batch.py` |
| Restoration quality report | `report.py`, studio scores |

## Scores

Both scores are heuristics, so describe them that way in your report.

- Restoration quality (0 to 100): sharpness gain (45%), noise reduction (25%), contrast (30%), measured at the same size against a bicubic upscale of the original.
- Preservation (0 to 100): structure SSIM on low-passed images, edge layout match, colour drift in Lab a/b, face SSIM for ID photos, OCR text similarity for documents when Tesseract is installed.
- Verdict: Faithful at 85 or more, Review at 70 or more, otherwise Altered.

## Known limits

- Face detection for ID type detection uses OpenCV Haar cascades, so profile or tiny faces can be missed. Use the Document type selector to override.
- Generative restoration can invent detail. Keep the preservation report with every restored record and review anything marked Review or Altered.
- CPU Real-ESRGAN is slow on large images. Inputs are capped at 2000 px and outputs at 3200 px.
