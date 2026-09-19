# Arxiv 文献检索 Agent

基于 LangGraph 的多节点文献检索流水线，输入研究命题 → 自动生成检索式 → 检索 arxiv → 生成结构化报告。

## 项目结构

```
arxiv_literature_agent/
├── graph.py            # 核心 Agent 代码（3 节点流水线）
├── langgraph.json      # LangGraph CLI 配置
├── requirements.txt    # Python 依赖
├── .env.example        # 环境变量模板
├── .env                # 实际环境变量（需自行配置）
└── test_search.py      # arxiv 检索节点测试脚本
```

## Agent 流水线

```
用户命题 → [generate_queries] → [search_arxiv] → [generate_report] → 检索报告
```

| 节点 | 功能 |
|------|------|
| generate_queries | LLM 根据命题生成 3~5 个 arxiv 检索式 |
| search_arxiv | 用检索式调用 arxiv API，去重、按时间排序 |
| generate_report | LLM 汇总文献，生成 Markdown 结构化报告 |

## 快速开始

### 1. 配置环境变量

复制 `.env.example` 为 `.env`，填入你的 LLM API 配置：

```env
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-api-key-here
```

> 兼容任何 OpenAI 接口的服务（如 DeepSeek、通义、Moonshot 等），只需改 `BASE_URL` 和 `MODEL`。

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 启动本地 API 服务

```bash
langgraph dev
```

启动后访问 http://127.0.0.1:2024 可看到 LangGraph Studio 调试面板。

### 4. 调用 API 测试

```bash
curl -X POST http://127.0.0.1:2024/runs/stream \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "literature_agent",
    "input": {"topic": "DRY AMD therapeutic candidates"}
  }'
```

## 输入输出

- **输入**: `{"topic": "你的研究命题"}`
- **输出**:
  - `queries`: 生成的检索式列表
  - `papers`: 检索到的文献详情（标题、作者、日期、摘要、PDF 链接）
  - `report`: Markdown 格式的结构化检索报告

## 报告结构

1. 检索概述（命题 + 文献总数）
2. 核心文献概览（5~10 篇最相关文献）
3. 研究方向分布（主题归类总结）
4. 趋势观察（近期研究热点）
5. 建议下一步（推荐检索方向）
