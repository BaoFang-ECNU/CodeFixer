const assert = require('assert');
const lib = require('./buggy_code');
assert.strictEqual(lib.containsKeyword('Agentic Repair', 'repair'), true);
assert.strictEqual(lib.containsKeyword('Agentic Repair', 'missing'), false);
