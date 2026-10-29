/* Exact budget-dependent antichains on an explicitly augmented course example. */
(function(root){
'use strict';
const base=typeof module!=='undefined'&&module.exports?require('./paper_engine.js'):root.KReach;
function reachSet(index,v,limit,reverse){
 const row=index.rank[v],out=[];
 for(let j=0;j<index.cover.length;j++){
  const code=reverse?index.codes[j][row]:index.codes[row][j];
  if(code>0&&code<=limit)out.push(index.cover[j]);
 }
 return out;
}
function antichain(index,candidates,limit,reverse){
 const sets=new Map(candidates.map(v=>[v,reachSet(index,v,limit,reverse)]));
 const order=[...candidates].sort((a,b)=>sets.get(b).length-sets.get(a).length||a-b),kept=[],removed=[];
 for(const child of order){
  const parent=kept.find(v=>sets.get(child).every(x=>sets.get(v).includes(x)));
  if(parent!==undefined)removed.push({child,parent});else kept.push(child);
 }
 return {kept:kept.sort((a,b)=>a-b),removed,sets:Object.fromEntries(sets)};
}
function run(g,s,t,k){
 const index=base.buildIndex(g,k),rs=index.rank[s],rt=index.rank[t];
 const caseId=rs>=0?(rt>=0?1:2):(rt>=0?3:4),local=(rs<0?1:0)+(rt<0?1:0),limit=3-local;
 const sources=rs>=0?[s]:index.a[s],targets=rt>=0?[t]:index.r[t];
 const out=rs>=0?{kept:sources,removed:[],sets:{}}:antichain(index,sources,limit,false);
 const incoming=rt>=0?{kept:targets,removed:[],sets:{}}:antichain(index,targets,limit,true);
 function evaluate(a,b){
  if(s===t)return {answer:true,probes:0};
  let probes=0,pair=null;
  for(const u of a)for(const v of b){
   probes++;pair={u,v};const code=index.codes[index.rank[u]][index.rank[v]];
   if(code>0&&code<=limit)return{answer:true,probes,pair,code};
  }
  return{answer:false,probes,pair};
 }
 const raw=evaluate(sources,targets),pruned=evaluate(out.kept,incoming.kept);
 return{index,caseId,budget:k-local,limit,sources,targets,out,incoming,raw,pruned};
}
const api={reachSet,antichain,run};
if(typeof module!=='undefined'&&module.exports)module.exports=api;
root.ThresholdDominance=api;
})(typeof window!=='undefined'?window:globalThis);

