import json,tempfile,time,wave,datetime,unittest
from pathlib import Path
from native_host import Journal
from auto_journals import prepare_journal,live_journals

class AutoTests(unittest.TestCase):
 def message(self,tab=1,meeting='a'*64):
  return {'type':'auto_sample','tab':tab,'client':'client-12345','page_id':'document-12345',
          'meeting_id':meeting,'title':'Тест DION','at':time.time()*1000,'state':'observing',
          'speakers':['Анна'],'profile':'{}','calibrated':True}
 def test_creates_journals_without_recorder_and_isolates_tabs(self):
  with tempfile.TemporaryDirectory() as tmp:
   j=Journal({'journals':tmp})
   a=j.handle(self.message());b=j.handle(self.message(2,'b'*64))
   self.assertNotEqual(a['path'],b['path'])
   self.assertTrue(Path(a['path'],'events.jsonl').exists())
   self.assertEqual(json.loads(Path(b['path'],'events.jsonl').read_text('utf-8'))['tab'],2)
 def test_reconnect_appends_same_document_and_end(self):
  with tempfile.TemporaryDirectory() as tmp:
   cfg={'journals':tmp};a=Journal(cfg).handle(self.message())
   j=Journal(cfg);b=j.handle(self.message())
   self.assertEqual(a['path'],b['path'])
   self.assertEqual(len(Path(a['path'],'events.jsonl').read_text('utf-8').splitlines()),2)
   j.handle({**self.message(),'type':'auto_end'})
   self.assertIn('ended_at',json.loads(Path(a['path'],'meta.json').read_text('utf-8')))
 def test_invalid_or_stale_sample_does_not_create_journal(self):
  with tempfile.TemporaryDirectory() as tmp:
   j=Journal({'journals':tmp})
   for changes in ({'at':0},{'meeting_id':'../bad'},{'page_id':'../bad'},{'speakers':['x\n']}):
    with self.subTest(changes=changes),self.assertRaises(ValueError):
     j.handle({**self.message(),**changes})
   self.assertEqual(list(Path(tmp).iterdir()),[])
 def test_empty_speaker_list_still_creates_meeting_journal(self):
  with tempfile.TemporaryDirectory() as tmp:
   out=Journal({'journals':tmp}).handle({**self.message(),'speakers':[]})
   self.assertTrue(Path(out['path'],'events.jsonl').exists())
 def fixture(self,p):
  session=p/'recording';session.mkdir()
  origin=time.monotonic()-2
  (session/'recording_clock.json').write_text(json.dumps({'remote_monotonic':origin}))
  (session/'meta.json').write_text(json.dumps({'created':datetime.datetime.now().isoformat()}))
  with wave.open(str(session/'remote.wav'),'wb') as w:
   w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes(b'\0'*80000)
  return session
 def test_import_only_one_candidate_and_preserve_old_journal(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);session=self.fixture(p);root=p/'journals'
   Journal({'journals':str(root)}).handle(self.message())
   result=prepare_journal(session,root)
   self.assertEqual(result['state'],'imported')
   events=[json.loads(x) for x in (session/'browser-speakers.jsonl').read_text('utf-8').splitlines()]
   self.assertTrue(events[0]['seconds']>=0)
   self.assertEqual(prepare_journal(session,root)['state'],'existing_session_journal')
 def test_multiple_meetings_require_selection(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);session=self.fixture(p);root=p/'journals';j=Journal({'journals':str(root)})
   a=j.handle(self.message());j.handle(self.message(2,'b'*64))
   result=prepare_journal(session,root)
   self.assertEqual(result['state'],'multiple_meetings_select_required')
   self.assertFalse((session/'browser-speakers.jsonl').exists())
   self.assertEqual(prepare_journal(session,root,a['path'])['state'],'imported')
 def test_journal_outside_recording_or_from_other_boot_is_ignored(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);session=self.fixture(p);root=p/'journals'
   a=Journal({'journals':str(root)}).handle(self.message())
   meta=Path(a['path'],'meta.json');d=json.loads(meta.read_text('utf-8'));d['boot_epoch']-=10000
   meta.write_text(json.dumps(d))
   self.assertEqual(prepare_journal(session,root)['state'],'no_matching_journal')
 def test_no_recorder_clock_is_not_an_error_for_host(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);root=p/'journals';session=p/'session';session.mkdir()
   Journal({'journals':str(root)}).handle(self.message())
   self.assertEqual(prepare_journal(session,root)['state'],'missing_recording_clock')

 def test_live_status_requires_recent_unclosed_journal(self):
  with tempfile.TemporaryDirectory() as tmp:
   j=Journal({'journals':tmp})
   self.assertEqual(live_journals(tmp)['count'],0)
   j.handle(self.message())
   self.assertEqual(live_journals(tmp)['count'],1)
   j.handle({**self.message(),'type':'auto_end'})
   self.assertEqual(live_journals(tmp)['count'],0)
if __name__=='__main__':unittest.main()
