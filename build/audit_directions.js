// Audit generated walking directions by reading the TEXT back (not the internals) and checking it for contradictions.
const fs = require("fs");
const html = fs.readFileSync(process.argv[2], "utf8");
const N = Number(process.argv[3] || 300);
const grab = id => html.match(new RegExp('<script type="application/json" id="' + id + '">([\\s\\S]*?)</script>'))[1];
const i0 = html.lastIndexOf("<script>"), j0 = html.lastIndexOf("</script>");
const js = html.slice(i0 + 8, j0).replace("  // ---------- Router ----------", "globalThis.__t={planOptions,describeRoute,buildings,routable};\n  // ---------- Router ----------");
const fake = new Proxy(function () {}, { get: (t, k) => (k === Symbol.toPrimitive ? () => "" : fake), apply: () => fake, set: () => true });
const DATA = { "map-data": grab("map-data"), "path-data": grab("path-data"), "door-data": grab("door-data") };
globalThis.document = new Proxy({}, { get: (t, k) => k === "getElementById" ? id => (DATA[id] ? { textContent: DATA[id] } : fake) : fake });
globalThis.window = fake; globalThis.location = { hash: "" }; globalThis.localStorage = { getItem: () => null, setItem() {} }; globalThis.setTimeout = () => 0;
try { eval(js); } catch (e) { if (!globalThis.__t) throw e; }
const T = globalThis.__t;

const DIRS = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"];
const DIR_RE = "(northeast|northwest|southeast|southwest|north|south|east|west)";
const idx = w => DIRS.indexOf(w);
const turnK = (a, b) => { const k = ((b - a) % 8 + 8) % 8; return k > 4 ? k - 8 : k; };
const expectWord = k => k === 0 ? "continue straight" : Math.abs(k) === 4 ? "turn around" : (Math.abs(k) === 1 ? "bear " : Math.abs(k) === 2 ? "turn " : "make a sharp ") + (k > 0 ? "right" : "left");
const strip = t => t.replace(/^Near .*?, (?=(turn|bear|continue|make|take|cross)\b)/, "").replace(/^Walk about .*? from the door to the walkway, then /, "");
// Announced heading of a step in "both" style text.
function heading(t) {
  const m = t.match(new RegExp("(?:heading|head|walk|Walk|continue straight, heading) " + DIR_RE)) || t.match(new RegExp("heading " + DIR_RE));
  return m ? m[1] : null;
}
const endHeading = t => { const m = t.match(new RegExp("ends heading " + DIR_RE)); return m ? m[1] : null; };
const relWord = t => { const m = strip(t).match(/^(Continue straight|continue straight|Bear (left|right)|bear (left|right)|Turn around|turn around|Turn (left|right)|turn (left|right)|Make a sharp (left|right)|make a sharp (left|right))/); return m ? m[1].toLowerCase() : null; };

// Deterministic sample of building pairs.
let seed = 12345; const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
const B = T.buildings.filter(T.routable);
const pairs = [];
while (pairs.length < N) { const a = B[Math.floor(rnd() * B.length)], b = B[Math.floor(rnd() * B.length)]; if (a !== b) pairs.push([a, b]); }

const issues = { dupText: [], dupLeg: [], turnMismatch: [], noHeading: [], parallelCross: [], compassStyleTurn: [] };
let routes = 0, stepsTotal = 0;
for (const [A, Bd] of pairs) {
  const opts = T.planOptions(A, Bd, false);
  for (const o of opts) {
    routes++;
    const both = T.describeRoute(A, Bd, o.path, "both", "all");
    const comp = T.describeRoute(A, Bd, o.path, "compass", "all");
    const rel = T.describeRoute(A, Bd, o.path, "relative", "all");
    const walkSteps = both.steps.slice(0, -1);  // last is arrival
    stepsTotal += walkSteps.length;
    const tag = `${A.n} -> ${Bd.n} [${o.prof.name}]`;
    // 1. Identical consecutive step text (any style)
    for (const r of [both, comp, rel]) for (let k = 1; k < r.steps.length; k++) if (r.steps[k].text === r.steps[k - 1].text) issues.dupText.push(`${tag} step ${k + 1}: ${r.steps[k].text}`);
    // 2. Consecutive legs on the same path with no turn (should have been merged)
    for (let k = 1; k < both.meta.length; k++) {
      const a = both.meta[k - 1], b = both.meta[k];
      if ((a.kind === 0 || a.kind === 1) && a.kind === b.kind && a.label === b.label && b.turn === 0) issues.dupLeg.push(`${tag} steps ${k}-${k + 1}: ${walkSteps[k - 1].text} | ${walkSteps[k].text}`);
    }
    // 3. Turn words must match the change between the previously announced heading and the new one (read from text)
    let prevEnd = null;
    walkSteps.forEach((st, k) => {
      const h = heading(st.text), e = endHeading(st.text);
      if (!h) { issues.noHeading.push(`${tag} step ${k + 1}: ${st.text}`); prevEnd = null; return; }
      if (k > 0 && prevEnd) {
        const want = expectWord(turnK(idx(prevEnd), idx(h)));
        const got = relWord(st.text);
        const okNoWord = !got && want === "continue straight";  // stairs/crossings drop "continue straight"
        if (!okNoWord && got !== want) issues.turnMismatch.push(`${tag} step ${k}->${k + 1}: previous heading ${prevEnd}, now ${h}; expected "${want}", got "${got}"\n      ${walkSteps[k - 1].text}\n      ${st.text}`);
      }
      prevEnd = e || h;
    });
    // 4. Compass-only text must never contain left/right
    comp.steps.concat(comp.orient.map(t => ({ text: t, details: [] }))).forEach(st => {
      [st.text, ...(st.details || [])].forEach(t => { if (/ looks like: /.test(t)) return; if (/\b(left|right)\b/.test(t)) issues.compassStyleTurn.push(`${tag}: ${t}`); });
    });
    // 5. "crosses your path, running Xâ€“Y" where Xâ€“Y is the direction you are walking
    comp.steps.slice(0, -1).forEach((st, k) => {
      const h = (st.text.match(new RegExp("(?:heading|head|[Ww]alk|continue) " + DIR_RE)) || [])[1];
      if (!h) return;
      (st.details || []).forEach(d => {
        const re = /crosses your path, running (\w+)â€“(\w+)/g; let m;
        while ((m = re.exec(d))) if (m[1] === h || m[2] === h) issues.parallelCross.push(`${tag} step ${k + 1} (heading ${h}): ${d}`);
      });
    });
  }
}
console.log(`Audited ${routes} routes (${pairs.length} building pairs, all route types), ${stepsTotal} walking steps, 3 styles each.\n`);
for (const [k, v] of Object.entries(issues)) {
  console.log(`${k}: ${v.length}`);
  v.slice(0, 4).forEach(x => console.log("   " + x));
}
// Show every Libby Drive crossing in context, the case reported by the user.
let shown = 0;
for (const [A, Bd] of pairs) {
  if (shown >= 2) break;
  const o = T.planOptions(A, Bd, false)[0]; if (!o) continue;
  const r = T.describeRoute(A, Bd, o.path, "both", "none");
  const k = r.steps.findIndex(s => /cross Libby Drive/i.test(s.text));
  if (k < 0) continue;
  shown++;
  console.log(`\nLibby Drive crossing, ${A.n} -> ${Bd.n}:`);
  r.steps.slice(Math.max(0, k - 1), k + 2).forEach((s, q) => console.log(`   Step ${Math.max(0, k - 1) + q + 1}: ${s.text}`));
}

