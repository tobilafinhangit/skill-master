#!/usr/bin/env node
// product-idea-capture: log a general Vetted product idea / gap to a shared JSONL sink.
// Sibling of mcp-gap-capture/log_gap.mjs — same redaction + dedup, different schema.
// Redacts PII, de-dupes within the sink, appends one line. No DB, no credentials.

import { readFileSync, appendFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";

// ---- redaction (kept identical to mcp-gap-capture) ----
const EMAIL_RE = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
// Must look like a phone (international +…, or grouped 3-3-4) so ISO dates and
// timestamps (2026-09-20 21:26) survive as evidence.
const PHONE_RE = /(?:\+\d[\d\s().-]{6,}\d|\b\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b)/g;
const JWT_RE = /\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g;
const LONG_SECRET_RE = /\b(?:[A-Za-z0-9+/]{40,}={0,2}|[0-9a-fA-F]{48,})\b/g;
// Context-aware: bare words like "update"/"delete" appear in ordinary product prose,
// so require real SQL shape to avoid nuking legitimate observations.
const SQL_RE = /\b(?:select\s+[\s\S]{1,300}?\sfrom\s|insert\s+into\s|update\s+[\w."`\[\]]+\s+set\s|delete\s+from\s|drop\s+table\s|alter\s+table\s|truncate\s+table\s|create\s+table\s)/i;
const UUID_RE = /\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b/g;

function redactText(s, maxLen = 200) {
  if (typeof s !== "string") return s;
  let t = s;
  if (SQL_RE.test(t)) return "[sql-omitted]";
  const uuids = [];
  t = t.replace(UUID_RE, (m) => {
    uuids.push(m);
    return `\u0000${uuids.length - 1}\u0000`;
  });
  t = t.replace(JWT_RE, "[redacted-token]");
  t = t.replace(LONG_SECRET_RE, "[redacted-secret]");
  t = t.replace(EMAIL_RE, "[redacted-email]");
  t = t.replace(PHONE_RE, "[redacted-phone]");
  t = t.replace(/\u0000(\d+)\u0000/g, (_, i) => uuids[Number(i)] ?? _);
  if (t.length > maxLen) t = t.slice(0, maxLen) + `…[${s.length} chars total]`;
  return t;
}

function norm(s) {
  return String(s || "").toLowerCase().replace(/\s+/g, " ").trim();
}

// ---- arg parse (--key value) ----
const args = process.argv.slice(2);
const get = (k) => {
  const i = args.indexOf(`--${k}`);
  return i >= 0 ? args[i + 1] : undefined;
};
const dry = args.includes("--dry");

const type = get("type") || "gap"; // gap | idea | observation
const area = get("area") || "uncategorised";
const title = get("title");
const observation = get("observation");
const expected = get("expected");
const impact = get("impact");
const status = get("status") || "open";
const product = get("product") || "vetted";
const ticket = get("ticket");
const agent = get("agent") || process.env.PRODUCT_IDEA_AGENT || "unknown";
const sessionId =
  get("session") ||
  process.env.PRODUCT_IDEA_SESSION ||
  `sess-${Math.random().toString(36).slice(2, 8)}`;

if (!title) {
  console.error("product-idea-capture: --title is required");
  process.exit(2);
}

// ---- resolve sink + repo from config ----
function resolveConfig() {
  const cfgPath = resolve(process.cwd(), ".product-idea-capture.json");
  if (existsSync(cfgPath)) {
    try {
      return JSON.parse(readFileSync(cfgPath, "utf8"));
    } catch {}
  }
  return {};
}
const cfg = resolveConfig();
const sink =
  get("sink") || cfg.sink || process.env.PRODUCT_IDEA_SINK ||
  "/Users/USER/claude-workspace/_tobi_wiki/wiki/product-ideas.jsonl";
let repo = get("repo") || cfg.repo || process.env.PRODUCT_IDEA_REPO || "unknown";

const record = {
  ts: new Date().toISOString(),
  repo,
  agent,
  session_id: sessionId,
  product,
  type,
  area,
  title: redactText(title, 300),
  status,
  ...(ticket ? { ticket } : {}),
  ...(observation ? { observation: redactText(observation, 1000) } : {}),
  ...(expected ? { expected: redactText(expected, 1000) } : {}),
  ...(impact ? { impact: redactText(impact, 1000) } : {}),
};

const line = JSON.stringify(record);

// ---- dedup (same area + title already logged) ----
function wouldDup() {
  if (!existsSync(sink)) return false;
  const norm2 = `${norm(area)}|${norm(record.title)}`;
  try {
    return readFileSync(sink, "utf8")
      .split("\n")
      .filter(Boolean)
      .some((l) => {
        try {
          const r = JSON.parse(l);
          return `${norm(r.area)}|${norm(r.title)}` === norm2;
        } catch {
          return false;
        }
      });
  } catch {
    return false;
  }
}

if (dry) {
  console.log("[dry-run] would append to", sink);
  console.log(line);
  process.exit(0);
}

if (wouldDup()) {
  console.log(`product-idea-capture: dedup — skipped (already logged: ${area} / ${record.title})`);
  process.exit(0);
}

try {
  appendFileSync(sink, line + "\n");
  console.log(`product-idea-capture: logged ${type} → ${sink}`);
  console.log(line);
} catch (e) {
  console.error("product-idea-capture: write failed:", e.message);
  process.exit(1);
}
