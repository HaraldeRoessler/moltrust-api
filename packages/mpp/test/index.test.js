const { requireScore, getScore, extractWalletFromMPP } = require('../index');

const TEST_WALLET = '0x742d35Cc6634C0532925a3b844Bc9e7595f8fE00';

function makePaymentHeader(source) {
  const credential = {
    challenge: { id: 'test', intent: 'charge', method: 'tempo', realm: 'test.com', request: {} },
    payload: { signature: '0x123' },
    source: source,
  };
  return 'Payment ' + Buffer.from(JSON.stringify(credential)).toString('base64');
}

async function runTests() {
  let pass = 0, fail = 0;

  function check(name, condition) {
    if (condition) { console.log('  OK', name); pass++; }
    else { console.log('  FAIL', name); fail++; }
  }

  console.log('Test 1: source field — chainId:address format');
  const req1 = { headers: { authorization: makePaymentHeader('1:' + TEST_WALLET) } };
  check('wallet from source', extractWalletFromMPP(req1) === TEST_WALLET);

  console.log('Test 2: source field — plain address');
  const req2 = { headers: { authorization: makePaymentHeader(TEST_WALLET) } };
  check('wallet from plain source', extractWalletFromMPP(req2) === TEST_WALLET);

  console.log('Test 3: missing header');
  check('null on missing', extractWalletFromMPP({ headers: {} }) === null);

  console.log('Test 4: non-Payment header');
  check('null on Bearer', extractWalletFromMPP({ headers: { authorization: 'Bearer xyz' } }) === null);

  console.log('Test 5: MPP prefix also works (compat)');
  const cred5 = { source: TEST_WALLET, challenge: {}, payload: {} };
  const req5 = { headers: { authorization: 'MPP ' + Buffer.from(JSON.stringify(cred5)).toString('base64') } };
  check('MPP prefix compat', extractWalletFromMPP(req5) === TEST_WALLET);

  console.log('Test 6: payload.address fallback');
  const cred6 = { challenge: {}, payload: { address: TEST_WALLET } };
  const req6 = { headers: { authorization: 'Payment ' + Buffer.from(JSON.stringify(cred6)).toString('base64') } };
  check('payload.address', extractWalletFromMPP(req6) === TEST_WALLET);

  console.log('Test 7: from field fallback');
  const cred7 = { challenge: {}, payload: {}, from: TEST_WALLET };
  const req7 = { headers: { authorization: 'Payment ' + Buffer.from(JSON.stringify(cred7)).toString('base64') } };
  check('from field', extractWalletFromMPP(req7) === TEST_WALLET);

  console.log('Test 8: requireScore returns middleware');
  check('function returned', typeof requireScore({ minScore: 60 }) === 'function');

  console.log('Test 9: getScore returns number');
  const score = await getScore(TEST_WALLET);
  check('number returned', typeof score === 'number');

  console.log(`\n${pass} passed, ${fail} failed`);
  if (fail > 0) process.exit(1);
}

runTests().catch(e => { console.error(e); process.exit(1); });
