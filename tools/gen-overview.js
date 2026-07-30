// Generates docs/img/overview.svg: a friendly, labeled picture of ONE
// student's station. Labels are clickable (SVG <a>, target=_top) so the
// file works both inline and as an <object>. node tools/gen-overview.js

const fs = require("fs");
const path = require("path");

const C = {
  blue: "#2E7DBC", green: "#7CB342", orange: "#E8762C", navy: "#1B3A5C",
  ink: "#222A35", gray: "#6B7280", tan: "#E9D9B6", tanEdge: "#C9B489",
  board: "#1B7A3A", boardEdge: "#0E4D22", pad: "#D8B54A", screen: "#0B1220",
  cyan: "#38E8FF", teal: "#2AA9A0", red: "#C62828", wire: "#7CB342",
};
const W = 1000, H = 580;
let s = "";

function esc(t) { return String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;"); }
function txt(x, y, t, o = {}) {
  const { size = 14, color = C.ink, bold = false, anchor = "start", italic = false } = o;
  return `<text x="${x}" y="${y}" font-family="Arial, Helvetica, sans-serif" font-size="${size}"`
    + ` fill="${color}" text-anchor="${anchor}"${bold ? ' font-weight="bold"' : ""}`
    + `${italic ? ' font-style="italic"' : ""}>${esc(t)}</text>`;
}
// a clickable label: dot on the part, leader line, bold title + subtitle.
// `tie` picks which point of the TEXT BLOCK the leader attaches to, so a
// line reaches an edge/corner of the words instead of cutting across them.
function label(px, py, lx, ly, anchor, href, title, sub, color, tie) {
  // estimate the text block's size so we can find its edges/center
  const tw = Math.max(title.length * 15.5 * 0.58, sub.length * 12.5 * 0.52);
  const leftX = anchor === "middle" ? lx - tw / 2 : anchor === "end" ? lx - tw : lx;
  const centerX = leftX + tw / 2;
  const topY = ly - 17, bottomY = ly + 18;   // title top ... sub bottom
  let ex = lx, ey = ly;                       // default: old attach point
  if (tie === "bottom-center") { ex = centerX; ey = bottomY; }
  else if (tie === "top-center") { ex = centerX; ey = topY; }
  else if (tie === "bottom-left") { ex = leftX; ey = bottomY; }
  else if (tie === "top-left") { ex = leftX; ey = topY; }
  let g = `<a href="${href}" target="_top">`;
  g += `<circle cx="${px}" cy="${py}" r="7" fill="none" stroke="${color}" stroke-width="3"/>`;
  g += `<circle cx="${px}" cy="${py}" r="2.5" fill="${color}"/>`;
  g += `<path d="M${px} ${py} L${ex} ${ey}" stroke="${color}" stroke-width="2" fill="none"/>`;
  g += txt(lx, ly - 4, title, { size: 15.5, bold: true, color: C.navy, anchor });
  g += txt(lx, ly + 14, sub, { size: 12.5, color: C.gray, anchor });
  g += `</a>`;
  return g;
}

// ---- the breadboard ----
s += `<rect x="250" y="330" width="340" height="150" rx="12" fill="${C.tan}" stroke="${C.tanEdge}" stroke-width="2"/>`;
for (let r = 0; r < 4; r++) for (let c = 0; c < 22; c++) {
  s += `<circle cx="${268 + c * 14.5}" cy="${356 + r * 26}" r="2.2" fill="${C.tanEdge}"/>`;
}

// ---- the Pico ----
const px = 285, py = 348, pw = 120, ph = 120;
s += `<rect x="${px}" y="${py}" width="${pw}" height="${ph}" rx="10" fill="${C.board}" stroke="${C.boardEdge}" stroke-width="2"/>`;
s += `<rect x="${px + pw / 2 - 18}" y="${py - 10}" width="36" height="14" rx="3" fill="#9AA5AD"/>`;
for (let i = 0; i < 8; i++) {
  s += `<rect x="${px + 6}" y="${py + 12 + i * 13}" width="9" height="9" rx="2" fill="${C.pad}"/>`;
  s += `<rect x="${px + pw - 15}" y="${py + 12 + i * 13}" width="9" height="9" rx="2" fill="${C.pad}"/>`;
}
s += `<rect x="${px + 30}" y="${py + 40}" width="60" height="40" rx="4" fill="#12331d"/>`;
s += txt(px + pw / 2, py + 64, "Pico", { size: 13, color: "#CFEAD6", anchor: "middle", bold: true });
// onboard LED, lit
s += `<circle cx="${px + 22}" cy="${py + 16}" r="4" fill="#7CFF6B"/>`;

// ---- the sensor ----
const sx = 430, sy = 356, sw = 96, sh = 66;
s += `<rect x="${sx}" y="${sy}" width="${sw}" height="${sh}" rx="8" fill="${C.teal}" stroke="#1c7d76" stroke-width="2"/>`;
s += `<circle cx="${sx + sw / 2}" cy="${sy + 26}" r="13" fill="#0e4d48"/>`;
s += `<circle cx="${sx + sw / 2}" cy="${sy + 26}" r="6" fill="#7fd8d0"/>`;
s += txt(sx + sw / 2, sy + 56, "sensor", { size: 11, color: "#e6fffb", anchor: "middle", bold: true });
// two wires Pico -> sensor
s += `<path d="M${px + pw} ${py + 30} q30 0 ${sx - (px + pw)} 10" stroke="${C.red}" stroke-width="3" fill="none"/>`;
s += `<path d="M${px + pw} ${py + 56} q30 20 ${sx - (px + pw)} 24" stroke="${C.wire}" stroke-width="3" fill="none"/>`;

// ---- the OLED screen ----
const ox = 300, oy = 250, ow = 150, oh = 62;
s += `<rect x="${ox}" y="${oy}" width="${ow}" height="${oh}" rx="6" fill="${C.screen}" stroke="#33414f" stroke-width="2"/>`;
s += txt(ox + 12, oy + 26, "Soil temp", { size: 12, color: "#7fbfd8" });
s += txt(ox + 12, oy + 48, "24.6", { size: 24, color: C.cyan, bold: true });
s += txt(ox + 74, oy + 48, "C", { size: 14, color: "#7fbfd8" });
// wire Pico -> OLED
s += `<path d="M${px + 40} ${py} q-6 -20 ${ox + 40 - (px + 40)} ${oy + oh - py}" stroke="${C.blue}" stroke-width="3" fill="none"/>`;

// ---- WiFi arcs ----
const wx = px + pw + 6, wy = py + 4;
for (let i = 1; i <= 3; i++) {
  s += `<path d="M${wx} ${wy - i * 4} a${i * 16} ${i * 16} 0 0 1 ${i * 13} ${i * 15}" stroke="${C.orange}" stroke-width="3" fill="none" opacity="${1 - i * 0.18}"/>`;
}

// ---- the phone ----
const fx = 700, fy = 210, fw = 180, fh = 320;
s += `<rect x="${fx}" y="${fy}" width="${fw}" height="${fh}" rx="22" fill="#111827" stroke="#2b3648" stroke-width="3"/>`;
s += `<rect x="${fx + 12}" y="${fy + 26}" width="${fw - 24}" height="${fh - 52}" rx="8" fill="#0f172a"/>`;
s += `<circle cx="${fx + fw / 2}" cy="${fy + 14}" r="3" fill="#33414f"/>`;
s += txt(fx + fw / 2, fy + 50, "MY WORM BIN", { size: 12, color: "#a3e635", anchor: "middle", bold: true });
// two stat cards
const cards = [["TEMP", "24.6", "#fb923c"], ["WATER", "63%", "#38bdf8"]];
cards.forEach((cd, i) => {
  const cy2 = fy + 66 + i * 66;
  s += `<rect x="${fx + 22}" y="${cy2}" width="${fw - 44}" height="54" rx="8" fill="#1e293b"/>`;
  s += txt(fx + 34, cy2 + 20, cd[0], { size: 10, color: "#94a3b8", bold: true });
  s += txt(fx + 34, cy2 + 44, cd[1], { size: 24, color: cd[2], bold: true });
});
// a little bar chart
const by = fy + 206;
s += `<rect x="${fx + 22}" y="${by}" width="${fw - 44}" height="72" rx="8" fill="#1e293b"/>`;
[30, 55, 40, 70, 60, 85].forEach((h, i) => {
  s += `<rect x="${fx + 34 + i * 20}" y="${by + 60 - h * 0.6}" width="12" height="${h * 0.6}" rx="2" fill="#34d399"/>`;
});
// wifi -> phone dotted link
s += `<path d="M${wx + 42} ${wy + 30} Q600 120 ${fx} ${fy + 90}" stroke="${C.orange}" stroke-width="2.5" fill="none" stroke-dasharray="4 6"/>`;

// ---- labels (clickable) ----
s += label(px + 60, py + ph, 210, 520, "start", "sessions.html",
  "Breadboard", "push parts together, no soldering yet", "#B08A3C", "top-center");
s += label(px + 30, py + 60, 70, 300, "start", "glossary.html#the-pico",
  "The brain", "a tiny $8 computer", C.green, "bottom-center");
s += label(sx + sw / 2, sy + 26, 500, 500, "start", "stations.html",
  "A sensor", "it measures the world", C.teal);
s += label(ox + ow - 30, oy, 330, 216, "start", "glossary.html",
  "A little screen", "see the reading right here", C.blue, "bottom-left");
s += label(wx + 34, wy + 2, 560, 216, "start", "sessions.html",
  "Its own WiFi", "no internet needed", C.orange);
s += label(fx + fw / 2, fy + 150, 760, 555, "middle", "demos/mission-control.html",
  "Your phone or laptop", "watch it live, anywhere in the room", C.navy, "top-left");

const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="60 195 880 375" font-family="Arial, Helvetica, sans-serif" role="img" aria-label="One student station: a Pico, a sensor, and a screen on a breadboard, sending readings over its own WiFi to a phone.">`
  + `<rect width="${W}" height="${H}" fill="#FFFFFF"/>` + s + `</svg>`;

const OUT = path.join(__dirname, "..", "docs", "img");
fs.mkdirSync(OUT, { recursive: true });
fs.writeFileSync(path.join(OUT, "overview.svg"), svg);
console.log("wrote docs/img/overview.svg (" + svg.length + " bytes)");
