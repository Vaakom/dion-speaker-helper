const {test}=require('node:test');
const assert=require('node:assert/strict');
const {journalView}=require('./extension/status-view.js');
const base={enabled:true,isDion:true,connection:{connected:true},status:{ok:true,state:'auto_journaling',last_at:100,path:'C:/journal/events.jsonl',speakers:[],observation_state:'observing'}};
test('fresh acknowledgement is healthy, silence is not an error',()=>assert.equal(journalView(base,102000).tone,'success'));
test('status expires without a storage update',()=>assert.equal(journalView(base,106000).label,'Журнал не обновляется'));
test('disconnect overrides a recent success and preserves journal path',()=>{
 const v=journalView({...base,connection:{connected:false}},102000);assert.equal(v.tone,'error');assert.equal(v.path,base.status.path);
});
test('closed meeting is not reported as stale or disconnected',()=>{
 const v=journalView({...base,connection:{connected:false},status:{...base.status,state:'meeting_closed'}},150000);
 assert.equal(v.label,'Встреча завершена');assert.equal(v.path,base.status.path);
});
test('unrelated tab does not expose another meeting journal',()=>{
 const v=journalView({...base,isDion:false},102000);assert.equal(v.path,'');assert.equal(v.last,null);
});
test('missing acknowledgement never means success',()=>assert.notEqual(journalView({...base,status:{}},102000).tone,'success'));
test('observer failure is visible even with a fresh disk acknowledgement',()=>assert.equal(journalView({...base,status:{...base.status,observation_state:'no_tiles'}},102000).tone,'warning'));
test('disabled journal and failed status request are explicit',()=>{
 assert.equal(journalView({...base,enabled:false},102000).label,'Журналирование отключено');
 assert.equal(journalView({error:'unavailable'},102000).tone,'error');
});

const vm=require('node:vm'),fs=require('node:fs'),{webcrypto}=require('node:crypto');
test('background reports disconnect without using status from another tab; closure retains path',async()=>{
 let handler,receive,disconnect;let active=1;
 const store={'journalStatus:1':{ok:true,state:'auto_journaling',last_at:100,path:'C:/one/events.jsonl'}};
 const chrome={
 runtime:{id:'test',onMessage:{addListener:f=>handler=f},onInstalled:{addListener:()=>{}},onStartup:{addListener:()=>{}},
 connectNative:()=>({onMessage:{addListener:f=>receive=f},onDisconnect:{addListener:f=>disconnect=f},postMessage:()=>{}})},
 storage:{local:{get:async keys=>Object.fromEntries((Array.isArray(keys)?keys:[keys]).map(k=>[k,store[k]])),set:async v=>Object.assign(store,v)}},
 tabs:{query:async()=>[{id:active,url:'https://dion.vc/test'}],onRemoved:{addListener:()=>{}},onUpdated:{addListener:()=>{}}},
 scripting:{executeScript:async()=>{}}
 };
 vm.runInNewContext(fs.readFileSync(__dirname+'/extension/background.js','utf8'),{chrome,crypto:webcrypto,TextEncoder,URL,Map,Uint8Array,Date});
 await new Promise(setImmediate);
 handler({type:'sample',page_id:'document-12345',meeting:true,at:Date.now(),state:'observing',speakers:[]},{url:'https://dion.vc/test',tab:{id:1}},()=>{});
 for(let i=0;i<100&&!disconnect;i++)await new Promise(r=>setTimeout(r,5));
 assert.ok(disconnect);
 disconnect();
 const status=()=>new Promise(resolve=>handler({type:'status'},{id:'test'},resolve));
 const first=await status();assert.equal(first.connection.connected,false);assert.equal(first.status.path,'C:/one/events.jsonl');
 active=2;assert.equal(Object.keys((await status()).status).length,0);
 active=1;
 await receive({ok:true,state:'meeting_closed',tab:1});
 const closed=await status();assert.equal(closed.status.state,'meeting_closed');assert.equal(closed.status.path,'C:/one/events.jsonl');
});
test('popup refresh timer expires cached status and clipboard offers manual fallback',async()=>{
 const elements={};let timer,now=102000,copied='',fail=false;
 function element(){return {textContent:'',dataset:{},value:'',disabled:false,focus(){this.focused=true;},select(){this.selected=true;}};}
 const document={getElementById:id=>elements[id]??=(element())};
 class Clock extends Date{static now(){return now;}}
 const context={document,journalView:v=>journalView(v,now),Date:Clock,Math,
 chrome:{runtime:{sendMessage:async()=>base,openOptionsPage:()=>{}},storage:{onChanged:{addListener:()=>{}}}},
 navigator:{clipboard:{writeText:async text=>{if(fail)throw Error('denied');copied=text;}}},
 setInterval:f=>{timer=f;return 1;},clearInterval:()=>{},addEventListener:()=>{}};
 vm.runInNewContext(fs.readFileSync(__dirname+'/extension/popup.js','utf8'),context);
 await new Promise(setImmediate);
 assert.equal(elements.status.textContent,'Журнал записывается');
 now=106000;await timer();assert.equal(elements.status.textContent,'Журнал не обновляется');
 await elements.copy.onclick();assert.equal(copied,base.status.path);
 fail=true;await elements.copy.onclick();assert.ok(elements.path.selected);assert.match(elements['copy-result'].textContent,/Ctrl\+C/);
});
