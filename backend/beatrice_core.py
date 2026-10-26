import os,sys,ctypes,threading,queue,time,numpy as np
class Config:
    # bypass=True means DSP is INACTIVE (raw mic passthrough).
    # bypass=False means DSP is ACTIVE (voice is being converted).
    # Start with bypass=True so the user hears their own raw mic on launch.
    bypass = True
    speaker_index = -1
    pitch_shift = 0.0  # Semitones shift
    formant_shift = 0.0  # Formant shift value
    volume = 1.0
    gate_threshold = 0.0  # Noise gate threshold
    input_meter = 0.0
    output_meter = 0.0
    muted = False
    
    # Advanced routing
    input_device_id = None
    output_device_id = None
    monitor_device_id = None
    hear_yourself = False
    
    # Deferred parameter updates — set by HTTP thread, consumed by audio callback
    pending_speaker_index = None
    pending_formant_shift = None
    
    # Persistent ctypes object to avoid pointer garbage collection and GC segmentation faults
    formant_val_ctypes = ctypes.c_float(0.0)
    
    # DSP ready flag — set to True after models are loaded and speaker 0 is initialised
    dsp_ready = False
    current_model = "jvs"

class GateState:
    envelope = 0.0
    hold_counter = 0

def save_settings(): pass
def clear_monitor_queue(): pass
def enqueue_monitor(*args): pass
# Resolve all paths relative to this script's directory so the project
# works on any machine regardless of where it is cloned or extracted.
_BASE_DIR = os.path.dirname(__file__)
from engine_paths import resolve_library
lib_path = resolve_library()
if lib_path is None:
    raise RuntimeError('Install the official Beatrice 2.0.0-rc.3 macOS plugin to enable this internal preview.')

lib = ctypes.CDLL(str(lib_path))
print("[+] Successfully loaded Beatrice 2.0.0-rc.3 VST3 library")

# C API declarations
lib.Beatrice20rc0_CreatePhoneExtractor.restype = ctypes.c_void_p
lib.Beatrice20rc0_ReadPhoneExtractorParameters.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lib.Beatrice20rc0_ReadPhoneExtractorParameters.restype = ctypes.c_int
lib.Beatrice20rc0_CreatePhoneContext1.argtypes = []
lib.Beatrice20rc0_CreatePhoneContext1.restype = ctypes.c_void_p
lib.Beatrice20rc0_DestroyPhoneContext1.argtypes = [ctypes.c_void_p]
lib.Beatrice20rc0_DestroyPhoneExtractor.argtypes = [ctypes.c_void_p]

lib.Beatrice20rc0_CreatePitchEstimator.restype = ctypes.c_void_p
lib.Beatrice20rc0_ReadPitchEstimatorParameters.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lib.Beatrice20rc0_ReadPitchEstimatorParameters.restype = ctypes.c_int
lib.Beatrice20rc0_CreatePitchContext1.argtypes = []
lib.Beatrice20rc0_CreatePitchContext1.restype = ctypes.c_void_p
lib.Beatrice20rc0_DestroyPitchContext1.argtypes = [ctypes.c_void_p]
lib.Beatrice20rc0_DestroyPitchEstimator.argtypes = [ctypes.c_void_p]

lib.Beatrice20rc0_CreateWaveformGenerator.restype = ctypes.c_void_p
lib.Beatrice20rc0_ReadWaveformGeneratorParameters.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lib.Beatrice20rc0_ReadWaveformGeneratorParameters.restype = ctypes.c_int
lib.Beatrice20rc0_CreateWaveformContext1.argtypes = []
lib.Beatrice20rc0_CreateWaveformContext1.restype = ctypes.c_void_p
lib.Beatrice20rc0_DestroyWaveformContext1.argtypes = [ctypes.c_void_p]
lib.Beatrice20rc0_DestroyWaveformGenerator.argtypes = [ctypes.c_void_p]

lib.Beatrice20rc0_CreateEmbeddingSetter.restype = ctypes.c_void_p
lib.Beatrice20rc0_ReadEmbeddingSetterParameters.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
lib.Beatrice20rc0_ReadEmbeddingSetterParameters.restype = ctypes.c_int
lib.Beatrice20rc0_CreateEmbeddingContext.argtypes = []
lib.Beatrice20rc0_CreateEmbeddingContext.restype = ctypes.c_void_p
lib.Beatrice20rc0_DestroyEmbeddingContext.argtypes = [ctypes.c_void_p]
lib.Beatrice20rc0_DestroyEmbeddingSetter.argtypes = [ctypes.c_void_p]

# Speaker Embeddings and Setters API
lib.Beatrice20rc0_ReadNSpeakers.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_int)]
lib.Beatrice20rc0_ReadNSpeakers.restype = ctypes.c_int

lib.Beatrice20rc0_ReadSpeakerEmbeddings.argtypes = [
    ctypes.c_char_p,
    ctypes.POINTER(ctypes.c_float),
    ctypes.POINTER(ctypes.c_float),
    ctypes.POINTER(ctypes.c_float),
    ctypes.POINTER(ctypes.c_float)
]
lib.Beatrice20rc0_ReadSpeakerEmbeddings.restype = ctypes.c_int

lib.Beatrice20rc0_SetCodebook.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float)]
lib.Beatrice20rc0_SetCodebook.restype = None

lib.Beatrice20rc0_SetAdditiveSpeakerEmbedding.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float), ctypes.c_void_p, ctypes.c_void_p]
lib.Beatrice20rc0_SetAdditiveSpeakerEmbedding.restype = None

lib.Beatrice20rc0_RegisterKeyValueSpeakerEmbedding.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float), ctypes.c_void_p]
lib.Beatrice20rc0_RegisterKeyValueSpeakerEmbedding.restype = None

lib.Beatrice20rc0_SetKeyValueSpeakerEmbedding.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]
lib.Beatrice20rc0_SetKeyValueSpeakerEmbedding.restype = None

lib.Beatrice20rc0_SetFormantShiftEmbedding.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float), ctypes.c_void_p, ctypes.c_void_p]
lib.Beatrice20rc0_SetFormantShiftEmbedding.restype = None

# DSP bindings
lib.Beatrice20rc0_ExtractPhone1.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float), ctypes.c_void_p]
lib.Beatrice20rc0_ExtractPhone1.restype = None

lib.Beatrice20rc0_EstimatePitch1.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_float), ctypes.c_void_p]
lib.Beatrice20rc0_EstimatePitch1.restype = None

lib.Beatrice20rc0_GenerateWaveform1.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float), ctypes.c_void_p]
lib.Beatrice20rc0_GenerateWaveform1.restype = None

# Global model references for runtime reloading
model_lock = threading.RLock()
phone_extractor = None
phone_context = None
pitch_estimator = None
pitch_context = None
waveform_generator = None
waveform_context = None
embedding_setter = None
embedding_context = None
n_speakers = 0
codebooks = None
additive_embeddings = None
formant_shift_embeddings = None
kv_embeddings = None

def load_vst3_model(model_name):
    with model_lock:
        if Config.dsp_ready and Config.current_model == model_name:
            return
        result = _load_vst3_model(model_name)
        save_settings()
        return result

def _load_vst3_model(model_name):
    global phone_extractor, phone_context
    global pitch_estimator, pitch_context
    global waveform_generator, waveform_context
    global embedding_setter, embedding_context
    global codebooks, additive_embeddings, formant_shift_embeddings, kv_embeddings, n_speakers
    
    if model_name not in ["jvs", "official_1", "old_tts", "trump"] and not model_name.startswith("custom:"):
        print(f"[-] Invalid model name requested: {model_name}")
        return
        
    if model_name.startswith("custom:"):
        folder_name = model_name[7:]
        if not folder_name or os.path.basename(folder_name) != folder_name or folder_name in ('.', '..'):
            return
        #  # strip 'custom:' prefix
        model_dir = os.path.join("custom_models", folder_name)
        custom_models_base = os.environ.get("BEATRICE_CUSTOM_MODELS_DIR")
        if custom_models_base:
            paraphernalia_dir = os.path.join(custom_models_base, folder_name)
        else:
            paraphernalia_dir = os.path.join(_BASE_DIR, "custom_models", folder_name)
        if not os.path.isdir(paraphernalia_dir):
            print(f"[-] Custom model folder not found: {paraphernalia_dir}")
            return
    else:
        if model_name == "official_1":
            model_dir = "beatrice_paraphernalia_official_1"
        elif model_name == "old_tts":
            model_dir = "beatrice_paraphernalia_old_tts"
        elif model_name == "trump":
            model_dir = "beatrice_paraphernalia_trump_00001200"
        else:
            model_dir = "beatrice_paraphernalia_jvs"
        paraphernalia_dir = os.path.join(_BASE_DIR, model_dir)
    phone_bin = f"{paraphernalia_dir}/phone_extractor.bin".encode()
    pitch_bin = f"{paraphernalia_dir}/pitch_estimator.bin".encode()
    waveform_bin = f"{paraphernalia_dir}/waveform_generator.bin".encode()
    embedding_bin_path = f"{paraphernalia_dir}/embedding_setter.bin"
    if not os.path.exists(embedding_bin_path):
        embedding_bin_path = os.path.join(_BASE_DIR, "beatrice_paraphernalia_jvs/embedding_setter.bin")
    embedding_bin = embedding_bin_path.encode()
    speaker_bin = f"{paraphernalia_dir}/speaker_embeddings.bin".encode()
    
    for required in (phone_bin, pitch_bin, waveform_bin, embedding_bin, speaker_bin):
        if not os.path.isfile(required):
            print(f'Model file missing: {os.fsdecode(required)}')
            return
    # 1. Clear dsp_ready to fallback to bypass mode safely during load
    Config.dsp_ready = False
    
    # Give a tiny sleep to let ongoing audio callbacks exit VST3 inference
    time.sleep(0.02)
    
    with model_lock:
        # Destroy existing native components
        try:
            if embedding_context:
                lib.Beatrice20rc0_DestroyEmbeddingContext(embedding_context)
            if waveform_context:
                lib.Beatrice20rc0_DestroyWaveformContext1(waveform_context)
            if pitch_context:
                lib.Beatrice20rc0_DestroyPitchContext1(pitch_context)
            if phone_context:
                lib.Beatrice20rc0_DestroyPhoneContext1(phone_context)
                
            if embedding_setter:
                lib.Beatrice20rc0_DestroyEmbeddingSetter(embedding_setter)
            if waveform_generator:
                lib.Beatrice20rc0_DestroyWaveformGenerator(waveform_generator)
            if pitch_estimator:
                lib.Beatrice20rc0_DestroyPitchEstimator(pitch_estimator)
            if phone_extractor:
                lib.Beatrice20rc0_DestroyPhoneExtractor(phone_extractor)
            print("[+] Successfully cleared old VST3 model contexts")
        except Exception as e:
            print("[-] Error destroying existing VST3 components:", e)
            
        print(f"[*] Loading Beatrice VST3 model parameters from: {model_dir}")
        try:
            phone_extractor = lib.Beatrice20rc0_CreatePhoneExtractor()
            lib.Beatrice20rc0_ReadPhoneExtractorParameters(phone_extractor, phone_bin)
            phone_context = lib.Beatrice20rc0_CreatePhoneContext1()
            
            pitch_estimator = lib.Beatrice20rc0_CreatePitchEstimator()
            lib.Beatrice20rc0_ReadPitchEstimatorParameters(pitch_estimator, pitch_bin)
            pitch_context = lib.Beatrice20rc0_CreatePitchContext1()
            
            waveform_generator = lib.Beatrice20rc0_CreateWaveformGenerator()
            lib.Beatrice20rc0_ReadWaveformGeneratorParameters(waveform_generator, waveform_bin)
            waveform_context = lib.Beatrice20rc0_CreateWaveformContext1()
            
            embedding_setter = lib.Beatrice20rc0_CreateEmbeddingSetter()
            lib.Beatrice20rc0_ReadEmbeddingSetterParameters(embedding_setter, embedding_bin)
            
            _n_spk_val = ctypes.c_int(0)
            lib.Beatrice20rc0_ReadNSpeakers(speaker_bin, ctypes.byref(_n_spk_val))
            n_speakers = _n_spk_val.value
            if not 1 <= n_speakers <= 256:
                raise ValueError('Invalid speaker embeddings.')
            print(f"[*] Speaker count: {n_speakers}")
            
            codebooks = (ctypes.c_float * (n_speakers * 512 * 128))()
            additive_embeddings = (ctypes.c_float * (n_speakers * 256))()
            formant_shift_embeddings = (ctypes.c_float * (9 * 256))()
            kv_embeddings = (ctypes.c_float * (n_speakers * 384 * 128))()
            
            lib.Beatrice20rc0_ReadSpeakerEmbeddings(
                speaker_bin,
                ctypes.cast(codebooks, ctypes.POINTER(ctypes.c_float)),
                ctypes.cast(additive_embeddings, ctypes.POINTER(ctypes.c_float)),
                ctypes.cast(formant_shift_embeddings, ctypes.POINTER(ctypes.c_float)),
                ctypes.cast(kv_embeddings, ctypes.POINTER(ctypes.c_float))
            )
            
            embedding_context = lib.Beatrice20rc0_CreateEmbeddingContext()
            
            # Apply default speaker index and formant shift
            Config.speaker_index = 0
            update_target_speaker(0)
            update_formant_shift(Config.formant_shift)
            
            Config.current_model = model_name
            Config.dsp_ready = True
            print(f"[+] Loaded VST3 model: {model_name} successfully")
        except Exception as e:
            print(f"[-] Failed to load model {model_name}: {e}")


# Helper functions to update target speaker index and formant shift coefficients
def update_target_speaker(speaker_id):
    with model_lock:
        return _update_target_speaker(speaker_id)

def _update_target_speaker(speaker_id):
    if speaker_id < 0 or speaker_id >= n_speakers:
        return
    try:
        # 1. Set Codebook
        codebook_offset = speaker_id * (512 * 128)
        codebook_ptr = ctypes.cast(ctypes.byref(codebooks, codebook_offset * ctypes.sizeof(ctypes.c_float)), ctypes.POINTER(ctypes.c_float))
        lib.Beatrice20rc0_SetCodebook(phone_context, codebook_ptr)
        
        # 2. Set Additive Speaker Embedding
        additive_offset = speaker_id * 256
        additive_ptr = ctypes.cast(ctypes.byref(additive_embeddings, additive_offset * ctypes.sizeof(ctypes.c_float)), ctypes.POINTER(ctypes.c_float))
        lib.Beatrice20rc0_SetAdditiveSpeakerEmbedding(
            embedding_setter, additive_ptr, embedding_context, waveform_context
        )
        
        # 3. Register Key-Value Speaker Embedding
        kv_offset = speaker_id * (384 * 128)
        kv_ptr = ctypes.cast(ctypes.byref(kv_embeddings, kv_offset * ctypes.sizeof(ctypes.c_float)), ctypes.POINTER(ctypes.c_float))
        lib.Beatrice20rc0_RegisterKeyValueSpeakerEmbedding(
            embedding_setter, kv_ptr, embedding_context
        )
        
        # 4. Set Key-Value Speaker Embedding (4 blocks loop)
        for block in range(4):
            lib.Beatrice20rc0_SetKeyValueSpeakerEmbedding(
                embedding_setter, block, embedding_context, waveform_context
            )
        Config.speaker_index = speaker_id
        print(f"[+] Successfully switched target speaker to index: {speaker_id}")
    except Exception as e:
        print("Error in update_target_speaker:", e)

def update_formant_shift(formant_shift_val):
    try:
        # Map formant shift in [-2.0, 2.0] to index [0, 8]
        idx = int(round(formant_shift_val * 2.0 + 4.0))
        idx = max(0, min(8, idx))
        
        # Set Formant Shift Embedding
        formant_offset = idx * 256
        formant_ptr = ctypes.cast(ctypes.byref(formant_shift_embeddings, formant_offset * ctypes.sizeof(ctypes.c_float)), ctypes.POINTER(ctypes.c_float))
        lib.Beatrice20rc0_SetFormantShiftEmbedding(
            embedding_setter, formant_ptr, embedding_context, waveform_context
        )
    except Exception as e:
        print("Error in update_formant_shift:", e)

# Persistent ctypes buffers for thread-safe real-time DSP execution to prevent real-time allocation overhead
class DSPBuffers:
    phone_features = (ctypes.c_float * 128)()
    pitch_features = (ctypes.c_float * 4)()
    out_samples   = (ctypes.c_float * 240)()

# Background speaker-update worker so the audio callback is never blocked by
# heavy C library calls (SetCodebook etc.).  The callback sets pending_speaker_index;
# this thread picks it up and applies it outside the real-time path.
_speaker_update_queue = queue.Queue(maxsize=4)

def _speaker_update_worker():
    while True:
        try:
            idx = _speaker_update_queue.get()
            if idx is None:
                break
            update_target_speaker(idx)
        except Exception as ex:
            print(f'[Beatrice] Speaker update worker error: {ex}')

_speaker_update_thread = threading.Thread(target=_speaker_update_worker, daemon=True)
_speaker_update_thread.start()

# Real-time audio stream callback
def dsp_callback(indata, outdata, frames, time_info, status, output_sample_rate=16000):
    # Input volume meter
    in_samples = indata[:, 0]
    if Config.muted:
        outdata.fill(0)
        Config.input_meter = Config.output_meter = 0.0
        clear_monitor_queue()
        return
    Config.input_meter = float(np.max(np.abs(in_samples)))

    # --- Noise gate envelope follower ---
    is_above = Config.input_meter >= Config.gate_threshold
    if is_above:
        GateState.envelope = 1.0
        GateState.hold_counter = 20  # 200ms hold (20 blocks * 10ms)
    else:
        if GateState.hold_counter > 0:
            GateState.hold_counter -= 1
            GateState.envelope = 1.0
        else:
            # Release time ~150ms: 15 blocks (decay rate per 10ms block: 1/15 = 0.067)
            GateState.envelope = max(0.0, GateState.envelope - 0.067)

    # Smoothly gate the input signal
    in_samples = in_samples * GateState.envelope

    if GateState.envelope <= 0.0:
        outdata[:, 0] = 0.0
        Config.output_meter = 0.0
        return

    # --- Dispatch pending speaker index to the background worker ---
    # We do NOT call update_target_speaker() directly here; that involves
    # multiple heavy C library calls and will cause callback overruns.
    if Config.pending_speaker_index is not None:
        try:
            _speaker_update_queue.put_nowait(Config.pending_speaker_index)
        except queue.Full:
            pass  # Drop if update queue is saturated; next change will catch it
        else:
            Config.pending_speaker_index = None

    # --- Formant shift can be updated safely here (single C call) ---
    if Config.pending_formant_shift is not None:
        Config.formant_shift = Config.pending_formant_shift
        try:
            update_formant_shift(Config.formant_shift)
        except Exception:
            pass
        Config.pending_formant_shift = None

    # --- Bypass: pass mic audio through unchanged ---
    if not Config.dsp_ready:
        outdata.fill(0)
        return
    if Config.bypass:
        Config.output_meter = float(Config.input_meter * Config.volume)
        out_numpy = np.interp(np.arange(len(outdata))*16000/output_sample_rate, np.arange(len(in_samples)), in_samples).astype(np.float32) * Config.volume
        outdata[:, 0] = out_numpy
        if Config.hear_yourself:
            enqueue_monitor(out_numpy, output_sample_rate)
        return

    # --- DSP pipeline ---
    try:
        in_samples_c = np.ascontiguousarray(in_samples, dtype=np.float32)
        input_ptr = in_samples_c.ctypes.data_as(ctypes.POINTER(ctypes.c_float))

        # 1. Phone feature extraction (128 floats)
        lib.Beatrice20rc0_ExtractPhone1(
            phone_extractor, input_ptr, DSPBuffers.phone_features, phone_context
        )

        # 2. Pitch estimation (1 int bin + 4 pitch floats)
        pitch_bin_val = ctypes.c_int(0)
        lib.Beatrice20rc0_EstimatePitch1(
            pitch_estimator, input_ptr,
            ctypes.byref(pitch_bin_val), DSPBuffers.pitch_features, pitch_context
        )

        # Optional pitch shift
        if Config.pitch_shift != 0.0 and pitch_bin_val.value > 0:
            shifted = pitch_bin_val.value + int(round(Config.pitch_shift * 8.0))
            pitch_bin_val.value = max(1, min(447, shifted))

        # 3. Waveform synthesis (240 floats @ 24 kHz)
        lib.Beatrice20rc0_GenerateWaveform1(
            waveform_generator,
            DSPBuffers.phone_features,
            ctypes.byref(pitch_bin_val),
            DSPBuffers.pitch_features,
            DSPBuffers.out_samples,
            waveform_context
        )

        # Read synthesised output — .copy() is critical: np.frombuffer gives a
        # read-only view into the ctypes buffer; without copy() the interp below
        # can reference stale data if the buffer is reused before numpy is done.
        out_24k = np.frombuffer(DSPBuffers.out_samples, dtype=np.float32).copy()

        if output_sample_rate == 24000:
            out_numpy = out_24k * Config.volume
        else:
            out_numpy = np.interp(np.arange(160)*1.5, np.arange(240), out_24k).astype(np.float32) * Config.volume

        outdata[:, 0] = out_numpy
        Config.output_meter = float(np.max(np.abs(out_numpy)))

        if Config.hear_yourself:
            enqueue_monitor(out_numpy, output_sample_rate)

    except Exception as exc:
        # Log the real reason for the fallback — this helps diagnose model issues
        import traceback
        print(f'[Beatrice] DSP callback exception (falling back to passthrough): {exc}')
        traceback.print_exc()
        fallback = np.zeros_like(in_samples)
        outdata[:, 0] = fallback
        Config.output_meter = float(Config.input_meter * Config.volume)
