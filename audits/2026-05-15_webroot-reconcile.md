# Webroot ↔ moltrust-web Reconcile-Audit

**Datum:** 2026-05-15 · **Typ:** Read-only Inventory · **Scope:** `/var/www/html/` ↔ `~/moltrust-web` (Website-Files; ohne `.git/ docs/ scripts/ .github/`)
**Webroot-Clone:** eingefroren auf `56b511b` (2026-04-23 10:39) · **Repo-HEAD:** `13c4554` (2026-05-15, nach PR #1+#2)
**Methodik:** sha256-Join pro relpath; Klassen A/B/C/D; mtime↔Repo-Commit-Forensik; Sensitive-Scan.
**Hinweis Audit-Integrität:** erste Parser-Version strippte führende `.` (→ `.well-known/*` falsch in A/B). Korrigiert, Zahlen unten sind die bereinigten.

## §1 Zusammenfassung
| Klasse | Bedeutung | Anzahl |
|---|---|--:|
| A | Server-only (nicht im Repo) | 21 |
| B | Repo-only (nicht auf Server) | 1 |
| C | beide, identisch (in-sync) | 58 |
| D | beide, divergent | 83 |
| (extra) | Server-`.bak`-Artefakte (manuelle On-Server-Backups) | 117 |

Webroot-Content-Files: 162 · Repo-Website-Files: 142 · Union: 163
D-Klassifikation: {'Deploy-Lag': 1, 'Server-Edit': 81, 'KONFLIKT': 1}

## §2 Klasse A — Server-only (21)
Content nur live, **nie ins Repo zurück**. Verdacht: server-seitig erstellt nach dem 2026-04-23-Import.

| Datei | Größe | mtime |
|---|--:|---|
| `aip-conformance-preprint-v1.pdf` | 24100 | 2026-04-23 |
| `api-llms.txt` | 6048 | 2026-05-10 |
| `api-robots.txt` | 1839 | 2026-05-08 |
| `arxiv-preprint-v1.9.pdf` | 407539 | 2026-04-23 |
| `bindings/trust-registry/v1.html` | 11424 | 2026-05-10 |
| `blog/aws-agent-authorization-identity-gap.html` | 20453 | 2026-05-06 |
| `blog/paris-weather-polymarket-manipulation.html` | 35066 | 2026-04-29 |
| `blog/trust-as-a-plugin-openclaw.html` | 30960 | 2026-05-06 |
| `developers.html.backup-2026-05-15-pre-PR2` | 65346 | 2026-05-06 |
| `hackathon.html.broken-20260417-205758` | 38893 | 2026-04-17 |
| `index.html.pre-seo-backup` | 37849 | 2026-02-22 |
| `index.html.trouvart` | 127420 | 2026-02-28 |
| `index.nginx-debian.html` | 1772 | 2026-04-23 |
| `publications/eu-ai-act-mapping.pdf` | 114914 | 2026-04-23 |
| `publications/index.html` | 25476 | 2026-05-09 |
| `publications/integrity.html` | 29467 | 2026-05-09 |
| `publications/nist-ai-rmf-mapping.pdf` | 124843 | 2026-04-23 |
| `publications/sybil-resistance-methodology.pdf` | 261336 | 2026-04-23 |
| `trouvart/feed_full.json` | 48624572 | 2026-03-21 |
| `trouvart/feed_top.json` | 3425830 | 2026-03-21 |
| `trouvart/trouvart_feed.json` | 52050392 | 2026-03-21 |

## §3 Klasse B — Repo-only (1)
Im Repo, **nicht** im Webroot. Verdacht: nie deployed, oder server-seitig umbenannt/ersetzt.

| Datei | Größe | Repo-Commit |
|---|--:|---|
| `blog/registry-sprawl.html` | 29606 | 2026-04-23T10:39:11Z |

> `blog/registry-sprawl.html` (Repo) entspricht server-seitig vermutlich `blog/registry-sprawl-agent-sprawl.html` (umbenannt, siehe Klasse A) — manuell prüfen.

## §4 Klasse C — in-sync (58)
sha256 identisch, keine Aktion.

`.well-known/a2a, .well-known/erc8004.json, .well-known/jwks.json, MolTrust_KYA_Whitepaper.pdf, MolTrust_KYA_Whitepaper_v1.pdf, MolTrust_KYA_Whitepaper_v2_backup.pdf, MolTrust_KYA_Whitepaper_v3.1.pdf, MolTrust_Protocol_TechSpec_v0.2.2.pdf, MolTrust_Protocol_TechSpec_v0.3.pdf, MolTrust_Protocol_TechSpec_v0.4.pdf, MolTrust_Protocol_TechSpec_v0.5.pdf, MolTrust_Protocol_TechSpec_v0.6.pdf, MolTrust_Protocol_TechSpec_v0.7.pdf, MolTrust_Protocol_TechSpec_v0.8.pdf, MolTrust_Protocol_Whitepaper_v0.4.pdf, MolTrust_Protocol_Whitepaper_v0.5.pdf, MolTrust_Protocol_Whitepaper_v0.6.1.pdf, MolTrust_Protocol_Whitepaper_v0.6.2.pdf, MolTrust_Protocol_Whitepaper_v0.6.pdf, MolTrust_Protocol_Whitepaper_v0.7.pdf, MolTrust_Protocol_Whitepaper_v0.8.pdf, MolTrust_Swarm_Intelligence_Whitepaper_v4.pdf, README.md, admin/index.html, apple-touch-icon.png, assets/js/site-search.js, blog/feed.xml, blog/og-blog.png, favicon-16x16.png, favicon-32x32.png, favicon.ico, favicon.svg, google5c32f1cff2da75eb.html, harness.html, img/mascot.svg, img/moltrust-logo.png, img/moltrust-mascot.svg, img/og/og-blog.png, img/og/og-default.png, img/og/og-integrity.png, img/og/og-moltguard.png, img/og/og-prediction.png, img/og/og-shopping.png, img/og/og-skills.png, img/og/og-sports.png, img/og/og-travel.png, img/team/bi.jpg, img/team/hr.jpg, img/team/kk.jpg, og-image-v2.png, og-image-v3.png, og-image.png, papers/concept_voice_agent_trust.pdf, test/SKILL-malicious.md, test/SKILL.md, trouvart/index.html, verify/index.html, wallet.html`

## §5 Klasse D — divergent (83)
Diff-Statistik (Zeilen nur-Server `<` / nur-Repo `>`), mtime↔Commit-Forensik, Klassifikation.

| Datei | srv-only Z. | repo-only Z. | srv mtime | repo commit | Klassifikation |
|---|--:|--:|---|---|---|
| `.gitignore` | 0 | 25 | 2026-04-23 | 2026-05-15 | Deploy-Lag -> deploy repo->server |
| `.well-known/agent-card.json` | 96 | 28 | 2026-05-10 | 2026-04-23 | Server-Edit -> sync server->repo |
| `CONFORMANCE.md` | 24 | 14 | 2026-05-12 | 2026-04-23 | Server-Edit -> sync server->repo |
| `about.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/a2a-v03-conformance.html` | 2 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/aae-agent-authorization-envelope.html` | 2 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/ai-bot-loses-250k-trust-infrastructure.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/aip-comparison.html` | 1 | 380 | 2026-05-02 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/aip-conformance.html` | 2 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/decentralized-identity-multi-agent-systems.html` | 2 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/erc8004-on-chain-off-chain-agent-trust.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/fake-products-salesguard-agent-commerce.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/fantasy-sports-developer-guide.html` | 2 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/glama-mcp-server-listing.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/hardening-the-moltrust-trust-stack.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/index.html` | 81 | 71 | 2026-05-06 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/internal-only-paradox.html` | 2 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/kernel-level-agent-enforcement.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/kya-whitepaper-know-your-agent.html` | 2 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/malicious-ai-skills-verifiable-identity.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/moltguard-v2-announcement.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/moltid-agent-identity-governance.html` | 2 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/moltrust-openclaw-v1.html` | 2 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/moltrust-protocol-agnostic-trust.html` | 2 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/moltrust-protocol-whitepaper.html` | 2 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/moltrust-sports-fantasy-lineup-verification.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/moltrust-sports-signal-provider-certification.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/moltrust-sports-trust-layer-betting-agents.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/moltrust-vs-aip.html` | 2 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/mt-music-verified-provenance.html` | 2 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/mt-shopping-autonomous-agents-trust-credentials.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/mt-shopping-product-guide.html` | 2 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/mt-skill-verification-350000-skills-zero-trust.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/mt-travel-autonomous-booking-agents-trust.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/openclaw-fake-agents-trust-crisis.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/openclaw-plugin.html` | 2 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/output-provenance-ipr.html` | 2 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/prediction-market-developer-guide.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/prediction-market-wallet-did-bridge.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/registry-sprawl-agent-sprawl.html` | 2 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/rsac-2026-gaps.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/rsac-2026-three-gaps.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/salesguard-developer-guide.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/scanned-50-agent-endpoints.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/shopping-developer-guide.html` | 2 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/signal-provider-developer-guide.html` | 2 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/skill-verification-developer-guide.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/sprint-march-2026.html` | 4 | 6 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/swarm-live-openclaw-scam.html` | 2 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/swarm-phase2.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/techspec-v06-multichain-vcone.html` | 2 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/travel-developer-guide.html` | 2 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/when-agents-replace-buyers.html` | 2 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `blog/who-verifies-the-verifier.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `contact.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `developers.html` | 4 | 5 | 2026-05-15 | 2026-05-15 | KONFLIKT (3-way, manual) |
| `did-method-spec.html` | 1 | 1 | 2026-04-23 | 2026-04-23 | Server-Edit -> sync server->repo |
| `enterprise/index.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `hackathon.html` | 1 | 2 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `impressum.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `index.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `integrity.html` | 8 | 10 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `llms.txt` | 54 | 122 | 2026-05-10 | 2026-04-23 | Server-Edit -> sync server->repo |
| `moltguard.html` | 1395 | 536 | 2026-04-29 | 2026-04-23 | Server-Edit -> sync server->repo |
| `partners/index.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `prediction.html` | 4 | 6 | 2026-05-04 | 2026-04-23 | Server-Edit -> sync server->repo |
| `privacy.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `regulated-markets.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `robots.txt` | 27 | 4 | 2026-05-08 | 2026-04-23 | Server-Edit -> sync server->repo |
| `salesguard-demo.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `salesguard.html` | 4 | 6 | 2026-05-04 | 2026-04-23 | Server-Edit -> sync server->repo |
| `search.html` | 2 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `shopping.html` | 4 | 6 | 2026-05-04 | 2026-04-23 | Server-Edit -> sync server->repo |
| `sitemap.xml` | 352 | 193 | 2026-04-23 | 2026-04-23 | Server-Edit -> sync server->repo |
| `skills.html` | 4 | 6 | 2026-05-04 | 2026-04-23 | Server-Edit -> sync server->repo |
| `sports.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `sustainability.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `terms.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `transparency.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `travel.html` | 4 | 6 | 2026-05-04 | 2026-04-23 | Server-Edit -> sync server->repo |
| `vcone.html` | 2 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `whitepaper.html` | 3 | 5 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |
| `zh/index.html` | 3 | 4 | 2026-04-28 | 2026-04-23 | Server-Edit -> sync server->repo |

## §6 Sensitive-Files-Warnung
Token-/Secret-Pattern-Scan über alle 21 Klasse-A-Server-only-Files (Pattern: `ghp_ sk_live_ whsec_ github_pat_ sk-ant- password= secret= api_key=`): **0 Treffer** — keine Klartext-Secrets in Server-only-Content.
**Hinweise (kein Secret-Inhalt ausgegeben):** `.well-known/` ist **root:root**-owned (nicht www-data) inkl. `agent-card.json` + 3 dated `.bak` (v1-upgrade-Lineage 05-08/09/10). `admin/index.html` ist auth-geschützter Dashboard-Content — vor jedem Sync manuell sichten. 117 `.bak`-Artefakte im Webroot (manuelle Edit-Backups, KEINE Secrets, aber Hygiene/Forensik-Relevanz — z.B. `prediction|salesguard|shopping|skills|travel.html.bak.darkmode.20260504/06` = Darkmode-Arbeit nur server-seitig).

## §7 Reconcile-Empfehlung pro Klasse
- **A (Server-only, 21):** *Server → Repo zurücksyncen.* Live-Content, der im Repo fehlt (u.a. `publications/*`, server-seitige Blog-Posts). Ausnahme vorab manuell: `admin/*`, `.well-known/*`, `trouvart/*` (Daten/Build-Artefakte, evtl. bewusst nicht im Repo).
- **B (Repo-only, 1):** Nur `blog/registry-sprawl.html` — vermutlich server-seitig umbenannt; **manuelle Auflösung** (Rename-Mapping), kein blindes Deploy.
- **C (in-sync, 58):** nichts.
- **D (divergent, 83):** je Klassifikation in §5 — *Server-Edit* → server→repo; *Deploy-Lag* → repo→server; *Konflikt* → 3-way manuell.

## §8 Vorgeschlagene Reconcile-Reihenfolge (Risiko/Wert-priorisiert)
1. **Zuerst — sensible/kanonische Files (manuell, kein Bulk):** `.well-known/agent-card.json` (Klasse D, OD-8 kanonisch, root-owned, server v1-upgrade May-10 vs Repo Apr-23 → **Server-Edit, server→repo**, aber manuell verifizieren) · `.well-known/{a2a,erc8004.json,jwks.json}` (Klasse C — in-sync, nur bestätigen) · `admin/index.html`.
2. **Sichtbare Falschaussagen:** Cross-Check ergab **keine** weiteren Seiten mit INC-09 (`/agents/register`) oder INC-06 (`trust_score:50/grade C`) — der Schritt-1-Surgical-Fix war das einzige Vorkommen. Kein Handlungsbedarf hier.
3. **Hoher Wert — Content-Recovery (Server-Edit, Bulk server→repo):** alle Klasse-A + Klasse-D-`Server-Edit` Blog-Posts & Seiten (Großteil von D ist Server-Edit; Repo ist beim Apr-23-Import eingefroren während Content live gepflegt wurde). `developers.html` Spezial: Hero-Block seit Schritt 1 in-sync; verbleibende D-Diff = die 3 server-only Nav/Footer/OpenClaw-Edits → server→repo.
4. **Zuletzt — Stylistic/Minor:** Darkmode-Varianten (`*.bak.darkmode.*` zeigen: Darkmode existiert live, evtl. nicht im Repo), `robots.txt`/`sitemap.xml`/`llms.txt` (generierte Files — Quelle klären statt blind syncen).

## §9 Risiken / Beobachtungen (kein Eingriff)
- Repo ist KEINE Source-of-Truth: 2026-04-23-Snapshot, seitdem 21 server-only + 83 divergente Files. Reconcile ist substanziell (Schritt 3, eigener Sprint).
- 117 `.bak`-Artefakte: server-seitige Edit-Kultur ohne Repo-Rückfluss; mehrere zeigen Feature-Arbeit nur live (Darkmode 05-04/06, agent-card v1-upgrade 05-10, hackathon js/navcss 04-17).
- Klasse-D-`Konflikt`-Files (beide Seiten seit Base geändert) brauchen echtes 3-way-Merge — Repo-Apr23-Base als Merge-Base nutzbar (Webroot-`.git` hat sie als `56b511b`).
- KEINE Deploy-Pipeline-Empfehlung (Schritt 3, separat — wie beauftragt).

---
*Read-only Audit. Keine Datei in `/var/www/html/` oder `~/moltrust-web` verändert; kein git pull/push/commit/fetch; Webroot-`.git` nur gelesen. Sensible Inhalte nicht ausgegeben.*
