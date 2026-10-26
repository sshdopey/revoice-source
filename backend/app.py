import io,os,sys,pathlib,json,time,threading,queue,multiprocessing as mp,zipfile,uuid,shutil,signal,secrets,logging
from collections import deque
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
os.environ['OMP_NUM_THREADS']='1'
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
HERE=pathlib.Path(__file__).resolve().parent
ENGINE=pathlib.Path(os.environ.get('REVOICE_ENGINE',str(HERE.parent/'engine')))
sys.path.insert(0,str(HERE))
import numpy as np,sounddevice as sd,soundfile as sf
from engine_paths import resolve_library
from streaming_resample import VoiceResampler
HOME=pathlib.Path(os.environ.get('REVOICE_HOME',str(pathlib.Path.home()/'Library/Application Support/Revoice')))
HOME.mkdir(parents=True,exist_ok=True);VOICES=HOME/'voices';VOICES.mkdir(exist_ok=True)
SETTINGS=HOME/'settings.json'
FRONTEND=HERE.parent/'frontend'
TOKEN=os.environ.get('REVOICE_TOKEN') or secrets.token_urlsafe(32)
BLOCK=6144
IO_BLOCK=480

class SampleFIFO:
 def __init__(self):self.chunks=deque();self.offset=0;self.size=0
 def append(self,a):self.chunks.append(a);self.size+=len(a)
 def clear(self):self.chunks.clear();self.offset=0;self.size=0
 def take(self,frames):
  y=np.zeros(frames,dtype=np.float32);written=0
  while self.chunks and written<frames:
   a=self.chunks[0];n=min(frames-written,len(a)-self.offset);y[written:written+n]=a[self.offset:self.offset+n];written+=n;self.offset+=n;self.size-=n
   if self.offset==len(a):self.chunks.popleft();self.offset=0
  return y,written

def apply_gain(samples,gain):
 # Preserve waveform shape when gain would otherwise flatten loud samples.
 peak=float(np.max(np.abs(samples)))
 samples*=min(gain,.95/max(peak,1e-9))
 return samples
DEFAULT={'voice':None,'input':None,'output':None,'hear':False,'muted':False,'pitch':0,'formant':0.,'index_rate':0.,'input_gain':1.,'gain':1.,'profile':'live','enabled':True,'noise_reduction':True,'paused':False}
try:settings=DEFAULT|json.loads(SETTINGS.read_text())
except (OSError,ValueError,TypeError):settings=DEFAULT.copy()
state={'phase':'Stopped','error':None,'input_level':0.,'output_level':0.,'processing_ms':0.,'drops':0,'empty_blocks':0,'monitor_empty_blocks':0,'recording':False,'recording_seconds':0.,'recording_file':None}
recording_blob=None
lock=threading.RLock();device_lock=threading.RLock();mutation_lock=threading.RLock();cached_worker=None;cached_key=None;refresh_pending=threading.Event();engine_thread=None;stop=threading.Event();shutdown=threading.Event();server=None

def discard_recording(identity=None):
 global recording_blob
 with lock:
  if identity is not None and identity!=state['recording_file']:return
  recording_blob=None;state['recording_file']=None

def publish_recording(samples):
 global recording_blob
 buffer=io.BytesIO();sf.write(buffer,samples,48000,format='WAV',subtype='PCM_16')
 with lock:
  recording_blob=buffer.getvalue();state['recording_file']=str(uuid.uuid4())


def save():
 temp=SETTINGS.with_suffix('.tmp');temp.write_text(json.dumps(settings));temp.replace(SETTINGS)

def voices():
 result=[]
 for d in VOICES.iterdir():
  try:
   v=json.loads((d/'voice.json').read_text())
   if v.get('engine')=='beatrice':result.append(v)
  except (OSError,ValueError):pass
 return sorted(result,key=lambda v:v['name'].lower())

def devices():
 with device_lock:return [{'id':i,'name':d['name'],'input':d['max_input_channels'],'output':d['max_output_channels'],'rate':d['default_samplerate']} for i,d in enumerate(sd.query_devices())]

def status():
 ds=devices()
 with lock:return state|settings|{'voices':voices(),'devices':ds,'driver_installed':any(d['name'] in ('Revoice Microphone','BlackHole 2ch') for d in ds),'engine':'Beatrice','virtual_microphone':virtual_name(ds),'engine_installed':resolve_library() is not None}









MODEL_FILES=('phone_extractor.bin','pitch_estimator.bin','waveform_generator.bin','embedding_setter.bin','speaker_embeddings.bin')
core=None

def virtual_name(ds=None):
 if ds is None:ds=devices()
 return next((name for name in ('Revoice Microphone','BlackHole 2ch') if any(d['name']==name and d['output'] for d in ds)), 'Revoice Microphone')

def close_audio_stream(monitor):
 if monitor is None:return
 for action in ('stop','close'):
  try:getattr(monitor,action)()
  except Exception:logging.exception('Audio stream cleanup failed')

def open_monitor(device,callback):
 monitor=None;noise=None
 try:
  monitor=sd.OutputStream(device=device['id'],samplerate=48000,channels=min(2,device['output']),blocksize=480,dtype='float32',latency=.003,callback=callback)
  monitor.start()
  state.pop('notice',None)
  return monitor
 except Exception:
  close_audio_stream(monitor)
  state['notice']='Listening output unavailable. Your virtual microphone is still connected. Reconnect or choose another output.'
  logging.exception('Listening output unavailable')
  return None

def get_core():
 global core
 if core is None:
  os.environ['BEATRICE_CUSTOM_MODELS_DIR']=str(VOICES)
  import beatrice_core
  core=beatrice_core
 return core

def validate_model(folder):
 for name in MODEL_FILES:
  if not (folder/name).is_file() or not 4<=(folder/name).stat().st_size<=64*1024**2:raise ValueError('Voice ZIP is missing a valid '+name+'.')
 # Parameter readers validate headers and complete payloads before inference.
 c=get_core()
 for stem,label in [('phone_extractor','PhoneExtractor'),('pitch_estimator','PitchEstimator'),('waveform_generator','WaveformGenerator'),('embedding_setter','EmbeddingSetter')]:
  ptr=getattr(c.lib,'Beatrice20rc0_Create'+label)()
  if not ptr:raise ValueError('Cannot allocate voice validator.')
  try:
   result=getattr(c.lib,'Beatrice20rc0_Read'+label+'Parameters')(ptr,str(folder/(stem+'.bin')).encode())
   if result!=0:raise ValueError('Invalid '+stem+' parameters.')
  finally:getattr(c.lib,'Beatrice20rc0_Destroy'+label)(ptr)
 import ctypes
 count=ctypes.c_int();result=c.lib.Beatrice20rc0_ReadNSpeakers(str(folder/'speaker_embeddings.bin').encode(),ctypes.byref(count))
 if result!=0 or not 1<=count.value<=256:raise ValueError('Invalid speaker embeddings.')
 return count.value

def import_voice(name,data):
 import stat
 import_name=name
 if not isinstance(name,str) or not name.strip() or len(name.strip())>80:raise ValueError('Enter a voice name of 1–80 characters.')
 if len(data)>128*1024**2:raise ValueError('Use a Beatrice voice ZIP under 128 MB.')
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  items=z.infolist()
  if len(items)>100 or sum(i.file_size for i in items)>256*1024**2:raise ValueError('Voice ZIP is too large.')
  for i in items:
   p=pathlib.PurePosixPath(i.filename)
   if p.is_absolute() or '..' in p.parts or '\\' in i.filename or stat.S_ISLNK(i.external_attr>>16):raise ValueError('ZIP contains unsafe file paths.')
  found={name:[i for i in items if pathlib.PurePosixPath(i.filename).name==name and '__MACOSX' not in i.filename] for name in MODEL_FILES}
  if any(len(v)!=1 for v in found.values()):raise ValueError('Choose a Beatrice export ZIP containing its five .bin files. RVC models are incompatible.')
  identity=uuid.uuid4().hex;dest=VOICES/identity;dest.mkdir()
  try:
   for name,entries in found.items():
    with z.open(entries[0]) as src,(dest/name).open('wb') as out:shutil.copyfileobj(src,out)
   count=validate_model(dest)
   stop_audio();v={'id':identity,'name':import_name.strip(), 'engine':'beatrice','version':'2.0.0-rc.3','has_index':False,'speakers':count,'added':time.time()}
   (dest/'voice.json').write_text(json.dumps(v));settings['voice']=identity;discard_recording();save();return v
  except Exception:shutil.rmtree(dest);raise

def run_audio():
 streams=[];mq=queue.Queue(2);recorded=[];record_started=None;last_hear=None;monitor=None;noise=None
 try:
  state.update(phase='Loading',error=None,input_level=0.,output_level=0.)
  from noise_reduction import NoiseReducer
  resampler=VoiceResampler();was_converting=False
  if settings['noise_reduction']:noise=NoiseReducer()
  c=get_core();identity=settings['voice']
  if identity not in {v['id'] for v in voices()}:raise ValueError('Add and select a Beatrice voice first.')
  c.load_vst3_model('custom:'+identity)
  if not c.Config.dsp_ready or c.Config.current_model!='custom:'+identity:raise ValueError('This voice could not be loaded.')
  c.Config.hear_yourself=False;c.Config.volume=1.;c.Config.gate_threshold=0.;c.update_formant_shift(settings['formant'])
  ds=devices();mic=next((d for d in ds if d['name']==settings['input'] and d['input']),None);target=next((d for d in ds if d['name']==virtual_name(ds) and d['output']),None)
  if mic is None or any(t in mic['name'].lower() for t in ('blackhole','revoice','virtual')):raise ValueError('Choose a physical microphone.')
  if target is None:raise ValueError('Install Revoice Microphone to connect your voice to other apps.')
  def callback(a,out,frames,t,event):
   nonlocal was_converting
   converting=settings['enabled'] and not settings['muted']
   if converting!=was_converting:resampler.reset();was_converting=converting
   out.fill(0)
   if event:state['drops']+=1
   if settings['muted']:state['input_level']=state['output_level']=0.;y=np.zeros(frames,dtype=np.float32)
   else:
    x=a[:,0].copy()
    if noise:x=noise.process(x)
    apply_gain(x,settings['input_gain']);state['input_level']=float(np.sqrt(np.mean(x*x)))
    if settings['enabled']:
     c.Config.muted=False;c.Config.bypass=False;c.Config.pitch_shift=settings['pitch']
     if c.Config.formant_shift!=settings['formant']:c.Config.formant_shift=settings['formant'];c.update_formant_shift(settings['formant'])
     y24=np.zeros((240,1),dtype=np.float32);x16=resampler.downsample(x)
     started=time.perf_counter();c.dsp_callback(x16[:,None],y24,160,t,event,output_sample_rate=24000);state['processing_ms']=(time.perf_counter()-started)*1000
     y=resampler.upsample(y24[:,0])
    else:y=x
    apply_gain(y,settings['gain'] if settings['enabled'] else 1.);state['output_level']=float(np.sqrt(np.mean(y*y)))
   out[:]=y[:,None]
   if settings['hear']:
    try:mq.put_nowait(y.copy())
    except queue.Full:
     try:mq.get_nowait();mq.put_nowait(y.copy())
     except (queue.Empty,queue.Full):pass
   if state['recording'] and len(recorded)<2000:recorded.append(y.copy())
  stream=sd.Stream(device=(mic['id'],target['id']),samplerate=48000,channels=(1,2),blocksize=480,dtype='float32',latency=.003,callback=callback)
  stream.start();streams.append(stream);state['phase']='Live';print(json.dumps({'audio_live':True}),flush=True)
  while not stop.wait(.03):
   if not stream.active:raise RuntimeError('Microphone disconnected. Choose a connected device.')
   desired=settings['output'] if settings['hear'] else None
   if desired!=last_hear:
    if monitor:close_audio_stream(monitor);monitor=None
    while not mq.empty():
     try:mq.get_nowait()
     except queue.Empty:break
    last_hear=desired
    if desired:
     d=next((d for d in devices() if d['name']==desired and d['output']),None)
     if not d:state['notice']='Listening output disconnected. Choose headphones.';continue
     def monitor_cb(out,frames,t,event):
      out.fill(0)
      if not settings['hear'] or settings['muted']:return
      try:y=mq.get_nowait()
      except queue.Empty:state['monitor_empty_blocks']+=1;return
      out[:]=y[:,None]
     monitor=open_monitor(d,monitor_cb)
   if monitor and not monitor.active:
    close_audio_stream(monitor);monitor=None
    state['notice']='Listening output disconnected. Your virtual microphone is still connected. Reconnect or choose another output.'
   if state['recording'] and record_started is None:recorded.clear();record_started=time.monotonic()
   if record_started is not None:
    state['recording_seconds']=min(20.,time.monotonic()-record_started)
    if not state['recording'] or state['recording_seconds']>=20:
     state['recording']=False;record_started=None;publish_recording(np.concatenate(recorded) if recorded else np.zeros(1));recorded.clear()
 except Exception as e:state['error']=str(e);logging.exception('Beatrice audio failed')
 finally:
  close_audio_stream(monitor)
  for s in streams:close_audio_stream(s)
  if noise:noise.close()
  if recorded:publish_recording(np.concatenate(recorded))
  state.update(phase='Stopped',recording=False,input_level=0.,output_level=0.)
  print(json.dumps({'audio_live':False}),flush=True)

def start_audio():
 global engine_thread
 if engine_thread and engine_thread.is_alive():return
 stop.clear();engine_thread=threading.Thread(target=run_audio,daemon=True);engine_thread.start()

def stop_audio():
 stop.set()
 if engine_thread:engine_thread.join(8)
 if engine_thread and engine_thread.is_alive():raise RuntimeError('Engine is still stopping. Please wait.')

def control(data):
 restart=state['phase'] in ('Live','Loading') and any(k in data and data[k]!=settings[k] for k in ('input','voice','noise_reduction'))
 action=data.get('action')
 if action=='refresh':
  restart=bool(settings['voice']) and not settings['paused'];stop_audio()
  with device_lock:
   if sd._initialized:sd._terminate()
   sd._initialize()
  state.pop('notice',None);state['error']=None
 elif action=='stop':
  stop_audio();settings['paused']=True
 elif action=='record':
  if state['phase']!='Live':raise ValueError('Connect your voice before recording.')
  state['recording']=not state['recording']
  if state['recording']:discard_recording();state['recording_seconds']=0.
 elif action=='discard-recording':discard_recording(data.get('id'))
 elif action=='rename':
  identity=data.get('id');name=data.get('name')
  voice=next((v for v in voices() if v['id']==identity),None)
  if voice is None:raise ValueError('Voice was not found.')
  if not isinstance(name,str):raise ValueError('Enter a voice name.')
  name=name.strip()
  if not 1<=len(name)<=80 or any(ord(c)<32 or ord(c)==127 for c in name):raise ValueError('Use a voice name between 1 and 80 characters.')
  voice['name']=name;path=VOICES/identity/'voice.json';temp=path.with_suffix('.tmp')
  temp.write_text(json.dumps(voice));temp.replace(path)
 elif action=='delete':
  identity=data.get('id')
  if identity not in {v['id'] for v in voices()}:raise ValueError('Voice was not found.')
  if settings['voice']==identity:stop_audio();settings['voice']=None;discard_recording()
  shutil.rmtree(VOICES/identity)
 elif action=='quit':shutdown.set()
 if restart:stop_audio()
 for key in ('input','output','voice'):
  if key in data:
   if key=='voice' and data[key] not in {v['id'] for v in voices()}:raise ValueError('Choose a Beatrice voice.')
   settings[key]=data[key]
 for key in ('hear','muted','enabled','noise_reduction'):
  if key in data:
   if not isinstance(data[key],bool):raise ValueError('Invalid switch value.')
   settings[key]=data[key]
 for key,low,high in [('input_gain',.5,6),('gain',.5,6),('pitch',-12,12),('formant',-2,2)]:
  if key in data:
   v=float(data[key])
   if not np.isfinite(v) or not low<=v<=high:raise ValueError('Setting is out of range.')
   settings[key]=v
 save()
 if action=='start':settings['paused']=False;save()
 if restart or action=='start':start_audio()

class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def reply(self,data,kind='application/json',code=200):
  if kind=='application/json':data=json.dumps(data).encode()
  self.send_response(code);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data)
 def authorized(self):
  host=self.headers.get('Host','');origin=self.headers.get('Origin')
  return host==f'127.0.0.1:{server.server_port}' and (origin is None or origin==f'http://{host}') and secrets.compare_digest(self.headers.get('X-Revoice-Token',''),TOKEN)
 def do_GET(self):
  path=urlparse(self.path).path
  if path in ('/','/app.css','/app.js'):
   f=FRONTEND/({'/':'index.html','/app.css':'app.css','/app.js':'app.js'}[path]);kind={'/':'text/html; charset=utf-8','/app.css':'text/css','/app.js':'text/javascript'}[path]
   if f.exists():self.reply(f.read_bytes(),kind);return
  if path=='/avatars/waves.js':
   self.reply((FRONTEND/'avatars/waves.js').read_bytes(),'text/javascript; charset=utf-8');return
  if path in ('/avatars/friend.svg','/avatars/studio.svg','/avatars/narrator.svg'):
   self.reply((FRONTEND/path.lstrip('/')).read_bytes(),'image/svg+xml');return
  if path=='/health':self.reply({'ok':True});return
  if not self.authorized():self.reply({'error':'Unauthorized'},code=403);return
  if path=='/status':self.reply(status())
  elif path=='/recording':
   identity=parse_qs(urlparse(self.path).query).get('id',[None])[0]
   with lock:blob=recording_blob if identity is None or identity==state['recording_file'] else None
   if blob is not None:self.reply(blob,'audio/wav')
   else:self.reply({'error':'This temporary recording is no longer available.'},code=404)
  else:self.reply({'error':'Not found'},code=404)
 def do_POST(self):
  if not self.authorized():self.reply({'error':'Unauthorized'},code=403);return
  try:
   length=int(self.headers.get('Content-Length',0))
   limit=128*1024**2 if urlparse(self.path).path=='/import' else 64*1024
   if length<0 or length>limit:raise ValueError('Use a Beatrice voice ZIP under 128 MB.' if urlparse(self.path).path=='/import' else 'Request too large.')
   self.connection.settimeout(120);body=self.rfile.read(length)
   if len(body)!=length:raise ValueError('Incomplete upload.')
   if urlparse(self.path).path=='/import':
    name=parse_qs(urlparse(self.path).query).get('name',[''])[0]
    with mutation_lock:result=import_voice(name,body)
   elif urlparse(self.path).path=='/control':
    with mutation_lock:control(json.loads(body))
    result={'ok':True}
   else:raise ValueError('Unknown action.')
   self.reply(result)
  except Exception as e:self.reply({'error':str(e)},code=400)

def main():
 global server
 logging.basicConfig(filename=str(HOME/'engine.log'),level=logging.INFO)
 settings['profile']='live'
 ds=devices()
 physical=[d for d in ds if not any(n in d['name'].lower() for n in ['revoice','blackhole','virtual'])]
 if not settings['input']:settings['input']=next((d['name'] for d in physical if 'MacBook' in d['name'] and d['input']),next((d['name'] for d in physical if d['input']),''))
 if not settings['output']:settings['output']=next((d['name'] for d in physical if d['output'] and 'EarPods' in d['name']),next((d['name'] for d in physical if d['output'] and 'MacBook' in d['name']),next((d['name'] for d in physical if d['output']),'')))
 save();server=ThreadingHTTPServer(('127.0.0.1',int(os.environ.get('REVOICE_PORT','0'))),Handler)
 threading.Thread(target=server.serve_forever,daemon=True).start()
 session=HOME/'session.json'
 fd=os.open(session,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
 with os.fdopen(fd,'w') as f:json.dump({'port':server.server_port,'token':TOKEN,'pid':os.getpid()},f)
 print(json.dumps({'port':server.server_port,'token':TOKEN}),flush=True)
 signal.signal(signal.SIGTERM,lambda *_:shutdown.set());signal.signal(signal.SIGINT,lambda *_:shutdown.set())
 while not shutdown.wait(.2):
  if refresh_pending.is_set() and state['phase'] not in ('Loading','Stopping'):
   refresh_pending.clear()
   try:
    with mutation_lock:control({'action':'refresh'})
   except Exception as e:state['error']=str(e);logging.exception('Device refresh failed')
 stop_audio();discard_recording()
 
 server.shutdown();server.server_close()
 try:
  if json.loads(session.read_text()).get('pid')==os.getpid():session.unlink()
 except (OSError,ValueError):pass
if __name__=='__main__':mp.freeze_support();main()
