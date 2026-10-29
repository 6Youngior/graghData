"""Controlled threshold-dominance experiments; reuse independently audited queries."""
import argparse,csv,json,time,gc
from pathlib import Path
import numpy as np
from graphio import ROOT,DATASETS,load_graph,from_edges
from kreach import make_cover,cover_distances,build_index
from kreach_experiments import pin,timed_call
from dominance import all_boundaries,query_boundary_batch,profile_boundaries

VARIANTS={
 'Ranked-CSR':('csr','raw',False),'Join-CSR':('csr','raw',True),
 'Dominance-CSR':('csr','both',False),'DominanceJoin-CSR':('csr','both',True),
 'Ranked-Adaptive':('adaptive','raw',False),'Dominance-Adaptive':('adaptive','both',False),
 'Source-Adaptive':('adaptive','source',False),'Target-Adaptive':('adaptive','target',False)}


def append(path,rows):
    with path.open('a',newline='',encoding='utf-8')as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        if f.tell()==0:w.writeheader()
        w.writerows(rows)


def unique_bytes(arrays):
    return sum(a.nbytes for a in {id(a):a for a in arrays}.values())


def run(name,args):
    g=load_graph(name);cover,rank=make_cover(g,args.cover_seed)
    base='dominance'if args.cover_seed==17 else f'dominance_cover/seed-{args.cover_seed}'
    root=ROOT/f'data/results/{base}/{name}';root.mkdir(parents=True,exist_ok=True)
    if all((root/f'k-{k}/DONE.json').exists()for k in args.ks)and not args.force:return
    begin=time.perf_counter();table,_=cover_distances(g[0],g[1],cover,rank,max(args.ks))
    bfs_seconds=time.perf_counter()-begin
    for k in args.ks:
        folder=root/f'k-{k}';folder.mkdir(exist_ok=True)
        if(folder/'DONE.json').exists()and not args.force:continue
        for filename in ['timing.csv','summary.csv','strata.csv']:
            p=folder/filename
            if p.exists():p.unlink()
        begin=time.perf_counter();bound=all_boundaries(g,rank,table,k)
        boundary_seconds=time.perf_counter()-begin
        indexes={c:build_index(table,k,c)for c in ['csr','adaptive']}
        stat=dict(dataset=name,k=k,cover=len(cover),boundary_build_seconds=boundary_seconds,
          shared_bfs_seconds=bfs_seconds,bfs_kmax=max(args.ks),scratch_distance_bytes=table.nbytes,
          max_certificate_scratch_bytes=max(bound['stats'][b]['certificate_scratch_bytes']for b in bound['stats']),
          boundaries=bound['stats'],boundary_bytes={key:unique_bytes(bound[key])for key in ['raw','source','target','both']},
          core_index_bytes={c:ix.nbytes+cover.nbytes+rank.nbytes for c,ix in indexes.items()})
        (folder/'build.json').write_text(json.dumps(stat,indent=2),encoding='utf-8')
        if k==4:
            arrays=bound['both'];raw=bound['raw']
            np.savez_compressed(folder/'boundaries.npz',
                **{f'pruned_{i}':a for i,a in enumerate(arrays)},
                **{f'raw_{i}':a for i,a in enumerate(raw[:4])},cover=cover,rank=rank)
        for workload in ['uniform','balanced']:
            for seed in args.seeds:
                with np.load(ROOT/f'data/results/kreach/{name}/k-{k}/{workload}-{seed}-queries.npz')as saved:
                    q,truth=saved['queries'],saved['answers']
                profiles={}
                # Warm and check every implementation before timing.
                for variant,(codec,which,join)in VARIANTS.items():
                    ix=indexes[codec]
                    answer=query_boundary_batch(rank,ix.mode,*ix.arrays,*bound[which],q,join)
                    assert np.array_equal(answer,truth),(name,k,variant,workload,seed)
                    profiles[variant]=profile_boundaries(rank,ix.mode,*ix.arrays,*bound[which],q)
                    np.savez_compressed(folder/f'{workload}-{seed}-{variant}.npz',
                        answers=answer,point_path_probes=profiles[variant])
                values={v:[]for v in VARIANTS};order=list(VARIANTS);rng=np.random.default_rng(seed+20261029)
                for rep in range(args.repeats):
                    rng.shuffle(order);rows=[]
                    for variant in order:
                        codec,which,join=VARIANTS[variant];ix=indexes[codec]
                        duration,rounds=timed_call(lambda:query_boundary_batch(rank,ix.mode,*ix.arrays,*bound[which],q,join),args.target)
                        us=duration/len(q)*1e6;values[variant].append(us)
                        rows.append(dict(dataset=name,k=k,workload=workload,seed=seed,variant=variant,
                          repeat=rep,us_per_query=us,batch_queries=len(q),batch_rounds=rounds))
                    append(folder/'timing.csv',rows)
                rows=[];rawprobes=profiles['Ranked-Adaptive']
                for variant,times in values.items():
                    codec,which,join=VARIANTS[variant]
                    rows.append(dict(dataset=name,k=k,workload=workload,seed=seed,variant=variant,
                        queries=len(q),errors=0,latency_us=float(np.median(times)),repeat_min=min(times),repeat_max=max(times),
                        point_path_mean_probes=float(profiles[variant].mean()),
                        point_path_increase_queries=int(np.sum(profiles[variant]>rawprobes)),
                        core_index_bytes=stat['core_index_bytes'][codec],
                        boundary_bytes=stat['boundary_bytes'][which],
                        deployment_bytes=stat['core_index_bytes'][codec]+stat['boundary_bytes'][which]))
                append(folder/'summary.csv',rows)
                print(name,k,workload,seed,[(v,round(float(np.median(values[v])),4))for v in ['Ranked-Adaptive','Dominance-Adaptive','Join-CSR','DominanceJoin-CSR']],flush=True)
                if seed==17:
                    # All four graph-structural strata are reported; no best-only selection.
                    s,t=q[:,0],q[:,1];rs,rt=rank[s],rank[t]
                    capacity=np.where(rs>=0,1,np.diff(bound['raw'][0])[s]).astype(np.int64)
                    capacity*=np.where(rt>=0,1,np.diff(bound['raw'][2])[t])
                    cases=np.where(rs>=0,np.where(rt>=0,1,2),np.where(rt>=0,3,4))
                    groups=[('case1',cases==1),('case2',cases==2),('case3',cases==3),('case4',cases==4),
                            ('product1',capacity<=1),('product2to4',(capacity>=2)&(capacity<=4)),
                            ('product5to16',(capacity>=5)&(capacity<=16)),('product17plus',capacity>=17)]
                    for label,mask in groups:
                        sub=q[mask]
                        if len(sub)<8:continue
                        for variant in ['Ranked-Adaptive','Dominance-Adaptive','Join-CSR','DominanceJoin-CSR']:
                            codec,which,join=VARIANTS[variant];ix=indexes[codec]
                            vals=[timed_call(lambda:query_boundary_batch(rank,ix.mode,*ix.arrays,*bound[which],sub,join),.015)[0]/len(sub)*1e6 for _ in range(5)]
                            append(folder/'strata.csv',[dict(dataset=name,k=k,workload=workload,group=label,
                                variant=variant,queries=len(sub),latency_us=float(np.median(vals)))])
        (folder/'DONE.json').write_text(json.dumps(dict(status='PASS',dataset=name,k=k,
            queries_per_batch=5000,seeds=args.seeds,variants=list(VARIANTS),repeats=args.repeats),indent=2),encoding='utf-8')
        del bound,indexes;gc.collect()


def main():
    p=argparse.ArgumentParser();p.add_argument('--datasets',nargs='+',default=DATASETS)
    p.add_argument('--ks',type=int,nargs='+',default=[2,4,6]);p.add_argument('--seeds',type=int,nargs='+',default=[17,29,43])
    p.add_argument('--repeats',type=int,default=9);p.add_argument('--target',type=float,default=.08)
    p.add_argument('--cover-seed',type=int,default=17)
    p.add_argument('--force',action='store_true');args=p.parse_args();pin()
    base='dominance'if args.cover_seed==17 else f'dominance_cover/seed-{args.cover_seed}'
    root=ROOT/f'data/results/{base}';root.mkdir(parents=True,exist_ok=True)
    (root/'environment.json').write_text(json.dumps(dict(parameters=vars(args),
        cpu_affinity=2,timing='identical answers-only boundary query kernel; warmed; shuffled variants; median',
        baseline='pre-ranked boundaries for all variants; CSR join implements paper 4.2.2 merge plus deterministic cost switch'),indent=2),encoding='utf-8')
    tiny=from_edges([(0,1),(1,2),(2,3)],4);cover,rank=make_cover(tiny,17)
    table,_=cover_distances(tiny[0],tiny[1],cover,rank,6);all_boundaries(tiny,rank,table,4)
    for name in args.datasets:run(name,args)

if __name__=='__main__':main()

