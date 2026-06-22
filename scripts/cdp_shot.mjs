// CDP screenshot helper — drives the already-running Chrome (port 9222).
// Scrolls through the page first so Framer-Motion whileInView reveals fire.
// usage: node cdp_shot.mjs <fileUrl> <outPng> [waitMs]
import fs from "fs";

const [, , fileUrl, out, waitMsRaw] = process.argv;
const waitMs = parseInt(waitMsRaw || "9000", 10);
const base = "http://127.0.0.1:9222";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const v = await (await fetch(base + "/json/version")).json();
const ws = new WebSocket(v.webSocketDebuggerUrl);
let id = 0;
const pending = new Map();
const errors = [];
const send = (method, params = {}, sessionId) =>
  new Promise((res) => { const _id = ++id; pending.set(_id, res); ws.send(JSON.stringify({ id: _id, method, params, sessionId })); });

await new Promise((r) => (ws.onopen = r));
ws.onmessage = (m) => {
  const d = JSON.parse(m.data);
  if (d.id && pending.has(d.id)) { pending.get(d.id)(d.result); pending.delete(d.id); return; }
  if (d.method === "Runtime.exceptionThrown") errors.push("EXC: " + (d.params.exceptionDetails.exception?.description || d.params.exceptionDetails.text));
  if (d.method === "Runtime.consoleAPICalled" && d.params.type === "error") errors.push("CONSOLE: " + d.params.args.map((a) => a.value || a.description || "").join(" "));
};

const { targetId } = await send("Target.createTarget", { url: "about:blank" });
const { sessionId } = await send("Target.attachToTarget", { targetId, flatten: true });
await send("Page.enable", {}, sessionId);
await send("Runtime.enable", {}, sessionId);
await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false }, sessionId);
await send("Page.navigate", { url: fileUrl }, sessionId);
await sleep(waitMs);

// scroll through to trigger whileInView reveals
const evalJS = (expression) => send("Runtime.evaluate", { expression, returnByValue: true }, sessionId);
const { result: hres } = await evalJS("document.body.scrollHeight");
const total = hres.value || 2000;
for (let y = 0; y < total; y += 700) { await evalJS("window.scrollTo(0," + y + ")"); await sleep(180); }
await evalJS("window.scrollTo(0,0)");
await sleep(900);

const probe = await evalJS("JSON.stringify({root:(document.getElementById('root')||{}).childElementCount||0,h:document.body.scrollHeight})");
console.log("PROBE:", probe.result?.value);

const { contentSize } = await send("Page.getLayoutMetrics", {}, sessionId);
const height = Math.min(Math.ceil(contentSize.height), 16000);
const isJpg = out.endsWith(".jpg") || out.endsWith(".jpeg");
const shot = await send("Page.captureScreenshot",
  { format: isJpg ? "jpeg" : "png", quality: isJpg ? 82 : undefined, captureBeyondViewport: true,
    clip: { x: 0, y: 0, width: 1440, height, scale: 1 } }, sessionId);
fs.writeFileSync(out, Buffer.from(shot.data, "base64"));
console.log("WROTE:", out, Math.round(fs.statSync(out).size / 1024) + "KB", "h=" + height);
console.log(errors.length ? "ERRORS:\n" + errors.slice(0, 6).join("\n") : "no console errors");
await send("Target.closeTarget", { targetId });
ws.close();
process.exit(0);
