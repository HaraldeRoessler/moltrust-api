/**
 * inbound_claim hook handler.
 *
 * Per openclaw hook-message.types.ts: returning {handled: true, reply: ...}
 * stops further claim processing and replies to the sender.
 *
 * Strategy:
 *   - extract sender DID: event.metadata?.did first, else senderId if it
 *     itself looks like a did:* string
 *   - if cfg.minTrustScore <= 0 → no-op
 *   - fetch trust score; if below threshold → return handled+warn-reply
 *
 * Failure mode (lookup errors): controlled by cfg.failOpen. Default
 * cfg.failOpen=false → fail-CLOSED: block the inbound claim with a warn-reply
 * (handled: true). Opt-in cfg.failOpen=true → warn-log and pass through.
 * See ADR 0001 + README "Security Posture & Roadmap".
 */
import type { MolTrustClient } from "../client.js";
import type {
  InboundClaimContext,
  InboundClaimEvent,
  InboundClaimResult,
  MolTrustConfig,
  OpenClawLogger,
} from "../openclaw-types.js";
import { isLikelyDid } from "../utils.js";

export interface InboundClaimDeps {
  cfg: Required<MolTrustConfig>;
  client: Pick<MolTrustClient, "getTrustScore">;
  logger: OpenClawLogger;
}

export function makeInboundClaimHandler(deps: InboundClaimDeps) {
  const { cfg, client, logger } = deps;

  return async function inboundClaim(
    event: InboundClaimEvent,
    _ctx: InboundClaimContext,
  ): Promise<InboundClaimResult | undefined> {
    if (cfg.minTrustScore <= 0) return undefined;

    const metaDid =
      typeof event.metadata?.did === "string" ? event.metadata.did : undefined;
    const senderDid =
      metaDid ?? (isLikelyDid(event.senderId) ? event.senderId : undefined);
    if (!senderDid) return undefined;

    try {
      const result = await client.getTrustScore(senderDid);
      if (result.score < cfg.minTrustScore) {
        const reason = `Inbound message from ${senderDid} blocked: trust score ${result.score} < ${cfg.minTrustScore}`;
        logger.warn(`[moltrust] ${reason}`);
        return { handled: true, reply: { content: `⚠️ ${reason}` } };
      }
    } catch (err) {
      const msg = (err as Error).message;
      if (cfg.failOpen) {
        logger.warn(
          `[moltrust] inbound DID ${senderDid} lookup failed (failOpen=true, allowing): ${msg}`,
        );
        // fall through to undefined (allow)
      } else {
        const reason = `Inbound message from ${senderDid} blocked: trust score lookup failed and failOpen=false: ${msg}`;
        logger.warn(`[moltrust] ${reason}`);
        return { handled: true, reply: { content: `⚠️ ${reason}` } };
      }
    }
    return undefined;
  };
}
