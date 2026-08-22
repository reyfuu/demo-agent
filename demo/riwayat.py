"""Riwayat run: simpan hasil tiap demo supaya bisa dibaca ulang tanpa kuota.

Disimpan sebagai JSON Lines di `riwayat.jsonl` (satu baris satu run),
formatnya tahan banting kalau file terpotong di tengah penulisan.
"""

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BERKAS = ROOT / "riwayat.jsonl"

MAKS = 200  # simpan sekian run terakhir
_kunci = threading.Lock()


def _baca_semua() -> list[dict]:
    if not BERKAS.exists():
        return []
    keluar = []
    for baris in BERKAS.read_text(encoding="utf-8").splitlines():
        baris = baris.strip()
        if not baris:
            continue
        try:
            keluar.append(json.loads(baris))
        except json.JSONDecodeError:
            continue  # lewati baris rusak
    return keluar


def simpan(
    framework: str,
    topik: str,
    model: str,
    hemat: bool,
    peristiwa: list[dict],
    status: str,
    detik: float,
) -> dict:
    """Catat satu run. Kembalikan ringkasannya."""
    entri = {
        "id": uuid.uuid4().hex[:10],
        "waktu": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "framework": framework,
        "topik": topik,
        "model": model,
        "hemat": hemat,
        "status": status,  # "selesai" | "gagal"
        "detik": round(detik, 1),
        "langkah": sum(1 for p in peristiwa if p["type"] == "step"),
        "peristiwa": peristiwa,
    }
    with _kunci:
        semua = _baca_semua()
        semua.append(entri)
        semua = semua[-MAKS:]
        tmp = BERKAS.with_suffix(".tmp")
        tmp.write_text(
            "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in semua),
            encoding="utf-8",
        )
        tmp.replace(BERKAS)  # atomic, aman kalau proses mati di tengah jalan
    return entri


def daftar(limit: int = 50, framework: str | None = None) -> list[dict]:
    """Ringkasan run terbaru lebih dulu, tanpa isi peristiwa."""
    semua = _baca_semua()
    if framework:
        semua = [e for e in semua if e.get("framework") == framework]
    ringkas = []
    for e in reversed(semua[-limit:]):
        r = {k: v for k, v in e.items() if k != "peristiwa"}
        cuplik = next(
            (p["data"] for p in e.get("peristiwa", []) if p["type"] == "token"), ""
        )
        r["cuplikan"] = cuplik[:160]
        ringkas.append(r)
    return ringkas


def ambil(run_id: str) -> dict | None:
    for e in _baca_semua():
        if e.get("id") == run_id:
            return e
    return None


def hapus_semua() -> int:
    with _kunci:
        n = len(_baca_semua())
        BERKAS.unlink(missing_ok=True)
    return n


def statistik() -> dict:
    semua = _baca_semua()
    per_fw: dict[str, int] = {}
    for e in semua:
        per_fw[e.get("framework", "?")] = per_fw.get(e.get("framework", "?"), 0) + 1
    return {
        "total": len(semua),
        "per_framework": per_fw,
        "gagal": sum(1 for e in semua if e.get("status") == "gagal"),
    }
