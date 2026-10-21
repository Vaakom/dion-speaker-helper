const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const {webcrypto}=require('node:crypto');

function background(store={}){
 const handlers={},frames=[];
 const chrome={runtime:{id:'extension-id',onMessage:{addListener:f=>handlers.message=f},
  onInstalled:{addListener:()=>{}},onStartup:{addListener:()=>{}},
  connectNative:()=>({onMessage:{addListener:()=>{}},onDisconnect:{addListener:()=>{}},postMessage:m=>frames.push(m)})},
 storage:{local:{get:async keys=>Object.fromEntries((Array.isArray(keys)?keys:[keys]).map(k=>[k,store[k]])),
  set:async patch=>Object.assign(store,patch)}},
 tabs:{query:async()=>[],onRemoved:{addListener:f=>handlers.removed=f},onUpdated:{addListener:f=>handlers.updated=f}},
 scripting:{executeScript:async()=>[]}};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'extension/background.js'),'utf8'),
  {chrome,crypto:webcrypto,TextEncoder,URL,Map,Uint8Array});
 return {handlers,frames,store};
}
async function waitFor(f){for(let i=0;i<100&&!f();i++)await new Promise(r=>setTimeout(r,5));assert.ok(f());}
async function sample(b,tab=1){
 b.handlers.message({type:'sample',page_id:'document-12345',meeting:true,at:Date.now(),state:'observing',speakers:[],tiles:1},
  {url:'https://dion.vc/meeting/one',tab:{id:tab,title:'DION'}},()=>{});
 await waitFor(()=>b.frames.some(m=>m.tab===tab&&m.type==='auto_sample'));
}
test('Closed meeting tab sends reason even after service worker restart',async()=>{
 const b=background();await sample(b);
 const next=background(b.store);next.handlers.removed(1,{isWindowClosing:false});
 await waitFor(()=>next.frames.length);
 assert.equal(next.frames[0].reason,'tab_closed');
 assert.equal(next.frames[0].page_id,'document-12345');
});
test('Window closure and other tabs are isolated',async()=>{
 const b=background();await sample(b);
 b.handlers.removed(999,{isWindowClosing:false});await new Promise(setImmediate);
 assert.equal(b.frames.length,1);
 b.handlers.removed(1,{isWindowClosing:true});await waitFor(()=>b.frames.length===2);
 assert.equal(b.frames[1].reason,'browser_window_closed');
});
test('Only explicit meeting-end sample ends meeting; invalid selectors do not',async()=>{
 const b=background();await sample(b);
 const sender={url:'https://dion.vc/meeting/one',tab:{id:1,title:'DION'}};
 b.handlers.message({type:'sample',page_id:'document-12345',state:'invalid_selectors'},sender,()=>{});
 await new Promise(setImmediate);assert.equal(b.frames.length,1);
 b.handlers.message({type:'sample',page_id:'document-12345',meeting:false,end_reason:'meeting_ended'},sender,()=>{});
 await waitFor(()=>b.frames.length===2);assert.equal(b.frames[1].reason,'meeting_ended');
});
test('Navigation away ends meeting; same URL reload does not',async()=>{
 const b=background();await sample(b);
 b.handlers.updated(1,{url:'https://dion.vc/meeting/one'});
 await new Promise(r=>setTimeout(r,20));assert.equal(b.frames.length,1);
 b.handlers.updated(1,{url:'https://example.org/'});
 await waitFor(()=>b.frames.length===2);assert.equal(b.frames[1].reason,'meeting_page_closed');
});
test('Content requires eight seconds without meeting tiles and tolerates transient gaps',async()=>{
 let tick,last,now=0,tiles=true;
 const sent=[];
 const chrome={storage:{local:{get:async()=>({profile:{tile:'.tile',name:'.name',active:'.active'}})},onChanged:{addListener:()=>{}}},
 runtime:{sendMessage:async m=>sent.push(m),onMessage:{addListener:()=>{}}}};
 const tile={getClientRects:()=>[{}],matches:()=>false,querySelectorAll:()=>[]};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'extension/content.js'),'utf8'),
 {crypto:{randomUUID:()=> 'document-12345'},document:{querySelectorAll:()=>tiles?[tile]:[]},
  getComputedStyle:()=>({visibility:'visible'}),Date:{now:()=>now},setInterval:f=>(tick=f,1),clearInterval:()=>{},chrome});
 await new Promise(setImmediate);assert.equal(sent.length,1);
 tiles=false;now=1000;await tick();now=6000;await tick();assert.equal(sent.length,1);
 tiles=true;await tick();assert.equal(sent.at(-1).meeting,true);
 tiles=false;now=7000;await tick();now=14999;await tick();assert.equal(sent.at(-1).meeting,true);
 now=15000;await tick();assert.equal(sent.at(-1).end_reason,'meeting_ended');
 assert.equal(sent.at(-1).meeting,false);
});
