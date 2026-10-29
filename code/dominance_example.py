"""An explicitly augmented paper graph exposes reversal between two budgets."""
import json
import numpy as np
from graphio import ROOT,from_edges
from bfs import ground_truth
from kreach import cover_distances,build_index
from paper_example import paper_graph
from dominance import all_boundaries,query_boundary_batch,profile_boundaries


def main():
    graph=paper_graph();graph['edges'].append([2,3])
    graph['source']='Course counterexample: paper Figure 1 plus c→d; not an original paper figure.'
    g=from_edges(graph['edges'],10);cover=np.array(graph['cover'],np.int32)
    rank=np.full(10,-1,np.int32);rank[cover]=np.arange(len(cover),dtype=np.int32)
    table,_=cover_distances(g[0],g[1],cover,rank,6)
    b=all_boundaries(g,rank,table,3)
    low=b['both'][1][b['both'][0][2]:b['both'][0][3]]
    high=b['both'][5][b['both'][4][2]:b['both'][4][3]]
    assert list(cover[low])==[1]and list(cover[high])==[3]
    fixtures=[]
    for k in range(2,7):
        boundaries=all_boundaries(g,rank,table,k)
        index=build_index(table,k,'adaptive')
        q=np.array([(s,t,k)for s in range(10)for t in range(10)],np.int32)
        truth,distance=ground_truth(g[0],g[1],q)
        raw=profile_boundaries(rank,index.mode,*index.arrays,*boundaries['raw'],q)
        cut=profile_boundaries(rank,index.mode,*index.arrays,*boundaries['both'],q)
        answer=query_boundary_batch(rank,index.mode,*index.arrays,*boundaries['both'],q)
        assert np.array_equal(answer,truth)
        for i,(s,t,_)in enumerate(q):
            fixtures.append(dict(s=int(s),t=int(t),k=k,answer=bool(truth[i]),
                distance=int(distance[i]),raw_probes=int(raw[i]),pruned_probes=int(cut[i])))
    own=ROOT/'visualization'
    (own/'dominance_graph.json').write_text(json.dumps(graph,ensure_ascii=False,indent=2),encoding='utf-8')
    (own/'dominance_fixtures.json').write_text(json.dumps(fixtures),encoding='utf-8')
    # Generate a course example; original \PaperGraph remains untouched.
    base=(ROOT/'docs/slides/assets/paper_graph.tex').read_text(encoding='utf-8')
    tex=base.replace(r'\PaperGraph',r'\DominanceGraph')
    marker=r'\foreach \u/\v in {#2}'
    extra=r'\draw[-{Stealth[length=2mm]},draw=Teal,line width=1.3pt] (c) to[bend left=25] (d);'+'\n'
    tex=tex.replace(marker,extra+marker)
    (ROOT/'docs/slides/assets/dominance_graph.tex').write_text(tex,encoding='utf-8')
    result=dict(status='PASS',counterexample='Same boundary keeps b for budget1, d for budget2',
        fixture_queries=len(fixtures),paper_graph_augmentation='one edge c→d')
    (ROOT/'data/results/dominance_example_check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()

