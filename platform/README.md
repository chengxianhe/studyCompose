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
- **检索**（`knowledge.search`）：配置本机 ES 后，对已批准知识按 Markdown
  标题分块，BM25 与 kNN 各召回最多 40 块，在平台内用 RRF 融合为最多
  30 块，再由本地中文 Cross-Encoder 对前 20 块重排。返回父知识来源、
  子块位置和相关性状态；`answer_assessment=not_assessed` 明确表示答案充分性尚未评估。
  未配置或 ES 故障时保留原有 SQLite 检索路径。
  实现与分数限制见 `docs/design-notes.md`。
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
  判断"够不够相关"；这是未配置 ES 时的旧检索路径。ES 路径使用本地
  Cross-Encoder 分数做相关性判断，阈值仍需随人工样本复核。
- **人工确认不等于防伪身份系统。** 自动化证据检查防止误用旧结果；同机受信任调用者仍可伪造文件或身份。
  验证模式由任务确定，CLI 只校验所选模式与证据一致，不自动理解契约语义。
- **没有后台持续开发调度。** 当前会话执行任务，文件和数据库保存接续；不承诺关闭会话后继续开发。

这些不是"以后要修的 bug 列表"，是这套原型现在的真实边界，做决策（比如
要不要拿它去接真实任务）之前应该知道的东西。

## 快速开始

```bash
cd platform
uv sync --locked
uv run python -m govplatform.model_cache prepare
HF_HUB_OFFLINE=1 uv run python -m govplatform.model_cache check
uv run python -m govplatform.rerank_model prepare
HF_HUB_OFFLINE=1 uv run python -m govplatform.rerank_model check
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

### 本地检索模型

`prepare` 把固定修订的 `Qdrant/bge-small-zh-v1.5` ONNX 模型预下载到
`platform/.data/models/`，逐文件核对源码记录的 SHA-256，并运行一次 512 维向量生成。
再次运行会验证已有文件，不重新下载。`check` 只读已缓存资产，不会尝试下载；
配合 `HF_HUB_OFFLINE=1` 可确认断网启动。该目录已被 Git 忽略，不随源码提交，
也不包含在知识数据库备份里；换电脑时需重新执行 `prepare`。

MCP、HTTP 与命令行检索都通过同一加载函数使用这个目录，无需单独启动模型服务。
如需改存储位置，启动 `prepare` 和 MCP 进程前都设置相同的绝对路径
`FASTEMBED_CACHE_PATH`。缺失或摘要不符时，`check` 明确失败；搜索仍按现有设计
降级为 `bm25_only`，不会把错误向量用于排序。模型修订或摘要若需更新，必须同时
评估 SQLite 中现有向量是否需要重算，不能只替换 ONNX 文件。

### 本机 ES 混合检索与重排

ES 是从 SQLite 已批准、未过期知识生成的派生索引，知识审核和备份仍以 SQLite 为准。
在本机安装并启动 [Elasticsearch 9.x](https://www.elastic.co/docs/deploy-manage/deploy/self-managed/install-elasticsearch-from-archive-on-linux-macos)，
将监听地址限制为本机；设置 `GOVPLAT_ES_URL` 后启用新检索链路。例如开发环境
可把 ES 监听在 `http://127.0.0.1:19200`。安全配置由 ES 安装方式决定；若启用
API Key 和 TLS，可同时设置 `GOVPLAT_ES_API_KEY`、`GOVPLAT_ES_CA_CERTS`。

```bash
export GOVPLAT_ES_URL=http://127.0.0.1:19200
HF_HUB_OFFLINE=1 uv run python -m govplatform.ingest sync
HF_HUB_OFFLINE=1 uv run python -m govplatform.ingest status
HF_HUB_OFFLINE=1 uv run python -m govplatform.ingest doctor
# 长时间运行时另开终端，负责审批/下线/到期后的自动同步：
HF_HUB_OFFLINE=1 uv run python -m govplatform.ingest watch
```

`sync` 按知识标题层级生成 child chunk，保存 `parent_id`、正文、来源、版本、
BM25 文本和 512 维向量；内容指纹不变时再次执行不会重建。`watch` 独立于
在线查询，每 5 秒检查审批、下线和时效变化，完整构建后原子切换 ES 别名。
索引未就绪时查询走原有 SQLite 路径；返回前仍以 SQLite 复核知识状态。
ES 索引可删除后重建，不属于知识数据库备份。
`doctor` 只读检查两套本地模型、ES 连接、集群状态、当前索引与可用磁盘，
返回 JSON；`ready: false` 时退出码为 1。正常切换时旧索引与别名一起移除；
失败构建会清理未发布目标，下次同步还会清理超过一小时且无别名的本项目孤儿索引。
ES 的免费 Basic 许可不包含内置 RRF，本项目在应用层融合两路 ES 结果，
无需开启试用或付费许可。[Elastic 许可说明](https://www.elastic.co/pricing/faq)。

仓库根目录的 `.mcp.json` 已为该项目的 MCP 服务设置本机 ES 地址；MCP 客户端
须重连或开启新会话才能读到新配置和工具字段。不读取 `.mcp.json` 的客户端需在
自己的 MCP 启动环境中设置同一个 `GOVPLAT_ES_URL`。ES 未启动时仍会回退 SQLite。

Codex 应核对实际生效的 `mcp_servers.govplatform.env.GOVPLAT_ES_URL`，不能只看
`.mcp.json`。本机曾因此缺少 ES 地址而持续降级；补正用户级该服务器配置并通过
`config/mcpServer/reload` 重载后，需分别核对新连接与当前绑定连接的工具目录和实际后端。
本次修复及运行状态见 [T-029](../docs/tasks/t-029.md)。
本机已下载的测试版 ES 可从仓库根目录启动：

```bash
ES_JAVA_OPTS="-Xms512m -Xmx512m" platform/.data/es/elasticsearch-9.5.6/bin/elasticsearch \
  -Ediscovery.type=single-node -Enetwork.host=127.0.0.1 \
  -Expack.security.enabled=false -Ehttp.port=19200
```

这是只监听本机的开发配置。启动后在另一终端运行上面的 `ingest watch`，
用 `ingest status` 确认 `ready: true`；磁盘接近 ES 默认水位时先腾出空间，
不要把本轮测试的临时水位设置当作长期配置。

`knowledge.search` 分别返回 `relevance_grade` 与 `answer_assessment`。
相关性 `pass` 仅表示候选可供阅读；答案评估当前始终为 `not_assessed`，
平台没有独立的语义判定器，不能据此推断资料已经足以回答。
`retry` 时保留原问题约束改写 query，把 `attempt` 从 0 依次递增到 1、2；
`insufficient` 表示本次检索最终未提供足够相关依据；`unavailable` 表示
相关性判定不可用，包括 SQLite 降级路径，需说明实际后端和模式。

宿主收到候选后，按原问题逐项核对所需信息、对象/版本/时间/适用范围、来源有效性与冲突，
以及每个关键结论的原文依据。片段不足时使用 `knowledge.get` 读取全文，重新核对状态和版本；
新读取结果与检索版本不一致时，应重新检索或说明待确认，不能将两个版本的证据混用。

| 宿主核对结论 | 回答方式 |
|---|---|
| 所需信息都有证据 | 给出有来源支持的答案，保留适用条件 |
| 只有部分信息有证据 | 只回答有依据的部分，并明确尚缺什么 |
| 证据不足 | 说明当前资料无法回答，指出需要补充的来源或信息 |
| 存在未解决的冲突 | 展示冲突及各自来源/范围，说明需要确认的取舍 |

例如报销材料清单与“报销网址是什么”主题相关，但未给出 URL 时不能提供地址；
API v1/v2 的调用指引也不能回答 API v3 的具体限流数字。
以上语义结论由宿主另行记录，不写成检索平台的已评估状态。
工具说明和字段不能强制所有宿主遵守核对步骤；测试协议返回也不能证明语义判断正确。

内部证据不足时，宿主继续识别缺口：缺对象才澄清，缺可查事实则在权限/预算内外查并读一手原文，
需要环境证明则执行已授权检查。即使 relevance pass，信息不全也不能直接结束任务。
补证后复核对象、版本、时间与冲突；无可靠资料、工具不可用或预算用尽时说明实际查证过程和停止原因。
内部改写仍最多两轮；外查共享任务预算，不发送私有原文或凭据，不把临时证据自动转成 active 知识。

新增 `govplatform.evaluation.evidence_trace.EvidenceTrace` 用于记录原问、工具观察、来源引文、
逐项要求和停止状态。它只做确定性结构/引用检查，不联网、不写知识、不调用模型；
`answer_assessment=host_reported` 属于这份宿主记录，search 响应仍为 `not_assessed`。
`host_observed` 与 `fixture_replay` 区分实际宿主走查与固定回放；工具观察仍需对照原始日志，
记录自报的真实性和语义是否充分不能由 schema 保证。
六类草案案例见 `evals/evidence-completion-v1.json`，实际范围和人工结论见 [T-031](../docs/tasks/t-031.md)。
该循环由当前会话完成，平台本身不调用云端 LLM API，也不提供无人值守的自动生成服务。

## 目录结构

见 `src/govplatform/`：

- `identity/` —— Human/Agent 身份模型，`resolve_principal()` 做白名单
  校验。
- `knowledge/` —— 知识对象、生命周期（propose/approve/deprecate/get）、
  敏感信息筛查（`sensitive.py`）。
- `embedding.py` —— 本地向量模型的加载与调用，`knowledge/` 和 `search/`
  都依赖它，两者互相不依赖。
- `ingest/` —— Markdown 分块和可重建 ES 索引。
- `rerank_model.py` —— 固定版本、文件摘要和断网校验的本地重排模型。
- `search/` —— ES 双路召回、应用层 RRF、本地重排与相关性判定；
  `index.py`/`hybrid.py` 保留 SQLite 降级，`service.py` 是统一入口。
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
## 来源与关系图谱（T-028）

图谱复用 SQLite，新增来源版本记录和三种关系：`derived_from`（知识→来源）、
`depends_on`（知识→前置知识）、`supersedes`（新知识→旧知识）。
来源由调用方提供，标记 `caller_reported`，平台不自动抓取或核验外部内容。
来源有 SHA-256 时按定位符+摘要去重；未知摘要必须提供显式 `idempotency_key`。
许可、归属和版本标签可登记为未知；登记时间不表示语义版本最新。

新 MCP 进程提供 `graph.source_register`、`graph.propose`、`graph.get/list`、
`graph.explain`、`graph.impact`。现有连接需重启/重连才能加载新增工具。
示例调用顺序（由宿主按 MCP 工具参数调用，不是 shell 命令）：

```text
graph.source_register(locator="来源定位符", content_hash="64位SHA-256", caller=Agent)
graph.propose(kind="derived_from", subject_id=已生效知识ID,
              target_source_id=来源ID, evidence_source_id=来源ID,
              reason="引用依据", applicability="适用范围", caller=Agent)
本人在本机审核页 /graph 查看证据并批准
graph.explain(knowledge_id=知识ID, caller=Agent)
graph.impact(key="source:来源ID", caller=Agent)
```

`depends_on/supersedes` 使用 `target_knowledge_id`，仍须来源证据、理由和适用范围。
只有当前有效知识才能作为提案端点；新内容沿用现有知识提案流程创建新 ID。
关系审核绑定端点版本/摘要和有效期；页面过期、并发修改或重复提交会被拒绝。
批准替代关系不会自动废弃旧知识，也不更改 `knowledge.search` 的结果或排序。

`graph.explain` 只沿可用关系展开；返回的 `usable:false` 关系仅是风险诊断。
`graph.impact` 沿已审核的派生/依赖关系反向查询，保留过期和撤销历史并标记风险；
`replacement_candidates` 另列替代指引，不将其作为依赖传播。
每个访问节点保留首条见证路径，并不枚举所有路径。默认 2 跳、最多 3 跳，
节点最多 100、关系（含替代候选）最多 200；证据来源元数据最多随这些关系返回 200 条。
检查 `truncated/cutoff_reasons`、`warnings` 和 `applicability`；潜在影响不是失效判决。
依赖循环可存在，替代循环拒绝；未批准就被撤销的候选不进入历史影响查询。

本机审核沿用 `uv run --project platform python -m govplatform.review`，打开
<http://127.0.0.1:8765/graph>。入口使用本机访问、CSRF、来源校验、一次性表单和端点快照，
操作前备份。新表为增量添加；SQLite 备份清单包含图记录，旧格式无图的备份仍可恢复到新路径。
完整设计、引用及验收状态见 [T-028](../docs/tasks/t-028.md)；总体方向见
[能力路线图](../docs/knowledge/capability-roadmap.md)。

## 小型检索质量基线（T-029）

`platform/evals/retrieval-v1.json` 是公开合成资料与 16 例草案标注，覆盖中文、英文、
新旧知识并存、过期/废弃过滤和无答案；不是人工验收通过的保留集。
从仓库根目录运行（输出文件必须不存在，其父目录须已存在）：

```bash
uv run --project platform python -m govplatform.evaluation \
  --dataset platform/evals/retrieval-v1.json --backend both \
  --es-url http://127.0.0.1:19200 --output /private/tmp/retrieval-quality-new.json
```

评测只在新建临时 SQLite 库中初始化合成知识，用独立 `govplatform_eval_*` 索引，
结束后清理临时库与该索引。没有生产库路径参数，不覆盖生产知识，不操作其审批状态。
合成人工批准只用于该临时夹具；`runner` 会临时切换进程环境，**只在独立 CLI 进程使用**，
不可挂到正在处理其他请求的 MCP/HTTP 进程。ES 地址只允许本机，不安装额外依赖或调用付费 LLM。

报告包含数据/代码摘要、固定模型修订、每例排序、Recall@5、MRR@10、无答案判定与耗时。
排名按父知识去重；查询固定 `attempt=2`，不评估自动改写或最终回答质量。
SQLite 本来没有相关性闸门，无答案指标记为未评分，不把 unavailable 或后端失败当成正确拒答。
执行失败/降级单列并返回非零；正常跑完但质量较差仍输出真实报告，不靠改标注或阈值变绿。
每个后端仅做一次未计分预热；构建、预热、查询时间分别报告，不声称严格性能基准。

当前实际结果与待改进案例见[质量报告](../docs/metrics/retrieval-quality-v1.md)。
