# Revoice

Apple Silicon macOS voice changer. A native window hosts a local voice library and Beatrice inference, with Revoice Microphone routing audio into calling and recording apps.

## Source availability

This repository contains the Revoice 0.2.4 application source, microphone driver source, noise-reduction source, and checks. It does not provide an installer, the Beatrice inference binary, a Python runtime, voice models, or recordings. Packaging requires a separately obtained compatible runtime and engine; see [RELEASING.md](RELEASING.md).

With a locally packaged build, place Revoice in Applications and open it. The app includes microphone setup; macOS asks for administrator approval when its driver is missing. Select **Revoice Microphone** in your calling app.

The library starts empty. Add a name and a compatible Beatrice ZIP containing `phone_extractor.bin`, `pitch_estimator.bin`, `waveform_generator.bin`, `embedding_setter.bin`, and `speaker_embeddings.bin`. Voices and recordings are deliberately excluded from this repository and its releases.

Requires Apple Silicon and macOS 13+. The local packaging scripts produce ad-hoc signed builds, which are not notarized and may require approval in macOS Privacy & Security. Local checks do not replace installation and audio testing on another Mac.

## Controls

- Closing the window or pressing Cmd+Q keeps audio running and hides the Dock icon.
- Use the menu-bar controls for voice selection, conversion, mute and monitoring.
- Hide the menu-bar icon in Settings; reopen Revoice from Applications to access controls again.
- **Quit Revoice**, **Quit Revoice completely** in Settings, or Cmd+Option+Q stops the engine.
- Conversion off passes your natural voice through Revoice Microphone. Hear myself controls headphone monitoring independently.

Audio stays local. macOS microphone privacy indicators remain active while recording. No account is required.

## Development

`Revoice.swift` is the native shell, `frontend/` is the local interface, and `backend/` handles audio, models and recording. `vendor/` contains the microphone driver and noise-reduction sources with their licenses.

Create a Python environment and run the fixture-free checks:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-test.txt
.venv/bin/python scripts/check.py
```

On Linux, install PortAudio (`libportaudio2`) first. Tests use temporary settings and mocked audio devices; they do not open a microphone. Native compilation and full packaging run on macOS.

## Build and release

See [RELEASING.md](RELEASING.md). Local packaging rebuilds the native app, microphone driver and noise reducer from this source while reusing a separately supplied, checksum-pinned Python runtime and Beatrice binary. It does not build Beatrice's inference library from source. Automatic binary publishing is not configured in this repository.

Compatible new voice exports can be imported without rebuilding the application. No voice model or training job runs in CI. DSP processing times are not microphone-to-headphone latency measurements.

Revoice source is GPL-3.0; third-party components retain their own licenses. See [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
