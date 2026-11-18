const assert = require("node:assert/strict");
const { test } = require("node:test");
const { loadSource } = require("./load-source.cjs");
const { validatePrediction, predictDemand } = loadSource("../src/services/predictionService.ts");
const { api, formatDate, formatWeekday } = loadSource("../src/lib/api.ts");
// Recorded real HI05 output is a test fixture, never a fallback in the UI.
const sample = require("../../reports/Hieu/hi05_sample_response.json");
const request = { store_id: sample.store_id, item_id: sample.item_id, horizon: sample.horizon };

test("accepts the recorded 28-day HI05 forecast with historical UTC dates", () => {
  assert.equal(validatePrediction(sample, request), sample);
  assert.equal(formatDate(sample.forecast_start_date), "23/5/2016");
  assert.equal(formatWeekday(sample.forecast_start_date), "Thứ Hai");
});

const corruptions = [
  ["wrong store", value => { value.store_id = "CA_2"; }],
  ["wrong item", value => { value.item_id = "NOT_IN_MVP"; }],
  ["wrong horizon", value => { value.horizon = 7; }],
  ["missing day", value => { value.forecast.pop(); }],
  ["duplicate day", value => { value.forecast[1].date = value.forecast[0].date; }],
  ["gap in dates", value => { value.forecast[1].date = "2016-05-25"; }],
  ["invalid calendar date", value => { value.forecast_start_date = "2016-02-30"; }],
  ["invalid day format", value => { value.forecast[0].date = "23/05/2016"; }],
  ["negative units", value => { value.forecast[0].predicted_sales = -1; }],
  ["NaN units", value => { value.forecast[0].predicted_sales = NaN; }],
  ["infinite units", value => { value.forecast[0].predicted_sales = Infinity; }],
  ["wrong total", value => { value.total_predicted_sales += 1; }],
  ["infinite total", value => { value.total_predicted_sales = Infinity; }],
  ["missing model version", value => { value.model_version = ""; }],
  ["non-string data version", value => { value.data_version = 42; }],
];
for (const [name, corrupt] of corruptions) {
  test(`rejects ${name} before chart/table rendering`, () => {
    const value = structuredClone(sample);
    corrupt(value);
    assert.throws(() => validatePrediction(value, request));
  });
}

test("rejects invalid requests without a network call", async () => {
  const original = global.fetch;
  global.fetch = () => { assert.fail("Invalid requests must not reach fetch"); };
  try {
    for (const horizon of [0, 29, 1.5, NaN]) {
      await assert.rejects(predictDemand(request.store_id, request.item_id, horizon), /1 đến 28/);
    }
    await assert.rejects(predictDemand("", request.item_id, 28));
    await assert.rejects(predictDemand(request.store_id, "", 28));
  } finally { global.fetch = original; }
});

test("sends the selected store, item and horizon as JSON", async () => {
  const original = global.fetch;
  global.fetch = async (url, init) => {
    assert.ok(url.endsWith("/predict"));
    assert.equal(init.method, "POST");
    assert.equal(init.headers["Content-Type"], "application/json");
    assert.deepEqual(JSON.parse(init.body), request);
    return Response.json(sample);
  };
  try { assert.deepEqual(await predictDemand(request.store_id, request.item_id, request.horizon), sample); }
  finally { global.fetch = original; }
});

test("surfaces 503, structured 422, network and timeout errors", async () => {
  const original = global.fetch;
  try {
    global.fetch = async () => Response.json({ detail: "Model chưa sẵn sàng" }, { status: 503 });
    await assert.rejects(api("/predict"), /Model chưa sẵn sàng/);
    global.fetch = async () => Response.json({ detail: [{ msg: "validation failed" }] }, { status: 422 });
    await assert.rejects(api("/predict"), /số ngày nguyên từ 1 đến 28/);
    global.fetch = async () => { throw new TypeError("Failed to fetch"); };
    await assert.rejects(api("/predict"), /Không kết nối được API/);
    global.fetch = async () => { throw new DOMException("aborted", "AbortError"); };
    await assert.rejects(api("/predict"), /phản hồi quá chậm/);
  } finally { global.fetch = original; }
});
