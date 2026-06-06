const assert = require('assert');
const lib = require('./buggy_code');
assert.deepStrictEqual(lib.countWords(['a', 'a']), { a: 2 });
