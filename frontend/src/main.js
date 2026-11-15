import "./styles.css";
import { hydrateIcons } from "./icons.js";
import { mountCompare } from "./slider.js";
import { landscapeAfter, landscapeBefore, idCardAfter, idCardBefore, docAfter, docBefore } from "./scenes.js";
import { initStudio } from "./studio.js";
import { url } from "./api.js";

const CODE = `Prepare  load, fix orientation, measure blur and noise
Upscale  Real-ESRGAN x4, OpenCV Lanczos as fallback
Faces    GFPGAN, blended with the original face
Enhance  denoise, levels, CLAHE contrast, unsharp
Verify   structure, layout, colour, face, text
Report   JSON, HTML report, ZIP and CSV for batches

curl -X POST http://127.0.0.1:8000/api/restore \\
  -F "file=@old_id.jpg" \\
  -F "mode=auto" \\
  -F "scale=0"`;

function highlight(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .split("\n")
    .map((line) =>
      line
        .replace(/^(Prepare|Upscale|Faces|Enhance|Verify|Report)\b/, '<span class="tk-verb">$1</span>')
        .replace(/^(curl)\b/, '<span class="tk-verb">$1</span>')
        .replace(/"[^"]*"/g, '<span class="tk-str">$&</span>')
    )
    .join("\n");
}

hydrateIcons();

mountCompare(document.getElementById("hero-compare"), {
  before: landscapeBefore("hb"),
  after: landscapeAfter("ha"),
  beforeLabel: "Before",
  afterLabel: "After",
  start: 50,
});
mountCompare(document.getElementById("gal-id"), {
  before: idCardBefore("gib"),
  after: idCardAfter("gia"),
  beforeLabel: "Faded",
  afterLabel: "Restored",
  start: 45,
});
mountCompare(document.getElementById("gal-doc"), {
  before: docBefore("gdb"),
  after: docAfter("gda"),
  beforeLabel: "Scanned",
  afterLabel: "Cleaned",
  start: 55,
});

document.getElementById("code-body").innerHTML = highlight(CODE);
document.getElementById("copy-code").addEventListener("click", async (e) => {
  const label = e.currentTarget.querySelector("span");
  try {
    await navigator.clipboard.writeText(CODE);
    label.textContent = "Copied";
  } catch (_) {
    label.textContent = "Press Ctrl+C";
  }
  setTimeout(() => (label.textContent = "Copy"), 1600);
});

document.getElementById("api-docs").href = url("/docs");
document.getElementById("footer-docs").href = url("/docs");

initStudio();
