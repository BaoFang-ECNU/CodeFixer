const assert = require('assert');
const lib = require('./buggy_code');
assert.strictEqual(lib.lastItem([1, 2, 3]), 3);
