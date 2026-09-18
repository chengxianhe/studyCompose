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
MCP 接入、`CLAUDE.md` 的使用指引都已就绪。下一步不是自动继续往阶段2
（交付契约）推进——那需要重新走一遍决策确认，不是这份骨架的自然延伸。
在那之前，更现实的下一步是：让知识库在真实开发中被真正用起来（见
`docs/LESSONS.md` 里"重复2次提示写入知识库"那条规则），先积累真实数据，
再看阶段2 是否真的需要。
