/* K-Reach Algorithms 1–2, independently readable exact teaching implementation. */
(function(root){
  'use strict';
  function adjacency(g){
    const a=Array.from({length:g.nodes.length},()=>[]),r=a.map(()=>[]);
    for(const [u,v]of g.edges){a[u].push(v);r[v].push(u);}
    a.forEach(x=>x.sort((u,v)=>u-v));r.forEach(x=>x.sort((u,v)=>u-v));return{a,r};
  }
  function distances(a,s){
    const d=Array(a.length).fill(Infinity),q=[s];d[s]=0;
    for(let head=0;head<q.length;head++){const u=q[head];for(const v of a[u])if(!Number.isFinite(d[v])){d[v]=d[u]+1;q.push(v);}}
    return d;
  }
  function layout(codes){
    const c=codes.length,stride=Math.ceil(c/4),counts=codes.map(row=>row.filter(x=>x>0).length);
    const total=counts.reduce((s,v)=>s+v,0),isDense=counts.map(n=>stride<4*n+Math.ceil(n/4));
    const sparseEntries=counts.reduce((s,n,i)=>s+(isDense[i]?0:n),0),denseRows=isDense.filter(Boolean).length;
    const bytes={csr:8*(c+1)+4*total+Math.ceil(total/4),dense:c*stride+8,
      hybrid:8*(c+1)+4*c+denseRows*stride+4*sparseEntries+Math.ceil(sparseEntries/4)};
    const mode=bytes.hybrid<=Math.min(bytes.csr,bytes.dense)?2:(bytes.csr<=bytes.dense?0:1);
    return{mode,bytes,isDense,counts,stride};
  }
  function buildIndex(g,k){
    if(!Number.isInteger(k)||k<2)throw new Error('演示索引要求固定 k ≥ 2');
    const {a,r}=adjacency(g),cover=[...g.cover],rank=Array(g.nodes.length).fill(-1);
    cover.forEach((v,i)=>rank[v]=i);
    for(const [u,v]of g.edges)if(rank[u]<0&&rank[v]<0)throw new Error('S 必须覆盖每条边');
    const dist=cover.map(s=>distances(a,s));
    const codes=cover.map((u,i)=>cover.map(v=>dist[i][v]>k?0:(dist[i][v]<=k-2?1:(dist[i][v]===k-1?2:3))));
    return{a,r,cover,rank,dist,codes,layout:layout(codes),k};
  }
  function decode(index,u,v,codec){
    const row=index.rank[u],col=index.rank[v];let dense=codec==='dense';
    if(codec==='adaptive'){const l=index.layout;dense=l.mode===1||(l.mode===2&&l.isDense[row]);}
    if(dense)return{code:index.codes[row][col],comparisons:0,format:'两位稠密行',byte:Math.floor(col/4),bit:2*(col%4)};
    const ids=index.codes[row].flatMap((c,j)=>c?[j]:[]);let left=0,right=ids.length,comparisons=0;
    while(left<right){comparisons++;const middle=Math.floor((left+right)/2);if(ids[middle]<col)left=middle+1;else right=middle;}
    return{code:left<ids.length&&ids[left]===col?index.codes[row][col]:0,comparisons,format:'稀疏有序行',ids};
  }
  function trace(g,s,t,k,codec='adaptive'){
    const index=buildIndex(g,k),name=v=>g.nodes[v].name,rs=index.rank[s],rt=index.rank[t];
    const caseId=rs>=0?(rt>=0?1:2):(rt>=0?3:4),local=(rs<0?1:0)+(rt<0?1:0),limit=3-local;
    const sources=rs>=0?[s]:index.a[s],targets=rt>=0?[t]:index.r[t];
    let probes=0,comparisons=0;const frames=[];
    function frame(message,answer=null,pair=null,decoded=null){frames.push({message,answer,pair,decoded,
      probes,comparisons,caseId,local,budget:k-local,sourceCandidates:[...sources],targetCandidates:[...targets]});}
    frame(`端点分类：Case ${caseId}；先扣除 ${local} 跳，核心预算为 ${k-local}。`);
    if(s===t){frame('源点与目标点相同，零长度路径直接成立。',true);return{index,frames};}
    frame(`枚举核心候选：源侧 {${sources.map(name).join(', ')||'空'}}；目标侧 {${targets.map(name).join(', ')||'空'}}。`);
    for(const u of sources)for(const v of targets){
      const decoded=decode(index,u,v,codec);probes++;comparisons+=decoded.comparisons;
      const code=decoded.code,weight=code===1?k-2:(code===2?k-1:k);
      frame(`读取 (${name(u)}, ${name(v)})：${decoded.format}解出 ${code.toString(2).padStart(2,'0')}；`+
        (code?`核心距离${code===1?'≤':'='}${weight}，预算 ${k-local}。`:'超过 k 或不可达，继续下一候选。'),null,{u,v},decoded);
      if(code>0&&code<=limit){frame(`存在合法核心点对：端点 ${local} 跳 + 核心至多 ${weight} 跳 ≤ ${k}，接受。`,true,{u,v},decoded);return{index,frames};}
    }
    const previous=frames.at(-1);
    frame('全部核心候选检查完，均不满足剩余预算，拒绝。',false,previous.pair,previous.decoded);
    return{index,frames};
  }
  const api={adjacency,distances,layout,buildIndex,decode,trace};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  root.KReach=api;
})(typeof window!=='undefined'?window:globalThis);
