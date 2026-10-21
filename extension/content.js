(() => {
  if(globalThis.__dionAutoJournalLoaded)return;
  globalThis.__dionAutoJournalLoaded=true;
  const pageId=crypto.randomUUID();
  const defaults={tile:'.e19i99td0',name:'[data-testid="name"]',active:'[data-testid="green-frame"] .e1iqp3xy0'};
  let timer, profile = {}, enabled = false, hadMeeting=false, missingSince=null;
  function visible(el) { return !!(el && el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden'); }
  function inspect() {
    const p = profile;
    if (!p.tile || !p.name || !p.active) return {state:'unconfigured', speakers:[], tiles:0};
    try {
      const rawTiles = [...document.querySelectorAll(p.tile)];
      const tiles = rawTiles.filter(visible);
      const speakers = [];
      for (const tile of tiles) {
        const names = [...tile.querySelectorAll(p.name)].filter(visible);
        const active = tile.matches(p.active) || [...tile.querySelectorAll(p.active)].some(visible);
        if (active && names.length === 1) {
          const name = names[0].textContent.trim().replace(/\s+/g,' ');
          if (name && name.length <= 160) speakers.push(name);
        }
      }
      return {state: tiles.length ? 'observing' : 'no_tiles', speakers, tiles:tiles.length, meeting:rawTiles.length>0};
    } catch { return {state:'invalid_selectors', speakers:[], tiles:0}; }
  }
  async function tick() {
    if (!enabled) return;
    const sample=inspect();
    if(sample.meeting===true){hadMeeting=true;missingSince=null;}
    else if(sample.state==='no_tiles'&&hadMeeting){
      if(missingSince===null)missingSince=Date.now();
      if(Date.now()-missingSince<8000)return;
      sample.end_reason='meeting_ended';
    }else{return;} // Missing selectors or a frozen page are not meeting-end evidence.
    try { await chrome.runtime.sendMessage({type:'sample', ...sample, page_id:pageId, at:Date.now()}); } catch {}
  }
  async function configure() {
    const s = await chrome.storage.local.get(['profile','autoJournalEnabled']);
    profile = {...defaults,...(s.profile||{})}; enabled = s.autoJournalEnabled !== false;
    clearInterval(timer);
    if (enabled) { timer = setInterval(tick, 500); tick(); }
  }
  chrome.runtime.onMessage.addListener((m, sender, reply) => {
    if (m.type === 'inspect') reply(inspect());
    if (m.type === 'probe') {
      const seeds=[...document.querySelectorAll('video,[data-testid*="tile"],[data-testid*="participant"],[class*="speaking"],[class*="speaker"]')].filter(visible);
      const scopes=new Set();
      for(const seed of seeds.slice(0,24)){
        let el=seed;
        for(let i=0;el && i<4;i++,el=el.parentElement){
          if(['BODY','HTML','MAIN'].includes(el.tagName))break;
          scopes.add(el);
        }
      }
      const all=new Set();
      for(const scope of scopes){
        all.add(scope);
        for(const el of [...scope.querySelectorAll('*')].slice(0,120))all.add(el);
      }
      const nodes=[];let budget=0;
      for(const el of all){
        if(nodes.length>=200 || !visible(el))continue;
        if(el.closest('input,textarea,[contenteditable="true"],[role="log"],[data-testid*="chat"],[class*="chat"]'))continue;
        const cs=getComputedStyle(el);
        const node={
          tag:el.tagName,classes:String(el.className).slice(0,240),
          testid:el.getAttribute('data-testid')?.slice(0,100),
          role:el.getAttribute('role')?.slice(0,60),
          label:el.getAttribute('aria-label')?.slice(0,120),
          text:el.children.length===0 && !['SCRIPT','STYLE','INPUT','TEXTAREA'].includes(el.tagName)?el.textContent.trim().slice(0,100):undefined,
          parent:{tag:el.parentElement?.tagName,classes:String(el.parentElement?.className||'').slice(0,160)},
          data:[...el.attributes].filter(a=>/^data-|^aria-/.test(a.name)).slice(0,8).map(a=>[a.name,a.value.slice(0,100)]),
          style:{border:cs.border,outline:cs.outline,shadow:cs.boxShadow,background:cs.backgroundColor},
          children:el.children.length
        };
        const bytes=new TextEncoder().encode(JSON.stringify(node)).length;
        if(budget+bytes>45000)break;
        budget+=bytes;nodes.push(node);
      }
      reply({type:'probe',schema:2,at:Date.now(),videoCount:document.querySelectorAll('video').length,
        frameCount:document.querySelectorAll('iframe').length,seedCount:seeds.length,nodes});
    }
  });
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === 'local' && (changes.profile || changes.autoJournalEnabled)) configure();
  });
  configure();
})();
