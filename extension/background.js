const HOST='local.dion_speaker_helper';
let port, clientPromise;
const documents=new Map();
// Green means speech was actually saved by the native journal, not merely detected.
const speakingTabs=new Map();
let iconTimer, lastIcon, toolbarEnabled=true;
// Dion mark, traced as vector contours from https://dion.vc/logo192.png.
function contour(start,segments){
  const points=[start];let from=start;
  for(const s of segments){
    if(s.length===2){points.push(s);from=s;continue;}
    const [cx,cy,x,y]=s;
    for(let n=1;n<=20;n++){
      const t=n/20,u=1-t;
      points.push([u*u*from[0]+2*u*t*cx+t*t*x,u*u*from[1]+2*u*t*cy+t*t*y]);
    }
    from=[x,y];
  }
  return points;
}
const dionMark=[
  contour([40,28],[[91,28],[97,28,95,34],[89,56,66,56],[40,56],[35,56,35,51],[35,33],[35,28,40,28]]),
  contour([152,28],[[157,28,157,33],[157,51],[157,56,152,56],[117,56],[111,56,111,62],
    [111,96],[111,166,41,166],[35,166,35,160],[35,142],[35,136,41,136],[61,136],
    [81,136,81,116],[81,96],[81,28,152,28]]),
  contour([126,136],[[152,136],[157,136,157,142],[157,160],[157,166,152,166],[101,166],
    [96,166,98,160],[104,136,126,136]])
];
function insideMark(x,y,polygon){
  let inside=false;
  for(let i=0,j=polygon.length-1;i<polygon.length;j=i++){
    const [xi,yi]=polygon[i],[xj,yj]=polygon[j];
    if((yi>y)!==(yj>y)&&x<(xj-xi)*(y-yi)/(yj-yi)+xi)inside=!inside;
  }
  return inside;
}
function toolbarIcon(active,size){
  const data=new Uint8ClampedArray(size*size*4);
  const color=active?[34,197,94]:[120,128,140];
  for(let y=0;y<size;y++)for(let x=0;x<size;x++){
    const px=(x+.5)/size,py=(y+.5)/size;
    const dx=Math.max(.12-px,0,px-.88),dy=Math.max(.12-py,0,py-.88);
    if(dx*dx+dy*dy>.12*.12)continue;
    const bar=dionMark.some(p=>insideMark(24+px*144,24+py*144,p));
    const i=(y*size+x)*4;
    data.set(bar?[255,255,255,255]:[...color,255],i);
  }
  return new ImageData(data,size,size);
}
function refreshToolbar(){
  if(!chrome.action)return;
  clearTimeout(iconTimer);
  const now=Date.now();
  for(const [tab,until] of speakingTabs)if(until<=now)speakingTabs.delete(tab);
  const active=speakingTabs.size>0;
  if(active!==lastIcon){
    lastIcon=active;
    Promise.all([
      chrome.action.setIcon({imageData:Object.fromEntries([16,20,24,32,48].map(size=>[size,toolbarIcon(active,size)]))}),
      chrome.action.setTitle({title:active?'Dion: участник говорит, журнал записывается':'Dion: нет подтверждённой записи речи'})
    ]).catch(()=>{lastIcon=undefined;});
  }
  if(active)iconTimer=setTimeout(refreshToolbar,Math.max(1,Math.min(...speakingTabs.values())-now));
}
function clearSpeech(tab){
  if(Number.isInteger(tab))speakingTabs.delete(tab);else speakingTabs.clear();
  refreshToolbar();
}
refreshToolbar();
chrome.storage.onChanged?.addListener((changes,area)=>{
  if(area==='local'&&changes.autoJournalEnabled){
    toolbarEnabled=changes.autoJournalEnabled.newValue!==false;
    if(!toolbarEnabled)clearSpeech();
  }
});
function validUrl(url){
  try{const u=new URL(url);return u.protocol==='https:'&&(u.hostname==='dion.vc'||u.hostname.endsWith('.dion.vc'));}catch{return false;}
}
async function clientId(){
  if(!clientPromise)clientPromise=chrome.storage.local.get('journalClient').then(async s=>{
    if(s.journalClient)return s.journalClient;
    const id=crypto.randomUUID();await chrome.storage.local.set({journalClient:id});return id;
  });
  return clientPromise;
}
async function meetingId(url){
  const u=new URL(url);
  // Keep identity, never persist query parameters, invitations or full URLs.
  const route=u.origin+u.pathname+u.search+u.hash;
  const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(route));
  return [...new Uint8Array(bytes)].map(x=>x.toString(16).padStart(2,'0')).join('');
}
async function publish(value){
  if(value.ok===true&&value.state==='auto_journaling'&&Number.isInteger(value.tab)){
    const until=Number(value.last_at)*1000+5000;
    if(toolbarEnabled&&value.observation_state==='observing'&&Array.isArray(value.speakers)&&value.speakers.length&&until>Date.now())
      speakingTabs.set(value.tab,until);
    else speakingTabs.delete(value.tab);
    refreshToolbar();
  }else if(value.ok===false||value.state==='meeting_closed')clearSpeech(value.tab);
  const patch={};
  if(value.state==='auto_journaling')patch.nativeConnection={connected:true,at:Date.now()};
  if(Number.isInteger(value.tab)){
    const key='journalStatus:'+value.tab;
    const old=await chrome.storage.local.get(key);
    patch[key]={...(old[key]||{}),...value};
  }
  if(Object.keys(patch).length)await chrome.storage.local.set(patch);
}
function connect(){
  if(port)return port;
  port=chrome.runtime.connectNative(HOST);
  port.onMessage.addListener(publish);
  port.onDisconnect.addListener(()=>{
    const error=chrome.runtime.lastError?.message||'Связь с локальным журналом потеряна';
    port=null;chrome.storage.local.set({nativeConnection:{connected:false,error,at:Date.now()}});publish({ok:false,error,retry:'При следующем наблюдении повторим подключение'});
  });
  return port;
}
chrome.runtime.onMessage.addListener((m,sender,reply)=>{
  if(m.type==='sample'){
    if(!validUrl(sender.url)||!Number.isInteger(sender.tab?.id)||typeof m.page_id!=='string')return;
    (async()=>{
      const s=await chrome.storage.local.get(['profile','autoJournalEnabled']);
      if(s.autoJournalEnabled===false){clearSpeech(sender.tab.id);return;}
      if(m.state!=='observing'||!Array.isArray(m.speakers)||!m.speakers.length)clearSpeech(sender.tab.id);
      if(m.meeting!==true){
        if(m.meeting===false&&m.end_reason==='meeting_ended')
          await endDocument(sender.tab.id,'meeting_ended',m.page_id);
        return;
      }
      const doc={page:m.page_id,client:await clientId(),meeting:await meetingId(sender.url)};
      documents.set(sender.tab.id,doc);
      await chrome.storage.local.set({['journalDoc:'+sender.tab.id]:doc});
      connect().postMessage({
        type:'auto_sample',tab:sender.tab.id,page_id:m.page_id,client:await clientId(),
        lifecycle_version:1,meeting_id:doc.meeting,title:String(sender.tab.title||'DION').slice(0,160),
        at:m.at,state:m.state,speakers:m.speakers,tiles:m.tiles,
        calibrated:s.profile?.calibrated===true,profile:JSON.stringify(s.profile||{})
      });
    })().catch(e=>publish({ok:false,tab:sender.tab.id,error:e.message}));
    return;
  }
  if(sender.id!==chrome.runtime.id||sender.tab)return;
  if(m.type==='inspect'||m.type==='probe'){
    chrome.tabs.query({active:true,currentWindow:true}).then(tabs=>{
      if(!validUrl(tabs[0]?.url))throw Error('Откройте вкладку DION');
      return chrome.tabs.sendMessage(tabs[0].id,{type:m.type});
    }).then(result=>{
      if(m.type==='probe'&&!result.error)connect().postMessage(result);
      reply(result);
    }).catch(e=>reply({error:e.message}));return true;
  }
  if(m.type==='status'){
    chrome.tabs.query({active:true,currentWindow:true}).then(async tabs=>{
      const tab=tabs[0],key='journalStatus:'+tab?.id;
      const s=await chrome.storage.local.get(['autoJournalEnabled',key,'nativeConnection','profile']);
      reply({enabled:s.autoJournalEnabled!==false,isDion:validUrl(tab?.url),profile_verified:s.profile?.calibrated===true,
        connection:s.nativeConnection,status:validUrl(tab?.url)?s[key]||{}:{}});
    }).catch(e=>reply({error:e.message}));return true;
  }
});

async function endDocument(tab,reason,page){
  const stored=await chrome.storage.local.get('journalDoc:'+tab);
  const doc=documents.get(tab)||stored['journalDoc:'+tab];
  if(!doc||(page&&page!==doc.page))return;
  clearSpeech(tab);
  connect().postMessage({type:'auto_end',tab,page_id:doc.page,client:doc.client,reason});
  documents.delete(tab);
}
chrome.tabs.onRemoved.addListener((tab,info)=>{
  clearSpeech(tab);
  endDocument(tab,info?.isWindowClosing?'browser_window_closed':'tab_closed')
    .catch(e=>publish({ok:false,tab,error:e.message}));
});
chrome.tabs.onUpdated.addListener((tab,change)=>{
  if(!change.url)return;
  (async()=>{
    const stored=await chrome.storage.local.get('journalDoc:'+tab);
    const doc=documents.get(tab)||stored['journalDoc:'+tab];
    if(doc&&(!validUrl(change.url)||await meetingId(change.url)!==doc.meeting))
      await endDocument(tab,'meeting_page_closed');
  })().catch(e=>publish({ok:false,tab,error:e.message}));
});

async function attachOpenDionTabs(){
  const tabs=await chrome.tabs.query({url:['https://dion.vc/*','https://*.dion.vc/*']});
  for(const tab of tabs){
    try{await chrome.scripting.executeScript({target:{tabId:tab.id},files:['content.js']});}
    catch(e){publish({ok:false,tab:tab.id,error:e.message});}
  }
}
chrome.runtime.onInstalled.addListener(()=>attachOpenDionTabs().catch(e=>publish({ok:false,error:e.message})));
chrome.runtime.onStartup.addListener(()=>attachOpenDionTabs().catch(e=>publish({ok:false,error:e.message})));
attachOpenDionTabs().catch(e=>publish({ok:false,error:e.message}));
