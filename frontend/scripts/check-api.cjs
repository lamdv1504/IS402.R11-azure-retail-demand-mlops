// Real HTTP checks through the frontend service. This does not simulate a browser.
const assert = require("node:assert/strict");
const { mkdirSync, writeFileSync } = require("node:fs");
const { resolve } = require("node:path");
const { loadSource } = require("../tests/load-source.cjs");
const { api, getHealth, getCatalog, getModelInfo, resolveApiUrl } = loadSource("../src/lib/api.ts");
const { predictDemand } = loadSource("../src/services/predictionService.ts");

const target = process.env.L05_API_TARGET;
if (!["local", "aci"].includes(target)) throw new Error("Run npm run test:local or npm run test:aci.");
const baseUrl = resolveApiUrl();
const report = {
  target, api_url: baseUrl, started_at: new Date().toISOString(),
  verification: "Node HTTP + actual frontend predictionService; browser UI/Network not verified by this command",
  checks: [], requests: [],
};
const originalFetch = global.fetch;
global.fetch = async (url, init = {}) => {
  // Browsers add Origin automatically. Node needs it explicitly for CORS evidence.
  const headers = new Headers(init.headers);
  if (!headers.has("Origin")) headers.set("Origin", "http://localhost:3000");
  const record = { url: String(url), method: init.method || "GET", origin: headers.get("Origin"), request: init.body ? JSON.parse(init.body) : null };
  report.requests.push(record);
  const started = performance.now();
  try {
    const response = await originalFetch(url, { ...init, headers, signal: init.signal || AbortSignal.timeout(15000) });
    record.status = response.status;
    record.cors = Object.fromEntries(["access-control-allow-origin", "access-control-allow-methods", "access-control-allow-headers"].map(key => [key, response.headers.get(key)]));
    record.response = await response.clone().json().catch(() => null);
    return response;
  } catch (error) {
    record.error = error.message;
    record.error_code = error.cause?.code || error.name;
    throw error;
  } finally { record.duration_ms = Math.round(performance.now() - started); }
};

async function check(name, work) {
  try {
    const result = await work();
    const warning = result && typeof result === "object" ? result.warning : null;
    const note = warning || result;
    report.checks.push({ name, status: warning ? "warning" : "passed", ...(note ? { note } : {}) });
    console.log(`${warning ? "WARN" : "PASS"} ${name}${note ? `: ${note}` : ""}`);
    return true;
  } catch (error) {
    report.checks.push({ name, status: "failed", error: error.message });
    console.error(`FAIL ${name}: ${error.message}`);
    return false;
  }
}

async function main() {
  // Stop early if ACI is stopped; do not wait on every route separately.
  if (!await check("health_model_loaded", async () => {
    const health = await getHealth();
    assert.equal(health.status, "healthy");
    assert.equal(health.model_loaded, true);
  })) {
    report.remaining_checks = "not_run: API/model is not ready";
    return;
  }

  await check("model_metadata", async () => {
    const model = await getModelInfo();
    assert.equal(model.status, "ready");
    assert.ok(model.model_version);
    assert.equal(model.forecast_horizon, 28);
    assert.ok(model.features_used.length > 0);
    return model.model_version;
  });
  await check("catalog_300_items", async () => {
    const catalog = await getCatalog();
    assert.equal(catalog.store_id, "CA_1");
    assert.equal(catalog.items.length, 300);
    assert.equal(new Set(catalog.items.map(item => item.item_id)).size, 300);
    assert.deepEqual(catalog.categories_breakdown, { FOODS: 100, HOBBIES: 100, HOUSEHOLD: 100 });
    assert.ok(catalog.items.some(item => item.item_id === "FOODS_1_017"));
  });
  for (const origin of ["http://localhost:3000", "http://127.0.0.1:3000"]) {
    await check(`cors_${origin}`, async () => {
      const response = await fetch(`${baseUrl}/predict`, {
        method: "OPTIONS", headers: { Origin: origin, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type" },
      });
      assert.equal(response.status, 200);
      assert.equal(response.headers.get("access-control-allow-origin"), origin);
      assert.match(response.headers.get("access-control-allow-methods") || "", /POST/);
      assert.match(response.headers.get("access-control-allow-headers") || "", /content-type/i);
      const health = await fetch(`${baseUrl}/health`, { headers: { Origin: origin } });
      assert.equal(health.status, 200);
      assert.equal(health.headers.get("access-control-allow-origin"), origin);
    });
  }
  await check("forecast_28_days", async () => {
    const result = await predictDemand("CA_1", "FOODS_1_017", 28);
    assert.equal(report.requests.at(-1).status, 200);
    assert.equal(report.requests.at(-1).cors["access-control-allow-origin"], "http://localhost:3000");
    const model = await getModelInfo();
    assert.equal(result.model_version, model.model_version);
    assert.equal(result.data_version, model.data_version);
    report.forecast = result;
    return `${result.forecast.length} days, ${result.total_predicted_sales} units, ${result.model_version}`;
  });
  await check("unknown_item_404", async () => {
    await assert.rejects(predictDemand("CA_1", "NOT_IN_MVP", 28));
    assert.equal(report.requests.at(-1).status, 404);
  });
  await check("invalid_horizon_422", async () => {
    await assert.rejects(api("/predict", { method: "POST", body: JSON.stringify({ store_id: "CA_1", item_id: "FOODS_1_017", horizon: 29 }) }), /1 đến 28/);
    assert.equal(report.requests.at(-1).status, 422);
  });
  await check("dashboard_availability", async () => {
    const response = await fetch(`${baseUrl}/dashboard`);
    if (target === "aci" && response.status === 503) {
      assert.equal((await response.json()).error_code, "DASHBOARD_NOT_READY");
      return { warning: "History unavailable: Q05 image excludes processed Parquet. Forecast uses the HI05 bundle independently." };
    }
    assert.equal(response.status, 200);
    const data = await response.json();
    assert.equal(data.item_count, 300);
    assert.equal(data.daily_sales.length, 1941);
  });
}

main().catch(error => {
  report.checks.push({ name: "unexpected_error", status: "failed", error: error.message });
}).finally(() => {
  global.fetch = originalFetch;
  report.finished_at = new Date().toISOString();
  report.status = report.checks.some(check => check.status === "failed") ? "failed"
    : report.checks.some(check => check.status === "warning") ? "passed_with_warnings" : "passed";
  const output = resolve(__dirname, `../../reports/Lam/l05_${target}_api_check.json`);
  mkdirSync(resolve(output, ".."), { recursive: true });
  writeFileSync(output, `${JSON.stringify(report, null, 2)}\n`);
  console.log(`Evidence: ${output}`);
  if (report.status === "failed") process.exitCode = 1;
});
