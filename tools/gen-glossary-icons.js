// gen-glossary-icons.js - small, consistent cartoon icons for glossary terms.
// One SVG per term id at docs/img/glossary/<id>.svg. The glossary auto-shows
// an icon wherever the file exists, so adding art here needs no HTML edits.
//   node tools/gen-glossary-icons.js
const fs = require("fs");
const path = require("path");

const C = { blue:"#2E7DBC", green:"#7CB342", orange:"#E8762C", yellow:"#E8B62C",
  navy:"#1B3A5C", ink:"#222A35", gray:"#6B7280", red:"#C62828", line:"#C9D3DD",
  gold:"#C9A227", copper:"#B5651D", skin:"#F4F7FA" };
const W = 132, H = 96;

function svg(inner) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" `
    + `font-family="Arial, Helvetica, sans-serif">`
    + `<rect width="${W}" height="${H}" fill="#FFFFFF"/>${inner}</svg>`;
}
const t = (x,y,s,o={}) => `<text x="${x}" y="${y}" font-size="${o.s||11}" `
  + `fill="${o.c||C.gray}" text-anchor="${o.a||"middle"}"${o.b?' font-weight="bold"':""}>${s}</text>`;

const ICONS = {};

// ---- electricity ----------------------------------------------------
ICONS.voltage = () =>                      // water tower = pressure
  `<rect x="30" y="16" width="42" height="30" rx="4" fill="${C.blue}" opacity=".85"/>`
  + `<rect x="46" y="46" width="10" height="26" fill="${C.line}"/>`
  + `<path d="M40 72 h60 v6 h-60z" fill="${C.blue}"/>`
  + `<path d="M100 78 q8 8 0 12" fill="none" stroke="${C.blue}" stroke-width="3"/>`
  + t(51,66,"V",{c:"#fff",b:1,s:14}) + t(51,90,"pressure");
ICONS.current = () =>                       // charges flowing
  `<line x1="14" y1="42" x2="112" y2="42" stroke="${C.navy}" stroke-width="4"/>`
  + `<path d="M96 42 l14 0 m-8 -6 l8 6 -8 6" fill="none" stroke="${C.blue}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>`
  + [26,50,74].map(x=>`<circle cx="${x}" cy="42" r="6" fill="${C.blue}"/>`).join("")
  + t(66,74,"I",{c:C.blue,b:1,s:14}) + t(66,90,"flow");
ICONS.resistance = () =>                    // a squeeze in the pipe
  `<path d="M12 40 h34 l14 8 -14 8 h-34z M120 40 h-34 l-14 8 14 8 h34z" fill="${C.orange}" opacity=".85"/>`
  + `<circle cx="66" cy="48" r="7" fill="${C.navy}"/>` + t(66,86,"pushes back");
ICONS.ground = () =>                        // ground symbol
  `<line x1="66" y1="20" x2="66" y2="46" stroke="${C.ink}" stroke-width="4"/>`
  + `<line x1="42" y1="46" x2="90" y2="46" stroke="${C.ink}" stroke-width="5"/>`
  + `<line x1="52" y1="56" x2="80" y2="56" stroke="${C.ink}" stroke-width="5"/>`
  + `<line x1="60" y1="66" x2="72" y2="66" stroke="${C.ink}" stroke-width="5"/>`
  + t(66,88,"0 V, the black wire");
ICONS["short-circuit"] = () =>              // + straight to - , spark
  `<path d="M20 30 h40 v40 h40" fill="none" stroke="${C.red}" stroke-width="4"/>`
  + `<path d="M60 30 v40" stroke="${C.red}" stroke-width="4"/>`
  + `<path d="M58 44 l8 -3 -4 7 8 -2 -9 10 3 -7 -8 2z" fill="${C.yellow}" stroke="${C.orange}"/>`
  + t(66,88,"power straight to GND");
ICONS["open-circuit"] = () =>               // a break/gap
  `<line x1="16" y1="46" x2="56" y2="46" stroke="${C.navy}" stroke-width="4"/>`
  + `<line x1="76" y1="46" x2="116" y2="46" stroke="${C.navy}" stroke-width="4"/>`
  + `<circle cx="56" cy="46" r="4" fill="${C.navy}"/><circle cx="76" cy="46" r="4" fill="${C.navy}"/>`
  + t(66,30,"gap",{c:C.red,b:1}) + t(66,88,"no current flows");

// ---- parts ----------------------------------------------------------
function band(x,col){ return `<rect x="${x}" y="40" width="6" height="24" fill="${col}"/>`; }
ICONS.resistor = () =>
  `<line x1="8" y1="52" x2="30" y2="52" stroke="${C.gray}" stroke-width="3"/>`
  + `<line x1="102" y1="52" x2="124" y2="52" stroke="${C.gray}" stroke-width="3"/>`
  + `<rect x="30" y="40" width="72" height="24" rx="10" fill="#D9B98F"/>`
  + band(42,C.yellow)+band(54,"#7A4DA0")+band(66,C.red)+band(88,C.gold)
  + t(66,86,"color bands = value");
ICONS.led = () =>
  `<path d="M52 54 a14 14 0 0 1 28 0 v6 h-28z" fill="${C.green}"/>`
  + `<rect x="52" y="60" width="28" height="6" fill="${C.green}"/>`
  + `<line x1="60" y1="66" x2="60" y2="86" stroke="${C.gray}" stroke-width="3"/>`
  + `<line x1="72" y1="66" x2="72" y2="80" stroke="${C.gray}" stroke-width="3"/>`
  + [[66,20],[92,30],[96,54]].map(([x,y])=>`<line x1="66" y1="42" x2="${x+ (x-66)*0.2}" y2="${y}" stroke="${C.yellow}" stroke-width="3" stroke-linecap="round"/>`).join("")
  + t(66,94,"long leg = +");
ICONS.photoresistor = () =>
  `<circle cx="60" cy="46" r="24" fill="#F6E7A0" stroke="${C.gray}" stroke-width="2"/>`
  + `<path d="M46 46 q7 -10 14 0 q7 10 14 0" fill="none" stroke="${C.copper}" stroke-width="3"/>`
  + [[92,20],[100,40]].map(([x,y])=>`<line x1="72" y1="34" x2="${x}" y2="${y}" stroke="${C.yellow}" stroke-width="3" stroke-linecap="round"/>`).join("")
  + t(60,90,"more light, less Ω");
ICONS.servo = () =>
  `<rect x="34" y="40" width="46" height="40" rx="4" fill="${C.blue}"/>`
  + `<circle cx="80" cy="34" r="7" fill="${C.navy}"/>`
  + `<rect x="77" y="10" width="6" height="26" rx="3" fill="${C.gray}" transform="rotate(30 80 34)"/>`
  + `<path d="M96 30 a10 10 0 0 1 0 8" fill="none" stroke="${C.orange}" stroke-width="3"/>`
  + t(57,92,"goes to an angle");
ICONS.relay = () =>
  `<rect x="30" y="34" width="72" height="40" rx="5" fill="#3F6EA5"/>`
  + `<line x1="46" y1="60" x2="66" y2="46" stroke="#fff" stroke-width="4" stroke-linecap="round"/>`
  + `<circle cx="46" cy="60" r="4" fill="#fff"/><circle cx="70" cy="46" r="4" fill="#fff"/>`
  + `<rect x="82" y="46" width="10" height="16" rx="2" fill="${C.orange}"/>`
  + t(66,90,"a switch you click");
ICONS.breadboard = () => {
  let dots=""; for(let r=0;r<4;r++)for(let c=0;c<9;c++)dots+=`<circle cx="${26+c*10}" cy="${34+r*9}" r="2.3" fill="${C.line}"/>`;
  return `<rect x="14" y="20" width="104" height="60" rx="6" fill="#F1ECDD" stroke="#D8CFB8"/>`
    + `<rect x="14" y="48" width="104" height="6" fill="#EDE6D2"/>` + dots + t(66,92,"rows of 5 connect");
};
ICONS["jumper-wires"] = () => {
  const cols=[C.red,C.orange,C.ink,C.green,"#DDD",C.yellow,C.blue];
  return cols.map((c,i)=>`<path d="M${18+i*15} 20 q6 30 0 56" fill="none" stroke="${c==='#DDD'?'#CFCFCF':c}" stroke-width="5" stroke-linecap="round"/>`).join("")
    + t(66,92,"one meaning per color");
};
ICONS.multimeter = () =>
  `<rect x="34" y="22" width="64" height="56" rx="6" fill="${C.yellow}"/>`
  + `<rect x="42" y="30" width="48" height="18" rx="3" fill="#1c3b2a"/>` + t(66,44,"3.3",{c:"#8dffb0",b:1,s:12})
  + `<circle cx="66" cy="62" r="9" fill="#fff" stroke="${C.gray}"/><line x1="66" y1="62" x2="72" y2="56" stroke="${C.ink}" stroke-width="2"/>`
  + t(66,92,"volts, ohms, beeps");

// ---- buses / signals ------------------------------------------------
ICONS.i2c = () =>
  `<line x1="10" y1="34" x2="122" y2="34" stroke="${C.green}" stroke-width="4"/>`
  + `<line x1="10" y1="46" x2="122" y2="46" stroke="#BFC9D2" stroke-width="4"/>`
  + [24,58,92].map(x=>`<g><rect x="${x-8}" y="52" width="16" height="16" rx="2" fill="${C.blue}"/><line x1="${x-3}" y1="52" x2="${x-3}" y2="46" stroke="${C.gray}" stroke-width="2"/><line x1="${x+3}" y1="52" x2="${x+3}" y2="34" stroke="${C.gray}" stroke-width="2"/></g>`).join("")
  + t(66,88,"2 wires, many chips");
ICONS.pwm = () => {
  let d="M12 66 "; const seg=[[10,'up'],[14,'dn'],[22,'up'],[6,'dn'],[10,'up'],[24,'dn'],[10,'up']];
  let x=12,y=66; d="M12 66 "; const pts=[[12,66]];
  const on=[16,66],pat=[8,20,8,20,30,8]; // widths alternating low/high heights
  // simple square wave
  let path=`M12 66 `; let cx=12; const w=[10,18,10,10,26,10,14];
  let hi=false;
  for(const seg2 of w){ const ny = hi?46:66; path+=`H${cx} V${ny} `; cx+=seg2; hi=!hi; }
  path+=`H120`;
  return `<path d="${path}" fill="none" stroke="${C.blue}" stroke-width="4" stroke-linejoin="round"/>`
    + t(66,88,"on/off, fast = a level");
};
ICONS["digital-vs-analog"] = () =>
  `<path d="M12 62 H32 V34 H56 V62 H80" fill="none" stroke="${C.navy}" stroke-width="4"/>`
  + `<path d="M80 60 q12 -34 24 0 t24 0" fill="none" stroke="${C.orange}" stroke-width="4"/>`
  + t(40,90,"digital",{c:C.navy}) + t(100,90,"analog",{c:C.orange});
ICONS.adc = () =>
  `<path d="M12 62 q14 -34 28 0" fill="none" stroke="${C.orange}" stroke-width="4"/>`
  + `<path d="M52 46 h10 v-8 h10 v-6" fill="none" stroke="${C.navy}" stroke-width="3"/>`
  + `<rect x="74" y="30" width="44" height="30" rx="4" fill="${C.blue}"/>` + t(96,50,"1 0 1",{c:"#fff",b:1,s:11})
  + t(66,88,"voltage -> number");

// ---- debugging ------------------------------------------------------
ICONS["brown-out"] = () =>
  `<path d="M12 34 H50 L60 66 L70 34 H120" fill="none" stroke="${C.red}" stroke-width="4"/>`
  + t(60,84,"voltage sags, reset",{c:C.red});
ICONS["cold-joint"] = () =>
  `<line x1="66" y1="18" x2="66" y2="44" stroke="${C.gray}" stroke-width="5"/>`
  + `<path d="M50 62 q16 -20 32 0 q-4 6 -16 6 q-12 0 -16 -6z" fill="#9AA6B0"/>`
  + `<path d="M60 52 l4 8" stroke="${C.red}" stroke-width="2"/>` + t(66,90,"dull + cracked = bad");
ICONS["floating-pin"] = () =>
  `<rect x="40" y="30" width="30" height="30" rx="4" fill="${C.blue}"/>` + t(55,50,"?",{c:"#fff",b:1,s:16})
  + `<line x1="70" y1="45" x2="96" y2="45" stroke="${C.gray}" stroke-width="3" stroke-dasharray="4 4"/>`
  + `<circle cx="96" cy="45" r="3" fill="${C.gray}"/>` + t(66,86,"nothing attached = noise");

// ---- the truth light ------------------------------------------------
ICONS["onboard-led-the-truth-light"] = () =>
  `<rect x="30" y="30" width="72" height="40" rx="6" fill="#186c34"/>`
  + `<rect x="42" y="42" width="14" height="9" rx="2" fill="#7CFF6B"/>`
  + [[86,26,C.yellow],[96,42,C.yellow]].map(([x,y,c])=>`<line x1="56" y1="46" x2="${x}" y2="${y}" stroke="${c}" stroke-width="3" stroke-linecap="round"/>`).join("")
  + t(66,88,"blinking = it's alive");

const OUT = path.join(__dirname, "..", "docs", "img", "glossary", "icons");
fs.mkdirSync(OUT, { recursive: true });
let n = 0;
for (const id in ICONS) { fs.writeFileSync(path.join(OUT, id + ".svg"), svg(ICONS[id]())); n++; }
console.log("wrote " + n + " glossary icons to docs/img/glossary/");
