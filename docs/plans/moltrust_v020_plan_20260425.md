# moltrust v0.2.0 — Implementation Plan

**Date:** 2026-04-25
**Driver:** Reply commitment to aeoess on `a2aproject/A2A#1755` ("end of this week / early next week" delivery of `MolTrustResolver` for `aeoess/a2a-compliance-harness`).
**Scope (per #1755 thread):**
- ✅ `did:moltrust:*` native (with trust-score integration)
- ✅ `did:web:*` covered (W3C-standard client-side resolution)
- ✅ `did:moltrust:ext_*` bridge-resolved + bridge-bug fix on backend
- ❌ `did:agentnexus:` / `did:meeet:` native NOT in scope (handed back honestly to aeoess in reply)

**No coding in this phase.** Plan only.

---

## 1. Audit Findings

### 1.1 Repo state — `MoltyCel/moltrust-sdk`

| Item | State |
|---|---|
| Last push | 2026-03-27 (28 days untouched) |
| Repo language stat | TypeScript primary |
| Python files | `moltrust/{__init__,client,models}.py`, `tests/test_integration.py`, `mcp_server.py`, `examples/{langchain_tool,crewai_guard}.py` |
| pyproject.toml | `setuptools>=68.0`, version `0.1.0`, deps: `httpx>=0.25.0`, requires-python `>=3.9` |
| Public API today | `MolTrust` (sync client), `AsyncMolTrust`, `Agent`, `Credential`, `Reputation`, `VerificationResult`, `MolTrustError` |
| `client.py:resolve(did)` | already exists — `GET /identity/resolve/{did}`, returns raw dict |
| `MolTrustResolver` class | does NOT exist |
| `did:web` handling | NOT present in client |
| `did:moltrust:ext_*` handling | NOT present |
| Test fixtures | live integration test in `tests/test_integration.py`, currently relies on `MOLTRUST_API_KEY` env var (hardcoded test-key in source already redacted to `***REMOVED***`) |
| GitHub workflows | **none** — no `.github/workflows/` directory at all → v0.1.0 was published manually |

### 1.2 PyPI publish setup

- v0.1.0 uploaded 2026-02-19 by `kersten.kroehl@cryptokri.ch` (Lars' personal email) under name `moltrust`
- `moltrust-mcp-server` (separate package) published under `info@moltrust.ch` — likely same PyPI account, second verified email
- **No automated workflow** — Lars used manual `twine upload` for v0.1.0
- Local `~/.pypirc` does NOT exist on this machine (Lars' Mac) — twine credentials must be entered interactively or come from another machine

### 1.3 Server-side resolver code

**`/identity/resolve/{did:path}`** — `app/main.py:1371-1437`
- Special-case: `did == "did:web:api.moltrust.ch"` → returns hardcoded `DID_WEB_DOCUMENT`
- Then: `if DID_PATTERN.match(did)` → DB lookup in `agents` table → builds full DID Document with verificationMethod, authentication, assertionMethod, optional `service` block (PaymentService for wallet-bound agents)
- Then: `if did.startswith("did:web:")` → HTTP 501 "External did:web resolution not yet supported"
- Else: HTTP 400 "Unsupported DID method"

**`/identity/resolve-external/{external_did:path}`** — `app/main.py:1971-2020`
- Validates `did:` prefix + length ≤256
- Queries `did_bridges WHERE external_did = $1`
- If found: returns `{external_did, moltrust_did, chain, bridged_at, document: {...metadata...}}` — but **document does NOT include verificationMethod** (incomplete shape vs `/identity/resolve`)

### 1.4 Bridge-bug root cause

**`DID_PATTERN = re.compile(r"^did:moltrust:[a-f0-9]{16}$")`** at `app/main.py:455`

This regex requires **exactly 16 hex chars** after `did:moltrust:`. Kevin's bridged DID `did:moltrust:ext_516a656bafa39e5c` has `ext_` prefix → 20 chars after `did:moltrust:` → **regex fails** → `/identity/resolve` returns 400 "Unsupported DID method" before ever reaching the DB.

**The DID exists in the `agents` table:**
```
did                              | display_name                | created_at
did:moltrust:ext_516a656bafa39e5c| bridged:agentnexus:z6MkhaXg | 2026-04-22 20:46:48
```

Currently **1 such `ext_*` agent** exists (Kevin's). The same regex blocks at:
- main.py:1378 (resolve)
- main.py:1441 (key endpoint)
- main.py:1498 (verify)
- main.py:2173, 2242 (other consumers)
- main.py:752, 777 (DTO validation)
- main.py:2415 (already has `did:web:` + `did:key:` exception in OR)

**Side-bug:** `did_bridges` table likely **does not contain** Kevin's bridge either (we saw 5 entries: `did:sol:meeet_agent_42`, four `did:aps:...`). Kevin's bridge to `did:agentnexus:z6MkhaXg...` was probably created via `/test-harness/invoke` handshake which writes directly to `agents` but skips `did_bridges`. So `/identity/resolve-external/did:agentnexus:z6MkhaXg...` would also 404 even if we fixed the regex — needs DB row or handshake-also-writes-bridge fix.

### 1.5 `/.well-known/did.json` (self-DID)

✅ `/.well-known/did.json` returns valid W3C DID Document with `@context`, `id=did:web:api.moltrust.ch`, `controller`, `verificationMethod`, `authentication`, `assertionMethod` — works for any did:web client. No fix needed.

---

## 2. Phase 2 — Backend Fixes (moltstack)

### 2.1 File list

| File | Change |
|---|---|
| `/home/moltstack/moltstack/app/main.py` line 455 | Relax `DID_PATTERN` to accept `ext_` prefix |
| `/home/moltstack/moltstack/app/main.py` line 1971-2020 | Enrich `resolve-external` response to include verificationMethod (parity with `/identity/resolve`) |
| `/home/moltstack/moltstack/app/test_harness/routes.py` | When test-harness creates a bridge, also INSERT into `did_bridges` table (currently writes only to `agents`) |
| Optional: `/home/moltstack/moltstack/app/main.py` line 1437 | Promote `did:web:*` external resolution from 501 to actual W3C-standard client-fetch (or leave as 501 if we want to enforce client-side resolution per W3C spec — recommended) |

### 2.2 Patch — DID_PATTERN

**Current** (line 455):
```python
DID_PATTERN = re.compile(r"^did:moltrust:[a-f0-9]{16}$")
```

**Proposed:**
```python
DID_PATTERN = re.compile(r"^did:moltrust:(?:ext_)?[a-f0-9]{16}$")
```

Backwards-compatible: native `did:moltrust:abc...` (16 hex) still matches; bridged `did:moltrust:ext_abc...` (4-char prefix + 16 hex) also matches.

**Validation policy concern:** the same regex is used at:
- `register` / `bridge` endpoints (DTOs at line 752, 777) — should `ext_` be createable via these public endpoints? **No** — `ext_` DIDs are server-issued via test-harness/bridge-handshake, never user-supplied at register-time. → Keep DID_PATTERN as the lenient pattern, but add a separate stricter `NATIVE_DID_PATTERN` for register/create paths.

**Cleanest split:**
```python
# Resolve / verify / endorse — accepts both native and bridged
DID_PATTERN = re.compile(r"^did:moltrust:(?:ext_)?[a-f0-9]{16}$")
# Register / create — rejects bridged form (server creates those)
NATIVE_DID_PATTERN = re.compile(r"^did:moltrust:[a-f0-9]{16}$")
```

Then audit each call site (8 locations total) and assign the appropriate pattern. Conservative: only loosen at line 1378 (resolve) for v0.2.0 minimum, leave others tight.

### 2.3 Patch — `resolve-external` document parity

The existing `/identity/resolve-external` returns a flat metadata blob without `verificationMethod`. To make MolTrustResolver output identical regardless of which endpoint it hit, the `document` block should include the same Ed25519 verificationMethod / authentication / assertionMethod fields that `/identity/resolve` builds.

**Approach:** factor the DID document construction (lines 1378-1437) into `_build_did_document(row)` helper, call from both endpoints.

### 2.4 Patch — test-harness bridge writes

`app/test_harness/routes.py` `/test-harness/invoke` handler currently creates an `ext_*` agent in `agents` but doesn't write `did_bridges`. Add the bridge INSERT. Reproducible test with Kevin's existing `did:moltrust:ext_516a656bafa39e5c`: backfill the bridge row manually, confirm `/identity/resolve-external/did:agentnexus:z6MkhaXg...` then returns the bridged document.

### 2.5 did:web — leave at 501

W3C did:web spec says external did:web is resolved client-side: parse `did:web:domain.com:path` → `https://domain.com/path/did.json`. Server-side proxy is unnecessary and adds rate-limit attack surface. Leave the 501 response intact in `/identity/resolve`. MolTrustResolver Python class handles did:web client-side directly.

### 2.6 Backend deploy

- Edit `app/main.py`, `app/test_harness/routes.py` on server
- `systemctl restart moltstack` (the FastAPI service)
- Smoke test: 4 curls against the 4 DID-method paths, verify endorsement-roundtrip still works

---

## 3. Phase 3 — Python Package (moltrust v0.2.0)

### 3.1 New files

| Path | Purpose |
|---|---|
| `moltrust/resolver.py` | new — `MolTrustResolver` class |
| `moltrust/__init__.py` | extend `__all__` to export `MolTrustResolver`, `DIDDocument`, `ResolutionResult`, `ResolutionError` |
| `moltrust/models.py` | extend — add `DIDDocument`, `ResolutionResult`, `ResolutionError` dataclasses |
| `tests/test_resolver.py` | new — unit + integration tests for resolver |
| `tests/conftest.py` | new — pytest fixtures (env-loaded API key, optional skip-if-no-network) |
| `pyproject.toml` | bump version `0.1.0` → `0.2.0`; pin minimum httpx version; update `Documentation` URL |
| `README.md` | rewrite Python section to be co-equal with TypeScript section; add MolTrustResolver quickstart |
| `CHANGELOG.md` | new — record v0.2.0 changes |
| `.github/workflows/python-publish.yml` | new — automated PyPI publish on tag `v*` (Trusted Publishing / OIDC pattern as in `moltrust-mcp-server`) |
| `.github/workflows/python-test.yml` | new — CI run `pytest` on push/PR for Python 3.10/3.11/3.12 |

### 3.2 `MolTrustResolver` API skeleton (NOT IMPLEMENTED — design only)

```python
# moltrust/resolver.py

from typing import Optional, Protocol
from dataclasses import dataclass

@dataclass
class DIDDocument:
    """W3C DID Document (subset)."""
    id: str
    context: list[str]
    controller: Optional[str]
    verification_method: list[dict]
    authentication: list[str]
    assertion_method: list[str]
    service: list[dict]
    raw: dict  # full document for forward compat

@dataclass
class ResolutionResult:
    """W3C DID Resolution result."""
    did_document: Optional[DIDDocument]
    did_resolution_metadata: dict   # error code, contentType, etc.
    did_document_metadata: dict     # created, updated, version, etc.

class ResolutionError(Exception):
    def __init__(self, code: str, did: str, detail: str = ""):
        self.code = code      # "methodNotSupported" | "notFound" | "invalidDid" | ...
        self.did = did
        self.detail = detail
        super().__init__(f"{code}: {did} ({detail})")

class DIDResolver(Protocol):
    """Protocol matching aeoess/a2a-compliance-harness contract."""
    def resolve(self, did: str) -> DIDDocument: ...

class MolTrustResolver:
    """Resolves did:moltrust:* (native + bridged) and did:web:* via W3C standards.

    Methods supported:
      - did:moltrust:<16hex>          → MolTrust API /identity/resolve
      - did:moltrust:ext_<16hex>      → MolTrust API /identity/resolve (after backend fix)
      - did:web:<domain>[:path...]    → client-side fetch of /.well-known/did.json
                                        per W3C did:web spec — no MolTrust API call

    Methods NOT supported (raises ResolutionError "methodNotSupported"):
      - did:agentnexus:*  (use AgentNexus's own resolver)
      - did:meeet:*       (use MEEET's own resolver)
      - did:key:*         (client-side decode — out of scope, separate package)
      - all other methods
    """

    SUPPORTED_METHODS = {"moltrust", "web"}
    DEFAULT_API_BASE = "https://api.moltrust.ch"

    def __init__(
        self,
        api_base: str = DEFAULT_API_BASE,
        timeout: float = 10.0,
        http_client: Optional["httpx.Client"] = None,
    ): ...

    # Standard DIDResolver Protocol — returns DIDDocument or raises
    def resolve(self, did: str) -> DIDDocument: ...

    # Full W3C resolution — returns ResolutionResult never raises (errors in metadata)
    def resolve_full(self, did: str) -> ResolutionResult: ...

    # async variants
    async def aresolve(self, did: str) -> DIDDocument: ...
    async def aresolve_full(self, did: str) -> ResolutionResult: ...

    # Internals (not public)
    def _resolve_moltrust(self, did: str) -> DIDDocument: ...
    def _resolve_web(self, did: str) -> DIDDocument: ...
    def _parse_did_web(self, did: str) -> str: ...   # → URL of did.json
    def _close(self): ...
    def __enter__(self) / __exit__(self): ...
```

### 3.3 Behavior contract for each method

| Input | Path | Network calls | Returns | Errors |
|---|---|---|---|---|
| `did:moltrust:abc...def` (16 hex) | `_resolve_moltrust` | `GET {api_base}/identity/resolve/{did}` | DIDDocument | `notFound` (404) → ResolutionError |
| `did:moltrust:ext_abc...def` | `_resolve_moltrust` | same as above (after backend fix) | DIDDocument | `notFound` if bridge missing |
| `did:web:api.moltrust.ch` | `_resolve_web` | `GET https://api.moltrust.ch/.well-known/did.json` | DIDDocument | `notFound`/network error |
| `did:web:foo.com:agents:bot` | `_resolve_web` | `GET https://foo.com/agents/bot/did.json` | DIDDocument | per W3C did:web spec |
| `did:agentnexus:...` | (none) | none | raises `ResolutionError("methodNotSupported")` | always |
| `did:meeet:...` | (none) | none | raises `ResolutionError("methodNotSupported")` | always |
| Anything else | (none) | none | raises `ResolutionError("methodNotSupported")` | always |

### 3.4 Test plan

**Unit (`tests/test_resolver.py`, run without network — `pytest tests/test_resolver.py -m "not integration"`):**
- `test_did_web_url_parsing` — `did:web:foo.com` → `https://foo.com/.well-known/did.json`; `did:web:foo.com:bar:baz` → `https://foo.com/bar/baz/did.json`
- `test_unsupported_method_raises` — `did:agentnexus:...`, `did:meeet:...`, `did:key:...`, `did:invalid:...` all raise `methodNotSupported`
- `test_invalid_did_raises` — empty string, missing `did:` prefix, no method, no method-specific-id all raise `invalidDid`

**Integration (`tests/test_resolver.py -m integration` — needs network + `MOLTRUST_API_BASE` env):**
- `test_resolve_moltrust_native_live` — resolve TrustScout `did:moltrust:d34ed796a4dc4698`, assert document has `id`, `verificationMethod` non-empty
- `test_resolve_moltrust_bridged_live` — resolve `did:moltrust:ext_516a656bafa39e5c`, assert bridges resolve cleanly (depends on Phase 2 deploy)
- `test_resolve_did_web_self_live` — resolve `did:web:api.moltrust.ch`, assert document has `id` matching
- `test_resolve_did_web_external_live` — resolve `did:web:w3.org` if reachable (else skip) — proves cross-domain client-fetch works
- `test_resolve_unknown_native_did` — resolve random `did:moltrust:0000000000000000`, expect `notFound`
- `test_async_variants_match_sync` — basic parity check

**Fixture for aeoess' a2a-compliance-harness:**
- `examples/use_with_a2a_compliance_harness.py` — minimal `harness.py + MolTrustResolver` snippet matching aeoess' Protocol example, copy-pasteable for harness consumers

### 3.5 pyproject.toml diff

```diff
 [project]
 name = "moltrust"
-version = "0.1.0"
+version = "0.2.0"
 description = "MolTrust SDK - Trust Layer for the Agent Economy"
 ...
+ classifiers = [
+    "Development Status :: 4 - Beta",
+    "Intended Audience :: Developers",
+    "License :: OSI Approved :: MIT License",
+    "Programming Language :: Python :: 3",
+    "Programming Language :: Python :: 3.10",
+    "Programming Language :: Python :: 3.11",
+    "Programming Language :: Python :: 3.12",
+    "Topic :: Software Development :: Libraries",
+    "Topic :: Security",
+ ]
 dependencies = [
-    "httpx>=0.25.0",
+    "httpx>=0.27.0",
 ]
+
+[project.optional-dependencies]
+test = ["pytest>=7.0", "pytest-asyncio>=0.21"]
```

Plus `[project.urls]` add CHANGELOG and Issues.

### 3.6 README.md changes

Currently README is 90% TypeScript, 10% Python afterthought. Restructure:

- Header: `# moltrust — Python + TypeScript SDK for MolTrust`
- Section 1: **Quickstart (Python)** — new, equal weight to TypeScript section
  - `pip install moltrust`
  - `from moltrust import MolTrust, MolTrustResolver` — **new** Resolver section
  - 3-line resolve example
  - Link to a2a-compliance-harness integration example
- Section 2: **Quickstart (TypeScript)** — kept, lightly updated
- Section 3: **MolTrustResolver API** (Python only — new section) — full method docs, supported DID methods, errors
- Section 4: **MolTrust client API** (existing)
- Section 5: **Examples** (langchain, crewai, a2a-compliance-harness)

### 3.7 CHANGELOG.md (new)

```markdown
# Changelog

## v0.2.0 — 2026-04-?? (target: end of week)

### Added
- `MolTrustResolver` class for W3C-compliant DID resolution
  - `did:moltrust:*` native (incl. bridged `ext_*` form, requires backend ≥1.4)
  - `did:web:*` via W3C-standard client-side fetch
- `DIDDocument`, `ResolutionResult`, `ResolutionError` dataclasses
- Async variants: `aresolve()`, `aresolve_full()`
- pytest test suite (unit + integration)
- GitHub Actions CI for Python 3.10/3.11/3.12
- GitHub Actions Trusted Publishing workflow

### Changed
- README restructured — Python and TypeScript sections co-equal
- Bumped `httpx` minimum to 0.27.0

### Backend dependency
- v0.2.0 of this package expects MolTrust API ≥ 1.4.0 (which fixes the
  `did:moltrust:ext_*` resolution bug). Earlier API versions return 400 for
  bridged DIDs but native resolution still works.
```

### 3.8 Publish workflow — `.github/workflows/python-publish.yml`

Mirror the `moltrust-mcp-server` pattern (per MEMORY.md: "PyPI publish workflow: push tag v* triggers build + upload (trusted publishing/OIDC)").

Trigger: `on: push: tags: [v*]`
Steps: checkout → setup-python → build via `python -m build` → publish via `pypa/gh-action-pypi-publish@release/v1` (Trusted Publishing, no API token needed if PyPI account is configured).

**Pre-req:** Trusted Publishing must be configured in PyPI for the `moltrust` project (separate from `moltrust-mcp-server`). One-time setup at https://pypi.org/manage/project/moltrust/settings/publishing/ — needs Lars to log into PyPI and add the repo (`MoltyCel/moltrust-sdk` + workflow filename).

---

## 4. Sequence + dependencies

```
Phase 2 (Backend)              Phase 3 (Python package)
─────────────────              ────────────────────────
DID_PATTERN regex relax    →   blocks: integration test 'bridged DID'
↓                              ↓
test-harness bridge writes →   blocks: bridge resolves through resolve-external
↓                              ↓
resolve-external doc parity →  blocks: same DIDDocument shape from both paths
↓
moltstack restart + smoke test
                               
                               Then in any order:
                               • resolver.py + tests
                               • README rewrite
                               • CHANGELOG
                               • pyproject bump
                               • .github/workflows
                               
                               Finally:
                               • Configure PyPI Trusted Publishing
                               • git tag v0.2.0 → CI → PyPI

                               Then in #1755 reply:
                               • Confirm Protocol shape
                               • Honest scope: did:moltrust + did:web only
                               • Accept co-maintainer invite (which account?)
```

### 4.1 Open question — co-maintainer account

aeoess will invite a GitHub account as `aeoess/a2a-compliance-harness` co-maintainer. Options:

1. **MoltyCel** — current default, but recently active in many threads, suspension-risk pattern (cf. VCOne)
2. **Lars personal** — clearest accountability, but ties his real identity to bot-activity
3. **Dedicated `moltrust-bot` account** — cleanest, requires new PyPI/GitHub identity setup before merge

Recommend: **Lars personal** for v0.2.0, since this is a low-bot-activity collaboration repo. If MolTrust later automates contributions to it, switch to dedicated bot then.

### 4.2 Time estimate (rough, for Lars to plan)

| Phase | Effort |
|---|---|
| 2.2 DID_PATTERN regex + test | 30 min |
| 2.3 resolve-external doc parity | 60 min |
| 2.4 test-harness bridge writes | 60 min |
| 2.6 deploy + smoke test | 30 min |
| Phase 2 total | **~3h** |
| 3.1-3.3 resolver.py + models | 90 min |
| 3.4 tests (unit + integration) | 90 min |
| 3.5-3.6 pyproject + README | 60 min |
| 3.8 GitHub workflows + PyPI Trusted Publishing | 60 min |
| First publish + #1755 reply | 30 min |
| Phase 3 total | **~5.5h** |
| **Grand total** | **~8.5h, fits in 1 working day** |

---

## 5. Risks + mitigations

| Risk | Mitigation |
|---|---|
| DID_PATTERN regex change breaks endorsements | Pattern stays superset of original — all 16-hex DIDs continue matching. Run endorsement integration test after deploy. |
| moltstack restart drops in-flight requests | Coordinated restart during low-traffic window (~03:00 UTC), or rolling if behind nginx |
| PyPI Trusted Publishing setup blocks publish | Fallback: manual `twine upload` like v0.1.0 — Lars enters PyPI password once |
| aeoess' v0.1 harness lands before our v0.2.0 publish | Inline-snippet in #1755 reply (resolver code as gist) so harness can integrate without waiting on PyPI |
| `did:web` cross-origin resolution hits CORS or rate-limits | httpx makes server-to-server calls, no browser CORS. Per-domain rate-limit risk is theoretical — caller's responsibility, not resolver-internal. |
| Backwards-compat break for moltrust v0.1.0 users | None — `MolTrust` client class API unchanged. Only additive. |

---

## 6. Out-of-scope (explicit)

- did:agentnexus / did:meeet native resolvers — these are AgentNexus's and MEEET's domain
- did:key client-side decoder — separate concern, would belong in different package (~50 LOC, multibase + JWK construction)
- did:moltrust → did:agentnexus reverse-bridge lookup — not needed for the harness use case
- Multi-method resolver chaining / fallback — keep MolTrustResolver focused, harness's `--resolver-config` handles chaining
- Rewriting the existing `MolTrust` client class — only add Resolver, leave client.py alone
- Repository renaming or splitting — moltrust-sdk repo stays as dual-language Python+TypeScript

---

## 7. Verification before going to Phase 2

Before Lars greenlights coding, verify:

- [ ] PyPI Trusted Publishing setup — does Lars want to do this himself or hand off?
- [ ] Co-maintainer GitHub account decision (Lars personal vs MoltyCel vs new account)
- [ ] Restart-window for moltstack — when can we afford 30s API blip?
- [ ] aeoess' harness URL still live and Protocol-shape unchanged (re-fetch a2aproject/A2A#1755 last comment + harness repo HEAD before coding)
- [ ] Backwards-compatibility commitment to v0.1.0 callers — ANY actual users currently? (`pip install moltrust` download stats)

---

_Plan end. Phase 2 / Phase 3 await Lars-OK._
