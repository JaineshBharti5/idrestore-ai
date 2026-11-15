import { icon } from "./icons.js";

export function mountCompare(host, { before, after, beforeLabel = "Before", afterLabel = "After", start = 50, ratio } = {}) {
  host.classList.add("cmp");
  if (ratio) host.style.aspectRatio = ratio;
  host.innerHTML = `
    <div class="cmp-layer cmp-after">${after}</div>
    <div class="cmp-layer cmp-before">${before}</div>
    <span class="cmp-tag cmp-tag-before">${beforeLabel}</span>
    <span class="cmp-tag cmp-tag-after">${afterLabel}</span>
    <div class="cmp-divider"></div>
    <div class="cmp-grip" role="slider" tabindex="0" aria-label="Comparison position" aria-valuemin="0" aria-valuemax="100">
      ${icon("caret-left", 16)}${icon("caret-right", 16)}
    </div>`;
  const grip = host.querySelector(".cmp-grip");
  let pos = start;
  let dragging = false;

  function set(value) {
    pos = Math.min(100, Math.max(0, value));
    host.style.setProperty("--pos", pos + "%");
    grip.setAttribute("aria-valuenow", String(Math.round(pos)));
  }

  function fromEvent(e) {
    const r = host.getBoundingClientRect();
    set(((e.clientX - r.left) / r.width) * 100);
  }

  host.addEventListener("pointerdown", (e) => {
    dragging = true;
    host.setPointerCapture(e.pointerId);
    fromEvent(e);
  });
  host.addEventListener("pointermove", (e) => dragging && fromEvent(e));
  const stop = () => (dragging = false);
  host.addEventListener("pointerup", stop);
  host.addEventListener("pointercancel", stop);
  grip.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") set(pos - 2);
    else if (e.key === "ArrowRight") set(pos + 2);
    else if (e.key === "Home") set(0);
    else if (e.key === "End") set(100);
    else return;
    e.preventDefault();
  });

  set(start);
  return { set };
}
