# @moltrust/x402

Trust score middleware for x402 endpoints. One line of code.

## Install

```bash
npm install @moltrust/x402
```

## Usage

```javascript
const { requireScore } = require('@moltrust/x402');

// Block agents with trust score below 60
app.use(requireScore({ minScore: 60 }));

// Custom deny handler
app.use(requireScore({
  minScore: 40,
  onDeny: (req, res, { wallet, score }) => {
    res.status(403).json({ message: `Score ${score} too low`, wallet });
  }
}));

// Allow unregistered agents (score = shadow score)
app.use(requireScore({ minScore: 0, allowUnregistered: true }));
```

## How it works

1. Extracts paying wallet from x402 `X-Payment` header
2. Looks up MolTrust trust score for that wallet
3. Allows or denies based on configurable `minScore` threshold
4. Attaches `req.moltrust = { wallet, score }` for downstream use

Scores are cached for 5 minutes. Zero latency impact on warm cache.

## License

MIT — CryptoKRI GmbH, Zurich

## Links

- [MolTrust](https://moltrust.ch)
- [API Docs](https://api.moltrust.ch/docs)
- [Protocol Whitepaper](https://moltrust.ch/whitepaper)
