# Spec — MoltGuard Discovery (Phase 1, WORKFLOW §3.3)

**Status:** ENTWURF — Lars-Freigabe vor Code.
**§2.3-Cross-Review:** offen, Entscheidung nach Lars-Sichtung. Vermutete Empfehlung: **Skip** — kein Auth-/Credential-/Token-Pfad geändert; rein deklarative Metadaten- + Doku-Surfaces über bereits live laufende MoltGuard-v1.5.0-Fläche.
**Datum:** 2026-05-20 · **Repo:** moltrust-api · **Branch:** docs/moltguard-discovery-spec
**Live-State (verifiziert 2026-05-20):**
- `api.moltrust.ch/openapi.json` enthält **0 von 136 Paths unter `/guard/`** (MoltGuard ist eigenständiger Node-Service, nicht im FastAPI-Mount).
- `api.moltrust.ch/llms.txt` referenziert **5 /guard/-Endpoints** (von ~68 public + paid).
- `api.moltrust.ch/.well-known/agent-card.json` hat **5 Extensions**, davon **0 für MoltGuard** (keine eigenständige Skill-/Extension-Deklaration).
- `api.moltrust.ch/guard/api/info` self-dokumentiert **24 free + 11 paid = 35 Endpoints** — die einzige aktuelle Discovery-Surface, ist aber human-readable JSON, keine OpenAPI.

## 1. Goal

MoltGuard's ~68 public + paid /guard/-Endpoints (heute praktisch unsichtbar für maschinelle Discovery) auf den drei kanonischen Discovery-Surfaces deklarieren, damit Agent-Konsumenten / KI-Clients / Devs sie ohne Repo-Lese-Pflicht finden, klassifizieren (free/paid) und nutzen können:

1. **OpenAPI 3.1** — eigener `/guard/openapi.json` an MoltGuard (Hono-generiert).
2. **Agent-Card-Extension** — `agent-card.json` `capabilities.extensions[]` +1 Eintrag `moltguard/v1` mit Cluster-Liste + Cross-Link auf `/guard/openapi.json`.
3. **`api.moltrust.ch/llms.txt`** — eigener Block `## MoltGuard endpoints (api.moltrust.ch/guard/)` mit free/paid-Untergliederung.

## 2. Non-Goals

- **Keine** MoltGuard-Endpoint-Logik-Änderung, keine Routenumbenennung, keine x402-Pricing-Anpassung. Reine Discovery-Deklaration.
- **Kein** `internal/*` (auth-gegated) und keine Webhook-Receiver-Endpoints in öffentlichen Surfaces — die bleiben absichtlich unentdeckbar.
- **Keine** Subscription-Tier-/API-Key-spezifische Discovery (das ist `extendedAgentCard`-Sache, separat).
- **Kein** moltrust-web Touch — das Marketing-`llms.txt` unter `moltrust.ch/llms.txt` referenziert MoltGuard nur konzeptuell (Produkt-Seite `/moltguard.html`), nicht endpoint-granular.

## 3. Architecture-Layer-Scope *(Pflichtfeld)*

### 3.1 Welche Surfaces — und was kommt rein

| Surface | Rolle | Inhalt (neu) | Tech-Quelle |
|---|---|---|---|
| `/guard/openapi.json` (NEU) | Maschinen-Spec, Single Source of Truth pro Endpoint | OpenAPI 3.1: alle public + paid Endpoints mit Params, Body, Responses, Security (x402), Tags pro Capability-Cluster | Hono `@hono/zod-openapi` oder vergleichbar — generiert aus Route-Definitionen in `~/moltguard/src/routes/` |
| `agent-card.json` extension `moltguard/v1` | A2A-konsumente Discovery-Marker | URI + baseUrl + openapi-URL + Cluster-Liste + paymentProtocol | FastAPI agent-card builder in `moltrust-api/app/` (heute 5 Extensions, +1 wird 6) |
| `api.moltrust.ch/llms.txt` | LLM/Agent-friendly Endpoint-Reference | Neuer Block `## MoltGuard endpoints` mit Sub-Listen `free` / `paid via x402` — kein Webhook, kein internal | Generierung im moltrust-api Repo (statisches File oder FastAPI-Endpoint, je nach existierender Implementierung) |

### 3.2 Separates `/guard/openapi.json` vs Integration in `api.moltrust.ch/openapi.json`

**Empfehlung: separates `/guard/openapi.json`.**

Begründung:
- **Tech-Stack-Trennung spiegelt operative Realität.** MoltGuard ist eigenständiger Hono/Node-Service mit eigenem Deploy-Zyklus, eigener Versionierung (v1.5.0), eigenem Wallet, eigener DB-Connection. Eine OpenAPI-Spec, die zwei unabhängige Codebasen zusammenfasst, fördert genau die Drift, vor der wir gerade kommen (heute: 0 `/guard/`-Paths im FastAPI-OpenAPI, weil keine FastAPI-Routen → korrekt!, ein Merge würde rein deklarativ erfolgen und sofort driften).
- **Konsumenten-Erwartung.** A2A-konformes Discovery erlaubt mehrere OpenAPI-URLs pro Service. Wir verlinken beide kreuzweise: das `agent-card.json` listet sowohl die FastAPI-Spec (`documentationUrl`) als auch die MoltGuard-Spec (`extensions.moltguard.v1.openapi`).
- **Build-Pipeline.** FastAPI generiert seine OpenAPI auto; Hono braucht `zod-openapi`-Integration (Phase 2). Beides parallel, ohne Cross-Repo-Build-Schritt.

**Verworfen:** Integration via Reverse-Proxy-Merge — nginx-seitiges Mergen zweier OpenAPI-Dokumente ist möglich aber fehleranfällig (Component-Name-Kollisionen, Tag-Konflikte). Tradeoff nicht wert.

**Konsequenz:** Konsumenten haben **zwei** OpenAPI-URLs. Mitigation: beide in jeder Discovery-Surface klar referenziert (agent-card + llms.txt).

### 3.3 Klassifikation als hartes Regelwerk

Drei Klassen, harte Aufnahme-Regel pro Surface:

| Klasse | Definition | OpenAPI | agent-card | llms.txt |
|---|---|---|---|---|
| **public/free** | Kein Payment, optional rate-limited via Free-Tier (1/10min etc.) | ✅ | ✅ (via Cluster) | ✅ Free-Block |
| **paid (x402)** | In `x402-prices.ts` mit Preis > 0 | ✅ mit `security.x402` | ✅ (via Cluster) | ✅ Paid-Block, mit Preis |
| **internal** | Unter `/internal/*` (Hono `authMiddleware` ab `app.use('/internal/*')`) — `harness/*`, `auth/login` | ❌ explizit AUSGESCHLOSSEN | ❌ | ❌ |
| **webhook (consumer-internal)** | `POST /api/webhooks/aeoess` — externer Service callt rein, kein Agent-Pull | ❌ AUSGESCHLOSSEN | ❌ | ❌ |
| **Subscription-/API-Key-gated** | Existiert in MoltGuard heute nicht; falls künftig: `extendedAgentCard`-Pfad statt public Discovery | n/a | (extendedAgentCard) | n/a |

Internal/webhook bleiben absichtlich unentdeckbar. Discovery-Checklist im neu gemergten `CLAUDE.md` §Gate (PR #47) deckt das: „Ist der Endpoint internal-only / admin-only? Wenn ja: nicht in Agent-Card / öffentlicher OpenAPI-Spec eintragen."

### 3.4 Capability-Cluster (für agent-card-Skills + llms.txt-Gruppierung + OpenAPI-Tags)

Statt einer flachen 68-Endpoint-Liste schlage ich 10 Cluster vor, abgeleitet aus den 22 Route-Files unter `~/moltguard/src/routes/`:

1. **agent-scoring** — `/api/agent/*` (score, score-free, detail, sample) — 4 Endpoints
2. **sybil-detection** — `/api/sybil/*` — 1 Endpoint
3. **market-integrity** — `/api/market/*` + `/events/feed` — 5 Endpoints
4. **skill-verification** — `/skill/*` + `/audit/*` + `/vc/skill/*` — 9 Endpoints
5. **credential-issuance** — `/api/credential/*` + `/vc/*/issue` Sammlung — 6 Endpoints
6. **shopping-vc** — `/shopping/*` + `/vc/buyer-agent/issue` — 5 Endpoints
7. **travel-vc** — `/travel/*` + `/vc/travel-agent/issue` — 6 Endpoints
8. **salesguard** — `/salesguard/*` — 5 Endpoints
9. **prediction-markets** — `/prediction/*` + `/vc/prediction/issue` — 5 Endpoints
10. **transparency** — `/transparency/*` + `/health` + `/api/info` — 5 Endpoints

Zusätzlich (vermutlich kein eigener Cluster, kandidiert für 11):
- **graph + flags + action + governance + aae + wallet-attest + hackathon + challenge** — 19 Endpoints. **Open Decision (§9):** ein eigener Cluster `agent-graph` oder mehrere Sub-Cluster? Tendenz: lieber 3–4 kleinere Cluster (`agent-graph`, `agent-flags`, `aae-evaluation`, `attestation`) als ein Sammel-Cluster.

Resultat: ~10–14 Cluster, je ein OpenAPI-Tag und ein agent-card-Skill (oder: ein einziges `moltguard/v1`-Extension mit Cluster-Array im params).

## 4. Data-Model-Changes

Keine. Reine Doku-/Metadaten-Surfaces.

## 5. API-Contract-Changes

Drei additive Änderungen, kein Breaking.

### 5.1 `/guard/openapi.json` (NEU)

Specification: **OpenAPI 3.1**. Spec-Gerüst:

```yaml
openapi: 3.1.0
info:
  title: MoltGuard
  version: 1.5.0
  description: |
    Trust & Integrity Service for the x402 Agent Economy.
    Sub-API of MolTrust Trust Registry (api.moltrust.ch).
    See also: https://api.moltrust.ch/openapi.json (parent service).
  contact:
    name: CryptoKRI GmbH
    url: https://moltrust.ch
  license:
    name: Apache-2.0  # zu verifizieren — repo-LICENSE auf Server
servers:
  - url: https://api.moltrust.ch/guard
    description: Production
security: []  # default: public
components:
  securitySchemes:
    x402:
      type: apiKey  # OpenAPI hat kein natives x402; pragmatisch via apiKey-Marker mit description, plus extension x-moltrust-pricing
      in: header
      name: X-PAYMENT
      description: |
        x402 v2 payment receipt header. Format: "x402 <base64-encoded-receipt>".
        See https://x402.org/writing/x402-v2-launch.
  schemas:
    # zod-openapi generiert aus den existierenden Hono-Schemas (~/moltguard/src/schemas/)
paths:
  /api/agent/score/{address}:
    get:
      tags: [agent-scoring]
      security:
        - x402: []
      x-moltrust-pricing:
        amount: "0.05"
        currency: USDC
        chain: eip155:8453
      # … Params, Responses
  # … (~57 public + 11 paid weitere Pfade)
tags:
  - name: agent-scoring
  - name: sybil-detection
  - name: market-integrity
  # … 10–14 Cluster
```

Auslieferung: `GET https://api.moltrust.ch/guard/openapi.json` → 200 application/json. Optional: `GET https://api.moltrust.ch/guard/docs` → Swagger-UI (analog zu FastAPI's `/docs`).

### 5.2 `agent-card.json` Extension

Additiver Eintrag in `capabilities.extensions[]` (heute 5 → wird 6):

```json
{
  "uri": "https://moltrust.ch/extensions/moltguard/v1",
  "description": "MoltGuard sub-API — risk scoring, sybil detection, market integrity, skill/shopping/travel/prediction credential issuance. x402-paid endpoints on Base L2.",
  "required": false,
  "params": {
    "baseUrl": "https://api.moltrust.ch/guard",
    "openapi": "https://api.moltrust.ch/guard/openapi.json",
    "infoEndpoint": "https://api.moltrust.ch/guard/api/info",
    "capabilityClusters": [
      "agent-scoring",
      "sybil-detection",
      "market-integrity",
      "skill-verification",
      "credential-issuance",
      "shopping-vc",
      "travel-vc",
      "salesguard",
      "prediction-markets",
      "transparency"
    ],
    "paymentProtocol": "x402",
    "paymentChain": "eip155:8453",
    "paymentCurrency": "USDC"
  }
}
```

Hinweis: das Extension-Objekt-Format ist 1:1 an die existierenden 5 Extensions in `agent-card.json` angelehnt (`uri`, `description`, `required`, `params`). Konsumenten, die `moltguard/v1` ignorieren, sind unberührt (additiv).

### 5.3 `api.moltrust.ch/llms.txt` neuer Block

Eingefügt zwischen `## Live endpoints — paid via x402 (USDC on Base L2)` und `## DID method`, oder als eigene Section direkt nach den existierenden Endpoint-Blöcken:

```markdown
## MoltGuard sub-API (api.moltrust.ch/guard/)

OpenAPI: <https://api.moltrust.ch/guard/openapi.json> · Self-doc: <https://api.moltrust.ch/guard/api/info>

### Free (no payment; some rate-limited)
- `GET /guard/health` — Service status
- `GET /guard/api/info` — Self-documentation (live pricing inventory)
- `GET /guard/api/agent/sample` — Sample wallet score (no auth)
- `GET /guard/api/agent/score-free/{address}` — Wallet score, 1 req/10min
- `GET /guard/api/market/sample` — Sample market score
- `GET /guard/api/market/check-free/{marketId}` — Market check, 1 req/10min
- `GET /guard/skill/info` · `GET /guard/skill/schema`
- `GET /guard/skill/audit?url=<github-url>` — Skill repo audit, 5 req/hr
- `GET /guard/skill/verify/{skillHash}` · `GET /guard/skill/verify/did/{did}`
- `GET /guard/shopping/info` · `GET /guard/shopping/schema` · `GET /guard/shopping/receipt/{id}` · `POST /guard/shopping/verify`
- `GET /guard/travel/info` · `GET /guard/travel/schema` · `GET /guard/travel/receipt/{id}` · `GET /guard/travel/trip/{tripId}` · `POST /guard/travel/verify`
- `POST /guard/prediction/wallet-link` · `GET /guard/prediction/wallet/{address}` · `GET /guard/prediction/leaderboard`
- `POST /guard/api/credential/verify` — Verify W3C VC + AAE chain
- `GET /guard/transparency/latest` · `GET /guard/transparency/history` · `GET /guard/transparency/verify/{hash}`
- (siehe OpenAPI für die vollständige Liste, ~57 free Endpoints)

### Paid via x402 (USDC on Base L2)
- `GET /guard/api/agent/score/{address}` — $0.05 — Full risk profile
- `GET /guard/api/agent/detail/{address}` — $0.05 — Detailed agent breakdown
- `GET /guard/api/sybil/scan/{address}` — $0.10 — On-chain sybil-cluster detection
- `GET /guard/api/market/check/{id}` — $0.05 — Market integrity check
- `GET /guard/api/market/feed` — $0.10 — Market data feed
- `POST /guard/api/credential/issue` — $0.10 — Generic credential issuance
- `GET /guard/prediction/integrity/{market_id}` — $0.10 — Prediction-market integrity
- `POST /guard/vc/skill/issue` — $5.00 — VerifiedSkillCredential issuance
- `POST /guard/vc/prediction/issue` — $5.00 — PredictionTrackCredential issuance
- `POST /guard/vc/buyer-agent/issue` — $5.00 — BuyerAgentCredential issuance
- `POST /guard/vc/travel-agent/issue` — $5.00 — TravelAgentCredential issuance
```

## 6. Migration-Path (Phasen)

| Phase | Inhalt | Repo | Branch | Deploy |
|---|---|---|---|---|
| **P1 (diese SPEC)** | Architektur-Briefing, kein Code | moltrust-api | `docs/moltguard-discovery-spec` | Nein |
| **P2 — OpenAPI** | `@hono/zod-openapi` einbauen in `~/moltguard`, `/guard/openapi.json` + optional `/guard/docs` ausspielen | moltguard (separates Repo, server-only heute) | `feature/openapi` | Ja (MoltGuard restart) |
| **P3 — Agent-Card** | Extension `moltguard/v1` in agent-card-Builder, openapi-Cross-Link | moltrust-api | `feature/agent-card-moltguard-extension` | Ja (moltrust-api restart) |
| **P4 — llms.txt** | Neuer Block in api.moltrust.ch/llms.txt | moltrust-api | `feature/llms-moltguard-block` | Ja (statisches File oder API-restart, je nach Implementation) |
| **P5 — Verifikation** | Live-Probes (curl der drei Surfaces), Discovery-Checklist abhaken | — | — | — |

**Reihenfolge:** P2 muss vor P3/P4 fertig sein (OpenAPI-URL muss live sein, bevor agent-card/llms.txt drauf verlinken). P3 und P4 können parallel.

## 7. Rollback-Plan

- **P2:** `/guard/openapi.json`-Endpoint deaktivieren (Hono-Route entfernen) — keine Konsumenten-Datenwirkung, da neuer Endpoint. Bestehende /guard/*-Routen unberührt.
- **P3:** Extension-Eintrag aus agent-card-Builder entfernen — rein additiv reversibel.
- **P4:** Block aus llms.txt entfernen — trivial reversibel.
- Keine DB-Migrationen, kein State-Roll.

## 8. Success-Criteria

1. `GET https://api.moltrust.ch/guard/openapi.json` → 200, OpenAPI-3.1-konformes JSON, alle public + paid Endpoints enthalten, **kein** `/internal/*`-Pfad, **kein** `/api/webhooks/*`-Pfad.
2. Anzahl Paths in `/guard/openapi.json` ≈ Anzahl Endpoints im Route-Code minus internal/webhook (Toleranz ±2 für Audit-Aliasse).
3. `GET .well-known/agent-card.json` → `capabilities.extensions[]` Länge wird von 5 auf 6; Eintrag mit `uri:.../moltguard/v1` enthält `openapi`-Param mit URL aus (1.).
4. `GET api.moltrust.ch/llms.txt` → Block `## MoltGuard sub-API` existiert, listet ≥ 11 paid und ≥ 22 free Endpoints, verweist auf `/guard/openapi.json`.
5. Discovery-Checklist (`CLAUDE.md`, V1.2 nach PR #47) für die Phase-Abschluss-Items abgehakt: Agent-Card ✓, Extended Card unverändert ✓, OpenAPI-Contract ✓, llms.txt ✓.

## 9. Open Decisions (für Lars vor P2-Start zu klären)

- **9.1 OpenAPI-Generator-Choice.** `@hono/zod-openapi` (offiziell, mature) vs `hono-openapi` (community) vs manueller Spec-Pflege-Pfad. Tendenz: zod-openapi, weil MoltGuard schon Zod-Schemas hat (`~/moltguard/src/schemas/`). Sub-Entscheidung: Schema-Reuse vs `.openapi(...)`-Annotationen pro Route — am bestehenden Code-Stil ausrichten, nicht erfinden.
- **9.2 Cluster-Granularität für die „Sammel-19" (graph/flags/action/governance/aae/wallet-attest/hackathon/challenge).** Drei Optionen:
  - (a) ein Sammel-Cluster `agent-graph-and-tools` (zu grob, schlechte Discovery).
  - (b) 4 Cluster: `agent-graph`, `agent-flags`, `aae-evaluation`, `attestation-and-hackathon`.
  - (c) je 1 Cluster pro Route-File (8 zusätzliche Cluster, gesamt 18) — wird im agent-card-Skill-Array unhandlich.
  - Empfehlung: (b).
- **9.3 OpenAPI `/guard/openapi.json` URL-Stabilität.** Versionierung? `/guard/openapi.json` vs `/guard/v1/openapi.json`. Tendenz: heute `/guard/openapi.json` (analog zu FastAPI's `/openapi.json`), Version 1.5.x im `info.version`-Feld; Major-Bumps via separate Route nur falls je nötig.
- **9.4 `extendedAgentCard`-Konsequenz.** Heute deklariert die `extendedAgentCard` (auth-gated) laut `llms.txt` „9 skills + 7 extensions including x402 pricing inventory and MoltGuard capabilities". Mit dem neuen `moltguard/v1`-Extension in der public agent-card ist die Frage: bleibt die x402-Pricing-Inventory in der extendedAgentCard, oder wandert sie in `/guard/openapi.json`'s `x-moltrust-pricing`-Felder? Tendenz: Pricing ist **public knowledge** → in OpenAPI + öffentliche Extension. extendedAgentCard kann auf öffentliche Extension verweisen statt zu duplizieren. Konkrete Doku-Drift-Korrektur ist Subscope von P3.
- **9.5 `/events/feed` Pricing-Lücke.** Memory + Outreach-Doku nennen `/events/feed` als $0.05-paid, aber `x402-prices.ts` listet nur `/api/market/feed`. Live: `/guard/events/feed` antwortet 200 GET ohne Payment-Header. **Pre-P2-TODO:** Mit MoltGuard-Owner klären — fehlt das Pricing in der Config, oder ist `/events/feed` doch free? OpenAPI-Spec muss dieser Realität entsprechen.
- **9.6 §2.3 Cross-Review jetzt oder bei P2.** Diese SPEC selbst hat keinen Auth-/Credential-Pfad. P2 (OpenAPI-Implementation) hat ebenfalls keinen — aber P3 (agent-card-Builder-Patch) berührt die signierte agent-card-Generierungslogik. Empfehlung: §2.3-Cross-Review **bei P3-PR**, nicht für diese SPEC und nicht für P2.

## Appendix A — Vollständige Endpoint-Inventur (live verifiziert 2026-05-20)

Quelle: Route-Files unter `~/moltguard/src/routes/` (SSH read-only Enumeration) + `x402-prices.ts` Pricing-Config + Live-Probes gegen `api.moltrust.ch/guard/*`. Pfade hier ohne `/guard/`-Prefix (das ist nginx-Proxy-Pfad-Mount, im Spec-OpenAPI als `server.url` deklariert).

### A.1 Paid (x402) — 11 Endpoints, alle in `x402-prices.ts`

| Method | Path | Preis | Cluster |
|---|---|---|---|
| GET | `/api/agent/score/{address}` | $0.05 | agent-scoring |
| GET | `/api/agent/detail/{address}` | $0.05 | agent-scoring |
| GET | `/api/sybil/scan/{address}` | $0.10 | sybil-detection |
| GET | `/api/market/check/{marketId}` | $0.05 | market-integrity |
| GET | `/api/market/feed` | $0.10 | market-integrity |
| POST | `/api/credential/issue` | $0.10 | credential-issuance |
| GET | `/prediction/integrity/{market_id}` | $0.10 | prediction-markets |
| POST | `/vc/skill/issue` | $5.00 | skill-verification |
| POST | `/vc/prediction/issue` | $5.00 | prediction-markets |
| POST | `/vc/buyer-agent/issue` | $5.00 | shopping-vc |
| POST | `/vc/travel-agent/issue` | $5.00 | travel-vc |

### A.2 Free / rate-limited public — ~57 Endpoints

**transparency + meta:**
- GET `/` (landing HTML — NICHT in OpenAPI; HTML, kein API)
- GET `/health`
- GET `/api/info` (heutiges Self-Doc)
- GET `/transparency/latest`, `/transparency/history`, `/transparency/verify/{hash}`

**agent-scoring:**
- GET `/api/agent/sample`
- GET `/api/agent/score-free/{address}` (rate-limit 1/10min)

**market-integrity:**
- GET `/api/market/sample`
- GET `/api/market/check-free/{marketId}` (rate-limit 1/10min)
- GET `/events/feed` (siehe §9.5 — Pricing-Klärung offen)

**skill-verification:**
- GET `/skill/info`, `/skill/schema`
- GET `/skill/audit?url=<github-url>` (rate-limit 5/hr)
- GET `/skill/verify/{skillHash}`, `/skill/verify/did/{did}`
- GET `/skill/anchor/{skillHash}`
- GET `/audit/checks`, `/audit/version`

**credential-issuance:**
- POST `/api/credential/verify`

**shopping-vc:**
- GET `/shopping/info`, `/shopping/schema`
- GET `/shopping/receipt/{id}`
- POST `/shopping/verify`

**travel-vc:**
- GET `/travel/info`, `/travel/schema`
- GET `/travel/receipt/{id}`, `/travel/trip/{tripId}`
- POST `/travel/verify`

**salesguard:**
- POST `/salesguard/brand/register`, `/salesguard/product/register`, `/salesguard/reseller/authorize`
- GET `/salesguard/verify/{product_id}`, `/salesguard/reseller/verify/{reseller_did}`

**prediction-markets:**
- POST `/prediction/wallet-link`
- GET `/prediction/wallet/{address}`, `/prediction/leaderboard`

**Sammel-19 (Cluster-Frage §9.2):**
- AAE: GET/POST `/vc/aae/evaluate`, GET `/vc/aae/info`
- Wallet attestation: POST `/api/wallet/attest`, GET `/api/wallet/attest/{did}`
- Hackathon: POST `/hackathon/register`, GET `/hackathon/stats`
- Challenge (VC binding): GET `/vc/challenge`, POST `/vc/verify-binding`, POST `/vc/register-key`
- Action: POST `/api/action/check`, GET `/api/action/stats`, GET `/api/action/events/{did}`
- Governance: POST `/governance/validate-capabilities`
- Graph: GET `/api/graph/score/{fromDid}/{toDid}`, `/api/graph/neighbours/{did}`, `/api/graph/stats`
- Flags: GET `/api/flags`, `/api/flags/track-record`, `/api/flags/{flagId}`; POST `/api/flags/record`

### A.3 AUSGESCHLOSSEN aus Discovery (zur Dokumentation)

**Internal (`/internal/*`, hinter `authMiddleware`) — 7 Endpoints:**
- POST `/internal/auth/login`
- GET `/internal/harness/verticals`, POST `/internal/harness/run`, `/internal/harness/grade`, `/internal/harness/generate-case`, `/internal/harness/publish-proof`
- GET `/internal/harness/proofs`

**Webhook-Receiver (consumer-internal) — 1 Endpoint:**
- POST `/api/webhooks/aeoess`

Diese 8 Endpoints sind bewusst opaque für externe Discovery und bleiben es. Falls je ein internes admin-Interface eine eigene authentifizierte Discovery-Surface bekommen soll → separates `extendedAgentCard`-Skill, nicht hier.

## Appendix B — BACKLOG-Mapping

`docs/BACKLOG.md` enthält heute (verifiziert):
- Zeile 309: „`/guard/audit/version` funktioniert, aber `/audit/version` 404, `/guard/audit` 404. Inkonsistente Convention. Fix: alle Audit-Endpoints unter `/guard/audit/*` konsolidieren ODER 301-redirects einrichten." → **berührt §A.2 audit-Items**; OpenAPI-Spec sollte die Convention-Klärung antriggern. Ist aber Code-Issue, nicht Discovery-Issue. Wird im P2-PR mitvermerkt, kein Blocker für diese SPEC.

Kein direktes Backlog-Item „MoltGuard Discovery" existiert heute — diese SPEC ist die Initialisierung des Backlogs für den ~60-Endpoint-Gap.
