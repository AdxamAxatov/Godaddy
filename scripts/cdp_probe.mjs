// Probe geometry of hero headline vs nav. usage: node cdp_probe.mjs <fileUrl> [waitMs]
const [, , fileUrl, waitRaw] = process.argv;
const wait = parseInt(waitRaw || "9000", 10);
const base = "http://127.0.0.1:9222";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const v = await (await fetch(base + "/json/version")).json();
const ws = new WebSocket(v.webSocketDebuggerUrl);
let id = 0; const pending = new Map();
const send = (m, p = {}, s) => new Promise((r) => { const _i = ++id; pending.set(_i, r); ws.send(JSON.stringify({ id: _i, method: m, params: p, sessionId: s })); });
await new Promise((r) => (ws.onopen = r));
ws.onmessage = (e) => { const d = JSON.parse(e.data); if (d.id && pending.has(d.id)) { pending.get(d.id)(d.result); pending.delete(d.id); } };
const { targetId } = await send("Target.createTarget", { url: "about:blank" });
const { sessionId } = await send("Target.attachToTarget", { targetId, flatten: true });
await send("Page.enable", {}, sessionId);
await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false }, sessionId);
await send("Page.navigate", { url: fileUrl }, sessionId);
await sleep(wait);
const js = `(function(){
  function box(el){ if(!el) return null; var r=el.getBoundingClientRect(); var s=getComputedStyle(el);
    return {top:Math.round(r.top),bottom:Math.round(r.bottom),h:Math.round(r.height),vis:s.visibility,op:s.opacity,disp:s.display,txt:(el.innerText||'').slice(0,40)}; }
  var h1=document.querySelector('#top h1, #top [class*=font-heading]');
  var nav=document.querySelector('header nav, header');
  var script=document.querySelector('.font-script');
  return JSON.stringify({nav:box(nav), h1:box(h1), script:box(script)});
})()`;
const res = await send("Runtime.evaluate", { expression: js, returnByValue: true }, sessionId);
console.log(res.result.value);
await send("Target.closeTarget", { targetId }); ws.close(); process.exit(0);
