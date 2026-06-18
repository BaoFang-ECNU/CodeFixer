const assert = require('assert');
const lib = require('./buggy_code');
assert.strictEqual(lib.sumToN(1), 1);
assert.strictEqual(lib.sumToN(5), 15);
