"""Export small, exact query traces from the saved real-graph experiments."""
import json
from collections import deque
import numpy as np
from graphio import ROOT, load_graph
from kreach import lookup, Index
from dominance import query_boundary_batch, profile_boundaries


def shortest_path(graph, source, target):
    ptr, adj = graph[:2]
    parent = {source: None}
    todo = deque([source])
    while todo:
        u = todo.popleft()
        if u == target:
            path = []
            while u is not None:
                path.append(u)
                u = parent[u]
            return path[::-1]
        for v in adj[ptr[u]:ptr[u+1]]:
            v = int(v)
            if v not in parent:
                parent[v] = u
                todo.append(v)
    return []


def export_example(name, seed, number, key, title):
    root = ROOT/f'data/results/dominance/{name}/k-4'
    base = ROOT/f'data/results/kreach/{name}/k-4'
    with np.load(ROOT/f'data/processed/{name}.npz') as data:
        original = data['original_ids']
    with np.load(base/'adaptive_index.npz') as data:
        index = Index(int(data['mode']), *(data[k] for k in ['ptr','ids','bits','dense','rowmap']), int(data['k']))
    with np.load(root/'boundaries.npz') as data:
        rank, cover = data['rank'], data['cover']
        raw = tuple(data[f'raw_{i}'] for i in range(4))
        cut = tuple(data[f'pruned_{i}'] for i in range(8))
    with np.load(base/f'balanced-{seed}-queries.npz') as data:
        query = data['queries'][number:number+1].copy()
        truth = bool(data['answers'][number])
    s, t, k = map(int, query[0])
    assert rank[s] < 0 and rank[t] < 0 and k == 4
    sources = raw[1][raw[0][s]:raw[0][s+1]].tolist()
    targets = raw[3][raw[2][t]:raw[2][t+1]].tolist()
    kept_s = cut[1][cut[0][s]:cut[0][s+1]].tolist()
    kept_t = cut[3][cut[2][t]:cut[2][t+1]].tolist()
    codes = [[int(lookup(index.mode, u, v, *index.arrays)) for v in targets] for u in sources]
    graph = load_graph(name)

    def trace(a, b, boundaries, variant):
        pairs = []
        witness = []
        for u in a:
            for v in b:
                row, col = sources.index(u), targets.index(v)
                accepted = codes[row][col] == 1
                pairs.append(dict(row=row, col=col, code=codes[row][col], accepted=accepted))
                if accepted:
                    core_path = shortest_path(graph, int(cover[u]), int(cover[v]))
                    assert core_path and len(core_path)-1 <= k-2
                    witness = [int(original[x]) for x in [s, *core_path, t]]
                    break
            if witness:
                break
        assert bool(witness) == truth
        probes = int(profile_boundaries(rank, index.mode, *index.arrays, *boundaries, query)[0])
        answer = bool(query_boundary_batch(rank, index.mode, *index.arrays, *boundaries, query)[0])
        with np.load(root/f'balanced-{seed}-{variant}.npz') as saved:
            assert probes == int(saved['point_path_probes'][number])
            assert answer == bool(saved['answers'][number])
        assert probes == len(pairs) and answer == truth
        return dict(trace=pairs, path=witness)

    baseline = trace(sources, targets, raw+raw, 'Ranked-Adaptive')
    pruned = trace(kept_s, kept_t, cut, 'Dominance-Adaptive')
    distance_path = shortest_path(graph, s, t)
    assert bool(distance_path and len(distance_path)-1 <= k) == truth
    return dict(id=key, title=title, dataset=name, seed=seed, workload='balanced', query_index=number,
        source=int(original[s]), target=int(original[t]), k=k, budget=k-2, caseId=4,
        answer=truth, distance=len(distance_path)-1 if distance_path else None,
        sources=[dict(id=int(original[cover[u]]), kept=u in kept_s) for u in sources],
        targets=[dict(id=int(original[cover[v]]), kept=v in kept_t) for v in targets],
        codes=codes, baseline=baseline, pruned=pruned)


def main():
    # These examples are chosen for readable boundary sizes and distinct behavior.
    # Whole-workload performance is presented separately, without extrapolating
    # the selected query's probe ratio into a time speedup.
    examples = [
        export_example('wiki-Vote',17,1207,'wiki-positive','Wiki-Vote · 可达查询'),
        export_example('wiki-Vote',17,317,'wiki-negative','Wiki-Vote · 不可达查询'),
        export_example('p2p-Gnutella31',43,1719,'p2p-unchanged','Gnutella31 · 无支配关系'),
    ]
    (ROOT/'visualization/comparison_examples.json').write_text(json.dumps(examples,ensure_ascii=False,indent=2),encoding='utf-8')
    report = dict(status='PASS', examples=[dict(id=e['id'],source=e['source'],target=e['target'],
        raw_probes=len(e['baseline']['trace']),pruned_probes=len(e['pruned']['trace']),answer=e['answer']) for e in examples])
    (ROOT/'data/results/comparison_examples_check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    return examples


if __name__ == '__main__':
    main()
