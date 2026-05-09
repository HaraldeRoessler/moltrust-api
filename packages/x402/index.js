const https = require('https');

const MOLTRUST_API = 'https://api.moltrust.ch';
const CACHE_TTL = 300000; // 5 min cache
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
        } catch { resolve(0); }
      });
    }).on('error', () => resolve(0));
  });
}

function extractWallet(req) {
  const payment = req.headers['x-payment'] || req.headers['x-402-payment'] || '';
  const match = payment.match(/0x[a-fA-F0-9]{40}/);
  return match ? match[0] : null;
}

function requireScore(options = {}) {
  const {
    minScore = 60,
    onDeny = null,
    allowUnregistered = false,
    apiBase = MOLTRUST_API
  } = options;

  return async function moltrustMiddleware(req, res, next) {
    const wallet = extractWallet(req);

    if (!wallet) {
      if (allowUnregistered) return next();
      return res.status(403).json({
        error: 'trust_check_failed',
        reason: 'no_wallet_identified',
        message: 'No wallet address found in x402 payment header.',
        register: 'https://moltrust.ch/register'
      });
    }

    const score = await getScore(wallet);

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

    req.moltrust = { wallet, score };
    next();
  };
}

module.exports = { requireScore, getScore };
