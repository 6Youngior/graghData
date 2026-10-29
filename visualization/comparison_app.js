/* Deterministic motion timeline shared by the interactive view and video export. */
(function () {
'use strict';
const examples=DATA.comparisonExamples, clamp=x=>Math.max(0,Math.min(1,x));
const ease=x=>{x=clamp(x);return x*x*(3-2*x);};
const SETUP=1.1, PRUNE=2.0, HOLD=1.7, START=SETUP+PRUNE;
let current=examples[0],position=0,motion=null,raf=null,elapsed=0;
let traces={baseline:ComparisonTrace.trace(current,false),pruned:ComparisonTrace.trace(current,true)};
const total=()=>Math.max(traces.baseline.length,traces.pruned.length);
const duration=(pace=.65)=>START+total()*pace+HOLD;

function pause(){
 if(raf!==null)cancelAnimationFrame(raf);
 raf=null;$('cmp-play').textContent='播放对比';
}
function ys(n){
 const gap=n>1?Math.min(80,252/(n-1)):0;
 return Array.from({length:n},(_,i)=>160-gap*(n-1)/2+gap*i);
}
function text(parent,x,y,value,cls,anchor='middle'){
 parent.append(svgElement('text',{x,y,class:cls,'text-anchor':anchor},value));
}
function markerFor(svg,id,color){
 const defs=svgElement('defs',{}),m=svgElement('marker',{id,viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:5,markerHeight:5,orient:'auto'});
 m.append(svgElement('path',{d:'M0 0L10 5L0 10z',fill:color}));
 defs.append(m);svg.append(defs);
}
function geometry(a,b){
 const dx=b.x-a.x,dy=b.y-a.y;
 const start=Math.min(a.w/Math.abs(dx),a.h/Math.abs(dy));
 const end=Math.min(b.w/Math.abs(dx),b.h/Math.abs(dy));
 return {x1:a.x+dx*start,y1:a.y+dy*start,x2:b.x-dx*end,y2:b.y-dy*end};
}
function edge(svg,a,b,cls,id,opacity=1){
 const g=geometry(a,b);
 const path=svgElement('path',{d:'M'+g.x1+','+g.y1+'L'+g.x2+','+g.y2,class:cls,'marker-end':'url(#'+id+')',opacity});
 svg.append(path);return {path,...g};
}
function layout(nodes,prune){
 const raw=ys(nodes.length),kept=nodes.filter(v=>v.kept),compact=ys(kept.length);
 let index=0;
 return nodes.map((node,i)=>{
  const drop=node.kept?0:ease((prune-.08-i*.025)/.7);
  const y=node.kept?raw[i]+(compact[index++]-raw[i])*ease(prune):raw[i];
  return {y,opacity:1-drop,drop};
 });
}
function context(method,count){
 const sequence=traces[method],moving=motion&&motion.phase==='query'&&count<sequence.length;
 return {moving,pair:moving?sequence[count]:count?sequence[count-1]:null,
  fraction:moving?motion.fraction:1,done:count===sequence.length};
}
function graphFor(method,count){
 const pruned=method==='pruned',svg=$('cmp-'+method+'-graph'),color=pruned?'#176b59':'#245c91';
 const prune=pruned?(motion?motion.prune:1):0,reveal=motion?motion.reveal:1;
 svg.replaceChildren();
 const normal='cmp-'+method+'-arrow',active='cmp-'+method+'-active';
 markerFor(svg,normal,'#94a5b3');markerFor(svg,active,color);
 const sy=layout(current.sources,prune),ty=layout(current.targets,prune);
 const s={x:44,y:160,w:32,h:21},t={x:516,y:160,w:32,h:21};
 const {pair,moving,fraction}=context(method,count);
 text(svg,188,13,'N⁺(s)','symbol');text(svg,372,13,'N⁻(t)','symbol');
 current.sources.forEach((node,i)=>{
  edge(svg,s,{x:188,y:sy[i].y,w:29,h:15},'endpoint-edge',normal,sy[i].opacity*ease(reveal));
 });
 current.targets.forEach((node,i)=>{
  edge(svg,{x:372,y:ty[i].y,w:29,h:15},t,'endpoint-edge',normal,ty[i].opacity*ease(reveal));
 });
 if(pair){
  const a={x:188,y:sy[pair.row].y,w:29,h:15},b={x:372,y:ty[pair.col].y,w:29,h:15};
  const accepted=pair.accepted&&(!moving||fraction>.83);
  edge(svg,s,a,'candidate-edge',active);
  edge(svg,b,t,'candidate-edge',active);
  const line=edge(svg,a,b,accepted?'accepted-edge':'current-edge',active);
  if(moving){
   line.path.setAttribute('stroke-dashoffset',-fraction*21);
   const p=ease(fraction),x=line.x1+(line.x2-line.x1)*p,y=line.y1+(line.y2-line.y1)*p;
   svg.append(svgElement('circle',{cx:x,cy:y,r:11,fill:color,opacity:.12}));
   svg.append(svgElement('circle',{cx:x,cy:y,r:4.5,fill:color,stroke:'#fff','stroke-width':1.5}));
  }
  const label=moving&&fraction<=.83?'d ≤ '+current.budget+' ?':'d '+(pair.accepted?'≤':'>')+' '+current.budget;
  text(svg,280,(a.y+b.y)/2-13,label,'distance-label');
 }
 function nodes(values,positions,x){
  values.forEach((node,i)=>{
   const revealNode=ease((reveal*1.6-.06*i)/.55);
   const opacity=positions[i].opacity*revealNode;
   if(opacity<.002)return;
   const selected=pair&&((x===188?pair.row:pair.col)===i);
   const group=svgElement('g',{transform:'translate('+x+','+positions[i].y+')',opacity});
   group.append(svgElement('rect',{x:-29,y:-15,width:58,height:30,rx:4,class:'core-node'+(selected?' current-node':'')+(positions[i].drop>0?' removing-node':'')}));
   text(group,0,5,node.id,'node-id');
   if(positions[i].drop>.08)group.append(svgElement('path',{d:'M-21 0L21 0',class:'remove-mark',opacity:clamp(positions[i].drop*3)}));
   svg.append(group);
  });
 }
 nodes(current.sources,sy,188);nodes(current.targets,ty,372);
 for(const [node,id,label]of [[s,current.source,'s'],[t,current.target,'t']]){
  const group=svgElement('g',{opacity:ease(reveal*2)});
  group.append(svgElement('rect',{x:node.x-32,y:node.y-21,width:64,height:42,rx:4,class:'endpoint-node'}));
  text(group,node.x,node.y+6,id,'endpoint-id');text(group,node.x,node.y-33,label,'endpoint-symbol');svg.append(group);
 }
}
function matrixFor(method,count){
 const sequence=traces[method],prune=method==='pruned'?(motion?motion.prune:1):0;
 const seen=new Map(sequence.slice(0,count).map((p,i)=>[p.row+'-'+p.col,{...p,step:i+1}]));
 const {pair,moving,fraction}=context(method,count);
 $('cmp-'+method+'-matrix').innerHTML='<table aria-label="候选核心点对"><thead><tr><th>u ∖ v</th>'+
 current.targets.map(v=>'<th>'+v.id+'</th>').join('')+'</tr></thead><tbody>'+
 current.sources.map((u,row)=>'<tr><th>'+u.id+'</th>'+current.targets.map((v,col)=>{
  const p=seen.get(row+'-'+col),dropped=prune>.1&&(!u.kept||!v.kept);
  let cls=dropped?'dropped':'';
  if(p)cls+=' visited'+(p.accepted?' accepted':'');
  const selected=pair&&pair.row===row&&pair.col===col;
  if(selected)cls+=moving?' scanning':' current';
  const value=p?(p.accepted?'✓':p.step):selected&&moving?'·':'';
  const style=selected&&moving?' style="--scan:'+Math.sin(fraction*Math.PI).toFixed(3)+'"':'';
  return '<td class="'+cls+'"'+style+' title="'+u.id+' → '+v.id+(dropped?'：已剪枝':'')+'">'+value+'</td>';
 }).join('')+'</tr>').join('')+'</tbody></table>';
}
function methodFor(method){
 const count=Math.min(position,traces[method].length),state=context(method,count),done=state.done;
 $('cmp-'+method+'-count').textContent=count;
 const pair=state.pair;
 $('cmp-'+method+'-pair').textContent=pair?
  '检查 '+current.sources[pair.row].id+' → '+current.targets[pair.col].id:
  motion&&motion.phase==='pruning'&&method==='pruned'?'按当前预算约简边界':'等待查询';
 const status=$('cmp-'+method+'-state');
 status.textContent=done?(current.answer?'已找到 · 可达':'已完成 · 不可达'):
  motion&&motion.phase==='pruning'&&method==='pruned'?'离线剪枝':pair?'检查中':'';
 status.className=done&&!current.answer?'finished-no':'';
 const witness=$('cmp-'+method+'-path');
 witness.textContent=done?(current.answer?'路径：'+current[method].path.join(' → '):'所有保留候选均不满足预算'):'\u00a0';
 witness.className='witness-path'+(done&&current.answer?' found':'');
 graphFor(method,count);matrixFor(method,count);
 return done;
}
function render(){
 const a=methodFor('baseline'),b=methodFor('pruned');
 $('cmp-seek').value=position;$('cmp-progress').textContent=position+' / '+total();
 $('cmp-back').disabled=position===0;$('cmp-next').disabled=position===total();
 const raw=traces.baseline.length,cut=traces.pruned.length;
 $('cmp-outcome').textContent=a&&b?(raw===cut?
  '两种方法均检查 '+raw+' 次，查询结果相同。':
  '核心查找 '+raw+' → '+cut+' 次，两种方法都返回'+(current.answer?'可达':'不可达')+'。'):
  b?'剪枝后'+(current.answer?'已找到可达路径':'已完成判定')+'；K-Reach 继续检查候选。':
  motion&&motion.phase==='pruning'?'离线阶段：消去当前预算下的冗余边界候选。':'';
}
function renderTime(seconds,pace=.65){
 const t=Math.max(0,seconds);
 if(t<SETUP){
  position=0;motion={phase:'setup',prune:0,reveal:clamp(t/SETUP),fraction:0};
 }else if(t<START){
  position=0;motion={phase:'pruning',prune:clamp((t-SETUP)/PRUNE),reveal:1,fraction:0};
 }else{
  const work=(t-START)/pace;
  position=Math.min(total(),Math.floor(work+1e-7));
  motion={phase:position===total()?'result':'query',prune:1,reveal:1,fraction:clamp(work-position)};
 }
 render();
}
function select(id){
 pause();current=examples.find(e=>e.id===id)||examples[0];position=0;motion=null;elapsed=0;
 traces={baseline:ComparisonTrace.trace(current,false),pruned:ComparisonTrace.trace(current,true)};
 $('cmp-example').value=current.id;$('cmp-seek').max=total();
 $('cmp-query').textContent='s = '+current.source+'  →  t = '+current.target;
 $('cmp-budget').textContent='k = '+current.k+'，核心预算 = '+current.budget;
 $('cmp-baseline-boundary').textContent='出边界 '+current.sources.length+' · 入边界 '+current.targets.length;
 $('cmp-pruned-boundary').textContent='出边界 '+current.sources.length+' → '+current.sources.filter(v=>v.kept).length+
  ' · 入边界 '+current.targets.length+' → '+current.targets.filter(v=>v.kept).length;
 render();
}
function seek(value){
 pause();position=Math.max(0,Math.min(total(),Math.round(value)));motion=null;
 elapsed=position?START+position*(+$('cmp-pace').value/1000):0;render();
}
function play(){
 if(raf!==null){pause();return;}
 const pace=+$('cmp-pace').value/1000;
 if(position===total())elapsed=0;
 const from=elapsed,start=performance.now();
 $('cmp-play').textContent='暂停';
 function tick(now){
  elapsed=from+(now-start)/1000;renderTime(elapsed,pace);
  if(elapsed>=duration(pace)){pause();return;}
  raf=requestAnimationFrame(tick);
 }
 raf=requestAnimationFrame(tick);
}
examples.forEach(e=>{const option=document.createElement('option');option.value=e.id;option.textContent=e.title;$('cmp-example').append(option);});
document.querySelector('.figure-legend').before(document.querySelector('.comparison-transport'));
$('cmp-example').onchange=()=>select($('cmp-example').value);
$('cmp-play').onclick=play;$('cmp-reset').onclick=()=>seek(0);
$('cmp-back').onclick=()=>seek(position-1);$('cmp-next').onclick=()=>seek(position+1);
$('cmp-seek').oninput=()=>seek(+$('cmp-seek').value);$('cmp-pace').onchange=()=>seek(position);
document.addEventListener('viewchange',pause);
document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});
document.addEventListener('keydown',e=>{
 if($('comparison').hidden||e.target.matches('select,input,button,video'))return;
 if(e.code==='ArrowRight'){e.preventDefault();seek(position+1);}
 if(e.code==='ArrowLeft'){e.preventDefault();seek(position-1);}
 if(e.code==='Space'){e.preventDefault();play();}
});
$('open-video').onclick=()=>{$('video-dialog').showModal();$('comparison-video').play().catch(()=>{});pause();};
$('close-video').onclick=()=>{$('comparison-video').pause();$('video-dialog').close();};
$('video-dialog').addEventListener('close',()=>$('comparison-video').pause());
$('cmp-fullscreen').onclick=async()=>{
 if(document.fullscreenElement)await document.exitFullscreen();
 else await $('comparison').requestFullscreen();
};
document.addEventListener('fullscreenchange',()=>{
 $('cmp-fullscreen').textContent=document.fullscreenElement?'退出全屏':'全屏演示';
});
window.QueryComparison={select,seek,pause,renderTime,duration,
 state:()=>({example:current.id,position,total:total(),phase:motion?motion.phase:'still',playing:raf!==null})};
select(current.id);
})();

