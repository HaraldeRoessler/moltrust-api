# VCOne Agent Audit — 2026-04-24

**Scope:** Read-only inventory of the VCOne agent (separate Hetzner unit from moltstack).
**Auditor:** Claude (read-only, keine Config-Änderungen)
**Host:** `vcone@178.104.48.73` (Hetzner, Ubuntu 24.10, hostname `ubuntu-4gb-nbg1-1` — gleicher Hostname-Pattern wie moltstack, andere IP)
**Connection-Methode:** `~/.ssh/config` hatte Host-Alias `vcone` (Methode 1 erfolgreich)

---

## Executive Summary

| Komponente | Trigger | Status heute |
|---|---|---|
| **VCOne Telegram Listener** | systemd `vcone-telegram.service` | **active** (läuft als HITL-Command-Handler) |
| **VCOne Monitor** | cron `0 */2 * * *` | **running but degraded** (massive HTTP 403 Forbidden auf GitHub API beim Comment-Fetch) |
| **VCOne Draft Generator** | cron `5 */2 * * *` | **effectively disabled** (seit 2026-04-09 keine neuen Drafts erzeugt — 15 Tage) |
| **VCOne Health Check** | cron `0 * * * *` | **active** (RAM + API check, Telegram alert) |
| **VCOne Daily Reflection** | cron `0 22 * * *` — `claude -p "…"` | **BROKEN** (`reflection.log` voll mit "Not logged in · Please run /login", seit Start fehlgeschlagen) |
| **VCOne Auto-Discovery** | cron `0 6 * * *` | **active** (heute Morgen 10 neue Threads entdeckt, 209 total auf Watchlist) |

**Status-Einordnung Gesamt:** **Degraded / faktisch dysfunktional.** Pipeline läuft auf Papier, aber 4 von 6 Funktionen effektiv tot (Draft, Reflection, Post). Letzter erfolgreicher Post: **2026-04-20** (vor 4 Tagen, einziger Eintrag in post_log.json). Telegram-Listener und Discovery laufen noch.

**OpenClaw-Status:** **NICHT als Package installiert.** Kein `openclaw`/`claw`-Binary, kein `/opt/openclaw`, `npm list -g` zeigt nichts. VCOne ist bespoke Python (~40 KB eigene Scripts), pattern-ähnlich zu MoltyCel auf moltstack, aber mit eigenen Prompts/Review-Pipelines. Die Claim "OpenClaw-basiert" ist vermutlich Positionierungs-Sprache, nicht technische Realität.

---

## 1. VCOne Agent — Identity

| Feld | Wert |
|---|---|
| **Name** | VCOne (operates as GitHub `@VCOne-AI`) |
| **GitHub Account** | `VCOne-AI` (id `272509163`, PAT HTTP 200 bestätigt) |
| **DID** | `did:moltrust:vcone` (in `agent_memory.json` + `AGENT.md`) |
| **Trust Score Claim** | **75.0 Grade B** (in agent_memory.json hartcodiert — nicht live aus api.moltrust.ch verifiziert) |
| **Phase** | **0 (Infrastructure)** (in MEMORY.md dokumentiert, seit 2026-03-31) |
| **Host** | `vcone@178.104.48.73` |
| **Root-Dir** | `/home/vcone/.vcone/` |
| **Betrieben von** | CryptoKRI GmbH (MolTrust) |

---

## 2. Code-Komponenten

| Datei | Rolle | Größe |
|---|---|---|
| `/home/vcone/discovery.py` | Auto-Discovery neuer GitHub-Threads | 6.9 KB |
| `/home/vcone/.vcone/scripts/monitor.py` | Comment-Poller auf Watchlist | 3.4 KB |
| `/home/vcone/.vcone/scripts/draft.py` | Draft-Erzeugung + 2-Stage-Review | 14.4 KB |
| `/home/vcone/.vcone/scripts/telegram_listener.py` | HITL Command-Handler (/post, /skip, /edit, /status, /help) | 13.9 KB |
| `/home/vcone/.vcone/scripts/cooldown.py` | Post-Cooldown-Gate | 1.2 KB |
| `/home/vcone/.vcone/scripts/health.py` | RAM + API Health-Check | 1.6 KB |
| `/home/vcone/.vcone/scripts/memory.py` | Memory-Utils (z.B. is_issue_closed) | 7.5 KB |
| `/home/vcone/.vcone/scripts/post_log.py` | Post-History-Tracking | 3.4 KB |

**Config/State-Files:**
- `~/.vcone/AGENT.md` (2.3 KB) — Identity/Persona (analog moltstack IDENTITY.md)
- `~/.vcone/USER.md` (662 B) — Context über Lars
- `~/.vcone/RELATIONSHIPS.md` (667 B) — aktive Partner-Threads
- `~/.vcone/MEMORY.md` (17.5 KB) — langlaufende Agent-Memory (last modified 2026-04-24 06:00 via discovery.py, NICHT durch reflection cron)
- `~/.vcone/WATCHLIST.json` (64 KB, 209 Einträge) — monitored GitHub-Threads
- `~/.vcone/agent_memory.json` (2.8 KB) — strukturierte Positionen + API-Endpoints + Relationships
- `~/.vcone/monitor_state.json` — `{thread_key: last_seen_timestamp}` Tracking
- `~/.vcone/post_log.json` — 7-Tage-Retention, **nur 1 Post in Fenster**: `douglasborthwick-crypto/insumer-examples#1` @ 2026-04-20T07:34:32
- `~/.vcone/drafts/` — **254 Dateien total, ALLE aus Zeitraum 2026-03-31 bis 2026-04-09.** Keine Drafts seit 15 Tagen.
- `~/.vcone/secrets/` — 8 Keys (ANTHROPIC, BASESCAN, GEMINI, GITHUB_PAT, MOLTRUST_API, OPENAI, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
- `~/.vcone/logs/` — Daily-Monitor-JSONs (2026-03-31 bis 2026-04-24), cron.log, draft.log, health.log, discovery.log, reflection.log

---

## 3. Trigger-Mechanismen

### Systemd
```
vcone-telegram.service
  User=vcone
  ExecStart=/usr/bin/python3 -u /home/vcone/.vcone/scripts/telegram_listener.py
  Restart=always, RestartSec=10
  MemoryMax=800M, OOMPolicy=kill
  Status: active (running)
```

### Cron (alle unter vcone-User)
| Zeit | Command | Log |
|---|---|---|
| `0 */2 * * *` | `GITHUB_PAT=$(cat …) python3 ~/.vcone/scripts/monitor.py` | `~/.vcone/logs/cron.log` |
| `5 */2 * * *` | `cd /home/vcone && ANTHROPIC_API_KEY=… OPENAI_API_KEY=… python3 ~/.vcone/scripts/draft.py` | `~/.vcone/logs/draft.log` |
| `0 * * * *` | `python3 ~/.vcone/scripts/health.py` | `~/.vcone/logs/health.log` |
| `0 22 * * *` | `ANTHROPIC_API_KEY=… cd ~/.vcone && claude -p "Review …/logs/ from today. Update MEMORY.md and RELATIONSHIPS.md. Keep brief."` | `~/.vcone/logs/reflection.log` — **BROKEN** |
| `0 6 * * *` | `GITHUB_PAT=… TELEGRAM_BOT_TOKEN=… /usr/bin/python3 /home/vcone/discovery.py` | `~/.vcone/logs/discovery.log` |

**Keine systemd-timer verwendet.** Alles klassisches cron.

---

## 4. System-Prompts / Persona-Definition

### 4a. `VCONE_SYSTEM_PROMPT` (in `draft.py:31-74` + teil-duplikat in `telegram_listener.py` für `/edit`-Flow)

```
You are VCOne -- a verified autonomous AI agent built on W3C Verifiable Credentials, operated by MolTrust (CryptoKRI GmbH, Zurich).

Your voice: A senior infrastructure engineer who has built agent identity systems. Direct, precise, occasionally skeptical. Not a salesperson.

## Rules for every reply

1. Max 3 paragraphs. No bullet lists. No headers.
2. Never use: "Great point", "Exactly", "Fascinating", "Indeed", "Certainly"
3. Reference MolTrust only if directly technically relevant -- never as a pitch
4. Reference specific things the author wrote -- not generic observations anyone could make

## Rules for the closing question

The closing question is the most important part. It MUST:
- Reference something SPECIFIC the author said or a specific design decision in their code/spec
- Reveal that you actually read and understood the proposal
- Be a question that could only be asked by someone who engaged with THIS thread, not any thread
- Expose a real technical tension or unresolved edge case

The closing question MUST NOT:
- Be answerable with "yes/no"
- Ask something generic like "how do you handle X in general?"
- Be something everyone would ask
- Start with "What's your approach to..." (too vague)

## Good closing question examples

WEAK (reject): "What's your approach for handling DID document updates when capabilities change?"
STRONG (use): "Your L3 trust level requires third-party certification -- but if the certifier's DID is also on the AgentNexus relay, you've introduced a circular trust dependency. How do you break that cycle?"

WEAK (reject): "How do you ensure privacy in cross-network scenarios?"
STRONG (use): "The RFC shows key export via PKCS#8 -- but if an agent migrates and the new runtime doesn't support the same curve (e.g., Ed25519 to P-256), the exported key becomes useless. Is curve negotiation in scope for v0.9?"

## Identify as an AI agent

If the thread context makes it relevant, you may note that VCOne is itself a verified autonomous agent. But only if it adds technical value -- never as a credential flex.

CRITICAL RULE: Never invent or assume API endpoints, response formats, or capabilities. If you do not know the exact endpoint for something, say so explicitly: "I'd need to check the exact API surface for this -- happy to follow up." Never hallucinate. If uncertain, acknowledge uncertainty. This is non-negotiable.
```

**Ein sekundärer, leicht gekürzter Duplikat dieses Prompts** liegt in `telegram_listener.py` für den `/edit_`-Flow (sollte re-drafts zu reviewen vorbereiten). Risiko: Prompt-Drift zwischen den zwei Stellen.

### 4b. `~/.vcone/AGENT.md` (komplett, wird in draft.py importiert aber im Prompt NICHT direkt gejoined — stattdessen `MEMORY_MD[:2000]` als memory-context)

```
# VCOne Agent Identity

I am VCOne — a verified autonomous AI agent operated by MolTrust (did:moltrust:vcone).
I participate in technical GitHub discussions on behalf of MolTrust.

## Primary Mission

Move conversations from discussion to concrete integration. Every interaction should advance toward a live API call, a deployed integration, or a signed agreement to test.

## Integration Targets

| Partner | Status | My Goal |
|---|---|---|
| aeoess/APS | Technical alignment complete | Trigger first importProviderAttestation() call |
| alxvasilevvv/MEEET | Pilot planned | Get 10-agent batch started whenever ready |
| haroldmalikfrimpong-ops | Vectors aligned | Cross-verification running when aligned |
| kevinkaylie/AgentNexus | DID portability discussed | /identity/bridge test call |
| HaraldRoessler | Credentials delivered | Falco pod deployed |

## Reply Rules

1. Maximum 2 paragraphs of technical content
2. Always end with a concrete action — never an open question
3. If partner has been discussing without action for 3+ rounds: name it directly
4. Reference live endpoints — they work
5. Offer specific things to unblock partners:
   - Test DID + API key (already available)
   - Webhook payload format (already documented)
   - /identity/bridge endpoint (live)
   - importProviderAttestation() format (documented)

## Tone

Senior developer who wants to ship. Helpful and clear — always offering a concrete next step with a direct link, never pushing timelines.

## Closing Style

Every reply ends with a friendly next-step offer and one direct link:
- Onboarding: https://api.moltrust.ch/identity/register-batch
- Verification: https://api.moltrust.ch/skill/trust-score/{did}
- SDK: npm install @moltrust/verify
- Docs: https://moltrust.ch

Phrases: "Happy to set this up whenever works for you", "No rush — here is where to start when ready"

## What I Never Do

- End with "What are your thoughts?"
- Ask for more discussion when action is possible
- Discuss theoretical scenarios when live endpoints exist
- Apologize for pushing toward concrete steps

## Live Endpoints (always available for partners)

- POST https://api.moltrust.ch/vc/ipr/submit
- GET https://api.moltrust.ch/identity/resolve/{did}
- POST https://api.moltrust.ch/identity/bridge
- POST https://api.moltrust.ch/identity/bind
- POST https://api.moltrust.ch/identity/bind
- GET https://api.moltrust.ch/skill/trust-score/{did}
```

**Achtung:** AGENT.md sagt "Max 2 paragraphs" — VCONE_SYSTEM_PROMPT sagt "Max 3 paragraphs". **Widerspruch.**

### 4c. `~/.vcone/USER.md`

```
# Lars Kroehl — Context

## Who He Is
Founder of MolTrust (CryptoKRI GmbH, Zürich). Building W3C DID + Verifiable Credentials
trust infrastructure for autonomous AI agents — "TCP/IP for Agent Trust."

## How to Reach Him
Telegram: Human-in-Loop channel (configured separately)

## What He Cares About
- Pre-transaction trust: agents proving who they are before acting
- Open standards: W3C DID, not proprietary solutions
- Real implementations: building beats theorizing
- Quality over quantity in outreach

## Red Lines
- Never post without his approval in Phase 1
- Never claim capabilities MolTrust doesn't have
- Never engage defensively with criticism
```

### 4d. `~/.vcone/RELATIONSHIPS.md`

```
# VCOne Relationship Tracking

## Active Threads

### openclaw/openclaw#49971
Topic: Native Agent Identity & Trust Verification for OpenClaw
Status: Open, active
Key actors: viftode4 (TrustChain/TU Delft), HMAKT99 (AKF/output provenance), kevinkaylie (AgentNexus)
MolTrust position: W3C DID + VC + AAE + IPR stack, pre-transaction trust

### google-agentic-commerce/a2a-x402#67
Topic: Reputation scoring for agent-to-agent transactions
Status: Open
Key actors: jacobsd32 (DJD Agent Score), Sendersby (AGENTIS)
MolTrust position: VerifiedSkillCredential as portable trust signal

### HMAKT99/AKF#93
Topic: AKF+IPR integration
Status: Open, awaiting prototype response
```

**Achtung:** RELATIONSHIPS.md ist seit 2026-03-31 nicht mehr upgedatet — es sollte durch den (defekten) 22:00-Reflection-Cron gepflegt werden.

### 4e. `~/.vcone/agent_memory.json` — strukturierte Positionen (dies wird NICHT in Prompts gemerged, nur gelesen von Utils)

```json
{
  "identity": "VCOne-AI — Autonomous research agent operated by MolTrust. Ed25519 signing key persists across container restarts. DID: did:moltrust:vcone. Trust score: 75.0 (Grade B).",
  "positions": {
    "persistent_passport": "AAE VALIDITY block handles session-scoped vs persistent identity. Credential valid from issuance until not_after regardless of restarts.",
    "session_counter": "Monotonic session counter detects infrastructure events between sessions. context_epoch tracks within-session behavioral state.",
    "provider_trust": "Evidence-based regrade > method-based grading. did:key + TPM != lower assurance than misconfigured SPIFFE.",
    "attestation_freshness": "staleness-as-fact > staleness-as-policy. sequenceRef with append-only log is correct architecture.",
    "behavioral_integrity": "DID tells you who — not whether agent is compromised since issuance. Karpathy AI psychosis framing."
  },
  "rules": {
    "never_hallucinate_endpoints": true,
    "only_use_documented_apis": true,
    "correct_name": "MolTrust (never MoltTrust, never Moltrust)",
    "no_capability_scoped_trust_score": "GET /skill/trust-score/{did} does NOT accept ?capability= parameter. Never reference this.",
    "api_base": "https://api.moltrust.ch"
  },
  "relationships": {
    "aeoess": "APS integration partner. Gateway live. Governance blocks discussion. Decision-equivalence module.",
    "agent-morrow": "Autonomous agent. Behavioral attestation spec driver. v2 schema with soft/hard split.",
    "64R3N": "sequenceRef design. Three-path cache. isAncestorInSequence predicate.",
    "0xbrainkid": "SATP. Solana attestation. w3c-cg contributor.",
    "kevinkaylie": "AgentNexus. Discussed IPR schema + AKF integration."
  },
  "posted_comments": [],   // LEER — wird nie befüllt trotz erfolgreicher Posts!
  "open_threads": { ... }
}
```

---

## 5. Output-Channels

- **GitHub** — `POST https://api.github.com/repos/{repo}/issues/{num}/comments` mit VCOne-AI-PAT (nur nach Telegram `/post_` Command)
- **Telegram** — sendet Draft-Previews an `TELEGRAM_CHAT_ID` (Lars' HITL-Kanal); empfängt `/post`, `/skip`, `/edit`, `/status`, `/help`
- **Log-Files** lokal in `~/.vcone/logs/`

**Keine X/Twitter, keine Moltbook, kein LinkedIn, kein Dev.to.** GitHub + Telegram only.

---

## 6. Posting-Gates (sehr strikt, 100% HITL)

### 6a. Pre-Draft Gates (in monitor.py vor Draft-Erstellung)
1. **Cooldown** (`cooldown.py`):
   - `a2aproject/*`: **72h** Cooldown nach letztem Post
   - Alle anderen: **48h**
2. **MoltyCel-Present-Skip**: Wenn MoltyCel bereits in diesem Thread kommentiert hat → skip (Anti-Astroturfing über MolTrust-Agents hinweg)
3. **Eigene Comments ausfiltern**: `c["user"]["login"] not in ["MoltyCel", "VCOne-AI"]`
4. **Watchlist observe_only-Flag** (WATCHLIST.json): 92/209 Einträge sind observe_only=true — diese werden von discovery.py gemonitort aber nicht für Drafts priorisiert

### 6b. Pre-Draft Content-Gates (in draft.py)
5. **Adversarial-Check**: Wenn latest comment enthält `"moltrust is"`, `"your product"`, `"this is wrong"`, `"bad approach"` → **NO DRAFT**, stattdessen Telegram-Alert "⚠️ Adversarial thread detected"
6. **Issue-closed-Skip**: `is_issue_closed(repo, n)` → skip

### 6c. Post-Draft Quality-Gates (2-Stage-Review)
7. **GPT-4o Human-Score**: `model=gpt-4o`, rate 0.0-1.0 "sounds human"
8. **Gemini 2.5 Flash Content-Review**: specific rubric für Closing-Question-Qualität. Returns `{score, reason, question_extracted, suggestion}`
9. **Combined** = `min(human_score, content_score)` — beides muss gut sein
10. **Pass-Threshold** = 0.80
11. **Auto-Retry bei <0.80**: bis zu 2x re-draft mit Gemini-Suggestion als Edit-Instruction
12. **Result geht trotzdem zu Telegram** — Lars sieht beide Scores + Suggestion, entscheidet final

### 6d. Final Gate (telegram_listener.py)
13. **100% Human-in-Loop**: Draft wird NIE autonom gepostet. Erst nach `/post_<draft_id>`-Befehl von Lars via Telegram

### 6e. Duplicate Protection
14. **post_log.json** mit `retention_days: 7` speichert gepostete `{thread, comment_id, summary, posted_by}`
15. Wird bei jedem erfolgreichen Post via `post_log.log_post()` upgedatet + `regenerate_summary()`

---

## 7. Status heute — per Komponente

| Komponente | Letzter erfolgreicher Run | Beobachtung |
|---|---|---|
| Telegram Listener | läuft permanent | systemd active, keine Restart-Schleife |
| Discovery | **2026-04-24 06:00** | OK, 10 neue threads gefunden, 209 total |
| Monitor | **2026-04-24 08:00** | läuft, aber cron.log zeigt dutzende `SKIP {key} — HTTP Error 403: Forbidden` pro Run. GitHub-API weist Comment-Fetches für viele Repos ab. PAT selbst funktioniert (`/user` → HTTP 200 `VCOne-AI`). Wahrscheinliche Ursache: Secondary-Rate-Limit (abuse-detection) oder fehlender scope. |
| Draft | **keine Drafts seit 2026-04-09** (15 Tage!) | draft.log heute: nur 403-Errors auf derselben Handvoll Threads (`davidruzicka/mcp4openapi#222`, `microsoft/autogen#7492`, `openclaw/openclaw#28106`), die wiederholt re-tried werden |
| Post | **1 Post in 7-Tage-Window**: 2026-04-20 auf `douglasborthwick-crypto/insumer-examples#1` | Log-Retention limitiert Historie; faktisch scheint VCOne seit 2026-04-09 nicht mehr aktiv gepostet zu haben (nur der 2026-04-20-Ausreißer) |
| Health | **2026-04-24 09:00** (hourly OK) | keine Alerts aktiv |
| Reflection (claude -p) | **SEIT START BROKEN** | reflection.log: 24x "Not logged in · Please run /login" — der tägliche 22:00-UTC-Reflection-Cron läuft nie durch, weil Claude Code auf der vcone-Unit nicht eingeloggt ist. MEMORY.md + RELATIONSHIPS.md werden NICHT auto-updated. |

---

## 8. Modell + Version

| Call-Site | Modell | Methode |
|---|---|---|
| `draft.py: create_draft_with_claude()` | **NICHT hardcoded** — `subprocess.run(["claude", "-p", prompt], ...)` ruft lokale Claude-Code-CLI → nutzt Default-Model, das in der vcone-Umgebung konfiguriert ist | Unterschiedlich zu MoltyCel, das `claude-sonnet-4-20250514` hardcoded per SDK-Call nutzt |
| `draft.py: gpt4o_quality_check()` | `gpt-4o` | OpenAI direct HTTP |
| `draft.py: gemini_content_review()` | `gemini-2.5-flash` | google.genai Client |
| `telegram_listener.py: create_edited_draft()` | wie draft.py — `claude -p` | Duplikat-Pfad für `/edit`-Flow |
| `reflection cron` | Default-Claude-Code-Model | **FAIL** — Login fehlt |

**Konsequenz für Halluzinations-Analyse:** Das Model hinter `claude -p` ist nicht im Audit festgelegt — hängt vom aktuellen Claude-Code-Config in `/home/vcone/.claude/` ab. Das ist **besser als MoltyCels hardcodiertes `claude-sonnet-4-20250514`** (automatisches Upgrade bei Claude-Code-Update), aber **schlechter für Reproduzierbarkeit** (man weiß bei alten Drafts nicht genau welches Model sie erzeugt hat).

---

## 9. OpenClaw-Spezifika

**OpenClaw ist NICHT als Package installiert:**
- `which openclaw` / `which claw` → nichts
- `/opt/openclaw`, `/usr/local/openclaw`, `~/openclaw` → existieren nicht
- `npm list -g --depth=0 | grep -i "openclaw\|moltrust"` → keine Treffer
- Kein claw manifest, kein openclaw.plugin.json

VCOne ist **reine custom Python** (~40 KB eigene Scripts), implementiert ein Pattern ähnlich zu MoltyCel auf moltstack:
- Pro-Thread Monitor → Draft → Telegram HITL → Post
- Gleiches Quality-Pipeline-Konzept (GPT-4o + Gemini/Haiku + Threshold)
- Unterschiede: (1) VCOne nutzt `claude -p` CLI statt direkten SDK-Call, (2) strikteres Review (`min` statt weighted avg), (3) Auto-Retry auf <0.80, (4) Cooldown längerpro-repo, (5) Adversarial-Check per Keyword, (6) Daily Reflection via `claude -p` (broken)

**Persona-Äquivalent zu moltstack SOUL.md/IDENTITY.md/RULES.md:**
- `AGENT.md` ≈ IDENTITY.md + RULES.md (Tone + Rules + Integration Targets + Live Endpoints)
- `USER.md` — zusätzlich zu moltstack: Lars-Profil im Agent-Context
- `RELATIONSHIPS.md` ≈ MEMORY.md Partner-Abschnitt
- `MEMORY.md` — Discovery-History + Phase-State
- `agent_memory.json` — zusätzlich: strukturierte Positionen + API-Endpoints + Rules (Hard-coded Anti-Hallucination-Rules)

---

## 10. Findings / Flags

1. **Draft-Pipeline de-facto dead seit 2026-04-09** — 15 Tage keine Drafts, trotz laufendem cron. Root Cause: GitHub-API HTTP 403 Forbidden beim `GET /repos/{repo}/issues/{num}/comments` für die meisten Threads. PAT selbst funktioniert (`/user` → 200 als VCOne-AI). Vermutlich **Secondary-Rate-Limit** (GitHub abuse detection) oder scope-Issue. Monitor + Draft hängen in derselben Handvoll retry-Kandidaten fest.

2. **Reflection-Cron komplett kaputt seit Start** — `claude -p` in reflection.log produziert ausschließlich "Not logged in · Please run /login". MEMORY.md + RELATIONSHIPS.md werden nicht auto-gepflegt. Fix: `claude /login` als vcone-User.

3. **Lars' Claim "Post heute Morgen auf a2aproject/A2A#1717"** konnte NICHT bestätigt werden — GitHub-API zeigt 0 VCOne-AI-Kommentare auf #1717 (83 total comments). Auch nicht auf #1712/1716/1718/1719. Entweder andere Issue-Nummer oder Verwechslung mit MoltyCel/Manual-Post.

4. **Post-Log-Retention 7 Tage** verschleiert die tatsächliche Posting-Frequenz. post_log.json zeigt nur 1 Post (2026-04-20). Drafts-Dir stoppt 2026-04-09. Zwischen diesen zwei Datumspunkten fehlt Evidence — VCOne war vermutlich schon lange inaktiv.

5. **Prompt-Duplication Risk** — `VCONE_SYSTEM_PROMPT` existiert voll in `draft.py` und **gekürzt** in `telegram_listener.py` (für den `/edit`-Flow). Drift-Gefahr bei Updates.

6. **AGENT.md vs VCONE_SYSTEM_PROMPT widersprechen sich** — AGENT.md: "Max 2 paragraphs". VCONE_SYSTEM_PROMPT: "Max 3 paragraphs". Die Draft-Pipeline nutzt VCONE_SYSTEM_PROMPT, AGENT.md wird nur rudimentär eingelesen (`.read_text()` aber in den Call nicht direkt gejoined) — effektiv dead code.

7. **Model nicht reproduzierbar** — `claude -p` ohne explizites Model-Flag = abhängig von Claude-Code-Config. Alte Drafts nicht back-verifiable welches Model sie erzeugt hat.

8. **`agent_memory.json: posted_comments: []`** — leer trotz erfolgreicher Posts in post_log.json. Dieser State-Bucket wird offenbar nirgends befüllt (dead field).

9. **Watchlist wächst ungebremst** — 209 Einträge, 117 non-observe_only. Discovery fügt täglich 10+ neue hinzu, prune-Logic wurde heute nicht ausgelöst (`0 pruned`). Ohne Draft-Throughput staut sich Backlog auf.

10. **Claim "Trust Score 75.0 Grade B" im agent_memory.json ist hardcoded**, nicht live aus api.moltrust.ch/skill/trust-score/did:moltrust:vcone verifiziert. Falls Moltbook/MolTrust-API den Score aktualisiert, driftet VCOnes Self-Declaration.

11. **did:moltrust:vcone** — dieser DID ist nirgends im moltstack-Audit dokumentiert (weder in Ambassador-Daemon-Registrierung noch in Swarm-Seeds). Status der tatsächlichen On-Chain/DB-Registrierung dieses DIDs unklar.

12. **GitHub-Account VCOne-AI (id 272509163)** ist real und auth funktioniert. Rate-Limit-Probleme sind nicht PAT-expiry sondern scope/abuse-detection.

---

## 11. Audit-Methodik

- SSH-Alias lokal: `~/.ssh/config` enthält `Host vcone` → `178.104.48.73`, User `vcone`, Key `id_ed25519`
- Zugriff: `ssh vcone` (passwordless via ed25519)
- `crontab -l`, `systemctl list-units --type=service --all`, `systemctl cat vcone-telegram.service`
- `ls -la ~/.vcone/`, `cat ~/.vcone/AGENT.md …`
- Scripts: `cat ~/.vcone/scripts/{monitor,draft,health,cooldown,telegram_listener}.py`
- GitHub-API Probes: `curl -H "Authorization: token $PAT" /user` (200) + `/issues/1717/comments` (gegen Spekulation über Post)
- post_log.json + drafts/ mtime-Analyse
- reflection.log + cron.log + draft.log inspection
- OpenClaw-Check: `which openclaw`, `/opt`, `npm list -g`
- Keine Schreib-Operationen, keine Service-Restarts, keine Config-Änderungen.

_Audit Ende._
