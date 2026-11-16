// NearMind WhatsApp bridge. Links to the owner's WhatsApp as a linked device (pairing code).
// Safety rules (hard-coded):
//  - It NEVER starts a chat. It only sends to (a) the owner's own number, or (b) an allow-listed friend
//    who has already messaged first in a 1:1 chat. Groups and everyone else are ignored.
//  - A friend can send "stop" and is removed from the allow-list.
import makeWASocket, { useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion, Browsers } from '@whiskeysockets/baileys'
import pino from 'pino'
import http from 'node:http'
import fs from 'node:fs'

const PHONE = (process.env.WA_PHONE || '').replace(/\D/g, '')
if (!PHONE) { console.error('Set WA_PHONE (your WhatsApp number, country code, digits only) in .env'); process.exit(1) }
const OWN = `${PHONE}@s.whatsapp.net`
const APP = process.env.APP_URL || 'http://127.0.0.1:5215'
const PORT = Number(process.env.BRIDGE_PORT || 5216)
const ALLOW_FILE = './allow.json'
const logger = pino({ level: 'silent' })

let sock, state = 'starting', code = null, ownLid = null
const sent = new Map()          // text -> time, ignore our own echoes in the self-chat
const JID_FILE = './jids.json'
// friend/neighbor number -> the jid they wrote from (reply there). Persisted so an opt-in survives a bridge restart.
const jidOf = new Map((() => { try { return Object.entries(JSON.parse(fs.readFileSync(JID_FILE, 'utf8'))) } catch { return [] } })())
const rememberJid = (n, j) => { if (jidOf.get(n) === j) return; jidOf.set(n, j); try { fs.writeFileSync(JID_FILE, JSON.stringify(Object.fromEntries(jidOf))) } catch {} }
const queue = []                // {jid, text}
let pumping = false

const norm = j => (j || '').split('@')[0].split(':')[0]
const digits = s => String(s || '').replace(/\D/g, '')
const loadAllow = () => { try { return JSON.parse(fs.readFileSync(ALLOW_FILE, 'utf8')).numbers || [] } catch { return [] } }
const saveAllow = n => fs.writeFileSync(ALLOW_FILE, JSON.stringify({ numbers: [...new Set(n)] }))

async function pump() {
  if (pumping) return
  pumping = true
  while (queue.length) {
    const item = queue[0]
    if (state !== 'open') break
    queue.shift()
    try {
      // human pace: show "typing…" first, longer for longer messages
      const wait = Math.min(4500, 1200 + item.text.length * 22)
      try { await sock.sendPresenceUpdate('composing', item.jid) } catch {}
      await new Promise(r => setTimeout(r, wait))
      try { await sock.sendPresenceUpdate('paused', item.jid) } catch {}
      if (item.jid === OWN) sent.set(item.text, Date.now())
      await sock.sendMessage(item.jid, { text: item.text })
    } catch (e) { console.error('send failed', e?.message) }
    await new Promise(r => setTimeout(r, 1200))
  }
  pumping = false
}

function enqueue(jid, text) { queue.push({ jid, text: String(text).slice(0, 3500) }); pump() }

async function start() {
  const { state: auth, saveCreds } = await useMultiFileAuthState('./auth')
  const { version } = await fetchLatestBaileysVersion()
  sock = makeWASocket({ version, auth, logger, printQRInTerminal: false, browser: Browsers.windows('Chrome'), markOnlineOnConnect: false, syncFullHistory: false })
  sock.ev.on('creds.update', saveCreds)

  if (!sock.authState.creds.registered) {
    state = 'pairing'
    setTimeout(async () => {
      try { code = await sock.requestPairingCode(PHONE); console.log('PAIRING CODE', code) }
      catch (e) { console.error('pairing failed', e?.message); state = 'error' }
    }, 3000)
    // codes expire after a couple of minutes: reconnect for a fresh one if nobody used it
    setTimeout(() => { if (!sock.authState.creds.registered && state === 'pairing') { code = null; try { sock.ws.close() } catch {} } }, 100000)
  }

  sock.ev.on('connection.update', ({ connection, lastDisconnect }) => {
    if (connection === 'open') {
      state = 'open'; code = null
      ownLid = sock.user?.lid ? norm(sock.user.lid) : null
      console.log('WhatsApp connected as', sock.user?.id)
      pump()
    } else if (connection === 'close') {
      const status = lastDisconnect?.error?.output?.statusCode
      if (status === DisconnectReason.loggedOut) { state = 'logged_out'; console.log('logged out'); return }
      state = 'reconnecting'
      setTimeout(start, 2000)
    }
  })

  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return
    for (const m of messages) {
      const remote = m.key.remoteJid || ''
      if (remote.endsWith('@g.us') || remote === 'status@broadcast') continue   // never groups/status
      const text = m.message?.conversation || m.message?.extendedTextMessage?.text
      if (!text) continue
      const jid = norm(remote)
      const alt = norm(m.key.remoteJidAlt)
      let from = null
      if (m.key.fromMe) {
        // owner's own self-chat only
        const isSelf = jid === PHONE || (ownLid && jid === ownLid) || alt === PHONE
        if (!isSelf) continue
        if (text.startsWith('​')) continue
        if (sent.has(text) && Date.now() - sent.get(text) < 300000) continue
      } else {
        // an allow-listed friend writing to us first, 1:1
        const allow = loadAllow()
        from = allow.find(n => n === jid || n === alt)
        if (!from) continue
        rememberJid(from, remote)
        if (/^\s*(stop|quit|unsubscribe)\s*$/i.test(text)) {
          saveAllow(allow.filter(n => n !== from))
          jidOf.delete(from); try { fs.writeFileSync(JID_FILE, JSON.stringify(Object.fromEntries(jidOf))) } catch {}
          enqueue(OWN, '​⏹️ +' + from + ' sent "stop": NearMind won\'t message them again.')   // tell you; stay silent in their chat
          continue
        }
      }
      try {
        await fetch(`${APP}/api/wa/incoming`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ text, from }) })
      } catch (e) { console.error('app unreachable', e?.message) }
    }
  })
}

http.createServer((req, res) => {
  const json = (o, c = 200) => { res.writeHead(c, { 'content-type': 'application/json' }); res.end(JSON.stringify(o)) }
  const body = cb => { let b = ''; req.on('data', d => (b += d)); req.on('end', () => { try { cb(JSON.parse(b || '{}')) } catch { json({ ok: false }, 400) } }) }
  if (req.method === 'GET' && req.url === '/status') return json({ state, code, phone: PHONE })
  if (req.method === 'GET' && req.url === '/allow') return json({ numbers: loadAllow() })
  if (req.method === 'POST' && req.url === '/allow') return body(d => {
    let n = loadAllow()
    if (d.add) { const x = digits(d.add); if (x.length >= 8 && x !== PHONE) n.push(x) }
    if (d.remove) n = n.filter(x => x !== digits(d.remove))
    saveAllow(n); json({ numbers: loadAllow() })
  })
  if (req.method === 'POST' && req.url === '/send') return body(({ text, to }) => {
    if (!text) return json({ ok: false }, 400)
    if (!to) { enqueue(OWN, '​' + text); return json({ ok: true }) }
    const num = digits(to)
    if (!loadAllow().includes(num) || !jidOf.has(num)) return json({ ok: false, error: 'not allowed or has not messaged first' }, 403)
    enqueue(jidOf.get(num), text); json({ ok: true })
  })
  json({ error: 'not found' }, 404)
}).listen(PORT, '127.0.0.1', () => console.log('bridge http on', PORT))

start()
