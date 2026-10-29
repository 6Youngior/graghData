"""Independent integer-distance certificates for every removed real boundary."""
import json
import numpy as np
from numba import njit
from graphio import ROOT,DATASETS,load_graph
from kreach import make_cover,cover_distances,Index
from dominance import all_boundaries,query_boundary_batch
from dominance_experiments import VARIANTS

@njit(cache=True)
def verify_one(ptr,adj,rank,table,cutptr,cutadj,budget,reverse):
    removed=0;witness_cells=0;kept_count=0
    for node in range(len(ptr)-1):
        if rank[node]>=0:
            assert cutptr[node]==cutptr[node+1];continue
        lo,hi=cutptr[node],cutptr[node+1]
        previous=-1
        for a in range(lo,hi):
            parent=cutadj[a];assert parent>previous;previous=parent
            assert 0<=parent<len(table)
            present=False
            for e in range(ptr[node],ptr[node+1]):
                if rank[adj[e]]==parent:present=True;break
            assert present;kept_count+=1
        for e in range(ptr[node],ptr[node+1]):
            child=rank[adj[e]]
            still_kept=False
            for a in range(lo,hi):
                if cutadj[a]==child:still_kept=True;break
            if still_kept:continue
            witnessed=False
            for a in range(lo,hi):
                parent=cutadj[a];contained=True
                for z in range(len(table)):
                    child_value=table[z,child]if reverse else table[child,z]
                    if 0<child_value<=budget+1:
                        parent_value=table[z,parent]if reverse else table[parent,z]
                        witness_cells+=1
                        if parent_value==0 or parent_value>budget+1:
                            contained=False;break
                if contained:witnessed=True;break
            assert witnessed
            removed+=1
    return removed,witness_cells,kept_count


def main():
    reports=[];answers=0;main_answers=0;probe_increases=0;live_checkpoint_answers=0
    roots=[(ROOT/'data/results/dominance',17)]
    roots.extend((ROOT/f'data/results/dominance_cover/seed-{seed}',seed)for seed in [29,43])
    for root,seed in roots:
        for name in DATASETS:
            g=load_graph(name);cover,rank=make_cover(g,seed)
            table,_=cover_distances(g[0],g[1],cover,rank,6)
            for k in ([2,4,6]if seed==17 else[4]):
                folder=root/name/f'k-{k}'
                assert(folder/'DONE.json').exists()
                bound=all_boundaries(g,rank,table,k);a=bound['both']
                if k==4:
                    with np.load(folder/'boundaries.npz')as checkpoint:
                        assert np.array_equal(checkpoint['rank'],rank)
                        assert np.array_equal(checkpoint['cover'],cover)
                        for i,array in enumerate(a):assert np.array_equal(checkpoint[f'pruned_{i}'],array)
                        for i,array in enumerate(bound['raw'][:4]):assert np.array_equal(checkpoint[f'raw_{i}'],array)
                    if seed==17:
                        with np.load(ROOT/f'data/results/kreach/{name}/k-4/adaptive_index.npz')as saved:
                            assert np.array_equal(saved['rank'],rank)
                            deployed=Index(int(saved['mode']),saved['ptr'],saved['ids'],saved['bits'],saved['dense'],saved['rowmap'],4)
                removed=cells=kept=0
                for off,b,reverse in [(0,k-2,False),(2,k-2,True),(4,k-1,False),(6,k-1,True)]:
                    p,adj=(g[2],g[3])if reverse else(g[0],g[1])
                    r,c,n=verify_one(p,adj,rank,table,a[off],a[off+1],b,reverse)
                    removed+=int(r);cells+=int(c);kept+=int(n)
                seeds=[17,29,43]if seed==17 else[17]
                for work in ['uniform','balanced']:
                    for qseed in seeds:
                        with np.load(ROOT/f'data/results/kreach/{name}/k-{k}/{work}-{qseed}-queries.npz')as saved:
                            truth=saved['answers']
                            if k==4 and seed==17:
                                for which in ['raw','both']:
                                    actual=query_boundary_batch(rank,deployed.mode,*deployed.arrays,*bound[which],saved['queries'])
                                    assert np.array_equal(actual,truth)
                                    live_checkpoint_answers+=len(truth)
                        with np.load(folder/f'{work}-{qseed}-Ranked-Adaptive.npz')as raw:
                            raw_probes=raw['point_path_probes']
                        if seed==17:
                            with np.load(ROOT/f'data/results/kreach/{name}/k-{k}/{work}-{qseed}-csr-evidence.npz')as original:
                                assert np.array_equal(raw_probes,original['probes'])
                        for variant in VARIANTS:
                            with np.load(folder/f'{work}-{qseed}-{variant}.npz')as e:
                                assert np.array_equal(e['answers'],truth)
                                answers+=len(truth)
                                if seed==17:main_answers+=len(truth)
                                if variant=='Dominance-Adaptive':probe_increases+=int(np.sum(e['point_path_probes']>raw_probes))
                reports.append(dict(dataset=name,k=k,cover_seed=seed,removed_candidates_certified=removed,
                    integer_reach_memberships_checked=cells,kept_candidates_checked=kept))
                print('PASS',name,k,seed,'removed',removed,flush=True)
            del table,bound
    result=dict(status='PASS',main_method_answers=main_answers,all_method_answers=answers,
        live_deployment_checkpoint_answers=live_checkpoint_answers,
        raw_boundary_probes_match_original_paper_implementation=True,
        certificate_method='direct integer-distance inclusion; independent of construction bit packing',
        actual_probe_increase_queries=probe_increases,reports=reports)
    (ROOT/'data/results/dominance_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items()if k!='reports'},indent=2))

if __name__=='__main__':main()

