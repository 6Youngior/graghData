/* The displayed sequence uses the same nested boundary order as the query kernel. */
(function(root){
'use strict';
function trace(example,pruned){
 const pairs=[];
 for(let row=0;row<example.sources.length;row++){
  if(pruned&&!example.sources[row].kept)continue;
  for(let col=0;col<example.targets.length;col++){
   if(pruned&&!example.targets[col].kept)continue;
   const code=example.codes[row][col],accepted=code===1;
   pairs.push({row,col,code,accepted});
   if(accepted)return pairs;
  }
 }
 return pairs;
}
const api={trace};
if(typeof module!=='undefined'&&module.exports)module.exports=api;
root.ComparisonTrace=api;
})(typeof window!=='undefined'?window:globalThis);
