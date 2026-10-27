const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
function harness(){
 let now=10000,receive,disconnect,changed,removed,timer;
 const icons=[],titles=[],store={};
 const chrome={
  action:{setIcon:async v=>icons.push(v),setTitle:async v=>titles.push(v.title)},
  runtime:{onMessage:{addListener:()=>{}},onInstalled:{addListener:()=>{}},onStartup:{addListener:()=>{}},
   connectNative:()=>({onMessage:{addListener:f=>receive=f},onDisconnect:{addListener:f=>disconnect=f},postMessage:()=>{}})},
  storage:{onChanged:{addListener:f=>changed=f},local:{get:async()=>({}),set:async v=>Object.assign(store,v)}},
  tabs:{query:async()=>[],onRemoved:{addListener:f=>removed=f},onUpdated:{addListener:()=>{}}},
  scripting:{executeScript:async()=>{}}
 };
 const ctx=vm.createContext({chrome,Map,Uint8ClampedArray,Date:{now:()=>now},
  ImageData:class{constructor(data,width,height){Object.assign(this,{data,width,height});}},
  setTimeout:(f,ms)=>(timer={f,ms},1),clearTimeout:()=>{timer=null;}});
 vm.runInContext(fs.readFileSync(path.join(__dirname,'extension/background.js'),'utf8'),ctx);
 vm.runInContext('connect()',ctx);
 const ack=(tab=1,speakers=['Анна'],extra={})=>receive({ok:true,state:'auto_journaling',tab,
  speakers,observation_state:'observing',last_at:now/1000,...extra});
 return {ack,icons,titles,disconnect,changed,removed,
  active:()=>titles.at(-1).includes('участник говорит'),
  expire:()=>{now+=5001;timer.f();}};
}
test('Green only after saved speech; silence and invalid observation turn it off',async()=>{
 const b=harness();assert.equal(b.active(),false);
 await b.ack();assert.equal(b.active(),true);
 const pixels=b.icons.at(-1).imageData[16].data;
 assert.ok(Array.from({length:pixels.length/4},(_,i)=>i*4).some(i=>pixels[i]===34&&pixels[i+1]===197&&pixels[i+2]===94));
 await b.ack(1,[]);assert.equal(b.active(),false);
 await b.ack();await b.ack(1,['Анна'],{observation_state:'invalid_selectors'});assert.equal(b.active(),false);
});
test('Stale acknowledgement, native failure and disconnect never leave green',async()=>{
 const b=harness();await b.ack(1,['Анна'],{last_at:1});assert.equal(b.active(),false);
 await b.ack();b.expire();assert.equal(b.active(),false);
 await b.ack();await b.ack(1,['Анна'],{ok:false,error:'Disk full'});assert.equal(b.active(),false);
 await b.ack();b.disconnect();assert.equal(b.active(),false);
});
test('Any live meeting can light toolbar; closing one preserves the other',async()=>{
 const b=harness();await b.ack(1);await b.ack(2);
 b.removed(1,{});assert.equal(b.active(),true);
 await b.ack(2,[]);assert.equal(b.active(),false);
 await b.ack(2);b.changed({autoJournalEnabled:{newValue:false}},'local');assert.equal(b.active(),false);
 await b.ack(2);assert.equal(b.active(),false,'Late acknowledgement cannot undo disable');
});
