"""
DEMO 2 - LangGraph (Gemini)
===========================
Graph berstate dengan LOOP revisi:
    tulis -> nilai -> (skor < 8 dan putaran < 3 ? kembali ke tulis : selesai)

    python demo/02_langgraph_demo.py
"""

import operator
import re
import uuid
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from config import HEMAT, llm_dengan_fallback, teks

BATAS_SKOR = 8
# Mode hemat: cukup 1 putaran (2 request). Penuh: sampai 3 putaran (6 request).
BATAS_PUTARAN = 1 if HEMAT else 3


class State(TypedDict):
    topik: str
    draf: str
    skor: int
    kritik: str
    putaran: int
    log: Annotated[list[str], operator.add]  # reducer: digabung, bukan ditimpa


def build(lapor=None):
    llm, _model = llm_dengan_fallback(lapor=lapor)

    def node_tulis(s: State) -> dict:
        kritik = s.get("kritik") or ""
        tambahan = f"\n\nPerbaiki berdasarkan kritik: {kritik}" if kritik else ""
        draf = teks(llm.invoke(
            f"Tulis paragraf 100 kata Bahasa Indonesia tentang '{s['topik']}'.{tambahan}"
        ))
        return {
            "draf": draf,
            "putaran": s.get("putaran", 0) + 1,
            "log": [f"tulis#{s.get('putaran', 0) + 1}"],
        }

    def node_nilai(s: State) -> dict:
        hasil = teks(llm.invoke(
            "Nilai teks berikut 1-10 lalu beri 1 kalimat kritik.\n"
            "Format WAJIB persis:\nSKOR: <angka>\nKRITIK: <teks>\n\n" + s["draf"]
        ))
        m = re.search(r"SKOR:\s*(\d+)", hasil, re.I)
        skor = int(m.group(1)) if m else 5
        k = re.search(r"KRITIK:\s*(.+)", hasil, re.I)
        kritik = k.group(1).strip() if k else hasil.strip()
        return {"skor": skor, "kritik": kritik, "log": [f"nilai={skor}"]}

    def rute(s: State) -> str:
        if s["skor"] >= BATAS_SKOR or s["putaran"] >= BATAS_PUTARAN:
            return "selesai"
        return "revisi"

    g = StateGraph(State)
    g.add_node("tulis", node_tulis)
    g.add_node("nilai", node_nilai)
    g.add_edge(START, "tulis")
    g.add_edge("tulis", "nilai")
    g.add_conditional_edges("nilai", rute, {"revisi": "tulis", "selesai": END})
    return g.compile(checkpointer=MemorySaver())


def jalankan(topik: str, thread_id: str | None = None):
    """Generator event untuk UI, streaming per node."""
    catatan = []
    app = build(lapor=catatan.append)
    for c in catatan:
        yield "step", c
    # thread_id unik supaya checkpoint tiap run tidak tercampur
    cfg = {"configurable": {"thread_id": thread_id or uuid.uuid4().hex[:8]}}
    akhir = {}
    jejak: list[str] = []  # log dikumpulkan sendiri; update() akan menimpanya

    for event in app.stream({"topik": topik, "putaran": 0}, cfg):
        for nama_node, out in event.items():
            jejak += out.get("log", [])
            akhir.update(out)
            if nama_node == "tulis":
                yield "step", f"Node `tulis` - putaran {out['putaran']}"
                yield "token", out["draf"]
            elif nama_node == "nilai":
                yield "step", f"Node `nilai` - skor {out['skor']}/10"
                yield "token", f"Kritik: {out['kritik']}"

    berhenti_karena_batas = (
        akhir.get("skor", 0) < BATAS_SKOR and akhir.get("putaran", 0) >= BATAS_PUTARAN
    )
    yield "step", "Berhenti (batas putaran)" if berhenti_karena_batas else "Selesai"
    yield "token", (
        f"\n**Skor akhir:** {akhir.get('skor')} | "
        f"**Putaran:** {akhir.get('putaran')}\n\n"
        f"**Jejak node:** {' -> '.join(jejak)}"
    )
    yield "done", ""


def main():
    for tipe, teks in jalankan("AI Agent untuk UMKM di Indonesia"):
        if tipe == "step":
            print(f"\n\n=== {teks} ===")
        elif tipe == "token":
            print(teks)
    print("\n=== GRAPH ===")
    print(build().get_graph().draw_ascii())


if __name__ == "__main__":
    main()
