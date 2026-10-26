# Local packaging

This public repository publishes Revoice source. It does not host the private preview installer, runtime bootstrap, Beatrice inference binary, or voice models. The Checks workflow runs source checks; no workflow publishes application binaries.

## Requirements

Use an Apple Silicon Mac with Xcode Command Line Tools and Python 3. Packaging also requires the original compatible Revoice 0.2.4 bootstrap DMG, obtained separately with permission to use its bundled components. There is no public bootstrap download configured here.

The expected bootstrap SHA-256 is:

```text
6a6a529109c8865f0cddc6b17b1bf2d0b72bb33e219feb01c12d2991c8d982a2
```

## Build locally

Point the packaging script at your local bootstrap:

```sh
REVOICE_BOOTSTRAP_DMG="/path/to/Revoice.dmg" bash scripts/build-release.sh
```

The script verifies the checksum, mounts the DMG read-only, rebuilds the microphone package and app, runs fixture-free checks, and creates `dist/Revoice.dmg`. It does not install the driver or change an installed Revoice app. It reuses the bundled Python runtime and Beatrice inference binary; it is not a complete source build of those dependencies.

The Beatrice bundled notice identifies a private inference library, and the existing preview does not establish permission for public or commercial redistribution. Keep the third-party notices intact. Publishing this application's GPL source does not grant rights to redistribute separately obtained engine binaries or voice models.

## Apple signing and notarization

Local preview builds use ad-hoc signatures. No Apple credentials are stored in the repository.

With Developer ID Application and Installer identities available on a release Mac, run `release-tools/sign-app.py --help` against the staged `build/Revoice-Beatrice.app`. Supply both identities and a notarytool Keychain profile. The script signs and notarizes the embedded microphone package, then the application, and staples their tickets. Rebuild the DMG afterwards; notarize/staple the DMG and validate Gatekeeper before distributing it as a notarized release. Do not rerun the app builder after Developer ID signing, as it replaces signatures.

## Validation

Before sharing a locally built application, verify first installation, driver approval, microphone permission, ZIP import, call-app routing, background operation, explicit quit, device reconnect and sleep/wake on a second Mac. Update `VERSION` and `BUILD_NUMBER` together when preparing a new version, and keep the About text and frontend version label in sync.
