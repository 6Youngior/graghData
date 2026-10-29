"""Numerical evidence and projection-sized charts for threshold dominance."""
import json
from pathlib import Path
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from graphio import ROOT,DATASETS
from kreach_figures import NAMES,BLUE,TEAL,GOLD,GRAY,NAVY
BLUE,TEAL,GOLD,GRAY='#245C91','#176B59','#A47C22','#718297'

OUT=ROOT/'data/results/dominance_figures';OUT.mkdir(exist_ok=True)
BASE={'Ranked-CSR':'Ranked-CSR','Join-CSR':'Ranked-CSR','Dominance-CSR':'Ranked-CSR',
 'DominanceJoin-CSR':'Join-CSR','Ranked-Adaptive':'Ranked-Adaptive',
 'Dominance-Adaptive':'Ranked-Adaptive','Source-Adaptive':'Ranked-Adaptive','Target-Adaptive':'Ranked-Adaptive'}


def save(fig,name):
    fig.savefig(OUT/f'{name}.pdf',bbox_inches='tight',pad_inches=.04)
    fig.savefig(OUT/f'{name}.png',bbox_inches='tight',pad_inches=.04,dpi=210)
    plt.close(fig)


def collect():
    folders=[p.parent for p in (ROOT/'data/results/dominance').glob('*/k-*/DONE.json')]
    df=pd.concat([pd.read_csv(p/'summary.csv')for p in folders],ignore_index=True)
    timing=pd.concat([pd.read_csv(p/'timing.csv')for p in folders],ignore_index=True)
    strata=pd.concat([pd.read_csv(p/'strata.csv')for p in folders],ignore_index=True)
    keys=['dataset','k','workload','seed'];lookup=df.set_index(keys+['variant']).latency_us
    df['baseline']=df.variant.map(BASE)
    df['speedup']=[lookup.loc[tuple(getattr(r,k)for k in keys)+(BASE[r.variant],)]/r.latency_us for r in df.itertuples()]
    df.to_csv(ROOT/'data/results/dominance_all.csv',index=False)
    timing.to_csv(ROOT/'data/results/dominance_timing.csv',index=False)
    strata.to_csv(ROOT/'data/results/dominance_strata.csv',index=False)
    facts=dict(query_instances=int(df[df.variant=='Ranked-CSR'].queries.sum()),
      method_answers=int(df.queries.sum()),main_k=4,datasets={})
    for name in DATASETS:
        a=df[(df.dataset==name)&(df.k==4)]
        raw=a[a.variant=='Ranked-Adaptive'];cut=a[a.variant=='Dominance-Adaptive']
        join=a[a.variant=='DominanceJoin-CSR']
        stats=json.loads((ROOT/f'data/results/dominance/{name}/k-4/build.json').read_text())
        def gm(values):return float(np.exp(np.log(values).mean()))
        facts['datasets'][name]=dict(pruning_speedup=gm(cut.speedup),join_pruning_speedup=gm(join.speedup),
          raw_mean_probes=float(raw.point_path_mean_probes.mean()),pruned_mean_probes=float(cut.point_path_mean_probes.mean()),
          probe_reduction=float(1-cut.point_path_mean_probes.mean()/raw.point_path_mean_probes.mean()),
          actual_probe_increase_queries=int(cut.point_path_increase_queries.sum()),
          queries=int(cut.queries.sum()),boundary_build_seconds=stats['boundary_build_seconds'],
          boundary_raw_bytes=stats['boundary_bytes']['raw'],boundary_pruned_bytes=stats['boundary_bytes']['both'],
          deployment_raw_bytes=stats['core_index_bytes']['adaptive']+stats['boundary_bytes']['raw'],
          deployment_pruned_bytes=stats['core_index_bytes']['adaptive']+stats['boundary_bytes']['both'],
          certificate_scratch_bytes=stats['max_certificate_scratch_bytes'],
          scratch_distance_bytes=stats['scratch_distance_bytes'])
    (ROOT/'data/results/dominance_facts.json').write_text(json.dumps(facts,indent=2),encoding='utf-8')
    return df,strata,facts


def speed_plot(df):
    fig,ax=plt.subplots(figsize=(6.5,2.6))
    value_labels=[]
    for i,name in enumerate(DATASETS):
        for offset,work,color,marker in [(.24,'uniform',BLUE,'o'),(-.24,'balanced',TEAL,'s')]:
            x=df[(df.dataset==name)&(df.k==4)&(df.variant=='Dominance-Adaptive')&(df.workload==work)].speedup
            mean=x.mean()
            ax.errorbar(mean,2-i+offset,xerr=[[mean-x.min()],[x.max()-mean]],fmt=marker,
                        color=color,markersize=6,capsize=3,linewidth=1.5)
            # Aligned value column keeps near-identical ratios apart and clear
            # of both the interval and the next dataset's labels.
            value_labels.append(ax.text(1.60,2-i+offset,f'{mean:.2f}×',
                ha='center',va='center',fontsize=12,fontweight='semibold',color=color))
    ax.axvline(1,color=GRAY,linewidth=1,linestyle='--')
    ax.set_yticks([2,1,0],[NAMES[n]for n in DATASETS],fontsize=12)
    ax.set_xlim(.78,1.69);ax.set_ylim(-.6,2.6);ax.grid(axis='x',alpha=.5)
    ax.set_xticks([.8,.9,1.,1.1,1.2,1.3,1.4])
    ax.axvspan(1.48,1.69,color='white',zorder=2)
    for label in value_labels:label.set_zorder(3)
    ax.set_xlabel('查询加速比（原边界时间 / 剪枝后时间）',fontsize=11)
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([0],[0],marker='o',color=BLUE,linestyle='',label='均匀查询'),
                       Line2D([0],[0],marker='s',color=TEAL,linestyle='',label='50/50 正负查询')],
              loc='lower center',bbox_to_anchor=(.44,1.04),frameon=False,fontsize=11,ncol=2,
              handletextpad=.35,columnspacing=1.3)
    fig.tight_layout(pad=.5)
    fig.canvas.draw()
    boxes=[label.get_window_extent(fig.canvas.get_renderer()).expanded(1.05,1.15) for label in value_labels]
    assert all(not a.overlaps(b) for i,a in enumerate(boxes) for b in boxes[i+1:])
    (ROOT/'data/results/plot_layout_check.json').write_text(json.dumps(dict(status='PASS',
        speed_value_labels=len(value_labels),value_label_overlaps=0,
        numeric_labels=[label.get_text() for label in value_labels]),indent=2),encoding='utf-8')
    save(fig,'pruning_speed')


def case_probes():
    name='wiki-Vote';folder=ROOT/f'data/results/dominance/{name}/k-4'
    with np.load(folder/'boundaries.npz')as f:rank=f['rank']
    values={v:[]for v in ['Ranked-Adaptive','Source-Adaptive','Target-Adaptive','Dominance-Adaptive']}
    for seed in [17,29,43]:
        with np.load(ROOT/f'data/results/kreach/{name}/k-4/balanced-{seed}-queries.npz')as f:q=f['queries']
        rs,rt=rank[q[:,0]],rank[q[:,1]]
        cases=np.where(rs>=0,np.where(rt>=0,1,2),np.where(rt>=0,3,4))
        for variant in values:
            with np.load(folder/f'balanced-{seed}-{variant}.npz')as f:p=f['point_path_probes']
            values[variant].append([p[cases==c].mean()for c in [1,2,3,4]])
    fig,ax=plt.subplots(figsize=(6.5,2.3))
    for j,(variant,label,color)in enumerate([('Ranked-Adaptive','原边界',GRAY),
            ('Source-Adaptive','仅出边界',GOLD),('Target-Adaptive','仅入边界',BLUE),
            ('Dominance-Adaptive','双侧剪枝',TEAL)]):
        x=np.arange(4)+(j-1.5)*.19
        ax.bar(x,np.array(values[variant]).mean(axis=0),width=.19,label=label,color=color)
    ax.set_xticks(range(4),['内→内','内→外','外→内','外→外'],fontsize=10)
    ax.set_ylabel('实际核心点对查找 / 次',fontsize=10);ax.grid(axis='y',alpha=.5)
    ax.legend(frameon=False,fontsize=10,ncol=4,loc='lower center',bbox_to_anchor=(.5,1.02))
    ax.set_ylim(0,max(np.array(v).mean(axis=0).max() for v in values.values())*1.12)
    fig.tight_layout(pad=.3);save(fig,'case_probes')


def k_plot(df):
    fig,ax=plt.subplots(figsize=(5.5,1.9))
    for name,color,marker in zip(DATASETS,[BLUE,GOLD,TEAL],['o','s','^']):
        a=df[(df.dataset==name)&(df.variant=='Dominance-Adaptive')].groupby('k').speedup.apply(lambda x:np.exp(np.log(x).mean()))
        ax.plot(a.index,a.values,marker=marker,color=color,label=NAMES[name],linewidth=1.5)
    ax.axhline(1,color=GRAY,linestyle='--',linewidth=1)
    ax.set_xticks([2,4,6]);ax.set_xlabel('k',fontsize=10);ax.set_ylabel('剪枝额外加速比',fontsize=10)
    ax.legend(frameon=False,fontsize=9,ncol=3,loc='lower center',bbox_to_anchor=(.5,1.02));ax.grid(axis='y',alpha=.4)
    fig.tight_layout(pad=.3);save(fig,'k_pruning')


def cover_plot(df):
    rows=[]
    for seed in [17,29,43]:
        source=df[(df.k==4)&(df.seed==17)]if seed==17 else pd.concat([
            pd.read_csv(p)for p in (ROOT/f'data/results/dominance_cover/seed-{seed}').glob('*/k-4/summary.csv')])
        base=source[source.variant=='Ranked-Adaptive'].set_index(['dataset','workload']).latency_us
        for r in source[source.variant=='Dominance-Adaptive'].itertuples():
            rows.append(dict(dataset=r.dataset,workload=r.workload,cover_seed=seed,
                             speedup=float(base.loc[(r.dataset,r.workload)]/r.latency_us)))
    a=pd.DataFrame(rows);a.to_csv(ROOT/'data/results/dominance_cover_summary.csv',index=False)
    fig,ax=plt.subplots(figsize=(5.5,1.9))
    for name,color,marker in zip(DATASETS,[BLUE,GOLD,TEAL],['o','s','^']):
        b=a[a.dataset==name].groupby('cover_seed').speedup.apply(lambda x:np.exp(np.log(x).mean()))
        ax.plot(b.index,b.values,marker=marker,color=color,label=NAMES[name],linewidth=1.5)
    ax.axhline(1,color=GRAY,linestyle='--',linewidth=1)
    ax.set_xticks([17,29,43]);ax.set_xlabel('覆盖构造随机种子',fontsize=10)
    ax.set_ylabel('剪枝额外加速比',fontsize=10);ax.legend(frameon=False,fontsize=9,ncol=3,loc='lower center',bbox_to_anchor=(.5,1.02))
    ax.grid(axis='y',alpha=.4);fig.tight_layout(pad=.3);save(fig,'cover_pruning')


def ablation(df):
    variants=['Ranked-Adaptive','Source-Adaptive','Target-Adaptive','Dominance-Adaptive']
    labels=['原边界','仅出边界','仅入边界','双侧剪枝']
    a=df[(df.dataset=='wiki-Vote')&(df.k==4)&(df.workload=='balanced')]
    fig,ax=plt.subplots(figsize=(5.5,1.9))
    vals=[float(np.exp(np.log(a[a.variant==v].speedup).mean()))for v in variants]
    ax.bar(range(4),vals,color=[GRAY,GOLD,BLUE,TEAL],width=.55)
    for i,v in enumerate(vals):ax.text(i,v+.02,f'{v:.2f}×',ha='center',fontsize=10)
    ax.axhline(1,color=GRAY,linestyle='--',linewidth=1)
    ax.set_xticks(range(4),labels,fontsize=10);ax.set_ylim(0,max(vals)+.3)
    ax.set_ylabel('相对原边界加速比',fontsize=10);ax.grid(axis='y',alpha=.4)
    fig.tight_layout(pad=.3);save(fig,'ablation')


def synthetic():
    a=pd.read_csv(ROOT/'data/results/dominance_synthetic/summary.csv')
    fig,axes=plt.subplots(1,2,figsize=(6.2,2.15))
    n=a[(a.variant=='Dense')&(~a.positive)].sort_values('degree')
    axes[0].plot(n.degree,n.raw_probes,'o-',color=GRAY,label='原边界')
    axes[0].plot(n.degree,n.pruned_probes,'s-',color=TEAL,label='剪枝')
    axes[0].set_xscale('log',base=2);axes[0].set_yscale('log')
    axes[0].set_xlabel('边界大小 d',fontsize=9);axes[0].set_ylabel('核心查找 / 次',fontsize=9)
    axes[0].set_xticks([4,8,16,32,64],['4','8','16','32','64'])
    axes[0].legend(frameon=False,fontsize=9,ncol=2,loc='lower center',bbox_to_anchor=(.5,1.02))
    for variant,label,color in [('Dense','Dense 原边界',GRAY),('Dominance-Dense','Dense 剪枝',TEAL),
            ('Join-CSR','CSR 求交',BLUE),('DominanceJoin-CSR','求交＋剪枝',GOLD)]:
        b=a[(a.variant==variant)&(~a.positive)].sort_values('degree')
        axes[1].plot(b.degree,b.latency_us,'o-',color=color,label=label,markersize=3,linewidth=1.2)
    axes[1].set_xscale('log',base=2);axes[1].set_yscale('log')
    axes[1].set_xticks([4,8,16,32,64],['4','8','16','32','64'])
    axes[1].set_xlabel('边界大小 d',fontsize=9);axes[1].set_ylabel('μs / 查询（对数）',fontsize=9)
    axes[1].legend(frameon=False,fontsize=9,ncol=2,loc='lower center',bbox_to_anchor=(.5,1.02),columnspacing=.8,handlelength=1.4)
    for ax in axes:ax.grid(alpha=.4)
    fig.tight_layout(pad=.3,w_pad=.5);save(fig,'synthetic')


def main():
    df,strata,facts=collect();speed_plot(df);case_probes();k_plot(df);cover_plot(df);ablation(df);synthetic()
    print(json.dumps(facts,indent=2))

if __name__=='__main__':main()

