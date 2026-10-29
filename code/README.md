# 代码

| 文件 | 用途 |
|---|---|
| kreach.py、bfs.py、graphio.py | K-Reach、完整 BFS 和图数据读取 |
| dominance.py | 两个预算、两个方向的边界支配剪枝 |
| *_experiments.py、dominance_synthetic.py | 真实图与合成图实验 |
| test_*.py、verify_*.py | 小图穷举和真实实验结果验证 |
| *_figures.py、write_*_report.py | 从保存结果生成图表与报告 |
| paper_example.py、dominance_example.py、comparison_examples.py | 论文示例、预算反例和真实查询动画数据 |
| build_kreach_demo.py | 构建离线网页 |
| query.py | 以 SNAP 原始节点编号执行查询 |
| scripts/ | 数据下载、PDF、动画视频和整体构建工具 |

在项目根目录运行 `powershell -ExecutionPolicy Bypass -File code/scripts/rebuild.ps1`。完整命令与环境见根目录 README。
