"""Check the paper-first delivery's numerical, source and presentation evidence."""
from pathlib import Path
import hashlib
import json
import re
import fitz
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]


def read(name):return json.loads((ROOT/'data/results'/name).read_text(encoding='utf-8'))


def main():
    data=pd.read_csv(ROOT/'data/results/kreach_all.csv')
    keys=['dataset','k','workload','seed','codec']
    assert len(data)==162 and not data.duplicated(keys).any()
    assert set(data.k)=={2,4,6}and set(data.codec)=={'csr','dense','adaptive'}
    assert not data.errors.any()
    assert int(data[data.codec=='csr'].queries.sum())==270000
    assert int(data.queries.sum())==810000
    for _,group in data.groupby(keys[:-1]):
        assert group.queries.nunique()==1 and group.mean_probes.nunique()==1
    timing=pd.read_csv(ROOT/'data/results/kreach_timing.csv')
    assert len(timing)==1458 and timing.groupby(keys).repeat.nunique().eq(9).all()
    med=timing.groupby(keys).us_per_query.median()
    for row in data.itertuples():
        key=tuple(getattr(row,k)for k in keys)
        assert np.isclose(row.latency_us,med.loc[key],rtol=1e-12)
    st=pd.read_csv(ROOT/'data/results/kreach_index_stats.csv')
    assert len(st)==27
    for _,group in st.groupby(['dataset','k']):
        a=group.set_index('codec').total_bytes
        assert a['adaptive']<=min(a['csr'],a['dense'])
    facts=read('kreach_facts.json')
    for name,value in facts['datasets'].items():
        a=st[(st.dataset==name)&(st.k==4)].set_index('codec')
        for codec,size in value['index_mib'].items():
            assert np.isclose(size,a.loc[codec,'total_bytes']/2**20)
        for k in [2,4,6]:
            p=ROOT/f'data/results/kreach/{name}/k-{k}'
            assert(p/'DONE.json').exists()
            for workload in ['uniform','balanced']:
                for seed in [17,29,43]:
                    with np.load(p/f'{workload}-{seed}-queries.npz')as q:
                        truth=q['answers'];distance=q['distance']
                        assert len(truth)==5000
                        assert np.array_equal(truth,(distance>=0)&(distance<=k))
                        for codec in ['csr','dense','adaptive']:
                            with np.load(p/f'{workload}-{seed}-{codec}-evidence.npz')as e:
                                assert np.array_equal(e['answers'],truth)
            if k==4:assert(p/'adaptive_index.npz').exists()
    sensitivity=pd.read_csv(ROOT/'data/results/kreach_cover_sensitivity.csv')
    assert len(sensitivity)==18 and set(sensitivity.cover_seed)=={17,29,43}
    dominance=pd.read_csv(ROOT/'data/results/dominance_all.csv')
    dkeys=['dataset','k','workload','seed','variant']
    assert len(dominance)==432 and not dominance.duplicated(dkeys).any()
    assert not dominance.errors.any()
    assert int(dominance[dominance.variant=='Ranked-CSR'].queries.sum())==270000
    assert int(dominance.queries.sum())==2160000
    dtiming=pd.read_csv(ROOT/'data/results/dominance_timing.csv')
    assert len(dtiming)==3888 and dtiming.groupby(dkeys).repeat.nunique().eq(9).all()
    dmed=dtiming.groupby(dkeys).us_per_query.median()
    for row in dominance.itertuples():
        key=tuple(getattr(row,k)for k in dkeys)
        assert np.isclose(row.latency_us,dmed.loc[key],rtol=1e-12)
        p=ROOT/f'data/results/dominance/{row.dataset}/k-{row.k}/{row.workload}-{row.seed}-{row.variant}.npz'
        with np.load(p)as e:
            assert len(e['answers'])==row.queries
            assert np.isclose(e['point_path_probes'].mean(),row.point_path_mean_probes)
    dfacts=read('dominance_facts.json')
    for dataset,v in dfacts['datasets'].items():
        a=dominance[(dominance.dataset==dataset)&(dominance.k==4)]
        cut=a[a.variant=='Dominance-Adaptive']
        assert np.isclose(v['pruning_speedup'],np.exp(np.log(cut.speedup).mean()))
        assert np.isclose(v['deployment_pruned_bytes'],cut.deployment_bytes.iloc[0])
    dcovers=pd.read_csv(ROOT/'data/results/dominance_cover_summary.csv')
    assert len(dcovers)==18 and set(dcovers.cover_seed)=={17,29,43}
    for name in ['kreach_correctness.json','kreach_audit.json','paper_example_check.json',
                 'paper_js_check.json','paper_demo_browser_check.json','theme_check.json',
                 'dominance_correctness.json','dominance_audit.json','dominance_example_check.json',
                 'dominance_js_check.json','comparison_examples_check.json','comparison_video_check.json','plot_layout_check.json']:
        assert read(name)['status']=='PASS',name
    daudit=read('dominance_audit.json')
    assert daudit['main_method_answers']==2160000 and daudit['all_method_answers']==2640000
    assert daudit['live_deployment_checkpoint_answers']==180000
    assert read('dominance_synthetic/definition.json')['status']=='PASS'
    audit=read('kreach_audit.json')
    assert audit['main_query_instances']==270000 and audit['main_method_answers']==810000
    assert audit['independent_scipy_distance_checks']==648
    build=read('pdf_build_check.json');visual=read('pdf_visual_audit.json')
    assert not build['warnings']and not visual['text_outside_page']
    pdf=fitz.open(ROOT/'docs/第十三组-期中汇报.pdf')
    assert len(pdf)==27
    assert(ROOT/'docs/slides/main.pdf').read_bytes()==(ROOT/'docs/第十三组-期中汇报.pdf').read_bytes()
    fonts={f[0]:f[3]for page in pdf for f in page.get_fonts()}
    assert all(pdf.extract_font(xref)[3]for xref in fonts)
    assert 'K-Reach'in pdf[0].get_text()and '第十三组'in pdf[0].get_text()
    assert '研究背景与问题定义'in pdf[1].get_text()
    assert 'Who is in Your Small World'in pdf[2].get_text()
    assert re.search(r'附录\s*A',pdf[13].get_text())
    main=(ROOT/'docs/slides/report.tex').read_text(encoding='utf-8')
    qa=(ROOT/'docs/slides/qa.tex').read_text(encoding='utf-8')
    paper=(ROOT/'docs/slides/paper.tex').read_text(encoding='utf-8')
    improvement=(ROOT/'docs/slides/improvement.tex').read_text(encoding='utf-8')
    assert sum(s.count(r'\begin{frame}')for s in [main,paper,improvement])==13
    assert qa.count(r'\begin{frame}')==14
    checked=missing=0
    for record in json.loads((ROOT/'data/source_manifest.json').read_text(encoding='utf-8')):
        path=ROOT/record['path']
        if not path.exists()and record['path'].startswith('docs/papers/'):
            missing+=1;continue
        assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256'],path
        checked+=1
    required=['README.md','docs/方法说明.md','docs/文献调研.md','docs/实验协议.md','docs/实验报告.md',
        'docs/十分钟讲稿与答辩.md','docs/paper_review/K-Reach精读.md',
        'docs/slides/main.tex','docs/slides/report.tex','docs/slides/paper.tex','docs/slides/improvement.tex','docs/slides/qa.tex','docs/slides/references.bib',
        'docs/slides/vendor-fdu/LICENSE','docs/slides/vendor-fdu/beamerthemefdu.sty','docs/slides/resources/fudan.pdf',
        'visualization/index.html','code/query.py','code/scripts/rebuild.ps1']
    required+=['visualization/方法对比.mp4','visualization/comparison_examples.json',
        'visualization/comparison_app.js','visualization/comparison_engine.js','code/comparison_examples.py',
        'code/scripts/render_comparison_video.py']
    assert all((ROOT/p).stat().st_size>0 for p in required)
    html=(ROOT/'visualization/index.html').read_text(encoding='utf-8')
    assert '<script src='not in html and '<link rel="stylesheet"'not in html
    video=read('comparison_video_check.json')
    assert video['width']==1920 and video['height']==1080 and video['fps']=='60/1'
    assert len(video['examples'])==3 and video['bytes']==(ROOT/'visualization/方法对比.mp4').stat().st_size
    result=dict(status='PASS',formal_configurations=432,query_instances=270000,method_answers=2160000,
        timing_records=3888,auxiliary_codec_answers=810000,live_deployment_answers=180000,
        logical_index_configurations=9,cover_sensitivity_rows=18,pdf_pages=27,main_slides=13,
        pdf_warnings=0,fonts_embedded=len(fonts),source_hashes_checked=checked,
        optional_reading_papers_omitted=missing,required_deliverables_present=True)
    (ROOT/'data/results/final_check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()

