"""
DEMO 3 - CrewAI
===============
Fokus: TIM AGENT berperan (role-based). Agent punya role/goal/backstory,
Task punya deskripsi + expected_output, Crew mengatur proses sequential/hierarchical.
Cocok untuk: simulasi tim (peneliti + penulis + editor), workflow bisnis.

Jalankan:
    pip install crewai crewai-tools
    export OPENAI_API_KEY=sk-...
    python 03_crewai_demo.py
"""

from crewai import Agent, Task, Crew, Process

TOPIK = "AI Agent untuk UMKM di Indonesia"

# --- AGENT: didefinisikan lewat persona, bukan kode alur ---
peneliti = Agent(
    role="Peneliti Teknologi",
    goal=f"Mengumpulkan 5 fakta kunci tentang {TOPIK}",
    backstory="Analis riset yang teliti dan anti-halusinasi. Selalu spesifik.",
    verbose=True,
    allow_delegation=False,
)

penulis = Agent(
    role="Penulis Konten",
    goal="Mengubah riset menjadi artikel blog yang enak dibaca",
    backstory="Content writer 10 tahun, gaya santai tapi kredibel.",
    verbose=True,
    allow_delegation=False,
)

editor = Agent(
    role="Editor",
    goal="Memastikan artikel akurat, ringkas, dan bebas typo",
    backstory="Editor senior yang galak soal kejelasan kalimat.",
    verbose=True,
    allow_delegation=False,
)

# --- TASK: output task sebelumnya otomatis jadi konteks task berikutnya ---
t_riset = Task(
    description=f"Riset {TOPIK}. Fokus: manfaat, kendala, contoh nyata.",
    expected_output="Daftar 5 poin fakta, tiap poin 1-2 kalimat.",
    agent=peneliti,
)

t_tulis = Task(
    description="Tulis artikel blog 300 kata berdasarkan hasil riset.",
    expected_output="Artikel markdown dengan judul, 3 subjudul, dan penutup.",
    agent=penulis,
    context=[t_riset],
)

t_edit = Task(
    description="Edit artikel: perjelas kalimat, buang basa-basi, cek konsistensi.",
    expected_output="Versi final artikel markdown siap publish.",
    agent=editor,
    context=[t_tulis],
    output_file="artikel_final.md",
)

crew = Crew(
    agents=[peneliti, penulis, editor],
    tasks=[t_riset, t_tulis, t_edit],
    process=Process.sequential,  # ganti Process.hierarchical untuk pakai manager agent
    verbose=True,
)


def main():
    hasil = crew.kickoff()
    print("\n=== OUTPUT FINAL ===")
    print(hasil)
    print("\nToken usage:", crew.usage_metrics)


if __name__ == "__main__":
    main()
