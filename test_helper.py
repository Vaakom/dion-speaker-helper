import io,json,struct,tempfile,time,unittest
from pathlib import Path
from native_host import read_message,write_message,Journal
from speaker_names_voice import apply_names
class Tests(unittest.TestCase):
    def test_unicode_protocol(self):
        b=io.BytesIO();write_message(b,{'name':'Иван'});b.seek(0)
        self.assertEqual(read_message(b),{'name':'Иван'})
        with self.assertRaises(ValueError):read_message(io.BytesIO(struct.pack('<I',70000)))
        with self.assertRaises(ValueError):read_message(io.BytesIO(b'xx'))
    def test_attribution_overlap_gap_unverified_and_me(self):
        with tempfile.TemporaryDirectory() as temp:
            samples=[{'seconds':i*.5,'speakers':['Иван'],'state':'observing','calibrated':True,'profile':'a'} for i in range(5)]
            samples += [{'seconds':3,'speakers':['Иван','Анна'],'state':'observing','calibrated':True,'profile':'a'},
                        {'seconds':3.5,'speakers':['Иван','Анна'],'state':'observing','calibrated':True,'profile':'a'},
                        {'seconds':4,'speakers':['Анна'],'state':'observing','calibrated':False,'profile':'a'},
                        {'seconds':4.5,'speakers':['Анна'],'state':'observing','calibrated':False,'profile':'a'}]
            p=Path(temp)/'browser-speakers.jsonl';p.write_text('\n'.join(json.dumps(x) for x in samples),'utf-8')
            rows=[{'start':a,'end':b,'speaker':s,'text':'текст'} for a,b,s in
                  [(0.2,.8,'Спикер 1'),(2.1,2.8,'Спикер 1'),(3.1,3.4,'Спикер 2'),(4.1,4.4,'Спикер 2'),(.2,.8,'Я')]]
            self.assertEqual(apply_names(rows,temp),rows)  # No voice evidence: no names.
            p.write_text('{bad','utf-8');self.assertEqual(apply_names(rows,temp),rows)
            p.write_text('{}','utf-8');self.assertEqual(apply_names(rows,temp),rows)
    def test_binding_session_bounds_stale_and_switch(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);session=root/'sessions'/'one';session.mkdir(parents=True)
            active=root/'active.json'
            active.write_text(json.dumps({'session':str(session)}))
            (session/'status.json').write_text(json.dumps({'state':'recording'}))
            (session/'recording_clock.json').write_text(json.dumps({'remote_monotonic':time.monotonic()-1}))
            j=Journal({'active':str(active),'sessions':str(root/'sessions')})
            j.handle({'type':'bind','tab':2})
            m={'type':'sample','tab':2,'at':time.time()*1000,'state':'observing','speakers':['Иван'],'calibrated':True,'profile':'a'}
            self.assertTrue(j.handle(m)['ok'])
            with self.assertRaises(ValueError):j.handle({**m,'tab':3})
            with self.assertRaises(ValueError):j.handle({**m,'at':0})
            with self.assertRaises(ValueError):j.handle({**m,'profile':'changed'})
            active.write_text(json.dumps({'session':str(root)}))
            with self.assertRaises(ValueError):j.handle(m)
if __name__=='__main__':unittest.main()
