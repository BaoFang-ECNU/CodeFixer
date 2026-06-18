const assert = require('assert');
const lib = require('./buggy_code');
assert.strictEqual(lib.safeAverage([2, 4, 6]), 4);
