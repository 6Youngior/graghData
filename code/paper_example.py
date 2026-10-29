"""Single source of truth for the paper figure, worked queries, and demo."""
import json
import numpy as np
from graphio import ROOT,from_edges
from bfs import distances,ground_truth
from kreach import cover_distances,build_index,query_batch,query_profile,lookup


def paper_graph():
    names=list('abcdefghij')
    positions=[(0,0),(1.2,0),(1.8,1.15),(2.4,0),(3.6,0),(3.6,-1.15),
               (4.8,0),(5.4,1.15),(6,0),(7.2,0)]
    edges=[('a','b'),('c','b'),('b','d'),('d','c'),('d','e'),('e','g'),
           ('d','f'),('g','f'),('g','h'),('g','i'),('i','j')]
    return dict(nodes=[dict(name=name,x=x,y=y)for name,(x,y)in zip(names,positions)],
                edges=[[names.index(u),names.index(v)]for u,v in edges],cover=[1,3,6,8],
                source='K-Reach, Figure 1–2, pp.1295–1296; redrawn')


def main():
    graph=paper_graph();g=from_edges(graph['edges'],10)
    cover=np.array(graph['cover'],np.int32);rank=np.full(10,-1,np.int32);rank[cover]=np.arange(4,dtype=np.int32)
    table,_=cover_distances(g[0],g[1],cover,rank,6)
    expected={('b','d'):1,('d','b'):2,('b','g'):3,('d','g'):2,('d','i'):3,('g','i'):1}
    for (s,t),distance in expected.items():
        assert distances(g[0],g[1],ord(s)-97)[ord(t)-97]==distance
    for k in range(2,7):
        q=np.array([(s,t,k)for s in range(10)for t in range(10)],np.int32)
        truth,_=ground_truth(g[0],g[1],q)
        for codec in ['csr','dense','adaptive']:
            index=build_index(table,k,codec)
            assert np.array_equal(query_batch(*g,rank,index.mode,*index.arrays,q),truth)
    path=ROOT/'visualization/paper_graph.json'
    path.write_text(json.dumps(graph,ensure_ascii=False,indent=2),encoding='utf-8')
    fixtures=[]
    for k in range(2,7):
        qs=np.array([(s,t,k)for s in range(10)for t in range(10)],np.int32)
        profiles={}
        for codec in ['csr','dense','adaptive']:
            index=build_index(table,k,codec)
            profiles[codec]=query_profile(*g,rank,index.mode,*index.arrays,qs)
        for j,(s,t,_)in enumerate(qs):
            d=distances(g[0],g[1],s)
            fixtures.append(dict(s=int(s),t=int(t),k=k,answer=bool(d[t]>=0 and d[t]<=k),distance=int(d[t]),
                cases=int(profiles['csr'][0][j]),probes=int(profiles['csr'][1][j]),
                comparisons={c:int(profiles[c][2][j])for c in profiles}))
    (ROOT/'visualization/paper_fixtures.json').write_text(json.dumps(fixtures),encoding='utf-8')
    assets=ROOT/'docs/slides/assets';assets.mkdir(parents=True,exist_ok=True)
    # TeX graph is generated from the exact same nodes/edges used in the demo.
    lines=[r'\newcommand{\PaperGraph}[2][1]{%',r'\begin{tikzpicture}[x=10mm,y=8mm,vertex/.style={circle,draw=Line,fill=white,minimum size=6.5mm,inner sep=0pt,font=\normalsize},core/.style={vertex,draw=Gold,fill=Gold!12,line width=1.1pt},every edge/.style={-{Stealth[length=1.8mm]},draw=Edge,line width=.7pt}]',r'\ifnum#1=0\tikzset{core/.style={vertex}}\fi']
    for i,node in enumerate(graph['nodes']):
        style='core'if i in graph['cover']else'vertex'
        lines.append(rf'\node[{style}] ({node["name"]}) at ({node["x"]},{node["y"]}) {{{node["name"]}}};')
    lines.append(r'\begin{scope}[on background layer]')
    for u,v in graph['edges']:
        lines.append(rf'\draw[every edge] ({graph["nodes"][u]["name"]}) -- ({graph["nodes"][v]["name"]});')
    lines.append(r'\foreach \u/\v in {#2}{\draw[-{Stealth[length=2.1mm]},draw=FBlue,line width=1.7pt] (\u) -- (\v);}')
    lines.extend([r'\end{scope}',r'\end{tikzpicture}}'])
    (assets/'paper_graph.tex').write_text('\n'.join(lines),encoding='utf-8')
    result=dict(status='PASS',paper_figure_distances_checked=len(expected),demo_query_fixtures=len(fixtures),
                codec_answer_checks=len(fixtures)*3)
    (ROOT/'data/results/paper_example_check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
