"""
DEMO 2 - LangGraph
==================
Fokus: GRAPH berstate. Node + edge + kondisi + loop + memory.
Cocok untuk: agent yang perlu retry, self-correction, human-in-the-loop, branching.

Demo: penulis artikel dengan loop revisi.
  tulis -> nilai -> (skor < 8 ? revisi : selesai)

Jalankan:
    pip install langgraph langchain-openai
    export OPENAI_API_KEY=sk-...
    python 02_langgraph_demo.py
"""

from typing import TypedDict, Annotated
import operator

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


# --- STATE: data bersama yang mengalir antar node ---
class State(TypedDict):
    topik: str
    draf: str
    skor: int
    kritik: str
    putaran: int
    log: Annotated[list[str], operator.add]  # reducer: list digabung, bukan ditimpa


# --- NODE ---
def node_tulis(state: State) -> dict:
    kritik = state.get("kritik", "")
    instruksi = f"\n\nPerbaiki berdasarkan kritik ini: {kritik}" if kritik else ""
    draf = llm.invoke(
        f"Tulis paragraf 100 kata tentang '{state['topik']}'.{instruksi}"
    ).content
    return {"draf": draf, "putaran": state.get("putaran", 0) + 1, "log": ["tulis"]}


def node_nilai(state: State) -> dict:
    hasil = llm.invoke(
        "Nilai teks berikut 1-10 lalu beri 1 kalimat kritik.\n"
        "Format WAJIB: SKOR: <angka>\nKRITIK: <teks>\n\n" + state["draf"]
    ).content
    skor = 5
    kritik = hasil
    for baris in hasil.splitlines():
        if baris.upper().startswith("SKOR:"):
            try:
                skor = int("".join(c for c in baris if c.isdigit())[:2])
            except ValueError:
                pass
        if baris.upper().startswith("KRITIK:"):
            kritik = baris.split(":", 1)[1].strip()
    return {"skor": skor, "kritik": kritik, "log": [f"nilai={skor}"]}


# --- CONDITIONAL EDGE: inti pembeda LangGraph ---
def rute(state: State) -> str:
    if state["skor"] >= 8 or state["putaran"] >= 3:
        return "selesai"
    return "revisi"


graph = StateGraph(State)
graph.add_node("tulis", node_tulis)
graph.add_node("nilai", node_nilai)
graph.add_edge(START, "tulis")
graph.add_edge("tulis", "nilai")
graph.add_conditional_edges("nilai", rute, {"revisi": "tulis", "selesai": END})

# --- MEMORY / CHECKPOINT: bisa pause, resume, time-travel ---
app = graph.compile(checkpointer=MemorySaver())


def main():
    config = {"configurable": {"thread_id": "demo-1"}}
    hasil = app.invoke({"topik": "AI Agent untuk UMKM", "putaran": 0}, config)

    print("=== HASIL ===")
    print(hasil["draf"])
    print("\nSkor akhir :", hasil["skor"])
    print("Putaran    :", hasil["putaran"])
    print("Jejak node :", " -> ".join(hasil["log"]))

    print("\n=== ASCII GRAPH ===")
    print(app.get_graph().draw_ascii())


if __name__ == "__main__":
    main()
