const fs=require('fs'),path=require('path'),assert=require('assert');
const K=require('./paper_engine.js');
const graph=JSON.parse(fs.readFileSync(path.join(__dirname,'paper_graph.json'),'utf8'));
const fixtures=JSON.parse(fs.readFileSync(path.join(__dirname,'paper_fixtures.json'),'utf8'));
for(const q of fixtures)for(const codec of ['csr','dense','adaptive']){
  const result=K.trace(graph,q.s,q.t,q.k,codec).frames.at(-1);
  assert.equal(result.answer,q.answer,JSON.stringify({q,codec}));
  assert.equal(result.caseId,q.cases,JSON.stringify({q,codec}));
  assert.equal(result.probes,q.probes,JSON.stringify({q,codec}));
  assert.equal(result.comparisons,q.comparisons[codec],JSON.stringify({q,codec}));
}
console.log(`PASS: ${fixtures.length*3} codec queries match Python answers, all four cases, probes, and binary comparisons.`);
fs.writeFileSync(path.join(__dirname,'../data/results/paper_js_check.json'),JSON.stringify({status:'PASS',fixture_queries:fixtures.length,codec_queries:fixtures.length*3,checks:['answers','four cases','core probes','binary comparisons']},null,2));
