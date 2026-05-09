# MolTrust Enterprise — Business Case v0.2
## Überarbeitet nach AI Review (7 Reviewer, April 2026)

**Status:** Draft v0.2 — bereit für zweiten Review-Durchlauf  
**Datum:** April 2026  
**Autor:** CryptoKRI GmbH / Lars Kroehl  
**Änderungen gegenüber v0.1:** Pricing-Brackets, SLA-Roadmap, Henne-Ei-Lösung, AAE-Terminologie, IMDA-Beleg, Free Tier, Contingency Plan

---

## 1. Was ist MolTrust Enterprise?

MolTrust ist Trust-Infrastruktur für autonome AI Agents: kryptografische Identität (W3C DID), Autorisations-Scoping (AAE — Agent Authorization Envelope, MolTrusts Implementierung von W3C Verifiable Credentials für Agent-Autorisierung¹), Verhaltenshistorie (IPR) und On-Chain-Verankerung auf Base L2.

**Enterprise = MolTrust als managed Service** für Unternehmen die AI Agents in Production betreiben und nachweisen müssen:
- Welche Agents handeln in ihrem Namen
- Was diese Agents dürfen und nicht dürfen
- Was diese Agents getan haben (unveränderlicher Audit Trail)

¹ *AAE (Agent Authorization Envelope) ist MolTrusts Bezeichnung für strukturierte W3C Verifiable Credentials die Mandate, Constraints und Validity-Parameter eines Agents maschinenlesbar kapseln. Der Begriff ist MolTrust-spezifisch, nicht W3C-normativ.*

---

## 2. Zielgruppen (ICP)

### Primär: Developer-Teams mit AI Agents in Production
**Wer:** CTOs / Lead Engineers von Startups und Scale-ups die MCP/A2A-basierte Multi-Agent-Systeme betreiben.
**Problem:** Kein Audit Trail, keine nachweisbare Compliance, kein Schutz gegen rogue agents.
**Trigger:** Erster Security Incident, EU AI Act Vorbereitung, Investor Due Diligence.
**Wo finden:** OpenClaw Community, A2A GitHub, MCP Ecosystem, Dev.to.

### Sekundär: Compliance-pflichtige Sektoren
**Wer:** Fintech, Legaltech, Healthcare-AI.
**Problem:** EU AI Act, DSGVO, FINMA, MiFID II verlangen nachvollziehbare Agent-Autorisierung.
**Wo finden:** Bernd (BI), LinkedIn, Compliance-Communities. Vorlaufzeit 6-12 Monate.

### Tertiär: Agent Platforms / Marketplaces (B2B2B)
**Wer:** Amazon Bedrock AgentCore, LangGraph, Coinbase AgentKit.
**Wann:** Nicht Q2 — frühestens wenn erster Case Study vorliegt.

---

## 3. Wie finden uns unsere Kunden?

### Heute (ohne Budget)
1. GitHub Working Groups (A2A, MCP, OpenClaw, qntm, x402)
2. npm / PyPI Downloads
3. Dev.to / Blog (ausbaufähig)
4. A2A v0.3 Agent Card (neu live)
5. Badge-Virality (/badge/{did})
6. Sunil Prakash Outreach (arXiv-Zitation)

### Timeline
- Monat 1-2: Organische Discovery, Free Tier
- Monat 2-3: Erste Developer-Tier Conversions
- Monat 3: aeoess Case Study → Enterprise-Outreach
- Monat 4-6: Startup/Business-Kunden
- Monat 6+: Enterprise-Leads

---

## 4. Pricing

### Tier 1 — Free ($0)
5 DIDs, 5.000 API Calls/mo, 500 Trust Queries. Kein On-Chain, kein SLA.

### Tier 2 — Developer ($29/mo)
25 DIDs, 25.000 Calls, 2.500 Queries, On-Chain ✅, 99% SLA, Email 48h.

### Tier 3 — Startup ($149/mo)
250 DIDs, 150.000 Calls, Custom AAE, MoltGraph, CSV Export, IMDA Report, 99% SLA.

### Tier 4 — Business ($499/mo)
2.500 DIDs, 1M Calls, Unlimited Queries, Falco/K8s, Admin Dashboard, Slack 8h, 99.5% SLA (ab Q3).

### Tier 5 — Enterprise (Brackets)
| API Calls/Monat | Preis |
|---|---|
| bis 5 Mio. | $2.500/mo |
| bis 20 Mio. | $5.000/mo |
| Unlimited | $10.000/mo |

**Founder Deal — First 3 Customers:** $500/mo flat für 6 Monate + Named Case Study + Quarterly Review mit Lars.

---

## 5. Wettbewerber

| Anbieter | Schwäche vs. MolTrust |
|---|---|
| AstraSync | Vendor Lock-in, kein W3C |
| Skyfire | Kein Trust Score, kein Audit Trail |
| Nevermined | Zu komplex, nicht Enterprise-ready |
| Okta/Auth0 | Kein Agent-Kontext |
| AWS Agent Registry | Proprietär — wir = External Catalog |

---

## 6. USP
1. Einzige produktive Referenzimplementierung mit on-chain Anchoring (live März 2026)
2. W3C-Standard statt proprietär
3. Behavioral History on-chain — akkumuliert, unveränderlich
4. Schweizer Infrastruktur (CryptoKRI GmbH, Zürich)
5. First known IMDA MGF implementation (https://www.imda.gov.sg/..., Mapping: moltrust.ch/imda-mgf)

---

## 7. SLA-Roadmap

| Phase | Wann | Setup | SLA |
|---|---|---|---|
| Phase 1 | Jetzt | Single Node | 99% |
| Phase 2 | Q3 2026 | 2-Node + LB | 99.5% |
| Phase 3 | Q4 2026 | Redis + Horizontal | 99.9% |

Enterprise-Verträge erst ab Phase 2.

---

## 8. Contingency Plan

- <5 Developer-Kunden in Monat 3 → aeoess Case Study priorisieren + Founder Deal bewerben
- <1 Enterprise-Lead in Monat 6 → B2B2B Plattform-Strategie (Circle, Coinbase, Amazon)
- Infra skaliert nicht bis Q3 → Enterprise-Launch verschieben

---

## 9. Offene Fragen für Review

1. Founder Deal $500/mo — zu niedrig/hoch? Abschreckend oder einladend?
2. Enterprise Brackets ($2.5k/$5k/$10k nach API-Vol) — verständlich oder zu komplex?
3. SLA-Roadmap öffentlich zeigen oder nur aktuellen Stand?
4. Free Tier 5 DIDs / 5.000 Calls — ausreichend für PoC?
5. AAE als Terminologie beibehalten oder umbenennen?
