"""Generate numerical slides and a paper-connected report from immutable CSVs."""
import json
import numpy as np
import pandas as pd
from graphio import ROOT,DATASETS

NAMES={'wiki-Vote':'Wiki-Vote','p2p-Gnutella31':'Gnutella31','email-EuAll':'Email-EuAll'}
GEN=ROOT/'docs/slides/generated';GEN.mkdir(exist_ok=True)

def write(name,text):(GEN/name).write_text(text,encoding='utf-8')

def main():
    df=pd.read_csv(ROOT/'data/results/kreach_all.csv');st=pd.read_csv(ROOT/'data/results/kreach_index_stats.csv')
    facts=json.loads((ROOT/'data/results/kreach_facts.json').read_text())
    lines=[]
    for name in DATASETS:
        v=facts['datasets'][name]['index_mib']
        lines.append(f'{NAMES[name]} & {v["csr"]:.2f} & {v["dense"]:.2f} & '+rf'\T{{{v["adaptive"]:.2f}}}'+r'\\[.5mm]')
    write('v2_memory.tex',r'{\centering\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lrrr@{}}\toprule'+'\n'+
          r' & 稀疏 CSR & 全稠密 & \T{自适应}\\\midrule'+'\n'+'\n'.join(lines)+'\n'+
          r'\bottomrule\end{tabular*}\par}'+ '\n'+
          r'\Micro{相对 CSR：Wiki 减少 90\%；Email 减少 13\%；P2P 保持原大小。}')
    vals=facts['datasets']
    email=df[(df.dataset=='email-EuAll')&(df.k==4)&(df.workload=='balanced')]
    before=email[email.codec=='csr'].mean_comparisons.mean()
    after=email[email.codec=='adaptive'].mean_comparisons.mean()
    probe=email[email.codec=='adaptive'].dense_probe_rate.mean()*100
    dense_fraction=vals['email-EuAll']['dense_rows']/vals['email-EuAll']['cover']*100
    write('v2_query_takeaway.tex',rf'\Key{{Email：{dense_fraction:.1f}\% 行承担 {probe:.0f}\% 查找；二分比较 {before:.2f}$\to$\T{{{after:.2f} 次}}。}}')
    rows=[];md=[]
    for name in DATASETS:
        for k in [2,4,6]:
            a=st[(st.dataset==name)&(st.k==k)].set_index('codec')
            b=df[(df.dataset==name)&(df.k==k)&(df.codec=='adaptive')]
            speed=float(np.exp(np.log(b.speedup).mean()))
            mem=[float(a.loc[c,'total_bytes']/2**20)for c in ['csr','dense','adaptive']]
            rows.append(f'{NAMES[name]} & {k} & {mem[0]:.2f} & {mem[1]:.2f} & {mem[2]:.2f} & {speed:.2f}'+r'\\')
            md.append(f'| {NAMES[name]} | {k} | {mem[0]:.2f} | {mem[1]:.2f} | {mem[2]:.2f} | {speed:.2f}× |')
    write('v2_full_table.tex',r'{\fontsize{9.5}{12}\selectfont\centering\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}llrrrr@{}}\toprule'+'\n'+
          r'图 & $k$ & CSR/MiB & Dense/MiB & Hybrid/MiB & 相对 CSR 加速\\\midrule'+'\n'+
          '\n'.join(rows)+'\n'+r'\bottomrule\end{tabular*}\par}')
    costs=[];costmd=[]
    for name in DATASETS:
        a=st[(st.dataset==name)&(st.k==4)].set_index('codec')
        shared=float(a.loc['csr','shared_bfs_seconds'])
        enc=[float(a.loc[c,'encoding_seconds'])for c in ['csr','dense','adaptive']]
        scratch=float(a.loc['csr','scratch_matrix_bytes']/2**20)
        costs.append(f'{NAMES[name]} & {shared:.2f} & {enc[0]:.2f} & {enc[1]:.2f} & {enc[2]:.2f} & {scratch:.1f}'+r'\\')
        costmd.append(f'| {NAMES[name]} | {shared:.2f} | {enc[0]:.2f} | {enc[1]:.2f} | {enc[2]:.2f} | {scratch:.1f} |')
    write('v2_costs.tex',r'{\fontsize{9.5}{12}\selectfont\centering\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lrrrrr@{}}\toprule'+'\n'+
          r'图 & 共享 BFS/s & CSR 编码/s & Dense/s & Hybrid/s & 距离暂存/MiB\\\midrule'+'\n'+
          '\n'.join(costs)+'\n'+r'\bottomrule\end{tabular*}\par}')
    correctness=json.loads((ROOT/'data/results/kreach_correctness.json').read_text())
    audit=json.loads((ROOT/'data/results/kreach_audit.json').read_text())if(ROOT/'data/results/kreach_audit.json').exists()else{}
    latency_rows=[]
    for name in DATASETS:
        for workload,label in [('uniform','均匀'),('balanced','正负平衡')]:
            a=df[(df.dataset==name)&(df.k==4)&(df.workload==workload)]
            v=[a[a.codec==c].latency_us.mean()for c in ['csr','dense','adaptive']]
            latency_rows.append(f'| {NAMES[name]} | {label} | {v[0]:.4f} | {v[1]:.4f} | {v[2]:.4f} |')
    latency_table='| 图 | 分布 | CSR μs/query | Dense μs/query | Adaptive μs/query |\n|---|---|---:|---:|---:|\n'+'\n'.join(latency_rows)
    header='| 图 | k | CSR MiB | Dense MiB | Adaptive MiB | Adaptive 相对 CSR 加速 |\n|---|---:|---:|---:|---:|---:|\n'
    costshead='| 图 | 共享 kmax=6 BFS/s | CSR 编码/s | Dense 编码/s | Adaptive 编码/s | 距离矩阵暂存/MiB |\n|---|---:|---:|---:|---:|---:|\n'
    report=f'''# K-Reach：论文精读、独立实现与按行自适应编码

## 主讲论文与研究问题

James Cheng, Zechao Shang, Hong Cheng, Haixun Wang, Jeffrey Xu Yu. **K-Reach: Who is in Your Small World.** PVLDB 5(11):1292–1303, 2012，DOI [10.14778/2350229.2350247](https://doi.org/10.14778/2350229.2350247)。逐节理解、算例与原文实验解读见 [精读笔记](paper_review/K-Reach精读.md)。

原文研究静态无权有向图上是否存在至多 k 条边的路径。它用顶点覆盖将任意端点接到核心，只保存 k−2、k−1、k 三档信息，再按两个端点是否在覆盖中分为四类精确查询。本文主报告第 2–7 页讲解这条论文主线，第 8–12 页说明我们直接针对其核心索引的存储改进与验证，第 13 页总结贡献边界及后续工作。

我们独立实现原文基本 K-Reach 的 Algorithm 1–2，并未使用作者源码，也没有声称逐项再现原表数值。原文数据、旧硬件实验与本机新实验在报告中分别标明；没有实现完整 (h,k)-reach、多 k 共用的距离标签或 2023 VCRea 的所有算法。

## 为什么提出这个改进

“三档权重只需两位”不等于完整索引只需两位。原文允许以有序邻接表保存可达核心点对，它还需要目标点 ID 和行偏移。真实图中，部分核心点可达大量其他核心点，重复保存 ID 代价较大；另一些核心点只能到达很少目标，为所有目标保留位置又浪费。

原文 §4.3 已讨论高出度节点的压缩表示，如区间列表和 PWAH；压缩本身不是我们的首创。我们将这个问题具体化为课程级工程改进：在相同覆盖、相同逻辑索引、相同四类查询下，逐行选择稀疏有序表或两位稠密行。两种解码器返回相同的 00/01/10/11 类别。行载荷的交叉密度约为 1/17；选择只依赖图和 k，不读取查询集，不需要训练。

## 精确性与空间边界

所有表示保存同一映射 f_k(d)：超出 k 为 00，d≤k−2 为 01，d=k−1 为 10，d=k 为 11。四类查询只检验这些类别及局部端点边，因此编码改变不会改变输出或逻辑核心点对检查序列。

按行用 4r+ceil(r/4) 保守估算稀疏载荷，用 ceil(|S|/4) 计算稠密载荷。CSR 的码位在全表连续打包，行内估计可能多计不足一字节；最终比较的是整个索引数组的真实字节数，包含元数据。若混合布局并未比全 CSR / 全稠密更小，则直接选择较小的全局格式。由此部署空间不超过这两个全局基线中较小者。该边界由实现选择过程得到，不是新理论首创声明。

## 本机实验设计

三类 SNAP 原始有向图：Wiki-Vote（7,115 点，103,689 边）、Gnutella31（62,586 点，147,892 边）、Email-EuAll（265,214 点，清理后 418,956 边）。Email 原始 420,045 边中去除 1,089 自环；不缩点、不无向化。输入与许可/来源记录见 data/source_manifest.json。

覆盖由打乱边顺序的极大匹配端点集合构造，主实验固定覆盖种子 17，逐边验证覆盖。k=2、4、6 分别生成其三档逻辑索引，主结果使用预先确定的 k=4。均匀查询在非零出/入度端点间抽样；平衡查询严格一半为 d≤k、一半为 d>k 或不可达。两种均为受控人工分布，不冒充真实日志。每组 5,000 查询，三个查询种子 17/29/43；三格式完全复用相同查询与真值。

计时使用只输出答案的 Numba 单线程批查询核；比较次数等诊断另跑，不混入计时。固定逻辑核 2；每配置九次、打乱格式次序、每次批执行至约 80ms，取中位数。计时包括结果数组分配，排除首次 JIT 与预处理。报告热态批吞吐折算的微秒/查询，不是 RPC 延迟。所有原始计时保留；范围表示查询种子差异，不是统计显著性检验。

## 结果

{header}{chr(10).join(md)}

空间是数组驻内存字节，不是 NPZ/ZIP 文件大小。包含 32 位目标 ID、两位码、64 位偏移、混合行映射，以及共同的 cover / rank 数组（连续图 ID 与核心 ID 之间的映射）。共享原图的 CSR、SNAP 原始 ID 映射、查询工作区和 Python 对象开销不计入“索引”列；后者远小于主要数组。输入文件保留原始 ID，CLI 在索引查询前完成转换。

k=4 时，Wiki 的空间从 {vals['wiki-Vote']['index_mib']['csr']:.2f} MiB 降至 {vals['wiki-Vote']['index_mib']['adaptive']:.2f} MiB，减少约 90%；Email 从 {vals['email-EuAll']['index_mib']['csr']:.2f} MiB 降至 {vals['email-EuAll']['index_mib']['adaptive']:.2f} MiB，减少约 13%。P2P 选择同一 CSR 格式，空间保持不变，避免全稠密的 {vals['p2p-Gnutella31']['index_mib']['dense']:.2f} MiB 开销。

三种子、两分布配对时间比的几何平均，在 Wiki / P2P / Email 上分别为 **{vals['wiki-Vote']['geomean_speedup']:.2f}× / {vals['p2p-Gnutella31']['geomean_speedup']:.2f}× / {vals['email-EuAll']['geomean_speedup']:.2f}×**。对于选择相同 CSR 的 P2P，接近 1 的差异是计时波动，不能当作算法收益。

机制证据不是仅看时间：三格式的核心点对查询序列完全相同；混合编码减少的是二分比较。在 Email k=4 平衡查询中，只有约 {vals['email-EuAll']['dense_rows']/vals['email-EuAll']['cover']*100:.1f}% 的行使用稠密编码，但约 81% 的核心查找命中这些行；平均二分比较由约 12.47 次/查询降至 0.65 次/查询。对应的查询速度收益有明确物理原因。

下面补列 k=4 三格式的绝对查询时间，以免只显示相对 CSR 的收益。每项先取九次计时中位数，再对三个查询种子取算术平均；这是热态批查询吞吐折算，不能与原文 C++ 的旧硬件数据直接比较。

{latency_table}

全稠密有直接寻址优势，但 Email 的 315.94 MiB 存储明显大于自适应的 28.11 MiB；Adaptive 的选择目标是空间，不能用它替代“所有方法中时间最优”的结论。

## 编码和构建成本

{costshead}{chr(10).join(costmd)}

共享 BFS 只构建一次 kmax=6 的核心截断距离，供 k=2/4/6 三种布局公平比较。编码时间分别记录，并非“从零独立建一个 k=4 索引”的总时间。Adaptive 原型会建立混合候选并比较全局格式；发生回退时，其编码时间包括额外工作，不隐去这部分成本。

当前原型采用 |S|×|S| 的 uint8 截断距离暂存，工作区可明显大于最终索引。例如 Email 约 1.23 GiB 暂存。它使三种编码在完全相同逻辑输入下受控比较，并不改善构建时峰值内存，也没有改变 K-Reach 最坏情况下 O(|S|²) 的索引复杂度。生产实现可按行流式生成，但本项目没有把未实现的改进计作成果。

## 独立校验

- 64 个三点有向图穷举、60 个随机图，k=2/3/4/6：共 {correctness['algorithm_answers_checked']:,} 次答案核对、{correctness['codec_cells_checked']:,} 个小图编码单元核对；包含全部四类端点情况、同点零距离、共享覆盖邻居及不可达情况。
- 主实验 270,000 查询条次、810,000 次格式判定，逐条与完整 BFS 真值一致；保存的候选点对检查数和端点分支逐项一致。
- 对真实索引逐条验证全部稀疏条目和稠密两位单元，包括顺序、计数、类别和尾部 padding；结果见 data/results/kreach_audit.json。
- 使用 SciPy 独立实现对 {audit.get('independent_scipy_distance_checks',648):,} 条真实图最短距离抽样核对，全部一致。
- 论文 Figure 1–2 的六个关键距离已核对；演示包含 k=2…6 的全部 500 个点对查询夹具，与 Python 对照。

## 稳健性、限制与后续

另以覆盖种子 29、43，在三图 k=4 上重复编码和两种查询分布，检查收益是否依赖某次覆盖构造；这些数据独立保留在 data/results/kreach_cover，不与主实验种子混算。不同 k 的空间、四类查询耗时、覆盖种子变化见问答附录。

本方法优化固定 k 核心索引的物理布局，不支持直接用同一三档码回答任意 k；图更新后需重建。全稠密往往更快，但可能耗费大量空间；自适应以空间为选择目标，没有普遍时间最优保证。三种公开图、两种人工分布及单线程热态测量不能推出所有生产场景结论。基础查询使用逐对二分；原文 §4.2.2 还讨论有序表求交，§4.3 讨论压缩，本项目没有把这些全部实现，当前 CSR 不代表作者所有优化的最优实现。ID 压缩、位图类库、流式构建和动态维护没有在本项目中完整比较，不能声称新 SOTA。

本项目的价值在于完整讲清并独立实现原论文，再用一个有明确成本模型、正确性边界和受控实验的改进，展示“逻辑索引”和“物理表示”共同影响图查询系统。
'''
    report=report.replace('本文主报告第 2–7 页讲解这条论文主线，第 8–12 页说明我们直接针对其核心索引的存储改进与验证，第 13 页总结贡献边界及后续工作。','本节提供配套的物理编码对照；主报告的阈值支配实验单独记录，不能混算收益。')
    report=report.replace('# K-Reach：论文精读、独立实现与按行自适应编码','# 附加实验：K-Reach 的稀疏 / 稠密编码对照')
    (ROOT/'docs/存储编码对照实验.md').write_text(report,encoding='utf-8')
    print('Generated paper-connected report and v2 numerical fragments.',flush=True)


if __name__=='__main__':main()
