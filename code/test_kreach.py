"""K-Reach independent oracle and codec equivalence on exhaustive/random graphs."""
import itertools
import json
import time
import numpy as np
from graphio import ROOT,from_edges
from bfs import python_oracle as oracle
from kreach import make_cover,cover_distances,row_counts,build_index,lookup,query_batch,query_profile


def check(n,edges,seed,all_pairs=True):
    graph=from_edges(edges,n);cover,rank=make_cover(graph,seed)
    table,_=cover_distances(graph[0],graph[1],cover,rank,6)
    total=0;entries=0
    for k in [2,3,4,6]:
        pairs=list(itertools.product(range(n),repeat=2))
        if not all_pairs:
            rng=np.random.default_rng(seed+k);pairs=[pairs[i]for i in rng.choice(len(pairs),min(200,len(pairs)),replace=False)]
        queries=np.array([(s,t,k)for s,t in pairs],np.int32)
        truth=oracle(n,edges,queries)
        counts=row_counts(table,k)
        indexes=[build_index(table,k,c,counts)for c in ['csr','dense','adaptive']]
        assert indexes[2].nbytes<=min(indexes[0].nbytes,indexes[1].nbytes)
        for index in indexes:
            out=query_batch(*graph,rank,index.mode,*index.arrays,queries)
            assert np.array_equal(out,truth),(n,edges,k,index.mode,queries[out!=truth])
            for i in range(len(cover)):
                for j in range(len(cover)):
                    value=table[i,j]
                    expected=0 if value==0 or value>k+1 else(1 if value<=k-1 else(2 if value==k else 3))
                    assert lookup(index.mode,i,j,*index.arrays)==expected
                    entries+=1
        total+=len(queries)*len(indexes)
    return total,entries


def main():
    start=time.perf_counter();queries=entries=0
    possible=[(u,v)for u in range(3)for v in range(3)if u!=v]
    for mask in range(64):
        edges=[edge for bit,edge in enumerate(possible)if mask&(1<<bit)]
        q,e=check(3,edges,mask);queries+=q;entries+=e
    rng=np.random.default_rng(73123)
    for trial in range(60):
        n=int(rng.integers(4,32));p=float(rng.choice([.02,.08,.2,.5]))
        edges=np.argwhere(rng.random((n,n))<p)
        edges=edges[edges[:,0]!=edges[:,1]].tolist()
        q,e=check(n,edges,trial,False);queries+=q;entries+=e
    # Every endpoint branch, including the two-uncovered shared-neighbor case.
    g=from_edges([(0,1),(2,1),(1,3),(3,4)],5)
    cover=np.array([1,3],np.int32);rank=np.array([-1,0,-1,1,-1],np.int32)
    t,_=cover_distances(g[0],g[1],cover,rank,6)
    ix=build_index(t,3,'adaptive')
    qs=np.array([[1,3,3],[1,4,3],[0,3,3],[0,4,3],[2,4,3]],np.int32)
    cases=query_profile(*g,rank,ix.mode,*ix.arrays,qs)[0]
    assert list(cases)==[1,2,3,4,4]
    result=dict(status='PASS',exhaustive_graphs=64,randomized_graphs=60,
                oracle='Independent Python deque full BFS',algorithm_answers_checked=queries,
                codec_cells_checked=entries,all_four_query_cases_checked=True,
                adaptive_size_envelope_checked=True,elapsed_seconds=time.perf_counter()-start)
    (ROOT/'data/results/kreach_correctness.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
