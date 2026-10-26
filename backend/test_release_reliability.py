import os,tempfile,unittest,threading,json,http.client
from unittest.mock import patch,MagicMock
from pathlib import Path

home=tempfile.TemporaryDirectory();os.environ['REVOICE_HOME']=home.name
import app

class ReliabilityTest(unittest.TestCase):
 def test_one_device_snapshot(self):
  ds=[{'id':1,'name':'Revoice Microphone','input':2,'output':2,'rate':48000}]
  with patch.object(app,'devices',return_value=ds) as query:
   s=app.status();query.assert_called_once();self.assertEqual(s['virtual_microphone'],'Revoice Microphone');self.assertTrue(s['driver_installed'])
 def test_failed_monitor_does_not_stop_virtual_audio(self):
  app.state['phase']='Live';app.state['error']=None;app.stop.clear()
  monitor=MagicMock();monitor.start.side_effect=RuntimeError('output disconnected')
  with patch.object(app.sd,'OutputStream',return_value=monitor),patch.object(app.logging,'exception'):
   self.assertIsNone(app.open_monitor({'id':1,'output':2},lambda *args:None))
  self.assertEqual(app.state['phase'],'Live');self.assertIsNone(app.state['error']);self.assertFalse(app.stop.is_set());monitor.close.assert_called_once();self.assertIn('still connected',app.state['notice'])
 def test_monitor_cleanup_attempts_close_after_stop_failure(self):
  monitor=MagicMock();monitor.stop.side_effect=RuntimeError('disconnected')
  with patch.object(app.logging,'exception'):app.close_audio_stream(monitor)
  monitor.close.assert_called_once()
 def test_successful_monitor_clears_notice(self):
  app.state['notice']='old output issue';monitor=MagicMock()
  with patch.object(app.sd,'OutputStream',return_value=monitor):self.assertIs(app.open_monitor({'id':1,'output':2},lambda *args:None),monitor)
  self.assertNotIn('notice',app.state)
 def test_natural_voice_does_not_use_conversion_volume(self):
  import numpy as np
  app.settings.update(voice='saved-voice',input='Physical Mic',noise_reduction=False,enabled=False,muted=False,hear=False,input_gain=1.,gain=2.5)
  ds=[{'id':0,'name':'Physical Mic','input':1,'output':0,'rate':48000},{'id':1,'name':'Revoice Microphone','input':2,'output':2,'rate':48000}]
  core=MagicMock();core.Config.dsp_ready=True;core.Config.current_model='custom:saved-voice'
  converted=[]
  def stream_factory(**kwargs):
   stream=MagicMock();stream.active=True
   def begin():
    out=np.zeros((480,2),dtype=np.float32);kwargs['callback'](np.full((480,1),.02,dtype=np.float32),out,480,None,None);converted.append(out.copy());app.stop.set()
   stream.start.side_effect=begin;return stream
  app.stop.clear()
  with patch.object(app,'get_core',return_value=core),patch.object(app,'voices',return_value=[{'id':'saved-voice'}]),patch.object(app,'devices',return_value=ds),patch.object(app.sd,'Stream',side_effect=stream_factory):app.run_audio()
  np.testing.assert_allclose(converted[0],.02,rtol=0,atol=1e-8)
  self.assertEqual(app.state['phase'],'Stopped')
 def test_device_refresh_keeps_released_microphone_closed(self):
  app.settings['voice']='saved-voice';app.settings['paused']=True
  with patch.object(app,'stop_audio'),patch.object(app,'start_audio') as start,patch.object(app.sd,'_terminate'),patch.object(app.sd,'_initialize'):
   app.control({'action':'refresh'});start.assert_not_called()
  self.assertTrue(app.settings['paused'])
 def test_limits_checked_before_reading_request_body(self):
  server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler);app.server=server
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   for route,length in [('/import',128*1024**2+1),('/control',65537)]:
    connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=2)
    connection.request('POST',route,body=b'',headers={'X-Revoice-Token':app.TOKEN,'Content-Length':str(length)})
    response=connection.getresponse();self.assertEqual(response.status,400);self.assertIn('error',json.loads(response.read()));connection.close()
  finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()
