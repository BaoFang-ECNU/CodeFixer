const assert = require('assert');
const lib = require('./buggy_code');
assert.deepStrictEqual(lib.topScores([10, 40, 20, 30], 3), [40, 30, 20]);
