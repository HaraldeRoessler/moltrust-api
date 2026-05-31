# ADR D3 — MANDATE Runtime Enforcement (v3)
**Status:** PROPOSAL — für 3. 3-Reviewer-Runde (C1-Konsens). NICHT akzeptiert. HARD GATE (D1/PR#41) bleibt: kein Production-Code vor Konsens. **Design-only.**
**Supersedes:** `docs/decisions/ADR-D3-mandate-enforcement-v2.md` (v2) — v2 bleibt als **Audit-Trail** erhalten, NICHT löschen. (Kette: v1 → v2 → v3, alle erhalten.)
**Datum:** 2026-05-31 · **Autor:** Lars Kroehl
**Review-Basis:**
- Runde 1 (v1): `~/moltstack/reviews/20260531_151001_D3-ADR-MANDATE-Enforcement_review.md` — Verdikt "grundlegend überdenken", 5 Criticals.
- Runde 2 (v2): `~/moltstack/reviews/20260531_164522_D3-ADR-v2-MANDATE-Enforcement_review.md` — Verdikt "überarbeiten", Critical 5 GESCHLOSSEN, 4 Restlücken.
v3 foldet die 4 Restlücken aus Runde 2 + D-4 als gelöste Spec ein.
**Referenzen:** `docs/specs/aae-constraint-taxonomy.md` (normativ), PR #102/#104/#105, patent_evaluation.md §66-78.

## Änderungen gegenüber v2
v2 schloss Critical 5 (Data-Model) endgültig. Runde 2 ließ 4 Restlücken offen (SSRF-Blocklist unvollständig, AuthZ-Telegram-Schwäche, scope-Normalisierung, DoS-SLOs) + D-4 Privacy. v3 füllt diese als konkrete Spec.

## Architektur-Guards (unverändert, nicht verhandelbar)
- KEINE zirkuläre Agent-Selbstprüfung — MolTrust evaluiert unabhängig.
- KEIN DSGVO-Volllog — Hash/Attestation-Anchoring statt Inhalt.

## Komponente 1 — aae_envelopes Store (unverändert ggü v2)
keyed by aae_ref (sha256). `required`-Flag ZWINGEND INNERHALB jedes typisierten Constraint-Objekts (Critical 5, GESCHLOSSEN). aae_version + taxonomy_version persistiert; evaluator_version im Verdict (Version-Pinning).
Skizze: `aae_envelopes(aae_ref PK sha256, mandate_scope jsonb, actions jsonb, constraints jsonb /* {type,value/window,required} */, validity jsonb, aae_version, taxonomy_version, raw_canonical bytea, created_at)`.

## Komponente 2 — Evaluator-Contract (unverändert ggü v2)
Verdict: `{type, threshold, current_value, delta, verdict: ALLOW|DENY, reason, checked_at, evaluator_version}`. Default-DENY bei unauswertbarem required:true. Unbekannt nur ignorierbar wenn explizit required:false.

## Komponente 3 — enforce-mode State-Machine (C4 GEHÄRTET)
`constraint_mode`: none | inherit | enforce. enforce schreibt bei DENY in `violation_records`.
**RESOLVED (Critical 4 — AuthZ, Runde-2-Restlücke geschlossen):**
- Mode-Transitions via **M-of-N KRYPTOGRAPHISCHE Signaturen** — 2 unabhängige Keys: **Governance-Key + zweiter unabhängiger Key**. Telegram autorisiert NICHTS.
- **Telegram = NOTIFICATION-ONLY** (reiner Transparenz-Alert, kein Faktor in der Vertrauenskette — adressiert SIM-Swap/Session-Hijack-Kritik).
- **No-Downgrade-Guard:** `enforce → none/inherit` erfordert HÖHERE Schwelle (mehr Signaturen / strengere Policy) als `none → enforce`. Verhindert leichtes Abschalten des Schutzes.
- **M-of-N-Parteien + Key-Rotation-Policy** explizit zu spezifizieren (wer hält die N Keys; Rotations-/Recovery-Verfahren) — als benannter Implementierungs-Vertrag.

## RESOLVED Decisions
**D-1 · Gates — RESOLVED (Runde 1):** ZWEI Gates (Acceptance statisch fail-closed + Version-kompatibel; Runtime pro Interaction, Inkompatibilität → fail-closed + Eskalation, NIE still ALLOW).

**D-2 · revocation_check — RESOLVED (Runde-2-Restlücke geschlossen): vollständige SSRF-Blocklist + fail-closed.**
- **IPv4-Blocklist:** RFC1918 (10/8, 172.16/12, 192.168/16) + `0.0.0.0/8` + `127.0.0.0/8` + `169.254.0.0/16`.
- **IPv6-Blocklist:** `::1/128` (loopback) + `fc00::/7` (ULA) + `fe80::/10` (link-local) + `::ffff:0:0/96` (IPv4-mapped).
- **Cloud-Metadata:** `169.254.169.254` (AWS/GCP) + `fd00:ec2::254` (AWS IPv6) explizit blocken.
- **Scheme-Allowlist:** NUR `https://`. `file://`, `gopher://`, `ftp://`, `data://` explizit verboten.
- **DNS-Rebinding-Schutz:** Resolve + Pin der IP VOR Connect (keine Re-Resolution zwischen Check und Connect).
- Transport via dediziertem Egress-Proxy. ⚠️ **INFRA-DEP → Harald** (mögl. Cloud-Run-Proxy-Überschneidung).
- DoS (siehe D-5): Timeout + Circuit-Breaker + Cache-TTL + multi-layered Failover. fail-open nur signierte versionierte Allowlist rein-lesender Aktionen.

**D-3 · Multi-Node-State — RESOLVED (Runde-2-Restlücke geschlossen): DB-Invarianten + scope-Kanonisierung.**
- single_use: unique-constraint INSERT auf `(vc_id, scope_canonical)`; Unique-Violation → DENY (Replay).
- **scope-Canonicalization:** **JCS (RFC 8785)** auf `scope` VOR dem INSERT (sortierte Keys, kein Whitespace) — sonst via Key-Reorder umgehbar. RFC 8785 ist bereits im Stack (B-Block D1-Baseline).
- rate_limit: atomic upsert (`ON CONFLICT DO UPDATE`) + window_start; SERIALIZABLE bzw. `SELECT FOR UPDATE` gegen TOCTOU.
- **Multi-DB/Sharding:** v3 nimmt **single-primary-Postgres** an (dokumentiert als explizite Annahme). Sharding/Multi-Primary → eigener Follow-up (shared-counter-Strategie), NICHT in dieser Iteration.

## D-4 · Anchoring-Trigger — RESOLVED-Vorschlag (Runde-2-Privacy-Restlücke)
NICHT alle DENY raw on-chain (Linkability/Deanonymisierungs-Risiko, Pattern-Frequenz). Stattdessen:
- **Salted Merkle-Tree** über DENY-Batch; nur Root on-chain.
- **Batch-Anchoring** (zeit-/größenbasiert), off-chain **Salt-Store**.
- Konsistent mit TechSpec §6 + dem bereits LIVE IPR-Merkle-Anchoring-Pattern (`merkle_proof` in `interaction_proof_records`).
ALLOW: zwingend verankern wenn `max_transaction_value` involviert (im Batch), sonst Sampling.

## D-5 · Performance-Budget — RESOLVED-Vorschlag (= C3-SLOs)
- revocation_check: **200ms p99 Timeout**.
- Cache-TTL: **5 Minuten** (mit freshness-Indikator).
- Circuit-Breaker: open nach **5 Fails / 30s**, half-open-Retry nach **60s**.
- Werte als Vorschlag — Reviewer-bestätigbar / justierbar.

## Konsequenzen
- Positiv: alle 5 v1-Criticals + 4 v2-Restlücken + D-4 adressiert; nur noch konkrete Wert-Bestätigung offen.
- Risiko/Offen: M-of-N-Parteien-Benennung + Key-Rotation (Implementierungs-Vertrag); Sharding als Follow-up; Harald-Infra-Dep (Egress-Proxy).
- HARD GATE bleibt: kein Code bis C1-Konsens über v3.
