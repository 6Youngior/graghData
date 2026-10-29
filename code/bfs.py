"""Independent full BFS oracle utilities, separate from K-Reach query logic."""
from collections import deque
import numpy as np
from numba import njit


@njit(cache=True)
def distances(ptr,adj,s):
    n=len(ptr)-1;d=np.full(n,-1,np.int32);queue=np.empty(n,np.int32)
    d[s]=0;queue[0]=s;head,tail=0,1
    while head<tail:
        u=queue[head];head+=1
        for e in range(ptr[u],ptr[u+1]):
            v=adj[e]
            if d[v]<0:d[v]=d[u]+1;queue[tail]=v;tail+=1
    return d


@njit(cache=True)
def ground_truth(ptr,adj,queries):
    order=np.argsort(queries[:,0]);previous=-1
    dist=np.empty(len(ptr)-1,np.int32)
    answer=np.zeros(len(queries),np.int8);actual=np.full(len(queries),-1,np.int32)
    for i in order:
        s,t,k=queries[i]
        if s!=previous:dist=distances(ptr,adj,s);previous=s
        actual[i]=dist[t];answer[i]=int(dist[t]>=0 and dist[t]<=k)
    return answer,actual


def python_oracle(n,edges,queries):
    neighbors=[[]for _ in range(n)]
    for u,v in edges:neighbors[u].append(v)
    out=[]
    for s,t,k in queries:
        d=[-1]*n;d[s]=0;q=deque([s])
        while q:
            u=q.popleft()
            for v in neighbors[u]:
                if d[v]<0:d[v]=d[u]+1;q.append(v)
        out.append(int(d[t]>=0 and d[t]<=k))
    return np.array(out,np.int8)
