const BASE = import.meta.env.VITE_API_URL ?? (location.port === "5173" ? "http://127.0.0.1:8000" : "");

export const url = (path) => (path.startsWith("http") ? path : BASE + path);

async function parse(res) {
  if (res.ok) return res.json();
  let detail = `Request failed (${res.status})`;
  try {
    const body = await res.json();
    if (body.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
  } catch (_) {}
  throw new Error(detail);
}

function form(opts) {
  const f = new FormData();
  f.append("mode", opts.mode);
  f.append("scale", String(opts.scale));
  f.append("denoise", String(opts.denoise));
  f.append("sharpen", String(opts.sharpen));
  f.append("contrast", String(opts.contrast));
  f.append("fidelity", String(opts.fidelity));
  return f;
}

export async function health() {
  try {
    return await parse(await fetch(url("/api/health")));
  } catch (_) {
    return null;
  }
}

export async function restoreOne(file, opts) {
  const f = form(opts);
  f.append("file", file);
  return parse(await fetch(url("/api/restore"), { method: "POST", body: f }));
}

export async function restoreBatch(files, opts) {
  const f = form(opts);
  files.forEach((file) => f.append("files", file));
  return parse(await fetch(url("/api/batch"), { method: "POST", body: f }));
}

export async function getAdvice(jobId) {
  return parse(await fetch(url(`/api/jobs/${jobId}/advice`), { method: "POST" }));
}
