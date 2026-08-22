"""
Lihat riwayat run dari terminal (tanpa memakai kuota Gemini).

    python demo/05_lihat_riwayat.py              # daftar 20 terakhir
    python demo/05_lihat_riwayat.py langgraph    # filter framework
    python demo/05_lihat_riwayat.py --id a1b2c3  # tampilkan satu run penuh
"""

import sys

import riwayat

NAMA = {"langchain": "LangChain", "langgraph": "LangGraph", "crewai": "CrewAI"}


def tampilkan_satu(run_id: str) -> int:
    e = riwayat.ambil(run_id)
    if not e:
        print(f"Run '{run_id}' tidak ditemukan.")
        return 1

    print(f"\n{'=' * 66}")
    print(f"{NAMA.get(e['framework'], e['framework'])}  |  {e['topik']}")
    print(
        f"{e['waktu']}  |  model {e['model']}  |  {e['detik']}s"
        f"{'  |  mode hemat' if e.get('hemat') else ''}"
    )
    print("=" * 66)

    for p in e["peristiwa"]:
        if p["type"] == "step":
            print(f"\n--- {p['data']} ---")
        elif p["type"] == "error":
            print(f"\n[ERROR] {p['data']}")
        else:
            print(p["data"])
    print()
    return 0


def tampilkan_daftar(framework: str | None) -> int:
    item = riwayat.daftar(limit=20, framework=framework)
    if not item:
        print("Belum ada riwayat. Jalankan salah satu demo dulu.")
        return 0

    s = riwayat.statistik()
    print(f"\n{s['total']} run tersimpan ({s['gagal']} gagal)")
    print(f"{'ID':<12}{'FRAMEWORK':<12}{'STATUS':<11}{'WAKTU':<18}TOPIK")
    print("-" * 84)
    for e in item:
        status = "gagal" if e["status"] == "gagal" else f"{e['langkah']} langkah"
        waktu = e["waktu"].replace("T", " ")[5:16]  # MM-DD HH:MM
        print(
            f"{e['id']:<12}{NAMA.get(e['framework'], e['framework']):<12}"
            f"{status:<11}{waktu:<18}{e['topik'][:30]}"
        )
    print("\nLihat detail:  python demo/05_lihat_riwayat.py --id <ID>\n")
    return 0


def main() -> int:
    arg = sys.argv[1:]
    if arg and arg[0] == "--id":
        if len(arg) < 2:
            print("Pemakaian: python demo/05_lihat_riwayat.py --id <ID>")
            return 1
        return tampilkan_satu(arg[1])
    return tampilkan_daftar(arg[0] if arg else None)


if __name__ == "__main__":
    raise SystemExit(main())
