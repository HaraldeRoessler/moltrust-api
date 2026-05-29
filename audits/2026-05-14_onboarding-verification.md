# Onboarding Verification — Phase 1 Read-Only Audit

**Datum:** 2026-05-14
**Scope:** V-1..V-9, ausschließlich Inspektion (kein Code-Change, kein Commit, kein Service-Restart)
**Quellen:** live API (`api.moltrust.ch`), live `uresolver.moltrust.ch`, npm registry, server-lokale Sources unter `~/moltstack/app/`, `psql` SELECT auf `moltstack` DB, journal `moltstack.service`.

---

## V-8 — OpenAPI-Spec (ANSWERED)

**Status:** ANSWERED.

**Antwort.** Die OpenAPI-Spec ist live exponiert.

- `GET https://api.moltrust.ch/openapi.json` → HTTP 200, 88 312 bytes, `application/json`.
- `openapi: 3.1.0`, `info.title = "MolTrust API"`, `info.version = "2.4"`, **136 Pfade**.
- `GET /docs` → HTTP 200, `text/html` (Swagger UI).
- `GET /redoc` → HTTP 200, `text/html`.

**Hinweis zum Wording im Briefing.** Es existiert **kein** `/agents/register`. Der reale Pfad heißt `POST /identity/register`. Alle weiteren V-Items, die `/agents/register` referenzieren, wurden gegen den realen Pfad geprüft.

---

## V-2 — Register-Response (ANSWERED, ohne Test-Registrierung)

**Status:** ANSWERED. Schema im OpenAPI ist leer (`schema: {}`), darum direkt aus dem Quellcode beantwortet — keine Test-Registrierung nötig.

**Antwort.** `POST /identity/register` liefert **ein vollständiges, freistehendes Verifiable Credential plus Meta-Daten**, **kein** AAE-tragendes VC.

Response-Body (aus `~/moltstack/app/main.py:840-901`):

```jsonc
{
  "did": "did:moltrust:<16hex>",
  "display_name": "...",
  "status": "registered",
  "badge": "✓ Verified by MolTrust | did:moltrust:... | Register: https://api.moltrust.ch/join?ref=...",
  "credential": {  // FULL VC, signiert; type=AgentTrustCredential
    "issuer": "...",
    "issuanceDate": "...",
    "expirationDate": "...",
    "credentialSubject": {
      "trustProvider": "MolTrust",
      "reputation": { "score": 0.0, "total_ratings": 0 },
      "verified": true
    },
    "proof": { "proofValue": "..." }
  },
  "credits": { "balance": 175, "currency": "CREDITS" },
  "base_anchor": {
    "tx_hash": "...",
    "chain": "base",
    "explorer": "https://basescan.org/tx/..."
  },
  "headers": {
    "X-MolTrust-DID": "did:moltrust:...",
    "X-MolTrust-Verify": "https://api.moltrust.ch/join?ref=..."
  },
  "erc8004": { ... }   // nur wenn body.erc8004 == true
}
```

**Wichtige Details:**
- Das eingebettete VC ist ein `AgentTrustCredential` mit **Initial-Reputation 0.0** — der "echte" Phase-2-Trust-Score wird erst durch Endorsements / IPR / Cross-Vertical aktiviert (vgl. V-3).
- AAE-Envelopes werden hier **nicht** ausgegeben; AAE ist in `agent-card.json` als separate Extension `moltrust.ch/extensions/aae/v1` deklariert und läuft über `POST /delegation/configure`.
- Sub-Pfad `/identity/register-batch` existiert zusätzlich (admin-only, ADMIN_KEY-gated).

**Evidenz.**
```
sed -n "815..901" ~/moltstack/app/main.py
    @app.post("/identity/register")
    @limiter.limit("10/minute")
    async def register_agent(request, body: RegisterRequest, api_key = Depends(verify_api_key)):
      ...
      auto_vc = issue_credential(agent_did, "AgentTrustCredential", {...})
      ...
      response = { "did": ..., "credential": auto_vc, "credits": ..., "base_anchor": ..., ... }
      return response
```

---

## V-1 — SDK-Methoden (ANSWERED)

**Status:** ANSWERED.

**Antwort.**
- `@moltrust/sdk` ist auf npm in **Version 1.1.0** publiziert.
- Es exportiert `AgentTrust.register(params: RegisterOptions): Promise<unknown>`.
- Es exportiert **keine** `selfOnboard()`-Methode.

**Evidenz.**
```
$ npm view @moltrust/sdk version   → 1.1.0
$ grep -nE "register|selfOnboard" dist/*.d.ts
dist/agent-trust.d.ts:54:  static register(params: RegisterOptions): Promise<unknown>;
dist/types.d.ts:40:  /** Options for AgentTrust.register() */
```

- `dist/agent-trust.d.ts` enthält den vollständigen Doc-Comment für `register(...)` (Line 49–54), inklusive Beispiel `const agent = await AgentTrust.register({...})`.
- README dokumentiert **nur** `AgentTrust.verify(...)` — `register()` ist programmatic-only und nicht im README beworben (asymmetrischer Public-API-Hint Richtung Verifier-Use-Case).
- Der Return-Type ist `Promise<unknown>` — d. h. clientseitig **keine** TypeScript-Garantie über die Response-Struktur; das tatsächliche Schape entspricht V-2.

---

## V-3 — Score-Progression (ANSWERED)

**Status:** ANSWERED.

### Was den Score verändert (aus `~/moltstack/app/swarm/trust_score.py`)

Phase-2-Formel (Kommentar im Code, Zeilen 1–13):

```
score = α·direct + β·propagated + γ·cross_vertical
        + interaction_bonus + prediction_bonus + wallet_bonus + agent_class_modifier
        - sybil_penalty·20 + inactivity_penalty
```

Mit `ALPHA=0.6`, `BETA=0.3`, `GAMMA=0.1`. Clamp `[0, 100]`. Bei Seeds: `max(base_score, final_score)`. Bei <3 Endorsern und kein Seed: `score=None` → `withheld=true`.

| Aktion | Größenordnung | Quelle |
| --- | --- | --- |
| **Endorsement erhalten** (gewichtet, 90 d Half-Life-Decay) | `direct_score` 0–100, geht zu **60 %** in den Score | `compute_phase2_score` Step 1, Konstante `DECAY_HALF_LIFE_DAYS=90` |
| **Cross-Vertical-Diversität** | `min(unique_verticals × 10, 30)`, × **10 %** Gewichtung → max +3 | Step 3 |
| **Propagierter Score** der Endorser | rekursiv (max depth 3), × **30 %** Gewichtung | Step 2 |
| **IPR / Interaction-Proof-Records** | Neu: `compute_ipr_bonus(...)`. Legacy: `min(count × 2, 10)` → max **+10** | Step 4 |
| **Prediction-Accuracy** (≥3 settled) | accuracy ≥60 % → **+2..+10**, <40 % → **−2..−10** | `compute_prediction_accuracy_bonus` |
| **Wallet-Attestation** (≤30 min alt) | **0..+20** direkt aus `wallet_attestations.wallet_score` | `compute_wallet_attestation_bonus` |
| **Agent-Class-Modifier** (ZeroID Feature 1) | orchestrator **+5**, autonomous 0, human_initiated 0, copilot **−10** | `AGENT_CLASS_MODIFIER` |
| **Sybil-Penalty** | `sybil_penalty × 20` Abzug (Jaccard-Cluster, Vertical-Diversity-Penalty) | `compute_sybil_penalty` aus `anti_collusion.py` |
| **Inactivity-Penalty** (RSAC Gap 3) | additiv negativ (Code-Vorzeichen: addiert; Funktion liefert ≤0) | `app.anomaly.get_inactivity_penalty` |
| **Revocation** | hart auf `trust_score=0`, `grade="REVOKED"` | `main.py:1187+` Revocation-Check vor compute |
| **Seed-Floor** | `final = max(seed.base_score, final)` — Seeds fallen nie unter `base_score` | Line ~395, Kommentar "Deployed 2026-03-22" |

### Live-Verteilung in der DB

`psql -U moltstack -d moltstack`:

```
SELECT count(*) AS total_agents,
       (SELECT count(*) FROM trust_score_cache) AS cached,
       (SELECT count(*) FROM swarm_seeds) AS seeds,
       (SELECT count(*) FROM endorsements) AS endorsements
FROM agents;
 total_agents | cached | seeds | endorsements
--------------+--------+-------+--------------
           68 |     86 |     5 |           61

-- Bucketed
   bucket   | count | min  | max  | avg
------------+-------+------+------+------
 A (80-94)  |     2 | 80.0 | 85.0 | 82.5
 B (60-79)  |     3 | 60.0 | 75.0 | 68.3
 F (<20)    |    81 | -1.0 |  0.0 | -1.0
```

**Interpretation der Verteilung (für minScore-Leiter 0/50/60/80):**
- Es gibt heute **5 Agents mit nutzbarem Score ≥60** — und das sind exakt die 5 Seeds.
- Alle anderen cache-Einträge sitzen bei `-1.0` (Sentinel für `withheld`) bzw. `0.0`. Schema hat keine `grade`-Spalte; grade wird auf Read berechnet.
- **Plausibilität minScore-Ladder:**
  - `minScore=0` (default / open) ist die einzige Stufe, auf der aktuell >5 Agents durchkommen.
  - `minScore=50/60/80` würde im heutigen State 95 %+ aller registrierten Agents (außer Seeds) blocken — also nur als **Future-Gate** sinnvoll, wenn die Endorsement-Dichte wächst (>3 Endorser/Agent).
  - Die Brücke baut Phase 2 selbst: ohne ≥3 Endorser ist `score=null/withheld`, nicht 0 — d. h. ein verify-Gate auf `score >= X` rejected korrekt, würde aber 90 % der heutigen Population als „nicht verifizierbar" markieren.

---

## V-4 — uresolver Live (ANSWERED)

**Status:** ANSWERED.

**Antwort.** `uresolver.moltrust.ch` ist live und liefert ein valides DID-Document im Universal-Resolver-Format (`didDocument` + `didResolutionMetadata` + `didDocumentMetadata`).

```
$ curl https://uresolver.moltrust.ch/1.0/identifiers/did:moltrust:d34ed796a4dc4698
HTTP/2 200, Content-Type: application/json; charset=utf-8, 1306 bytes

{
  "didDocument": {
    "@context": ["https://www.w3.org/ns/did/v1", "https://w3id.org/security/suites/ed25519-2020/v1"],
    "id": "did:moltrust:d34ed796a4dc4698",
    "controller": "did:web:api.moltrust.ch",
    "verificationMethod": [{
      "id": "did:moltrust:d34ed796a4dc4698#key-1",
      "type": "Ed25519VerificationKey2020",
      "controller": "did:moltrust:d34ed796a4dc4698",
      "publicKeyHex": "7559b2..."
    }],
    "authentication": ["did:moltrust:d34ed796a4dc4698#key-1"],
    "assertionMethod": ["did:moltrust:d34ed796a4dc4698#key-1"],
    "service": [{
      "id": "...#payment",
      "type": "PaymentService",
      "serviceEndpoint": { "address": "0x3802...", "chain": "base", "currency": "USDC", "bound_at": "..." }
    }]
  },
  "didResolutionMetadata": { "contentType": "application/did+ld+json" },
  "didDocumentMetadata": { "created": "2026-03-16...", "keyAnchor": { "chain": "base", "tx": "0xde57...", "block": 43992036 } }
}
```

Auch der `keyAnchor` (Base L2 Tx-Hash) ist im DID-Document-Metadata präsent — Cross-Verify gegen on-chain möglich.

---

## V-5 — Badge-Endpoint (ANSWERED)

**Status:** ANSWERED.

**Antwort.** `GET /badge/{did}` ist live, liefert ein SVG mit korrektem MIME-Type.

```
$ curl -w "%{http_code} %{content_type} %{size_download}\n" \
       https://api.moltrust.ch/badge/did:moltrust:d34ed796a4dc4698
HTTP 200, image/svg+xml, 1174 bytes

<svg ... role="img" aria-label="MolTrust: 85 / A">
  <title>MolTrust Trust Score: 85 / A</title>
  ...
</svg>
```

Anzeige der DID rendert Score **85 / A** (matched mit Live-`/skill/trust-score/...` Antwort, vgl. V-7). Direkter Embed via `<img src="">` oder Shields-style Badges funktioniert (`@moltrust/openclaw` README nutzt das bereits in der eigenen `[![MolTrust Verified](...)]`-Zeile).

---

## V-6 — OpenClaw First-Boot (ANSWERED)

**Status:** ANSWERED.

**Antwort.** **Nein.** `@moltrust/openclaw` v1.0.1 onboardet sich beim Start **NICHT** selbst. Es ruft `/identity/register` nirgends auf.

Aus `dist/index.js` der Service-`start`-Handler:

```js
api.registerService({
  id: "moltrust-monitor",
  start: async () => {
    // Self-verify own DID on startup if configured
    if (cfg.verifyOnStart && cfg.agentDid) {
      const result = await client.verifyDid(cfg.agentDid);   // <-- VERIFY, nicht REGISTER
      ...
    }
    // Periodic health ping every 6 hours
    monitorInterval = setInterval(async () => { await client.ping(); }, 6*60*60*1000);
  },
  stop: () => { ... },
});
```

Der `MolTrustClient` exponiert nur:
- `verifyDid(did)` → `GET /identity/verify/{did}`
- `getTrustScore(did)` → `GET /skill/trust-score/{did}`
- `getWalletScoreFree(addr)` → `GET /guard/api/agent/score-free/{addr}`
- `ping()` → `GET /health`

**Es gibt keinen `register(...)` Aufruf im Plugin-Code.** Onboarding setzt voraus, dass `agentDid` und `apiKey` schon vom User in der `configSchema` eingetragen wurden (`openclaw.plugin.json` definiert beide als Plain Config-Properties).

**Die Aussage auf der Resources-Karte ist also korrekt** — die Fähigkeit „self-onboard on first boot" existiert in v1.0.1 **nicht**. Ein zukünftiger Sprint müsste:
1. `MolTrustClient` um `registerAgent(...)` ergänzen (gegen `POST /identity/register`),
2. Im `start`-Handler einen Branch `if (cfg.autoRegister && !cfg.agentDid) → register → persist did + credential` einbauen,
3. Plugin-Config-Schema um `autoRegister: boolean` + persistent-Storage-Hook erweitern.

---

## V-7 — CAEP-Subscription (ANSWERED)

**Status:** ANSWERED in allen drei Teilen (a/b/c).

### (a) `@moltrust/agent-firewall` v1.0.0 — `PROFILE.md` + Code

- **Status laut PROFILE.md:** "v1 — proprietary, polling-only, not OpenID SET". Explizit **kein** OpenID-SSF/RFC-8417 SET. Authentizität auf Event-Ebene ruht auf TLS; nur `trust_score_change` wird Ende-zu-Ende kryptographisch validiert (signierter Score-Pull).
- **Endpoints (alle gegen `https://api.moltrust.ch`):**
  - `GET /caep/pending/{did}?since={evt_id}&limit={n}` — cursor-based, default 100, max 500, **120 polls/h pro DID**, 30 s Mindest-Intervall (server-cap).
  - `POST /caep/acknowledge/{event_id}` — soft-ack, 90 d Retention, idempotent.
  - `GET /.well-known/registry-key.json` — Ed25519 JWK, `Cache-Control: max-age=3600`.
  - `GET /skill/trust-score/{did}` — signierte 5-Feld-Payload (`did`, `trust_score`, `computed_at`, `valid_until`, `policy_version`), JCS + Ed25519, kid `moltrust-registry-2026-v1`.
- **Event-Format:** `{ event_id, subject_did, event_type, emitted_at, payload }`. Event-Typen: `trust_score_change` (LIVE, ≥10 Punkte Swing), `did_revoked` / `flag_added` / `flag_removed` (reserved für Phase 0.5).
- **Retry / Backoff (aus `dist/caep/polling-source.d.ts`):**
  - Default `intervalMs = 30 000` (= 120/h, exakt am Limit).
  - `maxBackoffMs` per-DID exponential, jittered.
  - `requestTimeoutMs = 10 000` default.
  - Auf 429: Lib respektiert `Retry-After`-Header.
  - Acks werden alle 5 s in Batches mit `ackConcurrency=10` geflusht; auf 4xx (≠429) wird der Ack als permanent-failed gedroppt, max 5 Retries.
  - `MoltrustCaepClient.dropUnsignedEvents` default **true** → unsignierte Event-Typen feuern keine typed handlers, nur `'event'`-Stream.

### (b) Live-Erreichbarkeit der CAEP-Endpoints

```
$ curl -w "%{http_code} %{content_type} %{size}\n" \
       "https://api.moltrust.ch/caep/pending/did:moltrust:d34ed796a4dc4698?limit=2"
HTTP 200, application/json, 78 bytes
{"did":"did:moltrust:d34ed796a4dc4698","events":[],"count":0,"has_more":false}

$ curl https://api.moltrust.ch/.well-known/registry-key.json
HTTP 200, application/json, 139 bytes
{"kid":"moltrust-registry-2026-v1","kty":"OKP","crv":"Ed25519","x":"Pii06SUC...","use":"sig","alg":"EdDSA"}

$ curl "https://api.moltrust.ch/skill/trust-score/did:moltrust:d34ed796a4dc4698"
HTTP 200, application/json, 788 bytes
{ "did": "...", "trust_score": 85.0, "grade": "A",
  "breakdown": {...}, "endorser_count": 2,
  "flags": ["repetitive_endorsements","ghost_agent"], "flag_count": 2,
  "computed_at": "2026-05-14T06:55:01...", "cache_valid_until": "2026-05-14T07:55:01...",
  "consistency_level": "L1", ... }
```

Alle drei Endpoints erreichbar; server-side Code in `~/moltstack/app/caep.py` (Router separat von `main.py`), Rate-Limit dort via **eigener** `_caep_limiter = Limiter(key_func=_did_keyfunc)` mit `@_caep_limiter.limit("120/hour")` an `caep_pending` (Line 147–148). Per-DID-Key, unabhängig vom globalen IP-Limiter.

> **Inkonsistenz mit PROFILE.md.** PROFILE.md sagt "default limit 100, max 500"; der reale Code (`~/moltstack/app/caep.py:151`) hat `limit: int = Query(default=50, ge=1, le=PENDING_LIMIT_MAX)`. Default ist 50, nicht 100. Max-Wert `PENDING_LIMIT_MAX` — Quelle nicht weiter geprüft, vermutlich 500. Doku-Drift, nicht funktional kritisch, aber Library setzt `pageLimit: 100` default und liegt damit innerhalb des Caps.

### (c) CAEP in `agent-card.json`?

**Status:** **Nicht deklariert.** `GET /.well-known/agent-card.json` → HTTP 200, 7926 bytes. `capabilities.extensions` listet 5 Extensions:

1. `https://moltrust.ch/extensions/trust-score/v1`
2. `https://moltrust.ch/extensions/aae/v1`
3. `https://moltrust.ch/extensions/erc8004/v1`
4. `https://moltrust.ch/extensions/x402-payment/v1`
5. `https://moltrust.ch/extensions/discovery-surfaces/v1`

`grep -ci "caep" /.well-known/agent-card.json → 0`.

**Folge:** Ein A2A-Konsument, der nur die `agent-card.json`-Extensions liest, erkennt nicht, dass das Registry CAEP-Events emittiert. Wer `agent-firewall` integrieren will, muss die Endpoints aus `PROFILE.md` hardcoden oder aus `discovery-surfaces` heraus eine zusätzliche `caep`-URL ableiten. **Phase-1-Lücke**: eigene `caep/v1`-Extension fehlt.

---

## V-9 — Free-Path Rate-Limits (PARTIAL)

**Status:** PARTIAL — (a) **eindeutig beantwortbar**, (b) **enthält eine Ermessensfrage**, separat markiert.

### (a) Ist Rate-Limiting auf dem freien Pfad implementiert?

**Antwort: Teilweise.**

- **Globaler Limiter:** `~/moltstack/app/main.py:7-62` — `slowapi.Limiter(key_func=_ratelimit_key)`. Key-Func: API-Key wenn vorhanden, sonst Client-IP. Funktioniert nur auf Endpoints, deren Handler `request: Request` als Parameter haben **und** einen `@limiter.limit(...)`-Decorator tragen.
- **CAEP-Limiter:** `~/moltstack/app/caep.py:140-148` — eigener `Limiter(key_func=_did_keyfunc)`, Key = DID-Path-Param, `@_caep_limiter.limit("120/hour")` auf `/caep/pending/{did:path}`.

**Rate-Limits der für Onboarding relevanten Endpoints:**

| Endpoint | Limit (aktuell) | Key | Quelle |
| --- | --- | --- | --- |
| `POST /identity/register` | **10/minute** | IP (API-Key existiert beim Register noch nicht) | `main.py:816` |
| `POST /identity/register-batch` | (keine `@limiter.limit`) | ADMIN_KEY-gated | `main.py:2488` |
| `GET /skill/trust-score/{did:path}` | **kein Limit** (Handler hat keinen `request`-Parameter) | — | `main.py:1187-1188` |
| `GET /swarm/graph/{did:path}` | **kein Limit** (analog) | — | `main.py:1316` |
| `GET /swarm/stats` | **kein Limit** (analog) | — | `main.py:1398` |
| `GET /caep/pending/{did:path}` | **120/hour** | per-DID | `caep.py:147` |
| `POST /caep/acknowledge/{event_id}` | (kein Limit) | — | `caep.py:181` |
| `GET /.well-known/registry-key.json` | (kein Limit) | — | `caep.py:205` |

**Befund:** Die heute existierenden Limits decken Register und CAEP-Polling ab. **Trust-Score-Reads sind aktuell un-rate-limited** — der Handler `async def get_trust_score(did: str):` enthält keinen `request: Request`-Parameter, daher kann `@limiter.limit(...)` selbst wenn vorhanden nicht greifen. **Das ist die größte erkennbare Lücke gegenüber der Phase-1-Strategie**, die `60/min · 5 000/Tag` für Trust-Score-Reads vorschlägt.

### (b) Sind die vorgeschlagenen Limits mit der Hetzner-Kapazität tragbar?

**Aktuelles Volumen (Plausibilisierung):**

```
journalctl -u moltstack --since "24 hours ago" | grep -cE "HTTP" → 4 723 requests
Top paths last 1h: /health (97), /skill/trust-score/... (13), /.well-known/did.json (12), /stats (13)
```

- **Heutige Last:** ~4.7 k Requests / 24 h = ~0.05 RPS Durchschnitt, ~3 RPM Peak. Hetzner-VPS (Ubuntu 24, asyncio FastAPI + asyncpg) sitzt fast im Leerlauf.
- **Proposed `register 10/Tag/IP`:** strengere Drosselung als der heutige `10/minute` → **trivial tragbar**, defensiver gegen Sybil-Massen-Registrierung, kostet legitime Bursts (Hackathon-Demos). Empfehlung: zweistufig (10/min UND 10/24 h/IP via slowapi `dual limits`).
- **Proposed `Trust-Score-Reads 60/min · 5 000/Tag`:** aktuell **kein** Limit; bei 60 RPM/IP pro Endpoint bleibt das System weit unter Auslastung selbst bei 100 parallelen Konsumenten. Tragbar — Umsetzungs-Blocker ist die fehlende `request: Request`-Signatur, nicht die Kapazität.
- **Proposed `CAEP-Polling per-DID ≥30s`:** bereits live (`120/hour` = exakt 30 s Intervall). Empfehlung: deckungsgleich übernehmen, keine Änderung nötig.

**Ermessensfrage (nicht eindeutig beantwortbar).** Ob `register 10/Tag/IP` für die geplanten Hackathon-Use-Cases zu eng ist, hängt davon ab, wie viele Demo-Agents pro Workshop-Teilnehmer registriert werden sollen. Mit NAT-Pooling hinter Hochschul-/Café-Routern kann ein einzelner Hackathon-Tisch leicht 10–50 Registrierungen aus einer IP generieren. **Lars: bitte Hackathon-Annahmen festlegen, bevor `10/Tag/IP` produktiv geschaltet wird.** Markiert.

---

## Zusammenfassung (1 Zeile / Item)

```
V-1  ANSWERED  @moltrust/sdk@1.1.0: AgentTrust.register() vorhanden, selfOnboard() NICHT. Return Promise<unknown>.
V-2  ANSWERED  POST /identity/register → vollständiges AgentTrustCredential (Init-Score 0) + 175 Credits + Base-Anchor + Badge-String. Kein AAE-Envelope.
V-3  ANSWERED  9 Score-Komponenten (Endors / Propag / CrossVert / IPR / Pred / Wallet / AgentClass / Sybil / Inactivity). Live-DB: 68 Agents, nur 5 ≥60 = alle Seeds.
V-4  ANSWERED  uresolver live (200), valides DID-Document mit keyAnchor zu Base-Tx.
V-5  ANSWERED  /badge/{did} live (200, image/svg+xml, 1174 B), Score „85 / A".
V-6  ANSWERED  @moltrust/openclaw@1.0.1: NEIN, registriert sich NICHT selbst. Service-start verifyOnStart → verifyDid(), kein register-Call.
V-7  ANSWERED  agent-firewall@1.0.0 — PROFILE.md ist sauber (4 Endpoints, 120/h, JCS+Ed25519); alle 3 Endpoints live; CAEP NICHT als agent-card-Extension deklariert.
V-8  ANSWERED  /openapi.json live (OpenAPI 3.1.0, 136 paths, MolTrust API v2.4); /docs + /redoc auch live.
V-9  PARTIAL   Limits live für Register (10/min/IP) + CAEP (120/h/DID); Trust-Score-Reads UN-RATE-LIMITED (Handler ohne request-Param). Kapazität reicht; Hackathon-IP-Pool-Frage offen.
```

---

## KORREKTUR-NOTIZ (2026-05-18) — V-2: /identity/register verlangt X-API-Key

**Status:** Faktenkorrektur, nachträglich angehängt. Der ursprüngliche V-2-Befund oben
bleibt unverändert (forensisch); diese Notiz korrigiert ihn.

**Befund (read-only Code-Verifikation gegen aktuellen `main`):**
- `POST /identity/register` trägt ein **hartes `Depends(verify_api_key)`** —
  `app/main.py:973` (`register_agent(..., api_key: str = Depends(verify_api_key))`),
  `verify_api_key` `app/main.py:621` (`x_api_key: str = Header(alias="X-API-Key")`,
  **ohne Default → Pflicht-Header**). Live: keyloser Aufruf → `422`
  (`loc:["header","X-API-Key"]`), ungültiger Key → `403 "Invalid API key"`.
- Der `credit_middleware`-„Bypass" (`app/main.py:530-531`) betrifft **ausschließlich
  die Credit-Verrechnung**; danach `call_next` → der Handler erzwingt den Key über
  seine Dependency. **Credit-Bypass ≠ Auth-Bypass** (zwei getrennte Mechanismen).
- `git blame`/Pickaxe: Dependency seit Initial-Commit `6c6a892` (2026-03-10) —
  **keine** Regression der Security-Hardening-PRs (#17/#27/#29), ursprüngliches Design.

**Korrektur:** Die ursprüngliche V-2-Formulierung (sinngemäß „kein Key nötig / Register
frei") ist **falsch**. Korrekt: **credit-frei JA, key-frei NEIN.** Dies war die
**Wurzel der Verwechslung**, die sich in die Phase-1-Analyse fortgepflanzt hat
(`moltrust-web/docs/specs/2026-05-14_onboarding-flow-analysis.md` — dort separat als
v9-Faktenkorrektur behoben, moltrust-web PR #8) sowie in die Developer-Seiten-Aussage
„No account. No API key." (breitere Korrektur = Reconcile-/moltrust-web-Strang).

— Ende Korrektur-Notiz —
