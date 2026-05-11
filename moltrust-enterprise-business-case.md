# MolTrust Enterprise — Business Case v0.1
## Zur Überprüfung durch AI Review Engine (ChatGPT / Gemini / Perplexity)

**Status:** Draft — internes Working Document  
**Datum:** April 2026  
**Autor:** CryptoKRI GmbH / Lars Kroehl  

---

## 1. Was ist MolTrust Enterprise?

MolTrust ist Trust-Infrastruktur für autonome AI Agents: 
kryptografische Identität (W3C DID), Autorisations-Envelopes (AAE), 
Verhaltenshistorie (IPR) und On-Chain-Verankerung auf Base L2.

**Enterprise = MolTrust als managed Service** für Unternehmen die 
AI Agents in Production betreiben und nachweisen müssen:
- Welche Agents handeln in ihrem Namen
- Was diese Agents dürfen und nicht dürfen
- Was diese Agents getan haben (unveränderlicher Audit Trail)

Der Unterschied zur kostenlosen API: SLA, Support, Compliance-Reporting, 
Custom AAE Templates, Audit Export, eigene Branding-Optionen.

---

## 2. Zielgruppen (ICP — Ideal Customer Profile)

### Primär: Developer-Teams mit AI Agents in Production

**Wer:** CTOs / Lead Engineers von Startups und Scale-ups die MCP/A2A-basierte 
Multi-Agent-Systeme betreiben.

**Problem:** Kein Audit Trail, keine nachweisbare Compliance, kein Schutz 
gegen rogue agents.

**Trigger:** Erster Security Incident, EU AI Act Vorbereitung, Investor Due 
Diligence, Enterprise-Kunde fordert Compliance-Nachweis.

**Wo finden:** OpenClaw Community, A2A GitHub, MCP Ecosystem, Dev.to, 
GitHub Working Groups — organisch durch unsere bestehende Präsenz.

### Sekundär: Compliance-pflichtige Sektoren

**Wer:** Fintech, Legaltech, Healthcare-AI — überall wo AI Agents auf 
regulierte Daten oder Transaktionen zugreifen.

**Problem:** EU AI Act, DSGVO, FINMA, MiFID II verlangen nachvollziehbare 
Agent-Autorisierung. Kein Standard-Tool existiert.

**Trigger:** Regulatory Audit, Compliance-Beauftragter blockiert 
AI-Agent-Deployment, Versicherung fordert Nachweis.

### Tertiär: Agent Platforms / Marketplaces (B2B2B)

**Wer:** Plattformen die selbst AI Agents hosten oder vermitteln 
(Bedrock AgentCore, LangGraph, Coinbase AgentKit, zukünftig AWS Agent Registry).

**Problem:** Plattform haftet für Agent-Verhalten ihrer Nutzer. 
Kein eingebettetes Trust-Layer verfügbar.

---

## 3. Wie finden uns unsere Kunden?

### Heute (ohne Budget)

1. **GitHub Working Groups** — A2A, MCP, OpenClaw, qntm, x402-foundation.
2. **npm / PyPI** — @moltrust/sdk, @moltrust/x402, MCP Server.
3. **Dev.to / Blog** — Technical Content über W3C DID, AAE, A2A Conformance.
4. **OpenClaw Plugin** — Viral-Potential wenn OpenClaw-Adoption wächst.
5. **Badge-Endpoint** — /badge/{did} als visueller Trust-Nachweis.
6. **arXiv-Zitationen** — Sunil Prakash zitiert MolTrust.

### Realistische Erwartung

Ohne Paid Marketing: 3-6 Monate bis erste organische zahlende Kunden. 
Developer-Tier kann schneller konvertieren als Enterprise. 
Erstes Ziel: 10 zahlende Developer-Kunden, dann Case Study, dann Enterprise.

---

## 4. Pricing — Vorschlag

| Tier | Preis | DIDs | API Calls/Mo | Trust Queries | On-Chain | SLA |
|------|-------|------|-------------|--------------|---------|-----|
| Free | $0 | 3 | 1.000 | 100 | ❌ | ❌ |
| Developer | $29/mo | 25 | 10.000 | 1.000 | ✅ | 99% |
| Startup | $149/mo | 250 | 100.000 | 10.000 | ✅ | 99.5% |
| Business | $499/mo | 2.500 | 1.000.000 | Unlimited | ✅ | 99.9% |
| Enterprise | On Request | Unlimited | Custom | Custom | ✅ | 99.99% |

Enterprise Richtwert: $2k-$10k/mo. Erste 3 Kunden: $500-1k/mo für Case Study.

---

## 5. Wettbewerber & Benchmark

| Anbieter | Ansatz | Schwäche vs MT |
|---|---|---|
| AstraSync | Proprietär, PDLSS | Vendor Lock-in, kein W3C |
| Skyfire | Payment-Fokus | Kein Trust Score, kein Audit Trail |
| Nevermined | Crypto-native | Zu komplex, kein Enterprise-Ready |
| Ping Identity | IAM für Menschen | Nicht für AI Agents gebaut |
| Okta/Auth0 | OAuth/OIDC | Kein Agent-Kontext |
| AWS Agent Registry | Proprietäres Catalog | Gefahr: External Catalog werden |

---

## 6. USP

1. Einzige produktive Referenzimplementierung mit on-chain Anchoring (live seit März 2026)
2. W3C-Standard statt proprietär — kein Vendor Lock-in
3. Behavioral History on-chain — akkumulierte, unveränderliche Geschichte
4. Schweizer Infrastruktur (CryptoKRI GmbH, Zürich)
5. Weltweit erste IMDA MGF Implementierung

---

## 7. Must-Have für Launch

- ✅ DID Registration / Resolution API (live)
- ✅ Trust Score Query (live)
- ✅ AAE Credential Issuance (live)
- ✅ On-Chain Anchoring (live)
- ✅ Revocation Registry (live)
- 🔲 Admin Dashboard (enterprise.moltrust.ch)
- 🔲 Stripe-Integration
- 🔲 API Key Management (Tier-basiert)
- 🔲 Usage Tracking per Customer
- 🔲 Audit Export (CSV/JSON)

---

## 8. SLAs & ToS

Heute realistisch: 99% (Single Node). Business-Tier: 2-Node + LB nötig.
ToS: Schweizer Recht, kein Adjudikator, DSGVO-konform, DPA auf Anfrage.

---

## 9. Billing & Payment

Stripe → Webhook → API Key Provisioning → Usage Metering → Invoice.
Stripe Customer Portal für Self-Service. USD primär, CHF für CH.

---

## 10. Marketing ohne Budget

Prinzip: Jede technische Aktion ist ein Marketing-Event.
Channels: Dev.to (1x/Woche), GitHub Working Groups, LinkedIn (Lars), Badge-Virality.

---

## 11. Automatisierungsgrad

Ziel: Lars und Bernd <2h/Woche auf Operations.
Alles außer Enterprise-Support vollautomatisch via Stripe.

---

## 12. Offene Fragen

1. Pricing realistisch? $29/$149/$499 für frühe Adoption ohne Case Study?
2. Free Tier: 3 DIDs / 1.000 Calls — zu restriktiv?
3. Enterprise On Request ohne Case Study — glaubwürdig?
4. Henne-Ei: Kein Kunde = kein Case Study. Wie aufbrechen?
5. Single-Node für 99% SLA ausreichend?
6. Stripe vs Chargebee/Lago für DACH?
7. IMDA MGF Claim überprüfbar?
8. Schnellstes Content-Format für Developer-Traffic?
