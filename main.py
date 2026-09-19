"""
FastAPI 封装的 Arxiv 文献检索 Agent
对外暴露 REST API，可部署到任意支持 Python 的平台
"""

import os
import asyncio
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

from graph import graph

app = FastAPI(title="Arxiv Literature Agent", version="1.0.0")

# 允许跨域，方便前端调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TopicRequest(BaseModel):
    """请求体：用户输入的研究命题"""
    topic: str


class PaperInfo(BaseModel):
    title: str
    authors: list
    published: str
    summary: str
    pdf_url: str
    entry_id: str
    categories: list


class AgentResponse(BaseModel):
    """完整返回：检索式 + 文献 + 报告"""
    topic: str
    queries: list[str]
    papers: list[dict]
    report: str


@app.get("/")
def health_check():
    """健康检查"""
    return {"status": "ok", "service": "arxiv-literature-agent"}


@app.post("/api/search", response_model=AgentResponse)
def search_literature(req: TopicRequest):
    """
    根据命题检索 arxiv 文献并生成报告
    - topic: 研究命题，如 "transformer based medical image segmentation"
    """
    result = graph.invoke({"topic": req.topic})
    return AgentResponse(
        topic=result.get("topic", req.topic),
        queries=result.get("queries", []),
        papers=result.get("papers", []),
        report=result.get("report", ""),
    )


@app.post("/api/search/stream")
async def search_literature_stream(req: TopicRequest):
    """
    流式返回检索过程（SSE）
    依次输出: 检索式 → 文献列表 → 最终报告
    """
    async def event_generator():
        # 第一步：生成检索式
        from graph import generate_queries
        state = {"topic": req.topic, "queries": [], "papers": [], "report": ""}
        q_result = generate_queries(state)
        state.update(q_result)
        yield f"data: {q_result}\n\n"

        # 第二步：检索 arxiv
        from graph import search_arxiv
        s_result = search_arxiv(state)
        state.update(s_result)
        yield f"data: {s_result}\n\n"

        # 第三步：生成报告
        from graph import generate_report
        r_result = generate_report(state)
        state.update(r_result)
        yield f"data: {r_result}\n\n"

        yield "data: [DONE]\n\n"

    from fastapi.responses import StreamingResponse
    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
