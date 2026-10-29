"""Paper-connected experiments: identical K-Reach logic, three physical codecs.

The independent Python implementation reproduces paper algorithms, not author
code, datasets, or reported timings. Fixed k=2/4/6; graph direction is preserved.
No query workload is used to choose the adaptive storage representation.
"""
import argparse
import csv
import ctypes
import gc
import json
import os
import platform
import time
from pathlib import Path
import numpy as np
import numba
from bfs import distances,ground_truth
from graphio import ROOT,DATASETS,load_graph
from kreach import make_cover,cover_distances,row_counts,build_index,query_batch,query_profile


def pin():
    if os.name=='nt':
        k=ctypes.windll.kernel32;k.GetCurrentProcess.restype=ctypes.c_void_p
        if not k.SetProcessAffinityMask(ctypes.c_void_p(k.GetCurrentProcess()),ctypes.c_size_t(1<<2)):
            raise OSError('CPU affinity failed')


def balanced_queries(graph,k,count,seed):
    rng=np.random.default_rng(seed);ptr,adj,rp,ra=graph
    sources=np.flatnonzero(np.diff(ptr)>0);targets=np.flatnonzero(np.diff(rp)>0)
    positive=[];negative=[];seen=set();half=count//2
    while len(positive)<half or len(negative)<count-half:
        s=int(rng.choice(sources));d=distances(ptr,adj,s)
        yes=targets[(d[targets]>0)&(d[targets]<=k)]
        no=targets[(d[targets]<0)|(d[targets]>k)]
        for choices,out,limit in [(yes,positive,half),(no,negative,count-half)]:
            if len(out)>=limit or not len(choices):continue
            # Four queries per sampled source cap cache reuse; all triples unique.
            for t in rng.choice(choices,min(4,len(choices)),replace=False):
                q=(s,int(t),k)
                if q not in seen:
                    seen.add(q);out.append(q)
                    if len(out)>=limit:break
    result=np.array(positive+negative,np.int32);rng.shuffle(result)
    return result


def uniform_queries(graph,k,count,seed):
    rng=np.random.default_rng(seed);ptr,_,rp,_=graph
    sources=np.flatnonzero(np.diff(ptr)>0);targets=np.flatnonzero(np.diff(rp)>0)
    out=[];seen=set()
    while len(out)<count:
        s,t=int(rng.choice(sources)),int(rng.choice(targets));q=(s,t,k)
        if s!=t and q not in seen:seen.add(q);out.append(q)
    return np.array(out,np.int32)


def timed_call(function,target=.09):
    function()
    begin=time.perf_counter_ns();function();first=(time.perf_counter_ns()-begin)/1e9
    repeats=max(1,min(2000,int(target/max(first,1e-6))))
    begin=time.perf_counter_ns()
    for _ in range(repeats):function()
    return (time.perf_counter_ns()-begin)/1e9/repeats,repeats


def append(path,rows):
    with path.open('a',newline='',encoding='utf-8')as file:
        w=csv.DictWriter(file,fieldnames=list(rows[0]))
        if file.tell()==0:w.writeheader()
        w.writerows(rows)


def run_dataset(name,args):
    base='kreach'if args.cover_seed==17 else f'kreach_cover/seed-{args.cover_seed}'
    folder=ROOT/f'data/results/{base}/{name}';folder.mkdir(parents=True,exist_ok=True)
    graph=load_graph(name);ptr,adj,rp,ra=graph;n=len(ptr)-1
    cover,rank=make_cover(graph,args.cover_seed)
    print(name,'cover',len(cover),'of',n,flush=True)
    np.savez_compressed(folder/'cover.npz',cover=cover,rank=rank)
    # JIT warmup on a genuine small graph, outside charged construction.
    warm_rank=np.full(n,-1,np.int32);warm_rank[cover[0]]=0
    kmax=max(args.ks)
    cover_distances(ptr,adj,cover[:1],warm_rank,kmax)
    started=time.perf_counter();table,scans=cover_distances(ptr,adj,cover,rank,kmax)
    bfs_seconds=time.perf_counter()-started
    print(name,'bounded BFS seconds',round(bfs_seconds,2),'scans',scans,flush=True)
    stats=[]
    for k in args.ks:
        path=folder/f'k-{k}';path.mkdir(exist_ok=True)
        if (path/'DONE.json').exists()and not args.force:continue
        for filename in ['timing.csv','summary.csv','by_case_timing.csv']:
            if (path/filename).exists():(path/filename).unlink()
        counts=row_counts(table,k)
        indexes={};encode_times={}
        # Warm every encoder on a small core matrix before timing large matrices.
        for codec in ['csr','dense','adaptive']:build_index(table[:4,:4].copy(),k,codec)
        for codec in ['csr','dense','adaptive']:
            start=time.perf_counter();indexes[codec]=build_index(table,k,codec,counts)
            encode_times[codec]=time.perf_counter()-start
            print(name,k,codec,'MiB',round(indexes[codec].nbytes/2**20,2),'mode',indexes[codec].mode,flush=True)
        assert indexes['adaptive'].nbytes<=min(indexes['csr'].nbytes,indexes['dense'].nbytes)
        common=cover.nbytes+rank.nbytes
        for codec,index in indexes.items():
            stats.append(dict(dataset=name,k=k,codec=codec,vertices=n,edges=len(adj),cover=len(cover),
                              reachable_core_pairs=int(counts.sum()),density=float(counts.mean()/len(cover)),
                              payload_bytes=index.nbytes,common_mapping_bytes=common,total_bytes=index.nbytes+common,
                              dense_rows=int(np.sum(index.rowmap>=0))if index.mode==2 else(len(cover)if index.mode==1 else 0),
                              sparse_rows=int(np.sum(index.rowmap<0))if index.mode==2 else(len(cover)if index.mode==0 else 0),
                              shared_bfs_seconds=bfs_seconds,bfs_kmax=kmax,
                              encoding_seconds=encode_times[codec],scratch_matrix_bytes=table.nbytes))
        with (path/'index_stats.csv').open('w',newline='',encoding='utf-8')as file:
            rows=[x for x in stats if x['k']==k]
            w=csv.DictWriter(file,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        np.savez_compressed(path/'row_density.npz',counts=counts,dense_threshold=(len(cover)+3)//4/4.25)
        if k==4:indexes['adaptive'].save(path/'adaptive_index.npz',cover,rank)
        for workload in ['uniform','balanced']:
            for seed in args.seeds:
                make=uniform_queries if workload=='uniform'else balanced_queries
                qs=make(graph,k,args.queries,seed+100*k)
                truth,true_dist=ground_truth(ptr,adj,qs)
                if workload=='balanced':assert truth.sum()==args.queries//2
                np.savez_compressed(path/f'{workload}-{seed}-queries.npz',queries=qs,answers=truth,distance=true_dist)
                profiles={};latencies={codec:[]for codec in indexes}
                for codec,index in indexes.items():
                    result=query_batch(*graph,rank,index.mode,*index.arrays,qs)
                    assert np.array_equal(result,truth),(name,k,workload,codec)
                    profiles[codec]=query_profile(*graph,rank,index.mode,*index.arrays,qs)
                    np.savez_compressed(path/f'{workload}-{seed}-{codec}-evidence.npz',answers=result,
                                        cases=profiles[codec][0],probes=profiles[codec][1],comparisons=profiles[codec][2],
                                        dense_probes=profiles[codec][3])
                # All codecs must perform identical logical lookups and branches.
                assert np.array_equal(profiles['csr'][1],profiles['adaptive'][1])
                assert np.array_equal(profiles['csr'][0],profiles['dense'][0])
                rng=np.random.default_rng(seed+711);keys=list(indexes)
                for rep in range(args.repeats):
                    rng.shuffle(keys);records=[]
                    for codec in keys:
                        index=indexes[codec]
                        fun=lambda:query_batch(*graph,rank,index.mode,*index.arrays,qs)
                        duration,rounds=timed_call(fun,args.target)
                        us=duration/len(qs)*1e6;latencies[codec].append(us)
                        records.append(dict(dataset=name,k=k,workload=workload,seed=seed,codec=codec,repeat=rep,
                                            us_per_query=us,batch_queries=len(qs),batch_rounds=rounds))
                    append(path/'timing.csv',records)
                rows=[]
                for codec,index in indexes.items():
                    cases,probes,comparisons,dp=profiles[codec]
                    rows.append(dict(dataset=name,k=k,workload=workload,seed=seed,codec=codec,
                                     queries=len(qs),positive_rate=float(truth.mean()),errors=0,
                                     latency_us=float(np.median(latencies[codec])),repeat_min=min(latencies[codec]),repeat_max=max(latencies[codec]),
                                     mean_probes=float(probes.mean()),mean_comparisons=float(comparisons.mean()),
                                     dense_probe_rate=float(dp.sum()/max(1,probes.sum())),total_index_bytes=index.nbytes+common))
                append(path/'summary.csv',rows)
                # Workload by case is measured separately, outside main latencies.
                if workload=='balanced'and seed==args.seeds[0]:
                    for case in range(1,5):
                        sub=qs[profiles['csr'][0]==case]
                        if not len(sub):continue
                        for codec,index in indexes.items():
                            vals=[]
                            for rep in range(5):
                                duration,_=timed_call(lambda:query_batch(*graph,rank,index.mode,*index.arrays,sub),.025)
                                vals.append(duration/len(sub)*1e6)
                            append(path/'by_case_timing.csv',[dict(dataset=name,k=k,case=case,codec=codec,queries=len(sub),latency_us=float(np.median(vals)))])
                print(name,k,workload,seed,[(c,round(np.median(v),4))for c,v in latencies.items()],flush=True)
        (path/'DONE.json').write_text(json.dumps(dict(dataset=name,k=k,seeds=args.seeds,queries=args.queries,
            repeats=args.repeats,shared_bfs_seconds=bfs_seconds,bfs_kmax=kmax),indent=2),encoding='utf-8')
        del indexes;gc.collect()
    # Include exact deployment bytes. Scratch shared only for measurement and
    # construction, never charged as compressed deployed storage.
    import pandas as pd
    paths=list(folder.glob('k-*/index_stats.csv'))
    if paths:pd.concat([pd.read_csv(p)for p in paths],ignore_index=True).to_csv(folder/'index_stats.csv',index=False)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--datasets',nargs='+',default=DATASETS)
    p.add_argument('--ks',nargs='+',type=int,default=[2,4,6])
    p.add_argument('--seeds',nargs='+',type=int,default=[17,29,43])
    p.add_argument('--cover-seed',type=int,default=17)
    p.add_argument('--queries',type=int,default=5000)
    p.add_argument('--repeats',type=int,default=9)
    p.add_argument('--target',type=float,default=.08)
    p.add_argument('--force',action='store_true')
    args=p.parse_args();pin()
    assert all(2<=k<=6 for k in args.ks)
    root=ROOT/('data/results/kreach'if args.cover_seed==17 else f'data/results/kreach_cover/seed-{args.cover_seed}')
    root.mkdir(parents=True,exist_ok=True)
    (root/'environment.json').write_text(json.dumps(dict(platform=platform.platform(),numpy=np.__version__,
        numba=numba.__version__,cpu_affinity=2,parameters=vars(args),
        timing='answers-only warmed single-thread Numba batch; diagnostics separate',
        cover=f'maximal matching endpoints, shuffled directed edges, seed{args.cover_seed}; verified edge coverage'),indent=2),encoding='utf-8')
    for name in args.datasets:run_dataset(name,args)


if __name__=='__main__':main()
