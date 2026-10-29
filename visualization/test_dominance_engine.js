const fs=require('fs'),path=require('path'),assert=require('assert'),D=require('./dominance_engine.js');
const graph=JSON.parse(fs.readFileSync(path.join(__dirname,'dominance_graph.json'),'utf8'));
const fixtures=JSON.parse(fs.readFileSync(path.join(__dirname,'dominance_fixtures.json'),'utf8'));
for(const q of fixtures){
 const r=D.run(graph,q.s,q.t,q.k);
 assert.equal(r.raw.answer,q.answer,JSON.stringify(q));
 assert.equal(r.pruned.answer,q.answer,JSON.stringify(q));
 assert.equal(r.raw.probes,q.raw_probes,JSON.stringify(q));
 assert.equal(r.pruned.probes,q.pruned_probes,JSON.stringify(q));
}
assert.deepEqual(D.run(graph,2,7,3).out.kept,[1]);
assert.deepEqual(D.run(graph,2,6,3).out.kept,[3]);
const result={status:'PASS',fixture_queries:fixtures.length,answer_checks:fixtures.length*2,
 checks:['raw and pruned answers','raw and pruned probe counts','budget reversal counterexample']};
fs.writeFileSync(path.join(__dirname,'../data/results/dominance_js_check.json'),JSON.stringify(result,null,2));
console.log(JSON.stringify(result));

