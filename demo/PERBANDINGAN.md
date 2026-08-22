# LangChain vs LangGraph vs CrewAI

Demo lengkap + perbandingan praktis. Semua kode ada di folder ini.

## Isi

| File | Isi |
|---|---|
| `01_langchain_demo.py` | Chain LCEL: dasar, bersusun, paralel, streaming |
| `02_langgraph_demo.py` | Graph berstate dengan loop revisi + checkpoint memory |
| `03_crewai_demo.py` | Crew 3 agent (Peneliti, Penulis, Editor) proses sequential |
| `04_simulasi_offline.py` | Jalan tanpa API key, memperlihatkan beda arsitektur |

## Cara cepat

```bash
python3 demo/04_simulasi_offline.py          # tanpa install apa pun

pip install -r demo/requirements.txt
export OPENAI_API_KEY=sk-...
python3 demo/01_langchain_demo.py
```

## Analogi 1 kalimat

- **LangChain** = pipa air lurus. Air masuk satu ujung, keluar ujung lain.
- **LangGraph** = papan sirkuit. Ada percabangan, saklar, dan kabel balik (loop).
- **CrewAI** = tim kantor. Kamu tulis job description, mereka kerja estafet.

## Tabel perbandingan

| Aspek | LangChain | LangGraph | CrewAI |
|---|---|---|---|
| Abstraksi inti | Chain / Runnable | Node + Edge + State | Agent + Task + Crew |
| Alur | Linear (DAG) | Graph, boleh siklik | Sequential / hierarchical |
| Loop & retry | Manual, canggung | Native (conditional edge) | Terbatas, implisit |
| State bersama | Tidak ada (lewat dict) | Kelas eksplisit + reducer | Konteks antar task |
| Memory | Per-chain, sederhana | Checkpointer, resume, time-travel | Short/long term memory built-in |
| Human-in-the-loop | Ditulis sendiri | `interrupt()` native | Terbatas |
| Kontrol alur | Sedang | Sangat tinggi | Rendah (LLM yang atur) |
| Kurva belajar | Rendah | Tinggi | Rendah |
| Determinisme | Tinggi | Tinggi | Rendah |
| Debug | Mudah | Sedang (ada visual graph) | Sulit (verbose log) |
| Biaya token | Paling hemat | Sedang | Paling boros (banyak agent) |
| Produksi | Cocok untuk task sederhana | Paling siap produksi | Cocok prototipe / demo |
| Relasi | Fondasi | Dibangun di atas LangChain | Berdiri sendiri (pakai LiteLLM) |

## Kapan pakai yang mana

**LangChain** jika alurnya sudah pasti: RAG tanya-jawab, ringkasan dokumen, klasifikasi tiket, ekstraksi data terstruktur. Kalau bisa digambar sebagai garis lurus, cukup LangChain.

**LangGraph** jika butuh keputusan dan pengulangan: coding agent yang retry saat test gagal, customer service yang eskalasi ke manusia, riset multi-langkah yang menilai hasil sendiri, workflow yang harus bisa di-pause lalu dilanjut besok.

**CrewAI** jika masalahnya cocok dipetakan ke peran manusia dan kecepatan prototipe lebih penting daripada kontrol: content pipeline, analisis pasar, laporan otomatis, demo ke stakeholder.

## Beda gaya kode

```python
# LangChain - komposisi
chain = prompt | llm | parser

# LangGraph - graf eksplisit
graph.add_node("tulis", node_tulis)
graph.add_conditional_edges("nilai", rute, {"revisi": "tulis", "selesai": END})

# CrewAI - deklarasi peran
Agent(role="Editor", goal="pastikan akurat", backstory="editor senior")
```

## Kombinasi umum

Ketiganya tidak saling meniadakan. Pola produksi yang sering dipakai:

```
LangChain  -> komponen (prompt, retriever, tool, parser)
LangGraph  -> orkestrasi (siapa jalan kapan, kapan berhenti)
CrewAI     -> lapisan simulasi tim jika memang perlu multi-persona
```

Rekomendasi: mulai dari LangChain, naik ke LangGraph saat butuh loop/kondisi, pakai CrewAI hanya kalau peran-peran itu memang menambah kualitas hasil.

## Jebakan yang sering kena

- LangChain: memaksakan alur bercabang pakai `RunnableBranch` sampai kodenya tidak terbaca. Itu tanda pindah ke LangGraph.
- LangGraph: over-engineering. 5 node untuk tugas yang sebenarnya satu prompt.
- CrewAI: token membengkak dan hasil tidak konsisten karena setiap agent memanggil LLM berkali-kali. Selalu batasi `max_iter`.
