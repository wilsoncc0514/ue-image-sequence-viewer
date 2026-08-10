#!/bin/zsh
set -u

APP_DIR="${0:A:h}"
cd "$APP_DIR" || exit 1

pause_before_exit() {
    [[ -t 0 ]] && read -r "REPLY?Press Return to close…"
}

if [[ -x "$APP_DIR/.venv/bin/python3" ]]; then
    PYTHON_BIN="$APP_DIR/.venv/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
else
    echo "[ERROR] Python 3.10 or newer was not found."
    pause_before_exit
    exit 1
fi

if ! "$PYTHON_BIN" -c 'import sys, tkinter; from PIL import Image; assert sys.version_info >= (3, 10)' 2>/dev/null; then
    REQUIREMENTS="$APP_DIR/requirements.txt"
    [[ -f "$REQUIREMENTS" ]] || REQUIREMENTS="$APP_DIR/../requirements.txt"
    echo "[ERROR] Python 3.10+, Tkinter, or Pillow is unavailable."
    echo "Run: $PYTHON_BIN -m pip install -r $REQUIREMENTS"
    pause_before_exit
    exit 1
fi

exec "$PYTHON_BIN" "$APP_DIR/main.py" "$@"
