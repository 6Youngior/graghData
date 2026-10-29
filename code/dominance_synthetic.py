"""Controlled nested-boundary graphs; mechanism stress tests, not real workloads."""
import json,time
import numpy as np,pandas as pd
from graphio import ROOT,from_edges
from kreach import cover_distances,build_index
from dominance import all_boundaries,query_boundary_batch,profile_boundaries
from kreach_experiments import pin,timed_call
from bfs import ground_truth


def main():
    pin();folder=ROOT/'data/results/dominance_synthetic';folder.mkdir(exist_ok=True)
    rows=[];timing=[];sources=32
    for degree in [4,8,16,32,64]:
        for positive in [False,True]:
            c=2*degree;n=c+2*sources
            a=np.arange(0,c,2);b=np.arange(1,c,2)
            edges=[]
            for group in [a,b]:
                edges.extend((int(group[i]),int(group[j]))for i in range(degree)for j in range(i))
            edges.extend((c+i,int(v))for i in range(sources)for v in a)
            edges.extend((int(v),c+sources+i)for i in range(sources)for v in b)
            if positive:edges.append((int(a[-1]),int(b[0])))
            g=from_edges(edges,n);cover=np.arange(c,dtype=np.int32)
            rank=np.full(n,-1,np.int32);rank[cover]=cover
            table,_=cover_distances(g[0],g[1],cover,rank,3)
            boundaries=all_boundaries(g,rank,table,3)
            queries=np.array([(c+i,c+sources+j,3)for i in range(sources)for j in range(sources)],np.int32)
            truth,_=ground_truth(g[0],g[1],queries)
            assert np.all(truth==int(positive))
            indexes={codec:build_index(table,3,codec)for codec in ['dense','csr']}
            variants={'Dense':('dense','raw',False),'Dominance-Dense':('dense','both',False),
                      'Join-CSR':('csr','raw',True),'DominanceJoin-CSR':('csr','both',True)}
            expected_raw=degree*(degree-1)+1 if positive else degree**2
            for which,expected in [('raw',expected_raw),('both',1)]:
                ix=indexes['dense'];p=profile_boundaries(rank,ix.mode,*ix.arrays,*boundaries[which],queries)
                assert np.all(p==expected)
            values={v:[]for v in variants};order=list(variants);rng=np.random.default_rng(731)
            for v,(codec,which,join)in variants.items():
                ix=indexes[codec];answer=query_boundary_batch(rank,ix.mode,*ix.arrays,*boundaries[which],queries,join)
                assert np.array_equal(answer,truth)
            for rep in range(9):
                rng.shuffle(order)
                for v in order:
                    codec,which,join=variants[v];ix=indexes[codec]
                    seconds,_=timed_call(lambda:query_boundary_batch(rank,ix.mode,*ix.arrays,*boundaries[which],queries,join),.04)
                    us=seconds/len(queries)*1e6;values[v].append(us)
                    timing.append(dict(degree=degree,positive=positive,variant=v,repeat=rep,us_per_query=us))
            for v,val in values.items():
                rows.append(dict(degree=degree,positive=positive,variant=v,queries=len(queries),
                    latency_us=float(np.median(val)),raw_probes=expected_raw,pruned_probes=1))
            print('synthetic',degree,positive,{v:round(float(np.median(x)),4)for v,x in values.items()},flush=True)
    pd.DataFrame(rows).to_csv(folder/'summary.csv',index=False)
    pd.DataFrame(timing).to_csv(folder/'timing.csv',index=False)
    report=dict(status='PASS',kind='controlled synthetic mechanism test; not production traces',
        cover='explicit 2d core vertices; every edge covered; interleaved IDs',
        graph='two nested directed core clusters; 32 outside sources and 32 outside targets',
        positive='one extra edge connects largest source core to maximal incoming target core',
        parameters=[4,8,16,32,64],queries_per_graph=1024,point_probe_identity='negative d^2; positive d(d-1)+1; pruned 1',
        answer_checks=int(sum(r['queries']for r in rows)))
    (folder/'definition.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

if __name__=='__main__':main()

