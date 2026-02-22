# Raspberry Pi 5 setup script for TARS
# Usage:
#   chmod +x scripts/setup_raspberry_pi.sh
#   ./scripts/setup_raspberry_pi.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${ROOT_DIR}/python/.venv"
REQ_FILE="${ROOT_DIR}/python/requirements.txt"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Install it with: sudo apt-get install -y python3"
  exit 1
fi

echo "Updating apt repositories..."
sudo apt-get update

echo "Installing system dependencies..."
sudo apt-get install -y \
  python3-venv \
  python3-pip \
  python3-dev \
  build-essential \
  portaudio19-dev \
  libasound2-dev \
  libportaudio2 \
  ffmpeg \
  espeak-ng \
  gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good

if [ ! -d "${VENV_DIR}" ]; then
  echo "Creating virtual environment at ${VENV_DIR}"
  python3 -m venv "${VENV_DIR}"
fi

# shellcheck disable=SC1090
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip

if [ ! -f "${REQ_FILE}" ]; then
  echo "Missing requirements file: ${REQ_FILE}"
  exit 1
fi

echo "Installing Python dependencies..."
python -m pip install -r "${REQ_FILE}"

echo "Done. To activate the venv later: source ${VENV_DIR}/bin/activate"
