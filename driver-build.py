import pathlib,subprocess,plistlib,shutil,uuid
root=pathlib.Path(__file__).resolve().parent
source_root=root/'vendor/BlackHole' if (root/'vendor/BlackHole').exists() else root/'BlackHole'
src=source_root/'BlackHole/BlackHole.c'
stage=root/'build/driver'; bundle=stage/'RevoiceMicrophone.driver'; mac=bundle/'Contents/MacOS'; resources=bundle/'Contents/Resources'
mac.mkdir(parents=True,exist_ok=True);resources.mkdir(parents=True,exist_ok=True)
args=['clang','-bundle','-O3','-arch','arm64','-arch','x86_64','-mmacosx-version-min=12.0','-framework','CoreAudio','-framework','CoreFoundation','-framework','Accelerate',str(src),'-o',str(mac/'RevoiceMicrophone')]
for macro in ['kDriver_Name="RevoiceMicrophone"','kPlugIn_BundleID="app.revoice.microphone"','kDevice_Name="Revoice Microphone"','kManufacturer_Name="Revoice"','kPlugIn_Icon="Revoice.icns"','kHas_Driver_Name_Format=false','kNumber_Of_Channels=2','kLatency_Frame_Size=0','kCanBeDefaultSystemDevice=false']:
 args.append('-D'+macro)
subprocess.run(args,check=True)
factory='ff218ee7-0e9c-4d84-8a27-90d6c482a31b'
info={'CFBundleExecutable':'RevoiceMicrophone','CFBundleIdentifier':'app.revoice.microphone','CFBundleName':'Revoice Microphone','CFBundlePackageType':'BNDL','CFBundleVersion':'1','CFBundleShortVersionString':'0.1.0','CFPlugInFactories':{factory:'BlackHole_Create'},'CFPlugInTypes':{'443ABAB8-E7B3-491A-B985-BEB9187030DB':[factory]}}
(bundle/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
shutil.copy(source_root/'LICENSE',resources/'LICENSE-GPL-3.0.txt')
if (root/'build/Revoice.icns').exists():shutil.copy(root/'build/Revoice.icns',resources/'Revoice.icns')
subprocess.run(['codesign','--force','--sign','-',str(bundle)],check=True)
pkg=root/'build/Revoice Microphone.pkg'
scripts=root/'build/driver-scripts';scripts.mkdir(exist_ok=True)
post=scripts/'postinstall';post.write_text('#!/bin/sh\n/usr/bin/killall coreaudiod 2>/dev/null || true\nexit 0\n');post.chmod(0o755)
subprocess.run(['pkgbuild','--root',str(stage),'--scripts',str(scripts),'--install-location','/Library/Audio/Plug-Ins/HAL','--identifier','app.revoice.microphone','--version','0.1.0',str(pkg)],check=True)
print(pkg)
