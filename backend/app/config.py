import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parent.parent
if load_dotenv:
    load_dotenv(BASE_DIR / ".env")
MODELS_DIR = Path(os.getenv("IDRESTORE_MODELS", BASE_DIR / "models"))
OUTPUT_DIR = Path(os.getenv("IDRESTORE_OUTPUT", BASE_DIR / "outputs"))
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"

REALESRGAN_WEIGHTS = MODELS_DIR / "RealESRGAN_x4plus.pth"
GFPGAN_WEIGHTS = MODELS_DIR / "GFPGANv1.4.pth"

MAX_UPLOAD_MB = 15
MAX_BATCH_FILES = 20
MAX_INPUT_SIDE = 2000
MAX_OUTPUT_SIDE = 3200
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
OCR_LANG = os.getenv("IDRESTORE_OCR_LANG", "eng")
GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_TEMPERATURE = 0.4
GROQ_MAX_TOKENS = 2048

JOBS_DIR = OUTPUT_DIR / "jobs"
BATCHES_DIR = OUTPUT_DIR / "batches"
JOBS_DIR.mkdir(parents=True, exist_ok=True)
BATCHES_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
