# govplatform（受控知识与交付契约原型）

对应 `../docs/ai-engineering-governed-delivery-platform.md`（完整方案）和
`../docs/ai-engineering-governed-delivery-platform-baseline.md`（阶段决策
记录与验收状态）。当前已实现知识治理、交付契约、Harness 状态追踪、
本机人工审核与会话内验证/交付证据流程。跟
studyCompose 的 Android app 完全隔离，通过 MCP 接入 Claude Code / Codex。

## 能做什么

2026-11-04 新增本机审核页、`knowledge.list/get`、审核前快照与校验恢复。
从仓库根运行 `uv run --project platform python -m govplatform.review`，打开
<http://127.0.0.1:8765/>。使用方法与首批审核建议见 [知识操作说明](../docs/knowledge/README.md)。
原型 JSON API 仍只用于本机受信任调用；不要公开监听到网络。

### 1. 知识治理——提交、审核、检索

- **提交**（`knowledge.propose`）：AI 或你自己提交一条知识（规则、决策、
  踩坑记录……），落地状态是"待审核"，还搜不到。入库前会拦截疑似敏感信息
  （手机号/身份证号/token/密码类赋值）。
- **审核**（HTTP `POST /knowledge/{id}/approve`）：**只有你能做**，AI
  没有这个权限。通过后状态变"生效"，才能被搜到。
- **下线**（HTTP `POST /knowledge/{id}/deprecate`）：**只有你能做**，
  要求填 `reason`。批错了、过时了，把一条"生效中"的知识转成"已废弃"，
  转完 `search()` 自动搜不到它。没有"取消下线"——下线错了就重新提交一条
  新的，不做撤销的撤销。
- **检索**（`knowledge.search`）：BM25 关键词匹配 + 本地向量语义检索
  混合，搜"耦合"能找到正文写"依赖"的知识。结果带来源、版本、权威级别，
  还能看出这次搜索有没有真的用上语义那条路（`retrieval_mode`）。实现
  细节、已知的分数压平问题见 `docs/design-notes.md`。
- **时效校验**：知识可以设生效时间/失效时间，过期或者还没生效的知识
  即使状态是"生效"也不会被搜到。

### 2. 交付契约——把"什么算做完"写成可验证的东西

- **起草**（`contract.create`/`contract.update`）：验收标准（AC-*）必须
  拆成前置条件、操作、输入、预期结果、验证方式这几个具体字段，不能是
  一句"体验良好"；每条验收标准至少关联一条测试用例（TC-*）。`update()`
  要求传 `expected_version`（乐观锁，真正的原子保护在 store 层的
  `WHERE ... AND version = ?`），版本对不上就拒绝更新，防止并发覆盖。
- **冻结**（HTTP `POST /contracts/{id}/freeze`）：**只有你能做**。冻结前
  会校验验收标准结构、引用的知识是否有效、`open_questions` 是否清空，
  任何一条不满足就拒绝冻结并说明原因。冻结后不能再改。完整校验清单见
  `docs/design-notes.md`。
- **知识快照**：契约冻结那一刻，系统会把被引用知识当时的版本和内容指纹
  固化下来，以后知识再怎么变，这份快照不变。
- **豁免**（HTTP `POST /contracts/{id}/waivers`，**只有你能做**）：契约
  某条 AC 通不过、但你判断可以接受风险时用——必填理由/风险/到期时间
  （必须带时区、必须晚于当前时间），不允许永久豁免，到期自动失效
  （fail closed，不自动续期）。涉及生产数据/不可逆操作的 AC **不允许
  豁免**，必须真通过。设计依据（SOC2/DevSecOps 共识 + 大厂/Anthropic
  公开实践调研）见 baseline 文档 §7.3。

### 3. Harness——记录"开发→验收→修复"，由外部 Agent 驱动

对应原方案 §10，设计决策见 baseline 文档 §7。**`govplatform` 只是账本，
不是引擎**——只负责记录状态，真正驱动开发/验收子任务的是外部驱动方
（Codex 或 Claude Code 会话），见下方"架构限制"。

- **开始一次运行**（HTTP `POST /harness-runs`，**只有你能做**）：只有
  冻结的契约能开始。是否要开始一次运行是单独的人工点火动作，跟"契约
  被冻结"是两件事——不能拿"契约冻结过了"代替"现在要不要真的跑一次"。
- **入门禁**（`harness.record_entry_gate`）：构建/静态检查/测试有没有过。
  没过打回开发，不进入验收，不消耗修复轮次。
- **独立验收**（`harness.record_acceptance`）：逐条核对契约里的 AC。全部
  解决（通过，或者有有效豁免覆盖）才算过。未解决的里只要有一条是真的
  需要重新开发——还没到 3 轮修复上限就自动进下一轮修复，到了上限直接
  **升级**（终态）；如果未解决的**全部**是 `manual_evidence` 类型（代码
  没问题，就差人确认），停在 `WAITING_FOR_HUMAN`，不消耗修复轮次。
- **交付**（HTTP `POST /harness-runs/{id}/deliver`，**只有你能做**）：
  运行状态必须是"全部通过"才能标记交付；执行 Agent 记录自动结果，用户确认人工项，
  最终由用户执行交付。Harness 本身不启动开发或替用户确认结果。

**验收边界**：当前由执行 Agent 记录真实自动检查结果，用户确认人工 AC 与最终交付。
人工补审保留本轮已有自动证据，不把它改记成人工结果；明确不通过进入修复，待定项等待用户。
本机页面支持人工证据输入、知识废弃和取消误启动的运行。历史结果保存 recorded_by，旧数据未知就留空。
同一契约只允许一条进行中的运行；取消/交付/升级后的记录保留，之后才能另开一轮。

验证 CLI 可以实际执行统一检查并导入证据，说明见 `../docs/workflow.md`。
状态机仍不是后台开发调度器，编写代码与修复由当前 Agent 会话执行，不默认启动模型审查。

### 会话内验证与交付（T-025）

`python -m govplatform.delivery` 提供 `prepare / verify / submit / status`：
对用户已启动的运行建立准入快照、执行统一检查、提交自动验收证据并读取接续状态。
HEAD、源码指纹、日志及验证模式必须匹配；这些命令不能代替人工批准、冻结或启动运行。
完整命令与边界见 [执行与验收流程](../docs/workflow.md)。

T-025 已于 2026-11-06 经用户确认交付，记录见 [任务接续](../docs/tasks/t-025.md)。
2026-11-09 提交版本 `d4f5f5b` 的完整检查通过，平台 120 个测试通过；
这不表示其他任务的人工项或 Android 业务验收也已完成。

### 4. 身份与审计——谁做了什么，全程留痕

- 每一次操作都要声明"我是谁"——人（你）还是 AI（区分 Claude Code /
  Codex，各自带会话标识），不允许混用身份。
- 每个动作都记一条审计事件，包括被拒绝的操作（敏感信息被拦、结构校验
  没过）也记，只带失败原因分类，不带正文。

## 做不到什么（如实列出，不是等你踩坑才发现）

- **审计数据只写不读。** 没有任何工具能查询这张表，想知道"这条知识是谁
  批的"只能直接打开 SQLite 文件手写 SQL。
- **不同任务分别验收。** T-022 知识可用性和 T-025 会话闭环已有用户确认记录；
  T-023 仍保留人工待审项，Android T-014 已有正式运行，但设备补验与人工审查尚未完成。
  状态见 [TASKS.md](../TASKS.md)，不能把平台单测当作业务验收。
- **身份是自报的，不是密码学验证的。** 只适合本机受信任进程，不能防
  冒充，见 `docs/design-notes.md`"已知的信任边界"。
- **单机 SQLite，备份默认也在本机。** 已有一致性快照和恢复校验；异机备份仍需用户安排。
- **语义检索的分数在小语料库下压得很扁**，只能看排序前后，不能看数值
  判断"够不够相关"。
- **人工确认不等于防伪身份系统。** 自动化证据检查防止误用旧结果；同机受信任调用者仍可伪造文件或身份。
  验证模式由任务确定，CLI 只校验所选模式与证据一致，不自动理解契约语义。
- **没有后台持续开发调度。** 当前会话执行任务，文件和数据库保存接续；不承诺关闭会话后继续开发。

这些不是"以后要修的 bug 列表"，是这套原型现在的真实边界，做决策（比如
要不要拿它去接真实任务）之前应该知道的东西。

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

# MCP server（stdio）；客户端配置示例见根目录 .mcp.json
uv run python -m govplatform.mcp_server.server
```

MCP 暴露 `knowledge.list/get/search/propose`、`contract.create/get/update` 和
`harness.record_entry_gate/record_acceptance/get`。按所用客户端的配置方式添加服务，
将工作目录设为仓库根目录（或为 `--project` 使用绝对路径）；不要假定所有客户端都会自动加载 `.mcp.json`。

## 目录结构

见 `src/govplatform/`：

- `identity/` —— Human/Agent 身份模型，`resolve_principal()` 做白名单
  校验。
- `knowledge/` —— 知识对象、生命周期（propose/approve/deprecate/get）、
  敏感信息筛查（`sensitive.py`）。
- `embedding.py` —— 本地向量模型的加载与调用，`knowledge/` 和 `search/`
  都依赖它，两者互相不依赖。
- `search/` —— `index.py` 是 BM25，`hybrid.py` 是 BM25+向量的 RRF 融合，
  `service.py` 是对外入口。
- `contract/` —— 交付契约的模型/存储/生命周期 + 豁免。`service.py` 是
  薄的重新导出入口，实际逻辑按操作拆在 `_shared.py`/`update_service.py`/
  `freeze_service.py`/`waiver_service.py` 几个文件里（详见
  `docs/design-notes.md`），外部调用方仍然只用 `contract_service.X`。
  `freeze()` 时会调 `knowledge_service.get()` 校验 `knowledge_refs`，是
  唯一一处跨模块依赖。
- `harness/` —— Harness 运行状态追踪，只记录状态、不驱动真正的开发/
  验收。同样拆成 `_shared.py`/`acceptance_service.py`/`service.py`（薄
  入口）。`record_acceptance()` 时会调
  `contract_service.get_without_audit()`/`is_ac_waived()`，是它对
  `contract/` 的唯一依赖。
- `audit/` —— 审计事件的写入（目前没有对应的查询工具，见上文限制）。
- `review/` —— 本机人工审核页、任务确认、人工验收与一次性操作票据。
- `delivery/` —— 会话准入快照、统一检查证据导入与审查包生成。
- `backup.py` —— 本机数据库快照及恢复校验。
- `db/` —— SQLite schema 和连接管理。
- `mcp_server/` —— MCP 工具出口（`knowledge.*`、`contract.*`、
  `harness.*`——`harness.start`/`contract.freeze`/`request_waiver`/
  `deliver` 这类只有 Human 能做的动作不在其中，只走 HTTP）。
- `api/` —— 调试用 HTTP 薄层，每个路由都只是薄适配层，业务逻辑全在
  对应的 `*/service.py`。

## 详细设计参考

每块能力的实现细节、取舍理由和已知技术缺口，见 `docs/design-notes.md`
——检索算法/时效校验/交付契约完整校验清单/Harness 的两个校验细节/
`contract`&`harness` 模块拆分说明/已知的信任边界。写代码/改代码之前
先看那份文件，避免重复踩过的坑。
