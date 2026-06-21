# Spec Facts — Verified Reference Repository

Each spec relevant to MolTrust gets its own `.md` file here. Memory holds only a reference pointer (see Memory #30).

Files:
- `aae.md` — AAE (draft-kroehl-agentic-trust-aae-00) ✅ VERIFIED
- `aps.md` — APS (source: `draft-pidlisnyi-aps-01` + Zenodo papers) ⚠️ STUB UNVERIFIED

Planned (as needed):
- `x402.md`, `action-ref.md`, `erc-8004.md`, `w3c-vc.md`, `w3c-did.md`

## Workflow

1. Before any public comment that cites a spec (section refs, hash algorithms, normative requirements): fetch the relevant file here and verify against the current source.
2. If facts have changed: update the file first, then write the comment.
3. Each file carries: source URL, verification date, sha256 of source text, section map, key mechanics, and common attribution errors to avoid.
