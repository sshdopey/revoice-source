#!/usr/bin/env python3
import pathlib
import py_compile
import subprocess
import sys

root = pathlib.Path(__file__).resolve().parent.parent
for path in list((root / "backend").glob("*.py")) + list(root.glob("*.py")):
    py_compile.compile(str(path), doraise=True)
for test in ("test_engine_paths.py", "test_release_reliability.py", "test_streaming_resample.py"):
    subprocess.run([sys.executable, str(root / "backend" / test)], cwd=root, check=True)
print("Python syntax, engine resolution, audio reliability and resampler checks passed.")
