# 0001 — JWS Response Signature Verification deferred to @moltrust/openclaw-plugin v2.1

**Datum:** 2026-05-28
**Status:** Accepted

## Context

Der §12-Review für `@moltrust/openclaw-plugin@2.0.0-alpha.0` (Run 2026-05-28 16:36 UTC, Output `~/moltstack/reviews/20260528_163640_openclaw-plugin-v2.0.0-alpha.0_review.md`) hat als Blocker #3 (Konsens von Gemini 3.1 Pro Preview + Perplexity Sonar Pro) markiert:

> Keine JWS-Signatur-Verifikation der API-Antworten → MITM-anfällig.

Die MolTrust-API liefert seit CAEP Profile v1 (LIVE 2026-05-09, `kid: moltrust-registry-2026-v1`) Ed25519-signierte Trust-Scores. Der OpenClaw-Plugin-Client (`moltrust-openclaw-v2/src/client.ts`) ruft die Endpoints heute ohne lokale Signatur-Verifikation auf — er vertraut HTTPS + JSON-Parsing.

Risiko bei MITM-Szenarien (Corporate-Proxy mit gefälschten CA-Roots, Routing-Manipulation, kompromittierte Edge-Node): gefälschte ALLOW/DENY-Entscheidungen würden vom Plugin unbeanstandet ausgeführt.

## Decision

Die JWS-Verifikation wird **explizit deferred** auf `@moltrust/openclaw-plugin v2.1`, nicht in v2.0.0-alpha.1 implementiert.

Begründung:

- v2.0.0-alpha.x ist Public-Preview, kein Production-Release. Trust-Threshold ist `0` per Default (opt-in via `minTrustScore`).
- Saubere JWS-Verifikation braucht: (a) öffentlicher Key-Bootstrap-Mechanismus (JWKS-Fetch, Trust-on-First-Use, Pinning?), (b) Rotations-Policy (Plugin muss Key-Rotation der MolTrust-Registry handhaben), (c) Failure-Mode-Spec (Signatur-Mismatch vs Key-not-found vs Clock-Skew). Diese drei Punkte sind eine eigene Design-Spec, kein 1-Sprint-Fix.
- Der gefährlichste Fail-Open-Pfad (Plugin lässt Agents trotz API-Ausfall durch) wird **in v2.0.0-alpha.1** durch Blocker-Fix #1 (`failOpen: false` Default, opt-in) bereits geschlossen — damit ist der primäre MITM-Attack-Surface „API not reachable, fall through" mitigiert. Verbleibende MITM-Surface: aktive Man-in-the-Middle-Manipulation einer eigentlich erreichbaren API-Antwort.

## Consequences

**Positiv:**

- v2.0.0-alpha.1 kann zeitnah re-reviewed und publik gemacht werden (Preview-Status, kein Production-Trust-Gating-Anspruch).
- v2.1-Spec bekommt einen eigenen Sprint mit Design-Review für JWS-Bootstrap, Key-Rotation und Failure-Modes.

**Negativ:**

- Bis v2.1 publiziert ist, müssen Operators in MITM-fähigen Netzwerken (z.B. Corporate-Proxy mit Custom-CA) das Plugin als „ungeeignet für Production-Trust-Gating in solchen Umgebungen" einstufen.
- README muss diesen Trade-off explizit kommunizieren (Section „Security Posture & Roadmap").

**Pflicht-Begleitmaßnahmen für v2.0.0-alpha.1:**

- README-Note: „Response signature verification planned for v2.1 — see ADR 0001"
- ADR-Link aus README erreichbar (Discovery)
- v2.1-Spec als Item in `docs/BACKLOG.md` festhalten (separat von diesem PR)

## Alternatives considered

1. **JWS-Verify in v2.0.0-alpha.1 ad-hoc implementieren** — verworfen: ohne Bootstrap-/Rotations-Spec wird der Plugin selbst zur Angriffsfläche (z.B. Plugin akzeptiert jeden Key beim First-Use ohne Pinning, oder bricht stumm bei Routine-Key-Rotation der Registry).
2. **Public Release blocken bis v2.1 fertig** — verworfen: v2.0.0-alpha.x ist Preview. Realistische Anwender setzen es jetzt zum Testen ein, nicht für Production-Trust-Gating. Veröffentlichung mit klarer Roadmap-Note ist ehrlicher als Stillstand.
3. **Plugin als private (nicht-npm) Package halten bis v2.1** — verworfen: widerspricht dem v2-Ziel (öffentliche OpenClaw-Integration), und die Preview-Phase ist gerade dafür gedacht, dass Early-Adopters Feedback geben.
