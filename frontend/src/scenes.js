const NOISE = (id) => `
  <filter id="n-${id}" x="0" y="0" width="100%" height="100%">
    <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch"/>
    <feColorMatrix values="0 0 0 0 0.3  0 0 0 0 0.3  0 0 0 0 0.3  0 0 0 0.55 0"/>
  </filter>`;

const SOFTEN = (id, blur) => `
  <filter id="f-${id}" x="-5%" y="-5%" width="110%" height="110%">
    <feGaussianBlur stdDeviation="${blur}"/>
    <feColorMatrix type="saturate" values="0.3"/>
    <feComponentTransfer>
      <feFuncR type="linear" slope="0.8" intercept="0.1"/>
      <feFuncG type="linear" slope="0.8" intercept="0.1"/>
      <feFuncB type="linear" slope="0.8" intercept="0.1"/>
    </feComponentTransfer>
  </filter>`;

export function landscapeAfter(id) {
  return `<svg viewBox="0 0 800 500" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Warm dusk landscape">
  <defs>
    <linearGradient id="sky-${id}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#f0c9a0"/><stop offset="0.55" stop-color="#dd9a6f"/><stop offset="1" stop-color="#9c5a3f"/>
    </linearGradient>
    <radialGradient id="sun-${id}" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#fbe7c6"/><stop offset="1" stop-color="#fbe7c6" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="800" height="500" fill="url(#sky-${id})"/>
  <circle cx="560" cy="190" r="150" fill="url(#sun-${id})"/>
  <circle cx="560" cy="190" r="38" fill="#fbe7c6"/>
  <path d="M0 330 L110 250 L210 310 L330 220 L460 320 L580 240 L700 310 L800 270 V500 H0 Z" fill="#b87450"/>
  <path d="M0 385 L140 300 L260 365 L400 280 L540 370 L680 300 L800 360 V500 H0 Z" fill="#8a4f36"/>
  <path d="M0 445 L160 385 L300 432 L450 365 L620 440 L800 400 V500 H0 Z" fill="#5e3426"/>
</svg>`;
}

export function landscapeBefore(id) {
  return `<svg viewBox="0 0 800 500" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Cool night landscape">
  <defs>
    <linearGradient id="sky-${id}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#cdd9d0"/><stop offset="0.55" stop-color="#9aa39a"/><stop offset="1" stop-color="#5d645d"/>
    </linearGradient>
  </defs>
  <rect width="800" height="500" fill="url(#sky-${id})"/>
  <rect width="800" height="500" fill="#8a8f8a" opacity="0.25"/>
  <circle cx="560" cy="190" r="34" fill="#dfe6e0" opacity="0.8"/>
  <path d="M0 330 L110 250 L210 310 L330 220 L460 320 L580 240 L700 310 L800 270 V500 H0 Z" fill="#8b948c"/>
  <path d="M0 385 L140 300 L260 365 L400 280 L540 370 L680 300 L800 360 V500 H0 Z" fill="#6a716a"/>
  <path d="M0 445 L160 385 L300 432 L450 365 L620 440 L800 400 V500 H0 Z" fill="#474d47"/>
</svg>`;
}

function idCardBody() {
  let bars = "";
  const widths = [3, 1, 2, 1, 4, 1, 2, 3, 1, 2, 1, 3, 2, 1, 4, 1, 2, 1, 3];
  let x = 330;
  widths.forEach((w, i) => {
    if (i % 2 === 0) bars += `<rect x="${x}" y="378" width="${w * 2}" height="52" fill="#2b251d"/>`;
    x += w * 2 + 2;
  });
  return `
  <rect width="800" height="500" fill="#e6dcc8"/>
  <rect x="70" y="50" width="660" height="400" rx="26" fill="#f6f1e7"/>
  <path d="M96 50 H704 A26 26 0 0 1 730 76 V120 H70 V76 A26 26 0 0 1 96 50 Z" fill="#c4633f"/>
  <text x="104" y="97" font-family="Inter, Arial, sans-serif" font-size="26" font-weight="800" fill="#f6f1e7">Northfield Group</text>
  <text x="696" y="97" text-anchor="end" font-family="Inter, Arial, sans-serif" font-size="16" font-weight="600" fill="#f6f1e7">EMPLOYEE</text>
  <rect x="104" y="150" width="190" height="236" rx="14" fill="#e6dcc8"/>
  <circle cx="199" cy="236" r="46" fill="#5c5346"/>
  <path d="M120 386 C120 316 160 292 199 292 C238 292 278 316 278 386 Z" fill="#5c5346"/>
  <text x="330" y="190" font-family="Inter, Arial, sans-serif" font-size="34" font-weight="800" fill="#2b251d">Aarav Menon</text>
  <text x="330" y="230" font-family="Inter, Arial, sans-serif" font-size="20" fill="#5c5346">People Operations</text>
  <text x="330" y="282" font-family="Inter, Arial, sans-serif" font-size="16" fill="#5c5346">Employee ID</text>
  <text x="330" y="312" font-family="Inter, Arial, sans-serif" font-size="26" font-weight="700" fill="#2b251d">EMP-20418</text>
  <text x="330" y="352" font-family="Inter, Arial, sans-serif" font-size="16" fill="#5c5346">Joined 12 Mar 2011</text>
  ${bars}`;
}

export function idCardAfter(id) {
  return `<svg viewBox="0 0 800 500" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Restored employee ID card">${idCardBody()}</svg>`;
}

export function idCardBefore(id) {
  return `<svg viewBox="0 0 800 500" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Faded employee ID card">
  <defs>${SOFTEN(id, 3.4)}${NOISE(id)}</defs>
  <g filter="url(#f-${id})">${idCardBody()}</g>
  <rect width="800" height="500" filter="url(#n-${id})" opacity="0.5"/>
  <rect width="800" height="500" fill="#c9b98f" opacity="0.18"/>
</svg>`;
}

function docBody() {
  let lines = "";
  const widths = [610, 560, 600, 480, 590, 540, 300];
  for (let block = 0; block < 2; block++) {
    widths.forEach((w, i) => {
      lines += `<rect x="90" y="${178 + block * 150 + i * 18}" width="${w}" height="7" rx="3" fill="#2b251d" opacity="0.82"/>`;
    });
  }
  return `
  <rect width="800" height="500" fill="#e6dcc8"/>
  <rect x="60" y="24" width="680" height="470" rx="6" fill="#f6f1e7"/>
  <text x="90" y="86" font-family="Inter, Arial, sans-serif" font-size="30" font-weight="800" fill="#2b251d">Employment record</text>
  <rect x="90" y="104" width="610" height="3" fill="#2b251d"/>
  <text x="90" y="144" font-family="Inter, Arial, sans-serif" font-size="16" fill="#5c5346">Name: Aarav Menon     Department: People Operations</text>
  ${lines}
  <circle cx="630" cy="420" r="44" fill="none" stroke="#c4633f" stroke-width="4"/>
  <text x="630" y="426" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="15" font-weight="800" fill="#c4633f">VERIFIED</text>`;
}

export function docAfter(id) {
  return `<svg viewBox="0 0 800 500" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Cleaned HR document">${docBody()}</svg>`;
}

export function docBefore(id) {
  return `<svg viewBox="0 0 800 500" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Scanned HR document with shadows">
  <defs>${SOFTEN(id, 2.2)}${NOISE(id)}
    <linearGradient id="sh-${id}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#8a6a3a" stop-opacity="0.55"/><stop offset="0.5" stop-color="#c9b98f" stop-opacity="0.2"/><stop offset="1" stop-color="#5c5346" stop-opacity="0.5"/>
    </linearGradient>
  </defs>
  <g filter="url(#f-${id})">${docBody()}</g>
  <rect width="800" height="500" fill="url(#sh-${id})"/>
  <rect width="800" height="500" filter="url(#n-${id})" opacity="0.5"/>
</svg>`;
}
