import json
import os
import re

from . import config

_client = None

SYSTEM_PROMPT = (
    "You are an image restoration quality analyst for HR document digitization. "
    "Always respond with valid JSON only, no markdown formatting."
)

KIND_NOTES = {
    "id_photo": "an employee ID photo. Face identity must be preserved exactly.",
    "document": "a scanned HR document or ID card. Text, fields and layout must stay faithful.",
}


def is_configured() -> bool:
    return bool(os.environ.get("GROQ_API_KEY"))


def get_client():
    global _client
    if _client is None:
        from groq import Groq

        _client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    return _client


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._ -]", "", name)[:80] or "file"


def readability_of(job: dict) -> dict:
    return job["metrics"].get("readability") or {"status": "ok"}


def build_prompt(job: dict) -> str:
    q = job["metrics"]["quality"]
    p = job["metrics"]["preservation"]
    r = readability_of(job)
    ocr_before = r.get("ocr_before") or {}
    facts = {
        "file": safe_name(job["filename"]),
        "detected_type": job["kind"],
        "issues_found": job["diagnosis"]["issues"],
        "resolution_before": job["size"]["before"],
        "resolution_after": job["size"]["after"],
        "upscale_method": job["methods"]["upscale"],
        "face_method": job["methods"]["face"],
        "pipeline_steps": [f"{s['name']}: {s['detail']}" for s in job["steps"]],
        "restoration_quality_score": q["score"],
        "sharpness": q["sharpness"],
        "noise": q["noise"],
        "contrast": q["contrast"],
        "preservation_score": p["score"],
        "preservation_verdict": p["verdict"],
        "preservation_checks_percent": p["checks"],
        "options_used": job["options"],
        "source_readability_status": r.get("status", "ok"),
        "source_sharpness_0_to_100": r.get("source_sharpness"),
        "words_ocr_could_read_in_original": ocr_before.get("words_read"),
    }
    kind_note = KIND_NOTES.get(job["kind"], "an image.")
    return f"""Review this restoration result. The input was {kind_note}

MEASUREMENTS (JSON):
{json.dumps(facts, indent=2)}

Write for an HR team migrating legacy employee records to an HRMS.
Rules:
- Use only the numbers above. Do not invent measurements.
- Preservation checks are percentages where higher means closer to the original. A null check was not applicable.
- source_readability_status says whether the ORIGINAL image was sharp enough to restore. "ok" means yes, "review" means it is soft and every field needs checking by eye, "recapture" means it is too blurry to recover.
- If source_readability_status is "recapture": say plainly that the original must be re-scanned or re-photographed, that fine text and faces in the output were guessed and not recovered, that the output must not be stored as the record, and give no settings recommendations because settings cannot fix this.
- If it is "review": the verdict can never be safe_to_use.
- A high restoration score does not make a blurry source reliable.
- Be specific about whether the restored file is safe to store as the record or needs human review.

Return strictly valid JSON with exactly these keys:
{{
  "summary": "two or three plain sentences on what improved and what did not",
  "verdict": "one of: safe_to_use, review_manually, redo_with_different_settings, recapture_needed",
  "risks": ["up to three short risks, empty list if none"],
  "recommendations": [
    {{"setting": "one of: mode, scale, denoise, sharpen, contrast, fidelity", "value": "suggested value", "reason": "one short sentence"}}
  ],
  "hr_note": "one sentence an HR officer can attach to the record"
}}"""


def extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError("Could not extract valid JSON from response")


REQUIRED = ["summary", "verdict", "risks", "recommendations", "hr_note"]
VERDICTS = {"safe_to_use", "review_manually", "redo_with_different_settings", "recapture_needed"}

RECAPTURE_NOTE = "Source image too blurry to recover. Re-scan the original before storing this record."


def validate(result: dict, job: dict) -> dict:
    if not all(k in result for k in REQUIRED):
        raise ValueError("Invalid response structure from AI")
    if result["verdict"] not in VERDICTS:
        result["verdict"] = "review_manually"
    result["risks"] = [str(x) for x in list(result["risks"])[:3]]
    recs = []
    for r in list(result["recommendations"])[:4]:
        if isinstance(r, dict) and {"setting", "value", "reason"} <= set(r):
            recs.append({"setting": str(r["setting"]), "value": str(r["value"]), "reason": str(r["reason"])})
    result["recommendations"] = recs
    result["summary"] = str(result["summary"])
    result["hr_note"] = str(result["hr_note"])

    # The measured readability decides the verdict, whatever the model said.
    status = readability_of(job).get("status", "ok")
    if status == "recapture":
        result["verdict"] = "recapture_needed"
        result["recommendations"] = []
        result["hr_note"] = RECAPTURE_NOTE
    elif status == "review" and result["verdict"] == "safe_to_use":
        result["verdict"] = "review_manually"
    return result


def advise(job: dict) -> dict:
    completion = get_client().chat.completions.create(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(job)},
        ],
        model=config.GROQ_MODEL,
        temperature=config.GROQ_TEMPERATURE,
        max_tokens=config.GROQ_MAX_TOKENS,
    )
    result = validate(extract_json(completion.choices[0].message.content), job)
    result["model"] = config.GROQ_MODEL
    return result