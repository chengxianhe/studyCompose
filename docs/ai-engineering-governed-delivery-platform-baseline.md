# 受控交付平台 · 阶段0 落地基线

> 配套文档：`docs/ai-engineering-governed-delivery-platform.md`（方案原文）。
> 本文件记录该方案 §14「需要团队确认的设计决策」在本次试点中的实际结论，
> 以及技术栈、落地位置等阶段0需要先钉死的选择。原方案本身不改，避免混淆
> "设计"和"决策记录"。

## 1. 试点范围

- 试点项目：`studyCompose` 本身（对应原方案 §14.8）。
- 使用者：目前只有仓库所有者一人 + 多个 Agent（Claude Code、Codex）接入，
  没有多人多角色场景，因此原方案里完整的空间层级/RBAC 模型（§14.1）在
  阶段0/1 不展开，先用最小身份模型（见第 4 节），后续真有多人协作需求时
  再按 §14.1 扩展。
- 落地位置：仓库根目录新增 `platform/` 目录，与现有 Gradle 多模块体系
  （`app/`、`feature/*`、`core/*`、`domain/*`、`data/*`）完全隔离，不接入
  `settings.gradle.kts`，不受 `build-logic` 约定插件管理，有自己独立的
  依赖锁定和 CI 检查线。`CLAUDE.md` 里对 feature/domain/data 分层、设计
  系统 token、Konsist 断言等硬性规则，只约束 Android 代码，不适用于
  `platform/` 目录。

## 2. §14 决策清单结论

| # | 决策项 | 阶段0/1 结论 |
|---|---|---|
| 1 | 空间层级、跨空间引用、角色权限 | 阶段0/1 只有一个空间（试点项目本身），角色只分「人类所有者」和「Agent」两类，不做跨空间引用。真正多团队/多项目时再引入空间层级。 |
| 2 | 哪些知识类型必须人工审核 | 组织规范/项目规范/领域知识三类必须审核；项目事实（自动采集）、经验知识先不强制审核。阶段0/1 审核人只有仓库所有者一人。 |
| 3 | 敏感信息识别、脱敏、审计保留 | `knowledge.propose` 入库前对 title/body/source/tags 做正则筛查（手机号/身份证号/`password=`这类赋值），命中就拒绝入库并记一条只带分类标签、不带原文的 `knowledge.propose.rejected` 审计事件，见 `knowledge/sensitive.py`——这是尽力而为的规则筛查，不是完整 DLP，拦不住刻意变形的内容。`knowledge.search` 的查询词写审计前会先脱敏。审计日志保留期目标 90 天，但清理/归档任务还没做，库里数据量还小，不着急，等数据量上来了再补。 |
| 4 | 规则冲突最终裁决人 | 仓库所有者。 |
| 5 | 哪些验收项必须自动化 | Android 侧现有 `./gradlew :konsistTest:test detekt lint test` 全部保留为强制自动化门禁，不受本平台影响。平台自身新增的「知识/契约/Harness」相关验收，阶段0/1 允许人工证据，不强求自动化。 |
| 6 | 三轮修复后谁接收阻断 | 阶段0/1 只有仓库所有者，阻断直接升级给本人，不做角色分流。 |
| 7 | 知识/证据/代码/日志的存储边界与合规要求 | 阶段0/1 无外部合规要求（无真实用户数据），存储边界 = `platform/` 自身的数据库和对象存储，不与 Android app 的生产数据/日志混放。 |
| 8 | 首个试点项目、验收基线、成功指标 | 试点项目 = `studyCompose`；验收基线 = 现有 CLAUDE.md 自检要求；成功指标见第 5 节。 |

## 3. 技术栈决策

- 语言/框架：**Python + FastAPI + Pydantic**。
- 工具出口：**MCP Python SDK**（官方 SDK 中示例和文档最完整的一档）。
- 自检线（对应 Android 侧 `konsistTest/detekt/lint/test`）：
  **mypy --strict + ruff + pytest**，纳入独立 CI job，不进现有三级门禁。
- 选型理由：知识检索相关的生态（embedding、BM25、rerank、向量库客户端）
  在 Python 里现成的库和参考实现最多；MCP Python SDK 最成熟。代价是失去
  Kotlin sealed class + `when` 在编译期强制状态机穷尽的免费保障，需要靠
  `mypy --strict` + `Enum`/`Literal` + `assert_never` 人为补上，并在 CI 里
  强制检查，不能靠人工记得住。

## 4. 身份模型（阶段0最小版）

```text
Principal
  ├─ Human(id)                      # 目前只有仓库所有者
  └─ Agent(kind, session_id)        # kind: "claude-code" | "codex" | ...
```

- 每一次 MCP 调用、每一条审计事件都必须携带 `Principal`，不允许用人的身份
  代表 Agent 的操作，也不允许 Agent 之间共用身份。
- 权限模型阶段0极简：`Human` 拥有全部权限；`ALLOWED_AGENT_KINDS`
  白名单里的 Agent（目前是 `claude-code`、`codex`）从第一天起就同时拥有
  `knowledge.search`（读）和 `knowledge.propose`（写）——这是有意的选择，
  不是"先只读再逐步开放"那个分阶段模型：`knowledge.propose` 只会把知识写成
  "待审核"状态，不会让它生效，真正有实际影响的操作是审核通过
  （`knowledge.approve`），那一步已经在代码里强制只有 `Human` 能做。
  `decision.record`、`contract.create/update`、`harness.run` 这些阶段2+
  才会有的工具，到时候再单独定它们的权限模型，不在这份最小版里预先假设。
- 现在读、写用的是同一份白名单（`config.py` 里的 `ALLOWED_AGENT_KINDS`），
  没有分开。如果以后需要单独收回某个 Agent 的提交权限（比如它老是提交垃圾
  内容）而不影响它的检索权限，到时候再把写权限拆成单独的白名单，现在没有
  这个需求，不提前做。

## 5. 阶段0/1 成功指标

- [x] `platform/` 能跑通最小闭环：一条知识写入 → 审核生效 → 被
  `knowledge.search` 检索到并带上来源/版本/权威级别。已用真实数据验证。
- [x] Claude Code 和 Codex 都能以各自的 `Agent` 身份调用 `knowledge.search`，
  审计日志能区分两者。两边都已在各自的会话里确认能看到 `knowledge.search`/
  `knowledge.propose` 工具（2026-09-18）。**注意**：这只验证了工具"可见、
  能调用"，还没有真实积累的知识条目支撑"审计日志能区分两者"这句话的完整
  场景——库里目前还没有 Codex 真正写入/搜索过的数据。
- [x] mypy strict / ruff / pytest 全绿，作为这个目录自己的准入门禁。

## 6. 下一步

阶段0/1 的最小闭环已经跑通并接入真实会话，`platform/` 骨架、测试、CI、
MCP 接入、`CLAUDE.md` 的使用指引都已就绪。

**2026-09-18 更新**：用户明确表示这套系统的搭建目标之一是"通过搭建本身
成长"，不完全是需求驱动，所以后续往下推进不需要每次都等真实使用数据倒逼。
第一次主动深化：检索从纯 BM25 升级成 BM25 + 本地向量语义检索的混合方案
（`BAAI/bge-small-zh-v1.5`，通过 `fastembed` 加载，ONNX Runtime，不引入
PyTorch），解决"关键词对不上但意思相关"搜不到的问题，详见
`platform/README.md`"检索：BM25 + 向量语义混合"一节。cross-encoder 重排
（原方案 §7 混合检索的第三块）仍然没做，原因不变：语料量还小，用不上。
实测发现 RRF 融合常数在小语料库下会压平分数差距（排序仍然对，但分数看
不出相关程度强弱），已记录在 `platform/README.md`，暂不调整。

同一天经过一轮交叉审查，修了三个真问题（向量模型失败不该阻断
propose/search、向量要带模型身份避免换模型后硬比、迁移错误不能一把梭全
吞），并把 `TASKS.md` 补上了这两轮实际做的事。

第二次主动深化：补上原方案 §7 检索流程里的"时效校验"——`knowledge.
propose` 现在能设 `effective_at`/`expire_at`，`knowledge.search` 会排除
"还没生效"或"已经过期"的知识，哪怕它状态是 active。详见
`platform/README.md`"时效校验"一节。

又一轮交叉审查（同一天）修了三个问题：`SearchResponse` 加了
`retrieval_mode` 字段，如实反映这次搜索有没有真的用上向量检索；
`effective_at`/`expire_at` 时间区间无效（失效时间不晚于生效时间）现在会
被 `propose()` 拒绝，不会写进一条永远搜不到的知识；模型身份只存名字、
不存版本号/哈希这一条认同是真限制，但阶段0/1单人场景不成立，留到团队化
前再补。至此平台测试数 26 个（`TASKS.md` 记的数字要跟着更新，之前写的
19 已经过期）。

用户确认"阶段0/1可以算完成"，检索这条线的主动深化到此为止（cross-encoder
重排和更细的检索优化，语料量不够大，做了也看不出效果，等真有这个规模再
说）。

**阶段2 落地**：交付契约（原方案 §9）。架构上直接复用知识模块验证过的
"起草→人工冻结/审核→之后被引用"模式，新增 `contract/` 模块（模型/存储/
生命周期）、`contract.create`/`contract.update`/`contract.get` 三个
MCP 工具、`POST /contracts/{id}/freeze` 冻结（Human-only，跟
`knowledge.approve` 一样不做成 MCP 工具）。详见 `platform/README.md`
"交付契约"一节。**Harness（阶段3：拿冻结的契约驱动开发、三轮修复、准出
门禁）不在这轮范围内**——这轮只做"契约本身怎么被治理"，不是"拿契约做
什么"，两者是不同性质的工作，不会因为契约模块搭好了就自动往 Harness 推。

写这轮代码时发现一个真 bug：`freeze()` 拒绝时的审计写入和 `raise` 最初
写在同一个数据库连接块里，`get_connection()` 的设计是块内任何异常都会
回滚整个事务，导致刚写的拒绝审计记录被这次回滚吞掉——测试跑起来才发现
（`list_audit_events` 断言为空）。修法是把审计写入放进单独的连接块，
提交完再在块外抛异常，跟 `knowledge/service.py` 里敏感内容拒绝那段保持
同一个模式。

同一天又经过一轮交叉审查，指出阶段2 的"结构校验"其实没做全（AC 只有一
个自由文本字段，没有拆成原方案 §9.2 要求的前置条件/操作/输入/预期结果；
知识引用只查"存不存在"不查"是不是真的生效"；`contract.get` 没有身份和
审计）。这三条认同都是真缺口，不是新加的严格度，修完：`AcceptanceCriterion`
拆成 4 个必填字段（草稿期可留空，冻结时强制非空）；`freeze()` 成功时会
把被引用知识当时的 `version`/`content_hash` 固化成 `knowledge_snapshots`，
引用的知识必须当前"真的生效"（复用 `knowledge_service.is_currently_valid`）；
`contract.get` 现在要求 `caller` 并记审计事件，调试用的 HTTP 读接口也从
`GET` 改成 `POST /contracts/{id}/get`（跟 `knowledge.search` 一样，GET
没法带结构化的 caller）。契约正文也补上了敏感信息筛查（复用
`knowledge/sensitive.py`）。详见 `platform/README.md`"交付契约"一节。
