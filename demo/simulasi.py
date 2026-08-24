"""Mode simulasi: jalan tanpa API key / saat kuota habis.

Meniru alur ketiga framework dengan "LLM palsu" supaya perbedaan
ARSITEKTUR tetap terlihat walau Gemini tidak bisa dipanggil.
Event yang dihasilkan sama persis dengan modul asli: (tipe, teks).
"""

import random
import time

BANNER = (
    "**MODE SIMULASI** - tanpa API key, jawaban dibuat lokal (bukan dari Gemini).\n"
    "Isi `GOOGLE_API_KEY` di `.env` lalu restart untuk jawaban asli."
)


def _fake_llm(prompt: str, topik: str) -> str:
    return (
        f"(simulasi) Ringkasan tentang **{topik}**:\n"
        f"- Poin 1 hasil dari langkah: {prompt}\n"
        f"- Poin 2: contoh penerapan nyata\n"
        f"- Poin 3: risiko dan cara mengurangi\n"
    )


def _ketik(teks: str, jeda: float = 0.012):
    """Streaming per kata supaya UI terasa seperti run asli."""
    for kata in teks.split(" "):
        yield "token", kata + " "
        time.sleep(jeda)


def langchain(topik: str):
    yield "step", BANNER
    yield "step", "Chain linear: `prompt | llm | parser`"
    yield from _ketik(_fake_llm("prompt -> llm -> parser", topik))
    yield "step", "Chain bersusun: output chain pertama jadi input chain kedua"
    yield from _ketik(_fake_llm("chain bersusun (refine)", topik))
    yield "done", ""


def langgraph(topik: str):
    rng = random.Random(7)
    yield "step", BANNER
    yield "step", "Graph berstate: node `tulis` -> `nilai` -> rute (loop sampai skor >= 8)"
    putaran, skor = 0, 0
    while skor < 8 and putaran < 3:
        putaran += 1
        skor = rng.randint(4, 10)
        yield "step", f"Putaran {putaran}: node tulis -> node nilai (skor {skor})"
        yield from _ketik(_fake_llm(f"draf revisi ke-{putaran}", topik))
    yield "step", f"Rute selesai setelah {putaran} putaran (skor akhir {skor})"
    yield "done", ""


def crewai(topik: str):
    yield "step", BANNER
    yield "step", "Tim berperan: Peneliti -> Penulis -> Editor (konteks diestafetkan)"
    for peran, tugas in [
        ("Peneliti", "kumpulkan fakta"),
        ("Penulis", "susun artikel"),
        ("Editor", "poles akhir"),
    ]:
        yield "step", f"**{peran}**: {tugas}"
        yield from _ketik(_fake_llm(f"[{peran}] {tugas}", topik))
    yield "done", ""


PETA = {"langchain": langchain, "langgraph": langgraph, "crewai": crewai}


def jalankan(framework: str, topik: str):
    return PETA[framework](topik)
