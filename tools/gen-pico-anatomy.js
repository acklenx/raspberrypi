// Generates docs/img/pico-anatomy.svg: the Pico 2 W with the pins and
// parts a student actually needs, circled and labeled.
//
//   node tools/gen-pico-anatomy.js

const fs = require("fs");
const path = require("path");

const C = {
  blue: "#2E7DBC", green: "#7CB342", orange: "#E8762C", yellow: "#C99A1E",
  navy: "#1B3A5C", ink: "#222A35", gray: "#6B7280",
  board: "#1B5E20", boardEdge: "#0E3D12", pad: "#C9A227", padHole: "#5C4A00",
  padOff: "#AEB6BF", red: "#C62828",
};
const FUNC = {
  1: "GP0", 2: "GP1", 3: "GND", 4: "GP2", 5: "GP3", 6: "GP4", 7: "GP5",
  8: "GND", 9: "GP6", 10: "GP7", 11: "GP8", 12: "GP9", 13: "GND",
  14: "GP10", 15: "GP11", 16: "GP12", 17: "GP13", 18: "GND", 19: "GP14",
  20: "GP15", 21: "GP16", 22: "GP17", 23: "GND", 24: "GP18", 25: "GP19",
  26: "GP20", 27: "GP21", 28: "GND", 29: "GP22", 30: "RUN", 31: "GP26",
  32: "GP27", 33: "AGND", 34: "GP28", 35: "VREF", 36: "3V3", 37: "3V3EN",
  38: "GND", 39: "VSYS", 40: "VBUS",
};
const ADC = { 31: "ADC0", 32: "ADC1", 34: "ADC2" };

const BX = 420, BY = 96, BW = 170, BH = 520;
const ROW_Y0 = BY + 40, PITCH = 24;
const PAD_L = BX + 15, PAD_R = BX + BW - 15;

function pin(p) {
  let row, x;
  if (p <= 20) { row = p - 1; x = PAD_L; }
  else { row = 40 - p; x = PAD_R; }
  return { x, y: ROW_Y0 + row * PITCH, side: p <= 20 ? "L" : "R" };
}
function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;"); }
function text(x, y, s, o = {}) {
  const { size = 12, color = C.ink, bold = false, anchor = "start", italic = false } = o;
  return `<text x="${x}" y="${y}" font-family="Arial, Helvetica, sans-serif" font-size="${size}"`
    + ` fill="${color}" text-anchor="${anchor}"${bold ? ' font-weight="bold"' : ""}`
    + `${italic ? ' font-style="italic"' : ""}>${esc(s)}</text>`;
}

let s = "";

// board
s += `<rect x="${BX}" y="${BY}" width="${BW}" height="${BH}" rx="12" fill="${C.board}" stroke="${C.boardEdge}" stroke-width="2"/>`;
// USB connector
s += `<rect x="${BX + BW / 2 - 26}" y="${BY - 16}" width="52" height="22" rx="4" fill="#9AA5AD" stroke="#6B7680" stroke-width="1.5"/>`;
// BOOTSEL button
const BSX = BX + BW / 2, BSY = BY + 72;
s += `<rect x="${BSX - 18}" y="${BSY - 12}" width="36" height="24" rx="4" fill="#E8E8E8" stroke="#8B949C" stroke-width="1.5"/>`;
s += `<circle cx="${BSX}" cy="${BSY}" r="7" fill="#CFCFCF" stroke="#8B949C"/>`;
s += text(BSX, BSY + 26, "BOOTSEL", { size: 9, color: "#C7E0C9", anchor: "middle", bold: true });
// onboard LED
const LEDX = BX + 46, LEDY = BY + 26;
s += `<rect x="${LEDX - 6}" y="${LEDY - 4}" width="12" height="8" rx="2" fill="#7CFF6B" stroke="#3B8C3F"/>`;
s += text(LEDX, LEDY + 18, "LED", { size: 9, color: "#C7E0C9", anchor: "middle", bold: true });
// radio can
s += `<rect x="${BX + BW / 2 - 24}" y="${BY + BH - 92}" width="48" height="40" rx="4" fill="#B8BEC4" stroke="#8B949C" stroke-width="1.5"/>`;
s += text(BX + BW / 2, BY + BH - 68, "Wi-Fi", { size: 9, color: "#4A5A66", anchor: "middle" });
s += text(BX + BW / 2, BY + 26, "Pico 2 W", { size: 13, color: "#C7E0C9", anchor: "middle", bold: true });

// pins
for (let p = 1; p <= 40; p++) {
  const { x, y } = pin(p);
  s += `<rect x="${x - 8}" y="${y - 8}" width="16" height="16" rx="3" fill="${C.pad}" stroke="${C.boardEdge}" stroke-width="1"/>`;
  s += `<circle cx="${x}" cy="${y}" r="3.4" fill="${C.padHole}"/>`;
  const inX = p <= 20 ? x + 14 : x - 14;
  const anchor = p <= 20 ? "start" : "end";
  s += text(inX, y + 4, FUNC[p], { size: 11, color: "#EAF4EB", anchor });
  if (ADC[p]) {
    const ax = p <= 20 ? inX + 38 : inX - 40;
    s += text(ax, y + 4, ADC[p], { size: 8.5, color: "#A6C4A8", anchor });
  }
  const numX = p <= 20 ? x - 14 : x + 14;
  s += text(numX, y + 4, p, { size: 10, color: C.gray, anchor: p <= 20 ? "end" : "start" });
}

// ---- callouts: circle the pin/part, leader line to a label ----------
function callout(px, py, lx, ly, title, lines, color, anchor) {
  let o = `<circle cx="${px}" cy="${py}" r="14" fill="none" stroke="${color}" stroke-width="3"/>`;
  o += `<line x1="${px + (anchor === "end" ? -14 : 14)}" y1="${py}" x2="${lx + (anchor === "end" ? 8 : -8)}" y2="${ly - 4}" stroke="${color}" stroke-width="1.8"/>`;
  o += text(lx, ly, title, { size: 14, color, bold: true, anchor });
  lines.forEach((ln, i) => {
    o += text(lx, ly + 16 + i * 14, ln, { size: 11, color: C.ink, anchor });
  });
  return o;
}

const p36 = pin(36), p38 = pin(38), p40 = pin(40), p29 = pin(29);
const p1 = pin(1), p2 = pin(2), p31 = pin(31);

s += callout(BSX, BSY, 130, 108, "BOOTSEL (Boot SELect)", [
  "Hold while plugging in USB and the chip",
  "boots from its USB bootloader instead of",
  "flash: the board becomes a flash drive",
  "you drop firmware onto. One button,",
  "two boot sources.",
], C.orange, "start");

s += callout(LEDX, LEDY, 130, 40, "Onboard LED, the truth light", [
  "Blinking = your code is running.",
  "POST codes say which part is unhappy.",
], C.green, "start");

s += `<ellipse cx="${p1.x}" cy="${(p1.y + p2.y) / 2}" rx="16" ry="28" fill="none" stroke="${C.blue}" stroke-width="3"/>`;
s += `<line x1="${p1.x - 16}" y1="${(p1.y + p2.y) / 2}" x2="138" y2="206" stroke="${C.blue}" stroke-width="1.8"/>`;
s += ((lx, ly, title, lines, color, anchor) => { let o = text(lx, ly, title, { size: 14, color, bold: true, anchor });
  lines.forEach((ln, i) => { o += text(lx, ly + 16 + i * 14, ln, { size: 11, color: C.ink, anchor }); }); return o; })(130, 210, "GP0 + GP1: the I2C bus", [
  "SDA (green wire) and SCL (white wire).",
  "OLED, BME280, ADS1115 all share these",
  "two pins. Physical pins 1 and 2.",
], C.blue, "start");

s += callout(p36.x, p36.y, 905, 200, "3V3, physical pin 36", [
  "The 3.3 V power output.",
  "Feeds every sensor we use.",
  "The RED wire starts here.",
], C.red, "start");
s += callout(p40.x, p40.y, 905, 120, "VBUS, physical pin 40", [
  "Raw 5 V straight from USB.",
  "Servo food. Never for sensors.",
], C.orange, "start");
s += callout(p38.x, p38.y, 905, 288, "GND, physical pin 38", [
  "Ground, the shared zero volts.",
  "The BLACK wire. (Any of the 8",
  "GND pins works: 3, 8, 13, 18,",
  "23, 28, 33, 38.)",
], C.ink, "start");
s += callout(p29.x, p29.y, 905, 400, "GP22, physical pin 29", [
  "Our DS18B20 one-wire bus.",
  "Note: GP number and physical pin",
  "number are DIFFERENT numbers.",
], C.yellow, "start");
s += callout(p31.x, p31.y, 905, 490, "GP26 / GP27 / GP28", [
  "The three analog (ADC) pins,",
  "physical 31, 32, 34. Soil",
  "moisture, mic, photoresistor",
  "live here. Only these three",
  "can read analog.",
], C.green, "start");

s += text(130, 662, "Numbers INSIDE the green board are GP names (what code uses).", { size: 12, color: C.gray });
s += text(130, 678, "Numbers OUTSIDE are physical pin positions (what you count to when wiring).", { size: 12, color: C.gray });
s += text(40, 706, "Maker Lab Kids · the Pico 2 W, introduced properly", { size: 11, color: C.gray });
s += text(1110, 706, "MakerLabKids.com", { size: 11, color: C.blue, anchor: "end", bold: true });

const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1150 720" font-family="Arial, Helvetica, sans-serif">`
  + `<rect width="1150" height="720" fill="#FFFFFF"/>` + s + `</svg>`;

const OUT = path.join(__dirname, "..", "docs", "img");
fs.mkdirSync(OUT, { recursive: true });
fs.writeFileSync(path.join(OUT, "pico-anatomy.svg"), svg);
console.log("wrote docs/img/pico-anatomy.svg (" + svg.length + " bytes)");
