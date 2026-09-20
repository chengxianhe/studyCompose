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

用户自己复盘时又指出两个更根本的缺口：知识一旦生效没有下线机制、契约
草稿并发编辑没有冲突保护——这两条不是交叉审查发现的，是直接看代码、
看数据模型看出来的（`DEPRECATED`/`ARCHIVED` 两个状态从来没有代码路径
能到达；`Contract.version` 字段从来没被真正用过）。修完：新增
`knowledge_service.deprecate()`（Human-only，要求填 `reason`，把知识从
active 转成 deprecated，`search()` 不用改就自动搜不到，因为本来就只查
active）；`contract_service.update()` 现在要求 `expected_version`，用
`Contract.version` 字段做乐观锁，版本对不上就拒绝并提示重新读最新内容，
不会静默覆盖。详见 `platform/README.md`"能做什么"一节。

**阶段3（Harness）的门禁设计已经定下来，见第 7 节。** 实现顺序：先进
plan mode 设计 `harness/` 模块，再挑一个 studyCompose 真实的小功能起草
第一份契约、冻结、让 Harness 真正跑一次——这是这套系统第一次被用在
真实任务上，不是又一次自我验证的 demo。

## 7. 阶段3：Harness 门禁设计（2026-09-20，设计决策，实现前先定下来）

对应原方案 §10（Harness）。这一节只定"门禁怎么判、豁免怎么走"，具体的
状态机代码结构留给 plan mode 那一步去设计，这里先把决策钉死，不要边写
代码边改设计。

### 7.1 运行原则

用户明确决策：Harness 跑"开发 → 验收 → 修复"这个循环时**全自动**，不需要
每一步都问人。人只在两个节点参与：①需求/契约阶段（起草、补充、冻结）
②最终交付结果审阅。中间过程只有遇到系统自己判断不了的情况才停下来问，
不是随时可以打断——是专门设计好"什么情况该停"，而不是遇事就问。

已知会触发暂停、升级给人的场景（不是穷举）：
- 契约里某条 AC 的 `verification_type` 是 `manual_evidence`（本来就需要
  人看的证据，Harness 没有替代人眼的能力）
- 三轮修复仍然失败（原方案 §10.4 的硬性上限，到点必须停，不能接着改）
- 遇到需求/契约没写清楚、Harness 自己判断不了该怎么做的情况——跟原方案
  §9.2"无法确定的业务规则必须列为待澄清项，不能由 AI 自行假设"是同一条
  原则，从"起草阶段"延伸到"执行阶段"

### 7.2 三道门禁

```
[需求文本] --①需求准入门禁--> [契约草稿] --人冻结--> [冻结契约]
    --Harness开始自动跑--> [开发] --②入门禁--> [独立验收]
    --全部AC通过(或有效豁免覆盖)+③准出门禁--> [交付，人审]
    --部分失败--> [修复，最多3轮，回到②]
    --3轮仍失败 或 遇到需要人的情况--> [暂停，升级给人]
```

**① 需求准入门禁**（需求文本 → 开始起草契约之前）

能自动判断的：
- 敏感信息筛查——复用 `knowledge/sensitive.py`，命中拒绝，不进入分析

需要判断力的（由起草 Agent 判断，但要按下面这几条走，判断过程本身要
留痕，不是随便拍脑袋）：
- 范围合法性——是不是真的属于这个仓库该做的事
- 明确性下限——够不够具体到能看出改哪块，不够就打回去问人，不脑补
- 架构硬规则预检查——需求字面上有没有已经在要求违反 `CLAUDE.md` 硬规则
- 规模检查——是不是该拆成多份契约

身份门禁（最重要的一条）：**这道准入只有 Human 能触发。AI 不能自己给
自己提需求、自己决定要做什么、自己启动一轮 Harness 循环。** 自动跑的是
"开发→验收→修复"这个中间循环，要不要开始一次循环、做什么，永远是人
点的火。

**② 入门禁**（开发完成 → 进入独立验收之前，对应原方案"构建成功、依赖/
架构约束、静态检查、必需测试"）

- studyCompose 任务：`./gradlew :konsistTest:test detekt lint test` 全绿
- `platform/` 任务：`mypy --strict && ruff check && pytest` 全绿
- 没过直接打回开发，不进入验收阶段，不消耗验收/修复机会

**③ 准出门禁**（独立验收通过 → 真正交付之前）

- 契约里的 AC **必须全部通过，或者有一个未过期的豁免覆盖**（见 7.3）——
  没有"严重度分级、部分通过也算"这种概念，保持判定简单不含糊
- 每条通过都要有可复现证据（测试输出、构建日志……），不采信"验收 Agent
  自己说过了"
- ②的入门禁必须仍然是绿的（不能"AC 都过了但代码质量检查是红的"）
- 走到第几轮修复才过的要如实记录，不能假装一次就过
- 这一路的审计链完整，缺了不能算"可交付"

### 7.3 豁免机制

调研了 Google SRE（错误预算模式，服务级、持续运行场景，跟咱们"一次性
离散契约"不匹配，不适用）、Microsoft Azure DevOps release gates（有门禁
/审批编排，但没有正式的"豁免+到期"审计对象）、国内大厂"变更三板斧"
（可灰度/可监控/可回滚，用降低风险代替审批放行，思路互补）、以及
Anthropic 自己公开的工程实践（[How Anthropic secures its AI-native
SDLC](https://claude.com/blog/how-anthropic-secures-its-ai-native-software-development-lifecycle)、
[Effective harnesses for long-running agents](https://www.anthropic.com/engineering/harness-design-long-running-apps)）
——结论：没找到比下面这版更成熟的通用方案，SOC2/DevSecOps 领域那套
"独立对象+负责人+理由+范围+到期时间，到期 fail closed 不自动续期"的
共识可以直接采用，只需要吸收两条限制。

设计：
- 豁免是**独立的结构化对象**，精确关联"哪个契约的哪条 AC"，不能笼统
  豁免整份契约
- **只有 Human 能创建豁免**——跟审核/冻结/下线同一条身份限制
- 必填字段：理由、承担的风险、到期时间（**不允许永久豁免**）
- 到期自动失效，那条 AC 变回"未通过"，准出门禁重新拦住它，**不自动
  续期**
- 豁免创建本身要记审计事件

两条额外限制（调研得来，不是原创）：
1. **涉及生产数据/不可逆操作的 AC，不允许豁免**——必须真通过，没有例外
   路径（吸收自 Anthropic 自己"生产部署这类关键动作永远人工终审，没有
   AI/系统自己申请豁免"这条实践）
2. **涉及不可逆操作的契约，`risks` 字段必须写清楚回滚方案**——不是新增
   机制，是给契约结构加一条硬性要求（吸收自"变更三板斧：可灰度/可监控
   /可回滚"）

这两条限制会在 plan mode 设计 `contract`/`harness` 模块时落成具体的校验
规则，这里先把决策定下来。

### 7.4 实现状态（2026-09-20）

上面的设计已经落地：新增 `harness/` 模块（`HarnessRun` 状态追踪，
`start`/`record_entry_gate`/`record_acceptance`/`deliver`/`get`）、
`contract/` 加了 `Waiver` 模型和 `request_waiver()`/`is_ac_waived()`，
`AcceptanceCriterion` 加了 `touches_production_or_irreversible` 字段。
59 个测试（新增 `test_harness_lifecycle.py`、
`test_harness_repair_and_escalation.py`、`test_waivers.py`）覆盖了完整
状态机、三轮修复到升级、豁免覆盖/过期/生产数据不可豁免、冻结时回滚方案
校验。mypy strict/ruff/pytest 全绿。用构造场景（不是真实任务）手工跑通
了一遍全流程：起草→冻结→开发→入门禁失败重试→验收部分失败进修复→
人工豁免→再验收通过→AI 尝试交付被拒绝→人工确认交付。

写状态机的时候有一处返工：一开始按"第三次验收失败就升级"设计测试，
跑起来发现跟"最多三轮修复"的本意对不上——原方案状态机是"验收失败
（第1次）触发进入修复循环，循环本身最多绕三圈，第 4 次验收还失败才真正
升级"，不是"失败三次就停"。服务代码本来就是按这个理解写的，是测试的
期望值算错了，改的是测试不是实现。

**明确没做的（不在这轮范围内，是下一步）**：没有真的用 `Agent` 工具开
隔离子任务（开发+独立验收各一个）去跑一次 studyCompose 的真实功能——
这轮只验证了状态机本身对不对，下一步需要先选一个真实的小功能、走完
①需求准入门禁→起草→冻结这一整套流程，再真正驱动一次自动循环。
