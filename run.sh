#!/usr/bin/env bash
# Setup + jalankan demo. Menangani masalah versi Python secara otomatis.
set -e
cd "$(dirname "$0")"

VENV=.venv
PORT="${PORT:-8765}"

# --- 1. Cari Python yang kompatibel (crewai belum dukung 3.14) ---
if [ ! -x "$VENV/bin/python" ]; then
  PY=""
  for c in python3.13 python3.12 python3.11 python3.10; do
    command -v "$c" >/dev/null 2>&1 && { PY="$c"; break; }
  done
  if [ -z "$PY" ]; then
    v=$(python3 -c 'import sys;print("%d%d"%sys.version_info[:2])' 2>/dev/null || echo 0)
    if [ "$v" -ge 310 ] && [ "$v" -le 313 ]; then
      PY=python3
    else
      echo "ERROR: butuh Python 3.10-3.13, yang ada versi $(python3 -V 2>&1)."
      echo "Install salah satu:  sudo pacman -S python311   /   sudo apt install python3.12-venv"
      exit 1
    fi
  fi
  echo ">> Membuat virtualenv dengan $PY ..."
  "$PY" -m venv "$VENV"
  "$VENV/bin/pip" install -q --upgrade pip
fi

# --- 2. Install dependensi kalau belum ---
if ! "$VENV/bin/python" -c "import crewai, langgraph, fastapi, langchain_google_genai" 2>/dev/null; then
  echo ">> Menginstall dependensi (sekali saja, sekitar 1-2 menit) ..."
  "$VENV/bin/pip" install -q -r demo/requirements.txt
fi

# --- 3. Siapkan .env ---
[ -f .env ] || { cp .env.example .env; echo ">> .env dibuat. Isi GOOGLE_API_KEY-mu di sana."; }

if grep -q "isi_api_key" .env 2>/dev/null; then
  echo ""
  echo "  PERHATIAN: GOOGLE_API_KEY di .env masih placeholder."
  echo "  Ambil key gratis di https://aistudio.google.com/apikey lalu edit .env"
  echo "  UI tetap terbuka dan akan menampilkan statusnya."
  echo ""
fi

# --- 4. Jalankan ---
echo ">> Server jalan di http://127.0.0.1:$PORT"
PORT="$PORT" exec "$VENV/bin/python" demo/app.py
