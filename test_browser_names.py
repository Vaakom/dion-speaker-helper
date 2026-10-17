import json,tempfile,unittest
from pathlib import Path
from speaker_names import apply_names,UNKNOWN
class DirectTests(unittest.TestCase):
 def run_case(self,rows,samples=None,clock=None,broken=False):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)
   if samples is not None:(p/'browser-speakers.jsonl').write_text('\n'.join(json.dumps(s) for s in samples),'utf-8')
   if broken:(p/'browser-speakers.jsonl').write_text('{}','utf-8')
   if clock:(p/'recording_clock.json').write_text(json.dumps(clock),'utf-8')
   result=apply_names(rows,p)
   return result,json.loads((p/'speaker-name-report.json').read_text('utf-8'))
 def samples(self):
  return [{'seconds':i*.5,'state':'observing','speakers':['Анна'],'calibrated':True} for i in range(17)]
 def row(self,a=2,b=2.3,label='remote'):
  return {'start':a,'end':b,'speaker':label,'text':'слово'}
 def test_no_voice_evidence_required(self):
  out,report=self.run_case([self.row()],self.samples());self.assertEqual(out[0]['speaker'],'Анна');self.assertEqual(report['method'],'browser_only')
 def test_transition_is_questioned(self):
  s=self.samples()
  for x in s[8:]:x['speakers']=['Борис']
  out,_=self.run_case([self.row(3.7,4.2)],s)
  self.assertTrue(out[0]['speaker'].startswith('? '))
  self.assertIn('speaker_change_inside_word',out[0]['speaker_evidence']['reasons'])
 def test_both_names_are_questioned(self):
  s=self.samples()
  for x in s:x['speakers']=['Анна','Борис']
  out,_=self.run_case([self.row()],s);self.assertEqual(out[0]['speaker'],'? Анна')
 def test_missing_and_malformed_journals(self):
  for options in ({},{'broken':True}):
   out,_=self.run_case([self.row()],**options);self.assertEqual(out[0]['speaker'],UNKNOWN)
 def test_silence_gap_and_no_carry_after_end(self):
  s=self.samples()
  for x in s[6:10]:x['speakers']=[]
  out,_=self.run_case([self.row(3.3,3.5),self.row(9,9.3)],s)
  self.assertEqual([r['speaker'] for r in out],[UNKNOWN,UNKNOWN])
  out,_=self.run_case([self.row(2,2.3)],[s[0],s[-1]])
  self.assertEqual(out[0]['speaker'],UNKNOWN)
 def test_partial_coverage_and_unverified(self):
  out,_=self.run_case([self.row(-.1,.2)],self.samples())
  self.assertEqual(out[0]['speaker'],'? Анна')
  s=self.samples()
  for x in s:x['calibrated']=False
  out,_=self.run_case([self.row()],s);self.assertEqual(out[0]['speaker'],'? Анна')
 def test_microphone_uses_browser_name_and_clock(self):
  out,_=self.run_case([self.row(label='Я')],self.samples(),{'microphone_monotonic':10.3,'remote_monotonic':10})
  self.assertEqual(out[0]['speaker'],'Анна');self.assertAlmostEqual(out[0]['start'],2.3)
 def test_unknown_voice_label_can_receive_browser_name(self):
  out,_=self.run_case([self.row(label='Неопределённый спикер')],self.samples())
  self.assertEqual(out[0]['speaker'],'Анна')
if __name__=='__main__':unittest.main()
