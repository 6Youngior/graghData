from pathlib import Path
import gzip
import hashlib
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATASETS = ['wiki-Vote', 'p2p-Gnutella31', 'email-EuAll']


def csr(n, source, target):
    order = np.lexsort((target, source))
    source, target = source[order], target[order]
    ptr = np.zeros(n + 1, np.int64)
    ptr[1:] = np.cumsum(np.bincount(source, minlength=n))
    return ptr, np.asarray(target, dtype=np.int32)


def from_edges(edges, n=None):
    edges = np.unique(np.asarray(edges, dtype=np.int32).reshape(-1, 2), axis=0)
    if n is None:
        n = int(edges.max()) + 1
    ptr, adj = csr(n, edges[:, 0], edges[:, 1])
    rptr, radj = csr(n, edges[:, 1], edges[:, 0])
    return ptr, adj, rptr, radj


def load_graph(name):
    path = ROOT / f'data/processed/{name}.npz'
    if not path.exists():
        with gzip.open(ROOT / f'data/raw/{name}.txt.gz', 'rt') as file:
            raw = np.loadtxt(file, comments='#', dtype=np.int64)
        ids, mapped = np.unique(raw, return_inverse=True)
        edges = mapped.reshape(-1, 2)
        self_loops = int(np.sum(edges[:, 0] == edges[:, 1]))
        # A self loop never changes the <=k answer; remove and report it.
        edges = edges[edges[:, 0] != edges[:, 1]]
        ptr, adj, rptr, radj = from_edges(edges, len(ids))
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, ptr=ptr, adj=adj, rptr=rptr, radj=radj, original_ids=ids)
        meta = dict(name=name, nodes=len(ids), edges=len(adj), raw_edges=len(raw), removed_self_loops=self_loops,
                    removed_parallel_edges=len(edges)-len(adj), directed=True, weighted=False,
                    edge_sha256=hashlib.sha256(np.asarray(edges, dtype=np.int32).tobytes()).hexdigest())
        path.with_suffix('.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    d = np.load(path)
    return tuple(d[k] for k in ['ptr', 'adj', 'rptr', 'radj'])
