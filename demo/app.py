"""
Backend FastAPI untuk UI demo.
Streaming Server-Sent Events dari ketiga framework.

    .venv/bin/uvicorn app:app --reload --port 8000 --app-dir demo
atau
    .venv/bin/python demo/app.py
"""

import asyncio
import importlib
import json
import queue
import re
import sys
import threading
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse

import config

HERE = Path(__file__).resolve().parent

app = FastAPI(title="Demo LangChain vs LangGraph vs CrewAI")

MODUL = {
    "langchain": "01_langchain_demo",
    "langgraph": "02_langgraph_demo",
    "crewai": "03_crewai_demo",
}


def _sse(tipe: str, data) -> str:
    return f"data: {json.dumps({'type': tipe, 'data': data}, ensure_ascii=False)}\n\n"


@app.get("/")
def index():
    return FileResponse(HERE / "static" / "index.html")


@app.get("/api/status")
def status():
    habis = config._habis_hari_ini()
    hasil = {
        "model": config.MODEL,
        "model_aktif": config.model_tersedia(),
        "hemat": config.HEMAT,
        "habis": sorted(habis),
        "sisa_model": len([m for m in config.rantai_model() if m not in habis]),
        "total_model": len(config.rantai_model()),
        "api_key_ok": False,
        "frameworks": {},
    }
    try:
        config.api_key()
        hasil["api_key_ok"] = True
    except RuntimeError as e:
        hasil["pesan"] = str(e)

    for nama, paket in [
        ("langchain", "langchain_google_genai"),
        ("langgraph", "langgraph"),
        ("crewai", "crewai"),
    ]:
        try:
            importlib.import_module(paket)
            hasil["frameworks"][nama] = True
        except Exception:
            hasil["frameworks"][nama] = False
    return hasil


def _pesan_ramah(e: Exception) -> str:
    t = f"{type(e).__name__}: {e}"
    low = t.lower()
    if "api_key_invalid" in low or "api key not valid" in low:
        return (
            "API key Gemini tidak valid.\n"
            "Cek isi GOOGLE_API_KEY di file .env, lalu restart server.\n"
            "Ambil key baru di https://aistudio.google.com/apikey"
        )
    if "503" in low or "unavailable" in low or "high demand" in low:
        return (
            f"Server Gemini sedang sibuk untuk model '{config.MODEL}'.\n"
            "Ini biasanya sementara. Coba lagi sebentar lagi, atau ganti "
            "GEMINI_MODEL di .env ke gemini-3.5-flash / gemini-2.5-flash."
        )
    if "429" in low or "quota" in low or "rate limit" in low:
        return (
            "Kuota Gemini habis atau kena rate limit.\n"
            "Tunggu sekitar satu menit, lalu jalankan framework satu per satu "
            "(jangan tekan 'Jalankan Semua')."
        )
    if "not found" in low or "404" in low or "no longer available" in low:
        # Google biasanya menyebut model penggantinya di pesan error
        saran = re.search(r"use\s+models/([\w.\-]+)", t)
        if saran:
            return (
                f"Model '{config.MODEL}' sudah tidak tersedia.\n"
                f"Google menyarankan: {saran.group(1)}\n\n"
                f"Ubah di .env:  GEMINI_MODEL={saran.group(1)}\n"
                "lalu restart server."
            )
        return (
            f"Model '{config.MODEL}' tidak ditemukan. "
            "Ganti GEMINI_MODEL di .env, misalnya gemini-3.6-flash."
        )
    return t[:800]


@app.get("/api/run")
async def run(framework: str, topik: str = "AI Agent untuk UMKM di Indonesia"):
    if framework not in MODUL:
        return StreamingResponse(
            iter([_sse("error", "framework tidak dikenal")]),
            media_type="text/event-stream",
        )

    async def gen():
        q: queue.Queue = queue.Queue()

        def worker():
            try:
                config.api_key()
                mod = importlib.import_module(MODUL[framework])
                for tipe, teks in mod.jalankan(topik):
                    q.put((tipe, teks))
            except RuntimeError as e:
                # error konfigurasi: pesannya sudah ramah, tanpa traceback
                q.put(("error", str(e)))
            except Exception as e:
                traceback.print_exc()
                if config._kuota_habis(e):
                    # catat model yang habis (nama diambil dari pesan Google)
                    # supaya run berikutnya langsung memakai cadangan
                    config._tandai_habis(
                        config.model_dari_error(e) or config.model_tersedia()
                    )
                q.put(("error", _pesan_ramah(e)))
            finally:
                q.put((None, None))

        threading.Thread(target=worker, daemon=True).start()

        loop = asyncio.get_running_loop()
        while True:
            tipe, teks = await loop.run_in_executor(None, q.get)
            if tipe is None:
                break
            yield _sse(tipe, teks)
        yield _sse("end", "")

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    import os

    import uvicorn

    port = int(os.getenv("PORT", "8765"))
    print(f"\n  Buka di browser: http://127.0.0.1:{port}\n")
    uvicorn.run(app, host="127.0.0.1", port=port)
