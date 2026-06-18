const assert = require('assert');
const lib = require('./buggy_code');
assert.strictEqual(lib.isAdult(18), true);
