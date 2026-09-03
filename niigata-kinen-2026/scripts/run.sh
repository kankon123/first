#!/usr/bin/env bash
# Convenience wrappers for Niigata Kinen 2026
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export PATH="$HOME/.local/bin:$PATH"

cmd="${1:-}"
case "$cmd" in
  prepare)
    python3 video-pipeline/prepare_from_script.py \
      --project niigata-kinen-2026 \
      --ass-name niigata
    ;;
  build)
    bash video-pipeline/build_video.sh niigata-kinen-2026 niigata niigata_kinen_2026
    ;;
  status)
    echo "== narration =="
    wc -m niigata-kinen-2026/script/narration.txt || true
    echo "== assets =="
    ls niigata-kinen-2026/assets/scene_*.png 2>/dev/null | wc -l
    echo "== audio =="
    ls -lh niigata-kinen-2026/audio/narration.mp3 2>/dev/null || echo "(none)"
    echo "== out =="
    ls -lh niigata-kinen-2026/out/*.mp4 2>/dev/null || echo "(none)"
    ;;
  *)
    echo "Usage: $0 {prepare|build|status}"
    exit 1
    ;;
esac
