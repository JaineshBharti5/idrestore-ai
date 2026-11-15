# IDRestore AI: Employee Document Restorer

## Project Description

IDRestore AI restores degraded employee ID photos and scanned HR documents so legacy records can be migrated to a modern HRMS. A restoration pipeline denoises, deblurs and upscales each file, restores faces, and then measures whether photos, text, fields and layout stayed faithful to the original. A Generative AI advisor, powered by Groq's LLaMA 3.3-70B Versatile model, reads the measurements and explains the result to HR in plain language, flags risks and suggests better settings.

The platform is built with FastAPI and OpenCV on the backend, optional Real-ESRGAN and GFPGAN models for deep-learning restoration, and a Vite frontend with a before/after comparison slider. API keys are managed through `.env`, and the app is exposed publicly through Ngrok.

## Scenarios

**Scenario 1:** An HR officer uploads a faded, low-resolution employee ID photo. The system detects a face, upscales the image, restores facial detail with GFPGAN, and shows a before/after slider with quality and preservation scores.

**Scenario 2:** A team uploads 20 scanned HR documents in one batch. Each file is cleaned, a ZIP of restored images and a CSV summary are produced, and files whose preservation verdict is Review or Altered are flagged for manual checking. Failed files are reported without stopping the batch.

**Scenario 3:** A restored document gets a preservation score of 72. The officer clicks Ask AI advisor. The Groq model reads the measurements, explains that edge layout drifted, recommends lowering sharpness, and writes a one-line note to attach to the employee record.

## Technical Architecture

```
Browser (HTML, CSS, JavaScript, Vite)
   |  multipart upload / JSON
   v
FastAPI backend  ----------------------------->  Groq API (LLaMA 3.3-70B)
   |                                              advisor.py builds prompt,
   |  pipeline.py                                 extract_json() parses reply
   v
preprocess -> denoise -> deblur -> upscale (Real-ESRGAN | OpenCV)
   -> face restore (GFPGAN | OpenCV) -> enhance -> evaluate -> report
   |
   v
outputs/jobs/<id>/  original.jpg, restored.png, job.json, advice.json
```

Description: IDRestore AI uses a modular three-tier architecture. The frontend handles upload, settings and visual comparison. The FastAPI backend validates input, runs the restoration pipeline and evaluation, and stores each job as files. The Groq API is used only for the advisor, and it receives measurements, never the image. Local deployment is managed with uvicorn and exposed publicly through Ngrok.

Database note: the project does not use a database. Job results are stored as JSON files on disk, so no ER diagram is required.

## Pre-requisites

- FastAPI and Python programming
- OpenCV and basic image processing
- Groq API familiarity
- HTML, CSS and JavaScript
- Git for version control
- Ngrok for public deployment
- Optional: PyTorch, Real-ESRGAN, GFPGAN, Tesseract OCR

## Project Workflow

### Milestone 1: Model Selection and Architecture

**Activity 1.1: Generate a Groq API key.** Create an account at console.groq.com, open API Keys, click Create API Key, name it `idrestore-key`, copy it immediately, and save it in `backend/.env` as `GROQ_API_KEY=...`. The `.env` file is listed in `.gitignore` so the key is never committed.

**Activity 1.2: Select the models.**
- Real-ESRGAN x4plus for upscaling low-resolution images.
- GFPGAN v1.4 for face restoration.
- OpenCV for denoising, deblurring (Richardson-Lucy with total variation), levels, contrast and sharpening.
- Groq `llama-3.3-70b-versatile` for the advisor, with temperature 0.4 and max_tokens 2048 so the analysis stays consistent.

**Activity 1.3: Define the architecture.** See the architecture diagram above. Frontend: upload, options, comparison slider, report download. Backend: validation, pipeline, evaluation, advisor. AI integration: `build_prompt()` assembles measurements, the Groq client is called, `extract_json()` parses the reply and `validate()` checks required keys.

**Activity 1.4: Set up the environment.** From the `backend` folder: `python -m venv venv`, `venv\Scripts\activate`, `pip install -r requirements.txt`. Optional AI models: `pip install -r requirements-ai.txt` in a Python 3.10 or 3.11 environment, then place `RealESRGAN_x4plus.pth` and `GFPGANv1.4.pth` in `backend/models`.

### Milestone 2: Core Functionalities Development

**Activity 2.1: Core restoration features.**
- Data preparation: orientation fix, size limits, blur, noise, contrast and face diagnosis (`preprocess.py`, `make_samples.py`).
- Image upscaling (`upscale.py`).
- Face restoration with identity blend (`face.py`).
- Document quality enhancement (`enhance.py`).
- Record preservation evaluation: structure, layout, colour, face and OCR text checks (`evaluate.py`).
- Quality report in HTML and CSV (`report.py`).

**Activity 2.2: Implement the backend.** FastAPI routes manage uploads, validation (type, 15 MB limit, 20 files per batch), processing and error handling.

### Milestone 3: Backend Application Development

**Activity 3.1: Main application logic in `main.py`.**

| Route | Purpose |
| --- | --- |
| GET /api/health | Engine status for Real-ESRGAN, GFPGAN, OCR and the AI advisor |
| POST /api/restore | Restore one image, returns scores, steps and file URLs |
| POST /api/batch | Restore up to 20 images, returns results, errors, ZIP and CSV |
| GET /api/jobs/{id} | Stored job result |
| GET /api/jobs/{id}/report | Downloadable HTML report |
| POST /api/jobs/{id}/advice | Groq advisor analysis of a job |

Prompt helpers live in `advisor.py`: `build_prompt()` turns job measurements into a structured prompt that demands strict JSON, `extract_json()` parses direct JSON, markdown code blocks and raw JSON objects, and `validate()` enforces the required keys `summary`, `verdict`, `risks`, `recommendations` and `hr_note`.

Testing: `make_samples.py` builds clean and degraded pairs so restoration can be measured against ground truth. On the five synthetic pairs used during development the OpenCV engine improved PSNR on every file and SSIM by 0.035 on average.

### Milestone 4: Frontend Development

**Activity 4.1: Design the interface.** A warm sand and terracotta editorial design in the Inter typeface with a sticky navigation bar, a hero comparison slider, a gallery, a pipeline section and the Studio. Layouts use flexbox and grid and reflow to a single column on small screens.

**Activity 4.2: Dynamic rendering.** The Studio sends multipart requests with the Fetch API, shows a loader while processing, then renders the comparison slider, scores, measurements, preservation bars, pipeline steps and the AI advisor card. The Restore button is re-enabled in a `finally` block whether the request succeeds or fails.

### Milestone 5: Deployment

**Activity 5.1: Local deployment.** Backend: `uvicorn app.main:app --reload --port 8000`. Frontend: `npm install`, then `npm run dev` and open http://localhost:5173. To serve everything from one port run `npm run build`, then open http://127.0.0.1:8000.

**Activity 5.2: Local testing.** Test a single ID photo, a document, a batch, a corrupted file and an oversize file. Confirm the advisor card works after setting `GROQ_API_KEY`.

**Activity 5.3: Public deployment via Ngrok.** Install the Ngrok client, copy your authtoken from the Ngrok dashboard, add `NGROK_AUTHTOKEN=...` to `backend/.env`, run `npm run build` in the frontend, then from `backend` run `python run_public.py`. The script opens an HTTP tunnel to port 8000 and prints the public URL. `reload` is off so the reloader does not interfere with the tunnel. On the free plan the URL changes at every restart.

### Milestone 6: Conclusion

IDRestore AI combines classical image processing, deep-learning restoration and Generative AI explanation in one workflow for HR document digitization. Its preservation checks make restoration auditable, so records are not silently altered. Future work includes fine-tuning restoration on real HR scans, handwriting-aware OCR checks, user authentication with a stored audit trail, and support for PDF input.

## Evaluation Criteria Mapping

| Criterion | Weight | Where it is covered |
| --- | --- | --- |
| Employee Document Data Preparation | 15% | `preprocess.py`, `make_samples.py` |
| AI Restoration Implementation | 25% | `upscale.py`, `face.py`, `enhance.py` |
| Restoration Quality | 20% | quality score, before/after slider, measurements |
| Employee Information Preservation | 15% | `evaluate.py` preservation checks and verdict |
| Automated Pipeline and Testing | 15% | `pipeline.py`, batch endpoint, `run_batch.py` |
| Documentation and Final Demonstration | 10% | this document, README, HTML reports |

## Known Limits

- Without Real-ESRGAN and GFPGAN weights the app uses OpenCV only. It removes noise and sharpens moderately, but it cannot recover detail that is gone from a very low-resolution or heavily compressed image.
- Quality and preservation scores are heuristics.
- Generative restoration can invent detail. Review every file marked Review or Altered before replacing an original record.
