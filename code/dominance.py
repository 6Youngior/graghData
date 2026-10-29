"""Pilot exact threshold-dominance pruning of K-Reach's outside boundaries.

For budget b=k-2, u is redundant if R_b(u) is contained in R_b(w)
for another boundary vertex w. Incoming boundaries use reverse reach sets.
The deployed lists contain core IDs; the dense certificates are build scratch.
"""
from dataclasses import dataclass
import numpy as np
from numba import njit


@njit(cache=True)
def threshold_sets(table,budget):
    c=len(table);words=(c+63)//64
    forward=np.zeros((c,words),np.uint64)
    reverse=np.zeros((c,words),np.uint64)
    outcount=np.zeros(c,np.int32);incount=np.zeros(c,np.int32)
    for u in range(c):
        for v in range(c):
            if 0<table[u,v]<=budget+1:
                forward[u,v//64]|=np.uint64(1)<<np.uint64(v%64)
                reverse[v,u//64]|=np.uint64(1)<<np.uint64(u%64)
                outcount[u]+=1;incount[v]+=1
    return forward,reverse,outcount,incount


@njit(cache=True)
def prune_boundary(ptr,adj,rank,table,bits,counts,budget,reverse):
    n=len(ptr)-1
    result_ptr=np.zeros(n+1,np.int32)
    result_adj=np.empty(len(adj),np.int32)
    used=0;subset_checks=0;word_checks=0;removed=0;changed=0
    for node in range(n):
        if rank[node]>=0:
            result_ptr[node+1]=used
            continue
        candidates=rank[adj[ptr[node]:ptr[node+1]]].copy()
        assert np.all(candidates>=0)
        # Descending cardinality: a later set cannot strictly dominate a
        # previously retained one. Equal sets retain the smaller core ID.
        for i in range(1,len(candidates)):
            value=candidates[i];j=i-1
            while j>=0 and (counts[candidates[j]]<counts[value]or
                    (counts[candidates[j]]==counts[value]and candidates[j]>value)):
                candidates[j+1]=candidates[j];j-=1
            candidates[j+1]=value
        kept=np.empty(len(candidates),np.int32);size=0
        for child in candidates:
            dominated=False
            for pos in range(size):
                parent=kept[pos]
                # Reflexivity gives an O(1) necessary condition before
                # scanning the exact threshold certificate.
                distance=table[child,parent]if reverse else table[parent,child]
                if distance==0 or distance>budget+1:continue
                subset_checks+=1;contained=True
                for word in range(bits.shape[1]):
                    word_checks+=1
                    if bits[child,word]&~bits[parent,word]:
                        contained=False;break
                if contained:
                    dominated=True;break
            if not dominated:
                kept[size]=child;size+=1
        kept=kept[:size].copy()
        kept.sort() # Keep the same ID order for retained candidates.
        result_adj[used:used+size]=kept
        used+=size;result_ptr[node+1]=used
        removed+=len(candidates)-size
        if size<len(candidates):changed+=1
    return result_ptr,result_adj[:used].copy(),subset_checks,word_checks,removed,changed


@njit(cache=True)
def rank_boundary(ptr,adj,rank):
    outptr=np.zeros(len(ptr),np.int32)
    values=np.empty(len(adj),np.int32);used=0
    for node in range(len(ptr)-1):
        if rank[node]<0:
            for pos in range(ptr[node],ptr[node+1]):
                values[used]=rank[adj[pos]];used+=1
        outptr[node+1]=used
    return outptr,values[:used].copy()


def build_boundaries(graph,rank,table,k):
    b=k-2
    fw,rv,fc,rc=threshold_sets(table,b)
    p,a,rp,ra=graph
    out=prune_boundary(p,a,rank,table,fw,fc,b,False)
    inc=prune_boundary(rp,ra,rank,table,rv,rc,b,True)
    rawout=rank_boundary(p,a,rank);rawin=rank_boundary(rp,ra,rank)
    return dict(out=out[:2],incoming=inc[:2],rawout=rawout,rawin=rawin,
        stats=dict(budget=b,out_subset_checks=int(out[2]),in_subset_checks=int(inc[2]),
          out_word_checks=int(out[3]),in_word_checks=int(inc[3]),
          out_removed=int(out[4]),in_removed=int(inc[4]),
          out_changed_vertices=int(out[5]),in_changed_vertices=int(inc[5]),
          raw_out_entries=len(rawout[1]),raw_in_entries=len(rawin[1]),
          pruned_out_entries=len(out[1]),pruned_in_entries=len(inc[1]),
          certificate_scratch_bytes=fw.nbytes+rv.nbytes,
          deployed_boundary_bytes=sum(x.nbytes for x in (*out[:2],*inc[:2]))))

from kreach import lookup


@njit(cache=True,inline='always')
def accept_row(mode,row,targets,start,end,limit,iptr,ids,bits,dense,rowmap,join):
    # Paper §4.2.2 merge intersection, with a simple deterministic cost switch.
    # The join path is only used by CSR; the binary path supports every codec.
    if join and mode==0:
        rowlen=iptr[row+1]-iptr[row];targetlen=end-start
        lg=0;left=rowlen
        while left>0:lg+=1;left//=2
        if rowlen+targetlen<targetlen*(lg+1):
            a,b=iptr[row],start
            while a<iptr[row+1]and b<end:
                x,y=ids[a],targets[b]
                if x<y:a+=1
                elif x>y:b+=1
                else:
                    code=(bits[a//4]>>(2*(a%4)))&3
                    if 0<code<=limit:return True
                    a+=1;b+=1
            return False
    for pos in range(start,end):
        code=lookup(mode,row,targets[pos],iptr,ids,bits,dense,rowmap)
        if 0<code<=limit:return True
    return False


@njit(cache=True)
def query_boundary_batch(rank,mode,iptr,ids,bits,dense,rowmap,
        op2,oa2,rp2,ra2,op3,oa3,rp3,ra3,queries,join=False):
    answer=np.zeros(len(queries),np.int8)
    for i in range(len(queries)):
        s,t=queries[i,0],queries[i,1]
        if s==t:answer[i]=1;continue
        rs,rt=rank[s],rank[t]
        if rs>=0 and rt>=0:
            answer[i]=lookup(mode,rs,rt,iptr,ids,bits,dense,rowmap)>0
        elif rs>=0:
            answer[i]=accept_row(mode,rs,ra3,rp3[t],rp3[t+1],2,iptr,ids,bits,dense,rowmap,join)
        elif rt>=0:
            for pos in range(op3[s],op3[s+1]):
                code=lookup(mode,oa3[pos],rt,iptr,ids,bits,dense,rowmap)
                if 0<code<=2:answer[i]=1;break
        else:
            for pos in range(op2[s],op2[s+1]):
                if accept_row(mode,oa2[pos],ra2,rp2[t],rp2[t+1],1,iptr,ids,bits,dense,rowmap,join):
                    answer[i]=1;break
    return answer


@njit(cache=True)
def profile_boundaries(rank,mode,iptr,ids,bits,dense,rowmap,
        op2,oa2,rp2,ra2,op3,oa3,rp3,ra3,queries):
    # Untimed point-probe counts. Join timings are reported separately.
    probes=np.zeros(len(queries),np.int64)
    for i in range(len(queries)):
        s,t=queries[i,0],queries[i,1]
        if s==t:continue
        rs,rt=rank[s],rank[t]
        if rs>=0 and rt>=0:probes[i]=1
        elif rs>=0:
            for pos in range(rp3[t],rp3[t+1]):
                probes[i]+=1
                code=lookup(mode,rs,ra3[pos],iptr,ids,bits,dense,rowmap)
                if 0<code<=2:break
        elif rt>=0:
            for pos in range(op3[s],op3[s+1]):
                probes[i]+=1
                code=lookup(mode,oa3[pos],rt,iptr,ids,bits,dense,rowmap)
                if 0<code<=2:break
        else:
            found=False
            for a in range(op2[s],op2[s+1]):
                for b in range(rp2[t],rp2[t+1]):
                    probes[i]+=1
                    if lookup(mode,oa2[a],ra2[b],iptr,ids,bits,dense,rowmap)==1:
                        found=True;break
                if found:break
    return probes


def all_boundaries(graph,rank,table,k):
    low=build_boundaries(graph,rank,table,k)
    high=build_boundaries(graph,rank,table,k+1)
    raw=(*low['rawout'],*low['rawin'])
    out=dict(raw=raw+raw,
        source=(*low['out'],*low['rawin'],*high['out'],*high['rawin']),
        target=(*low['rawout'],*low['incoming'],*high['rawout'],*high['incoming']),
        both=(*low['out'],*low['incoming'],*high['out'],*high['incoming']),
        stats=dict(k_minus_2=low['stats'],k_minus_1=high['stats']))
    return out

