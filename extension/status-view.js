'use strict';
function journalView(value, now=Date.now()) {
  const s=value.status||{}, age=Number.isFinite(s.last_at)?Math.max(0,(now-s.last_at*1000)/1000):null;
  const result={label:'Ожидание журнала',tone:'warning',detail:'Откройте встречу DION.',path:s.path||'',age,last:s.last_at||null,speakers:s.speakers||[]};
  if(value.error)return {...result,label:'Не удалось получить статус',tone:'error',detail:value.error};
  if(value.enabled===false)return {...result,label:'Журналирование отключено',detail:'Новые события не записываются.'};
  if(!value.isDion)return {...result,label:'Откройте вкладку DION',path:'',last:null,age:null,speakers:[]};
  if(s.state==='meeting_closed')return {...result,label:'Встреча завершена',tone:'neutral',detail:'Запись событий этой встречи остановлена.'};
  if(s.ok===false)return {...result,label:'Ошибка журнала',tone:'error',detail:s.error||'Проверьте локальный помощник.'};
  if(value.connection?.connected===false)return {...result,label:'Связь с помощником потеряна',tone:'error',detail:'Ожидается переподключение при следующем наблюдении.'};
  if(s.state!=='auto_journaling'||age===null)return result;
  if(age>5)return {...result,label:'Журнал не обновляется',tone:'error',detail:'Нет новых событий более 5 секунд. Проверьте вкладку и локальный помощник.'};
  if(s.observation_state&&s.observation_state!=='observing')return {...result,label:'Участники не обнаружены',detail:'События сохраняются, но индикаторы участников недоступны.'};
  return {...result,label:'Журнал записывается',tone:'success',detail:s.speakers?.length?'Сейчас говорят: '+s.speakers.join(', '):'Сейчас никто не отмечен говорящим.'};
}
if(typeof module!=='undefined')module.exports={journalView};
