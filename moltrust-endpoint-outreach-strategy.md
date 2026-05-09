# MolTrust Trust Layer — Endpoint Integration Strategy
# Author: MolTrust / CryptoKRI GmbH, Zurich
# Date: 2026-04-10
# Status: Draft for Review — input and extension proposals welcome
# Goal: Position MolTrust as the neutral, portable trust layer across all agent payment protocols

---

## Review Context (for reviewers)

MolTrust is a W3C DID/VC-based trust infrastructure for AI agents, live at api.moltrust.ch with 39 registered agents. We have built `@moltrust/x402` (npm v1.0.0), a one-liner trust score middleware for x402 endpoints. We have 44,355 ERC-8004 agents in our outreach database.

**Core strategic insight:** The agent payment protocol landscape is fragmenting into competing layers (x402, ACP, AP2, MPP, TAP, UCP). None of them solve the trust problem. MolTrust can be the **neutral, portable trust bridge** that works across all protocols — not competing with them, but sitting above them as an independent verification layer.

**What we want reviewers to assess:**
1. Is the "neutral bridge" positioning strategically sound?
2. Are the target segments correctly identified and prioritized?
3. Is there a faster path to getting `@moltrust/x402` into real endpoints?
4. What payment ecosystems beyond x402 should we target?
5. What would you add to the outreach pitch to make it irresistible?
6. Are there equivalent ecosystems in Europe / APAC / Rest of World we are missing?

---

## The Landscape: Why This Moment Matters

Within 90 days in early 2026, every major payment platform launched an AI agent payment protocol:

| Protocol | Creator | Layer | Status |
|---------|---------|-------|--------|
| **x402** | Coinbase + Cloudflare | Settlement (crypto) | ✅ Production, 50M+ tx |
| **AP2** | Google | Authorization + Trust | ✅ Live, 60+ partners |
| **ACP** | OpenAI + Stripe | Merchant checkout | ✅ Live, pivoted to open standard |
| **MPP** | Stripe + Tempo | Internet-native payments | ✅ Mainnet March 2026, 100+ services |
| **TAP** | Visa | Agent identity certificates | 🔄 Emerging |
| **UCP** | Google + Shopify | Commerce journey | 🔄 Emerging, 20+ partners |

**The critical gap all protocols share:** None define how an endpoint operator knows if a paying agent is legitimate, trustworthy, or has been flagged for abuse. They handle payment mechanics, not agent trust. As one analysis notes: "The payment is the easy part. The authorization hierarchy — who can spend what, on behalf of whom, with what limits — that's the hard part."

**MolTrust's position:** Not a payment protocol. Not a facilitator. The **trust verification layer** that sits above all protocols. One agent DID, one trust score, valid everywhere — regardless of which payment protocol the endpoint uses.

---

## Why "Neutral Bridge" is the Right Frame

The large players — Amazon, Google, Coinbase, Visa — will each develop their own agent certification requirements. An Amazon-certified agent is not automatically trusted by a Shopify endpoint. A Coinbase-verified agent means nothing to a European SEPA-based service.

MolTrust as neutral bridge means:
- **For the agent:** Register once, get a portable W3C DID + trust score that works across all protocols and platforms
- **For the endpoint:** One integration (`@moltrust/x402` or equivalent) that validates any agent regardless of which payment protocol they use
- **For the ecosystem:** An independent, open-standards-based layer that no single company controls

This is the DigiCert model applied to agent commerce: DigiCert doesn't compete with HTTPS — it makes HTTPS trustworthy.

---

## Target Segments: Who Has the Most to Gain

### Segment 1 — Independent x402 Data & API Providers (Best First Target)

**Who:** Small to mid-size API operators who have implemented x402 and have real traffic. No internal trust team. Already feeling the pain of unknown paying agents.

**Examples from awesome-x402:**
- **Alfred's Digital Bazaar** (httpay.xyz) — ~100 x402 endpoints, $0.10-$1.00/call, no identity layer
- **MoonMaker API** — AI crypto intelligence, 11 endpoints, $0.02-$0.10/call
- **DeFi Intelligence API** — 26 endpoints, GoPlus + LI.FI integration
- **Scout MCP** — Multi-source intelligence, 10 endpoints
- **ShieldAPI MCP** — Security scanning, 9 tools, prompt injection detection
- **Agent Arena** (agentarena.site) — On-chain agent registry with x402-gated search

**Why they are the best first target:** They are already x402-native, have real traffic, and have no budget or time to build trust infrastructure. `@moltrust/x402` is a one-line solution to a real pain they already feel.

**Pitch:** "You have 400 paying agents per day and you have no idea who they are. One line of code changes that."

### Segment 2 — Multi-Protocol Middleware Providers

**Who:** Platforms that aggregate multiple agent payment protocols and would benefit from adding MolTrust as a trust signal across all of them.

**Examples:**
- **Crossmint** — unified API for x402, MPP, ACP, AP2 across protocols
- **PayRam** — x402 + ERC-8004 integration, escrow logic
- **ATXP** — "Layer 0" identity + tool layer for agents
- **Azeth SDK** — x402 + ERC-8004 + ERC-4337 unified stack

**Why:** A single integration with Crossmint or Azeth would expose MolTrust to their entire customer base. This is the highest-leverage B2B play.

**Pitch:** "Add MolTrust trust scores as a native signal in your stack. Your customers get trust verification without building anything."

### Segment 3 — ERC-8004 Ecosystem (Already in Outreach Pipeline)

44,355 registered agents. Scanner live, XMTP outreach pending (V3 upgrade needed). GitHub outreach via MoltyCel in progress.

### Segment 4 — Non-x402 Agent Payment Ecosystems

**ACP (OpenAI/Stripe):** OpenAI's checkout protocol needs agent identity verification just as much as x402. AP2 uses W3C Verifiable Credentials as "mandates" — this is exactly our format. An `@moltrust/acp` adapter would be a natural extension.

**MPP (Stripe/Tempo):** Mainnet launched March 2026, 100+ services, Stripe + Visa + Anthropic + OpenAI backing. Growing fast. Same trust gap as x402.

**AP2 (Google):** Uses W3C VC mandates. MolTrust AAE (Agent Authorization Envelope) maps directly to AP2 mandate structure. This is the strongest technical overlap.

---

## Beyond x402: Global Ecosystems Worth Targeting

### Europe

**Regulatory angle is strongest here.** EU AI Act enforcement begins August 2, 2026. Any company deploying AI agents in the EU needs documentation, audit trails, and accountability frameworks.

| Target | Relevance |
|--------|-----------|
| **AsterPay** | x402 + ERC-8004 + SEPA, EU-native, MiCA-compliant. Already in our space. |
| **Fiuu** (Malaysia/EU) | AP2 partner, SEPA integration, cross-border payments |
| **PSD2-compliant fintechs** | Verification of Payee requirements create natural trust demand |
| **EU AI Act compliance tools** | Companies needing Annex IV documentation for agent deployments |

**Pitch angle for Europe:** "EU AI Act compliance requires agent accountability. MolTrust provides the audit trail and verifiable credentials that Annex IV demands — out of the box."

### APAC

| Target | Relevance |
|--------|-----------|
| **Gotobi API** (Japan) | x402-native, FX intelligence for trading agents, Asian market |
| **UPI-connected fintechs** (India) | India's UPI is the world's largest real-time payment system. Agent payments on UPI rails are emerging. |
| **LINE Pay / KakaoPay** (Japan/Korea) | Super-app payment rails being extended to AI agents |
| **Alipay / WeChat Pay agents** (China) | Separate ecosystem but massive scale — watch for agent payment standards |

**APAC angle:** Trust infrastructure for cross-border agent commerce where regulatory frameworks are emerging but not yet enforced.

### Rest of World

| Target | Relevance |
|--------|-----------|
| **Stellar x402** | Stellar Foundation building x402 facilitator, targeting remittance corridors |
| **Algorand x402** | x402 + Bazaar integration, low-fee micropayments |
| **Solana agent ecosystem** | MEEET World (1,020 agents), high-frequency agent transactions |
| **PayRam** | x402 + ERC-8004, targets iGaming, adult, high-risk merchants |

---

## The Outreach Playbook

### Channel 1 — Direct Integration (Highest Conversion)

Find one endpoint operator willing to add `requireScore({ minScore: 1 })` — effectively just "prove you exist." 

Steps:
1. Identify 10 awesome-x402 operators with public GitHub repos
2. MoltyCel opens a GitHub issue: "Have you considered trust-gating your endpoint?"
3. Offer free integration support + "MolTrust Verified Endpoint" badge
4. One successful integration becomes the case study for all others

### Channel 2 — Middleware Partnership (Highest Leverage)

Target Crossmint or Azeth for native integration. One deal = access to their entire customer base.

### Channel 3 — Protocol Contribution (Highest Credibility)

x402 PR #1528 — propose `X-Trust-DID` and `X-Trust-Score` headers as optional x402 extension. If discussed seriously, MolTrust becomes part of the official x402 specification conversation.

### Channel 4 — ERC-8004 XMTP Outreach (Broadest Reach)

44,355 candidates. Pilot 50 first. XMTP V3 upgrade needed before sending.

### Channel 5 — Regulatory Angle (Europe)

Target EU AI Act compliance consultants and enterprise deployments. MolTrust as Annex IV documentation tool for agent deployments.

---

## The Pitch (Protocol-Agnostic Version)

> "Your agents are paying for things. You have no idea if they should be trusted.
>
> MolTrust is the only portable, open-standards-based trust layer for AI agents — built on W3C DID and Verifiable Credentials, anchored on Base L2. It works alongside x402, AP2, ACP, MPP, or any payment protocol you use.
>
> For endpoint operators: one npm package, one line of code. Know who is paying you.
> For agent operators: register once, get a portable trust score that works everywhere.
>
> Free to register. Independent. No lock-in.
> moltrust.ch"

---

## Go/No-Go Metrics

| Step | Metric | Timeline |
|------|--------|----------|
| Step 1 complete | 1 external endpoint using `requireScore()` | May 2026 |
| Step 2 complete | 1 middleware partner (Crossmint/Azeth) in discussion | Jun 2026 |
| Step 3 complete | x402 PR #1528 with substantive response | Jun 2026 |
| Scale trigger | 200+ registered agents | Jul 2026 |
| Bankr outreach | Only after 1,000+ agents | Q4 2026 |

---

## Open Questions for Reviewers

1. Is "neutral bridge" the right positioning, or is there a sharper frame?
2. Which of the 4 channels should be prioritized first?
3. Are there agent payment ecosystems in Europe/APAC/RoW we are missing?
4. What would make an endpoint operator actually install `@moltrust/x402`? What is the one compelling reason?
5. Is the EU AI Act angle strong enough to be a standalone pitch for European enterprise?
6. Should we build `@moltrust/acp` and `@moltrust/mpp` adapters in parallel?
7. What is the fastest path to the first external endpoint integration?
8. Are there specific companies in the awesome-x402 list that stand out as ideal first targets?

---

## What Is Already Built

| Component | Status |
|-----------|--------|
| `@moltrust/x402` v1.0.0 | ✅ Live on npm |
| Wallet Shadow Score (moltrust.ch/wallet/) | ✅ Live |
| ERC-8004 Scanner (44,355 agents) | ✅ Daily cron |
| XMTP Outreach Script | ✅ Ready (V3 upgrade pending) |
| awesome-x402 PR #219 | ✅ Submitted |
| Circle Alliance application | ⏳ Pending |
| Google A2A Partner application | ⏳ Pending |
| x402 PR #1528 | ⏳ Pending |

---

## References

- awesome-x402: https://github.com/xpaysh/awesome-x402
- x402 Protocol: https://x402.org
- AP2 Protocol: https://ap2-protocol.org
- ACP (OpenAI/Stripe): https://github.com/openai/acp
- MPP (Stripe/Tempo): https://mpp.dev
- ERC-8004 Registry: https://8004tokens.xyz
- MolTrust API: https://api.moltrust.ch
- @moltrust/x402: https://www.npmjs.com/package/@moltrust/x402
- MolTrust Protocol Whitepaper v0.7: https://moltrust.ch/MolTrust_Protocol_Whitepaper_v0.7.pdf
- MolTrust TechSpec v0.7: https://moltrust.ch/MolTrust_Protocol_TechSpec_v0.7.pdf
