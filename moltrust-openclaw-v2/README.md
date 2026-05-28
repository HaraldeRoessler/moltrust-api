# @moltrust/openclaw-plugin v2

> W3C DID trust verification + lifecycle gating for [OpenClaw](https://openclaw.ai)

v2 adds the four lifecycle hooks the OpenClaw core already exposes (per
`openclaw/openclaw#49971` close-comment) — `before_install`,
`before_tool_call`, `inbound_claim`, `gateway_start` — on top of the v1
agent tools / slash commands / gateway RPC / CLI surface.

> **Preview release.** v2.0.0-alpha.x is a public preview, not a Production
> Trust-Gating release. See *Security Posture & Roadmap* below for the
> v2.1 hardening list.

## Install

```bash
openclaw plugins install @moltrust/openclaw-plugin
```

Restart your gateway.

## What's new in v2

| Hook | What it gates |
|---|---|
| `before_install` | Plugin / skill installs against `installAllowlist` / `installBlocklist` |
| `before_tool_call` | Sensitive tool calls (default: `pay_*`, `transfer_*`, `x402_*`, `agent_call_*`) — blocks if own agent or any DID in params is below `minTrustScore` |
| `inbound_claim` | Inbound messages — replies with a warning when sender DID is below `minTrustScore` |
| `gateway_start` | Connectivity probe + optional self-verify |

All hooks are **opt-in by default** (`minTrustScore: 0` = no-op). Set a
non-zero threshold (e.g. `50`) to activate gating.

New tool: `moltrust_endorse` — issue a SkillEndorsementCredential (W3C VC,
90-day) for another agent, posting to `POST /skill/endorse`.

## Configuration

```json
{
  "plugins": {
    "entries": {
      "moltrust": {
        "enabled": true,
        "config": {
          "apiKey": "mt_live_...",
          "minTrustScore": 50,
          "agentDid": "did:moltrust:your-agent",
          "verifyOnStart": true,
          "sensitivePrefixes": ["pay_", "transfer_", "x402_", "agent_call_"],
          "gateAllTools": false,
          "installAllowlist": [],
          "installBlocklist": [],
          "cacheTtlMs": 10000,
          "failOpen": false
        }
      }
    }
  }
}
```

Get an API key at [api.moltrust.ch/auth/signup](https://api.moltrust.ch/auth/signup).

## Architecture

```
src/
├── openclaw-types.ts     vendored OpenClaw plugin SDK types (subset, range 0.9.x–1.0.x)
├── client.ts             MolTrustClient + LRU cache (10 s TTL default)
├── utils.ts              extractDids / isLikelyDid
├── hooks/
│   ├── before-install.ts     makeBeforeInstallHandler({cfg, logger})
│   ├── before-tool-call.ts   makeBeforeToolCallHandler({cfg, client, logger})
│   ├── inbound-claim.ts      makeInboundClaimHandler({cfg, client, logger})
│   └── gateway-start.ts      makeGatewayStartHandler({cfg, client, logger})
└── index.ts              wires hooks + v1 tools/commands/RPC/CLI
```

Each hook handler uses a factory pattern (`makeXxxHandler(deps)`) so it's
unit-testable without an OpenClaw host.

## Tests

```bash
npm install
npm test       # vitest — hooks + client (>= 27 tests)
npm run build  # produces dist/*.js + *.d.ts
```

## Security Posture & Roadmap

### Fail-closed by default (v2.0.0-alpha.1)

When a MolTrust API lookup fails (network, rate-limit, 5xx), `before_tool_call`
and `inbound_claim` **block the call/inbound** with a clear `blockReason`
mentioning `failOpen=false`. This is the default — safe for Production
Trust-Gating.

Opt-in fail-open is available via `failOpen: true` for fleets where
availability matters more than trust-gating (e.g. internal dev environments,
non-financial tools). Set it explicitly and monitor the warn-log.

### Response signature verification — planned for v2.1

This release does **not** verify the Ed25519 JWS signatures that
`api.moltrust.ch` returns on trust-score and verify responses (kid
`moltrust-registry-2026-v1`). It trusts HTTPS + JSON parsing.

In MITM-capable environments (Corporate-Proxy with custom CA, routing
manipulation, compromised edge node) an attacker could forge ALLOW/DENY
decisions. The fail-closed default mitigates the most common attack path
("API unreachable, fall through"), but does not stop active in-line
manipulation.

JWS verification is on the v2.1 roadmap as a dedicated design sprint
(JWKS bootstrap, key rotation, failure-mode spec). See [ADR
0001](../docs/decisions/0001-openclaw-jws-response-verification-deferred.md)
in the parent MolTrust API repo for the full reasoning.

### Cache TTL

Default `cacheTtlMs: 10000` (10 seconds). Tunes revocation latency vs.
API-call volume. Lower it to 0 to disable caching entirely; raise it only
if your `minTrustScore` threshold is well above the worst-case score of any
agent you'd permit (i.e. cache cannot mask a decision flip).

### OpenClaw version range

The plugin vendors a subset of OpenClaw's plugin SDK types
(`src/openclaw-types.ts`) pinned to the upstream signature baseline at
commit `45146913007d` (tested range: 0.9.x – 1.0.x). On host versions
outside this range the hook contracts may diverge silently. Bump-and-test
when upstream cuts a breaking minor.

## Privacy & Data Handling

This plugin sends agent DIDs and (optionally) wallet addresses to
`api.moltrust.ch` for trust-score lookups. Specifically:

- **`before_tool_call`** sends your `agentDid` plus any DIDs found in the
  tool call's `params` (via `did:*` regex on string values).
- **`inbound_claim`** sends the sender DID extracted from
  `event.metadata.did` or `event.senderId`.
- **`gateway_start`** sends `agentDid` only if `verifyOnStart: true`.
- The `moltrust_verify` / `moltrust_trust_score` / `moltrust_endorse` tools
  send whichever DID/address the calling agent passes as the argument.

**Endpoint:** `https://api.moltrust.ch` (configurable via `apiUrl` —
self-hosting documented separately).

**Retention:** the MolTrust service stores trust-score lookups per the
operator's privacy policy at [moltrust.ch/privacy](https://moltrust.ch/privacy)
(MolTrust as data processor; you remain controller for your fleet's DIDs).

**Disabling:** set `minTrustScore: 0` and `verifyOnStart: false`. The plugin
then makes no outbound calls except when the `moltrust_*` tools are
explicitly invoked.

This is a trust-verification plugin — running it inherently means sending
DIDs to MolTrust. There is no way to gate agents on remote trust scores
without that round-trip. If you need air-gapped trust gating, this plugin
is not the right fit.

## License

MIT © CryptoKRI GmbH (MolTrust), Zurich
