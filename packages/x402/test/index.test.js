const { requireScore, getScore } = require('../index');

const TEST_WALLET = '0x3802000000000000000000000000000000000000';

async function runTests() {
  console.log('Test 1: getScore returns number');
  const score = await getScore(TEST_WALLET);
  console.assert(typeof score === 'number', 'Score should be number');
  console.log(`  Score: ${score} ✓`);

  console.log('Test 2: requireScore returns middleware function');
  const mw = requireScore({ minScore: 60 });
  console.assert(typeof mw === 'function', 'Should return function');
  console.log('  Middleware function created ✓');

  console.log('Test 3: deny on missing wallet');
  const mw2 = requireScore({ minScore: 60 });
  let denied = false;
  const mockReq = { headers: {} };
  const mockRes = {
    status: (code) => ({ json: (body) => {
      console.assert(code === 403, 'Should return 403');
      console.assert(body.error === 'trust_check_failed', 'Should have error');
      denied = true;
    }})
  };
  await mw2(mockReq, mockRes, () => {});
  console.assert(denied, 'Should have been denied');
  console.log('  403 on missing wallet ✓');

  console.log('Test 4: allow unregistered when configured');
  const mw3 = requireScore({ allowUnregistered: true });
  let passed = false;
  await mw3({ headers: {} }, {}, () => { passed = true; });
  console.assert(passed, 'Should call next()');
  console.log('  allowUnregistered passes ✓');

  console.log('\nAll tests passed ✓');
}

runTests().catch(console.error);
