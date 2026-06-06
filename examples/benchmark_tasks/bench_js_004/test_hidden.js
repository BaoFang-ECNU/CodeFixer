const assert = require('assert');
const lib = require('./buggy_code');
assert.strictEqual(lib.parseIntOrDefault('42', -1), 42);
