#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/bootstrap dist
bootstrap="${REVOICE_BOOTSTRAP_DMG:-$PWD/build/bootstrap/Revoice.dmg}"
if [ ! -f "$bootstrap" ]; then
  echo "Set REVOICE_BOOTSTRAP_DMG to a separately obtained Revoice 0.2.4 bootstrap DMG." >&2
  exit 1
fi
BOOTSTRAP="$bootstrap" python3 - <<'PYVERIFY'
import hashlib, os, pathlib
path = pathlib.Path(os.environ['BOOTSTRAP'])
expected = '6a6a529109c8865f0cddc6b17b1bf2d0b72bb33e219feb01c12d2991c8d982a2'
if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
    raise SystemExit('Bootstrap checksum mismatch; refusing to build.')
PYVERIFY
mount="$PWD/build/bootstrap-mount"
mkdir -p "$mount"
hdiutil attach -readonly -nobrowse -mountpoint "$mount" "$bootstrap"
trap 'hdiutil detach "$mount" >/dev/null || true' EXIT
resources="$mount/Revoice.app/Contents/Resources"
"$resources/runtime/bin/python3.12" -m venv --clear build/tools
build/tools/bin/python -m pip install -r packaging-requirements.txt -r requirements-test.txt
build/tools/bin/python scripts/check.py
cp "$resources/Revoice.icns" build/Revoice.icns
build/tools/bin/python driver-build.py
build/tools/bin/python build-beatrice-app.py --personal-use --runtime-resources "$resources" --engine-plugin "$resources/engine/beatrice_2.0.0-rc.3.vst3"
codesign --verify --deep --strict build/Revoice-Beatrice.app
build/tools/bin/python build-beatrice-dmg.py
hdiutil verify dist/Revoice.dmg
(cd dist && shasum -a 256 Revoice.dmg > SHA256SUMS)
