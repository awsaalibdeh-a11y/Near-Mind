// NearMind's permanent address: nearmind.<account>.workers.dev forwards every request to the tunnel on the home computer.
// The tunnel's address changes when the computer restarts; start-public.bat redeploys this Worker with the new TARGET,
// so the workers.dev link never changes. Nothing is stored here: no API keys, no visitor data.

const OFFLINE = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NearMind is resting</title><style>
:root{--bg:#eef5f8;--card:#fff;--tx:#13232b;--dim:#5b6f78;--acc:#17c394}
@media (prefers-color-scheme:dark){:root{--bg:#0b1218;--card:#121c24;--tx:#e6eef2;--dim:#8ea3ae}}
body{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--bg);color:var(--tx);font:16px/1.5 system-ui,sans-serif;padding:16px;box-sizing:border-box}
.c{background:var(--card);border-radius:20px;padding:28px 24px;max-width:440px;text-align:center;box-shadow:0 10px 30px rgba(0,0,0,.08)}
h1{margin:8px 0 6px;font-size:24px}p{margin:0;color:var(--dim)}.r{font-size:56px}</style></head>
<body><div class="c"><div class="r">🤖💤</div><h1>NearMind is resting</h1>
<p>The NearMind server is offline for a moment. Please try again in a few minutes.</p></div></body></html>`;

export default {
  async fetch(request, env) {
    const target = (env.TARGET || "").replace(/\/+$/, "");
    if (!target) return new Response(OFFLINE, { status: 503, headers: { "content-type": "text/html; charset=utf-8" } });
    const url = new URL(request.url);
    const upstream = target + url.pathname + url.search;
    const headers = new Headers(request.headers);
    headers.delete("host");
    // tell the server who the real visitor is, so its per-visitor limits still work behind this proxy
    headers.set("X-NM-Client-IP", request.headers.get("CF-Connecting-IP") || "");
    if (env.PROXY_SECRET) headers.set("X-NM-Proxy-Secret", env.PROXY_SECRET);
    try {
      const resp = await fetch(upstream, {
        method: request.method,
        headers,
        body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
        redirect: "manual",
      });
      if (resp.status === 502 || resp.status === 530) throw new Error("tunnel down");
      const out = new Headers(resp.headers);
      out.set("X-NearMind-Via", "workers.dev");
      return new Response(resp.body, { status: resp.status, statusText: resp.statusText, headers: out });   // streams through
    } catch (e) {
      return new Response(OFFLINE, { status: 503, headers: { "content-type": "text/html; charset=utf-8", "retry-after": "60" } });
    }
  },
};
