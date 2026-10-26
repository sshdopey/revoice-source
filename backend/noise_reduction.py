import ctypes
from pathlib import Path
import numpy as np


class NoiseReducer:
    def __init__(self):
        library = Path(__file__).resolve().parent.parent / 'audio/librnnoise.dylib'
        if not library.is_file():
            library = Path(__file__).resolve().parent.parent / 'build/librnnoise.dylib'
        self.lib = ctypes.CDLL(str(library))
        self.lib.rnnoise_create.argtypes = []
        self.lib.rnnoise_create.restype = ctypes.c_void_p
        self.lib.rnnoise_destroy.argtypes = [ctypes.c_void_p]
        self.lib.rnnoise_destroy.restype = None
        pointer = ctypes.POINTER(ctypes.c_float)
        self.lib.rnnoise_process_frame.argtypes = [ctypes.c_void_p, pointer, pointer]
        self.lib.rnnoise_process_frame.restype = ctypes.c_float
        self.context = self.lib.rnnoise_create()
        if not self.context:
            raise RuntimeError('Noise reduction could not start.')
        self.input = np.empty(480, dtype=np.float32)
        self.output = np.empty(480, dtype=np.float32)
        self.input_pointer = self.input.ctypes.data_as(pointer)
        self.output_pointer = self.output.ctypes.data_as(pointer)

    def process(self, samples):
        if len(samples) != 480:
            raise ValueError('Noise reduction requires a 10 ms, 48 kHz frame.')
        np.multiply(samples, 32768., out=self.input)
        self.lib.rnnoise_process_frame(self.context, self.output_pointer, self.input_pointer)
        return self.output / 32768.

    def close(self):
        if self.context:
            self.lib.rnnoise_destroy(self.context)
            self.context = None
