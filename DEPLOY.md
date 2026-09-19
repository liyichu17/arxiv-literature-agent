# 部署指南 - 免费平台上线

不用付费的 LangSmith Deployment，直接用 FastAPI 封装后部署到免费平台。

## 方案推荐：Render（最简单，免费额度够用）

Render 提供免费的 Web Service 托管，自动 HTTPS、自动部署。

### 第 1 步：把代码推到 GitHub

```bash
# 在项目目录下
git init
git add .
git commit -m "FastAPI version"
git remote add origin https://github.com/你的用户名/arxiv-literature-agent.git
git push -u origin main
```

### 第 2 步：在 Render 上部署

1. 打开 https://render.com/ 注册账号（可以用 GitHub 登录）
2. 点 **New +** → **Web Service**
3. 选择你刚推的 GitHub 仓库
4. 配置如下：
   - **Name**: `arxiv-literature-agent`
   - **Region**: 选离你近的（新加坡 / 俄勒冈）
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free

### 第 3 步：配置环境变量

在 Render 的 **Environment** 标签页添加：

| Key | Value |
|-----|-------|
| `LLM_MODEL` | `deepseek-chat` |
| `LLM_BASE_URL` | `https://api.deepseek.com/v1` |
| `LLM_API_KEY` | 你的 DeepSeek API Key |

> 不要把 `.env` 文件提交到 GitHub（已在 `.gitignore` 中排除）。

### 第 4 步：部署完成

点击 **Create Web Service**，等 2~3 分钟构建完成。
你会得到一个公网地址，类似：
`https://arxiv-literature-agent.onrender.com`

### 测试调用

```bash
curl -X POST https://你的地址.onrender.com/api/search \
  -H "Content-Type: application/json" \
  -d '{"topic": "transformer medical image segmentation"}'
```

---

## 替代方案：Railway（更省事，有试用额度）

1. 打开 https://railway.app/ 用 GitHub 登录
2. 点 **New Project** → **Deploy from GitHub repo**
3. 选择你的仓库，Railway 会自动识别 Python 项目
4. 在 Variables 标签页填入 `LLM_MODEL`、`LLM_BASE_URL`、`LLM_API_KEY`
5. Railway 会自动分配域名和端口，无需手动配置 Start Command

---

## API 接口说明

部署完成后，你有两个接口可用：

### 1. 同步接口（等全部跑完返回）

```
POST /api/search
Content-Type: application/json

{"topic": "你的研究命题"}
```

返回：
```json
{
  "topic": "...",
  "queries": ["检索式1", "检索式2"],
  "papers": [{"title": "...", "authors": [...], "pdf_url": "..."}],
  "report": "## 检索报告..."
}
```

### 2. 流式接口（SSE，逐步返回）

```
POST /api/search/stream
Content-Type: application/json

{"topic": "你的研究命题"}
```

依次返回：检索式 → 文献列表 → 最终报告

---

## 注意事项

1. **免费平台会休眠**：Render 免费版 15 分钟无请求会休眠，下次访问需要冷启动（约 30 秒）
2. **超时限制**：免费平台通常有 30~60 秒请求超时，检索式 + 文献检索 + 报告生成可能需要 1~2 分钟，如果超时建议用流式接口或升级付费版
3. **环境变量**：所有密钥都在平台后台配置，不要写死在代码里
