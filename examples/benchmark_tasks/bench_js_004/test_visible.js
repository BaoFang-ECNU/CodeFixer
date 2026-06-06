const assert = require('assert');
const lib = require('./buggy_code');
assert.strictEqual(lib.parseIntOrDefault('bad', -1), -1);
