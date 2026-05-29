# Audit: API-Versionierung — v1-Contract vs. v2.4

**Datum:** 2026-05-15
**Scope:** Read-only Verifikation. Kein Code-Change, kein Commit, kein Service-Restart.
**Quellen:** live `api.moltrust.ch/openapi.json` + `/health`, server-lokale Sources unter `~/moltstack/app/`, `git log` auf `app/main.py`, `/var/www/html/.well-known/agent-card.json`.
**Auftrag:** Fakten für API-Sprint §5. KEINE Empfehlung — Entscheidung trifft Lars.

---

## V-10 — Woher kommt der String "v2.4" im OAS?

**Status:** ANSWERED.

**Antwort.** `v2.4` ist ein **hardcodierter String-Literal im FastAPI-Konstruktor**, an drei voneinander unabhängigen Stellen dupliziert — keine Single-Source-of-Truth, nicht aus `pyproject.toml`/`setup.cfg`/`app/__init__.py` gelesen.

**Evidenz.**

```
app/main.py:50
app = FastAPI(title="MolTrust API", version="2.4", docs_url=None)
```

Dieser `version=`-Parameter ist die Quelle des `info.version`-Felds in `/openapi.json` (FastAPI generiert das daraus automatisch).

Zusätzlich **manuell dupliziert** in Response-Bodies (NICHT aus dem app-Objekt gelesen):

```
app/main.py:1519     "version": "2.4",     # innerhalb /health-Handler (ab Zeile 1506)
app/main.py:5855     "version": "2.4",     # zweiter Handler-Body
```

`pyproject.toml` / `setup.cfg` / `app/__init__.py`: kein API-Versions-String gefunden (grep ohne Treffer). Es gibt also keinen zentralen Versions-Konstanten — drei separate `"2.4"`-Literals, die bei einem Bump alle einzeln angefasst werden müssten.

---

## V-11 — Gibt es bereits irgendwo eine "v1"-Deklaration?

**Status:** ANSWERED.

**Antwort.** Auf **API-Contract-Ebene existiert KEIN "v1"**. Die einzigen `1.0`/`1.0.0`-Strings im System sind modul- bzw. dokument-skopiert und haben nichts mit der API-Vertragsversion zu tun.

**Evidenz.**

`/openapi.json` info-Block (live):
```json
{ "title": "MolTrust API", "version": "2.4" }
```
→ Kein `v1`. `/health` liefert ebenfalls `version: "2.4"`.

Die drei `1.0*`-Vorkommen, jeweils anderer Scope:

1. **Sports-Modul-Version** — `app/main.py:3608`, im `/sports/health`-Handler:
   ```python
   return {
       "module": "moltrust-sports",
       "version": "1.0.0",
       ...
   }
   ```
   Versioniert das Sports-Submodul, nicht die API.

2. **Agent-Card Dokument-Version** — `/var/www/html/.well-known/agent-card.json`:
   ```
   "version": "1.0"
   "protocolVersion": "1.0"
   ```
   `version` = Agent-Card-Doc-Revision, `protocolVersion` = A2A-Protokoll-Version. Beide unabhängig vom API-Contract.

Kein `/v1`-String im OpenAPI-info-Block, keinem Pricing-/Marketing-Pfad im Code, keiner `.well-known`-Auslieferung als API-Vertragsnummer.

---

## V-12 — Sind URL-Pfade versioniert?

**Status:** ANSWERED.

**Antwort.** **Nein.** 0 von 136 Pfaden tragen ein Versions-Präfix. Konvention ist durchgängig flach/top-level ohne `/v1/`, `/v2/`, `/api/v*`.

**Evidenz.** Aus `/openapi.json` `paths`:
```
total paths: 136
version-prefixed paths (/v1/, /v2/, /api/v): 0
```
Erste Pfade (Stichprobe): `/.well-known/agent-registration.json`, `/.well-known/did.json`, `/a2a/agent-card/{did}`, `/admin/dashboard/*`, … — alle ohne Versions-Segment. Pfad-Konvention ist Domänen-präfixiert (`/identity/`, `/credits/`, `/skill/`, `/swarm/`, `/sports/`, `/a2a/`, `/admin/`, `/.well-known/`), nicht versions-präfixiert.

---

## V-13 — Was sagt die Git-History?

**Status:** PARTIAL.

**Antwort.** Der FastAPI-`version=`-String wurde laut Pickaxe nur im **Initial Commit** (`6c6a892`, 2026-03-10) gesetzt — und zwar initial auf **`"2.6"`**. Der aktuelle HEAD-Wert ist **`"2.4"`**. Es gab also eine **Dekrementierung 2.6 → 2.4** zu einem nicht eindeutig identifizierten Zeitpunkt nach dem Initial-Commit.

**Evidenz.**

```
git log --oneline -S 'version="' -- app/main.py
6c6a892 Initial commit — MolTrust platform

git log -p -S 'version="' -- app/main.py  (gekürzt):
commit 6c6a892  Date: Tue Mar 10 21:04:42 2026
+app = FastAPI(title="MolTrust API", version="2.6", docs_url=None)
```

Aktueller Stand:
```
app/main.py:50  app = FastAPI(title="MolTrust API", version="2.4", docs_url=None)
```

**Warum PARTIAL / Methoden-Limit:** `git log -S 'version="'` ist eine Pickaxe auf die *Anzahl* der String-Vorkommen. Eine reine Wert-Änderung `2.6` → `2.4` ändert die Vorkommen-Anzahl nicht, daher erscheint der Bump-Commit NICHT in diesem Log. Der exakte Commit der Dekrementierung ließe sich nur mit `git log -G'version="2\.' -- app/main.py` oder Pickaxe auf den konkreten Literal-Wert pinnen — bewusst nicht ausgeführt (Scope-Disziplin, war nicht in den Prüfpunkten). Faktum bleibt: Initial `2.6`, aktuell `2.4`, Richtung der Änderung ist **rückwärts** (untypisch für Semver).

Chronologischer Kontext: `app/main.py` hat 30+ commits seit Initial; der `version=`-Bump ist in keinem davon per Pickaxe-Count sichtbar — er passierte als Wert-Edit innerhalb eines Commits, der den String nicht zählungs-wirksam änderte.

---

## Zusammenfassung (ein Satz)

`"v2.4"` ist ein an drei Stellen hardcodierter, aus `2.6` rückwärts-dekrementierter FastAPI-`version=`-String ohne zentrale Quelle (kein pyproject), der via OpenAPI `info.version` nach außen sichtbar wird — ein API-Contract-`"v1"` existiert **nirgends** (die einzigen `1.0`-Strings sind Sports-Modul-Version, Agent-Card-Doc-Version und A2A-`protocolVersion`), und URL-Pfade sind komplett unversioniert (0/136).
