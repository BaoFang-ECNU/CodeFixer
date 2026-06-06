const assert = require('assert');
const lib = require('./buggy_code');
assert.deepStrictEqual(lib.countWords(['a', 'b', 'a']), { a: 2, b: 1 });
