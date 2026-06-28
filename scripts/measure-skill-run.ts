#!/usr/bin/env -S deno run --allow-read --allow-env
/**
 * measure-skill-run.ts — read a Claude Code session transcript and report the
 * context / token cost of a run, so batch-skill changes (qa-failed-triage,
 * pr-review bulk, …) can be measured before/after instead of guessed at.
 *
 * Usage (from a consumer repo that has the skill-master submodule):
 *   deno run --allow-read --allow-env \
 *     submodules/skill-master/scripts/measure-skill-run.ts \
 *     [transcript.jsonl] [--cards N] [--window N] [--label "..."]
 *
 * (From inside the skill-master repo itself, drop the submodules/skill-master/ prefix.)
 *
 * With no path it picks the most-recently-modified *.jsonl transcript for the
 * current working directory's project (~/.claude/projects/<cwd-slug>/).
 *
 * The metric that matters for crashes is **parent peak context** — the largest
 * single-turn context the MAIN agent had to read. When a bulk skill blows up, it
 * is the main window hitting the ceiling, not the subagents. A good fan-out keeps
 * parent peak roughly flat while pushing the heavy reads into sidechain
 * (subagent) turns — so we report parent and sidechain separately on purpose.
 *
 * Metrics per turn use the transcript's `message.usage`:
 *   read  = input_tokens + cache_read_input_tokens + cache_creation_input_tokens
 *           (everything the model had to read that turn ≈ context occupancy)
 *   out   = output_tokens (generative spend that turn)
 */

interface Usage {
  input_tokens?: number;
  output_tokens?: number;
  cache_read_input_tokens?: number;
  cache_creation_input_tokens?: number;
}

function fmt(n: number): string {
  return n.toLocaleString("en-US");
}

function parseArgs(argv: string[]) {
  let path: string | undefined;
  let cards: number | undefined;
  let window = 200_000;
  let label = "";
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--cards") cards = Number(argv[++i]);
    else if (a === "--window") window = Number(argv[++i]);
    else if (a === "--label") label = argv[++i];
    else if (!a.startsWith("--")) path = a;
  }
  return { path, cards, window, label };
}

function projectDir(cwd: string): string {
  const home = Deno.env.get("HOME") ?? "";
  // Claude Code slugs the cwd by replacing '/' and '.' with '-'.
  const slug = cwd.replace(/[/.]/g, "-");
  return `${home}/.claude/projects/${slug}`;
}

async function latestTranscript(dir: string): Promise<string | undefined> {
  let best: { path: string; mtime: number } | undefined;
  try {
    for await (const e of Deno.readDir(dir)) {
      if (!e.isFile || !e.name.endsWith(".jsonl")) continue;
      const p = `${dir}/${e.name}`;
      const st = await Deno.stat(p);
      const m = st.mtime?.getTime() ?? 0;
      if (!best || m > best.mtime) best = { path: p, mtime: m };
    }
  } catch {
    return undefined;
  }
  return best?.path;
}

async function main() {
  const { path: argPath, cards, window, label } = parseArgs(Deno.args);

  let path = argPath;
  if (!path) {
    const dir = projectDir(Deno.cwd());
    path = await latestTranscript(dir);
    if (!path) {
      console.error(`No transcript path given and none found under ${dir}`);
      console.error(`Pass a path explicitly: measure-skill-run.ts <session>.jsonl`);
      Deno.exit(1);
    }
  }

  let text: string;
  try {
    text = await Deno.readTextFile(path);
  } catch (e) {
    console.error(`Could not read ${path}: ${e instanceof Error ? e.message : e}`);
    Deno.exit(1);
  }

  let parentPeak = 0;
  let parentTurns = 0;
  let sideTurns = 0;
  let parentRead = 0;
  let parentOut = 0;
  let sideRead = 0;
  let sideOut = 0;
  let sidePeak = 0;

  for (const line of text.split("\n")) {
    if (!line.trim()) continue;
    let o: Record<string, unknown>;
    try {
      o = JSON.parse(line);
    } catch {
      continue;
    }
    const msg = (o.message ?? {}) as { usage?: Usage };
    const u: Usage | undefined = msg.usage ?? (o.usage as Usage | undefined);
    if (!u) continue;
    const read =
      (u.input_tokens ?? 0) +
      (u.cache_read_input_tokens ?? 0) +
      (u.cache_creation_input_tokens ?? 0);
    const out = u.output_tokens ?? 0;
    const isSide = o.isSidechain === true;
    if (isSide) {
      sideTurns++;
      sideRead += read;
      sideOut += out;
      if (read > sidePeak) sidePeak = read;
    } else {
      parentTurns++;
      parentRead += read;
      parentOut += out;
      if (read > parentPeak) parentPeak = read;
    }
  }

  const totalOut = parentOut + sideOut;
  const pct = (n: number) => ((100 * n) / window).toFixed(1) + "%";

  console.log("");
  console.log(`measure-skill-run${label ? ` — ${label}` : ""}`);
  console.log(`transcript: ${path}`);
  console.log("─".repeat(60));
  console.log(`turns: ${fmt(parentTurns)} parent · ${fmt(sideTurns)} sidechain (subagent)`);
  console.log("");
  console.log(`PARENT peak context : ${fmt(parentPeak)} tok  (${pct(parentPeak)} of ${fmt(window)} window)`);
  console.log(`   ^ the crash metric — keep this flat across batch size`);
  console.log(`sidechain peak ctx  : ${fmt(sidePeak)} tok  (per-subagent, disposable)`);
  console.log("");
  console.log(`output tokens       : ${fmt(totalOut)}  (${fmt(parentOut)} parent · ${fmt(sideOut)} subagent)`);
  console.log(`context read (sum)   : ${fmt(parentRead + sideRead)}  (${fmt(parentRead)} parent · ${fmt(sideRead)} subagent)`);
  if (cards && cards > 0) {
    console.log("");
    console.log(`per-card (n=${cards}):`);
    console.log(`   output/card       : ${fmt(Math.round(totalOut / cards))} tok`);
    console.log(`   parent-read/card  : ${fmt(Math.round(parentRead / cards))} tok`);
  }
  console.log("");
  console.log(
    `Compare runs: a healthy fan-out keeps PARENT peak ~constant as cards grow;`,
  );
  console.log(
    `a leaking one grows parent peak with every card and eventually crashes.`,
  );
  console.log("");
}

await main();
