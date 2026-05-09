# @moltrust/mpp

Trust score middleware for MPP (Machine Payments Protocol) endpoints.
Works alongside `mppx` — one line of code.

## Install
```
npm install @moltrust/mpp
```

## Usage
```javascript
const { requireScore } = require('@moltrust/mpp');
const { Mppx, tempo } = require('mppx/server');

// Add MolTrust trust check before MPP payment middleware
app.use(requireScore({ minScore: 60 }));
app.use(mppx.charge({ amount: '0.01' }));
```

## How it works
1. Extracts paying wallet from MPP Authorization credential header
2. Looks up MolTrust trust score for that wallet (5-min cache)
3. Allows or denies based on configurable minScore threshold
4. Attaches `req.moltrust = { wallet, score, protocol: 'mpp' }` for downstream use

## Companion packages
- [@moltrust/x402](https://www.npmjs.com/package/@moltrust/x402) — same API for x402 endpoints

## Links
- MolTrust: https://moltrust.ch
- MPP Protocol: https://mpp.dev
- Wallet profile: https://moltrust.ch/wallet/{address}

## License
MIT — Copyright (c) 2026 CryptoKRI GmbH, Zurich (MolTrust)
