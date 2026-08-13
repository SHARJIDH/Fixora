#!/bin/bash
# Start the CloudAgentPR backend server with ngrok tunnel
# Usage: ./start.sh

cd "$(dirname "$0")"

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# macOS fork-safety: RQ forks per job; the child crashes inside CoreFoundation
# (via _scproxy proxy lookup) because ObjC isn't fork-safe. These two vars
# disable the ObjC post-fork assertion and skip the macOS proxy lookup.
if [[ "$OSTYPE" == "darwin"* ]]; then
    export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
    export NO_PROXY="*"
fi

# Start ngrok in background if available
if command -v ngrok &> /dev/null; then
    echo "Starting ngrok tunnel..."
    ngrok start python &> /dev/null &
    NGROK_PID=$!
    sleep 2
    echo "ngrok started (PID: $NGROK_PID)"
    echo "Check ngrok URL at: http://localhost:4040"
fi

# Start RQ worker in background
echo "Starting RQ worker..."
python3 worker.py &
WORKER_PID=$!
echo "Worker started (PID: $WORKER_PID)"

# Run the Flask server
python3 app.py

# Cleanup on exit
if [ ! -z "$NGROK_PID" ]; then
    kill $NGROK_PID 2>/dev/null
fi
if [ ! -z "$WORKER_PID" ]; then
    kill $WORKER_PID 2>/dev/null
fi
