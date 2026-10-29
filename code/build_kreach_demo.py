"""Bundle a complete offline paper explainer, actual row excerpts and results."""
import base64
import json
import numpy as np
from graphio import ROOT,DATASETS
from kreach import lookup
from paper_example import main as example
from dominance_example import main as dominance_example
from comparison_examples import main as comparison_examples


def main():
    example()
    dominance_example()
    facts=json.loads((ROOT/'data/results/kreach_facts.json').read_text())
    storage={};names={'wiki-Vote':'Wiki-Vote','p2p-Gnutella31':'Gnutella31','email-EuAll':'Email-EuAll'}
    for name in DATASETS:
        folder=ROOT/f'data/results/kreach/{name}/k-4';ix=np.load(folder/'adaptive_index.npz')
        counts=np.load(folder/'row_density.npz')['counts'];mode=int(ix['mode']);c=len(counts)
        original=np.load(ROOT/f'data/processed/{name}.npz')['original_ids'];cover=ix['cover']
        arrays=tuple(ix[key]for key in ['ptr','ids','bits','dense','rowmap'])
        ptr,ids_all,bits_all,dense_all,rowmap_all=arrays
        def row(i):
            sample=[int(lookup(mode,i,j,*arrays))for j in range(min(24,c))]
            if mode==1 or(mode==2 and rowmap_all[i]>=0):
                drow=i if mode==1 else rowmap_all[i]
                codes=np.array([(int(dense_all[drow,j//4])>>(2*(j%4)))&3 for j in range(c)])
                ids=np.flatnonzero(codes);entries=[[int(j),f'{codes[j]:02b}']for j in ids[:12]]
                fmt='两位稠密行'
            else:
                ids=ids_all[ptr[i]:ptr[i+1]]
                entries=[[int(j),f'{int(lookup(mode,i,int(j),*arrays)):02b}']for j in ids[:12]]
                fmt='稀疏 CSR'+('（整体回退）'if mode==0 else'')
            count=int(counts[i])
            return dict(row=int(i),original=int(original[cover[i]]),count=count,format=fmt,
                        sparseBytes=4*count+(count+3)//4,denseBytes=(c+3)//4,
                        codes=[f'{v:02b}'for v in sample],entries=entries)
        storage[name]=dict(name=names[name],core=c,long=row(int(np.argmax(counts))),short=row(int(np.argmin(counts))))
    charts={}
    for key,file in [('speed','query_speed'),('density','row_density')]:
        content=(ROOT/f'data/results/kreach_figures/{file}.png').read_bytes()
        charts[key]='data:image/png;base64,'+base64.b64encode(content).decode()
    data=dict(graph=json.loads((ROOT/'visualization/paper_graph.json').read_text(encoding='utf-8')),facts=facts,storage=storage,charts=charts)
    data['dominanceGraph']=json.loads((ROOT/'visualization/dominance_graph.json').read_text(encoding='utf-8'))
    data['comparisonExamples']=comparison_examples()
    if (ROOT/'data/results/dominance_facts.json').exists():
        data['dominanceFacts']=json.loads((ROOT/'data/results/dominance_facts.json').read_text(encoding='utf-8'))
        for key,file in [('pruningSpeed','pruning_speed'),('caseProbes','case_probes')]:
            charts[key]='data:image/png;base64,'+base64.b64encode((ROOT/f'data/results/dominance_figures/{file}.png').read_bytes()).decode()
    html=(ROOT/'visualization/paper_template.html').read_text(encoding='utf-8')
    html=html.replace('<!--DOMINANCE-->',(ROOT/'visualization/dominance_panel.html').read_text(encoding='utf-8'))
    groups={'STYLE':['paper_style.css','dominance_style.css'],
            'ENGINE':['paper_engine.js','dominance_engine.js','comparison_engine.js'],
            'APP':['paper_app.js','dominance_app.js','comparison_app.js']}
    for marker,files in groups.items():
        html=html.replace('/*'+marker+'*/','\n'.join((ROOT/'visualization'/file).read_text(encoding='utf-8') for file in files))
    html=html.replace('/*DATA*/','window.PROJECT_DATA='+json.dumps(data,ensure_ascii=False).replace('</','<\\/')+';')
    (ROOT/'visualization/index.html').write_text(html,encoding='utf-8')
    print('Built offline comparison visualization/index.html',flush=True)


if __name__=='__main__':main()
