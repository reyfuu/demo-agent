"""
DEMO 3 - CrewAI (Gemini)
========================
Tim 3 agent berperan, proses sequential, konteks diestafetkan.

    python demo/03_crewai_demo.py
"""

from crewai import Agent, Crew, Process, Task

from config import HEMAT, MODEL, crewai_llm, model_tersedia


def build(topik: str, lapor=None):
    # CrewAI tidak punya with_fallbacks, jadi pilih model dari catatan kuota
    model = model_tersedia()
    if lapor and model != MODEL:
        lapor(f"Kuota `{MODEL}` habis hari ini, memakai `{model}`.")
    llm = crewai_llm(model=model)
    # Mode hemat: 1 iterasi per agent supaya tiap agent = 1 request LLM.
    iterasi = 1 if HEMAT else 3

    peneliti = Agent(
        role="Peneliti Teknologi",
        goal=f"Mengumpulkan 5 fakta kunci tentang {topik}",
        backstory="Analis riset yang teliti dan anti-halusinasi. Selalu spesifik.",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=iterasi,
    )
    penulis = Agent(
        role="Penulis Konten",
        goal="Mengubah riset jadi artikel blog yang enak dibaca",
        backstory="Content writer 10 tahun, gaya santai tapi kredibel.",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=iterasi,
    )
    editor = Agent(
        role="Editor",
        goal="Memastikan artikel akurat, ringkas, bebas typo",
        backstory="Editor senior yang galak soal kejelasan kalimat.",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=iterasi,
    )

    t1 = Task(
        description=f"Riset '{topik}'. Fokus: manfaat, kendala, contoh nyata.",
        expected_output="Daftar 5 poin fakta, tiap poin 1-2 kalimat, Bahasa Indonesia.",
        agent=peneliti,
    )
    t2 = Task(
        description="Tulis artikel blog 300 kata berdasarkan hasil riset.",
        expected_output="Artikel markdown: judul, 3 subjudul, penutup.",
        agent=penulis,
        context=[t1],
    )
    t3 = Task(
        description="Edit artikel: perjelas kalimat, buang basa-basi, cek konsistensi.",
        expected_output="Versi final artikel markdown siap publish.",
        agent=editor,
        context=[t2],
    )

    if HEMAT:
        # Hemat kuota: cukup 2 agent (Peneliti -> Penulis).
        # Konsep estafet konteks antar agent tetap terlihat.
        crew = Crew(
            agents=[peneliti, penulis],
            tasks=[t1, t2],
            process=Process.sequential,
            verbose=True,
        )
        return crew, [t1, t2]

    crew = Crew(
        agents=[peneliti, penulis, editor],
        tasks=[t1, t2, t3],
        process=Process.sequential,  # atau Process.hierarchical + manager_llm
        verbose=True,
    )
    return crew, [t1, t2, t3]


def jalankan(topik: str):
    """Generator event untuk UI. CrewAI blocking, jadi laporkan per task."""
    catatan = []
    crew, tasks = build(topik, lapor=catatan.append)
    for c in catatan:
        yield "step", c
    nama = ["Peneliti mengumpulkan fakta", "Penulis menyusun artikel", "Editor memoles"]

    n = len(tasks)
    hemat = " (mode hemat)" if HEMAT else ""
    yield "step", f"Crew dimulai ({n} agent, proses sequential){hemat}"
    hasil = crew.kickoff()

    for label, t in zip(nama, tasks):
        yield "step", label
        out = getattr(t, "output", None)
        yield "token", str(out.raw if out and hasattr(out, "raw") else out or "-")

    yield "step", "Output final"
    yield "token", str(hasil)
    yield "done", ""


def main():
    for tipe, teks in jalankan("AI Agent untuk UMKM di Indonesia"):
        if tipe == "step":
            print(f"\n\n=== {teks} ===")
        elif tipe == "token":
            print(teks)


if __name__ == "__main__":
    main()
