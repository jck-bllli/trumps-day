#!/bin/bash
# One-time setup on a fresh Linux machine: Python packages, the Kokoro voice model (~350 MB, from GitHub)
# and the color emoji font. Needs ffmpeg with the rubberband filter.
set -e
cd "$(dirname "$0")"
pip install --break-system-packages -q kokoro-onnx soundfile scipy pillow numpy 2>/dev/null \
  || pip install -q kokoro-onnx soundfile scipy pillow numpy
mkdir -p tts_model
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  [ -s "tts_model/$f" ] || curl -sSL --max-time 600 -o "tts_model/$f" \
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/$f"
done
emoji_ok() { python -c "from PIL import ImageFont; ImageFont.truetype('fonts/NotoColorEmoji.ttf', 109)" 2>/dev/null; }
if [ ! -s /usr/share/fonts/truetype/noto/NotoColorEmoji.ttf ] && ! emoji_ok; then
  # a cut-off or error-page download leaves a file Pillow can't open, so re-fetch until it loads
  rm -f fonts/NotoColorEmoji.ttf
  curl -fsSL --retry 3 --max-time 300 -o fonts/NotoColorEmoji.ttf \
    "https://github.com/googlefonts/noto-emoji/raw/main/fonts/NotoColorEmoji.ttf"
  emoji_ok || { echo "emoji font download is not a valid font ($(wc -c < fonts/NotoColorEmoji.ttf) bytes)"; exit 1; }
fi
command -v ffmpeg >/dev/null || { echo "ffmpeg is required (with the rubberband filter)"; exit 1; }
ffmpeg -hide_banner -filters 2>/dev/null | grep -q rubberband || { echo "ffmpeg lacks the rubberband filter"; exit 1; }
echo "render setup ok"
