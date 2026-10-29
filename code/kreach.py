"""K-Reach (Cheng et al., PVLDB 2012, Algorithms 1–2), independent implementation.

All codecs store the SAME three distance categories for a FIXED k>=2:
  0: unreachable within k; 1: d<=k-2; 2: d=k-1; 3: d=k.
The two-bit value is a category, NOT the actual distance.

Codec 0: sorted CSR IDs plus packed 2-bit values.
Codec 1: all-dense 2-bit rows.
Codec 2: per-row sparse/dense hybrid, with global fallback when smaller.
No approximate answer, learning, landmark fallback, or SCC contraction is used.
"""
from dataclasses import dataclass
import numpy as np
from numba import njit


@njit(cache=True)
def matching_cover(n, source, target, permutation):
    chosen=np.zeros(n,np.bool_)
    for e in permutation:
        u,v=source[e],target[e]
        if not chosen[u]and not chosen[v]:
            chosen[u]=True;chosen[v]=True
    cover=np.flatnonzero(chosen).astype(np.int32)
    rank=np.full(n,-1,np.int32)
    for i in range(len(cover)):rank[cover[i]]=i
    return cover,rank


def make_cover(graph,seed=17):
    ptr,adj,_,_=graph
    sources=np.repeat(np.arange(len(ptr)-1,dtype=np.int32),np.diff(ptr))
    order=np.random.default_rng(seed).permutation(len(adj)).astype(np.int64)
    cover,rank=matching_cover(len(ptr)-1,sources,adj,order)
    assert np.all((rank[sources]>=0)|(rank[adj]>=0))
    return cover,rank


@njit(cache=True)
def cover_distances(ptr,adj,cover,rank,kmax):
    """Bounded original-graph BFS; cache only core-to-core distances <= kmax.

    A zero byte means beyond kmax/unreachable; a positive byte means d+1.
    The temporary dense distance matrix is NOT the deployed index.
    """
    size=len(cover);n=len(ptr)-1
    # The map must belong to this exact cover, including JIT warmup calls.
    # Otherwise unchecked native indexing could corrupt the distance table.
    for v in range(n):assert rank[v]<size
    table=np.zeros((size,size),np.uint8)
    seen=np.zeros(n,np.int32);dist=np.zeros(n,np.int32);queue=np.empty(n,np.int32)
    scanned=0
    for row in range(size):
        s=cover[row];stamp=row+1;seen[s]=stamp;dist[s]=0;queue[0]=s
        head,tail=0,1
        while head<tail:
            u=queue[head];head+=1
            if rank[u]>=0:table[row,rank[u]]=dist[u]+1
            if dist[u]>=kmax:continue
            for e in range(ptr[u],ptr[u+1]):
                scanned+=1;v=adj[e]
                if seen[v]!=stamp:
                    seen[v]=stamp;dist[v]=dist[u]+1;queue[tail]=v;tail+=1
    return table,scanned


@njit(cache=True)
def category(value,k):
    if value==0 or value>k+1:return 0
    if value<=k-1:return 1
    if value==k:return 2
    return 3


@njit(cache=True)
def row_counts(table,k):
    size=len(table);counts=np.zeros(size,np.int64)
    for i in range(size):
        for j in range(size):
            if 0<table[i,j]<=k+1:counts[i]+=1
    return counts


@njit(cache=True)
def encode_csr(table,k,counts):
    size=len(table);ptr=np.empty(size+1,np.int64);ptr[0]=0
    for i in range(size):ptr[i+1]=ptr[i]+counts[i]
    ids=np.empty(ptr[-1],np.int32);bits=np.zeros((ptr[-1]+3)//4,np.uint8)
    for row in range(size):
        pos=ptr[row]
        for col in range(size):
            c=category(table[row,col],k)
            if c:
                ids[pos]=col;bits[pos//4]|=np.uint8(c<<(2*(pos%4)));pos+=1
    return ptr,ids,bits


@njit(cache=True)
def encode_dense(table,k):
    size=len(table);stride=(size+3)//4
    bits=np.zeros((size,stride),np.uint8)
    for row in range(size):
        for col in range(size):
            c=category(table[row,col],k)
            if c:bits[row,col//4]|=np.uint8(c<<(2*(col%4)))
    return bits


@njit(cache=True)
def encode_hybrid(table,k,counts):
    size=len(table);stride=(size+3)//4
    rowmap=np.full(size,-1,np.int32);ptr=np.zeros(size+1,np.int64)
    dense_count=0
    for row in range(size):
        # Compare bytes of row payload, including the sparse distance codes.
        if stride<4*counts[row]+(counts[row]+3)//4:
            rowmap[row]=dense_count;dense_count+=1
            ptr[row+1]=ptr[row]
        else:ptr[row+1]=ptr[row]+counts[row]
    dense=np.zeros((dense_count,stride),np.uint8)
    ids=np.empty(ptr[-1],np.int32);bits=np.zeros((ptr[-1]+3)//4,np.uint8)
    for row in range(size):
        pos=ptr[row];drow=rowmap[row]
        for col in range(size):
            c=category(table[row,col],k)
            if not c:continue
            if drow>=0:dense[drow,col//4]|=np.uint8(c<<(2*(col%4)))
            else:
                ids[pos]=col;bits[pos//4]|=np.uint8(c<<(2*(pos%4)));pos+=1
    return ptr,ids,bits,dense,rowmap


@dataclass
class Index:
    mode:int
    ptr:np.ndarray
    ids:np.ndarray
    bits:np.ndarray
    dense:np.ndarray
    rowmap:np.ndarray
    k:int

    @property
    def nbytes(self):return sum(x.nbytes for x in [self.ptr,self.ids,self.bits,self.dense,self.rowmap])

    @property
    def arrays(self):return self.ptr,self.ids,self.bits,self.dense,self.rowmap

    def save(self,path,cover,rank):
        np.savez_compressed(path,mode=self.mode,k=self.k,ptr=self.ptr,ids=self.ids,bits=self.bits,
                            dense=self.dense,rowmap=self.rowmap,cover=cover,rank=rank)


def build_index(table,k,codec,counts=None):
    if counts is None:counts=row_counts(table,k)
    empty_i=np.zeros(0,np.int32);empty_p=np.zeros(1,np.int64);empty_b=np.zeros(0,np.uint8)
    empty_d=np.zeros((0,0),np.uint8)
    if codec=='csr':
        p,i,b=encode_csr(table,k,counts)
        return Index(0,p,i,b,empty_d,empty_i,k)
    if codec=='dense':return Index(1,empty_p,empty_i,empty_b,encode_dense(table,k),empty_i,k)
    p,i,b,d,m=encode_hybrid(table,k,counts)
    hybrid=Index(2,p,i,b,d,m,k)
    # Whole-format fallback gives a precise deployment-size envelope. Encode
    # only the chosen representation; this preserves identical query semantics.
    csr_bytes=8*(len(table)+1)+4*int(counts.sum())+(int(counts.sum())+3)//4
    dense_bytes=len(table)*((len(table)+3)//4)+8
    if hybrid.nbytes>min(csr_bytes,dense_bytes):
        return build_index(table,k,'csr'if csr_bytes<=dense_bytes else'dense',counts)
    return hybrid


@njit(cache=True,inline='always')
def lookup(mode,row,col,ptr,ids,bits,dense,rowmap):
    if mode==1:return (dense[row,col//4]>>(2*(col%4)))&3
    if mode==2 and rowmap[row]>=0:return (dense[rowmap[row],col//4]>>(2*(col%4)))&3
    left,right=ptr[row],ptr[row+1]
    while left<right:
        middle=(left+right)//2
        value=ids[middle]
        if value<col:left=middle+1
        else:right=middle
    if left<ptr[row+1]and ids[left]==col:return (bits[left//4]>>(2*(left%4)))&3
    return 0


@njit(cache=True)
def query_batch(gptr,gadj,rptr,radj,rank,mode,iptr,ids,bits,dense,rowmap,queries):
    """Production query kernel: answers only, no per-query profiling arrays."""
    out=np.zeros(len(queries),np.int8)
    for q in range(len(queries)):
        s,t=queries[q,0],queries[q,1]
        if s==t:out[q]=1;continue
        rs,rt=rank[s],rank[t]
        if rs>=0 and rt>=0:
            out[q]=lookup(mode,rs,rt,iptr,ids,bits,dense,rowmap)>0
        elif rs>=0:
            for e in range(rptr[t],rptr[t+1]):
                code=lookup(mode,rs,rank[radj[e]],iptr,ids,bits,dense,rowmap)
                if 0<code<=2:out[q]=1;break
        elif rt>=0:
            for e in range(gptr[s],gptr[s+1]):
                code=lookup(mode,rank[gadj[e]],rt,iptr,ids,bits,dense,rowmap)
                if 0<code<=2:out[q]=1;break
        else:
            found=False
            for a in range(gptr[s],gptr[s+1]):
                u=rank[gadj[a]]
                for b in range(rptr[t],rptr[t+1]):
                    code=lookup(mode,u,rank[radj[b]],iptr,ids,bits,dense,rowmap)
                    if code==1:found=True;break
                if found:break
            out[q]=found
    return out


@njit(cache=True)
def query_profile(gptr,gadj,rptr,radj,rank,mode,iptr,ids,bits,dense,rowmap,queries):
    """Separate, untimed mechanism counters; not used in latency benchmarks."""
    probes=np.zeros(len(queries),np.int64);comparisons=np.zeros(len(queries),np.int64)
    cases=np.zeros(len(queries),np.int8)
    dense_probes=np.zeros(len(queries),np.int64)
    for q in range(len(queries)):
        s,t=queries[q,0],queries[q,1];rs,rt=rank[s],rank[t]
        cases[q]=1 if rs>=0 and rt>=0 else(2 if rs>=0 else(3 if rt>=0 else 4))
        if s==t:continue
        # Candidate arrays express exactly Algorithm 2's four branches.
        sources=np.array([rs],np.int32)if rs>=0 else rank[gadj[gptr[s]:gptr[s+1]]]
        targets=np.array([rt],np.int32)if rt>=0 else rank[radj[rptr[t]:rptr[t+1]]]
        limit=3 if cases[q]==1 else(1 if cases[q]==4 else 2)
        found=False
        for u in sources:
            for v in targets:
                probes[q]+=1
                if mode==1 or(mode==2 and rowmap[u]>=0):dense_probes[q]+=1
                else:
                    lo,hi=iptr[u],iptr[u+1]
                    while lo<hi:
                        comparisons[q]+=1;mid=(lo+hi)//2
                        if ids[mid]<v:lo=mid+1
                        else:hi=mid
                c=lookup(mode,u,v,iptr,ids,bits,dense,rowmap)
                if 0<c<=limit:found=True;break
            if found:break
    return cases,probes,comparisons,dense_probes
