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

// ---- basics / code words -------------------------------------------
ICONS.microcontroller = () =>
  `<rect x="40" y="26" width="52" height="44" rx="4" fill="${C.navy}"/>`
  + [0,1,2,3].map(i=>`<line x1="${48+i*12}" y1="26" x2="${48+i*12}" y2="16" stroke="${C.gray}" stroke-width="3"/><line x1="${48+i*12}" y1="70" x2="${48+i*12}" y2="80" stroke="${C.gray}" stroke-width="3"/>`).join("")
  + t(66,52,"chip",{c:"#fff",s:11,b:1}) + t(66,92,"a whole computer");
ICONS.micropython = () =>
  `<path d="M40 34 q26 -16 40 6 q-14 -6 -22 4 q10 8 22 4 q-2 22 -22 22 q-20 0 -18 -18 q10 6 20 2 q-12 -6 -20 -2 q0 -14 0 -20z" fill="${C.blue}"/>`
  + `<circle cx="72" cy="40" r="2.5" fill="#fff"/>` + t(66,90,"the language");
ICONS.ide = () =>
  `<rect x="20" y="22" width="92" height="56" rx="5" fill="#20303f"/>`
  + `<rect x="20" y="22" width="92" height="12" rx="5" fill="#33475a"/>`
  + [26,34,42].map((x,i)=>`<circle cx="${x}" cy="28" r="2.5" fill="${[C.red,C.yellow,C.green][i]}"/>`).join("")
  + [42,52,62].map((y,i)=>`<line x1="30" y1="${y}" x2="${70-i*10}" y2="${y}" stroke="${[C.green,C.blue,C.orange][i]}" stroke-width="3"/>`).join("")
  + t(66,92,"where you write code");
ICONS.run = () =>
  `<circle cx="66" cy="46" r="26" fill="${C.green}"/>`
  + `<path d="M58 34 l20 12 -20 12z" fill="#fff"/>` + t(66,90,"press to go");
ICONS.file = () =>
  `<path d="M44 20 h32 l14 14 v42 h-46z" fill="#fff" stroke="${C.gray}" stroke-width="2"/>`
  + `<path d="M76 20 v14 h14" fill="#EDF1F5" stroke="${C.gray}" stroke-width="2"/>`
  + [46,54,62].map(y=>`<line x1="52" y1="${y}" x2="82" y2="${y}" stroke="${C.line}" stroke-width="3"/>`).join("")
  + t(66,92,"named, saved code");
ICONS["upload-install"] = () =>
  `<rect x="34" y="52" width="64" height="24" rx="3" fill="#186c34"/>`
  + `<line x1="66" y1="16" x2="66" y2="44" stroke="${C.blue}" stroke-width="5"/>`
  + `<path d="M56 36 l10 12 10 -12" fill="none" stroke="${C.blue}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>`
  + t(66,92,"copy onto the Pico");
ICONS.dashboard = () =>
  `<rect x="46" y="14" width="40" height="68" rx="6" fill="${C.navy}"/>`
  + `<rect x="50" y="22" width="32" height="52" rx="2" fill="#EAF1F7"/>`
  + `<path d="M56 52 a10 10 0 0 1 20 0" fill="none" stroke="${C.blue}" stroke-width="3"/>`
  + `<line x1="66" y1="52" x2="72" y2="46" stroke="${C.red}" stroke-width="2"/>`
  + [58,64,70].map((x,i)=>`<rect x="${x}" y="${64-i*3}" width="4" height="${6+i*3}" fill="${C.green}"/>`).join("")
  + t(66,92,"readings on your phone");
ICONS["sensor-vs-actuator"] = () =>
  `<circle cx="40" cy="44" r="14" fill="none" stroke="${C.blue}" stroke-width="3"/><circle cx="40" cy="44" r="5" fill="${C.blue}"/>`
  + `<g transform="translate(86,44)"><circle r="12" fill="none" stroke="${C.orange}" stroke-width="3"/>`
  + [0,60,120,180,240,300].map(a=>`<rect x="-2" y="-16" width="4" height="6" fill="${C.orange}" transform="rotate(${a})"/>`).join("")+`</g>`
  + t(40,74,"sense",{c:C.blue}) + t(86,74,"act",{c:C.orange});
ICONS.calibration = () =>
  `<rect x="58" y="16" width="12" height="52" rx="6" fill="#fff" stroke="${C.gray}" stroke-width="2"/>`
  + `<circle cx="64" cy="70" r="10" fill="${C.red}"/><rect x="61" y="36" width="6" height="34" fill="${C.red}"/>`
  + `<line x1="74" y1="24" x2="86" y2="24" stroke="${C.blue}" stroke-width="2"/>` + t(96,27,"100",{c:C.gray,s:9,a:"start"})
  + `<line x1="74" y1="60" x2="86" y2="60" stroke="${C.blue}" stroke-width="2"/>` + t(96,63,"0",{c:C.gray,s:9,a:"start"})
  + t(50,92,"teach it the truth",{a:"start"});
ICONS.repl = () =>
  `<rect x="20" y="24" width="92" height="48" rx="5" fill="#14212e"/>`
  + t(30,54,"&gt;&gt;&gt;",{c:"#7FD07F",b:1,s:16,a:"start"})
  + `<rect x="72" y="44" width="8" height="14" fill="#7FD07F"/>` + t(66,90,"type a line, it runs");
ICONS["main-py"] = () =>
  `<path d="M44 18 h34 l12 12 v46 h-46z" fill="#fff" stroke="${C.blue}" stroke-width="2"/>`
  + `<path d="M78 18 v12 h12" fill="#EDF1F5" stroke="${C.blue}" stroke-width="2"/>`
  + t(66,56,"main",{c:C.navy,b:1,s:13}) + t(66,68,".py",{c:C.blue,b:1,s:12}) + t(66,92,"runs on power-up");

// ---- buses / pico ---------------------------------------------------
ICONS["signal-wire"] = () =>
  `<path d="M12 60 H36 V32 H60 V60 H84 V32 H108 V60 H120" fill="none" stroke="${C.yellow}" stroke-width="4"/>`
  + t(30,80,"HIGH / LOW",{c:C.gray,a:"start"}) + t(66,94,"carries a message");
ICONS.gpio = () =>
  `<rect x="30" y="18" width="72" height="60" rx="4" fill="#186c34"/>`
  + [0,1,2,3,4].map(i=>`<circle cx="40" cy="${28+i*11}" r="4" fill="${C.gold}"/><text x="52" y="${31+i*11}" font-size="8" fill="#dfeee3" font-family="Arial">GP${i}</text>`).join("")
  + t(66,92,"programmable pins");
ICONS["uart-serial"] = () =>
  `<path d="M16 38 H104 m-12 -6 l12 6 -12 6" fill="none" stroke="${C.blue}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>`
  + `<path d="M116 56 H28 m12 -6 l-12 6 12 6" fill="none" stroke="${C.orange}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>`
  + t(96,34,"TX",{c:C.blue,s:9}) + t(36,72,"RX",{c:C.orange,s:9}) + t(66,92,"send + receive");
ICONS.onewire = () =>
  `<line x1="16" y1="46" x2="116" y2="46" stroke="${C.green}" stroke-width="4"/>`
  + [34,62,90].map(x=>`<g><line x1="${x}" y1="46" x2="${x}" y2="62" stroke="${C.green}" stroke-width="3"/><rect x="${x-5}" y="62" width="10" height="12" rx="2" fill="${C.copper}"/></g>`).join("")
  + t(66,92,"1 wire, many probes");
ICONS["3v3-pin"] = () =>
  `<circle cx="50" cy="46" r="14" fill="${C.red}"/>` + t(50,50,"+",{c:"#fff",b:1,s:18})
  + `<line x1="64" y1="46" x2="96" y2="46" stroke="${C.red}" stroke-width="4"/>`
  + t(80,36,"3V3",{c:C.red,b:1,s:12}) + t(66,92,"powers the sensors");
ICONS.bootsel = () =>
  `<rect x="40" y="34" width="52" height="34" rx="6" fill="#E8E8E8" stroke="${C.gray}" stroke-width="2"/>`
  + `<rect x="56" y="42" width="20" height="18" rx="4" fill="#CFCFCF" stroke="${C.gray}"/>`
  + t(66,90,"hold while plugging in");
ICONS.firmware = () =>
  `<rect x="40" y="26" width="52" height="44" rx="4" fill="${C.navy}"/>`
  + `<g transform="translate(66,48)" fill="${C.yellow}"><circle r="7" fill="none" stroke="${C.yellow}" stroke-width="4"/>`
  + [0,60,120,180,240,300].map(a=>`<rect x="-2" y="-13" width="4" height="6" transform="rotate(${a})"/>`).join("")+`</g>`
  + t(66,90,"software baked in");
ICONS["flash-memory"] = () =>
  `<rect x="42" y="24" width="48" height="48" rx="4" fill="#3F6EA5"/>`
  + `<rect x="50" y="24" width="32" height="12" fill="#5580b5"/><rect x="58" y="24" width="16" height="8" fill="#EAF1F7"/>`
  + t(66,56,"MEM",{c:"#fff",b:1,s:11}) + t(66,90,"keeps files, power-off");
ICONS["voltage-divider"] = () =>
  `<line x1="66" y1="16" x2="66" y2="26" stroke="${C.red}" stroke-width="3"/>`
  + `<rect x="58" y="26" width="16" height="18" rx="3" fill="#D9B98F"/>`
  + `<rect x="58" y="52" width="16" height="18" rx="3" fill="#D9B98F"/>`
  + `<line x1="66" y1="44" x2="66" y2="52" stroke="${C.gray}" stroke-width="3"/>`
  + `<line x1="66" y1="70" x2="66" y2="80" stroke="${C.ink}" stroke-width="3"/>`
  + `<line x1="74" y1="48" x2="96" y2="48" stroke="${C.blue}" stroke-width="3"/><circle cx="96" cy="48" r="3" fill="${C.blue}"/>`
  + t(50,92,"tap in the middle",{a:"start"});

// ---- networking / soldering / debugging -----------------------------
ICONS["access-point-vs-station"] = () =>
  `<line x1="40" y1="30" x2="40" y2="70" stroke="${C.navy}" stroke-width="4"/>`
  + [10,18,26].map(r=>`<path d="M40 40 a${r} ${r} 0 0 1 ${r} ${r}" fill="none" stroke="${C.blue}" stroke-width="2"/><path d="M40 40 a${r} ${r} 0 0 0 -${r} ${r}" fill="none" stroke="${C.blue}" stroke-width="2"/>`).join("")
  + `<rect x="82" y="44" width="20" height="30" rx="3" fill="${C.navy}"/>` + t(66,92,"hosts vs joins");
ICONS.json = () =>
  t(30,56,"{",{c:C.orange,b:1,s:34,a:"start"}) + t(96,56,"}",{c:C.orange,b:1,s:34})
  + t(66,44,'"t": 24',{c:C.navy,s:12,b:1}) + t(66,90,"data, plain text");
ICONS.ssid = () =>
  [12,20,28].map(r=>`<path d="M66 62 a${r} ${r} 0 0 1 ${r*0.8} -${r*0.8}" fill="none" stroke="${C.blue}" stroke-width="3"/><path d="M66 62 a${r} ${r} 0 0 0 -${r*0.8} -${r*0.8}" fill="none" stroke="${C.blue}" stroke-width="3"/>`).join("")
  + `<circle cx="66" cy="62" r="4" fill="${C.blue}"/>`
  + `<rect x="40" y="16" width="52" height="16" rx="4" fill="${C.navy}"/>` + t(66,28,"PicoLab7",{c:"#fff",s:10})
  + t(66,92,"the network's name");
ICONS.soldering = () =>
  `<rect x="18" y="22" width="40" height="10" rx="3" fill="${C.ink}" transform="rotate(28 38 27)"/>`
  + `<path d="M60 44 l10 -14 6 4 -10 14z" fill="#B8BEC4"/>`
  + `<path d="M64 58 q10 -10 20 0 q-4 6 -10 6 q-6 0 -10 -6z" fill="${C.gold}"/>`
  + `<path d="M72 44 q3 -6 0 -10" fill="none" stroke="${C.line}" stroke-width="2"/>` + t(66,90,"melt metal to join");
ICONS["header-pins"] = () =>
  `<rect x="24" y="52" width="84" height="12" rx="2" fill="${C.ink}"/>`
  + [0,1,2,3,4,5].map(i=>`<rect x="${30+i*13}" y="26" width="6" height="30" rx="1" fill="${C.gold}"/>`).join("")
  + t(66,90,"pins that plug in");
ICONS["post-codes"] = () =>
  `<rect x="16" y="38" width="100" height="20" rx="6" fill="#14212e"/>`
  + [[28,"s"],[46,"s"],[64,"l"],[82,"s"]].map(([x,k])=>`<rect x="${x}" y="43" width="${k==='l'?18:8}" height="10" rx="3" fill="${k==='l'?C.orange:C.green}"/>`).join("")
  + t(66,84,"blinks say what's wrong");
ICONS["hot-plug"] = () =>
  `<rect x="20" y="34" width="52" height="34" rx="4" fill="#186c34"/><rect x="30" y="44" width="10" height="7" rx="2" fill="#7CFF6B"/>`
  + `<rect x="86" y="46" width="20" height="10" rx="2" fill="${C.gray}"/><line x1="72" y1="51" x2="86" y2="51" stroke="${C.gray}" stroke-width="4"/>`
  + `<path d="M80 40 l4 -6" stroke="${C.yellow}" stroke-width="2"/>` + t(66,90,"plug in while running");
ICONS.stall = () =>
  `<rect x="24" y="40" width="34" height="26" rx="3" fill="${C.blue}"/>`
  + `<rect x="58" y="49" width="26" height="8" rx="2" fill="${C.gray}"/>`
  + `<rect x="88" y="30" width="10" height="48" fill="#9AA6B0"/>`
  + `<path d="M84 44 l6 -3 -3 6 6 -2 -8 9 3 -7z" fill="${C.yellow}" stroke="${C.orange}"/>` + t(56,92,"pushing a hard stop");
ICONS["stale-library"] = () =>
  `<path d="M44 20 h30 l12 12 v46 h-42z" fill="#EDE6D2" stroke="#B9AE90" stroke-width="2"/>`
  + `<path d="M74 20 v12 h12" fill="#DED4B8" stroke="#B9AE90" stroke-width="2"/>`
  + t(65,58,".mpy",{c:"#8a7d5a",b:1,s:13}) + `<circle cx="52" cy="70" r="8" fill="none" stroke="${C.gray}" stroke-width="2"/><line x1="52" y1="70" x2="52" y2="65" stroke="${C.gray}" stroke-width="2"/><line x1="52" y1="70" x2="56" y2="70" stroke="${C.gray}" stroke-width="2"/>`
  + t(66,92,"old copy, shadows new");

const OUT = path.join(__dirname, "..", "docs", "img", "glossary", "icons");
fs.mkdirSync(OUT, { recursive: true });
let n = 0;
for (const id in ICONS) { fs.writeFileSync(path.join(OUT, id + ".svg"), svg(ICONS[id]())); n++; }
console.log("wrote " + n + " glossary icons to docs/img/glossary/");
