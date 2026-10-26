"""Causal, continuous FIR conversion for the 48k → 16k → 24k → 48k voice path."""
import numpy as np


def lowpass(taps, cutoff, rate=48000):
    offset = np.arange(taps, dtype=np.float64) - (taps - 1) / 2
    h = 2 * cutoff / rate * np.sinc(2 * cutoff / rate * offset)
    h *= np.kaiser(taps, 8)
    return (h / h.sum()).astype(np.float32)


class StreamingFIR:
    def __init__(self, coefficients):
        self.coefficients = coefficients
        self.history = np.zeros(len(coefficients) - 1, dtype=np.float32)

    def reset(self):
        self.history.fill(0)

    def process(self, samples):
        joined = np.concatenate((self.history, np.asarray(samples, dtype=np.float32)))
        result = np.convolve(joined, self.coefficients, mode='valid')
        self.history[:] = joined[-len(self.history):]
        return result


class VoiceResampler:
    # 63 + 31 samples at 48k: 1.96 ms total filter group delay, no block queue.
    def __init__(self):
        self.input_filter = StreamingFIR(lowpass(127, 7200))
        self.output_filter = StreamingFIR(2 * lowpass(63, 10800))

    def reset(self):
        self.input_filter.reset()
        self.output_filter.reset()

    def downsample(self, samples):
        if len(samples) != 480:
            raise ValueError('Expected a 480-sample microphone block.')
        return self.input_filter.process(samples)[::3].copy()

    def upsample(self, samples):
        if len(samples) != 240:
            raise ValueError('Expected a 240-sample Beatrice block.')
        expanded = np.zeros(480, dtype=np.float32)
        expanded[::2] = samples
        return self.output_filter.process(expanded)
