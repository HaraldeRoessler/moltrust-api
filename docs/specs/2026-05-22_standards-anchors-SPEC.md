# SPEC — Sprint 2.4: Western Institutional Anchors in Discovery-Surfaces

- **Datum:** 2026-05-22
- **Autor:** Lars Kroehl (CryptoKRI GmbH)
- **Status:** DRAFT — wartet auf Spec-Abnahme. **Phase 1 = reine Doku, kein Code-Change.**
- **Sprint-Kontext:** Visibility-Sprint 2.4 (Western Institutional Anchors).
- **§2.3 Cross-Review:** entfällt (deklarative Doku-Felder, kein Auth-/Credential-Pfad).

## 0. Ziel

5 Standards-Anchors maschinenlesbar in der Platform-Agent-Card referenzieren:
**NIST AI RMF · EU AI Act · FATF (2023) · MITRE ATLAS · OWASP LLM Top 10**.
Empfehlung §2.4: zusätzlich **Singapore IMDA MGF** (siehe §2.4) → 6 Einträge.

---

## ⚠️ 0.1 Zentraler Befund — Source-of-Truth-Drift (Phase-2-Vorbedingung)

Die Surfaces-Audit hat eine **unreconciled Repo↔Live-Drift** der `agent-card.json`
aufgedeckt, die Phase 2 blockiert, wenn sie nicht zuerst geklärt wird:

| Quelle | Stand |
|---|---|
| **Live** `/var/www/html/.well-known/agent-card.json` | **v1.0**, 7926 B, **5 Extensions**, 5 Skills — `www-data`, mtime 2026-05-10 |
| **GitHub `MoltyCel/moltrust-web`** `.well-known/agent-card.json` | **v0.3**, 4385 B, **1 Extension** (`trust-score`) — zuletzt in `9e1ddf8 chore: import /var/www/html production state` |

→ Das GitHub-Repo-File ist **stale** und **nicht** die Quelle der Live-Card. Die
Live-Card (v1.0, 5 Extensions) wurde server-seitig gepflegt. `/var/www/html/`
ist zudem **selbst ein git-Repo** (bekannte `.git-in-webroot`-Hygiene-Notiz).

**Konsequenz:** Würde Phase 2 das `moltrust-web`-Repo-File (v0.3) editieren und
deployen, würde die Live-Card **auf v0.3 zurückgeworfen** (4 Extensions verloren,
Versions-Downgrade). **Phase 2 darf nicht starten, bevor entschieden ist, was der
kanonische Quell-Ort der `agent-card.json` ist.** Optionen (Lars-Entscheidung):
- **A** — Live-v1.0-Inhalt in `MoltyCel/moltrust-web` reconcilen, dann dort die
  Anchors ergänzen, dann deployen. Sauber, aber Reconcile-Vorsprint nötig.
- **B** — Die Anchors direkt am kanonischen Live-Ort pflegen (webroot-git-Repo),
  + diesen Ort als SoT formalisieren.
- Verknüpft mit BACKLOG-Item „.well-known-Mirror-Generierung" (OD-8).

Diese SPEC beschreibt das Anchor-Design *zustands-unabhängig* — die SoT-Klärung
ist Schritt 0 der Phase-2-Ausführung.

---

## 1. Surfaces-Audit (read-only verifiziert 2026-05-22)

| Surface | Quelle / wer schreibt | Konsument | In Scope 2.4? |
|---|---|---|---|
| `api.moltrust.ch/.well-known/agent-card.json` | nginx-static aus `/var/www/html/.well-known/agent-card.json` | AI-Crawler, Agent-Directories, A2A-Clients | ✅ |
| `moltrust.ch/.well-known/agent-card.json` | **dieselbe Datei** — ETag `6a0055d6-1ef6` identisch zu api | dito | ✅ (= dieselbe Datei) |
| `extendedAgentCard` (`api.moltrust.ch/extendedAgentCard`) | `_load_public_agent_card()` liest `/var/www/html/.well-known/agent-card.json` + spreizt sie (`{**public_card, …}`) | auth. Clients | ✅ **automatisch** (erbt jedes Card-Feld via Spread) |
| `api.moltrust.ch/.well-known/erc8004.json` | statische Datei, eigenes Schema (`type/name/description/image/services/skills`) | ERC-8004-Resolver | ❌ (siehe §5) |
| `/a2a/agent-card/{did}` Per-DID-Cards | Handler-generiert aus DB (Trust-Card-Schema) | Per-Agent-Verifier | ❌ (siehe §5) |

**Kernbefund:** Die Platform-Card ist **eine einzige Datei**. „api-Card" und
„web-Card" sind byte-identisch (gleiche ETag) — **kein Multi-Copy-Drift**.
`extendedAgentCard` erbt jeden Card-Top-Level- und `capabilities`-Eintrag
automatisch über den Spread → **keine separate Arbeit dort**.

---

## 2. Schema-Design

### 2.1 Platzierung — Empfehlung: Extension, nicht Top-Level-Feld

**Empfehlung: ein neuer Eintrag in `capabilities.extensions[]`** statt eines
custom Top-Level-Felds (`complianceAnchors`).

Begründung:
- **A2A-Konformität:** Die Card deklariert sich als „Reference implementation of
  the Trust Registry Binding for **A2A v1.0**". Das A2A-AgentCard-Schema hat feste
  Top-Level-Felder; ein custom `complianceAnchors` Top-Level ist **nicht
  schema-konform** — strikte Validatoren droppen/ablehnen unbekannte Top-Level-Keys.
  `capabilities.extensions[]` **ist** der A2A-sanktionierte Erweiterungspunkt.
- **Präzedenz im eigenen Repo:** Die Card nutzt Extensions bereits für
  *Nicht-Capability-Metadaten* — `discovery-surfaces/v1` ist ein Datei-Inventar,
  keine Protokoll-Capability. Ein `standards-alignment`-Extension passt exakt in
  dieses etablierte Muster (aktuell 5 Extensions: trust-score, aae, erc8004,
  x402-payment, discovery-surfaces).
- **Trade-off (ehrlich):** Ein Top-Level-Feld wäre unmittelbar sichtbarer; das
  Extension ist unter `capabilities.extensions[]` verschachtelt. Mitigiert dadurch,
  dass A2A-Consumer das `extensions`-Array ohnehin nativ parsen und
  `discovery-surfaces/v1` Consumer bereits darauf trainiert.

### 2.2 Feld-Name — Empfehlung: `standards-alignment`

- ❌ `complianceAnchors` — „compliance" ist falsch für MITRE ATLAS / OWASP LLM
  Top 10 (Security-Knowledge-Bases, keine Compliance-Regime).
- ❌ `regulatoryAlignment` — „regulatory" ist falsch für NIST AI RMF (freiwilliges
  Framework) und MITRE/OWASP.
- ✅ `standards-alignment` — deckt Regulierung **und** Frameworks **und**
  Security-KBs ab; neutral und akkurat.

### 2.3 Struktur

```json
{
  "uri": "https://moltrust.ch/extensions/standards-alignment/v1",
  "description": "Alignment with external AI-governance, risk and security standards",
  "required": false,
  "params": {
    "frameworks": [
      {
        "name": "NIST AI Risk Management Framework",
        "id": "nist-ai-rmf",
        "url": "<kanonische NIST-AI-RMF-URL>",
        "mapping": "https://moltrust.ch/publications/nist-ai-rmf-mapping.pdf"
      },
      {
        "name": "EU AI Act",
        "id": "eu-ai-act",
        "url": "<kanonische EUR-Lex-URL>",
        "mapping": "https://moltrust.ch/publications/eu-ai-act-mapping.pdf"
      },
      { "name": "FATF Guidance (2023)", "id": "fatf-2023", "url": "<FATF-URL>" },
      { "name": "MITRE ATLAS", "id": "mitre-atlas", "url": "https://atlas.mitre.org" },
      { "name": "OWASP Top 10 for LLM Applications", "id": "owasp-llm-top10", "url": "<OWASP-URL>" },
      { "name": "Singapore IMDA Model AI Governance Framework", "id": "imda-mgf", "url": "<IMDA-URL>" }
    ]
  }
}
```

- `mapping` ist **optional** — nur gesetzt, wo ein internes Mapping-Dokument
  existiert (siehe §3). FATF/MITRE/OWASP/IMDA: vorerst ohne `mapping`.
- `id` als stabiler maschinenlesbarer Slug zusätzlich zum `name`.

### 2.4 Singapore IMDA MGF — Empfehlung: aufnehmen

**Ja, aufnehmen** (als 6. Eintrag). Die Card-`description` behauptet bereits
„Implements Singapore IMDA MGF for Agentic AI"; `llms.txt` referenziert es
(Z.3 + „Standards engagement"). Eine Anchor-Liste, die IMDA auslässt, während
die Prosa es führt, wäre ein Selbstwiderspruch. Der Sprint-Titel sagt „Western",
das Feld heißt aber neutral `standards-alignment` → IMDA passt.

---

## 3. URLs + interne Mapping-Files

### 3.1 Interne Mapping-Files — Pre-Check-Ergebnis

| Framework | Internes Mapping-Doc | Status |
|---|---|---|
| EU AI Act | `/publications/eu-ai-act-mapping.pdf` | ✅ existiert (live 200) |
| NIST AI RMF | `/publications/nist-ai-rmf-mapping.pdf` | ✅ existiert (live 200) |
| FATF (2023) | — | ❌ **kein Mapping-Doc** |
| MITRE ATLAS | — | ❌ **kein Mapping-Doc** |
| OWASP LLM Top 10 | — | ❌ **kein Mapping-Doc** |
| IMDA MGF | — | ❌ kein Mapping-Doc (Positionierung in `/regulated-markets.html`) |

→ Nur **2 von 5** internen Mapping-Dokumenten existieren. **Das blockiert 2.4
nicht:** der Anchor-Eintrag mit kanonischer Standard-URL ist eigenständig
wertvoll; `mapping` bleibt optional. Empfehlung: FATF-/MITRE-/OWASP-Mapping-Docs
als **separates Folge-BACKLOG-Item** (eigene Recherche-/Schreibarbeit), nicht
Teil von 2.4.

### 3.2 Kanonische Standard-URLs

Die `url` je Framework zeigt auf die **offizielle Standard-Quelle**. Exakte URLs
sind in Phase 2 mit Live-200-Probe zu **verifizieren** (kein hartes Festschreiben
unverifizierter Deep-Links in dieser SPEC — CLAUDE.md Hard-Rule). Zielquellen:
NIST AI RMF (nist.gov), EU AI Act (EUR-Lex), FATF (fatf-gafi.org), MITRE ATLAS
(`atlas.mitre.org`), OWASP LLM Top 10 (owasp.org-Projektseite), IMDA MGF
(imda.gov.sg / aiverifyfoundation.sg).

---

## 4. Drift-Prevention

**Ergebnis: kein Drift-Mechanismus für die Anchors nötig.** Begründung:
- Die `agent-card.json` ist **eine einzige Datei** (§1) — api-Card, web-Card und
  `extendedAgentCard` lesen alle dieselbe Quelle. Es gibt **keine** Multi-Copy,
  also keinen Anchor-Drift zwischen Surfaces. Build-Time-Generation oder
  Drift-Check-Skript wären over-engineered.
- Einzige separate Surface mit überlappendem Inhalt: **`llms.txt`** (führt die
  Standards prosaisch). 6 statische, selten ändernde Einträge → **hand-curated im
  selben PR** genügt; ein Drift-Skript ist unverhältnismäßig.

**Nicht zu verwechseln** mit der Repo↔Live-Drift aus §0.1 — das ist ein
*bestehendes* SoT-Problem, das Phase 2 als Schritt 0 löst, kein Anchor-Drift.

---

## 5. Scope

| In Scope | Out of Scope (mit Begründung) |
|---|---|
| Platform `agent-card.json` (= api + web + extendedAgentCard, eine Datei) | **Per-DID-Cards** `/a2a/agent-card/{did}` — Trust-Cards, agent-spezifisch, Handler-generiert; ein Platform-Standards-Anchor gehört nicht in eine Per-Agent-Surface |
| `llms.txt`-Standards-Block | **`erc8004.json`** — ERC-8004-Registrierungs-Datei mit eigenem Schema (`type/services/skills`); Compliance-Anchors passen nicht zu ihrem Zweck |

Deckt sich mit dem Lars-Bias: nur Platform-Cards für 2.4.

---

## 6. Verifikation (Phase 2, post-Deploy)

- `curl https://api.moltrust.ch/.well-known/agent-card.json` → `standards-alignment`-Extension mit allen 6 Frameworks, jede `url` löst 200.
- `curl https://moltrust.ch/.well-known/agent-card.json` → identisch (gleiche Datei).
- `curl -H "X-API-Key: …" https://api.moltrust.ch/extendedAgentCard` → Extension geerbt.
- `curl https://moltrust.ch/llms.txt` → Standards-Block listet alle 6.
- Pre-Flight: jede der 6 kanonischen URLs einzeln auf HTTP 200 prüfen.

---

## 7. Discovery-Checklist

- **Sitemap:** `agent-card.json` liegt unter `/.well-known/` — **keine** HTML-Seite,
  gehört **nicht** in `sitemap.xml`. Kein `lastmod`-Eintrag.
- **`llms.txt`:** der Block referenziert heute EU AI Act + NIST (als Publications)
  + IMDA (Standards engagement). Phase 2 **ergänzt FATF + MITRE ATLAS + OWASP LLM
  Top 10** → alle 6 konsistent zur Card.
- **RSS / JSON-LD:** nicht betroffen (kein neues Publikations-Artefakt; die
  Mapping-PDFs existieren bereits bzw. sind Folge-Item §3.1).

---

## 8. Phase-2-Ausführungs-Skizze (nach Spec-Abnahme — nicht dieser Sprint)

0. **SoT-Klärung** (§0.1) — Lars entscheidet A/B; ggf. Reconcile-Vorsprint.
1. `standards-alignment/v1`-Extension in die **kanonische** `agent-card.json` einfügen (6 Frameworks).
2. Kanonische URLs verifizieren (Live-200), `mapping` für EU AI Act + NIST setzen.
3. `llms.txt`-Standards-Block auf 6 ergänzen.
4. Deploy gemäß SoT-Entscheidung; `post-sha == repo-sha`.
5. Verifikation §6.
6. Folge-BACKLOG: FATF-/MITRE-/OWASP-Mapping-Dokumente.

## 9. Offene Abnahme-Fragen an Lars

1. Schema: Extension `standards-alignment/v1` (Empfehlung §2.1) — bestätigt, oder doch Top-Level `complianceAnchors`?
2. IMDA MGF als 6. Eintrag aufnehmen (Empfehlung §2.4) — bestätigt?
3. SoT-Klärung §0.1: Option A (Reconcile in moltrust-web) oder B (kanonisch am Live-Ort)?
4. FATF/MITRE/OWASP-Mapping-Docs als Folge-BACKLOG-Item — bestätigt?
