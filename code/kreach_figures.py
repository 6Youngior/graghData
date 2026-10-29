"""Presentation figures at their intended printed size; no tiny multi-panels."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from graphio import ROOT,DATASETS

OUT=ROOT/'data/results/kreach_figures';OUT.mkdir(parents=True,exist_ok=True)
BLUE='#1766A3';TEAL='#008B80';GOLD='#C49A3B';GRAY='#8998AA';NAVY='#132A46';LIGHT='#E3EBF2'
NAMES={'wiki-Vote':'Wiki-Vote','p2p-Gnutella31':'Gnutella31','email-EuAll':'Email-EuAll'}
POLICIES=['csr','dense','adaptive']
COLORS={'csr':GRAY,'dense':BLUE,'adaptive':TEAL}
plt.rcParams.update({'font.family':['Microsoft YaHei','DejaVu Sans'],'font.size':10,
                     'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold',
                     'axes.edgecolor':'#CBD6E0','axes.labelcolor':NAVY,'text.color':NAVY,
                     'xtick.color':'#62758B','ytick.color':'#62758B','grid.color':LIGHT,
                     'axes.axisbelow':True,'pdf.fonttype':42,'savefig.facecolor':'white'})


def save(fig,name):
    fig.savefig(OUT/f'{name}.pdf',bbox_inches='tight',pad_inches=.04)
    fig.savefig(OUT/f'{name}.png',bbox_inches='tight',pad_inches=.04,dpi=210)
    plt.close(fig)


def collect():
    tables=[];stats=[];timing=[];cases=[]
    for done in (ROOT/'data/results/kreach').glob('*/k-*/DONE.json'):
        p=done.parent;tables.append(pd.read_csv(p/'summary.csv'));stats.append(pd.read_csv(p/'index_stats.csv'))
        timing.append(pd.read_csv(p/'timing.csv'));cases.append(pd.read_csv(p/'by_case_timing.csv'))
    df=pd.concat(tables,ignore_index=True);st=pd.concat(stats,ignore_index=True)
    if 'shared_kmax6_bfs_seconds'in st:
        st['shared_bfs_seconds']=st['shared_kmax6_bfs_seconds'];st['bfs_kmax']=6
    base=df[df.codec=='csr'][['dataset','k','workload','seed','latency_us']]
    df=df.merge(base,on=['dataset','k','workload','seed'],suffixes=('','_csr'))
    df['speedup']=df.latency_us_csr/df.latency_us
    df.to_csv(ROOT/'data/results/kreach_all.csv',index=False)
    st.to_csv(ROOT/'data/results/kreach_index_stats.csv',index=False)
    pd.concat(timing,ignore_index=True).to_csv(ROOT/'data/results/kreach_timing.csv',index=False)
    pd.concat(cases,ignore_index=True).to_csv(ROOT/'data/results/kreach_cases.csv',index=False)
    agg=df.groupby(['dataset','k','workload','codec'],as_index=False).agg(
        mean_us=('latency_us','mean'),speedup=('speedup','mean'),speedup_min=('speedup','min'),speedup_max=('speedup','max'),
        mean_comparisons=('mean_comparisons','mean'),dense_probe_rate=('dense_probe_rate','mean'))
    agg.to_csv(ROOT/'data/results/kreach_aggregate.csv',index=False)
    facts={'query_instances':int(df[df.codec=='csr'].queries.sum()),'codec_answers':int(df.queries.sum()),'main_k':4,'datasets':{}}
    for name in DATASETS:
        a=st[(st.dataset==name)&(st.k==4)].set_index('codec')
        b=df[(df.dataset==name)&(df.k==4)&(df.codec=='adaptive')]
        s={c:float(a.loc[c,'total_bytes']/2**20)for c in POLICIES}
        facts['datasets'][name]=dict(index_mib=s,save_vs_csr=float(1-s['adaptive']/s['csr']),
            save_vs_dense=float(1-s['adaptive']/s['dense']),
            geomean_speedup=float(np.exp(np.log(b.speedup).mean())),
            dense_rows=int(a.loc['adaptive','dense_rows']),sparse_rows=int(a.loc['adaptive','sparse_rows']),
            cover=int(a.loc['adaptive','cover']),mode='sparse'if a.loc['adaptive','dense_rows']==0 else'mixed')
    (ROOT/'data/results/kreach_facts.json').write_text(json.dumps(facts,indent=2),encoding='utf-8')
    return df,st,agg,facts


def query_speed(df):
    fig,ax=plt.subplots(figsize=(5.5,1.95))
    for i,name in enumerate(DATASETS):
        for offset,workload,color,marker in [(-.13,'uniform',BLUE,'o'),(.13,'balanced',TEAL,'s')]:
            x=df[(df.dataset==name)&(df.k==4)&(df.codec=='adaptive')&(df.workload==workload)].speedup
            mean=x.mean()
            ax.errorbar(mean,2-i+offset,xerr=[[mean-x.min()],[x.max()-mean]],fmt=marker,
                        color=color,markersize=6,capsize=3,linewidth=1.5)
            ax.annotate(f'{mean:.2f}×',(mean,2-i+offset),xytext=(5,-9 if workload=='uniform' else 5),textcoords='offset points',fontsize=10,color=color)
    ax.axvline(1,color=GRAY,linewidth=1,linestyle='--')
    ax.set_yticks([2,1,0],[NAMES[n]for n in DATASETS],fontsize=10)
    ax.set_xlim(.75,3.05);ax.set_ylim(-.4,2.45)
    ax.set_xlabel('相对稀疏 CSR 的加速比（基线时间 / 自适应时间）',fontsize=10)
    ax.grid(axis='x',alpha=.6)
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([0],[0],marker='o',color=BLUE,linestyle='',label='均匀查询'),
                       Line2D([0],[0],marker='s',color=TEAL,linestyle='',label='50/50 正负查询')],
              loc='upper center',bbox_to_anchor=(.52,1.34),frameon=False,fontsize=9,ncol=2,
              handletextpad=.35,columnspacing=1.3)
    fig.tight_layout(pad=.3);save(fig,'query_speed')


def density_cdf():
    fig,ax=plt.subplots(figsize=(5.5,1.7))
    for name,color in zip(DATASETS,[BLUE,GOLD,TEAL]):
        counts=np.load(ROOT/f'data/results/kreach/{name}/k-4/row_density.npz')['counts']
        x=np.sort(counts)/len(counts)*100;y=np.arange(1,len(x)+1)/len(x)*100
        ax.plot(x,y,color=color,label=NAMES[name],linewidth=1.8)
    ax.axvline(100/17,color=GRAY,linestyle='--',linewidth=1)
    ax.text(100/17+1,17,'约 5.9%\n稀疏 / 稠密分界',fontsize=9,color='#62758B')
    ax.set_xlabel('一行中可达核心点的比例 / %',fontsize=10);ax.set_ylabel('累计行比例 / %',fontsize=10)
    ax.set_xlim(0,100);ax.set_ylim(0,103);ax.grid(alpha=.4)
    ax.legend(frameon=False,fontsize=9,loc='lower right')
    fig.tight_layout(pad=.3);save(fig,'row_density')


def robustness(df,st):
    fig,axes=plt.subplots(1,3,figsize=(5.5,1.9),sharey=True)
    for ax,name in zip(axes,DATASETS):
        for codec,label in [('csr','CSR'),('dense','Dense2'),('adaptive','Hybrid')]:
            a=st[(st.dataset==name)&(st.codec==codec)].sort_values('k')
            ax.plot(a.k,a.total_bytes/2**20,'o-',color=COLORS[codec],markersize=4,label=label,linewidth=1.5)
        ax.set_title(NAMES[name],fontsize=10);ax.set_xticks([2,4,6]);ax.set_xlabel('k',fontsize=10);ax.grid(axis='y',alpha=.5)
    axes[0].set_yscale('log');axes[0].set_ylabel('索引 MiB（对数）',fontsize=9)
    axes[-1].legend(frameon=False,fontsize=8,loc='best')
    fig.tight_layout(pad=.4,w_pad=.5);save(fig,'k_sensitivity')


def cases_plot():
    a=pd.read_csv(ROOT/'data/results/kreach_cases.csv')
    a=a[(a.dataset=='wiki-Vote')&(a.k==4)]
    fig,ax=plt.subplots(figsize=(5.5,2.0))
    for j,(c,label)in enumerate([('csr','稀疏 CSR'),('dense','全稠密'),('adaptive','自适应')]):
        sub=a[a.codec==c].set_index('case')
        x=np.arange(4)+(j-1)*.23
        ax.bar(x,[sub.loc[i,'latency_us']for i in range(1,5)],width=.23,color=COLORS[c],label=label)
    ax.set_xticks(range(4),['内→内','内→外','外→内','外→外'],fontsize=10)
    ax.set_ylabel('μs / 查询',fontsize=10);ax.legend(frameon=False,fontsize=9,ncol=3)
    ax.grid(axis='y',alpha=.5);fig.tight_layout(pad=.3);save(fig,'four_cases')


def original_evidence():
    # Direct transcription of ONE dataset in original Table 7; not our benchmark.
    fig,ax=plt.subplots(figsize=(2.85,1.4))
    labels=['μ-Reach','μ-Dist','μ-BFS'];values=[18.23,554.70,6852.91]
    ax.barh([2,1,0],values,color=[BLUE,GRAY,GRAY],height=.5)
    ax.set_xscale('log');ax.set_xlim(8,22000)
    ax.set_yticks([2,1,0],labels,fontsize=10)
    for y,v in zip([2,1,0],values):ax.text(v*1.15,y,f'{v:,.2f}',va='center',fontsize=9)
    ax.set_xlabel('百万查询总耗时 / ms（对数）',fontsize=9);ax.grid(axis='x',alpha=.4)
    fig.tight_layout(pad=.3);save(fig,'paper_nasa')


def cover_sensitivity():
    paths=list((ROOT/'data/results/kreach_cover').glob('seed-*/*/k-4/summary.csv'))
    if not paths:return
    extra=pd.concat([pd.read_csv(p).assign(cover_seed=int(p.parts[-4].split('-')[1]))for p in paths],ignore_index=True)
    main=pd.read_csv(ROOT/'data/results/kreach_all.csv');main=main[(main.k==4)&(main.seed==17)].copy();main['cover_seed']=17
    x=pd.concat([main,extra],ignore_index=True)
    base=x[x.codec=='csr'][['dataset','workload','cover_seed','latency_us']]
    h=x[x.codec=='adaptive'].merge(base,on=['dataset','workload','cover_seed'],suffixes=('','_base'))
    h['ratio']=h.latency_us_base/h.latency_us
    h.to_csv(ROOT/'data/results/kreach_cover_sensitivity.csv',index=False)
    fig,ax=plt.subplots(figsize=(5.5,2.0))
    for name,color,marker in zip(DATASETS,[BLUE,GOLD,TEAL],['o','s','^']):
        a=h[h.dataset==name].groupby('cover_seed').ratio.apply(lambda x:np.exp(np.log(x).mean()))
        ax.plot(a.index,a.values,marker=marker,color=color,label=NAMES[name],linewidth=1.5)
    ax.axhline(1,color=GRAY,linestyle='--',linewidth=1)
    ax.set_xticks([17,29,43]);ax.set_xlabel('覆盖构造随机种子',fontsize=10)
    ax.set_ylabel('相对 CSR 加速比',fontsize=10);ax.legend(frameon=False,fontsize=9,ncol=3)
    ax.grid(axis='y',alpha=.4);fig.tight_layout(pad=.4);save(fig,'cover_sensitivity')


def main():
    df,st,agg,facts=collect()
    query_speed(df);density_cdf();robustness(df,st);cases_plot();original_evidence();cover_sensitivity()
    print(json.dumps(facts,indent=2),flush=True)


if __name__=='__main__':main()
