import os
from pathlib import Path


PLUGIN = 'beatrice_2.0.0-rc.3.vst3'
BINARY = 'beatrice_2.0.0-rc.3'


def resolve_library(resources=None):
    resources = Path(resources) if resources else Path(__file__).resolve().parent.parent
    candidates = [
        resources / 'engine' / PLUGIN / 'Contents/MacOS' / BINARY,
        os.environ.get('REVOICE_BEATRICE_LIBRARY', ''),
        Path.home() / 'Library/Audio/Plug-Ins/VST3' / PLUGIN / 'Contents/MacOS' / BINARY,
        Path('/Library/Audio/Plug-Ins/VST3') / PLUGIN / 'Contents/MacOS' / BINARY,
    ]
    return next((Path(p) for p in candidates if p and Path(p).is_file()), None)
