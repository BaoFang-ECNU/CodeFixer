const assert = require('assert');
const lib = require('./buggy_code');
assert.deepStrictEqual(lib.topScores([1, 3, 2], 2), [3, 2]);
