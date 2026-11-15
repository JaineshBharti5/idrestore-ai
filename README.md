# IDRestore AI

Restore faded, noisy and low-resolution employee ID photos and scanned HR documents before they go into an HRMS, and know when an image is too damaged to trust.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688?logo=fastapi&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-frontend-646CFF?logo=vite&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-CUDA%20optional-EE4C2C?logo=pytorch&logoColor=white)

## Why this exists

Legacy HR records are full of old ID card photos and scans. Before digitising them into an HRMS, someone has to clean them up, and then someone has to decide whether the result can be trusted as the record. IDRestore AI does both:

1. It restores the image with a classical + deep-learning pipeline.
2. It measures how much the output still matches the original.
3. It checks whether the **source** was sharp enough to restore at all, and says so plainly when it was not.

## Features

- **Upscaling** with Real-ESRGAN x4, with an OpenCV Lanczos + unsharp fallback when the model is not installed.
- **Face restoration** with GFPGAN v1.4, blended with the original face through an adjustable identity slider.
- **Enhancement**: denoise, levels, CLAHE contrast and unsharp masking, each adjustable.
- **Preservation checks**: structure, layout, colour, face and text (OCR with Tesseract) compared against the original.
- **Source readability gate**: measures the sharpness of the original and returns `ok`, `review` or `recapture`. A too-blurry source gets a clear "re-scan needed" warning instead of a high score.
- **AI advisor** (Groq): reads the measurements and explains the result to HR in plain language. It never sees the image, and its verdict can never override the readability gate.
- **Batch mode**: up to 20 images, with a restored ZIP and a summary CSV.
- **Reports**: per-image JSON and a downloadable HTML report.
- **Public sharing**: optional ngrok tunnel for demos.

## How it works

| Step | What happens |
|---|---|
| Prepare | Load, fix orientation, measure blur and noise, detect the document type |
| Upscale | Real-ESRGAN x4 (OpenCV fallback) |
| Faces | GFPGAN, blended with the original (ID photo mode only) |
| Enhance | Denoise, levels, CLAHE contrast, unsharp |
| Verify | Structure, layout, colour, face and text checks, plus the readability gate |
| Report | JSON, HTML report, ZIP and CSV for batches |

## Be honest about limits

- Restoration cannot bring back detail that is not in the file. A heavily out-of-focus or heavily compressed image will not become readable, and a model that appears to make it readable is guessing the text and faces.
- GFPGAN generates facial detail. Keep the identity blend below 100% and review ID photos by eye.
- Quality and preservation scores are heuristics. Use the `readability` status and human review for decisions about records.
- The images in the website's Gallery section are illustrations of the kind of damage the pipeline repairs. They are not real outputs.

## Tech stack

- **Backend:** Python, FastAPI, Uvicorn, OpenCV, PyTorch, Real-ESRGAN, GFPGAN, Tesseract (pytesseract)
- **Frontend:** Vite, vanilla JavaScript
- **AI advisor:** Groq API
- **Public URL (optional):** pyngrok

## Getting started

### Prerequisites

- Python 3.12 and Node.js 18+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed and on your PATH (for the text check)
- A [Groq API key](https://console.groq.com) for the AI advisor (optional)
- An NVIDIA GPU with CUDA PyTorch is optional but much faster

### 1. Clone

```bash
git clone https://github.com/JaineshBharti5/idrestore-ai.git
cd idrestore-ai
```

### 2. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
pip install -r requirements-ai.txt   # deep-learning models
```

Create `backend/.env` from the example and add your keys:

```
GROQ_API_KEY=your_groq_key
NGROK_AUTHTOKEN=your_ngrok_token   # only needed for run_public.py
```

Never commit `.env`. It is already in `.gitignore`.

### 3. Model weights

The weights are too large for GitHub, so download them into `backend/models/`:

```bash
cd backend/models
curl -L -o RealESRGAN_x4plus.pth https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth
curl -L -o GFPGANv1.4.pth https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth
```

Without the weights the app still runs with the OpenCV fallback.

### 4. Run the backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Check that it is healthy at `http://127.0.0.1:8000/api/health`. It lists which engines (upscaler, face restorer, OCR, advisor) are active.

### 5. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

### Optional: share a public URL

```bash
cd frontend && npm run build
cd ../backend && python run_public.py
```

## Using the API

Interactive docs are at `http://127.0.0.1:8000/docs`.

```bash
curl -X POST http://127.0.0.1:8000/api/restore \
  -F "file=@old_id.jpg" \
  -F "mode=auto" \
  -F "scale=0"
```

| Field | Values |
|---|---|
| `mode` | `auto`, `id_photo`, `document` |
| `scale` | `0` (auto), `1`, `2`, `4` |

Limits: 15 MB per file, 20 files per batch. Supported formats: JPG, PNG, WEBP, BMP, TIFF.

Each result includes a `readability` block:

```json
{
  "status": "recapture",
  "source_sharpness": 0,
  "message": "The source image is too blurry to recover reliably. Re-scan or re-photograph the original..."
}
```

## Speed

Restoring a ~500 x 1100 px image took about 100 s on CPU and about 8 s on an RTX 3050 laptop GPU (after the models loaded). Install a CUDA build of PyTorch from [pytorch.org](https://pytorch.org/get-started/locally/) to use your GPU.

## Project structure

```
idrestore-ai/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI routes
│   │   ├── pipeline.py      # orchestrates the restore steps
│   │   ├── preprocess.py    # loading, diagnosis, face detection
│   │   ├── upscale.py       # Real-ESRGAN with OpenCV fallback
│   │   ├── face.py          # GFPGAN face restoration
│   │   ├── enhance.py       # denoise, levels, CLAHE, unsharp
│   │   ├── evaluate.py      # preservation checks and readability gate
│   │   ├── advisor.py       # Groq AI advisor
│   │   ├── report.py        # HTML / JSON reports
│   │   └── config.py
│   ├── models/              # downloaded weights (not in git)
│   ├── run_batch.py
│   └── run_public.py
├── frontend/                # Vite app
├── docs/
│   └── PROJECT_DOCUMENT.md
└── README.md
```

## Roadmap

- Verify OCR-read fields (employee ID, registration number) against existing HRMS records and flag mismatches.
- Explore generative restoration for heavily degraded images, always labelled as AI-reconstructed and never stored as the record without verification.
- Replace the heuristic quality score with a calibrated one.

## Contributors

- [JaineshBharti5](https://github.com/JaineshBharti5)
- [SiramGanesh](https://github.com/SiramGanesh)
- [saachiahuja02](https://github.com/saachiahuja02)
