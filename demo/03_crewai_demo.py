"""
DEMO 3 - CrewAI (Gemini)
========================
Tim 3 agent berperan, proses sequential, konteks diestafetkan.

    python demo/03_crewai_demo.py
"""

from crewai import Agent, Crew, Process, Task

from config import crewai_llm, llm_dengan_fallback


def build(topik: str, lapor=None):
    # pilih model yang kuotanya masih ada, lalu pakai untuk CrewAI
    _, model = llm_dengan_fallback(lapor=lapor)
    llm = crewai_llm(model=model)

    peneliti = Agent(
        role="Peneliti Teknologi",
        goal=f"Mengumpulkan 5 fakta kunci tentang {topik}",
        backstory="Analis riset yang teliti dan anti-halusinasi. Selalu spesifik.",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )
    penulis = Agent(
        role="Penulis Konten",
        goal="Mengubah riset jadi artikel blog yang enak dibaca",
        backstory="Content writer 10 tahun, gaya santai tapi kredibel.",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )
    editor = Agent(
        role="Editor",
        goal="Memastikan artikel akurat, ringkas, bebas typo",
        backstory="Editor senior yang galak soal kejelasan kalimat.",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=3,
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

    yield "step", "Crew dimulai (3 agent, proses sequential)"
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
