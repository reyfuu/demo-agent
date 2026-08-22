"""Konfigurasi bersama: load .env dan sediakan LLM Gemini."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")

# Free tier Gemini punya kuota PER MODEL (sekitar 20 request/hari/model).
# Kalau model utama habis kuota, otomatis geser ke model berikutnya.
CADANGAN = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
]

# Kalau keduanya diset, SDK Google memunculkan warning. Samakan saja.
if os.getenv("GOOGLE_API_KEY"):
    os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]


def rantai_model() -> list[str]:
    """Model utama dulu, lalu cadangan (tanpa duplikat)."""
    urut = [MODEL] + [m for m in CADANGAN if m != MODEL]
    return urut


def _kuota_habis(e: Exception) -> bool:
    t = f"{type(e).__name__}: {e}".lower()
    return "429" in t or "resource_exhausted" in t or "quota" in t


def api_key() -> str:
    key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not key or key.startswith("isi_api_key"):
        raise RuntimeError(
            "GOOGLE_API_KEY belum diisi.\n"
            "1. cp .env.example .env\n"
            "2. isi GOOGLE_API_KEY dari https://aistudio.google.com/apikey"
        )
    return key


def get_llm(temperature: float = 0.3, model: str | None = None):
    """LLM untuk LangChain / LangGraph."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=model or MODEL,
        temperature=temperature,
        google_api_key=api_key(),
        max_retries=3,  # tahan banting saat 503 "high demand"
    )


_terpilih = {}  # cache: temperature -> (llm, nama_model)


def llm_dengan_fallback(temperature: float = 0.3, lapor=None):
    """Kembalikan (llm, nama_model) memakai model pertama yang kuotanya masih ada.

    Hasil probe di-cache per proses supaya tidak memboroskan kuota
    free tier (sekitar 20 request per hari per model).
    """
    if temperature in _terpilih:
        llm, m = _terpilih[temperature]
        if lapor and m != MODEL:
            lapor(f"Kuota `{MODEL}` habis, memakai `{m}`.")
        return llm, m

    terakhir = None
    for m in rantai_model():
        try:
            llm = get_llm(temperature, model=m)
            llm.invoke("hai")  # probe sekali saja, lalu di-cache
            _terpilih[temperature] = (llm, m)
            if lapor and m != MODEL:
                lapor(f"Kuota `{MODEL}` habis, otomatis memakai `{m}`.")
            return llm, m
        except Exception as e:  # noqa: BLE001
            terakhir = e
            low = f"{e}".lower()
            if _kuota_habis(e) or "not_found" in low or "404" in low:
                continue
            raise
    raise terakhir if terakhir else RuntimeError("tidak ada model tersedia")


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
