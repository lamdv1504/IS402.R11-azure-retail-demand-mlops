// Run the actual TypeScript service in Node without adding a test framework.
const { readFileSync } = require("node:fs");
const { dirname, resolve } = require("node:path");
const { createRequire } = require("node:module");
const ts = require("typescript");
const cache = new Map();

function loadSource(filename) {
  const path = resolve(__dirname, filename);
  if (cache.has(path)) return cache.get(path).exports;
  const output = ts.transpileModule(readFileSync(path, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const module = { exports: {} };
  cache.set(path, module);
  const nativeRequire = createRequire(path);
  const localRequire = specifier => specifier.startsWith(".")
    ? loadSource(resolve(dirname(path), `${specifier}.ts`))
    : nativeRequire(specifier);
  new Function("require", "module", "exports", output)(localRequire, module, module.exports);
  return module.exports;
}

module.exports = { loadSource };
