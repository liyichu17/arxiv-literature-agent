"""
Arxiv 文献检索 Agent - LangGraph 多节点流水线
节点流程: 命题输入 → 检索式生成 → arxiv 检索 → 检索报告生成
"""

import os
import re
from dotenv import load_dotenv

# 显式加载 .env 文件，确保环境变量被正确读取
load_dotenv()

import arxiv
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


# ──────────────────────────── 状态定义 ────────────────────────────

class State(TypedDict):
    """Agent 全局状态"""
    topic: str               # 用户输入的命题/主题
    queries: List[str]       # 生成的检索式列表
    papers: List[dict]       # 检索到的文献列表
    report: str              # 最终检索报告


# ──────────────────────────── LLM 初始化 ────────────────────────────

def get_llm() -> ChatOpenAI:
    """从环境变量读取 LLM 配置，默认兼容 OpenAI 接口"""
    return ChatOpenAI(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        api_key=os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", "")),
        temperature=0.3,
    )


# ──────────────────────────── 节点 1: 检索式生成 ────────────────────────────

QUERY_SYSTEM_PROMPT = """你是一位学术文献检索专家。
根据用户给出的研究命题，生成 3~5 个 arxiv 检索式。

要求：
1. 每个检索式聚焦一个子方向，用 AND/OR/NOT 连接关键词
2. 关键词使用英文，贴合 arxiv 论文标题/摘要用语习惯
3. 检索式之间要有互补性，覆盖核心概念、方法、应用场景
4. 直接输出检索式列表，每行一个，不要编号、不要解释

示例输出：
"deep learning" AND "medical imaging" AND "diagnosis"
"transformer" AND "medical image segmentation"
"foundation model" AND "clinical" AND "arxiv"
"""


def generate_queries(state: State) -> dict:
    """根据用户命题生成 arxiv 检索式"""
    topic = state.get("topic", "")
    if not topic:
        raise ValueError(f"缺少 topic 输入，当前 state keys: {list(state.keys())}")

    print(f"[generate_queries] 收到命题: {topic}")
    llm = get_llm()
    messages = [
        SystemMessage(content=QUERY_SYSTEM_PROMPT),
        HumanMessage(content=f"研究命题: {topic}"),
    ]
    response = llm.invoke(messages)
    raw_text = response.content.strip()

    # 按行解析，过滤空行
    queries = [line.strip().strip('"').strip("'") for line in raw_text.split("\n") if line.strip()]
    # 去掉可能的编号前缀 (如 "1. xxx")
    queries = [re.sub(r'^\d+[\.\)]\s*', '', q) for q in queries]

    print(f"[generate_queries] 生成了 {len(queries)} 条检索式:")
    for i, q in enumerate(queries, 1):
        print(f"  {i}. {q}")

    return {"queries": queries}


# ──────────────────────────── 节点 2: arxiv 检索 ────────────────────────────

def search_arxiv(state: State) -> dict:
    """用生成的检索式在 arxiv 上检索文献"""
    queries = state.get("queries", [])
    if not queries:
        print("[search_arxiv] 没有检索式，跳过")
        return {"papers": []}

    client = arxiv.Client()
    all_papers = []
    seen_ids = set()

    for query in queries:
        print(f"[search_arxiv] 检索: {query}")
        search = arxiv.Search(
            query=query,
            max_results=5,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )
        try:
            for result in client.results(search):
                if result.entry_id in seen_ids:
                    continue
                seen_ids.add(result.entry_id)
                all_papers.append({
                    "title": result.title,
                    "authors": [a.name for a in result.authors],
                    "published": result.published.strftime("%Y-%m-%d"),
                    "summary": result.summary[:500],
                    "pdf_url": result.pdf_url,
                    "entry_id": result.entry_id,
                    "categories": result.categories,
                })
        except Exception as e:
            print(f"  检索出错: {e}")
            continue

    # 按发布日期倒序排列
    all_papers.sort(key=lambda x: x["published"], reverse=True)
    print(f"[search_arxiv] 共获取 {len(all_papers)} 篇去重文献")

    return {"papers": all_papers}


# ──────────────────────────── 节点 3: 检索报告生成 ────────────────────────────

REPORT_SYSTEM_PROMPT = """你是一位学术研究助手。
根据用户的研究命题和检索到的 arxiv 文献列表，生成一份结构化的中文检索报告。

报告结构：
1. **检索概述**：命题概述 + 检索到的文献总数
2. **核心文献概览**：列出 5~10 篇最相关的文献（标题、作者、年份、一句话亮点）
3. **研究方向分布**：按主题/方法对文献做归类总结
4. **趋势观察**：从发表时间、关键词分布看近期研究热点
5. **建议下一步**：推荐进一步检索方向或关键文献精读

要求：
- 使用 Markdown 格式
- 语言简洁专业，不要空话套话
- 每篇文献的亮点要具体，不要泛泛而谈
"""


def generate_report(state: State) -> dict:
    """根据检索结果生成结构化报告"""
    topic = state.get("topic", "未知命题")
    papers = state.get("papers", [])
    queries = state.get("queries", [])

    if not papers:
        return {
            "report": f"## 检索报告\n\n**命题**: {topic}\n\n未检索到相关文献，建议调整检索式或更换关键词后重试。"
        }

    # 把文献列表喂给 LLM
    papers_text = ""
    for i, p in enumerate(papers[:15], 1):
        authors_str = ", ".join(p["authors"][:3])
        if len(p["authors"]) > 3:
            authors_str += " et al."
        papers_text += (
            f"{i}. 标题: {p['title']}\n"
            f"   作者: {authors_str}\n"
            f"   发表日期: {p['published']}\n"
            f"   摘要: {p['summary'][:200]}...\n"
            f"   链接: {p['pdf_url']}\n\n"
        )

    llm = get_llm()
    messages = [
        SystemMessage(content=REPORT_SYSTEM_PROMPT),
        HumanMessage(
            content=f"研究命题: {topic}\n\n"
                    f"检索式: {' | '.join(queries)}\n\n"
                    f"检索到的文献 (共 {len(papers)} 篇):\n\n{papers_text}"
        ),
    ]
    response = llm.invoke(messages)
    report = response.content

    print(f"[generate_report] 报告已生成，长度 {len(report)} 字符")
    return {"report": report}


# ──────────────────────────── 构建 Graph ────────────────────────────

builder = StateGraph(State)

# 添加节点
builder.add_node("generate_queries", generate_queries)
builder.add_node("search_arxiv", search_arxiv)
builder.add_node("generate_report", generate_report)

# 设置入口
builder.set_entry_point("generate_queries")

# 线性流水线: generate_queries → search_arxiv → generate_report → END
builder.add_edge("generate_queries", "search_arxiv")
builder.add_edge("search_arxiv", "generate_report")
builder.add_edge("generate_report", END)

# 编译
graph = builder.compile()
