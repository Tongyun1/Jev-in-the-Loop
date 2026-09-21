(() => {
  if (!document.body) return null;
  const cache = window.__jevFast ||= {ids:new WeakMap(), nodes:new Map(), next:1};
  const identity = e => {
    if (!cache.ids.has(e)) cache.ids.set(e,cache.next++);
    const id=cache.ids.get(e); cache.nodes.set(id,e); return id;
  };
  for (const [id,e] of cache.nodes) if (!e.isConnected) cache.nodes.delete(id);
  const safe = e => !['password','file','hidden'].includes(e.type);
  const rendered = e => !e.closest('[inert]') &&
    e.checkVisibility({checkOpacity:true,checkVisibilityCSS:true});
  const steppers=new Map();
  const visible = e => rendered(e) && (steppers.has(e)
    ? !e.parentElement.closest('[aria-hidden="true"]')
    : !e.closest('[aria-hidden="true"]'));
  const name = (e,seen=new Set()) => {
    if (!e || seen.has(e)) return '';
    seen.add(e);
    const referenced=(e.getAttribute('aria-labelledby')||'').split(/\s+/)
      .map(id=>name(document.getElementById(id),seen)).filter(Boolean).join(' ');
    return referenced || e.getAttribute('aria-label') ||
      [...(e.labels||[])].map(l=>name(l,seen)).filter(Boolean).join(' ') ||
      (['button','submit','reset'].includes(e.type) ? e.value : '') || e.getAttribute('alt') ||
      (e.tagName==='INPUT' ? '' : [...e.childNodes].map(n=>n.nodeType===3 ? n.textContent :
        n.nodeType===1 && n.getAttribute('aria-hidden')!=='true' ? name(n,seen) : '').join(' ').trim()) ||
      e.getAttribute('title') || e.getAttribute('placeholder') || '';
  };
  const roles=['button','link','checkbox','radio','switch','tab','menuitem','menuitemradio',
    'option','gridcell','combobox','textbox','searchbox','spinbutton'];
  const selector='a[href],button,input,textarea,select,summary,[contenteditable="true"],[onclick],[tabindex],'+
    roles.map(role=>'[role="'+role+'"]').join(',');
  const candidates=new Set(document.querySelectorAll(selector));
  // Some visual steppers expose only a focusable group; +/- icons are aria-hidden.
  // Recover only paired, pointer-operated icons around an observed numeric value,
  // never arbitrary hidden elements or decorative icons inside real buttons.
  const direction=e=>{
    const tokens=String(e.getAttribute('class')||'').toLowerCase().split(/[^a-z]+/);
    const text=e.textContent.trim();
    if (text==='+' || tokens.some(t=>['plus','plusline','increment','increase','add'].includes(t))) return 1;
    if (['−','-','–'].includes(text) || tokens.some(t=>['minus','minusline','decrement','decrease'].includes(t))) return -1;
    return 0;
  };
  for (const group of document.querySelectorAll('[tabindex],[role="group"]')) {
    if (!rendered(group) || group.closest('[aria-hidden="true"],button,a') ||
        group.matches('[role="button"]')) continue;
    const children=[...group.children], icons=children.filter(e=>direction(e) &&
      rendered(e) && getComputedStyle(e).cursor==='pointer' && e.getBoundingClientRect().width>0);
    const number=children.find(e=>!icons.includes(e) && /^\d+$/.test(e.textContent.trim()));
    if (!number || !icons.some(e=>direction(e)===1) || !icons.some(e=>direction(e)===-1)) continue;
    const label=group.getAttribute('aria-label') || [...group.parentElement.children]
      .filter(e=>e!==group && visible(e)).map(e=>name(e)).filter(Boolean).join(' ').trim();
    if (!label || label.length>150) continue;
    const value=number.textContent.trim();
    for (const icon of icons) {
      steppers.set(icon,{label:(direction(icon)>0?'Increase ':'Decrease ')+label,
        context:label,current_value:value,stepper:label,control_node:identity(group)});
      candidates.add(icon);
    }
    candidates.delete(group);
  }
  for (const e of document.querySelectorAll('div,span')) {
    const r=e.getBoundingClientRect();
    if(r.width>0 && r.height>0 && r.width<600 && r.height<160 && r.bottom>0 && r.top<innerHeight &&
      getComputedStyle(e).cursor==='pointer' && getComputedStyle(e.parentElement).cursor!=='pointer' &&
      !e.querySelector(selector)) candidates.add(e);
  }
  // Do not expose a container's text/center as a button when its real children act.
  for (const e of [...candidates]) {
    if ([...steppers.keys()].some(icon=>e!==icon && e.contains(icon))) {
      candidates.delete(e); continue;
    }
    if (e.matches('button,a,input,textarea,select,summary,[role="button"],[role="link"]')) continue;
    if (!e.hasAttribute('onclick') && !e.hasAttribute('role') &&
        [...e.querySelectorAll(selector)].some(child=>candidates.has(child))) candidates.delete(e);
  }
  const inferredName=e=>{
    // A visible search input can have neither a label nor a placeholder yet.
    // Keep it actionable using observed search semantics, not recommendation text.
    if (isSearchInput(e)) return 'Search query';
    const icon=e.querySelector('svg title,img[alt]');
    if(icon) return icon.textContent || icon.getAttribute('alt');
    const tokens=String(e.className).replace(/([a-z])([A-Z])/g,'$1 $2').toLowerCase().split(/[^a-z0-9]+/);
    const searchContext=e.closest('form,[role="search"]')?.querySelector('input');
    if (searchContext && tokens.includes('search')) {
      if (tokens.some(t=>['clear','clean','reset'].includes(t))) return 'Clear search';
      if (tokens.some(t=>['close','dismiss','cancel'].includes(t))) return 'Close search';
      if (tokens.some(t=>['btn','button','submit'].includes(t))) return 'Search';
    }
    if(e.href) {try {const u=new URL(e.href);return 'Link to '+u.hostname+u.pathname;}catch{}}
    return '';
  };
  const role = e => {
    const explicit=e.getAttribute('role');
    if (roles.includes(explicit)) return explicit;
    if (e.tagName==='BUTTON' || e.tagName==='SUMMARY') return 'button';
    if (e.tagName==='A') return 'link';
    if (e.tagName==='SELECT') return 'combobox';
    if (e.tagName==='TEXTAREA' || e.isContentEditable) return 'textbox';
    if (e.tagName==='INPUT') {
      if (['checkbox','radio'].includes(e.type)) return e.type;
      if (['button','submit','reset','image'].includes(e.type)) return 'button';
      if (e.type==='search') return 'searchbox';
      if (e.type==='number') return 'spinbutton';
      if (['text','email','url','tel'].includes(e.type)) return 'textbox';
    }
    return candidates.has(e) ? 'button' : null;
  };
  cache.pageKey=()=>[performance.timeOrigin,location.href,scrollX,scrollY,innerWidth,innerHeight,
    [...document.querySelectorAll('input,textarea,select')].filter(safe)
      .map(e=>[identity(e),e.value,e.checked,e.selectedIndex,e.disabled,e.readOnly])];
  cache.guard=e=>{
    if (!e?.isConnected || !visible(e)) return null;
    const scope=e.closest('form,dialog,[role="dialog"],article,li,tr,[role="row"]') || e.parentElement;
    return [identity(e),role(e),name(e),e.value??null,e.checked??null,e.selectedIndex??null,
      e.readOnly??null,e.matches(':disabled'),e.getAttribute('aria-disabled'),
      e.getAttribute('aria-expanded'),e.getAttribute('aria-checked'),e.getAttribute('aria-selected'),
      e.getAttribute('href'),scope?.innerText?.slice(0,6000)||''];
  };
  const sensitivePattern=/password|passcode|one-time-code|cc-number|cc-csc|cc-exp|passport|social security|full name|guest name|contact name|phone|telephone|email|street-address|密码|验证码|护照|证件|身份证|卡号|手机号|电话号码|邮箱|姓名|联系人/i;
  const sensitive_fields=[...document.querySelectorAll('input,textarea,[contenteditable="true"]')]
    .filter(e=>e.type!=='hidden' && visible(e) && e.getBoundingClientRect().width>0 &&
      (['password','email','tel'].includes(e.type) || sensitivePattern.test(
        [name(e),e.name,e.id,e.autocomplete].join(' ')))).length;
  const actions=[], controls=[], emittedSteppers=new Set();
  const isSearchInput=e=>e.tagName==='INPUT' &&
    (e.type==='search' || e.getAttribute('role')==='searchbox' ||
      /search/i.test([e.id,e.name,e.className,e.closest('form')?.id,e.closest('form')?.className].join(' ')));
  const searchTarget=e=>{
    // Never associate by screen proximity or by a global Search label alone.
    const scope=e.form || e.closest('form,[role="search"]');
    if (!scope) return null;
    const fields=[...scope.querySelectorAll('input')].filter(x=>safe(x) && visible(x) && isSearchInput(x));
    return fields.length===1 ? fields[0] : null;
  };
  for (const e of candidates) {
    if (!safe(e) || !visible(e) || e.matches(':disabled') || e.closest('[aria-disabled="true"]')) continue;
    const r=e.getBoundingClientRect(), x=r.x+r.width/2, y=r.y+r.height/2, rname=role(e);
    if (!rname || r.width<=0 || r.height<=0 || x<0 || y<0 || x>=innerWidth || y>=innerHeight) continue;
    if (rname==='gridcell' && e.querySelector('button,[role="button"]')) continue;
    const stepper=steppers.get(e);
    const label=stepper?.label||name(e)||inferredName(e);
    if (!label) continue;
    if (!e.contains(document.elementFromPoint(x,y))) continue;
    const base={node:identity(e),role:rname,label,...(stepper||{}),
      href:e.href||null,rect:{x:r.x,y:r.y,w:r.width,h:r.height}};
    for (const key of ['checked','selected','expanded']) {
      const value=e.getAttribute('aria-'+key);
      if (value!==null) base[key]=value;
    }
    if (['checkbox','radio'].includes(e.type)) base.checked=String(e.checked);
    if (!stepper || !emittedSteppers.has(stepper.control_node)) {
      controls.push({node:stepper?.control_node||base.node,role:stepper?'spinbutton':base.role,
        label:stepper?.context||base.label,value:stepper?.current_value ?? (e.tagName==='SELECT' ?
        [...e.selectedOptions].map(o=>o.label).join(', ') : e.value??''),
        checked:base.checked??'',selected:base.selected??'',expanded:base.expanded??''});
      if(stepper) emittedSteppers.add(stepper.control_node);
    }
    if (e.tagName==='SELECT') {
      for (const o of e.options) if (!o.selected && !o.disabled && !o.closest('optgroup[disabled]'))
        actions.push({...base,kind:'select',value:o.value,
          current_value:[...e.selectedOptions].map(o=>o.label).join(', '),label:base.label+' → '+o.label});
    } else {
      const editable=!e.readOnly && e.getAttribute('aria-readonly')!=='true' &&
        (['textbox','searchbox','spinbutton'].includes(rname) ||
          (rname==='combobox' && ['INPUT','TEXTAREA'].includes(e.tagName)));
      const value='value' in e ? String(e.value) :
        e.isContentEditable || rname==='combobox' ? e.innerText.trim() : '';
      const target=!editable && /^(search|搜索|搜一下|查询)$/i.test(label.trim()) ? searchTarget(e) : null;
      actions.push({...base,kind:editable?'fill':'click',value,
        ...(editable && isSearchInput(e) ? {search_input:true} : {}),
        ...(target ? {search_input_node:identity(target)} : {})});
      if (editable) actions.push({...base,kind:'click',value,label:'Open '+base.label});
      if (editable && e.tagName==='INPUT' && value &&
          (e.type==='search' || /search/i.test([e.id,e.name,e.className,e.closest('form')?.id,e.closest('form')?.className].join(' '))))
        actions.push({...base,kind:'press',value,key:'Enter',search_input_node:base.node,
          label:'Search with Enter: '+base.label});
    }
  }
  const words=[], walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
  const range=document.createRange(); let node,length=0;
  while ((node=walker.nextNode()) && length<6000) {
    const value=node.textContent.trim(), parent=node.parentElement;
    if (!value || !parent || parent.closest('script,style,noscript,template') || !visible(parent)) continue;
    range.selectNodeContents(node); const r=range.getBoundingClientRect();
    if (r.width>0 && r.height>0 && r.bottom>0 && r.top<innerHeight && r.right>0 && r.left<innerWidth) {
      words.push(value); length+=value.length;
    }
  }
  const text=words.join('\n').slice(0,6000), height=document.documentElement.scrollHeight;
  const page_key=cache.pageKey(), guards={};
  for (const a of actions) if (!(a.node in guards)) guards[a.node]=cache.guard(cache.nodes.get(a.node));
  const semantics=actions.map(({rect,...action})=>action);
  const marker=[performance.timeOrigin,location.href,scrollX,scrollY,innerWidth,innerHeight,
    document.title,text,semantics,page_key[6]];
  const omitted_actions=Math.max(0,actions.length-250);
  actions.splice(250);
  actions.forEach((a,i)=>a.id='e'+(i+1));
  if (scrollY+innerHeight<height-2) actions.push({id:'scroll_down',kind:'scroll',label:'Scroll down',delta:560});
  if (scrollY>0) actions.push({id:'scroll_up',kind:'scroll',label:'Scroll up',delta:-560});
  actions.push({id:'wait',kind:'wait',label:'Wait for the page to update'});
  return {url:location.href,title:document.title,w:innerWidth,h:innerHeight,text,
    scroll:{y:scrollY,height},actions,controls,sensitive_fields,marker,page_key,guards,omitted_actions};
})()
