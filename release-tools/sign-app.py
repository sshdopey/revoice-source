#!/usr/bin/env python3
"""Sign a copied Revoice app and rebuild its embedded driver package."""
import argparse
import json
import pathlib
import plistlib
import subprocess
import tempfile

MAGIC = {bytes.fromhex(value) for value in (
    'cffaedfe', 'feedfacf', 'cafebabe', 'bebafeca', 'cafebabf', 'bfbafeca')}

def run(*args):
    subprocess.run([str(arg) for arg in args], check=True)

def macho(path):
    if path.is_symlink() or not path.is_file():
        return False
    with path.open('rb') as stream:
        return stream.read(4) in MAGIC

def sign(path, identity, entitlements=None):
    args = ['codesign', '--force', '--sign', identity, '--timestamp', '--options', 'runtime']
    if entitlements:
        args += ['--entitlements', str(entitlements)]
    run(*args, path)

def notarize(path, profile, logs, label):
    result = subprocess.run(['xcrun', 'notarytool', 'submit', str(path),
                             '--keychain-profile', profile, '--wait', '--output-format', 'json'],
                            capture_output=True, text=True)
    (logs / (label + '-submission.json')).write_text(result.stdout)
    if result.returncode:
        raise RuntimeError(result.stderr or 'Notary submission failed. Check the saved response.')
    response = json.loads(result.stdout)
    if response.get('status') != 'Accepted':
        if response.get('id'):
            run('xcrun', 'notarytool', 'log', response['id'], '--keychain-profile', profile,
                logs / (label + '-issues.json'))
        raise RuntimeError('Apple did not accept ' + label + '. Review the notarization log.')

def staple(path):
    run('xcrun', 'stapler', 'staple', path)
    run('xcrun', 'stapler', 'validate', path)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('app', type=pathlib.Path, help='A working copy, never /Applications/Revoice.app')
    parser.add_argument('--application-identity', required=True)
    parser.add_argument('--installer-identity', required=True)
    parser.add_argument('--notary-profile', help='Existing notarytool Keychain profile; signs only when omitted')
    args = parser.parse_args()
    app = args.app.resolve()
    if app.parent == pathlib.Path('/Applications'):
        parser.error('Use a release staging copy instead of the installed app.')
    if not args.application_identity.startswith('Developer ID Application:'):
        parser.error('Supply a Developer ID Application identity.')
    if not args.installer_identity.startswith('Developer ID Installer:'):
        parser.error('Supply a Developer ID Installer identity.')
    package = app / 'Contents/Resources/Revoice Microphone.pkg'
    if not package.is_file() or not (app / 'Contents/MacOS/Revoice').is_file():
        parser.error('Choose the complete supplied Revoice app.')
    logs = app.parent / 'notary-logs'
    if args.notary_profile:
        logs.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='revoice-sign-') as temporary:
        work = pathlib.Path(temporary)
        expanded = work / 'driver'
        run('pkgutil', '--expand-full', package, expanded)
        payload = expanded / 'Payload'
        driver = payload / 'RevoiceMicrophone.driver'
        scripts = expanded / 'Scripts'
        if not driver.is_dir() or not (scripts / 'postinstall').is_file():
            raise RuntimeError('Unexpected driver package layout; stop and inspect it.')
        sign(driver, args.application_identity)
        run('codesign', '--verify', '--strict', driver)
        signed_package = work / 'Revoice Microphone.pkg'
        run('pkgbuild', '--root', payload, '--scripts', scripts,
            '--install-location', '/Library/Audio/Plug-Ins/HAL',
            '--identifier', 'app.revoice.microphone', '--version', '0.1.0',
            '--sign', args.installer_identity, '--timestamp', signed_package)
        run('pkgutil', '--check-signature', signed_package)
        if args.notary_profile:
            notarize(signed_package, args.notary_profile, logs, 'microphone')
            staple(signed_package)
        package.write_bytes(signed_package.read_bytes())
        entitlements = work / 'audio-input.plist'
        entitlements.write_bytes(plistlib.dumps({'com.apple.security.device.audio-input': True}))
        binaries = sorted((p for p in app.rglob('*') if macho(p)),
                          key=lambda p: len(p.parts), reverse=True)
        for binary in binaries:
            needs_audio = binary.parent == app / 'Contents/MacOS' or (
                binary.parent.name == 'bin' and binary.name in {'python', 'python3', 'python3.12'})
            sign(binary, args.application_identity, entitlements if needs_audio else None)
        bundles = sorted((p for p in app.rglob('*') if p.is_dir() and
                          p.suffix in {'.vst3', '.framework', '.bundle', '.app'}),
                         key=lambda p: len(p.parts), reverse=True)
        for bundle in bundles:
            sign(bundle, args.application_identity)
        sign(app, args.application_identity, entitlements)
        run('codesign', '--verify', '--deep', '--strict', '--verbose=2', app)
        if args.notary_profile:
            archive = work / 'Revoice-notary.zip'
            run('ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', app, archive)
            notarize(archive, args.notary_profile, logs, 'app')
            staple(app)
    print('App and driver signed' + (' and notarized.' if args.notary_profile else
          '; NOT notarized yet. Follow START-HERE.md.'))

if __name__ == '__main__':
    main()
