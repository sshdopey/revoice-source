import hashlib
import json
import pathlib
import plistlib
import shutil
import subprocess
from ds_store import DSStore
from mac_alias import Alias

root = pathlib.Path(__file__).resolve().parent
version = (root / 'VERSION').read_text().strip()
stage = root / 'build/beatrice-dmg'
if stage.exists():
    shutil.rmtree(stage)
stage.mkdir(parents=True)
app = root / 'build/Revoice-Beatrice.app'
subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
subprocess.run(['ditto', str(app), str(stage / 'Revoice.app')], check=True)
(stage / 'Applications').symlink_to('/Applications')
(stage / '.background').mkdir()
subprocess.run(['swift', str(root / 'dmg-background.swift'), str(stage / '.background/background.png')], check=True)
outputs = root / 'dist'
outputs.mkdir(parents=True, exist_ok=True)
dmg = outputs / 'Revoice.dmg'
rw = root / 'build/Revoice-0.2.4-layout.dmg'
subprocess.run(['hdiutil', 'create', '-ov', '-volname', 'Revoice ' + version, '-srcfolder', str(stage), '-fs', 'HFS+', '-format', 'UDRW', str(rw)], check=True)
mount_dir = root / 'build/dmg-mount'
mount_dir.mkdir(exist_ok=True)
data = plistlib.loads(subprocess.check_output(['hdiutil', 'attach', '-nobrowse', '-mountpoint', str(mount_dir), '-plist', str(rw)]))
entity = next(x for x in data['system-entities'] if 'mount-point' in x)
mount = pathlib.Path(entity['mount-point'])
try:
    alias = Alias.for_file(str(mount / '.background/background.png')).to_bytes()
    with DSStore.open(str(mount / '.DS_Store'), 'w+') as ds:
        ds['.']['bwsp'] = {'ShowStatusBar': False, 'ShowToolbar': False, 'ShowPathbar': False, 'ShowSidebar': False, 'WindowBounds': '{{220, 180}, {760, 592}}', 'ContainerShowSidebar': False, 'SidebarWidth': 0}
        ds['.']['icvp'] = {'viewOptionsVersion': 1, 'backgroundType': 2, 'backgroundImageAlias': alias, 'iconSize': 128., 'gridSpacing': 100., 'gridOffsetX': 0., 'gridOffsetY': 0., 'arrangeBy': 'none', 'showIconPreview': True, 'showItemInfo': False, 'labelOnBottom': True, 'textSize': 14., 'scrollPositionX': 0., 'scrollPositionY': 0., 'backgroundColorRed': 0.075, 'backgroundColorGreen': 0.09, 'backgroundColorBlue': 0.11}
        ds['.']['vSrn'] = ('long', 1)
        ds['.']['icvl'] = ('type', 'icnv')
        ds['Revoice.app']['Iloc'] = (190, 300)
        ds['Applications']['Iloc'] = (570, 300)
finally:
    subprocess.run(['hdiutil', 'detach', entity['dev-entry']], check=True)
subprocess.run(['hdiutil', 'convert', str(rw), '-format', 'UDZO', '-imagekey', 'zlib-level=9', '-o', str(dmg), '-ov'], check=True)
metadata = {'dmg': str(dmg), 'bytes': dmg.stat().st_size, 'sha256': hashlib.sha256(dmg.read_bytes()).hexdigest(), 'contains_friend_voice': False, 'beatrice_library_bundled': True, 'microphone_setup': 'bundled; first launch offers administrator-approved installation inside Revoice', 'setup_window': 'Finder drag-and-drop only; no custom installer app', 'signed': 'ad-hoc', 'notarized': False}
(outputs / 'release.json').write_text(json.dumps(metadata, indent=2))
print(json.dumps(metadata, indent=2))
