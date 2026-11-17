# 基于DSL的大模型智能体高效构建方法研究与实现

毕业设计代码仓库，包含两个基于领域特定语言（DSL）的大模型智能体方法实现、对比基线模型以及前端演示系统。

## 仓库结构

```
├── 全部源码/
│   ├── DSAGM/           # 基于DSL的智能体方法一（DSL → 中间表示 → 智能体装配）
│   │   ├── dsl/         # DSL 核心：词法分析、语法分析、AST、校验器、IR 生成、执行引擎
│   │   ├── DSAGM.py     # 实验入口
│   │   ├── cail_big/    # 大规模数据集目录（未上传，需自行放置）
│   │   ├── cail_small/  # 小规模数据集目录（未上传，需自行放置）
│   │   ├── 消融实验/     # 消融实验脚本（直接映射、去角色/记忆/规划/工具/目标等变体）
│   │   └── 超参/        # 超参数分析实验脚本
│   ├── DAPOM/           # 基于DSL的智能体方法二（约束抽取 → 张量约束空间 → 拉格朗日优化）
│   │   ├── main.py      # 评估入口（python main.py --dataset small|big）
│   │   ├── models/      # 对比模型：LLM-only / 规则 / 机器学习基线
│   │   ├── cail_big/    # 大规模数据集目录（未上传，需自行放置）
│   │   └── cail_small/  # 小规模数据集目录（未上传，需自行放置）
│   ├── baseline_models/ # 基线模型：BERT、Lawformer、TopJudge、NeurJudge、CL4LHP、ML-LJP、TF-IDF+SVM 等
│   └── 实验数据/        # 论文中各实验表格数据（CSV）
└── 系统/                # Vue2 + Element UI 前端演示系统
    └── vue2-element-UI-system-main/
```

## 运行说明

### 环境依赖

- Python 3.8+（后端实验：PyTorch、OpenAI 兼容 API 等）
- Node.js（前端系统，Vue2 + Element UI）

### 数据集

受 GitHub 单文件 100 MB 限制，CAIL（法研杯）训练/测试数据集（jsonl 格式，单个 200+ MB）未纳入仓库。
请将数据集按以下路径放置后即可运行：

| 路径 | 文件 |
|---|---|
| `全部源码/DSAGM/cail_small/` | `data_train.jsonl`、`data_test.jsonl`、`data_valid.jsonl` |
| `全部源码/DSAGM/cail_big/` | `train.jsonl`、`test.jsonl` |
| `全部源码/DAPOM/cail_small/` | `data_train.jsonl`、`data_test.jsonl`、`data_valid.jsonl` |
| `全部源码/DAPOM/cail_big/` | `train.jsonl`、`test.jsonl` |

> 完整数据打包版本见 [Releases](../../releases) 页面的 `graduation-code.zip`（约 380 MB）。

### 运行示例

```bash
# DAPOM 评估
cd 全部源码/DAPOM
python main.py --dataset small

# DSAGM 实验
cd 全部源码/DSAGM
python DSAGM.py

# 前端系统
cd 系统/vue2-element-UI-system-main
npm install
npm run serve
```

### LLM 配置

实验通过 `runtime_config` 加载大模型 API 配置（OpenAI 兼容接口），运行前请配置相应的 API 地址与密钥。
