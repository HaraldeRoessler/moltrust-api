# Spec — V1.4-1: AAE ins Credential einbetten (9 Sektionen, WORKFLOW §1.3)

**Status:** ENTWURF — **SECURITY-KRITISCH** (Credential-/Auth-Pfad). **Cross-Review §2.3 PFLICHT vor Code** (WORKFLOW §2.3). KEIN Code vor Freigabe + Auflösung der blockierenden Open Decisions (§9).
**Datum:** 2026-05-18 · **Repo:** moltrust-api · **Branch:** docs/v141-aae-credential-spec
**Quelle:** Phase-1-Analyse UNC-07 (Lars-Entscheidung „API erweitern") + V1.4-1-Auftrag. State-Check (§2.1) gegen `main` nach PR #34/#35.
**Sequenz:** NACH Idempotency-Foundation (PR #34, gemerged). Beide berühren `/identity/register`.

## 1. Goal
`POST /identity/register` (und der Credential-Ausstellungspfad) so erweitern, dass das ausgestellte `AgentTrustCredential` den **AAE-Envelope (MANDATE / CONSTRAINTS / VALIDITY)** trägt — damit die (heute auf moltrust.ch entschärfte) Aussage „every credential embeds an AAE" wahr wird. Bestehender `POST /delegation/configure`-Pfad bleibt voll funktional (Backwards-Compat).

## 2. Non-Goals
- Kein Umbau der Idempotency-Foundation (PR #34); kein §9.2-global (eigenes BACKLOG, PR #35).
- Kein Bruch von `/delegation/configure` / `agent_delegation_config` / Delegations-Chain (`aae_id`).
- **Keine Erfindung eines AAE-Schemas** — die autoritative Struktur ist Voraussetzung, nicht Teil dieser Spec (siehe §9 D1, blockierend).

## 3. Architecture-Layer-Scope *(WORKFLOW-Pflichtfeld)*
- **API/Handler:** `register_agent` (`app/main.py:973`, Credential entsteht bei **`:996`** via `issue_credential(agent_did,"AgentTrustCredential",{…})`); `app/credentials.py:issue_credential` (Builder/Signer).
- **Signatur:** `issue_credential` signiert `json.dumps(credential, sort_keys=True)` über die **gesamte** `credentialSubject` (Ed25519Signature2020). → Ein AAE-Block in den `claims` wird **automatisch mitsigniert** (sauberer Integrationspunkt, verifiziert).
- **DB:** `credentials` (raw_vc JSON) — AAE landet in `raw_vc`. Evtl. Bezug zu `agent_delegation_config` (verifiziert: Spalten `delegation_permitted,max_depth,constraint_mode` — **NICHT** MANDATE/CONSTRAINTS/VALIDITY) und `aae_id` (Chain-Referenz). Reconciliation = offene Frage (§9 D3).
- **NICHT betroffen:** Credit-/Idempotency-Middleware-Layer (Begründung §6/§9 D-Interaktion), moltrust-web (Folge-Nachzug separat), Free-Tier.

## 4. Data-Model-Changes
- Primär: **kein** neues Schema — der AAE-Envelope wird Teil der `credentialSubject` (in `claims` an `issue_credential`), persistiert in `credentials.raw_vc` (bestehende Spalte). Form abhängig von D1.
- Offen (D3): ob ein separater AAE-Store / Verknüpfung mit `agent_delegation_config`/`aae_id` nötig ist — **nicht raten**, blockierend.

## 5. API-Contract-Changes
- Response von `POST /identity/register`: `credentialSubject` enthält zusätzlich den AAE-Envelope. Exakte Felder = D1 (autoritatives Schema).
- `POST /delegation/configure`: unverändert funktional; **offene Frage D3**: löst ein späterer `configure`-Call eine Credential-**Neuausstellung** mit aktualisiertem AAE aus, oder bleibt das ausgestellte Credential statisch und `configure` wirkt nur auf die Delegations-Chain? Nicht raten.
- Kein Pflicht-Parameter neu; kein Breaking Change am Request.

## 6. Migration-Path
- **Interaktion mit Idempotency-Foundation (präzise, verifiziert — nicht geraten):** `credit_middleware` behandelt `/identity/register` als **bedingten** Bypass: `app/main.py:530-531` — *unregistrierter* Erstaufruf (kein `caller_did`) ⇒ `call_next` ohne Charge ⇒ der **keyed Idempotency-Pfad greift NICHT** (er aktiviert nur auf dem charged Pfad). `ENDPOINT_COSTS["POST /identity/register"]=1` ⇒ ein **Re-Register durch einen bereits verknüpften Agent** wird charged ⇒ keyed Idempotency-Pfad *kann* greifen. AAE-Einbettung ist **Handler-Layer**, Idempotency ist **Middleware-Layer** → weitgehend orthogonal; sie treffen sich nur am Pfad-String. Im charged Re-Register-Replay-Fall würde eine wiedergegebene Antwort konsistent dasselbe (AAE-tragende) Credential des Erstlaufs liefern — unkritisch. **Kein Konflikt identifiziert; falls Cross-Review eine Wechselwirkung sieht → nachschärfen.**
- **Bereits ohne embedded AAE ausgestellte Credentials** *(Instruktion an dieser Stelle abgeschnitten — NICHT geraten, als Entscheidung geführt, §9 D4):* Optionen: (a) Grandfather (Altbestand bleibt AAE-los bis natürlicher Ablauf/Expiry 365 d), (b) Lazy-Reissue bei nächstem relevanten Call, (c) Batch-Reissue. Trade-offs in §9 D4; Lars entscheidet.

## 7. Rollback-Plan
- Code-Rollback: `issue_credential`/`register_agent` auf Vorstand — neue Registrierungen wieder AAE-los; bereits mit AAE ausgestellte Credentials bleiben gültig (additiv, signiert). Kein Daten-Rollback nötig (append-only `credentials`).
- `/delegation/configure` war nie verändert → kein Rollback dort.

## 8. Success-Criteria
1. Frische `POST /identity/register`-Response: `credentialSubject` enthält den AAE-Envelope gemäß autoritativem Schema (D1); Signatur deckt den AAE-Block (Verify-Roundtrip grün).
2. `/delegation/configure` unverändert funktional (Regressions-frei).
3. Delegations-Chain (`aae_id`, `agent_delegation_config`) unbeeinträchtigt.
4. moltrust.ch-Aussage „embeds an AAE" wird **erst nach** Merge wahr (Seiten-Nachzug separat).
5. Idempotency-Foundation unbeeinträchtigt (Re-Register-Replay liefert konsistentes AAE-Credential).

## 9. Open Decisions — teils BLOCKIEREND

**D1 [BLOCKIEREND] Autoritatives AAE-Envelope-Schema fehlt server-seitig.** State-Check verifiziert: **nirgends** in `app/` eine MANDATE/CONSTRAINTS/VALIDITY-Schemadefinition. Vorhanden nur: `agent_delegation_config` (delegation_permitted/max_depth/constraint_mode — *Delegations-Kontrolle, nicht der Envelope*), `aae_id` (Chain-Referenz), Doku-Referenzen (`@moltrust/aae` npm v0.5, Protocol-WP, moltrust-v08-patch-notes „L2 AAE: MANDATE+CONSTRAINTS+VALIDITY"). **Implementierung unmöglich, bis das autoritative Schema entschieden ist** (Quelle: `@moltrust/aae` v0.5 / Protocol-WP — von Lars zu bestätigen, **nicht von dieser Spec erfunden**).
**D2 [BLOCKIEREND] AAE eines frisch registrierten Agents.** Beim Register existiert noch **kein** Mandat. Optionen: (a) leeres/Default-Skelett (alle Felder „none"/leer, später via configure befüllt), (b) Einbettung erst nach erstem `/delegation/configure` + Reissue. Produktentscheidung Lars.
**D3 [BLOCKIEREND] Reconciliation mit `/delegation/configure`+`agent_delegation_config`+`aae_id`.** Trägt das Credential einen statischen AAE-Snapshot oder löst `configure` eine Reissue aus? Wie verhält sich der eingebettete Envelope zur bestehenden Delegations-Chain-Maschinerie? Nicht raten.
**D4 [HOCH] Migration Altbestand AAE-loser Credentials** (Instruktion abgeschnitten): Grandfather vs. Lazy-Reissue vs. Batch — Lars entscheidet (§6).
**D5 [HOCH] WORKFLOW §3.3** Multi-Layer + security-kritisch ⇒ nach Schema-Klärung (D1) Architecture-Brief + Lars-Approval **vor** Implementierung; **kein** Solo-LLM-Coding (WORKFLOW §8).

---
**Cross-Review §2.3 (PFLICHT, security-kritisch):** Diese Spec geht vor jeglichem Code durch den Multi-AI-Cross-Review (gefixtes ai_review.py, ehrlich seit PR #33). Ergebnis als Appendix; ≥1 Iteration. **Hinweis:** D1–D3 sind blockierend — diese Spec ist eine *Decision-/Architektur-Spec*, die die Blocker sauber freilegt, **nicht** implementierungsreif bis D1–D3 entschieden.

---

## Appendix A — Cross-Review §2.3 (2026-05-18, security mode) + Iteration

**Durchführung:** `ai_review.py` (GPT-4o + Gemini 2.5 + Perplexity → Claude-Synthese), ehrlich seit PR #33 (EXIT 0 = echter Erfolg), Modus **security**. Report: `reviews/20260518_114259_v141-aae-spec-xreview_review.md`.

**Verdikt: ÜBERARBEITEN / NICHT implementierungsreif.** Konsens aller drei Reviewer bestätigt: D1 (fehlendes AAE-Schema), D2 (Initial-Defaults), D3 (Reconciliation) sind **blockierend** und security-relevant (Schema-Mismatch/Injection, Privilege-Escalation durch veraltete AAE-Snapshots). Stärken bestätigt (Security-Kennzeichnung, Ed25519-Signatur über `credentialSubject` inkl. AAE, Append-only, transparente Blocker-Offenlegung, Backwards-Compat). Cross-Review bestätigt damit: diese Spec ist korrekt eine *Decision-Spec*, **kein** Code bevor D1–D3 + die folgenden neuen Security-Punkte entschieden sind.

**Neu eingearbeitet — zusätzliche blockierende/Security-Anforderungen (Konsens):**
- **D6 [BLOCKIEREND, Security] Revocation/Freshness.** Ein eingebetteter AAE-Snapshot darf nach Delegations-Entzug nicht weiter „gültig" sein (Gemini+Perplexity: Privilege-Escalation). Erfordert Credential-Status/Revocation-Mechanismus **oder** verbindliche Freshness-Regel (D3-gekoppelt). Vor Code zu lösen.
- **D7 [BLOCKIEREND, Security] Secure-by-Default für D2.** Default-AAE eines frisch registrierten Agents MUSS restriktiv sein („keine Berechtigungen", nicht „alle"). Macht D2 zur Security-Entscheidung, nicht nur Produkt.
- **D8 [HOCH, Security] Signatur-Canonicalization.** `issue_credential` signiert `json.dumps(sort_keys=True)` — Perplexity: bekannte CVE-Fläche bei JSON-LD/`Ed25519Signature2020`-Canonicalization. Vor Code: JCS (RFC 8785) oder formell definierte Canonicalization festlegen/prüfen.
- **D4 verschärft:** Grandfathering als Migration **vermeiden** (Downgrade-Angriffe); Lazy- oder Batch-Reissue bevorzugen. Endentscheidung Lars.
- **Idempotency-Cross-Ref (Divergenz aufgelöst — Perplexity Recht, aber bereits adressiert):** Cross-User-Replay-Sorge ist real; die gemergte Idempotency-Foundation (PR #34) bindet den Key bereits an `(agent_did, endpoint_key, idem_key)` — `agent_did` = Auth-Kontext. Für den charged Re-Register-Fall damit abgedeckt; explizit als Verifikationspunkt notiert, nicht offen.
- **Standards (MITTEL):** vor Code W3C VC 2.0, JCS/JSON-LD-Security, NIST SP 800-57/800-63, OWASP API Top 10 referenzieren (D1/D8-Kontext).

**Nächster Pflicht-Schritt (WORKFLOW):** D1–D3 + D6/D7 sind **Produkt-/Schema-Entscheidungen für Lars**. Erst danach: §3.3 Architecture-Brief + Lars-Approval, dann **erneuter** Cross-Review des konkreten Designs (security-kritisch), dann Code. **Solo-LLM-Coding verboten (§8).** Diese Spec geht NICHT in Implementierung über, solange die Blocker offen sind.
