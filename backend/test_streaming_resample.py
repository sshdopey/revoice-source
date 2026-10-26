import json,time
from pathlib import Path
import numpy as np
from streaming_resample import VoiceResampler

rng=np.random.default_rng(4)
x=rng.normal(size=480*100).astype(np.float32)
r=VoiceResampler()
y=np.concatenate([r.downsample(b) for b in x.reshape(-1,480)])
reference=np.convolve(x,r.input_filter.coefficients)[:len(x):3]
assert np.allclose(y,reference,atol=1e-6)
a=rng.normal(size=240*100).astype(np.float32)
z=np.concatenate([r.upsample(b) for b in a.reshape(-1,240)])
expanded=np.zeros(len(a)*2,dtype=np.float32);expanded[::2]=a
assert np.allclose(z,np.convolve(expanded,r.output_filter.coefficients)[:len(expanded)],atol=1e-6)

def response(freq):
 r=VoiceResampler();tone=np.sin(2*np.pi*freq*np.arange(48000)/48000).astype(np.float32)
 out=np.concatenate([r.downsample(b) for b in tone.reshape(-1,480)])[100:]
 return float(np.sqrt(np.mean(out*out)))
passband=response(1000);alias=response(10000)
assert abs(passband-2**-.5)<.002
assert 20*np.log10(alias/passband)<-75
r=VoiceResampler();ones=np.ones(240,dtype=np.float32)
u=np.concatenate([r.upsample(ones) for _ in range(5)])
assert np.max(abs(u[200:]-1))<.001
r.reset();assert not r.downsample(np.zeros(480,dtype=np.float32)).any();assert not r.upsample(np.zeros(240,dtype=np.float32)).any()
timings=[]
for _ in range(1000):
 start=time.perf_counter();r.downsample(x[:480]);r.upsample(a[:240]);timings.append((time.perf_counter()-start)*1000)
result={'block_continuity_verified':True,'passband_rms':passband,'10khz_alias_rejection_db':float(20*np.log10(alias/passband)),'filter_group_delay_ms':94/48,'resampling_p95_processing_ms':float(np.percentile(timings,95)),'note':'Processing and filter delay only; not total microphone-to-headphone latency.'}
print(json.dumps(result,indent=2))
