#!/bin/bash
# Start script for Local Agentic AI

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Starting Local Agentic AI..."
echo ""

# Check if Ollama is running
if ! curl -s http://localhost:11434/ > /dev/null 2>&1; then
    echo "WARNING: Ollama is not running. Please start Ollama first."
    echo "Run: ollama serve"
    exit 1
fi

echo "Ollama is running."

# Start backend
echo "Starting backend on http://0.0.0.0:8000 ..."
cd "$SCRIPT_DIR/backend"
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

sleep 3

# Check if backend started
if ! curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "ERROR: Backend failed to start."
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo "Backend is running."

# Start frontend
echo "Starting frontend on http://0.0.0.0:5173 ..."
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "=========================================="
echo "Local Agentic AI is now running!"
echo ""
echo "Frontend: http://localhost:5173"
echo "Backend:  http://localhost:8000"
echo ""
echo "For VPN access (Tailscale):"
echo "Frontend: http://100.75.236.123:5173"
echo "Backend:  http://100.75.236.123:8000"
echo ""
echo "Press Ctrl+C to stop all services."
echo "=========================================="

# Wait for user interrupt
trap "echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

wait
