import pathlib,subprocess,shutil,plistlib,sys,argparse
root=pathlib.Path(__file__).resolve().parent
version=(root/'VERSION').read_text().strip()
build_number=(root/'BUILD_NUMBER').read_text().strip()
parser=argparse.ArgumentParser()
parser.add_argument('--engine-plugin',type=pathlib.Path)
parser.add_argument('--engine-permission',type=pathlib.Path)
parser.add_argument('--personal-use',action='store_true')
parser.add_argument('--runtime-resources',type=pathlib.Path,help='Contents/Resources from a working Revoice app or mounted DMG payload')
args=parser.parse_args()
if args.engine_plugin:
 if not args.personal_use and (not args.engine_permission or not args.engine_permission.is_file()):
  parser.error('Select --personal-use for this personal build, or supply --engine-permission for an authorized distribution build.')
 if args.engine_plugin.name!='beatrice_2.0.0-rc.3.vst3' or not (args.engine_plugin/'Contents/MacOS/beatrice_2.0.0-rc.3').is_file():
  parser.error('Choose the complete official Beatrice 2.0.0-rc.3 macOS VST3 bundle.')
 if args.engine_permission and not args.engine_permission.read_text().strip():parser.error('The permission document is empty.')
app=root/'build/Revoice-Beatrice.app';res=app/'Contents/Resources';mac=app/'Contents/MacOS';mac.mkdir(parents=True,exist_ok=True);res.mkdir(exist_ok=True)
old=args.runtime_resources or root/'build/Revoice.app/Contents/Resources'
if not (old/'runtime/lib/python3.12/site-packages').is_dir():raise RuntimeError('Supply --runtime-resources pointing to Contents/Resources in the supplied Revoice app.')
def sync(src,dst,exclude=()):
 dst.mkdir(parents=True,exist_ok=True)
 args=['rsync','-aL','--delete']
 for x in exclude:args+=['--exclude',x]
 subprocess.run(args+[str(src)+'/',str(dst)+'/'],check=True)
sync(old/'runtime',res/'runtime',('site-packages','__pycache__','*.pyc','include','share','tcl*','tk*'))
site=res/'runtime/lib/python3.12/site-packages';site.mkdir(exist_ok=True)
patterns=['typing_extensions.py','typing_extensions-*.dist-info','numpy','numpy-*.dist-info','sounddevice.py','sounddevice-*.dist-info','soundfile.py','soundfile-*.dist-info','_sounddevice*','_soundfile*','_cffi_backend*.so','cffi','cffi-*.dist-info','pycparser','pycparser-*.dist-info']
for pat in patterns:
 for src in (old/'runtime/lib/python3.12/site-packages').glob(pat):
  dst=site/src.name
  if src.is_dir():sync(src,dst,('__pycache__','tests','test'))
  else:shutil.copy2(src,dst)
sync(root/'frontend',res/'frontend');(res/'backend').mkdir(exist_ok=True)
for name in ('app.py','beatrice_core.py','engine_paths.py','noise_reduction.py','streaming_resample.py'):shutil.copy2(root/'backend'/name,res/'backend'/name)
for name in ('Revoice.icns','Revoice Microphone.pkg'):
 artifact=root/'build'/name
 if not artifact.is_file():shutil.copy2(old/name,artifact)
 shutil.copy2(artifact,res/name)
licenses=res/'Licenses';licenses.mkdir(exist_ok=True)
for name in ('LICENSE','THIRD-PARTY-NOTICES.md'):shutil.copy2(root/name,licenses/name)
if (res/'engine').exists():shutil.rmtree(res/'engine')
if args.engine_plugin:
 sync(args.engine_plugin,res/'engine'/args.engine_plugin.name)
 for name in ('LICENSE.txt','LICENSES_BUNDLED.txt'):
  notice=args.engine_plugin.parent/name
  if not notice.is_file():notice=args.engine_plugin.parent.parent/'Licenses'/('Beatrice-'+name)
  if not notice.is_file():raise RuntimeError('Missing official Beatrice notice: '+name)
  shutil.copy2(notice,licenses/('Beatrice-'+name))
 if args.engine_permission:shutil.copy2(args.engine_permission,licenses/'Beatrice-redistribution-permission.txt')
 else:
  (licenses/'Beatrice-personal-use.txt').write_text('Personal build requested for the user and their friend. This is not a grant of public or commercial redistribution rights. Preserve the official notices.\n')
  (licenses/'Beatrice-redistribution-permission.txt').unlink(missing_ok=True)
elif (licenses/'Beatrice-redistribution-permission.txt').exists():
 (licenses/'Beatrice-redistribution-permission.txt').unlink()
(res/'audio').mkdir(exist_ok=True)
noise_library=root/'build/librnnoise.dylib'
if not noise_library.is_file():
 source=root/'vendor/rnnoise'
 subprocess.run(['clang','-dynamiclib','-O3','-arch','arm64','-mmacosx-version-min=13.0','-I'+str(source/'include'),'-I'+str(source/'src')]+[str(source/'src'/name) for name in ('denoise.c','rnn.c','rnn_data.c','pitch.c','kiss_fft.c','celt_lpc.c')]+['-o',str(noise_library),'-install_name','@rpath/librnnoise.dylib'],check=True)
shutil.copy2(noise_library,res/'audio/librnnoise.dylib')
shutil.copy2(root/'vendor/rnnoise/COPYING',licenses/'RNNoise-COPYING.txt')
sync(root/'vendor/BlackHole',res/'Driver Source/BlackHole',('.git',));shutil.copy2(root/'driver-build.py',res/'Driver Source/driver-build.py')
info={'CFBundleIconFile':'Revoice.icns','CFBundleName':'Revoice','CFBundleDisplayName':'Revoice','CFBundleIdentifier':'app.revoice.desktop','CFBundleExecutable':'Revoice','CFBundlePackageType':'APPL','CFBundleShortVersionString':version,'CFBundleVersion':build_number,'LSMinimumSystemVersion':'13.0','NSMicrophoneUsageDescription':'Revoice converts your microphone into the voice you select. Audio stays on your Mac.','NSHighResolutionCapable':True,'NSAppTransportSecurity':{'NSAllowsLocalNetworking':True},'NSPrincipalClass':'NSApplication'}
(app/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
subprocess.run(['swiftc','-O','-target','arm64-apple-macos13.0','-framework','Cocoa','-framework','WebKit','-framework','AVFoundation',str(root/'Revoice.swift'),'-o',str(mac/'Revoice')],check=True)
# Normalize each nested Mach-O for relocation, then sign from inside out.
for p in app.rglob('*'):
 if not p.is_file() or p.is_symlink():continue
 with p.open('rb') as f:magic=f.read(4)
 if magic not in (b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'\xca\xfe\xba\xbe',b'\xbe\xba\xfe\xca'):continue
 r=subprocess.run(['otool','-D',str(p)],capture_output=True,text=True)
 if any(x.strip().startswith(('/Users/','/opt/','/usr/local/')) for x in r.stdout.splitlines()[1:]):subprocess.run(['install_name_tool','-id','@rpath/'+p.name,str(p)],check=True)
 subprocess.run(['codesign','--force','--sign','-',str(p)],check=True,capture_output=True)
subprocess.run(['codesign','--force','--deep','--sign','-',str(app)],check=True)
print(app)
