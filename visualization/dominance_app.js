/* Teaching view for the course's budget reversal counterexample. */
(function(){
const model=DATA.dominanceGraph;let target=6,stage=0;
const names=values=>'{'+values.map(v=>model.nodes[v].name).join(', ')+'}';
function paint(result){
 const svg=$('dom-graph');svg.replaceChildren();marker(svg,'arrow-dominance');
 const xy=model.nodes.map(n=>({x:45+n.x*70,y:128-n.y*68}));
 for(const[u,v]of model.edges){
  const p=xy[u],q=xy[v],dx=q.x-p.x,dy=q.y-p.y,l=Math.hypot(dx,dy),added=u===2&&v===3;
  let d=`M${p.x+dx*19/l},${p.y+dy*19/l}L${q.x-dx*23/l},${q.y-dy*23/l}`;
  if(added)d=`M${p.x+13},${p.y+13}Q${p.x+58},${p.y+29} ${q.x+4},${q.y-23}`;
  const edge=svgElement('path',{d,class:'edge'+(added?' dom-added':''),'marker-end':'url(#arrow-dominance)'});
  svg.append(edge);
 }
 const removed=new Set(result.out.removed.map(x=>x.child));
 model.nodes.forEach((n,i)=>{
  let cls='vertex';if(model.cover.includes(i))cls+=' core';
  if(i===2||i===target)cls+=' endpoint';
  if(stage>=1&&removed.has(i))cls+=' dom-removed';
  if(stage>=1&&result.out.kept.includes(i))cls+=' dom-kept';
  const node=svgElement('g',{class:cls,transform:`translate(${xy[i].x},${xy[i].y})`});
  node.append(svgElement('circle',{r:18}));node.append(svgElement('text',{'text-anchor':'middle','dominant-baseline':'central'},n.name));svg.append(node);
 });
}
function render(){
 const result=ThresholdDominance.run(model,2,target,3),b=result.budget;
 paint(result);
 $('dom-budget-title').textContent=`预算 ${b}：比较 R${b}(b) 与 R${b}(d)`;
 $('dom-case-label').textContent='Case '+result.caseId;
 $('dom-sets').innerHTML='<table class="dom-set-table"><thead><tr><th>边界候选</th><th>预算内可达核心集合</th><th>处理</th></tr></thead><tbody>'+
  [1,3].map(v=>`<tr class="${stage>=1?(result.out.kept.includes(v)?'dom-keep-row':'dom-drop-row'):''}"><td>${model.nodes[v].name}</td><td>${names(result.out.sets[v])}</td><td>${stage>=1?(result.out.kept.includes(v)?'保留':'被包含，消去'):'待比较'}</td></tr>`).join('')+'</tbody></table>';
 const dropped=result.out.removed[0],child=model.nodes[dropped.child].name,parent=model.nodes[dropped.parent].name;
 $('dom-relation').textContent=`R${b}(${child}) ⊆ R${b}(${parent})`;
 $('dom-why').textContent=`保留 ${parent}，已经覆盖 ${child} 在当前预算内能贡献的全部核心目标。`;
 $('dom-budget').textContent=b;$('dom-raw-probes').textContent=stage===2?result.raw.probes:'—';
 $('dom-cut-probes').textContent=stage===2?result.pruned.probes:'—';
 $('dom-answer').textContent=stage===2?(result.pruned.answer?'TRUE':'FALSE'):'待判定';
 const messages=[
  `查询 c→${model.nodes[target].name}：Case ${result.caseId}，起点边界仍是 {b,d}，剩余预算为 ${b}。`,
  `在预算 ${b} 内，${child} 可达的核心目标均由 ${parent} 覆盖；消去 ${child}，保留 ${parent}。`,
  `沿用四类查询，核心查找由 ${result.raw.probes} 次变为 ${result.pruned.probes} 次，答案均为 ${result.pruned.answer?'True':'False'}。`
 ];
 $('dom-message').textContent=messages[stage];$('dom-progress').textContent=`步骤 ${stage+1} / 3`;
}
function choose(value){target=value;stage=0;$('dom-case3').classList.toggle('primary',target===6);$('dom-case4').classList.toggle('primary',target===7);render();}
$('dom-case3').onclick=()=>choose(6);
$('dom-case4').onclick=()=>choose(7);
$('dom-reset').onclick=()=>{stage=0;render();};
$('dom-back').onclick=()=>{stage=Math.max(0,stage-1);render();};
$('dom-next').onclick=()=>{stage=Math.min(2,stage+1);render();};
render();
})();
