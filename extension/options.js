const ids=['tile','name','active'];
const algorithm='browser_only_v1';
const defaults={tile:'.e19i99td0',name:'[data-testid="name"]',active:'[data-testid="green-frame"] .e1iqp3xy0'};
chrome.storage.local.get('profile').then(({profile:p={}})=>{
  for(const id of ids)document.getElementById(id).value=p[id]||defaults[id];
  document.getElementById('calibrated').checked=!!p.calibrated;
});
for(const id of ids)document.getElementById(id).addEventListener('input',()=>document.getElementById('calibrated').checked=false);
document.getElementById('form').onsubmit=async e=>{
  e.preventDefault();
  try {
    const p={algorithm};
    for(const id of ids){
      p[id]=document.getElementById(id).value.trim();
      if(!p[id])throw Error('Заполните все селекторы');
      document.querySelector(p[id]);
    }
    p.calibrated=document.getElementById('calibrated').checked;
    await chrome.storage.local.set({profile:p});
    document.getElementById('result').textContent=p.calibrated
      ? 'Имена берутся из DION без анализа голосов. Знак ? отмечает заметную неопределённость.'
      : 'Диагностический режим: автоматическая подстановка имён отключена.';
  }catch(err){document.getElementById('result').textContent='Ошибка: '+err.message;}
};
