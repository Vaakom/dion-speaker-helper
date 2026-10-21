const HOST='local.dion_speaker_helper';
let port, clientPromise;
const documents=new Map();
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
      if(s.autoJournalEnabled===false)return;
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
      const s=await chrome.storage.local.get(['autoJournalEnabled',key,'nativeConnection']);
      reply({enabled:s.autoJournalEnabled!==false,isDion:validUrl(tab?.url),
        connection:s.nativeConnection,status:validUrl(tab?.url)?s[key]||{}:{}});
    }).catch(e=>reply({error:e.message}));return true;
  }
});

async function endDocument(tab,reason,page){
  const stored=await chrome.storage.local.get('journalDoc:'+tab);
  const doc=documents.get(tab)||stored['journalDoc:'+tab];
  if(!doc||(page&&page!==doc.page))return;
  connect().postMessage({type:'auto_end',tab,page_id:doc.page,client:doc.client,reason});
  documents.delete(tab);
}
chrome.tabs.onRemoved.addListener((tab,info)=>{
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
