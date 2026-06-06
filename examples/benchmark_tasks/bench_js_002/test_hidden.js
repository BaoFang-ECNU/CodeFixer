const assert = require('assert');
const lib = require('./buggy_code');
assert.strictEqual(lib.largestOrNull([2, 9, 1]), 9);
