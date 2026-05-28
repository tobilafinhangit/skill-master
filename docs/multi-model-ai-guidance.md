# Multi-Model AI: Providers, Routing & Evaluation — Portable Guidance

Repo-agnostic lessons for any project that calls an LLM and might want to switch
models or providers later. Written from the VettedAI resume-screening eval
(Fizzy #1168, 2026-05), but the principles transfer. VettedAI-specific names are
marked *(example)*.

---

## 1. Don't hardcode the provider. Put one adapter between your code and the model.

The single highest-leverage decision: route every model call through a thin
**provider abstraction**, not a direct SDK call. The abstraction takes a config
tuple and returns a uniform response:

```
{ provider, model, apiKey, baseUrl, temperature, maxTokens, timeoutMs }  →  { content, usage, finishReason }
```

- **Most providers are OpenAI-API-compatible** (OpenRouter, OpenCode, Groq, DeepSeek,
  Together, Mistral, Qwen, local vLLM/Ollama). One `OpenAICompatibleProvider` that
  POSTs to `{baseUrl}/chat/completions` covers all of them — **adding a new service
  is a config tuple, zero code.**
- Only genuinely different APIs (Gemini's native multimodal, Anthropic's
  messages API) need their own ~150–200 line adapter.
- *(example: VettedAI `supabase/functions/_shared/agent-llm/` — `GeminiProvider`,
  `OpenAICompatibleProvider`, `createProvider()` factory.)*

**The trap:** having the abstraction is not the same as using it. If your call
sites still `import GoogleGenerativeAI` directly, switching is still a code edit
in N places. The abstraction only pays off once call sites go through it.

## 2. A "router" is just a task→model map your call sites read instead of hardcoding.

Once calls go through the adapter, add a lookup: `task → {provider, model, params}`,
stored in config or a DB table. Call sites ask the router "what model for task X?"
and never name a model themselves. Then switching a model — or A/B-ing two — is a
data change, not a deploy.

Sequence it right: **build the router *after* you know which models are worth
routing to.** Migrating call sites onto a router you can't yet populate with vetted
models is premature.

## 3. Always evaluate a new model against real data before trusting it. Build a shadow harness.

Never swap a model on vibes. The pattern that works:

1. **Snapshot a real cohort** from production (stratified across the output range —
   don't just test the easy middle).
2. **Reuse the EXACT production prompt + post-processing** (guardrails, score
   normalization). Copy it verbatim; a "close enough" prompt invalidates the comparison.
3. **Feed every candidate model the identical input**, and use your current prod
   output as the **baseline** row.
4. **Measure**: mean abs delta vs baseline, decision-agreement %, latency, tokens/cost.
   Persist results to a table so you can re-run as models change and diff over time.
5. It's **read-only** — it never touches the production path.

This makes "should we switch?" an evidence question, not an argument.

## 4. Reasoning vs non-reasoning is the #1 deployment variable. Know which you have.

This caught us out and is the most transferable lesson:

- **Reasoning models** (DeepSeek-R/V-reasoning, GPT-5 nano/mini, Qwen-3 "plus",
  GLM-5, MiniMax, most 2025+ "frontier" models) spend hidden output tokens
  *thinking* before answering. On a real judgment task they take **15–70s/call**
  and burn 200–600+ reasoning tokens — even when the visible answer is tiny.
- **Non-reasoning models** (Llama-3.3-70b, Mistral-small, Gemini *flash*/*flash-lite*,
  Qwen-2.5) answer directly — **1–5s/call.**

Implications:
- For **latency/throughput-bound** work (real-time scoring, high-volume batch,
  anything a user waits on), demand non-reasoning. A reasoning model will quietly
  reintroduce throughput problems. *(VettedAI example: a reasoning model at 30s/resume
  would undo the screening-throughput fix from #1154/#1163.)*
- Reasoning is task-triggered: a model can return instantly on "echo this JSON" and
  then reason for 30s on "score this candidate." **Test on a realistic task, not a toy.**
- Some platforms **mandate reasoning** and ignore `reasoning_effort:none` /
  `enable_thinking:false` — verify, don't assume you can turn it off.
- `max_tokens` must cover **reasoning + the visible answer**, or the model spends the
  whole budget thinking and returns **empty content**. Budget generously (8k+) for
  reasoning models.

## 5. Provider notes (2026-05; verify pricing/availability live — it churns)

- **OpenRouter** (`https://openrouter.ai/api/v1`) — one key → 300+ models, OpenAI-compatible.
  Has genuinely **fast cheap non-reasoning** options (`google/gemini-2.5-flash-lite`,
  `meta-llama/llama-3.3-70b-instruct`, `mistralai/mistral-small-24b`) at ~$0.05–0.40 / 1M tokens.
  Also a `:free` tier — but rate-limited (~20 req/min) and many free models reason. Best
  default for "try lots of models cheaply."
- **OpenCode Zen** (`https://opencode.ai/zen/v1`, curated set at `/zen/go/v1`) — strong for
  *agentic/coding* workloads, but **reasoning-mandatory** (can't disable) → slow for
  classification. Its "free" models rotate and **promos end without warning** mid-use.
  Good for agents, poor for latency-bound classification.
- **Gemini flash / flash-lite** — fast, cheap, non-reasoning; strong baseline for
  scoring/extraction. flash-lite is the cheap downgrade from flash.

## 6. Gotchas that cost real debugging time

- **Default HTTP client User-Agent gets blocked.** `python-urllib` → 403 on some
  providers (Cloudflare bot rules); curl's UA passes. Always set an explicit `User-Agent`.
- **Models wrap JSON in ```markdown``` fences.** Strip code-block wrappers before
  `JSON.parse`, even when you say "return ONLY JSON."
- **Always set a per-call timeout** (`AbortSignal.timeout`). One hung model call will
  otherwise wedge a whole batch indefinitely.
- **Input parity matters for fair eval.** If prod sends a *PDF/image* (multimodal) and
  your candidate model only takes *text*, you're comparing "text scoring" to "PDF
  scoring," not model vs model. Expect a systematic bias; note it, or feed the same
  modality. *(VettedAI: prod reads the resume PDF; text-only models scored ~10–25 pts
  lower — mostly this asymmetry, not quality.)*
- **Cost = per-1M input + per-1M output, billed separately.** Reasoning tokens count as
  output. A "cheap" reasoning model can cost more per useful answer than a pricier fast one.
- **Verify the model actually emits content**, not just a 200. Reasoning models with a
  too-small `max_tokens` return `finish_reason: length` and empty content.

## 7. Minimum viable setup for a new AI project

1. One provider adapter (start with OpenAI-compatible; add native adapters only as needed).
2. A task→model config (even a flat map in code is fine to start; promote to a DB
   table when you have >1 task or want runtime switching).
3. A shadow-eval script before any model change (§3).
4. Per-call timeout + markdown-strip + explicit User-Agent baked into the adapter.

That's enough to "drop in a new service, test it against real data, and switch by
config" — which is the whole goal.
