"""Konfigurasi bersama: load .env dan sediakan LLM Gemini."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


def api_key() -> str:
    key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not key or key.startswith("isi_api_key"):
        raise RuntimeError(
            "GOOGLE_API_KEY belum diisi.\n"
            "1. cp .env.example .env\n"
            "2. isi GOOGLE_API_KEY dari https://aistudio.google.com/apikey"
        )
    return key


def get_llm(temperature: float = 0.3):
    """LLM untuk LangChain / LangGraph."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=MODEL, temperature=temperature, google_api_key=api_key()
    )


def crewai_llm(temperature: float = 0.3):
    """LLM untuk CrewAI (lewat LiteLLM, butuh prefix 'gemini/')."""
    from crewai import LLM

    os.environ.setdefault("GEMINI_API_KEY", api_key())
    return LLM(model=f"gemini/{MODEL}", temperature=temperature)
