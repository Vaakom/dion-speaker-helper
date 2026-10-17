"""Chrome Native Messaging: append validated samples only to an explicitly bound recording."""
import json, struct, sys, time, os
from pathlib import Path

def read_message(stream):
    header=stream.read(4)
    if not header: return None
    if len(header)!=4: raise ValueError('Incomplete header')
    size=struct.unpack('<I',header)[0]
    if size>65536: raise ValueError('Message too large')
    body=bytearray()
    while len(body)<size:
        part=stream.read(size-len(body))
        if not part: raise ValueError('Incomplete body')
        body.extend(part)
    return json.loads(body)

def write_message(stream,value):
    body=json.dumps(value,ensure_ascii=False).encode('utf-8')
    stream.write(struct.pack('<I',len(body))+body);stream.flush()

class LegacyJournal:
    def __init__(self,config):
        self.config=config; self.session=None;self.tab=None;self.origin=None;self.profile=None
    def active_session(self):
        active=json.loads(Path(self.config['active']).read_text('utf-8'))
        session=Path(active['session']).resolve()
        root=Path(self.config['sessions']).resolve()
        if not session.is_relative_to(root): raise ValueError('Session outside configured folder')
        state=json.loads((session/'status.json').read_text('utf-8'))
        if state.get('state')!='recording': raise ValueError('No active recording')
        if time.time()-(session/'status.json').stat().st_mtime>5: raise ValueError('Recording status stale')
        return session
    def handle(self,msg):
        kind=msg.get('type')
        if kind=='probe':
            encoded=json.dumps(msg,ensure_ascii=False)
            if len(encoded.encode('utf-8'))>60000 or not isinstance(msg.get('nodes'),list):
                raise ValueError('Invalid diagnostic report')
            directory=Path(__file__).parent/'diagnostics'
            directory.mkdir(exist_ok=True)
            path=directory/('dom-'+str(time.time_ns())+'.json')
            path.write_text(encoded,'utf-8')
            return {'ok':True,'state':'diagnostic_saved','path':str(path)}
        if kind=='unbind':
            self.session=None; return {'ok':True,'state':'detached'}
        if kind=='bind':
            self.session=self.active_session();self.tab=msg['tab'];self.profile=None
            if not isinstance(self.tab,int): raise ValueError('Invalid tab')
            self.origin=json.loads((self.session/'recording_clock.json').read_text('utf-8'))['remote_monotonic']
            return {'ok':True,'state':'bound','session':self.session.name}
        if kind!='sample' or self.session is None: raise ValueError('Bind to an active recording first')
        if self.active_session()!=self.session: self.session=None;raise ValueError('Recording changed; bind again')
        if msg.get('tab')!=self.tab: raise ValueError('Wrong tab')
        now=time.monotonic()
        delay=time.time()*1000-float(msg['at'])
        if delay< -250 or delay>750: raise ValueError('Stale browser sample')
        state=msg.get('state')
        if state not in ('observing','unconfigured','no_tiles','invalid_selectors'): raise ValueError('Invalid state')
        names=msg.get('speakers')
        if not isinstance(names,list) or len(names)>30: raise ValueError('Invalid speakers')
        if any(not isinstance(n,str) or not n.strip() or len(n)>160 or any(c in n for c in '\r\n\x00') for n in names): raise ValueError('Invalid name')
        profile=msg.get('profile','')
        if not isinstance(profile,str) or len(profile)>1600: raise ValueError('Invalid profile')
        if self.profile is None:self.profile=profile
        if profile!=self.profile: raise ValueError('Profile changed; bind again')
        sample={'schema':1,'seconds':round(now-self.origin,4),'at':time.time(),
                'speakers':names,'state':state,'calibrated':msg.get('calibrated') is True,
                'delay_ms':round(delay),'profile':profile}
        with (self.session/'browser-speakers.jsonl').open('a',encoding='utf-8') as out:
            out.write(json.dumps(sample,ensure_ascii=False)+'\n')
        return {'ok':True,'state':'observing' if sample['calibrated'] else 'diagnostic_only',
                'speakers':names,'seconds':sample['seconds']}


class Journal(LegacyJournal):
    """Independent, deterministic journals for every observed DION document."""
    def __init__(self,config):
        super().__init__(config)
        self.streams={}
    def handle(self,msg):
        if msg.get('type') not in ('auto_sample','auto_end'):
            return super().handle(msg)
        import hashlib,re,datetime as dt,math
        tab=msg.get('tab')
        if not isinstance(tab,int) or isinstance(tab,bool) or tab<0:raise ValueError('Invalid tab')
        client,page=msg.get('client'),msg.get('page_id')
        if any(not isinstance(v,str) or not re.fullmatch(r'[a-zA-Z0-9-]{8,80}',v) for v in (client,page)):
            raise ValueError('Invalid browser document identity')
        key=(client,tab,page)
        if msg['type']=='auto_end':
            state=self.streams.pop(key,None)
            if state:
                meta=json.loads((state/'meta.json').read_text('utf-8'))
                meta['ended_at']=time.time()
                (state/'meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),'utf-8')
            return {'ok':True,'tab':tab,'state':'meeting_closed'}
        meeting=msg.get('meeting_id')
        if not isinstance(meeting,str) or not re.fullmatch(r'[0-9a-f]{64}',meeting):
            raise ValueError('Invalid meeting identity')
        at=msg.get('at')
        if not isinstance(at,(int,float)) or not math.isfinite(at):raise ValueError('Invalid sample time')
        delay=time.time()*1000-at
        if not -250<=delay<=1500:raise ValueError('Stale browser sample')
        names=msg.get('speakers')
        if not isinstance(names,list) or len(names)>30:raise ValueError('Invalid speakers')
        if any(not isinstance(n,str) or not n.strip() or len(n)>160 or any(c in n for c in '\r\n\x00') for n in names):
            raise ValueError('Invalid speaker name')
        profile=msg.get('profile','')
        if not isinstance(profile,str) or len(profile)>1600:raise ValueError('Invalid profile')
        sample_state=msg.get('state')
        if sample_state not in ('observing','unconfigured','no_tiles','invalid_selectors'):
            raise ValueError('Invalid observer state')
        title=str(msg.get('title','DION'))[:160]
        directory=Path(self.config.get('journals',str(Path(__file__).parent/'journals')))
        digest=hashlib.sha256(f'{client}:{tab}:{page}:{meeting}'.encode()).hexdigest()[:32]
        # Include day; reload/reconnect segments are linked by metadata, not by filenames.
        day=dt.datetime.now().strftime('%Y-%m-%d')
        target=directory/day/digest
        target.mkdir(parents=True,exist_ok=True)
        now=time.monotonic();wall=time.time()
        meta_path=target/'meta.json'
        if not meta_path.exists():
            meta={'schema':1,'client':client,'tab':tab,'page_id':page,'meeting_id':meeting,
                  'title':title,'started_at':wall,'boot_epoch':wall-now}
        else:meta=json.loads(meta_path.read_text('utf-8'))
        meta.update(last_at=wall,last_monotonic=now,title=title)
        # Atomic metadata avoids partial reads by the secretary.
        temp=target/'meta.json.tmp'
        temp.write_text(json.dumps(meta,ensure_ascii=False,indent=2),'utf-8');temp.replace(meta_path)
        sample={'schema':2,'monotonic':now,'at':wall,'delay_ms':round(delay),
                'speakers':names,'state':sample_state,'calibrated':msg.get('calibrated') is True,
                'profile':profile,'tab':tab,'meeting_id':meeting}
        with (target/'events.jsonl').open('a',encoding='utf-8') as out:
            out.write(json.dumps(sample,ensure_ascii=False)+'\n')
        self.streams[key]=target
        return {'ok':True,'state':'auto_journaling','tab':tab,'meeting_id':meeting[:12],
                'title':title,'path':str(target),'speakers':names,'last_at':wall,'observation_state':sample_state}

def main():
    if os.name=='nt':
        import msvcrt
        msvcrt.setmode(sys.stdin.fileno(),os.O_BINARY);msvcrt.setmode(sys.stdout.fileno(),os.O_BINARY)
    config=json.loads(Path(__file__).with_name('host-config.json').read_text('utf-8'))
    if len(sys.argv)<2 or sys.argv[1]!=config['origin']: raise ValueError('Extension origin mismatch')
    journal=Journal(config)
    while (msg:=read_message(sys.stdin.buffer)) is not None:
        try: result=journal.handle(msg)
        except (ValueError,KeyError,TypeError,OSError) as exc: result={'ok':False,'error':str(exc)}
        write_message(sys.stdout.buffer,result)
if __name__=='__main__':main()
