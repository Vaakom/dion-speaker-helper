const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
test('Status updates do not restart polling; ambiguous names remain ambiguous',async()=>{
 let changed,message,polls=0,requests=0,last;
 const element=(name)=>({getClientRects:()=>[{}],textContent:name});
 const tile=(name)=>({getClientRects:()=>[{}],matches:()=>true,querySelectorAll:s=>s==='.name'?[element(name)]:[]});
 const context={crypto:{randomUUID:()=> 'document-12345'},document:{querySelectorAll:()=>[tile('Иван'),tile('Иван')]},getComputedStyle:()=>({visibility:'visible'}),Date,
 setInterval:()=>++polls,clearInterval:()=>{},
 chrome:{storage:{local:{get:async()=>({enabled:false,profile:{tile:'.tile',name:'.name',active:'.active'}})},onChanged:{addListener:f=>changed=f}},
 runtime:{sendMessage:async m=>{last=m;requests++},onMessage:{addListener:f=>message=f}}}};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'extension','content.js'),'utf8'),context);
 await new Promise(setImmediate);
 assert.equal(polls,1);assert.equal(requests,1);assert.equal(last.meeting,true);
 changed({status:{newValue:{ok:true}}},'local');
 await new Promise(setImmediate);
 assert.equal(polls,1);assert.equal(requests,1);
 message({type:'inspect'},{},r=>{last=r});
 assert.equal(last.speakers.length,2);
 changed({profile:{newValue:{}}},'local');
 await new Promise(setImmediate);assert.equal(polls,2);
});
