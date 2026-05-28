/**
 * before_tool_call hook handler.
 *
 * Two checks for sensitive tool calls:
 *   1. own agentDid score (if cfg.agentDid set) >= cfg.minTrustScore
 *   2. counterparty DIDs found in event.params (extracted via did:* regex)
 *      each have score >= cfg.minTrustScore
 *
 * Skipped when:
 *   - toolName starts with "moltrust_" (own tools — avoid recursion)
 *   - toolName not in any cfg.sensitivePrefixes AND cfg.gateAllTools is false
 *   - cfg.minTrustScore <= 0 (opt-in design)
 *
 * Failure mode (lookup errors — network, rate-limit, 5xx): controlled by
 * cfg.failOpen. Default cfg.failOpen=false → fail-CLOSED: block the call
 * with a clear blockReason ("API unreachable"). Opt-in cfg.failOpen=true →
 * warn-log and pass through (legacy v2.0.0-alpha.0 behavior, only for fleets
 * where availability beats trust-gating). See ADR 0001 + README "Security
 * Posture & Roadmap".
 */
import type { MolTrustClient } from "../client.js";
import type {
  BeforeToolCallContext,
  BeforeToolCallEvent,
  BeforeToolCallResult,
  MolTrustConfig,
  OpenClawLogger,
} from "../openclaw-types.js";
import { extractDids } from "../utils.js";

export interface BeforeToolCallDeps {
  cfg: Required<MolTrustConfig>;
  client: Pick<MolTrustClient, "getTrustScore">;
  logger: OpenClawLogger;
}

function isSensitive(
  toolName: string,
  prefixes: string[],
  gateAll: boolean,
): boolean {
  if (gateAll) return true;
  return prefixes.some((p) => toolName.startsWith(p));
}

export function makeBeforeToolCallHandler(deps: BeforeToolCallDeps) {
  const { cfg, client, logger } = deps;

  return async function beforeToolCall(
    event: BeforeToolCallEvent,
    _ctx: BeforeToolCallContext,
  ): Promise<BeforeToolCallResult> {
    const toolName = event.toolName;
    if (!toolName) return undefined;

    // Skip moltrust's own tools — avoid self-recursion
    if (toolName.startsWith("moltrust_")) return undefined;

    if (!isSensitive(toolName, cfg.sensitivePrefixes, cfg.gateAllTools)) {
      return undefined;
    }

    if (cfg.minTrustScore <= 0) return undefined;

    // Check 1: own agent DID
    if (cfg.agentDid) {
      try {
        const own = await client.getTrustScore(cfg.agentDid);
        if (own.score < cfg.minTrustScore) {
          const reason = `[moltrust] tool ${toolName} blocked: own agent ${cfg.agentDid} score ${own.score} < threshold ${cfg.minTrustScore}`;
          logger.warn(reason);
          return { block: true, blockReason: reason };
        }
      } catch (err) {
        const msg = (err as Error).message;
        if (cfg.failOpen) {
          logger.warn(
            `[moltrust] own DID score lookup failed (failOpen=true, allowing): ${msg}`,
          );
        } else {
          const reason = `[moltrust] tool ${toolName} blocked: own DID ${cfg.agentDid} score lookup failed and failOpen=false: ${msg}`;
          logger.warn(reason);
          return { block: true, blockReason: reason };
        }
      }
    }

    // Check 2: counterparty DIDs in params.
    // Lookups run in parallel via Promise.allSettled — sequential await per
    // counterparty was O(N × API-latency) and could add 200ms+ to a 4-DID
    // tool call. Block-priority is deterministic: first counterparty in
    // array order whose result triggers a block wins.
    const counterparties = extractDids(event.params).filter(
      (d) => d !== cfg.agentDid,
    );
    const results = await Promise.allSettled(
      counterparties.map((did) => client.getTrustScore(did)),
    );
    for (let i = 0; i < counterparties.length; i++) {
      const did = counterparties[i];
      const r = results[i];
      if (r.status === "fulfilled") {
        if (r.value.score < cfg.minTrustScore) {
          const reason = `[moltrust] tool ${toolName} blocked: counterparty ${did} score ${r.value.score} < threshold ${cfg.minTrustScore}`;
          logger.warn(reason);
          return { block: true, blockReason: reason };
        }
      } else {
        const msg = (r.reason as Error).message;
        if (cfg.failOpen) {
          logger.warn(
            `[moltrust] counterparty ${did} lookup failed (failOpen=true, allowing): ${msg}`,
          );
        } else {
          const reason = `[moltrust] tool ${toolName} blocked: counterparty ${did} score lookup failed and failOpen=false: ${msg}`;
          logger.warn(reason);
          return { block: true, blockReason: reason };
        }
      }
    }

    return undefined;
  };
}
