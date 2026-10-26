import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from engine_paths import resolve_library, PLUGIN, BINARY


class EnginePathsTest(unittest.TestCase):
    def test_relocated_bundle_without_installed_plugin(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            resources = root / 'Different Folder/Revoice.app/Contents/Resources'
            bundled = resources / 'engine' / PLUGIN / 'Contents/MacOS' / BINARY
            external = root / 'external-library'
            external.write_bytes(b'fixture')
            bundled.parent.mkdir(parents=True)
            bundled.write_bytes(b'fixture')
            with patch.dict(os.environ, {'REVOICE_BEATRICE_LIBRARY': str(external)}):
                self.assertEqual(resolve_library(resources), bundled)

    def test_explicit_library_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            external = root / 'external-library'
            external.write_bytes(b'fixture')
            with patch.dict(os.environ, {'REVOICE_BEATRICE_LIBRARY': str(external)}):
                self.assertEqual(resolve_library(root / 'Resources'), external)


if __name__ == '__main__':
    unittest.main()
