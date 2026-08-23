#!/usr/bin/env node
// mcp-gap-capture: rank logged gaps by requested tool to find what to build next.

import { readFileSync, existsSync } from "node:fs";

const sink =
  process.argv[2] ||
  process.env.MCP_GAP_SINK ||
  "/Users/USER/claude-workspace/_tobi_wiki/wiki/mcp-gaps.jsonl";

if (!existsSync(sink)) {
  console.log("mcp-gap-capture: no gaps logged yet");
  process.exit(0);
}

let rows;
try {
  rows = readFileSync(sink, "utf8")
    .split("\n")
    .filter(Boolean)
    .map((l) => JSON.parse(l));
} catch (e) {
  console.error("mcp-gap-capture: failed to read sink:", e.message);
  process.exit(1);
}

const counts = {};
for (const r of rows) {
  const k = r.attempted_tool || "unknown";
  counts[k] = counts[k] || { tool: k, total: 0, high: 0, low: 0, fallbacks: {} };
  counts[k].total++;
  if (r.confidence === "high") counts[k].high++;
  else counts[k].low++;
  const fb = r.fallback_path || "other";
  counts[k].fallbacks[fb] = (counts[k].fallbacks[fb] || 0) + 1;
}

const ranked = Object.values(counts).sort((a, b) => b.total - a.total);
console.log(`# MCP gap rollup — ${rows.length} total gaps\n`);
console.log("count\ttool\t\t[confidence]\tfallbacks");
for (const c of ranked) {
  const fb = Object.entries(c.fallbacks)
    .map(([k, v]) => `${k}:${v}`)
    .join(" ");
  console.log(`${c.total}\t${c.tool}\t[high:${c.high} low:${c.low}]\t${fb}`);
}
