const assert = require('assert');
const lib = require('./buggy_code');
assert.strictEqual(lib.safeAverage([]), 0);
