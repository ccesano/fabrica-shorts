#!/usr/bin/env bash
# Prepara todo lo necesario para fabricar videos (en una sesión nueva de Claude, en GitHub Actions o en tu PC con Linux/WSL).
# uso: bash setup.sh            (todo)
#      bash setup.sh sin-voz    (sin Chatterbox: sólo Kokoro, más liviano)
# Idempotente: lo que ya está instalado se saltea.
set -euo pipefail
cd "$(dirname "$0")"
RAIZ=$PWD
LEMO_COMMIT=3961ddb3d24d8876e0e2754f7790d66908acee51
paso() { printf '\n\033[1m▶ %s\033[0m\n' "$*"; }

need() { command -v "$1" >/dev/null 2>&1; }
need ffmpeg || { paso "ffmpeg"; (sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg) || apt-get install -y -qq ffmpeg; }
need node || { echo "✗ Falta Node.js 20+"; exit 1; }
need uv || { paso "uv"; curl -LsSf https://astral.sh/uv/install.sh | sh; export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"; }

paso "Entorno principal (.venv)"
[ -x .venv/bin/python ] || uv venv -q -p 3.12 .venv
VIRTUAL_ENV=.venv uv pip install -q numpy scipy soundfile soxr kokoro-onnx sherpa-onnx num2words

if [ "${1:-}" != "sin-voz" ]; then
  paso "Entorno de voz clonada (.venv-voz, Chatterbox)"
  [ -x .venv-voz/bin/python ] || uv venv -q -p 3.11 .venv-voz
  if ! .venv-voz/bin/python -c "import chatterbox" 2>/dev/null; then
    # torch CPU es mucho más liviano; si download.pytorch.org no está permitido, cae a PyPI
    VIRTUAL_ENV=.venv-voz uv pip install -q --index-strategy unsafe-best-match --extra-index-url https://download.pytorch.org/whl/cpu \
      "torch==2.6.0" "torchaudio==2.6.0" chatterbox-tts==0.1.7 "setuptools<81" 2>/dev/null \
    || VIRTUAL_ENV=.venv-voz uv pip install -q chatterbox-tts==0.1.7 "setuptools<81"
  fi
fi

paso "Música: lemo-opuscar + instrumentos (~1,3 GB)"
if [ ! -d vendor/lemo-opuscar/.git ]; then
  mkdir -p vendor
  git clone -q https://github.com/lemomo-ai/lemo-opuscar vendor/lemo-opuscar
  git -C vendor/lemo-opuscar -c advice.detachedHead=false checkout -q $LEMO_COMMIT
fi
for lib in vsco2ce salamander freepats vcsl; do
  [ -d vendor/lemo-opuscar/core/audio/instruments/$lib ] || (cd vendor/lemo-opuscar && PY=$RAIZ/.venv/bin/python sh tools/fetch.sh instruments $lib)
done

paso "Modelos (Kokoro de respaldo + Whisper para el control de voz)"
mkdir -p modelos
B=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
[ -s modelos/kokoro-v1.0.onnx ] || curl -sSL -o modelos/kokoro-v1.0.onnx $B/kokoro-v1.0.onnx
[ -s modelos/voices-v1.0.bin ] || curl -sSL -o modelos/voices-v1.0.bin $B/voices-v1.0.bin
if [ ! -d modelos/sherpa-onnx-whisper-base ]; then
  curl -sSL https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-base.tar.bz2 | tar xj -C modelos
fi

paso "HyperFrames"
npx --yes hyperframes@0.8.190 --version >/dev/null && echo "hyperframes ok"

if [ ! -s voces/muestra.wav ]; then
  if [ -s voces/muestra.wav.gpg ] && [ -n "${VOZ_CLAVE:-}" ]; then
    gpg --batch --yes --quiet --passphrase "$VOZ_CLAVE" -o voces/muestra.wav -d voces/muestra.wav.gpg && echo "muestra de voz descifrada"
  else
    echo "⚠ Falta voces/muestra.wav (ver voces/LEEME.md). Sin ella se usa Kokoro."
  fi
fi
paso "Listo. Probá: .venv/bin/python fabrica/make_short.py videos/maradona-despedida/guion.json"
