import { hydrateIcons, icon } from "./icons.js";
import { mountCompare } from "./slider.js";
import { health, restoreOne, restoreBatch, getAdvice, url } from "./api.js";

const MAX_MB = 15;
const MAX_FILES = 20;
const EXT = /\.(jpe?g|png|webp|bmp|tiff?)$/i;

const $ = (id) => document.getElementById(id);
const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmtSize = (b) => (b > 1048576 ? (b / 1048576).toFixed(1) + " MB" : Math.max(1, Math.round(b / 1024)) + " KB");
const KIND = { id_photo: "ID photo", document: "Document" };

const state = {
  input: "single",
  files: [],
  busy: false,
  opts: { mode: "auto", scale: 0, denoise: true, sharpen: 0.5, contrast: 0.5, fidelity: 0.7 },
};

function showError(msg) {
  const el = $("error");
  el.textContent = msg || "";
  el.hidden = !msg;
}

function renderEngine(h) {
  const el = $("engine");
  if (!h) {
    el.innerHTML = `<span class="chip"><i></i>Backend offline. Start it with <b>uvicorn app.main:app --reload --port 8000</b></span>`;
    return;
  }
  const e = h.engines;
  const chip = (live, label, name, note) =>
    `<span class="chip ${live ? "live" : ""}" ${note ? `title="${esc(note)}"` : ""}><i></i>${label}: <b>${esc(name)}</b></span>`;
  el.innerHTML =
    chip(e.upscale.active, "Upscale", e.upscale.name, e.upscale.note) +
    chip(e.face.active, "Faces", e.face.name, e.face.note) +
    chip(e.ocr.active, "Text check", e.ocr.active ? "Tesseract OCR" : "OCR off, install Tesseract") +
    chip(e.advisor.active, "AI advisor", e.advisor.active ? e.advisor.name : "off, add GROQ_API_KEY");
}

function renderFiles() {
  const list = $("file-list");
  list.innerHTML = "";
  state.files.forEach((item, i) => {
    const li = document.createElement("li");
    li.innerHTML = `<img src="${item.preview}" alt="" /><span class="fname">${esc(item.file.name)}</span><span class="fsize">${fmtSize(item.file.size)}</span><button type="button" aria-label="Remove ${esc(item.file.name)}">${icon("x", 14)}</button>`;
    li.querySelector("button").addEventListener("click", () => {
      URL.revokeObjectURL(item.preview);
      state.files.splice(i, 1);
      renderFiles();
    });
    list.appendChild(li);
  });
  const n = state.files.length;
  $("run").disabled = state.busy || n === 0;
  $("run").textContent = state.input === "batch" ? (n > 1 ? `Restore ${n} images` : "Restore images") : "Restore image";
}

function addFiles(fileList) {
  showError("");
  const incoming = Array.from(fileList);
  const problems = [];
  const ok = incoming.filter((f) => {
    if (!EXT.test(f.name)) {
      problems.push(`${f.name} is not a supported image.`);
      return false;
    }
    if (f.size > MAX_MB * 1048576) {
      problems.push(`${f.name} is larger than ${MAX_MB} MB.`);
      return false;
    }
    return true;
  });
  if (state.input === "single") {
    if (ok.length) {
      state.files.forEach((x) => URL.revokeObjectURL(x.preview));
      state.files = [{ file: ok[0], preview: URL.createObjectURL(ok[0]) }];
    }
  } else {
    for (const f of ok) {
      if (state.files.length >= MAX_FILES) {
        problems.push(`Batch is limited to ${MAX_FILES} files.`);
        break;
      }
      if (!state.files.some((x) => x.file.name === f.name && x.file.size === f.size)) {
        state.files.push({ file: f, preview: URL.createObjectURL(f) });
      }
    }
  }
  if (problems.length) showError(problems.join(" "));
  renderFiles();
}

function setInputMode(mode) {
  state.input = mode;
  document.querySelectorAll("[data-input]").forEach((b) => {
    const on = b.dataset.input === mode;
    b.classList.toggle("on", on);
    b.setAttribute("aria-selected", String(on));
  });
  $("file").multiple = mode === "batch";
  $("drop-title").textContent = mode === "batch" ? "Drop up to 20 images" : "Drop an ID photo or scan";
  state.files.forEach((x) => URL.revokeObjectURL(x.preview));
  state.files = [];
  showError("");
  renderFiles();
}

function bindControls() {
  document.querySelectorAll("[data-input]").forEach((b) => b.addEventListener("click", () => setInputMode(b.dataset.input)));

  document.querySelectorAll(".seg[data-opt]").forEach((seg) => {
    seg.addEventListener("click", (e) => {
      const btn = e.target.closest("button");
      if (!btn) return;
      seg.querySelectorAll("button").forEach((b) => b.classList.toggle("on", b === btn));
      const key = seg.dataset.opt;
      state.opts[key] = key === "scale" ? Number(btn.dataset.value) : btn.dataset.value;
    });
  });

  $("opt-denoise").addEventListener("change", (e) => (state.opts.denoise = e.target.checked));
  ["sharpen", "contrast", "fidelity"].forEach((key) => {
    const input = $("opt-" + key);
    input.addEventListener("input", () => {
      state.opts[key] = Number(input.value) / 100;
      $("out-" + key).textContent = input.value + "%";
    });
  });

  const drop = $("drop");
  const input = $("file");
  input.addEventListener("change", () => {
    addFiles(input.files);
    input.value = "";
  });
  drop.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      input.click();
    }
  });
  ["dragenter", "dragover"].forEach((ev) =>
    drop.addEventListener(ev, (e) => {
      e.preventDefault();
      drop.classList.add("over");
    })
  );
  ["dragleave", "drop"].forEach((ev) =>
    drop.addEventListener(ev, (e) => {
      e.preventDefault();
      drop.classList.remove("over");
    })
  );
  drop.addEventListener("drop", (e) => addFiles(e.dataTransfer.files));

  $("run").addEventListener("click", run);
}

function working(text) {
  $("result").innerHTML = `<div class="working"><span class="spinner"></span><strong>${esc(text)}</strong><p>The first run loads the models, so it can take a little longer.</p></div>`;
}

function bars(job) {
  const names = { structure: "Structure", layout: "Layout", color: "Colour", face: "Face", text: "Text" };
  return Object.entries(job.metrics.preservation.checks)
    .map(([k, v]) =>
      v === null
        ? `<div class="bar-row na"><span>${names[k]}</span><div class="bar"></div><em>n/a</em></div>`
        : `<div class="bar-row"><span>${names[k]}</span><div class="bar"><i style="width:${v}%"></i></div><em>${v}%</em></div>`
    )
    .join("");
}

function readabilityHtml(job) {
  const r = job.metrics.readability;
  if (!r || r.status === "ok") return "";
  const recapture = r.status === "recapture";
  const title = recapture ? "Re-scan needed" : "Check every field by eye";
  const style = recapture
    ? "background:#fdecea;border:1px solid #c0392b;color:#7a1f14"
    : "background:#fff4e0;border:1px solid #d98a00;color:#6b4500";
  let ocr = "";
  if (r.ocr_before) {
    ocr = ` Text the OCR could read in the original: ${r.ocr_before.words_read} word(s).`;
  }
  return `<div role="alert" style="${style};border-radius:14px;padding:14px 18px;margin:0 0 16px">
      <strong style="display:block;margin-bottom:4px">${title}</strong>
      <span>${esc(r.message)}</span>
      <span style="display:block;margin-top:6px;font-size:0.85em;opacity:0.85">Source sharpness: ${r.source_sharpness} / 100.${esc(ocr)}</span>
    </div>`;
}

function jobHtml(job) {
  const q = job.metrics.quality;
  const p = job.metrics.preservation;
  const [bw, bh] = job.size.before;
  const [aw, ah] = job.size.after;
  const verdict = p.verdict.toLowerCase();
  const read = job.metrics.readability;
  const unreliable = read && read.status === "recapture";
  const ocrNote =
    job.kind === "document" && p.checks.text === null
      ? `<p class="fine">Text check was skipped. Install Tesseract to compare OCR text before and after.</p>`
      : "";
  const scoreNote = unreliable
    ? `<p class="fine">These scores describe how much this output changed. They do not mean it is accurate, because the source was too blurry to recover.</p>`
    : "";
  return `
    <div class="res-head">
      <div><h3 class="res-title">${esc(job.filename)}</h3><p class="res-sub">${KIND[job.kind] || job.kind} · ${bw} x ${bh} to ${aw} x ${ah} · ${(job.timings_ms.total / 1000).toFixed(1)} s</p></div>
      <div class="res-actions">
        <a class="btn btn-ink" href="${url(job.urls.download)}" download>${icon("download-simple", 16)}Restored PNG</a>
        <a class="btn btn-outline" href="${url(job.urls.report)}" download>${icon("file-text", 16)}Report</a>
      </div>
    </div>
    ${readabilityHtml(job)}
    <div class="res-frame" data-compare></div>
    <div class="methods">
      <span class="chip live"><i></i>Upscale: <b>${esc(job.methods.upscale)}</b></span>
      <span class="chip ${job.diagnosis.faces ? "live" : ""}"><i></i>Faces: <b>${esc(job.methods.face)}</b></span>
      ${job.diagnosis.issues.map((s) => `<span class="chip"><i></i>${esc(s)}</span>`).join("")}
    </div>
    <div class="scores">
      <div class="score"><b>${q.score}</b><span>Restoration quality</span></div>
      <div class="score"><b>${p.score}</b><span>Preservation</span><br /><span class="verdict ${verdict}">${esc(p.verdict)}</span></div>
      <div class="score"><b>${job.metrics.overall}</b><span>Overall</span></div>
    </div>
    ${scoreNote}
    <div class="cols">
      <div class="box">
        <h4>Measurements</h4>
        <table class="tbl">
          <tr><th></th><th>Before</th><th>After</th></tr>
          <tr><td>Sharpness</td><td>${q.sharpness.before}</td><td>${q.sharpness.after}</td></tr>
          <tr><td>Noise</td><td>${q.noise.before}</td><td>${q.noise.after}</td></tr>
          <tr><td>Contrast</td><td>${q.contrast.before}</td><td>${q.contrast.after}</td></tr>
          <tr><td>Brightness</td><td>${q.brightness.before}</td><td>${q.brightness.after}</td></tr>
        </table>
      </div>
      <div class="box"><h4>Preservation checks</h4>${bars(job)}</div>
    </div>
    <div class="box" style="margin-top:20px">
      <h4>What the pipeline did</h4>
      <ul class="steps-list">${job.steps.map((s) => `<li><b>${esc(s.name)}</b><span>${esc(s.detail)}</span></li>`).join("")}</ul>
    </div>
    <div class="box advisor" data-advisor style="margin-top:20px">
      <div class="adv-head"><h4>AI advisor</h4><button type="button" class="btn btn-terra btn-xs" data-ask>Ask AI advisor</button></div>
      <p class="hint">The AI advisor reads the measurements above and explains the result for HR in plain language.</p>
      <div data-advice></div>
    </div>
    ${ocrNote}
    <p class="fine">Scores are heuristic. Quality rewards sharpness gain, noise reduction and contrast. Preservation compares the result with the original.</p>`;
}

const VERDICT = {
  safe_to_use: ["Safe to use", ""],
  review_manually: ["Review manually", "review"],
  redo_with_different_settings: ["Redo with other settings", "altered"],
};

function adviceHtml(a) {
  const [label, cls] = VERDICT[a.verdict] || VERDICT.review_manually;
  const risks = a.risks.length ? `<h5>Risks</h5><ul class="adv-list">${a.risks.map((r) => `<li>${esc(r)}</li>`).join("")}</ul>` : "";
  const recs = a.recommendations.length
    ? `<h5>Suggested settings</h5><ul class="adv-list">${a.recommendations
        .map((r) => `<li><b>${esc(r.setting)}</b> to <b>${esc(r.value)}</b>. ${esc(r.reason)}</li>`)
        .join("")}</ul>`
    : "";
  return `<span class="verdict ${cls}">${label}</span><p class="adv-summary">${esc(a.summary)}</p>${risks}${recs}<h5>Note for the record</h5><p class="adv-note">${esc(a.hr_note)}</p><p class="fine">Written by ${esc(a.model)}. The AI only sees the measurements, not your image.</p>`;
}

function bindAdvisor(container, job) {
  const box = container.querySelector("[data-advisor]");
  const btn = box.querySelector("[data-ask]");
  const out = box.querySelector("[data-advice]");
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    btn.textContent = "Thinking";
    out.innerHTML = "";
    try {
      out.innerHTML = adviceHtml(await getAdvice(job.id));
      btn.textContent = "Ask again";
    } catch (err) {
      out.innerHTML = `<p class="error">${esc(err.message)}</p>`;
      btn.textContent = "Try again";
    } finally {
      btn.disabled = false;
    }
  });
}

function renderJob(container, job) {
  container.innerHTML = jobHtml(job);
  const [w, h] = job.size.before;
  mountCompare(container.querySelector("[data-compare]"), {
    before: `<img src="${url(job.urls.original)}" alt="Original" />`,
    after: `<img src="${url(job.urls.restored)}" alt="Restored" />`,
    ratio: `${w} / ${h}`,
    start: 50,
  });
  bindAdvisor(container, job);
  hydrateIcons(container);
}

function batchVerdict(j) {
  const r = j.metrics.readability;
  if (r && r.status === "recapture") return `<span class="verdict altered">Recapture</span>`;
  const v = j.metrics.preservation.verdict;
  return `<span class="verdict ${v.toLowerCase()}">${esc(v)}</span>`;
}

function renderBatch(batch) {
  const res = $("result");
  const rows = batch.jobs
    .map(
      (j) => `<tr data-job="${j.id}" tabindex="0">
        <td><img src="${url(j.urls.restored)}" alt="" /></td>
        <td>${esc(j.filename)}</td>
        <td>${KIND[j.kind] || j.kind}</td>
        <td>${j.metrics.quality.score}</td>
        <td>${j.metrics.preservation.score}</td>
        <td>${batchVerdict(j)}</td>
      </tr>`
    )
    .join("");
  const fails = batch.errors
    .map((e) => `<tr class="fail"><td></td><td>${esc(e.filename)}</td><td colspan="4">${esc(e.error)}</td></tr>`)
    .join("");
  res.innerHTML = `
    <div class="res-head">
      <div><h3 class="res-title">Batch finished</h3></div>
      <div class="res-actions">
        <a class="btn btn-ink" href="${url(batch.urls.zip)}" download>${icon("download-simple", 16)}Restored ZIP</a>
        <a class="btn btn-outline" href="${url(batch.urls.csv)}" download>${icon("file-text", 16)}Summary CSV</a>
      </div>
    </div>
    <p class="batch-sum"><span><b>${batch.ok}</b> restored</span><span><b>${batch.failed}</b> failed</span><span><b>${batch.total}</b> total</span></p>
    <div class="btable-wrap">
      <table class="btable">
        <thead><tr><th></th><th>File</th><th>Type</th><th>Quality</th><th>Kept</th><th>Verdict</th></tr></thead>
        <tbody>${rows}${fails}</tbody>
      </table>
    </div>
    <div class="detail" id="detail"></div>`;
  const open = (tr) => {
    res.querySelectorAll("tr.sel").forEach((x) => x.classList.remove("sel"));
    tr.classList.add("sel");
    const job = batch.jobs.find((j) => j.id === tr.dataset.job);
    renderJob($("detail"), job);
  };
  res.querySelectorAll("tr[data-job]").forEach((tr) => {
    tr.addEventListener("click", () => open(tr));
    tr.addEventListener("keydown", (e) => (e.key === "Enter" ? open(tr) : null));
  });
  const first = res.querySelector("tr[data-job]");
  if (first) open(first);
}

async function run() {
  if (state.busy || !state.files.length) return;
  state.busy = true;
  showError("");
  $("run").disabled = true;
  const files = state.files.map((x) => x.file);
  working(state.input === "batch" ? `Restoring ${files.length} images` : "Restoring your image");
  try {
    if (state.input === "batch") renderBatch(await restoreBatch(files, state.opts));
    else renderJob($("result"), await restoreOne(files[0], state.opts));
  } catch (err) {
    $("result").innerHTML = `<div class="empty"><span class="empty-icon">${icon("warning-circle", 28)}</span><h3>Restore failed</h3><p>${esc(err.message)}</p></div>`;
    showError("Check that the backend is running, then try again.");
  } finally {
    state.busy = false;
    renderFiles();
  }
}

export async function initStudio() {
  bindControls();
  renderFiles();
  renderEngine(await health());
}