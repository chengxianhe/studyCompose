# govplatform（阶段0/1 原型）

对应 `../docs/ai-engineering-governed-delivery-platform.md` 和
`../docs/ai-engineering-governed-delivery-platform-baseline.md`。这是受控
交付平台里知识治理部分的最小闭环原型：**提交知识 → 人工审核通过 → 通过
`knowledge.search` 检索到，带来源/版本/权威级别**。

## 范围

只做两个 MCP 工具：`knowledge.search`（只读）、`knowledge.propose`（写，
落地为 `in_review`）。审核通过走 HTTP `POST /knowledge/{id}/approve`，因为
阶段0没有对应的 MCP 工具。`contract.*`、`harness.*`、`evidence.query`、
向量检索+重排、Harness 状态机都不在这一轮范围内，属于原方案 §13 阶段2-4。

## 已知的信任边界

MCP 调用的 `caller` 字段是调用方自报的，服务端只做白名单校验
（`config.ALLOWED_AGENT_KINDS`），没有密码学身份验证。这套机制只保证审计
可追溯（谁在什么时候调用了什么），不是抵御恶意调用方的安全机制——阶段0
的使用者只有仓库所有者本人在本机运行的 Claude Code / Codex 两个受信任
进程，风险可接受。未来如果要接入不受信任的调用方，必须先补上真正的身份
验证再放开写权限。

`knowledge.propose` 入库前会对 title/body/source/tags 全部过一遍
`knowledge/sensitive.py` 里的正则筛查（手机号、身份证号、`password=`/
`token=`这类赋值），命中就拒绝入库，并记一条 `knowledge.propose.rejected`
审计事件（只带分类标签，比如"手机号"，不带原文）；`knowledge.search` 的
查询词写审计日志前也会做同样的脱敏。这是尽力而为的规则筛查，不是完整的
DLP 系统，拦不住故意变形过的敏感内容。

## 快速开始

```bash
cd platform
uv sync --locked
uv run pytest
uv run mypy --strict src tests
uv run ruff check .

# 手工跑通 HTTP 层
uv run uvicorn govplatform.api.app:app --reload
# 另开终端：
curl -X POST localhost:8000/knowledge/propose -H 'content-type: application/json' -d '{
  "title": "示例知识",
  "type": "reference",
  "body": "示例正文",
  "source": "manual-test",
  "authority_level": "reference",
  "caller": {"principal_type": "agent", "kind": "claude-code", "session_id": "manual"}
}'

# MCP server（stdio）
uv run python -m govplatform.mcp_server.server
```

## 目录结构

见 `src/govplatform/`：`identity/`（Human/Agent 身份模型）、
`knowledge/`（知识对象 + 生命周期）、`search/`（BM25 检索）、
`audit/`（审计事件）、`db/`（SQLite）、`mcp_server/`（MCP 工具出口）、
`api/`（调试用 HTTP 薄层，propose/search/approve 三个路由都只是薄适配层，
业务逻辑全在 `knowledge/service.py` 和 `search/service.py`）。
