const assert = require("node:assert/strict");
const { test } = require("node:test");
const { loadSource } = require("./load-source.cjs");
const { api, getHealth, getCatalog, getDashboard, getModelInfo } = loadSource("../src/lib/api.ts");
const { predictDemand } = loadSource("../src/services/predictionService.ts");

// Requires the local L03 backend. No mocks; these are service/HTTP checks, not browser tests.
test("loads the real MVP catalog, dashboard and model metadata", async () => {
  const [health, catalog, dashboard, model] = await Promise.all([getHealth(), getCatalog(), getDashboard(), getModelInfo()]);
  assert.equal(health.model_loaded, true);
  assert.equal(catalog.store_id, "CA_1");
  assert.equal(catalog.items.length, 300);
  assert.equal(new Set(catalog.items.map(item => item.item_id)).size, 300);
  assert.deepEqual(catalog.categories_breakdown, { FOODS: 100, HOBBIES: 100, HOUSEHOLD: 100 });
  assert.equal(dashboard.item_count, 300);
  assert.equal(dashboard.daily_sales.length, 1941);
  assert.equal(model.status, "ready");
  assert.ok(model.features_used.length > 0);
  assert.ok(model.temporal_split.validation_period);
  console.log(JSON.stringify({ model: model.model_version, items: catalog.items.length, history_days: dashboard.daily_sales.length }));
});

for (const horizon of [1, 7, 28]) {
  test(`validates a real ${horizon}-day forecast through predictionService`, async () => {
    const result = await predictDemand("CA_1", "FOODS_1_017", horizon);
    assert.equal(result.forecast.length, horizon);
    assert.equal(result.forecast_start_date, "2016-05-23");
    assert.equal(result.forecast.at(-1).date, { 1: "2016-05-23", 7: "2016-05-29", 28: "2016-06-19" }[horizon]);
    console.log(JSON.stringify({ horizon, total_units: result.total_predicted_sales, start: result.forecast_start_date, end: result.forecast.at(-1).date }));
  });
}

test("shows API errors for an unknown item and invalid horizon", async () => {
  await assert.rejects(predictDemand("CA_1", "NOT_IN_MVP", 28), /not found|không|MVP/i);
  await assert.rejects(api("/predict", { method: "POST", body: JSON.stringify({ store_id: "CA_1", item_id: "FOODS_1_017", horizon: 29 }) }), /1 đến 28/);
});
