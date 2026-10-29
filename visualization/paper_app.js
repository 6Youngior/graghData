'use strict';
const DATA=window.PROJECT_DATA,$=id=>document.getElementById(id),graph=DATA.graph,ns='http://www.w3.org/2000/svg';
let run=null,position=0,timer=null;
function svgElement(tag,attrs,text){const e=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;return e;}
function marker(svg,id){const defs=svgElement('defs',{}),m=svgElement('marker',{id,viewBox:'0 0 10 10',refX:8,refY:5,markerWidth:5,markerHeight:5,orient:'auto'});m.append(svgElement('path',{d:'M0 0L10 5L0 10z',fill:'#91a8b9'}));defs.append(m);svg.append(defs);}
function drawOriginal(frame){
  const svg=$('original-graph');svg.replaceChildren();marker(svg,'arrow-original');
  const xy=graph.nodes.map(n=>({x:45+n.x*70,y:128-n.y*68}));
  const s=+$('source').value,t=+$('target').value,active=new Set();
  if(frame.pair){if(!graph.cover.includes(s))active.add(`${s}-${frame.pair.u}`);if(!graph.cover.includes(t))active.add(`${frame.pair.v}-${t}`);}
  for(const[u,v]of graph.edges){const p=xy[u],q=xy[v],dx=q.x-p.x,dy=q.y-p.y,l=Math.hypot(dx,dy);svg.append(svgElement('path',{d:`M${p.x+dx*19/l},${p.y+dy*19/l}L${q.x-dx*23/l},${q.y-dy*23/l}`,class:'edge'+(active.has(`${u}-${v}`)?' active':''),'marker-end':'url(#arrow-original)'}));}
  graph.nodes.forEach((n,i)=>{let cls='vertex';if(graph.cover.includes(i))cls+=' core';if(i===s||i===t)cls+=' endpoint';if(frame.pair&&(i===frame.pair.u||i===frame.pair.v))cls+=' selected';const node=svgElement('g',{class:cls,transform:`translate(${xy[i].x},${xy[i].y})`});node.append(svgElement('circle',{r:18}));node.append(svgElement('text',{'text-anchor':'middle','dominant-baseline':'central'},n.name));svg.append(node);});
}
function drawIndex(frame){
  const svg=$('index-graph');svg.replaceChildren();marker(svg,'arrow-index');
  const xy=[{x:55,y:50},{x:235,y:50},{x:55,y:210},{x:235,y:210}],index=run.index,k=+$('k').value;
  for(let i=0;i<4;i++)for(let j=0;j<4;j++){
    const code=index.codes[i][j];if(!code||i===j)continue;
    const p=xy[i],q=xy[j],dx=q.x-p.x,dy=q.y-p.y,l=Math.hypot(dx,dy),selected=frame.pair&&frame.pair.u===index.cover[i]&&frame.pair.v===index.cover[j];
    const cls='edge'+(selected?(frame.answer===true?' accepted':frame.answer===false?' rejected':' active'):'');
    let d=`M${p.x+dx*19/l},${p.y+dy*19/l}L${q.x-dx*23/l},${q.y-dy*23/l}`;
    let lx=(p.x+q.x)/2+(-dy/l)*10,ly=(p.y+q.y)/2+(dx/l)*10;
    if(i===1&&j===0){d=`M${p.x-10},${p.y-17}Q145,-13 ${q.x+12},${q.y-19}`;lx=145;ly=13;}
    if(i===0&&j===3){lx+=12;ly-=8;}
    svg.append(svgElement('path',{d,class:cls,'marker-end':'url(#arrow-index)'}));
    svg.append(svgElement('text',{x:lx,y:ly,class:'weight','text-anchor':'middle'},code===1?'≤'+(k-2):String(code===2?k-1:k)));
  }
  index.cover.forEach((v,i)=>{const g=svgElement('g',{class:'vertex core'+(frame.pair&&(v===frame.pair.u||v===frame.pair.v)?' selected':''),transform:`translate(${xy[i].x},${xy[i].y})`});g.append(svgElement('circle',{r:18}));g.append(svgElement('text',{'text-anchor':'middle','dominant-baseline':'central'},graph.nodes[v].name));svg.append(g);});
  $('matrix').innerHTML='<table><thead><tr><th></th>'+index.cover.map(v=>`<th>${graph.nodes[v].name}</th>`).join('')+'</tr></thead><tbody>'+index.codes.map((row,i)=>'<tr><th>'+graph.nodes[index.cover[i]].name+'</th>'+row.map((c,j)=>{const selected=frame.pair&&frame.pair.u===index.cover[i]&&frame.pair.v===index.cover[j];const value=c?(c===1?'≤'+(k-2):c===2?k-1:k):'—';return`<td class="${!c?'zero ':''}${selected?'selected ':''}${selected&&frame.answer===false?'reject':''}"><strong>${value}</strong><small>${c.toString(2).padStart(2,'0')}</small></td>`;}).join('')+'</tr>').join('')+'</tbody></table>';
}
function stop(){if(timer)clearInterval(timer);timer=null;$('play').textContent='播放';}
function render(){
  const frame=run.frames[position];drawOriginal(frame);drawIndex(frame);
  $('case-value').textContent='Case '+frame.caseId;$('budget-value').textContent=frame.budget;$('probes-value').textContent=frame.probes;$('comparisons-value').textContent=frame.comparisons;$('step-message').textContent=frame.message;
  const decision=$('decision');decision.textContent=frame.answer===null?'逐步判定中':frame.answer?'TRUE · 接受':'FALSE · 拒绝';decision.className='pill'+(frame.answer===null?'':frame.answer?' yes':' no');
  $('progress').textContent=`步骤 ${position+1} / ${run.frames.length}`;
}
function rebuild(){stop();position=0;const s=+$('source').value,t=+$('target').value,k=+$('k').value;run=KReach.trace(graph,s,t,k,$('codec').value);const {a}=KReach.adjacency(graph),d=KReach.distances(a,s)[t];$('truth').textContent=`d(${graph.nodes[s].name}, ${graph.nodes[t].name}) = ${Number.isFinite(d)?d:'∞'}，k = ${k}；正确答案为 ${d<=k?'True':'False'}。`;render();}
function preset(s,t){$('source').value=s;$('target').value=t;$('k').value=3;rebuild();}
function next(){if(position<run.frames.length-1){position++;render();}else stop();}
graph.nodes.forEach((node,i)=>{for(const id of ['source','target']){const option=document.createElement('option');option.value=i;option.textContent=node.name;$(id).append(option);}});
$('source').value=2;$('target').value=5;
for(const id of ['source','target','k','codec'])$(id).onchange=rebuild;
$('case1').onclick=()=>preset(1,6);$('case2').onclick=()=>preset(3,7);$('case3').onclick=()=>preset(0,3);$('case4').onclick=()=>preset(2,5);$('negative').onclick=()=>preset(2,7);
$('reset').onclick=rebuild;$('back').onclick=()=>{stop();position=Math.max(0,position-1);render();};$('step').onclick=()=>{stop();next();};$('finish').onclick=()=>{stop();position=run.frames.length-1;render();};$('play').onclick=()=>{if(timer){stop();return;}if(position===run.frames.length-1)position=0;$('play').textContent='暂停';timer=setInterval(next,1050);render();};
document.querySelectorAll('.tab').forEach(tab=>tab.onclick=()=>{stop();document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active',t===tab));document.querySelectorAll('.view').forEach(v=>v.hidden=v.id!==tab.dataset.tab);document.dispatchEvent(new CustomEvent('viewchange',{detail:tab.dataset.tab}));});
document.addEventListener('keydown',e=>{if(e.target.matches('select,button')||$('algorithm').hidden)return;if(e.code==='ArrowRight'){e.preventDefault();stop();next();}if(e.code==='ArrowLeft'){e.preventDefault();stop();position=Math.max(0,position-1);render();}if(e.code==='Space'){e.preventDefault();$('play').click();}});
function stat(label,value,note){return`<div class="stat"><small>${label}</small><strong>${value}</strong><span>${note}</span></div>`;}
function rowHTML(row,c){return`<div class="row-details">原始节点 ID：<strong>${row.original}</strong>；覆盖内部行号：${row.row}<br>可达项 ${row.count.toLocaleString()} / ${c.toLocaleString()}，密度 ${(100*row.count/c).toFixed(2)}%<br>最终表示：<strong>${row.format}</strong></div><div class="savings"><div><span class="muted">稀疏行载荷估计</span><strong>${row.sparseBytes.toLocaleString()} B</strong></div><div><span class="muted">稠密行载荷</span><strong>${row.denseBytes.toLocaleString()} B</strong></div></div><p class="muted">前 24 个目标位置的两位类别：</p><div class="code-strip">${row.codes.join(' | ')}</div><p class="muted">前几个非零目标（核心 ID : 类别）：</p><div class="code-strip">${row.entries.map(x=>`${x[0]} : ${x[1]}`).join(' &nbsp; ')}</div>`;}
function storage(){const record=DATA.storage[$('storage-dataset').value],f=DATA.facts.datasets[$('storage-dataset').value],v=f.index_mib;$('storage-stats').innerHTML=stat('稀疏 CSR',v.csr.toFixed(2)+' MiB','目标 ID + 两位权重 + 偏移')+stat('全稠密',v.dense.toFixed(2)+' MiB','每个核心目标一个两位位置')+stat('最终自适应',v.adaptive.toFixed(2)+' MiB',f.mode==='sparse'?'整体回退为 CSR':`${f.dense_rows.toLocaleString()} 稠密行 / ${f.sparse_rows.toLocaleString()} 稀疏行`);$('dense-row').innerHTML=rowHTML(record.long,record.core);$('sparse-row').innerHTML=rowHTML(record.short,record.core);}
for(const [key,value]of Object.entries(DATA.storage)){const option=document.createElement('option');option.value=key;option.textContent=value.name;$('storage-dataset').append(option);}$('storage-dataset').onchange=storage;
$('result-table').innerHTML='<table class="result-table"><thead><tr><th>真实图</th><th>CSR MiB</th><th>Dense MiB</th><th>自适应 MiB</th><th>相对 CSR 加速</th></tr></thead><tbody>'+Object.entries(DATA.facts.datasets).map(([key,f])=>`<tr><td>${DATA.storage[key].name}</td><td>${f.index_mib.csr.toFixed(2)}</td><td>${f.index_mib.dense.toFixed(2)}</td><td class="best">${f.index_mib.adaptive.toFixed(2)}</td><td class="best">${f.geomean_speedup.toFixed(2)}×</td></tr>`).join('')+'</tbody></table>';
$('speed-chart').src=DATA.charts.speed;$('density-chart').src=DATA.charts.density;
storage();rebuild();

if(DATA.dominanceFacts){
 const f=DATA.dominanceFacts;
 $('result-table').innerHTML='<table class="result-table"><thead><tr><th>图数据</th><th>K-Reach 查找</th><th>剪枝后查找</th><th>加速比</th><th>额外空间 / KiB</th></tr></thead><tbody>'+
 Object.entries(f.datasets).map(([key,v])=>`<tr><td>${DATA.storage[key].name}</td><td>${v.raw_mean_probes.toFixed(2)}</td><td>${v.pruned_mean_probes.toFixed(2)}</td><td class="best">${v.pruning_speedup.toFixed(2)}×</td><td>${((v.boundary_pruned_bytes-v.boundary_raw_bytes)/1024).toFixed(1)}</td></tr>`).join('')+'</tbody></table>';
 $('speed-chart').src=DATA.charts.pruningSpeed;$('speed-chart').alt='相同核心编码下阈值剪枝的配对加速比及三种子范围';
 $('density-chart').src=DATA.charts.caseProbes;$('density-chart').alt='四类查询的原边界、单侧剪枝和双侧剪枝查找次数';
}
