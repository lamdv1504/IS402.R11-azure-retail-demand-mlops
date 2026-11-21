const assert = require("node:assert/strict");
const { test } = require("node:test");
const { loadSource } = require("./load-source.cjs");
const { api, resolveApiUrl } = loadSource("../src/lib/api.ts");

test("normalizes local and ACI URLs while retaining the handed-off HTTP port", () => {
  assert.equal(resolveApiUrl(""), "http://127.0.0.1:8000");
  assert.equal(resolveApiUrl(" http://example.azurecontainer.io:8000/// "), "http://example.azurecontainer.io:8000");
  assert.equal(resolveApiUrl("https://example.com/api/"), "https://example.com/api");
  for (const value of ["localhost:8000", "ftp://example.com", "https://user:secret@example.com", "https://example.com?token=secret", "https://example.com#fragment"]) {
    assert.throws(() => resolveApiUrl(value), /Cấu hình NEXT_PUBLIC_API_URL/);
  }
});

test("rejects HTTP API calls from an HTTPS page before fetch", async () => {
  const originalFetch = global.fetch;
  const originalWindow = global.window;
  const originalUrl = process.env.NEXT_PUBLIC_API_URL;
  global.window = { location: { protocol: "https:" } };
  process.env.NEXT_PUBLIC_API_URL = "http://example.azurecontainer.io:8000";
  global.fetch = () => assert.fail("Mixed content must be explained before a request");
  try { await assert.rejects(api("/health"), /API HTTPS/); }
  finally {
    global.fetch = originalFetch;
    if (originalWindow === undefined) delete global.window;
    else global.window = originalWindow;
    if (originalUrl === undefined) delete process.env.NEXT_PUBLIC_API_URL;
    else process.env.NEXT_PUBLIC_API_URL = originalUrl;
  }
});

test("surfaces malformed successful responses instead of rendering empty data", async () => {
  const original = global.fetch;
  try {
    for (const response of [new Response("<html>upstream unavailable</html>"), Response.json(null), Response.json("not an object")]) {
      global.fetch = async () => response;
      await assert.rejects(api("/health"), /JSON không hợp lệ/);
    }
    global.fetch = async () => new Response("upstream unavailable", { status: 502 });
    await assert.rejects(api("/health"), /API trả lỗi 502/);
  } finally { global.fetch = original; }
});

for (const phase of ["headers", "body"]) test(`aborts while waiting for response ${phase} after 15 seconds`, async () => {
  const originalFetch = global.fetch;
  const originalSetTimeout = global.setTimeout;
  const originalClearTimeout = global.clearTimeout;
  let abort;
  let cleared = false;
  global.setTimeout = (callback, milliseconds) => { assert.equal(milliseconds, 15000); abort = callback; return 123; };
  global.clearTimeout = id => { assert.equal(id, 123); cleared = true; };
  global.fetch = async (_url, { signal }) => {
    const wait = () => new Promise((_resolve, reject) => {
      signal.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
      abort();
    });
    return phase === "headers" ? wait() : { ok: true, json: wait };
  };
  try {
    await assert.rejects(api("/health"), /phản hồi quá chậm/);
    assert.equal(cleared, true);
  } finally {
    global.fetch = originalFetch;
    global.setTimeout = originalSetTimeout;
    global.clearTimeout = originalClearTimeout;
  }
});
