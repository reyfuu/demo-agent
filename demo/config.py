"""Konfigurasi bersama: load .env dan sediakan LLM Gemini."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")

# HEMAT=1 (default): pangkas jumlah panggilan LLM per demo.
# Set HEMAT=0 di .env kalau kuota sedang longgar dan ingin demo penuh.
HEMAT = os.getenv("HEMAT", "1").strip().lower() not in ("0", "false", "no")

# Free tier Gemini punya kuota PER MODEL (sekitar 20 request/hari/model).
# Kalau model utama habis kuota, otomatis geser ke model berikutnya.
# Model "lite" ditaruh di urutan atas saat hemat karena limitnya lebih longgar.
CADANGAN = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-flash-lite-latest",
]

# SDK Google memperingatkan kalau GOOGLE_API_KEY dan GEMINI_API_KEY sama-sama
# diset. CrewAI/LiteLLM butuh GEMINI_API_KEY, jadi sisakan satu saja.
if os.getenv("GOOGLE_API_KEY"):
    os.environ["GEMINI_API_KEY"] = os.environ.pop("GOOGLE_API_KEY")


def api_key_mentah() -> str:
    return os.getenv("GEMINI_API_KEY", "").strip()


def rantai_model() -> list[str]:
    """Model utama dulu, lalu cadangan (tanpa duplikat)."""
    urut = [MODEL] + [m for m in CADANGAN if m != MODEL]
    return urut


def _kuota_habis(e: Exception) -> bool:
    t = f"{type(e).__name__}: {e}".lower()
    return "429" in t or "resource_exhausted" in t or "quota" in t


def model_dari_error(e: Exception) -> str | None:
    """Ambil nama model yang kuotanya habis dari pesan error Google."""
    import re

    m = re.search(r"model:\s*([\w.\-]+)", f"{e}")
    return m.group(1) if m else None


def api_key() -> str:
    key = api_key_mentah()
    if not key or key.startswith("isi_api_key"):
        raise RuntimeError(
            "GOOGLE_API_KEY belum diisi.\n"
            "1. cp .env.example .env\n"
            "2. isi GOOGLE_API_KEY dari https://aistudio.google.com/apikey"
        )
    return key


def get_llm(temperature: float = 0.3, model: str | None = None):
    """LLM untuk LangChain / LangGraph (objek asli, aman untuk LCEL `|`)."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=model or MODEL,
        temperature=temperature,
        google_api_key=api_key(),
        max_retries=2,  # tahan banting saat 503 "high demand"
    )


# Catatan model yang kuotanya sudah habis hari ini, disimpan ke disk
# supaya restart server tidak mengulang percobaan yang pasti gagal.
_CACHE = ROOT / ".kuota_habis.json"


def _habis_hari_ini() -> set[str]:
    import datetime
    import json

    try:
        d = json.loads(_CACHE.read_text())
    except Exception:  # noqa: BLE001
        return set()
    if d.get("tanggal") != str(datetime.date.today()):
        return set()  # kuota Gemini reset harian
    return set(d.get("model", []))


def _tandai_habis(model: str) -> None:
    import datetime
    import json

    kumpulan = _habis_hari_ini() | {model}
    try:
        _CACHE.write_text(
            json.dumps(
                {"tanggal": str(datetime.date.today()), "model": sorted(kumpulan)}
            )
        )
    except Exception:  # noqa: BLE001
        pass


def model_tersedia() -> str:
    """Model pertama yang kuotanya belum habis hari ini."""
    habis = _habis_hari_ini()
    for m in rantai_model():
        if m not in habis:
            return m
    return MODEL  # semua habis, coba lagi model utama


def llm_dengan_fallback(temperature: float = 0.3, lapor=None):
    """Kembalikan (llm, nama_model) yang otomatis pindah model saat kuota habis.

    Tanpa probe (probe memboroskan kuota). Memakai `with_fallbacks` bawaan
    LangChain, jadi model cadangan baru dipakai kalau request asli gagal.
    Callback mencatat model yang kena 429 supaya run berikutnya langsung
    melompatinya.
    """
    from langchain_core.callbacks import BaseCallbackHandler

    class Pencatat(BaseCallbackHandler):
        def on_llm_error(self, error, **kw):
            if _kuota_habis(error):
                nama = model_dari_error(error)
                if nama:
                    _tandai_habis(nama)

    habis = _habis_hari_ini()
    urut = [m for m in rantai_model() if m not in habis] or rantai_model()
    utama, sisa = urut[0], urut[1:]

    cb = [Pencatat()]
    llm = get_llm(temperature, model=utama).with_config(callbacks=cb)
    if sisa:
        llm = llm.with_fallbacks(
            [get_llm(temperature, model=m).with_config(callbacks=cb) for m in sisa]
        )

    if lapor and utama != MODEL:
        lapor(f"Kuota `{MODEL}` habis hari ini, memakai `{utama}`.")
    elif lapor and sisa:
        lapor(f"Model `{utama}` (cadangan otomatis: {', '.join(sisa[:2])}).")
    return llm, utama


def crewai_llm(temperature: float = 0.3, model: str | None = None):
    """LLM untuk CrewAI (lewat LiteLLM, butuh prefix 'gemini/')."""
    from crewai import LLM

    os.environ.setdefault("GEMINI_API_KEY", api_key())
    return LLM(model=f"gemini/{model or MODEL}", temperature=temperature)


def teks(pesan) -> str:
    """Ambil teks polos dari respons LLM.

    Model Gemini baru mengembalikan `content` berupa list block
    (mis. [{'type':'text','text':...}]), bukan string. Fungsi ini
    menormalkannya jadi string biasa.
    """
    isi = getattr(pesan, "content", pesan)
    if isinstance(isi, str):
        return isi
    if isinstance(isi, list):
        bagian = []
        for b in isi:
            if isinstance(b, str):
                bagian.append(b)
            elif isinstance(b, dict) and b.get("type") == "text":
                bagian.append(b.get("text", ""))
        return "".join(bagian).strip()
    return str(isi)
