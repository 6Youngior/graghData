"""Query a delivered k=4 adaptive checkpoint using original SNAP node IDs."""
import argparse
import json
import numpy as np
from graphio import ROOT,DATASETS,load_graph
from kreach import Index,query_batch,query_profile
from bfs import distances
from dominance import query_boundary_batch,profile_boundaries


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',choices=DATASETS,default='wiki-Vote')
    parser.add_argument('--source',type=int)
    parser.add_argument('--target',type=int)
    parser.add_argument('--k',type=int,default=4)
    parser.add_argument('--method',choices=['dominance','ranked'],default='dominance')
    args=parser.parse_args()
    if (args.source is None)!=(args.target is None):
        parser.error('Supply both --source and --target, or neither.')
    graph=load_graph(args.dataset)
    folder=ROOT/f'data/results/kreach/{args.dataset}/k-4'
    with np.load(folder/'adaptive_index.npz')as saved:
        index=Index(int(saved['mode']),saved['ptr'],saved['ids'],saved['bits'],
                    saved['dense'],saved['rowmap'],int(saved['k']))
        rank=saved['rank']
    if args.k!=index.k:
        parser.error(f'This checkpoint is for k={index.k}; three-category codes cannot answer arbitrary k.')
    with np.load(ROOT/f'data/processed/{args.dataset}.npz')as saved:
        original=saved['original_ids']
    if args.source is None:
        with np.load(folder/'uniform-17-queries.npz')as saved:
            source,target=map(int,saved['queries'][0,:2])
    else:
        mapped=[]
        for value in [args.source,args.target]:
            pos=int(np.searchsorted(original,value))
            if pos==len(original)or int(original[pos])!=value:
                parser.error(f'Original node ID {value} is absent from {args.dataset}.')
            mapped.append(pos)
        source,target=mapped
    query=np.array([[source,target,index.k]],np.int32)
    with np.load(ROOT/f'data/results/dominance/{args.dataset}/k-4/boundaries.npz')as saved:
        assert np.array_equal(saved['rank'],rank)
        if args.method=='dominance':boundaries=tuple(saved[f'pruned_{i}']for i in range(8))
        else:
            raw=tuple(saved[f'raw_{i}']for i in range(4));boundaries=raw+raw
    answer=bool(query_boundary_batch(rank,index.mode,*index.arrays,*boundaries,query)[0])
    boundary_probes=profile_boundaries(rank,index.mode,*index.arrays,*boundaries,query)
    case,probes,comparisons,_=query_profile(*graph,rank,index.mode,*index.arrays,query)
    distance=int(distances(graph[0],graph[1],source)[target])
    truth=0<=distance<=index.k
    assert answer==truth
    print(json.dumps(dict(dataset=args.dataset,k=index.k,source=int(original[source]),target=int(original[target]),
        method=args.method,answer=answer,case=int(case[0]),core_probes=int(boundary_probes[0]),
        original_core_probes=int(probes[0]),
        full_bfs_distance=None if distance<0 else distance,full_bfs_truth=truth,
        storage_mode={0:'csr',1:'dense',2:'mixed'}[index.mode]),indent=2))


if __name__=='__main__':main()

