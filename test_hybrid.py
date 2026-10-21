import json,tempfile,unittest,os
from pathlib import Path
from speaker_names_voice import apply_names

class HybridTests(unittest.TestCase):
    def fixture(self):
        rows=[]
        for start in (0,9):
            for i in range(12):
                a=start+1+i*.4
                rows.append({'start':a,'end':a+.3,'speaker':'Спикер 1','text':'слово',
                    'speaker_evidence':{'method':'local_voice_clustering','status':'assigned','coverage':1,'overlap':0}})
        samples=[]
        for start in (0,9):
            samples += [{'seconds':start+i*.5,'profile':json.dumps({'algorithm':'browser_voice_agreement_v2'}),'state':'observing','calibrated':True,'speakers':['Анна']} for i in range(15)]
        return rows,samples,[{'start':0,'end':20,'speaker':0}]
    def run_case(self,rows,samples,turns):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp,'browser-speakers.jsonl').write_text('\n'.join(json.dumps(s) for s in samples),'utf-8')
            result=apply_names(rows,tmp,turns)
            report=json.loads(Path(tmp,'speaker-name-report.json').read_text('utf-8'))
            return result,report
    def test_stable_agreement_and_report(self):
        r,s,t=self.fixture();out,report=self.run_case(r,s,t)
        self.assertTrue(all(x['speaker']=='Анна' for x in out))
        self.assertEqual(report['named_words'],24)
        self.assertEqual(out[0]['speaker_evidence']['previous_label'],'Спикер 1')
    def test_legacy_profile_cannot_enable_new_algorithm(self):
        r,s,t=self.fixture()
        for item in s:item['profile']=json.dumps({'calibrated':True})
        out,_=self.run_case(r,s,t);self.assertEqual(out,r)
    def test_real_annotation_keeps_overlaps_uncertain(self):
        import sys
        skill=Path(os.environ.get('DION_SECRETARY_SKILL',str(Path(__file__).resolve().parents[2]/'skills/dion-secretary')))
        if not (skill/'scripts/diarization.py').is_file():
            self.skipTest('Optional recorder integration: set DION_SECRETARY_SKILL')
        sys.path.insert(0,str(skill/'scripts'))
        from diarization import annotate
        r,s,t=self.fixture()
        for row in r:row['speaker']='remote';row.pop('speaker_evidence')
        turns=t+[{'start':1,'end':1.3,'speaker':1}]
        annotated=annotate(r,turns)
        out,_=self.run_case(annotated,s,turns)
        self.assertEqual(out[0]['speaker'],'Неопределённый спикер')
        self.assertEqual(out[1]['speaker'],'Анна')
    def test_one_utterance_is_insufficient(self):
        r,s,t=self.fixture();out,_=self.run_case(r[:12],s[:15],t)
        self.assertEqual(out,r[:12])
    def test_known_overlap_does_not_get_name(self):
        r,s,t=self.fixture();t.append({'start':r[0]['start'],'end':r[0]['end'],'speaker':1})
        out,_=self.run_case(r,s,t)
        self.assertEqual(out[0],r[0]);self.assertEqual(out[1]['speaker'],'Анна')
    def test_uncertain_voice_is_never_repaired(self):
        r,s,t=self.fixture();r[0]['speaker']='Неопределённый спикер'
        r[0]['speaker_evidence']['status']='uncertain'
        out,_=self.run_case(r,s,t);self.assertEqual(out[0],r[0])
    def test_own_microphone_overlap(self):
        r,s,t=self.fixture()
        own={'start':0,'end':20,'speaker':'Я','text':'я'}
        out,report=self.run_case(r+[own],s,t)
        self.assertEqual(out,r+[own]);self.assertGreater(report['rejections']['own_microphone_overlap'],0)
    def test_conflicting_browser_names(self):
        r,s,t=self.fixture()
        for item in s[15:]:item['speakers']=['Борис']
        out,_=self.run_case(r,s,t);self.assertEqual(out,r)
    def test_unconfirmed_missing_voice_and_profile_change(self):
        for variant in ('unconfirmed','missing','profile'):
            with self.subTest(variant=variant):
                r,s,t=self.fixture()
                if variant=='unconfirmed':
                    for item in s:item['calibrated']=False
                if variant=='missing':t=None
                if variant=='profile':s[-1]['profile']='other'
                out,_=self.run_case(r,s,t);self.assertEqual(out,r)
    def test_gaps_and_both_browser_speakers(self):
        r,s,t=self.fixture()
        extra={**r[0],'start':7.5,'end':7.8}
        out,_=self.run_case(r+[extra],s,t);self.assertEqual(out[-1],extra)
        for item in s:item['speakers']=['Анна','Борис']
        out,_=self.run_case(r,s,t);self.assertEqual(out,r)
    def test_duplicate_words_do_not_manufacture_support(self):
        r,s,t=self.fixture();r=[r[0]]*30+[r[12]]*30
        out,_=self.run_case(r,s,t);self.assertEqual(out,r)
    def test_same_name_on_two_voice_clusters_is_ambiguous(self):
        r,s,t=self.fixture()
        second=[{**x,'start':x['start']+22,'end':x['end']+22,'speaker':'Спикер 2'} for x in r]
        samples=s+[{**x,'seconds':x['seconds']+22} for x in s]
        turns=t+[{'start':22,'end':42,'speaker':1}]
        out,_=self.run_case(r+second,samples,turns);self.assertEqual(out,r+second)

if __name__=='__main__':unittest.main()
