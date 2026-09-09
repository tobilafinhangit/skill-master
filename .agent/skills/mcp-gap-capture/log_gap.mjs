#!/usr/bin/env node
// mcp-gap-capture: log a Vetted MCP capability gap to a shared JSONL sink.
// Redacts PII, de-dupes within session, appends one line. No DB, no credentials.

import { readFileSync, appendFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";

// ---- redaction ----
const EMAIL_RE = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
const PHONE_RE = /\+?\d[\d\s().-]{7,}\d/g;
const JWT_RE = /\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g;
const LONG_SECRET_RE = /\b(?:[A-Za-z0-9+/]{40,}={0,2}|[0-9a-fA-F]{48,})\b/g;
const SQL_RE = /\b(?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE\s+TABLE|ALTER\s+TABLE|TRUNCATE)\b/i;

const UUID_RE = /\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b/g;

function redactText(s, maxLen = 200) {
  if (typeof s !== "string") return s;
  let t = s;
  if (SQL_RE.test(t)) return "[sql-omitted]";
  // Mask UUIDs first: digit runs inside them trip the phone pattern, and IDs are
  // explicitly wanted in triage context (repro steps), so they must survive.
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

function normalizeIntent(s) {
  return String(s || "").toLowerCase().replace(/\s+/g, " ").trim();
}

// ---- arg parse (--key value) ----
const args = process.argv.slice(2);
const get = (k) => {
  const i = args.indexOf(`--${k}`);
  return i >= 0 ? args[i + 1] : undefined;
};
const dry = args.includes("--dry");

const intent = get("intent");
const attemptedTool = get("attempted-tool") || "unknown";
const fallbackPath = get("fallback-path") || "other";
const confidence = get("confidence") || "low";
let repo = get("repo") || process.env.MCP_GAP_REPO || "unknown";
const agent = get("agent") || process.env.MCP_GAP_AGENT || "unknown";
const ticket = get("ticket");
// Triage context for the reviewing engineer (all redacted, 1000-char budget).
// repro: minimal steps to hit the gap. expected: what should have happened.
// impact: who is blocked / what it costs (unlocks, sends, manual workarounds).
const repro = get("repro");
const expected = get("expected");
const impact = get("impact");
const sessionId =
  get("session") ||
  process.env.MCP_GAP_SESSION || `sess-${Math.random().toString(36).slice(2, 8)}`;

if (!intent) {
  console.error("mcp-gap-capture: --intent is required");
  process.exit(2);
}

// ---- resolve sink + repo from config ----
function resolveConfig() {
  const cfgPath = resolve(process.cwd(), ".mcp-gap-capture.json");
  if (existsSync(cfgPath)) {
    try {
      return JSON.parse(readFileSync(cfgPath, "utf8"));
    } catch {}
  }
  return {};
}

const cfg = resolveConfig();
const sink =
  get("sink") || cfg.sink || process.env.MCP_GAP_SINK ||
  "/Users/USER/claude-workspace/_tobi_wiki/wiki/mcp-gaps.jsonl";
if (!repo || repo === "unknown") {
  repo = process.env.MCP_GAP_REPO || cfg.repo || "unknown";
}

const record = {
  ts: new Date().toISOString(),
  repo,
  agent,
  session_id: sessionId,
  intent: redactText(intent),
  attempted_tool: attemptedTool,
  fallback_path: fallbackPath,
  confidence,
  ...(ticket ? { ticket } : {}),
  ...(repro ? { repro: redactText(repro, 1000) } : {}),
  ...(expected ? { expected: redactText(expected, 1000) } : {}),
  ...(impact ? { impact: redactText(impact, 1000) } : {}),
};

const line = JSON.stringify(record);

// ---- dedup (compare against the redacted intent already stored) ----
function wouldDup() {
  if (!existsSync(sink)) return false;
  const norm = `${attemptedTool}|${fallbackPath}|${normalizeIntent(record.intent)}`;
  try {
    return readFileSync(sink, "utf8")
      .split("\n")
      .filter(Boolean)
      .some((l) => {
        try {
          const r = JSON.parse(l);
          return (
            `${r.attempted_tool}|${r.fallback_path}|${normalizeIntent(r.intent)}` ===
            norm
          );
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
  console.log(
    `mcp-gap-capture: dedup — skipped (already logged: ${attemptedTool} / ${fallbackPath})`,
  );
  process.exit(0);
}

try {
  appendFileSync(sink, line + "\n");
  console.log(`mcp-gap-capture: logged gap → ${sink}`);
  console.log(line);
} catch (e) {
  console.error("mcp-gap-capture: write failed:", e.message);
  process.exit(1);
}
