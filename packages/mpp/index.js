const https = require('https');

const MOLTRUST_API = 'https://api.moltrust.ch';
const CACHE_TTL = 300000; // 5 min
const scoreCache = new Map();

async function getScore(wallet) {
  const cached = scoreCache.get(wallet);
  if (cached && Date.now() - cached.ts < CACHE_TTL) return cached.score;

  return new Promise((resolve) => {
    https.get(`${MOLTRUST_API}/wallet/${wallet}`, (res) => {
      let data = '';
      res.on('data', d => data += d);
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          const score = json.shadow_score || json.trust_score || 0;
          scoreCache.set(wallet, { score, ts: Date.now() });
          resolve(score);
        } catch { resolve(null); }
      });
    }).on('error', () => resolve(null));
  });
}

/**
 * Extract payer wallet from MPP/Payment Authorization header.
 *
 * mppx credential format (Authorization: Payment <base64>):
 * {
 *   challenge: { id, intent, method, realm, request: { amount, currency, recipient } },
 *   payload: { signature: "0x..." },
 *   source: "<chainId>:<address>"   ← payer address lives here
 * }
 *
 * Fallback paths for other MPP implementations:
 * - credential.source (format: "chainId:0xAddress" or just "0xAddress")
 * - credential.payload.address
 * - credential.from
 */
function extractWalletFromMPP(req) {
  const auth = req.headers['authorization'] || '';

  // mppx uses "Payment" prefix
  const match = auth.match(/^(?:Payment|MPP)\s+(.+)$/i);
  if (!match) return null;

  try {
    const json = JSON.parse(Buffer.from(match[1], 'base64').toString('utf8'));

    // Primary: source field (mppx format — "chainId:0xAddress")
    if (json.source) {
      const parts = String(json.source).split(':');
      const addr = parts.find(p => /^0x[0-9a-fA-F]{40}$/.test(p));
      if (addr) return addr;
      // If source is just an address
      if (/^0x[0-9a-fA-F]{40}$/.test(json.source)) return json.source;
    }

    // Fallback: challenge.request.recipient (merchant, not payer — skip)
    // Fallback: payload.address
    if (json.payload?.address && /^0x[0-9a-fA-F]{40}$/.test(json.payload.address))
      return json.payload.address;

    // Fallback: from field
    if (json.from && /^0x[0-9a-fA-F]{40}$/.test(json.from))
      return json.from;

    return null;
  } catch { return null; }
}

function requireScore(options = {}) {
  const {
    minScore = 60,
    onDeny = null,
    allowUnregistered = false,
  } = options;

  return async function moltrustMPPMiddleware(req, res, next) {
    const wallet = extractWalletFromMPP(req);

    if (!wallet) {
      if (allowUnregistered) return next();
      return res.status(403).json({
        error: 'trust_check_failed',
        reason: 'no_wallet_in_mpp_credential',
        message: 'No wallet address found in MPP Authorization credential.',
        register: 'https://moltrust.ch/register'
      });
    }

    const score = await getScore(wallet);

    // Fail-open: if MolTrust API is unreachable, allow the request
    if (score === null) {
      req.moltrust = { wallet, score: null, protocol: 'mpp', failOpen: true };
      return next();
    }

    if (score < minScore) {
      if (onDeny) return onDeny(req, res, { wallet, score, minScore });
      return res.status(403).json({
        error: 'trust_score_insufficient',
        wallet,
        score,
        required: minScore,
        message: `Trust score ${score} is below required ${minScore}.`,
        profile: `https://moltrust.ch/wallet/${wallet}`,
        register: 'https://moltrust.ch/register?wallet=' + wallet
      });
    }

    req.moltrust = { wallet, score, protocol: 'mpp' };
    next();
  };
}

module.exports = { requireScore, getScore, extractWalletFromMPP };
