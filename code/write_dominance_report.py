"""Generate the dominance report and slide numbers from paired raw evidence."""
import json,math
import numpy as np,pandas as pd
from graphio import ROOT,DATASETS
from kreach_figures import NAMES

GEN=ROOT/'docs/slides/generated'
def write(name,text):(GEN/name).write_text(text,encoding='utf-8')
def gm(x):return float(np.exp(np.log(x).mean()))


def main():
    df=pd.read_csv(ROOT/'data/results/dominance_all.csv')
    facts=json.loads((ROOT/'data/results/dominance_facts.json').read_text())
    audit=json.loads((ROOT/'data/results/dominance_audit.json').read_text())
    correct=json.loads((ROOT/'data/results/dominance_correctness.json').read_text())
    wiki=df[(df.dataset=='wiki-Vote')&(df.k==4)&(df.workload=='balanced')]
    raw=wiki[wiki.variant=='Ranked-Adaptive'];cut=wiki[wiki.variant=='Dominance-Adaptive']
    before=raw.point_path_mean_probes.mean();after=cut.point_path_mean_probes.mean()
    write('v3_probe_takeaway.tex',rf'{{\fontsize{{11}}{{13}}\selectfont 双侧剪枝将平均核心查找由 {before:.2f} 次降至 {after:.2f} 次，减少 {(1-after/before)*100:.0f}\%。\par 两端均在覆盖内时，查找过程保持不变。}}')
    f=facts['datasets']['wiki-Vote'];extra=(f['boundary_pruned_bytes']-f['boundary_raw_bytes'])/1024
    write('v3_constants.tex',rf'\newcommand{{\WikiPruningSpeed}}{{{f["pruning_speedup"]:.2f}}}'+'\n'+rf'\newcommand{{\WikiJoinSpeed}}{{{f["join_pruning_speedup"]:.2f}}}'+'\n')
    write('v3_query_takeaway.tex',rf'{{\fontsize{{11}}{{13}}\selectfont Wiki 上平均加速 {f["pruning_speedup"]:.2f} 倍；P2P 和 Email 的查询时间变化较小。\par Wiki 增加约 {extra:.0f} KiB 边界索引，构建约 {f["boundary_build_seconds"]:.2f}s。}}')
    rows=[];md=[]
    for name in DATASETS:
        for k in [2,4,6]:
            a=df[(df.dataset==name)&(df.k==k)]
            def us(v):return a[a.variant==v].latency_us.mean()
            join_ratio=gm(a[a.variant=='DominanceJoin-CSR'].speedup)
            adaptive_ratio=gm(a[a.variant=='Dominance-Adaptive'].speedup)
            rows.append(f'{NAMES[name]} & {k} & {us("Join-CSR"):.3f} & {us("DominanceJoin-CSR"):.3f} & {join_ratio:.2f} & {us("Ranked-Adaptive"):.3f} & {us("Dominance-Adaptive"):.3f} & {adaptive_ratio:.2f}'+r'\\')
            md.append(f'| {NAMES[name]} | {k} | {us("Join-CSR"):.4f} | {us("DominanceJoin-CSR"):.4f} | {join_ratio:.2f}× | {us("Ranked-Adaptive"):.4f} | {us("Dominance-Adaptive"):.4f} | {adaptive_ratio:.2f}× |')
    write('v3_full_table.tex',r'{\fontsize{8.5}{11}\selectfont\centering\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}llrrrrrr@{}}\toprule'+'\n'+
        r'图 & $k$ & Join & +剪枝 & 加速 & Hybrid & +剪枝 & 加速\\\midrule'+'\n'+'\n'.join(rows)+'\n'+r'\bottomrule\end{tabular*}\par}'+'\n'+r'\Micro{时间单位：$\mu$s/查询。Join / Hybrid 各自配对比较，避免把换编码的收益算到剪枝上。}')
    costs=[];costmd=[]
    for name,f in facts['datasets'].items():
        vals=[f['boundary_raw_bytes']/2**20,f['boundary_pruned_bytes']/2**20,
              f['deployment_pruned_bytes']/2**20,f['boundary_build_seconds'],f['certificate_scratch_bytes']/2**20]
        costs.append(f'{NAMES[name]} & '+' & '.join(f'{v:.2f}'for v in vals)+r'\\')
        costmd.append(f'| {NAMES[name]} | '+' | '.join(f'{v:.2f}'for v in vals)+' |')
    write('v3_costs.tex',r'{\fontsize{9}{11}\selectfont\centering\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lrrrrr@{}}\toprule'+'\n'+
        r'图 & 原边界/MiB & 剪枝/MiB & 总部署/MiB & 构建/s & 证书/MiB\\\midrule'+'\n'+'\n'.join(costs)+'\n'+r'\bottomrule\end{tabular*}\par}')
    f=facts['datasets']['wiki-Vote'];a=df[(df.dataset=='wiki-Vote')&(df.k==4)]
    saving=a[a.variant=='Ranked-Adaptive'].latency_us.mean()-a[a.variant=='Dominance-Adaptive'].latency_us.mean()
    break_even=math.ceil(f['boundary_build_seconds']/(saving*1e-6))
    facts['wiki_k4_conservative_break_even_queries']=break_even
    (ROOT/'data/results/dominance_facts.json').write_text(json.dumps(facts,indent=2),encoding='utf-8')
    write('v3_amortization.tex',rf'\Micro{{Wiki $k=4$：按构建时间 {f["boundary_build_seconds"]:.2f}s 与当前平均查询节省估算，约 {break_even/1e6:.2f} 百万次查询可分摊构建开销。}}')
    main_header='| 图 | k | CSR 求交 μs | 求交＋剪枝 μs | 额外加速 | Hybrid μs | Hybrid＋剪枝 μs | 额外加速 |\n|---|---:|---:|---:|---:|---:|---:|---:|\n'
    cost_header='| 图 | 原边界 MiB | 剪枝边界 MiB | 剪枝后总部署 MiB | 额外边界构建/s | 构建证书暂存 MiB |\n|---|---:|---:|---:|---:|---:|\n'
    summary=[]
    for name,v in facts['datasets'].items():
        summary.append(f'- {NAMES[name]}：相同 Hybrid 编码的剪枝额外加速 {v["pruning_speedup"]:.2f}×；CSR 求交基线加剪枝为 {v["join_pruning_speedup"]:.2f}×；平均核心查找减少 {v["probe_reduction"]*100:.1f}%。')
    report=f'''# K-hop 可达性查询：K-Reach 与阈值支配剪枝

## 主讲论文与本项目问题

主讲 James Cheng 等，**K-Reach: Who is in Your Small World**，PVLDB 5(11):1292–1303, 2012，[DOI](https://doi.org/10.14778/2350229.2350247)。精读覆盖 Definition 1、Algorithms 1–2、Theorem 1、§4.2.2–4.4、§5 和 Tables 7–9，详细笔记见 paper_review/K-Reach精读.md。主报告第 2 页介绍背景与问题，第 3–7 页解释论文框架、顶点覆盖、三档索引、四类查询及算例，第 8–12 页介绍改进方法及实验；原文 h-hop 扩展和实验放在附录 C。

原文用顶点覆盖 S 将任意端点接入核心，但覆盖外端点仍可能接入多个核心邻居，Case 4 最多形成邻居笛卡尔积。我们研究：**能否利用原索引已有的阈值信息，提前删除不增加任何成功可能的边界候选，同时保持精确性？**

研究静态、无权、有向图上的 d(s,t)≤k 查询，每个 k 分别建立索引并进行精确判定。原文讨论的有序表求交、压缩和高出度覆盖优先等方法在论文精读中介绍。按行稀疏/稠密编码作为物理表示基线，单独对照见《存储编码对照实验》。

## 改进：预算相关的边界支配

定义 R_b(u)={{v∈S | d(u,v)≤b}}，L_b(u)={{v∈S | d(v,u)≤b}}。若 R_b(y)⊆R_b(x)，则出边界里的 y 可以由 x 代替；入边界用 L 的包含关系。相等集合保留一个确定代表，留下包含极大的集合，得到边界反链。

有且只有两个相关预算：Case 2/3 使用 k−1，Case 4 使用 k−2。两层分别对应原两位码的 01/10 与 01，不需要新增距离精度或额外全图 BFS。入、出方向也分别处理，最终得到四组预算相关的边界列表；Case 1 保持原判定。

改进直接约简待枚举的核心点对。我们将集合支配用于 K-Reach 的两种预算、双向边界，推导安全替代条件，通过反链构造保存代表，再以见证替代证明查询结果保持不变。

## 关键反例：同一个边界，不能只选一组代表

在原论文 Figure 1 中增加 c→d，保持 S={{b,d,g,i}}，k=3，构造如下预算反例。

- 预算 1：R₁(b)={{b,d}}，R₁(d)={{d}}，应保留 b。
- 预算 2：R₂(b)={{b,d}}，R₂(d)={{b,d,g}}，应保留 d。

c→g 属于 Case 3，需要预算 2。若误用预算 1 的代表 b，会因 d(b,g)=3 而错误拒绝；正确保留 d 后，d(d,g)=2，答案 True。b、d 又位于同一 SCC，说明普通可达等价也不能替代有限预算下的支配判断。该反例已生成 Python / JavaScript 500 个全部点对/k 夹具。

## 精确性与构建

被删去的任意源候选 y，都有保留代表 x，且 R_b(y)⊆R_b(x)。若原见证 y→v 满足预算，则 x→v 也满足。若终点侧 v 又被代表 v′ 替代，L_b(v)⊆L_b(v′) 保证 x→v′ 仍满足。反向因为保留边界是原边界子集，故不会引入错误接受。单侧情况只替换一侧；同点和零距离按原实现处理。

构建按集合大小降序检查包含，相同大小用核心 ID 决定代表。先利用反射性的必要条件做 O(1) 检查，再用位集合验证包含，避免无效全扫描。输出恢复原 ID 顺序，以免把额外重排效果混入剪枝。完整实现和独立整数距离证书分别在 dominance.py / verify_dominance.py。

潜在候选上界不会增加，**实际提前停止前的查找数不保证逐查询减少**。代表可能出现在原顺序更后面。审计实际发现 {audit['actual_probe_increase_queries']} 条发生探测增加的查询条次，已保留；报告没有声称逐条或逐图都更快。

## 受控实验

三张 SNAP 有向图：Wiki-Vote（7115 点、103689 边）、Gnutella31（62586 点、147892 边）、Email-EuAll（265214 点、去自环后 418956 边）。主覆盖仍使用极大匹配种子 17；k=2/4/6，主结果固定 k=4。

完全复用之前已与完整 BFS 核对、并由 SciPy 抽样核验的查询：每图/k 两种分布、三个查询种子，各 5000 条。均匀分布是非零出度源/非零入度终点集合上的均匀；平衡分布正负各半，二者均非生产日志。

比较八种方案：预先转换为核心 ID 的原边界 CSR、有序表求交 CSR、双侧剪枝 CSR、求交加双侧剪枝 CSR、原边界 Hybrid、双侧剪枝 Hybrid、仅出边界 Hybrid、仅入边界 Hybrid。原边界预先转换 ID，避免把 ID 转换节省冒充剪枝收益。求交实现原文 §4.2.2 的邻接表求交，并按确定成本比较选择二分或顺序求交；它仍不代表作者 C++ 所有优化。

所有方案使用相同答案核，改变的只有边界列表、物理编码和明确的求交开关。统计在计时外执行。固定逻辑核 2、单线程、热态批查询，九次计时并打乱方案顺序，取中位数。主实验 54 个查询批次、270000 查询条次、432 个方案配置、2160000 次方法判定；保存 3888 条原始计时。没有训练或测试集调参，边界剪枝只读取图和 k。

## 主实验结果

{main_header}{chr(10).join(md)}

绝对 μs 先取每批九次中位数，再对两分布三个查询种子取算术平均；加速比按对应查询批次配对后取几何平均，因此并非汇总时间简单相除。主图按分布分别展示三个种子的均值与最小/最大范围，不是置信区间。

{chr(10).join(summary)}

Wiki 在两种查询分布下均有收益，在 CSR 求交基线之上也获得额外加速。P2P 的支配关系很少；Email 的原始平均查找次数已接近一次，可减少的工作有限。这两张图的查询时间变化较小，与其边界冗余较少的现象一致。

Wiki k=4 平衡查询的平均核心查找为 {before:.2f}→{after:.2f}，减少 {(1-after/before)*100:.1f}%。四类端点和出/入单侧消融分别展示，Case 1 按设计不受影响。时延结果与少查点对相互印证，不用“删掉多少候选”自动替代时间测量。

## 空间、预处理与分摊

{cost_header}{chr(10).join(costmd)}

总部署计入核心索引、共同 cover/rank 映射及预算相关的边界数组；不把所有对照方案同时驻内存的合计当作单个方案成本。原边界两层预算复用同一数组，按真实唯一数组计数；剪枝四组边界分别保存，所以可能增加空间。

构建使用原核心距离暂存及额外的阈值位集合证书。Email 原核心距离暂存约 1.23 GiB，额外证书约 315 MiB；这些不是最终索引，也不是进程峰值 RSS 的实测。证书可释放，当前没有流式构建优化。

Wiki k=4 的额外边界约 {extra:.1f} KiB，边界构建约 {f['boundary_build_seconds']:.2f}s。按全部边界构建成本保守分摊、当前每次查询平均节省估计，需约 **{break_even/1e6:.2f} 百万次**查询抵消预处理。这里展示重复查询服务的取舍，没有声称这次 30000 条测量查询就取得端到端净收益。其他两图缺少可靠收益，不能据此建议默认启用。

## 稳健性与机制压力测试

覆盖种子 29、43 在三图 k=4、两个分布、查询种子 17 上另跑，仍是相同查询的配对比较，保存 data/results/dominance_cover。主实验未挑覆盖种子。所有四类查询和按原候选积 1 / 2–4 / 5–16 / ≥17 的分层都保留，不只报最快子集。

受控合成图专门验证嵌套边界这一机制：两组有向核心各自形成包含链，32 个源端点和 32 个终点，边界大小 d=4/8/16/32/64，核心 ID 交错。负例查找 d² 次，正例 d(d−1)+1 次；剪枝均降至 1 次，实测与解析数量一致。固定全稠密 O(1) lookup 也能观察增长差异，另含 CSR 求交对照。它是机制压力测试，不能当作真实业务加速比，也不进入主实验统计。

## 独立验证

- 124 个小图（含三点全部有向图），所有点对、k=2/3/4/6、原边界/单侧/双侧及 CSR 求交，与独立 Python BFS 对照：{correct['method_answers']:,} 次答案通过。
- 主实验 2160000 次判定及覆盖稳健性补充共 {audit['all_method_answers']:,} 次，与相同完整 BFS 真值一致。
- 对全部真实图被消去的边界，使用直接整数距离检查逐项给出保留代表，验证集合包含；不依赖构建时的位打包实现。
- 原边界的核心查找次数逐条与之前论文基本实现一致，确保新基线没有偷偷换枚举逻辑。
- 课程反例的 Python/JS 对照、浏览器预算切换与离线运行检查另存；所有原始计时和证书审计随源码交付。

## 适用范围

适用于静态图上固定 k 的重复查询，尤其是边界邻居在对应阈值下有较多包含关系的情形。启用时需要同时考虑构建工作区、额外部署空间和预处理分摊。后续可研究按节点收益选择性剪枝，降低构建成本，并改进核心距离暂存与阈值集合的空间开销。

后续 VCRea（Tang 等，2023，[DOI](https://doi.org/10.3390/app13063470)）通过额外距离标签控制高出度端点的比较次数；本方案利用阈值包含关系消除冗余边界。近期 CSUR 综述（在线 2025 / 卷期 2026，[DOI](https://doi.org/10.1145/3776737)）用于定位 hop-constrained 查询及相关索引方法。这两篇论文作为文献比较，实验基线为已实现的 K-Reach 查询方式。
'''
    (ROOT/'docs/实验报告.md').write_text(report,encoding='utf-8')
    print(json.dumps(dict(status='generated',wiki_pruning_speedup=f['pruning_speedup'],
        wiki_extra_boundary_kib=extra,conservative_break_even_queries=break_even),indent=2))

if __name__=='__main__':main()

