# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A side-by-side demo of three AI-agent frameworks — **LangChain**, **LangGraph**, **CrewAI** — all running the same topic through **Google Gemini**, with a FastAPI backend that streams each run live into a three-panel web UI. Everything (code, docs, identifiers) is in Bahasa Indonesia.

## Commands

```bash
./run.sh                      # main entry: picks a compatible Python, builds .venv, installs, runs server
PORT=9000 ./run.sh            # override port (default 8765)
```

`run.sh` is idempotent — it only creates the venv / installs when missing. Server then serves http://127.0.0.1:8765.

Run one framework from the CLI (each module is executable):

```bash
.venv/bin/python demo/01_langchain_demo.py
.venv/bin/python demo/02_langgraph_demo.py     # also prints the graph via draw_ascii()
.venv/bin/python demo/03_crewai_demo.py
.venv/bin/python demo/04_simulasi_offline.py   # no API key, no quota
```

History (reads `riwayat.jsonl`, no quota used):

```bash
.venv/bin/python demo/05_lihat_riwayat.py            # last 20
.venv/bin/python demo/05_lihat_riwayat.py langgraph  # filter by framework
.venv/bin/python demo/05_lihat_riwayat.py --id a1b2c3
```

**No test suite, linter, or build step exists.** The CLI entry points above (especially `04_simulasi_offline.py`, which needs no key) are the way to verify changes.

**Python 3.10–3.13 only** — `crewai` does not support 3.14. `run.sh` searches for a compatible interpreter; installing manually under 3.14 fails at build time.

## Architecture

### The event-generator contract (central abstraction)

Every framework module (`01_`, `02_`, `03_`) **and** `simulasi.py` exposes:

```python
def jalankan(topik: str) -> Iterator[tuple[str, str]]:  # yields (tipe, teks)
```

where `tipe` ∈ `"step"` (a labeled stage), `"token"` (streamed output text), `"done"`, `"error"`. `app.py` consumes this generator uniformly and re-emits each event as Server-Sent Events (`_sse`); it never knows anything framework-specific. **When adding a framework or changing a demo, conform to this contract** — the backend, the UI, and history storage all depend on it. The `step`/`token`/`error` events are also what get persisted to history.

Each module also has a `build(...)` that constructs the actual chain/graph/crew, and a `main()` for standalone CLI runs.

### Backend flow (`demo/app.py`)

`GET /api/run?framework=&topik=` runs the chosen module in a **background thread** (frameworks are blocking / sync), bridging its events to the async SSE response through a `queue.Queue` drained via `run_in_executor`. Key behaviors woven into this handler:
- **Simulation fallback**: if `config.api_key()` raises `RuntimeError` (key missing), it swaps in `simulasi.jalankan(...)` so the demo still runs offline. This is why `simulasi.py` must emit the same event shape as the real modules.
- **Quota tracking on error**: on a 429/quota exception it records the exhausted model via `config._tandai_habis(...)` so later runs skip it.
- **History**: after the stream ends, the run is saved via `riwayat.simpan(...)`; a history failure must never break the demo (caught + logged).
- `_pesan_ramah()` converts raw Gemini exceptions (invalid key / 503 / 429 / 404-model-gone) into actionable Indonesian messages.

Other endpoints: `GET /api/status`, `GET /api/riwayat`, `GET /api/riwayat/{id}`, `DELETE /api/riwayat`. UI is a single static file, `demo/static/index.html`.

### Model selection & quota fallback (`demo/config.py`)

Gemini free tier is ~20 requests/day **per model**, so config maintains a fallback chain `CADANGAN` (8 models). Two distinct fallback mechanisms — do not conflate them:
- **LangChain / LangGraph** use `llm_dengan_fallback()` → LangChain's native `with_fallbacks` plus a callback (`Pencatat`) that records any model hit by a 429.
- **CrewAI** has no `with_fallbacks`, so `03_` picks a model up-front via `model_tersedia()` (first model not already exhausted today) and builds `crewai_llm()` (LiteLLM, needs the `gemini/` prefix).

Exhausted models are cached to `.kuota_habis.json` with today's date; the set resets automatically on a new day. Also note:
- On import, config **renames `GOOGLE_API_KEY` → `GEMINI_API_KEY`** (CrewAI/LiteLLM require the latter, and setting both triggers an SDK warning).
- `teks(pesan)` normalizes Gemini responses — newer models return `content` as a list of typed blocks, not a string. Use it whenever reading raw LLM output.

### HEMAT (quota-saver) mode — cross-cutting

`config.HEMAT` (default on; `HEMAT=0` in `.env` for full demos) is read by **all three** demo modules to cut LLM calls: LangChain runs only the basic chain, LangGraph caps at 1 revision loop (`BATAS_PUTARAN`), CrewAI drops to 2 agents / `max_iter=1`. Full run ≈ 20 requests, hemat ≈ 5. Any edit to a demo should preserve both branches.

### History storage (`demo/riwayat.py`)

Append-only JSON Lines at `riwayat.jsonl` (gitignored), one run per line, capped at `MAKS=200`. Writes are lock-guarded and atomic (write `.tmp` then `replace`); malformed lines are skipped on read rather than crashing.

## Config / secrets

`.env` (gitignored) holds `GOOGLE_API_KEY`, optional `GEMINI_MODEL` (default `gemini-3.7-flash`), and `HEMAT`. Copy from `.env.example`. Get a free key at https://aistudio.google.com/apikey.
