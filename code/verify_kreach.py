"""Verify every encoded entry/cell and independently audit real graph truths."""
import json
import numpy as np
from numba import njit
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import shortest_path
from graphio import ROOT,DATASETS,load_graph
from kreach import make_cover,cover_distances,row_counts,build_index


@njit(cache=True)
def verify_payload(table,k,counts,mode,ptr,ids,bits,dense,rowmap):
    checked=0
    for row in range(len(table)):
        drow=row if mode==1 else(rowmap[row]if mode==2 else -1)
        if drow>=0:
            for col in range(len(table)):
                value=int(table[row,col])
                expected=0 if value==0 or value>k+1 else(1 if value<=k-1 else(2 if value==k else 3))
                actual=(dense[drow,col//4]>>(2*(col%4)))&3
                assert actual==expected
                checked+=1
            # Unused packed cells in the last byte must be zero.
            if len(table)%4:
                assert dense[drow,-1]>>(2*(len(table)%4))==0
        else:
            assert ptr[row+1]-ptr[row]==counts[row]
            previous=-1
            for pos in range(ptr[row],ptr[row+1]):
                col=ids[pos];assert previous<col<len(table);previous=col
                value=int(table[row,col]);assert 0<value<=k+1
                expected=1 if value<=k-1 else(2 if value==k else 3)
                actual=(bits[pos//4]>>(2*(pos%4)))&3
                assert actual==expected
                checked+=1
    return checked


def main():
    reports=[];answer_count=0;query_count=0;scipy_count=0
    rng=np.random.default_rng(90210)
    for name in DATASETS:
        graph=load_graph(name);p,a,_,_=graph
        cover,rank=make_cover(graph,17)
        table,_=cover_distances(p,a,cover,rank,6)
        checked=0
        sparse=csr_matrix((np.ones(len(a)),a,p),shape=(len(p)-1,len(p)-1))
        for k in [2,4,6]:
            folder=ROOT/f'data/results/kreach/{name}/k-{k}'
            assert(folder/'DONE.json').exists()
            counts=row_counts(table,k)
            sizes=[]
            for codec in ['csr','dense','adaptive']:
                index=build_index(table,k,codec,counts);sizes.append(index.nbytes)
                checked+=int(verify_payload(table,k,counts,index.mode,*index.arrays))
            assert sizes[2]<=min(sizes[:2])
            for file in folder.glob('*-queries.npz'):
                d=np.load(file);q,truth,dist=d['queries'],d['answers'],d['distance']
                query_count+=len(q)
                tag=file.name.replace('-queries.npz','')
                if tag.startswith('balanced'):assert int(truth.sum())==len(q)//2
                sample=rng.choice(len(q),12,replace=False)
                for part in np.array_split(sample,4):
                    oracle=shortest_path(sparse,directed=True,unweighted=True,indices=q[part,0])
                    actual=oracle[np.arange(len(part)),q[part,1]]
                    assert np.array_equal(actual,np.where(dist[part]<0,np.inf,dist[part]))
                    scipy_count+=len(part)
                cases=None;probes=None
                for codec in ['csr','dense','adaptive']:
                    evidence=np.load(folder/f'{tag}-{codec}-evidence.npz')
                    assert np.array_equal(evidence['answers'],truth)
                    if cases is not None:
                        assert np.array_equal(evidence['cases'],cases)
                        assert np.array_equal(evidence['probes'],probes)
                    cases=evidence['cases'];probes=evidence['probes'];answer_count+=len(q)
        reports.append(dict(dataset=name,encoded_entries_or_dense_cells_checked=checked))
        print('PASS',name,checked,flush=True)
    result=dict(status='PASS',main_query_instances=query_count,main_method_answers=answer_count,
                independent_scipy_distance_checks=scipy_count,all_logical_probe_sequences_equivalent=True,
                adaptive_space_never_exceeds_smaller_global_codec=True,reports=reports)
    (ROOT/'data/results/kreach_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
