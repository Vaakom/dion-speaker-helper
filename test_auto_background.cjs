const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const {webcrypto}=require('node:crypto');
test('Each DION tab starts independently without bind; reconnect resumes',async()=>{
 let listener,disconnect,connections=0;
 const frames=[],store={profile:{calibrated:true}};
 const chrome={
  runtime:{id:'extension-id',onMessage:{addListener:f=>listener=f},onInstalled:{addListener:()=>{}},onStartup:{addListener:()=>{}},
   connectNative:()=>{connections++;return {onMessage:{addListener:()=>{}},onDisconnect:{addListener:f=>disconnect=f},
    postMessage:m=>frames.push(m)};}},
  storage:{local:{get:async keys=>{const r={};for(const k of Array.isArray(keys)?keys:[keys])r[k]=store[k];return r;},
    set:async values=>Object.assign(store,values)}},
  tabs:{query:async()=>[],onRemoved:{addListener:()=>{}},onUpdated:{addListener:()=>{}}},
  scripting:{executeScript:async()=>[]}
 };
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'extension','background.js'),'utf8'),
   {chrome,crypto:webcrypto,TextEncoder,URL,Map,Uint8Array});
 async function sample(tab,url,meeting=true){
  const count=frames.length;
  listener({type:'sample',page_id:'document-12345',meeting,end_reason:meeting?undefined:'meeting_ended',at:Date.now(),state:'observing',speakers:['Анна'],tiles:2},
   {url,tab:{id:tab,title:'DION'}},()=>{});
  for(let i=0;i<100&&frames.length===count;i++)await new Promise(r=>setTimeout(r,5));
  assert.ok(frames.length>count,'Expected automatic native message');
  return frames.at(-1);
 }
 const a=await sample(1,'https://dion.vc/meeting/one?secret=hidden');
 const b=await sample(2,'https://dion.vc/meeting/two');
 assert.equal(a.type,'auto_sample');assert.equal(b.type,'auto_sample');
 assert.notEqual(a.meeting_id,b.meeting_id);assert.equal(a.client,b.client);
 assert.ok(!JSON.stringify(a).includes('hidden'));
 disconnect();
 const c=await sample(1,'https://dion.vc/meeting/one?secret=hidden');
 assert.equal(connections,2);assert.equal(c.meeting_id,a.meeting_id);
 const end=await sample(1,'https://dion.vc/meeting/one',false);
 assert.equal(end.type,'auto_end');
});
