"""
DEMO 4 - SIMULASI OFFLINE (tanpa API key, tanpa internet)
=========================================================
Meniru pola pikir ketiga framework dengan "LLM palsu" supaya perbedaan
ARSITEKTUR-nya terlihat jelas. Berguna untuk memahami konsep dulu
sebelum memasang API key.

    python demo/04_simulasi_offline.py
"""

import random

random.seed(7)


def fake_llm(prompt: str) -> str:
    return f"[jawaban LLM untuk: {prompt[:60]}...]"


# =====================================================================
# POLA 1 - LANGCHAIN: pipeline linear, komposisi fungsi
# =====================================================================
def pola_langchain(topik: str) -> str:
    print("\n--- POLA LANGCHAIN (chain linear) ---")
    langkah = [
        lambda x: f"Prompt: jelaskan {x}",  # prompt template
        fake_llm,                            # llm
        lambda x: x.strip().upper(),         # output parser
    ]
    nilai = topik
    for i, f in enumerate(langkah, 1):
        nilai = f(nilai)
        print(f"  step {i}: {nilai[:70]}")
    return nilai


# =====================================================================
# POLA 2 - LANGGRAPH: state machine, ada loop + percabangan
# =====================================================================
def pola_langgraph(topik: str) -> dict:
    print("\n--- POLA LANGGRAPH (graph berstate + loop) ---")
    state = {"topik": topik, "draf": "", "skor": 0, "putaran": 0, "log": []}

    def node_tulis(s):
        s["draf"] = fake_llm(f"tulis tentang {s['topik']} (revisi ke-{s['putaran']})")
        s["putaran"] += 1
        s["log"].append("tulis")
        return s

    def node_nilai(s):
        s["skor"] = random.randint(4, 10)
        s["log"].append(f"nilai={s['skor']}")
        return s

    def rute(s):
        return "selesai" if s["skor"] >= 8 or s["putaran"] >= 3 else "tulis"

    node = "tulis"
    while node != "selesai":
        state = node_nilai(node_tulis(state))
        node = rute(state)
        print(f"  putaran {state['putaran']} skor {state['skor']} -> {node}")
    print("  jejak:", " -> ".join(state["log"]))
    return state


# =====================================================================
# POLA 3 - CREWAI: tim berperan, output diestafetkan
# =====================================================================
def pola_crewai(topik: str) -> str:
    print("\n--- POLA CREWAI (tim role-based, estafet konteks) ---")
    tim = [
        ("Peneliti", "kumpulkan fakta"),
        ("Penulis", "susun artikel"),
        ("Editor", "poles akhir"),
    ]
    konteks = topik
    for role, tugas in tim:
        konteks = fake_llm(f"[{role}] {tugas} dari: {konteks}")
        print(f"  {role:<9}-> {konteks[:70]}")
    return konteks


if __name__ == "__main__":
    topik = "AI Agent untuk UMKM"
    pola_langchain(topik)
    pola_langgraph(topik)
    pola_crewai(topik)
    print(
        "\nRINGKASAN:\n"
        "  LangChain = pipa lurus   (deterministik, mudah didebug)\n"
        "  LangGraph = mesin state  (loop, cabang, retry, resume)\n"
        "  CrewAI    = tim manusia  (delegasi peran, cepat dibuat)"
    )
