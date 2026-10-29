"""Small-graph exactness audit for threshold-dependent boundary dominance."""
import json,time
import numpy as np
from graphio import ROOT,from_edges
from kreach import make_cover,cover_distances,build_index
from bfs import python_oracle
from dominance import all_boundaries,query_boundary_batch

def main():
    started=time.perf_counter();checked=0
    graphs=[]
    edges=[(u,v)for u in range(3)for v in range(3)if u!=v]
    for mask in range(64):
        graphs.append(from_edges([e for i,e in enumerate(edges)if mask&(1<<i)],3))
    rng=np.random.default_rng(613)
    for _ in range(60):
        n=int(rng.integers(4,32));e=np.argwhere(rng.random((n,n))<rng.uniform(.06,.4))
        e=e[e[:,0]!=e[:,1]];graphs.append(from_edges(e,n))
    for g in graphs:
        n=len(g[0])-1;cover,rank=make_cover(g,17)
        table,_=cover_distances(g[0],g[1],cover,rank,6)
        for k in [2,3,4,6]:
            boundaries=all_boundaries(g,rank,table,k)
            q=np.array([(s,t,k)for s in range(n)for t in range(n)],np.int32)
            edges=np.column_stack((np.repeat(np.arange(n),np.diff(g[0])),g[1]))
            oracle=python_oracle(n,edges,q)
            for codec in ['csr','adaptive']:
                index=build_index(table,k,codec)
                for variant in ['raw','source','target','both']:
                    for join in ([False,True]if codec=='csr'else[False]):
                        a=query_boundary_batch(rank,index.mode,*index.arrays,*boundaries[variant],q,join)
                        assert np.array_equal(a,oracle),(n,k,codec,variant,join,np.flatnonzero(a!=oracle)[:5])
                        checked+=len(q)
    report=dict(status='PASS',graphs=len(graphs),oracle='Independent Python deque BFS',
        method_answers=checked,checks=['all four endpoint cases','two threshold budgets',
        'source-only and target-only ablations','joint dominance','CSR join baseline','self and disconnected queries'],
        elapsed_seconds=time.perf_counter()-started)
    (ROOT/'data/results/dominance_correctness.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()

