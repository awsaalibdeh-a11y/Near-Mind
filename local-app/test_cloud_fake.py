"""NearMind Cloud-API path against a FAKE Meta endpoint: no real WhatsApp message is ever sent."""
import hashlib, hmac, json, os, sys, threading, time
from http.server import BaseHTTPRequestHandler, HTTPServer

SENT = []
class Fake(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        SENT.append((self.path, self.headers.get("Authorization"), body))
        self.send_response(200); self.send_header("content-type", "application/json"); self.end_headers()
        self.wfile.write(b'{"messages":[{"id":"wamid.X"}]}')
    def log_message(self, *a): pass
srv = HTTPServer(("127.0.0.1", 0), Fake); threading.Thread(target=srv.serve_forever, daemon=True).start()
os.environ.update(META_GRAPH_URL=f"http://127.0.0.1:{srv.server_port}/v22.0", META_TOKEN="test-token", META_PHONE_ID="123456",
                  META_APP_SECRET="shh", META_VERIFY="nearmind", OPENAI_API_KEY="x")
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))); import app as A

def post(c, payload, secret="shh"):
    raw = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return c.post("/api/wa/cloud", data=raw, headers={"X-Hub-Signature-256": sig, "content-type": "application/json"})

c = A.app.test_client()
# 1 verification handshake
r = c.get("/api/wa/cloud?hub.mode=subscribe&hub.verify_token=nearmind&hub.challenge=42"); assert r.data == b"42", r.data
assert c.get("/api/wa/cloud?hub.mode=subscribe&hub.verify_token=bad&hub.challenge=42").status_code == 403
# 2 signature enforced
assert post(c, {}, secret="wrong").status_code == 403
# 3 same, in PUBLIC mode the webhook must stay reachable (the bug fixed earlier)
A.PUBLIC = True
assert c.get("/api/wa/cloud?hub.mode=subscribe&hub.verify_token=nearmind&hub.challenge=7").data == b"7"
assert c.get("/api/wa/status").status_code == 404
A.PUBLIC = False
# 4 inbound text -> welcome message goes out through the Graph endpoint with the test number's phone id + bearer token
A.run_turn = lambda *a, **k: iter(())          # skip the LLM: only the wiring is under test
msg = {"entry": [{"changes": [{"value": {"messages": [{"from": "15551234567", "type": "text", "text": {"body": "anyone have salt?"}}]}}]}]}
assert post(c, msg).status_code == 200
for _ in range(60):
    if SENT: break
    time.sleep(0.2)
path, auth, body = SENT[0]
assert path == "/v22.0/123456/messages", path
assert auth == "Bearer test-token"
assert body["messaging_product"] == "whatsapp" and body["to"] == "15551234567" and body["type"] == "text"
assert "NearMind" in body["text"]["body"]
# 5 STOP ends the session
post(c, {"entry": [{"changes": [{"value": {"messages": [{"from": "15551234567", "type": "text", "text": {"body": "stop"}}]}}]}]})
assert "cloud:15551234567" not in A.SESS
print("OK: cloud webhook + send wiring verified against fake Meta;", len(SENT), "fake sends")
