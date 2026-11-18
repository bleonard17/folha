"use strict";
// Source-level regression tests for the exact files GitHub Pages serves.
// No production requests, API credentials, weather calls, or browser are required.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.join(__dirname, "..");
const html = fs.readFileSync(path.join(root, "index.html"), "utf8");
const i18n = fs.readFileSync(path.join(root, "i18n.js"), "utf8");

function seasonYear(today) {
  const match = html.match(/const thisSeasonYear\s*=\s*([^;]+);/);
  assert.ok(match, "must have a season-year selection expression");
  const expression = new Function("today", "return (" + match[1] + ");");
  return expression(today);
}

test("browser scripts parse without JavaScript syntax errors", () => {
  const start = html.lastIndexOf("<script>");
  const end = html.indexOf("</script>", start);
  assert.ok(start >= 0 && end > start, "main inline script exists");
  new vm.Script(html.slice(start + 8, end), { filename: "index.html" });
  new vm.Script(i18n, { filename: "i18n.js" });
});

test("date picker remains valid after the autumn season ends", () => {
  const samples = [
    ["2026-09-14", 2026], ["2026-12-15", 2026],
    ["2026-12-16", 2027], ["2026-12-17", 2027],
    ["2026-12-20", 2027], ["2026-12-21", 2027],
    ["2027-01-01", 2027], ["2027-12-16", 2028]
  ];
  for (const [today, expectedYear] of samples) {
    const year = seasonYear(today);
    assert.equal(year, expectedYear, "season year for " + today);
    const start = year + "-09-15", end = year + "-12-15";
    const min = today > start ? today : start;
    assert.ok(min <= end, "date picker min must not exceed max: " + today);
  }
});

test("canonical website, share image, satellite and localization links remain configured", () => {
  assert.match(html, /https:\/\/folha\.trilho\.dev\//);
  assert.match(html, /property="og:image"[^>]*https:\/\/folha\.trilho\.dev\/og-image\.png/);
  assert.match(html, /src="\.\/i18n\.js"/);
  assert.match(html, /data\/satellite-observations\.json/);
  assert.match(html, /type="date" id="visitDate"/);
  assert.ok(fs.statSync(path.join(root,"og-image.png")).size > 10_000);
  assert.equal(fs.readFileSync(path.join(root,"CNAME"),"utf8").trim(), "folha.trilho.dev");
});

test("exactly 19 unique destinations are defined", () => {
  const ids = Array.from(html.matchAll(/\{id:'([^']+)',name:/g), m => m[1]);
  assert.equal(ids.length, 19);
  assert.equal(new Set(ids).size, 19);
});

test("satellite samples must never be presented as verified foliage stages", () => {
  const data = JSON.parse(fs.readFileSync(path.join(root,"data/satellite-observations.json"),"utf8"));
  assert.equal(data.schema_version, 1);
  const entries = Object.values(data.destinations);
  assert.equal(entries.length, 19);
  for (const entry of entries) {
    assert.equal(entry.validated, false);
    assert.equal(entry.stage, null);
    assert.ok(["experimental","unavailable"].includes(entry.status));
  }
});
