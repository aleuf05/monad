const assert = require("assert");
require("./characters.js");
assert(MonadCharacters.list().length >= 4);
assert.equal(MonadCharacters.get("captain.monad").role, "command presence");
assert.equal(MonadCharacters.get("captain.monad").provenance.kind, "synthetic-character");
assert.throws(() => MonadCharacters.register({ name: "Missing id" }), /requires id and name/);
console.log("character model tests passed");
