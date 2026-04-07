#!/bin/bash
# Auto-Tensor 'War Room' Launcher (TS3 Stability Edition)

echo "[1/3] Clearing zombie processes on 8000 and 5173..."
fuser -k 8000/tcp 2>/dev/null
fuser -k 5173/tcp 2>/dev/null

echo "[2/3] Initializing FastAPI Bridge..."
source .venv/bin/activate
python3 core/api.py > logs/api.log 2>&1 &
echo "API live at http://localhost:8000"

echo "[3/3] Launching Vite Dashboard..."
cd ui
npm run dev
