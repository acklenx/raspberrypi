// autolink.js - link the FIRST occurrence of each glossary term on each docs
// page to its glossary deep-link (orange dashed .term style). Wikipedia rule:
// once per page. Exception: inside glossary.html, once per <dd> definition.
// Surgical: tokenizes into tags vs text and only wraps matches in text that is
// NOT inside a/code/pre/script/style/nav/headings, so the rest of the HTML is
// preserved byte-for-byte (clean diffs, idempotent).
const fs = require("fs");
const path = require("path");

// id -> phrases that should link to it. Longer/more specific first. cs = match
// case-sensitively (for abbreviations, so "AP"/"IP"/"POST" don't over-match).
const TERMS = [
  ["ohms-law", ["Ohm's law", "Ohm’s law"]],
  ["i2c-address", ["I2C address"]],
  ["voltage-divider", ["voltage divider"]],
  ["pullup-resistor", ["pullup resistor", "pull-up resistor", "pullup", "pull-up"]],
  ["photoresistor", ["photoresistor", "LDR"]],
  ["signal-wire", ["signal wire"]],
  ["short-circuit", ["short circuit", "short-circuit"]],
  ["open-circuit", ["open circuit", "open-circuit"]],
  ["jumper-wires", ["jumper wires", "jumper wire", "DuPont"]],
  ["cold-joint", ["cold joint", "cold-joint"]],
  ["header-pins", ["header pins", "header pin"]],
  ["access-point-vs-station", ["access point"]],
  ["ip-address", ["IP address"]],
  ["http-webserver", ["webserver", "web server", "HTTP"], true],
  ["onboard-led-the-truth-light", ["truth light", "onboard LED"]],
  ["flash-memory", ["flash memory"]],
  ["post-codes", ["POST codes", "power-on self-test", "POST"], true],
  ["brown-out", ["brown-out", "brownout", "brown out"]],
  ["stale-library", ["stale library", ".mpy"]],
  ["hot-plug", ["hot-plug", "hot plug"]],
  ["floating-pin", ["floating pin", "floating"]],
  ["digital-vs-analog", ["digital", "analog"]],
  ["sensor-vs-actuator", ["sensor", "actuator"]],
  ["uart-serial", ["UART", "serial"], true],
  ["vbus-vsys", ["VBUS", "VSYS"], true],
  ["3v3-pin", ["3V3"], true],
  ["onewire", ["OneWire", "1-Wire", "one-wire"]],
  ["exception-try-except", ["try-except", "try/except", "exception"]],
  ["library-driver", ["library"]],
  ["microcontroller", ["microcontroller"]],
  ["micropython", ["MicroPython"]],
  ["program-code", ["program", "code"]],
  ["calibration", ["calibration", "calibrate"]],
  ["breadboard", ["breadboard"]],
  ["multimeter", ["multimeter"]],
  ["resistor", ["resistor"]],
  ["voltage", ["voltage"]],
  ["current", ["current"]],
  ["resistance", ["resistance"]],
  ["ground", ["ground", "GND"]],
  ["firmware", ["firmware"]],
  ["fourwords", ["hardware", "software", "driver"]],
  ["dashboard", ["dashboard"]],
  ["servo", ["servo"]],
  ["relay", ["relay"]],
  ["soldering", ["soldering", "solder"]],
  ["tinning", ["tinning"]],
  ["wetting", ["wetting"]],
  ["flux", ["flux"]],
  ["stall", ["stall"]],
  ["bootsel", ["BOOTSEL"], true],
  ["firmware", ["firmware"]],
  ["gpio", ["GPIO"], true],
  ["adc", ["ADC"], true],
  ["pwm", ["PWM"], true],
  ["i2c", ["I2C"], true],
  ["led", ["LED"], true],
  ["ide", ["Viper IDE", "IDE"]],
  ["repl", ["REPL"], true],
  ["json", ["JSON"], true],
  ["ssid", ["SSID"], true],
  ["ip-address", ["IP"], true],
  ["access-point-vs-station", ["AP", "station"], true],
  ["main-py", ["main.py"]],
  ["run", ["run"]],
  ["file", ["file"]],
  ["upload-install", ["upload", "install"]],
];

function esc(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }

// flatten to matchers, longest phrase first so "voltage divider" beats "voltage"
const MATCH = [];
for (const [id, phrases, cs] of TERMS) {
  for (const p of phrases) {
    MATCH.push({ id, len: p.length,
      re: new RegExp("(?<![A-Za-z0-9])" + esc(p) + "(?![A-Za-z0-9])", cs ? "" : "i") });
  }
}
MATCH.sort((a, b) => b.len - a.len);

const SKIP = new Set(["a", "code", "pre", "kbd", "script", "style", "nav",
  "h1", "h2", "h3", "title", "dt", "button", "option", "textarea"]);

function linkText(text, seen, hrefBase, skipId) {
  let out = "", rest = text, guard = 0;
  while (rest && guard++ < 5000) {
    let best = null;
    for (const m of MATCH) {
      if (seen.has(m.id) || m.id === skipId) continue;
      const r = m.re.exec(rest);
      if (r && (!best || r.index < best.index || (r.index === best.index && r[0].length > best.text.length)))
        best = { id: m.id, index: r.index, text: r[0] };
    }
    if (!best) { out += rest; break; }
    out += rest.slice(0, best.index)
        + '<a class="term" href="' + hrefBase + best.id + '">' + best.text + "</a>";
    seen.add(best.id);
    rest = rest.slice(best.index + best.text.length);
  }
  return out;
}

function process(html, isGlossary) {
  const hrefBase = isGlossary ? "#" : "glossary.html#";
  const parts = html.split(/(<[^>]+>)/);
  const stack = [];                          // {name, skip}
  let pageSeen = new Set(), ddSeen = null, pendingDt = null, skipId = null;
  let out = "";
  const skipActive = () => stack.some(e => e.skip);
  for (let i = 0; i < parts.length; i++) {
    const tok = parts[i];
    if (i % 2 === 1) {                       // a tag
      const mm = tok.match(/^<\s*(\/?)\s*([a-zA-Z0-9]+)/);
      if (mm) {
        const closing = mm[1] === "/", name = mm[2].toLowerCase();
        const selfClose = /\/\s*>$/.test(tok) || ["br", "img", "hr", "input", "meta", "link"].includes(name);
        if (closing) { for (let k = stack.length - 1; k >= 0; k--) if (stack[k].name === name) { stack.splice(k, 1); break; }
          if (name === "dd") { ddSeen = null; skipId = null; } }
        else if (!selfClose) {
          const cls = (tok.match(/class="([^"]*)"/) || [, ""])[1];
          const clsSkip = /\b(cmd|pill)\b/.test(cls);   // terminal blocks + inline code chips
          stack.push({ name, skip: SKIP.has(name) || clsSkip });
          if (isGlossary && name === "dt") { const idm = tok.match(/id="([^"]+)"/); pendingDt = idm ? idm[1] : null; }
          if (isGlossary && name === "dd") { ddSeen = new Set(); skipId = pendingDt; }
        }
        // record existing glossary links so we do not double-link (idempotent)
        if (name === "a") {
          const hm = tok.match(/href="(?:glossary\.html)?#([^"]+)"/);
          if (hm) { (isGlossary ? (ddSeen || pageSeen) : pageSeen).add(hm[1]); }
        }
      }
      out += tok;
    } else {                                  // text
      if (!tok || skipActive()) { out += tok; continue; }
      if (isGlossary) {
        if (ddSeen) out += linkText(tok, ddSeen, hrefBase, skipId);   // only inside a dd
        else out += tok;
      } else {
        out += linkText(tok, pageSeen, hrefBase, null);
      }
    }
  }
  return out;
}

const DOCS = require("path").join(__dirname, "..", "docs");
const files = fs.readdirSync(DOCS).filter(f => f.endsWith(".html"));
let report = [];
for (const f of files) {
  const p = path.join(DOCS, f);
  const src = fs.readFileSync(p, "utf8");
  const isGloss = f === "glossary.html";
  const out = process(src, isGloss);
  const added = (out.match(/class="term"/g) || []).length - (src.match(/class="term"/g) || []).length;
  fs.writeFileSync(p, out);
  report.push(f + ": +" + added + " links");
}
console.log(report.join("\n"));
