const assert = require('assert');
const lib = require('./buggy_code');
assert.strictEqual(lib.isAdult(17), false);
assert.strictEqual(lib.isAdult(21), true);
