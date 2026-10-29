# 数据与实验结果

- `raw/`：SNAP 原始有向图压缩文件。
- `processed/`：正向、反向 CSR 和原始节点编号映射。
- `results/kreach/`：完整 BFS 真值、查询及核心编码检查点。
- `results/dominance/`：剪枝主实验、逐次计时、答案及边界检查点。
- `results/dominance_cover/`、`results/kreach_cover/`：覆盖随机种子补充。
- `results/dominance_synthetic/`：受控合成图定义与结果。
- `results/*_figures/`：由实验数据生成的图表。
- `results/*.csv`、`results/*.json`：汇总结果和检查记录。

图数据来自 [Stanford SNAP](https://snap.stanford.edu/data/) 的 Wiki-Vote、p2p-Gnutella31、Email-EuAll。下载地址和文件校验值见 `source_manifest.json`，获取脚本为 `code/scripts/acquire.py`。

`archive/` 保存本地历史版本，`results/preview/` 保存预览和临时渲染帧；这两类文件不提交到仓库。
