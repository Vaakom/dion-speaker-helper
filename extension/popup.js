const byId=id=>document.getElementById(id);
let busy=false;
async function show(){
  if(busy)return;busy=true;
  try{
    const value=await chrome.runtime.sendMessage({type:'status'});
    const view=journalView(value||{error:'Нет ответа расширения'});
    byId('status').textContent=view.label;byId('status').dataset.tone=view.tone;
    byId('detail').textContent=view.detail;
    byId('updated').textContent=view.last?'Последнее событие: '+new Date(view.last*1000).toLocaleTimeString('ru-RU')+' · '+Math.floor(view.age)+' с назад':'Событий пока нет';
    byId('path').value=view.path;
    byId('copy').disabled=!view.path;
  }catch(e){byId('status').textContent='Не удалось получить статус';byId('status').dataset.tone='error';byId('detail').textContent=e.message;byId('path').value='';byId('copy').disabled=true;}
  finally{busy=false;}
}
byId('copy').onclick=async()=>{
  try{await navigator.clipboard.writeText(byId('path').value);byId('copy-result').textContent='Путь скопирован';}
  catch{byId('path').focus();byId('path').select();byId('copy-result').textContent='Нажмите Ctrl+C, чтобы скопировать путь';}
};
for(const type of ['inspect','probe'])byId(type).onclick=async()=>{
  try{byId('diagnostics').textContent=JSON.stringify(await chrome.runtime.sendMessage({type}),null,2);}
  catch(e){byId('diagnostics').textContent=e.message;}
};
byId('options').onclick=()=>chrome.runtime.openOptionsPage();
chrome.storage.onChanged.addListener((changes,area)=>{if(area==='local')show();});
const refresh=setInterval(show,1000);
addEventListener('unload',()=>clearInterval(refresh));
show();
