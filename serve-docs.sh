#!/usr/bin/env bash

# Serve MkDocs documentation with live reload
# Usage: ./serve-docs.sh [HOST] [PORT]
# Example: ./serve-docs.sh 0.0.0.0 8201

set -e

# Defaults
HOST="${1:-0.0.0.0}"
PORT="${2:-8201}"

echo "🚀 Starting MkDocs development server..."
echo "📝 Documentation will be available at: http://$HOST:$PORT"
echo "🔄 Changes will auto-reload"
echo ""
echo "Press Ctrl+C to stop"
echo ""

uv run mkdocs serve -a "$HOST:$PORT"
