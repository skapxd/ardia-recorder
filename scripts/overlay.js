// Presentation layer injected with `ardia browse eval`: virtual pointer, highlight box,
// arrow, label and click pulse. It never intercepts clicks and removes itself with remove().
// marks(true) draws magenta squares in the page corners so window_capture can find the page;
// pointer(false) hides the pointer when the video is assembled from screenshots and the
// renderer animates it instead.
(() => {
  window.ardiaOverlay?.remove();
  const host = document.createElement('div');
  host.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:2147483647';
  document.documentElement.append(host);
  const root = host.attachShadow({mode:'closed'});
  root.innerHTML = `<style>
    .box,.tag,.pointer,.pulse{position:fixed;pointer-events:none}
    .box{border:3px solid #db263d;border-radius:7px;box-sizing:border-box}
    .tag{background:#b61630;color:white;font:600 17px/1.3 system-ui;padding:9px 13px;border-radius:6px}
    .pointer{width:22px;height:30px;top:0;left:0;filter:drop-shadow(0 2px 3px rgba(0,0,0,.35));transition:transform .8s cubic-bezier(.4,0,.2,1)}
    .pulse{width:24px;height:24px;margin:-12px;background:rgba(37,99,235,.35);border:2px solid rgba(37,99,235,.9);border-radius:50%;opacity:0}
    svg.lines{position:fixed;inset:0;width:100%;height:100%}
    .mark{position:fixed;width:16px;height:16px;background:#ff00ff}
  </style><div class="box"></div><svg class="lines"><defs><marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0 0L6 3L0 6Z" fill="#db263d"/></marker></defs><line stroke="#db263d" stroke-width="3" marker-end="url(#arrow)"/></svg><div class="tag"></div><svg class="pointer" viewBox="0 0 22 30"><path d="M2 2v22l5.5-5.2 3.6 8.4 3.7-1.6-3.6-8.2H19z" fill="#111" stroke="#fff" stroke-width="2" stroke-linejoin="round"/></svg><div class="pulse"></div>`;
  const get = s => root.querySelector(s);
  function point(selector, label) {
    const target = document.querySelector(selector);
    const r = target.getBoundingClientRect(), box = get('.box'), tag = get('.tag');
    Object.assign(box.style,{left:r.x-4+'px',top:r.y-4+'px',width:r.width+8+'px',height:r.height+8+'px'});
    for(const el of root.querySelectorAll('.box,.tag,svg.lines'))el.style.visibility='';
    tag.textContent = label;
    const x = Math.max(8,Math.min(innerWidth-tag.offsetWidth-8,r.x+30)), y = r.bottom+70;
    Object.assign(tag.style,{left:x+'px',top:y+'px'});
    const line=get('line');
    for(const [k,v] of Object.entries({x1:x+24,y1:y,x2:r.x+Math.min(32,r.width/2),y2:r.bottom+7}))line.setAttribute(k,v);
    get('.pointer').style.transform='translate('+ (r.x+Math.min(30,r.width/2))+'px,'+(r.y+r.height/2)+'px)';
    tag.animate([{opacity:0,transform:'translateY(7px)'},{opacity:1,transform:'translateY(0)'}],{duration:300});
    return {x: r.x+Math.min(30,r.width/2), y: r.y+r.height/2};
  }
  function marks(on) {
    root.querySelectorAll('.mark').forEach(m => m.remove());
    if (on) for (const pos of ['top:0;left:0','top:0;right:0','bottom:0;left:0','bottom:0;right:0']) {
      const m = document.createElement('div'); m.className = 'mark'; m.style.cssText = pos; root.append(m);
    }
  }
  function pointer(on) { get('.pointer').style.display = on ? '' : 'none'; }
  function pulse(e) {
    const ring=get('.pulse');
    Object.assign(ring.style,{left:e.clientX+'px',top:e.clientY+'px'});
    ring.animate([{opacity:1,transform:'scale(.4)'},{opacity:0,transform:'scale(3.5)'}],{duration:650});
  }
  document.addEventListener('click',pulse,true);
  function hide(){for(const el of root.querySelectorAll('.box,.tag,svg.lines'))el.style.visibility='hidden'}
  window.ardiaOverlay={point,hide,marks,pointer,remove(){document.removeEventListener('click',pulse,true);host.remove();delete window.ardiaOverlay}};
  return 'Overlay installed';
})()
