// Audit a rendered site for the 9 required sections + premium markers.
// usage: node cdp_audit.mjs <fileUrl> [waitMs]
const [, , fileUrl, waitRaw] = process.argv;
const wait = parseInt(waitRaw || "9000", 10);
const base = "http://127.0.0.1:9222";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const v = await (await fetch(base + "/json/version")).json();
const ws = new WebSocket(v.webSocketDebuggerUrl);
let id = 0; const pend = new Map();
const send = (m, p = {}, s) => new Promise((r) => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method: m, params: p, sessionId: s })); });
await new Promise((r) => (ws.onopen = r));
ws.onmessage = (e) => { const d = JSON.parse(e.data); if (d.id && pend.has(d.id)) { pend.get(d.id)(d.result); pend.delete(d.id); } };
const { targetId } = await send("Target.createTarget", { url: "about:blank" });
const { sessionId } = await send("Target.attachToTarget", { targetId, flatten: true });
await send("Page.enable", {}, sessionId);
await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false }, sessionId);
await send("Page.navigate", { url: fileUrl }, sessionId);
await sleep(wait);
// scroll so lazy/reveal content mounts
for (let y = 0; y < 8000; y += 800) { await send("Runtime.evaluate", { expression: "scrollTo(0," + y + ")" }, sessionId); await sleep(120); }
await send("Runtime.evaluate", { expression: "scrollTo(0,0)" }, sessionId); await sleep(400);
const js = `(function(){
  var hero=document.getElementById('top')||{};
  var heroBtns=hero.querySelectorAll?Array.from(hero.querySelectorAll('a,button')):[];
  var form=document.querySelector('#apply form');
  var has=function(id){return !!document.getElementById(id)};
  var txt=(document.body.innerText||'');
  return JSON.stringify({
    studio:(window.__DATA__&&window.__DATA__.studio.label)||'?',
    sections:{
      hero:has('top'), stats:has('stats'), services:has('services'), about:has('why'),
      process:has('process'), showcase:has('showcase'), testimonials:has('reviews'),
      ctaForm:!!form, footer:!!document.querySelector('footer')
    },
    hero:{
      headline:!!(hero.querySelector&&hero.querySelector('h1')),
      primaryCTA:!!heroBtns.find(function(e){return /apply|start/i.test(e.textContent)}),
      secondaryCTA:heroBtns.length>=2,
      visual:!!(hero.querySelector&&hero.querySelector('img')),
      trust:/obligation|trusted|refer|no credit|drivers/i.test(hero.innerText||'')
    },
    form:{fields: form?form.querySelectorAll('input,select').length:0, submit: form?!!form.querySelector('[type=submit]'):false},
    premium:{
      sections:document.querySelectorAll('section').length,
      images:document.images.length,
      marquee:!!document.querySelector('.marquee'),
      gradedImg:!!document.querySelector('.gimg'),
      footerWordmark:/.{0,3}/.test(txt)&&!!document.querySelector('footer'),
      animatedEls:document.querySelectorAll('[style*=transform],[style*=opacity]').length
    }
  });
})()`;
const r = await send("Runtime.evaluate", { expression: js, returnByValue: true }, sessionId);
console.log(r.result.value);
await send("Target.closeTarget", { targetId }); ws.close(); process.exit(0);
