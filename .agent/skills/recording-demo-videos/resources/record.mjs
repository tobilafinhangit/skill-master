/**
 * Demo-recorder engine (template). Copy to <repo>/demo/record.mjs and fill the CONFIG block.
 * Records a silent demo video of the real app by scripting a browser, driven by a FLOW.
 *
 * Run:  bash demo/run.sh <flow>     (run.sh points dev at staging, records, polishes, cleans up)
 * Or:   DEMO_FLOW=<flow> node demo/record.mjs    (with a dev server already on staging)
 *
 * See the recording-demo-videos skill for the gotchas (auth via setSession, staging env, etc.).
 */
import { chromium } from '@playwright/test';
import { createClient } from '@supabase/supabase-js';
import * as fs from 'fs';
import * as path from 'path';

// ─────────────────────────────────────────────────────────────────────────────
// CONFIG — the only repo-specific section. Fill these in.
// ─────────────────────────────────────────────────────────────────────────────
const CONFIG = {
  baseUrl: process.env.DEMO_BASE_URL || 'http://localhost:5173',
  // The STAGING Supabase project to record against (never prod).
  supabaseUrl: process.env.DEMO_SUPABASE_URL || '<https://YOUR-STAGING-ref.supabase.co>',
  // Names of the env vars (in .env.local) holding the staging service + anon/publishable keys.
  serviceKeyEnv: 'DEMO_SERVICE_KEY',   // e.g. VETTED_SUPABASE_KEY / STAGING_CONGRATS_SUPABASE_SERVICE_ROLE_KEY
  anonKeyEnv:    'DEMO_ANON_KEY',      // e.g. VETTED_SUPABASE_ANON_KEY / STAGING_CONGRATS_SUPABASE_ANON_KEY
  // The authorized test/login account (ask the user first).
  email: process.env.DEMO_EMAIL || '<test-account@example.com>',
  // Path Vite serves the app's supabase client at (used to log in in-page). Adjust if different.
  clientModulePath: '/src/integrations/supabase/client.ts',
  // env files to source for the above key env vars
  envFiles: ['.env', '.env.local', '.env.staging'],
  viewport: { width: 1440, height: 900 },
};

// ─────────────────────────────────────────────────────────────────────────────
// FLOWS — one entry per video. Copy a block, change url + steps.
// ─────────────────────────────────────────────────────────────────────────────
const FLOWS = {
  // Public page (no login) — set requiresAuth: false to skip the auth step entirely.
  landing: {
    label: 'landing',
    url: '/',
    requiresAuth: false,
    steps: async (page, ui) => {
      await ui.settle('the landing page', ['<a word on the public page>']);
      await ui.beat(1400);
      await ui.scrollThrough(0.9, 6);
      await ui.beat(1000);
    },
  },
  sample: {
    label: 'sample',
    url: '/',                                   // deep-link to the screen you want to demo
    steps: async (page, ui) => {
      await ui.settle('the page', ['<a word that proves the screen loaded>']);
      await ui.beat(1400);
      await ui.scrollThrough(0.9, 5);
      await ui.beat(800);
      await ui.clickFirst(['a[href*="/detail/"]', '[role="row"]', 'button:has-text("View")']);
      await ui.beat(1600);
      await ui.scrollThrough(0.5, 3);
      await ui.beat(1000);
    },
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Engine (rarely needs editing)
// ─────────────────────────────────────────────────────────────────────────────
for (const f of CONFIG.envFiles) {
  const p = path.join(process.cwd(), f);
  if (!fs.existsSync(p)) continue;
  for (const line of fs.readFileSync(p, 'utf-8').split('\n')) {
    const m = line.trim().match(/^([^#=][^=]*)=(.*)$/);
    if (m && !process.env[m[1].trim()]) process.env[m[1].trim()] = m[2].trim().replace(/^["']|["']$/g, '');
  }
}

const BASE = CONFIG.baseUrl;
const SURL = CONFIG.supabaseUrl;
const SVC = process.env[CONFIG.serviceKeyEnv];
const ANON = process.env[CONFIG.anonKeyEnv];
const REF = (() => { try { return new URL(SURL).host.split('.')[0]; } catch { return ''; } })();
const FLOW = process.env.DEMO_FLOW || Object.keys(FLOWS)[0];
const OUT_DIR = path.join(process.cwd(), 'demo', 'output');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const CURSOR_INIT = `
  (() => {
    const dot = document.createElement('div'); dot.id='__demo_cursor';
    Object.assign(dot.style,{position:'fixed',width:'22px',height:'22px',borderRadius:'50%',
      background:'rgba(124,58,237,0.35)',border:'2px solid #7C3AED',zIndex:2147483647,
      pointerEvents:'none',transform:'translate(-50%,-50%)',transition:'width .08s,height .08s',left:'-50px',top:'-50px'});
    const add=()=>document.body&&document.body.appendChild(dot);
    document.readyState==='loading'?document.addEventListener('DOMContentLoaded',add):add();
    addEventListener('mousemove',e=>{dot.style.left=e.clientX+'px';dot.style.top=e.clientY+'px';},true);
    addEventListener('mousedown',()=>{dot.style.width='34px';dot.style.height='34px';},true);
    addEventListener('mouseup',()=>{dot.style.width='22px';dot.style.height='22px';},true);
  })();
`;

function makeUi(page) {
  return {
    beat: (ms) => page.waitForTimeout(ms),
    async settle(_what, anyOfWords) {
      await page.waitForLoadState('networkidle', { timeout: 25000 }).catch(() => {});
      for (let i = 0; i < 20; i++) {
        const hit = await page.evaluate((w) => w.some((x) => document.body.innerText.includes(x)), anyOfWords).catch(() => false);
        if (hit) break;
        await sleep(500);
      }
    },
    async scrollThrough(fraction, steps) {
      const max = await page.evaluate(() => document.scrollingElement.scrollHeight - window.innerHeight);
      const target = Math.max(0, Math.floor(max * fraction));
      for (let i = 1; i <= steps; i++) {
        await page.evaluate((y) => window.scrollTo({ top: y, behavior: 'smooth' }), Math.floor((target / steps) * i));
        await sleep(900);
      }
      await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
      await sleep(900);
    },
    async clickFirst(selectors) {
      for (const sel of selectors) {
        const el = page.locator(sel).first();
        if (await el.count().catch(() => 0)) {
          const box = await el.boundingBox().catch(() => null);
          if (box) {
            await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 25 });
            await sleep(400);
            await el.click({ timeout: 4000 }).catch(() => {});
            return true;
          }
        }
      }
      return false;
    },
  };
}

async function mintSession() {
  if (!SVC || !ANON) throw new Error(`Missing ${CONFIG.serviceKeyEnv} / ${CONFIG.anonKeyEnv} in .env.local`);
  const admin = createClient(SURL, SVC, { auth: { persistSession: false, autoRefreshToken: false } });
  const gen = await admin.auth.admin.generateLink({ type: 'magiclink', email: CONFIG.email });
  if (gen.error) throw new Error('generateLink: ' + gen.error.message);
  const anon = createClient(SURL, ANON, { auth: { persistSession: false, autoRefreshToken: false } });
  const v = await anon.auth.verifyOtp({ email: CONFIG.email, token: gen.data.properties.email_otp, type: 'email' });
  if (v.error) throw new Error('verifyOtp: ' + v.error.message);
  return v.data.session;
}

async function main() {
  const flow = FLOWS[FLOW];
  if (!flow) throw new Error(`Unknown DEMO_FLOW '${FLOW}'. Known: ${Object.keys(FLOWS).join(', ')}`);
  fs.mkdirSync(OUT_DIR, { recursive: true });

  const needAuth = flow.requiresAuth !== false;
  const session = needAuth ? await (async () => { console.log(`▶ minting session for ${CONFIG.email} …`); return mintSession(); })() : null;

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: CONFIG.viewport, deviceScaleFactor: 2, recordVideo: { dir: OUT_DIR, size: CONFIG.viewport } });
  await context.addInitScript(CURSOR_INIT);
  const page = await context.newPage();
  const recStart = Date.now();

  if (needAuth) {
    // Log in via the app's OWN client (writes the correct storage envelope; see Gotcha 1).
    console.log('▶ establishing session via the app client …');
    await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded' }).catch(() => page.goto(`${BASE}/auth`, { waitUntil: 'domcontentloaded' }));
    await page.waitForTimeout(2500);
    const login = await page.evaluate(async ({ at, rt, mod }) => {
      const m = await import(mod);
      const { data, error } = await m.supabase.auth.setSession({ access_token: at, refresh_token: rt });
      return { user: data?.session?.user?.email || null, err: error?.message || null };
    }, { at: session.access_token, rt: session.refresh_token, mod: CONFIG.clientModulePath });
    if (!login.user) throw new Error('setSession failed: ' + (login.err || 'no user returned'));
    console.log(`   logged in as ${login.user}`);
  }

  const target = `${BASE}${flow.url}`;
  console.log(`▶ recording flow '${FLOW}' at ${target} …`);
  await page.goto(target, { waitUntil: 'domcontentloaded' });
  if (needAuth) {
    let authed = false;
    for (let i = 0; i < 12; i++) { await page.waitForTimeout(700); if (!/\/login|\/auth\//.test(page.url())) { authed = true; break; } }
    if (!authed) throw new Error(`Not authenticated — stuck on ${page.url()}.`);
  }

  await page.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(1500);
  const leadSec = Math.max(0, (Date.now() - recStart) / 1000 - 0.8);

  await flow.steps(page, makeUi(page));

  const video = page.video();
  await context.close();
  await browser.close();
  const named = path.join(OUT_DIR, `${flow.label}.webm`);
  fs.renameSync(await video.path(), named);
  fs.writeFileSync(`${named}.trim`, leadSec.toFixed(1));
  console.log(`✅ raw video: ${named}  (auto-trim ${leadSec.toFixed(1)}s lead-in)`);
  console.log(`   next: bash demo/polish.sh "${named}" "Optional caption"`);
}

main().catch((e) => { console.error('✖', e.message); process.exit(1); });
