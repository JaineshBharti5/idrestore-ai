import arrowUpRight from "@phosphor-icons/core/assets/regular/arrow-up-right.svg?raw";
import arrowsLeftRight from "@phosphor-icons/core/assets/regular/arrows-left-right.svg?raw";
import arrowsOut from "@phosphor-icons/core/assets/regular/arrows-out.svg?raw";
import bookOpen from "@phosphor-icons/core/assets/regular/book-open.svg?raw";
import caretLeft from "@phosphor-icons/core/assets/regular/caret-left.svg?raw";
import caretRight from "@phosphor-icons/core/assets/regular/caret-right.svg?raw";
import checkCircle from "@phosphor-icons/core/assets/regular/check-circle.svg?raw";
import columns from "@phosphor-icons/core/assets/regular/columns.svg?raw";
import copy from "@phosphor-icons/core/assets/regular/copy.svg?raw";
import cube from "@phosphor-icons/core/assets/regular/cube.svg?raw";
import downloadSimple from "@phosphor-icons/core/assets/regular/download-simple.svg?raw";
import fileText from "@phosphor-icons/core/assets/regular/file-text.svg?raw";
import githubLogo from "@phosphor-icons/core/assets/regular/github-logo.svg?raw";
import handPointing from "@phosphor-icons/core/assets/regular/hand-pointing.svg?raw";
import imageSquare from "@phosphor-icons/core/assets/regular/image-square.svg?raw";
import layout from "@phosphor-icons/core/assets/regular/layout.svg?raw";
import lightning from "@phosphor-icons/core/assets/regular/lightning.svg?raw";
import paintRoller from "@phosphor-icons/core/assets/regular/paint-roller.svg?raw";
import scan from "@phosphor-icons/core/assets/regular/scan.svg?raw";
import scissors from "@phosphor-icons/core/assets/regular/scissors.svg?raw";
import shieldCheck from "@phosphor-icons/core/assets/regular/shield-check.svg?raw";
import slidersHorizontal from "@phosphor-icons/core/assets/regular/sliders-horizontal.svg?raw";
import sparkle from "@phosphor-icons/core/assets/regular/sparkle.svg?raw";
import stack from "@phosphor-icons/core/assets/regular/stack.svg?raw";
import terminal from "@phosphor-icons/core/assets/regular/terminal.svg?raw";
import uploadSimple from "@phosphor-icons/core/assets/regular/upload-simple.svg?raw";
import userFocus from "@phosphor-icons/core/assets/regular/user-focus.svg?raw";
import warningCircle from "@phosphor-icons/core/assets/regular/warning-circle.svg?raw";
import xLogo from "@phosphor-icons/core/assets/regular/x-logo.svg?raw";
import x from "@phosphor-icons/core/assets/regular/x.svg?raw";

const ICONS = {
  "arrow-up-right": arrowUpRight,
  "arrows-left-right": arrowsLeftRight,
  "arrows-out": arrowsOut,
  "book-open": bookOpen,
  "caret-left": caretLeft,
  "caret-right": caretRight,
  "check-circle": checkCircle,
  columns,
  copy,
  cube,
  "download-simple": downloadSimple,
  "file-text": fileText,
  "github-logo": githubLogo,
  "hand-pointing": handPointing,
  "image-square": imageSquare,
  layout,
  lightning,
  "paint-roller": paintRoller,
  scan,
  scissors,
  "shield-check": shieldCheck,
  "sliders-horizontal": slidersHorizontal,
  sparkle,
  stack,
  terminal,
  "upload-simple": uploadSimple,
  "user-focus": userFocus,
  "warning-circle": warningCircle,
  "x-logo": xLogo,
  x,
};

export function icon(name, size = 20) {
  const svg = ICONS[name] || "";
  return svg.replace("<svg", `<svg width="${size}" height="${size}" aria-hidden="true" focusable="false"`);
}

export function hydrateIcons(root = document) {
  root.querySelectorAll("[data-ph]").forEach((el) => {
    el.innerHTML = icon(el.dataset.ph, Number(el.dataset.size || 20));
    el.removeAttribute("data-ph");
  });
}
