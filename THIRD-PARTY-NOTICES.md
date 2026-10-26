# Revoice 0.2.0 internal host

This personal-use build includes the official Beatrice 2.0.0-rc.3 macOS VST3 inside Revoice.app, loaded through its exported inference API. The wrapper's MIT license and the separate LICENSES_BUNDLED notice are retained under Licenses. That notice identifies a private inference library; this package does not claim a grant of public or commercial redistribution rights. Target voice models remain separate. The custom HAL driver is derived from BlackHole under GPL-3.0, with corresponding source and build script included. NumPy, SoundDevice, SoundFile, CFFI, typing_extensions and their packaged license notices retain their respective licenses.

## Historical RVC preview notices

The following notices describe the older archived RVC build. Those engine components are absent from 0.2.0.

# Third-party software

Revoice preview source is GPL-3.0. Revoice includes the Applio RVC inference engine (MIT, AI Hispano), a customized BlackHole audio server plug-in (GPL-3.0, Existential Audio), CPython, PyTorch, NumPy, SciPy, SoundDevice/PortAudio, SoundFile/libsndfile, FAISS, Transformers, Librosa, Pedalboard, and their dependencies. Their license files and package metadata are retained in the bundled runtime. DiceBear Waves avatar artwork is CC0 1.0: https://www.dicebear.com/styles/waves/ . Avatars are bundled locally; importing voices makes no avatar API call.

Revoice Microphone is a separately installed, customized build of the GPL-3.0 driver. Complete corresponding upstream source and the customization/build script are included under Contents/Resources/Driver Source. It is not a proprietary driver written from scratch. The GPL license is included. Revoice distribution source is provided separately alongside this preview DMG.

Model assets: ContentVec (MIT license included) (https://github.com/auspicious3000/contentvec , https://huggingface.co/IAHispano/Applio/tree/main/Resources/embedders/contentvec) and RMVPE (Apache-2.0 license included, https://github.com/Dream-High/RMVPE). These generic analysis assets do not contain the user's trained voice. The friend's trained RVC model and retrieval index are distributed only in a separate private ZIP.

Preview distribution: not Developer ID signed or notarized. Revoice's local ad-hoc signature is not public distribution approval. Public redistribution requires completing signing/notarization and a review of model-asset redistribution permissions. Apple Silicon only; no claim of tested compatibility on Intel or other operating systems.


Revoice avatar generation bundles DiceBear Core 10.6.0 (MIT; full license in frontend/avatars/DiceBear-core-LICENSE.txt) and the Waves definition from DiceBear Styles 10.6.0 (CC0 1.0, https://www.dicebear.com/styles/waves/). Avatars generate locally; names and voice IDs are not sent to DiceBear.


This build includes RNNoise v0.1 (Xiph/Mozilla, upstream commit cdf196b1e9de2f8ff1003328ebf9a4316477429d) for optional local 48 kHz noise reduction. Its BSD-style COPYING notice is included in Licenses/RNNoise-COPYING.txt. Matching source is included in the source archive under vendor/rnnoise; no external service receives audio.
