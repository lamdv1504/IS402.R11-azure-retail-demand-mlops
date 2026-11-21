const { spawnSync } = require("node:child_process");
const { resolve } = require("node:path");
const targets = require("../api-targets.json");

const [target, command, ...args] = process.argv.slice(2);
if (!Object.hasOwn(targets, target) || !["dev", "build", "check"].includes(command)) {
  console.error("Usage: node scripts/with-api.cjs <local|aci> <dev|build|check> [Next.js arguments]");
  process.exit(1);
}

const cwd = resolve(__dirname, "..");
const commandArgs = command === "check"
  ? [resolve(__dirname, "check-api.cjs")]
  : [require.resolve("next/dist/bin/next"), command, ...args];
console.log(`API (${target}): ${targets[target]}`);
const child = spawnSync(process.execPath, commandArgs, {
  cwd,
  env: { ...process.env, NEXT_PUBLIC_API_URL: targets[target], L05_API_TARGET: target },
  stdio: "inherit",
});
if (child.error) console.error(child.error.message);
process.exit(child.status ?? 1);
