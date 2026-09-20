#!/usr/bin/env node
// product-idea-capture: roll up logged product ideas/gaps by area and type.

import { readFileSync, existsSync } from "node:fs";

const sink =
  process.argv[2] ||
  process.env.PRODUCT_IDEA_SINK ||
  "/Users/USER/claude-workspace/_tobi_wiki/wiki/product-ideas.jsonl";

if (!existsSync(sink)) {
  console.log("product-idea-capture: nothing logged yet");
  process.exit(0);
}

let rows;
try {
  rows = readFileSync(sink, "utf8")
    .split("\n")
    .filter(Boolean)
    .map((l) => JSON.parse(l));
} catch (e) {
  console.error("product-idea-capture: failed to read sink:", e.message);
  process.exit(1);
}

const byArea = {};
for (const r of rows) {
  const k = r.area || "uncategorised";
  byArea[k] = byArea[k] || { area: k, total: 0, open: 0, types: {} };
  byArea[k].total++;
  if ((r.status || "open") === "open") byArea[k].open++;
  const t = r.type || "gap";
  byArea[k].types[t] = (byArea[k].types[t] || 0) + 1;
}

const ranked = Object.values(byArea).sort((a, b) => b.total - a.total);
console.log(`# Vetted product idea rollup — ${rows.length} total\n`);
console.log("count\topen\tarea\t[types]");
for (const c of ranked) {
  const types = Object.entries(c.types).map(([k, v]) => `${k}:${v}`).join(" ");
  console.log(`${c.total}\t${c.open}\t${c.area}\t[${types}]`);
}
