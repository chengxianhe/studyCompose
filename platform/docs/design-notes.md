# 设计细节参考

## 来源与关系图谱（T-028）

SQLite `graph_sources` 保存不可变、调用方登记的来源版本元数据，
`graph_relations` 的端点与证据使用外键约束，部分唯一索引防止重复待审/有效关系。
知识快照绑定 ID、version、content_hash；不为图谱复制知识正文或新增付费模型调用。
来源未知摘要时使用显式请求键幂等，不推测同名资料是同一版本。

图谱代码拆分登记、提案、审核和查询职责。提案/审核使用 `BEGIN IMMEDIATE`；
审核在事务内重新比较整个审核快照，只有 Human 能变更状态。有效知识的时效失效即使
没有修改数据库也会改变快照的 valid 标记，旧页面因此不能直接批准。
来源与关系字段过敏感信息筛查，审计只记录生成的记录 ID，不保存请求原文。

查询使用有界逐节点读取、visited 集合和节点/边预算；impact 沿派生/依赖反向找受影响者，
撤销历史须曾经获批才参与诊断；supersedes 是独立候选，不传递依赖。
explain 中不可用的边仅返回风险标记，不沿其继续形成有效证据路径。
每个访问节点只保留首条见证路径；到深度预算时保守报告截断，不宣称已枚举所有路径。
关系撤销不改变知识本身状态，原 `knowledge.search` 不自动采用图谱边重新排序。

借鉴来源为 [W3C PROV-O](https://www.w3.org/TR/prov-o/) 的派生/责任建模思想；
概念层 [SKOS](https://www.w3.org/TR/skos-reference/) 仍是后续参考。
本实现没有复制这些标准的代码或图，也不是完整的 PROV/SKOS 实现。
完整来源映射和后续能力见 `../../docs/knowledge/capability-roadmap.md`。

以下是每块能力的实现细节、取舍理由和已知的技术缺口，写代码/改代码之前
先看这里，避免重复踩过的坑。整体概览（能做什么/做不到什么/怎么跑起来）
见 `../README.md`；本文件之前是那份 README 的一部分，因为超过项目
250 行/文件上限被拆出来单独存放。

## 检索：受控子块 + 本机 ES 混合召回

`ingest/chunker.py` 按 Markdown 标题层级分节，长节以固定窗口和 80 字重叠
切成子块。每块保存 `parent_id`、知识版本、标题路径、来源、BM25 字段与向量。
`ingest/es_index.py` 以当前 SQLite 中已批准且有效的知识和模型版本生成索引指纹，
构建完整新索引后原子切换别名；索引丢失可重建，不作为知识真源。独立的
`ingest watch` 检查新知识审批、废弃和到期，在线查询只读已就绪的索引；
未就绪时降级，返回前仍以 SQLite 状态再次过滤。

ES 中 BM25 和 kNN 各召回最多 40 子块，在应用层用 RRF 融合为最多 30 块，
本地 Cross-Encoder 对前 20 块重排，返回最多 10 块。ES 9.5.6 的免费 Basic
许可不允许内置 RRF，真实集成报 `current license is non-compliant`；应用层同式
融合避免付费许可。重排原始分数经 sigmoid 映射，当前以 0.5 判断证据是否
足够；此阈值只通过少量真实查询和对照样本验证，扩大语料时需人工复核。
`relevance_grade=retry` 由 Codex 改写查询并递增 `attempt`，最多两轮；仍无
依据时为 `insufficient`。没有后台 LLM 服务或额外云端 API 调用。

未设置 `GOVPLAT_ES_URL` 或 ES 故障时保留原有 SQLite 路径：

`knowledge.search` 在降级路径中同样跑两路排序再融合：

- **BM25**（`search/index.py`）：关键词精确匹配，负责类名/接口名/错误码
  这类必须字面命中的场景。
- **向量语义检索**（`embedding.py` + `search/hybrid.py`）：用本地模型
  `BAAI/bge-small-zh-v1.5`（通过 [`fastembed`](https://github.com/qdrant/fastembed)
  加载，ONNX Runtime 跑，不需要装完整的 PyTorch）把知识正文变成向量，
  提交知识时算好存进 SQLite（`knowledge_objects.embedding` 列），搜索时
  现场把查询词也变成向量、算余弦相似度。
- 两路排序用 **Reciprocal Rank Fusion** 合并（`search/hybrid.py`），只看
  各自的名次、不看原始分数直接相加（BM25 分数和余弦相似度不是一个量纲）。

**一个如实的免责声明**：实测过这个模型在短文本上的余弦相似度，"完全不
相关"的两句话有时反而比"确实相关"的两句话分数更高——所以向量这条路径
**只做相对排序，不做绝对阈值过滤**。意味着如果关键词一个都没命中，你
可能还是会搜到一条分数很低、勉强算相关的结果，而不是搜到空结果——这是
故意的取舍（宁可多给一条弱相关结果让你自己判断，也不因为一个不可靠的
数字阈值悄悄藏起可能有用的结果），调用方应该看 `score` 字段自己判断，
不要假设返回的每一条都真的相关。

模型资产由 `model_cache.py` 固定到 Qdrant 的 ONNX 修订和必需文件 SHA-256，
`prepare` 从 Hugging Face 下载并校验到 `platform/.data/models/`；在线检索的
首次加载也能补下载缺失资产。预热后 `check` 可以断网验证，MCP 使用同一路径，
不再依赖 FastEmbed 默认的系统临时目录。仅 SQLite 降级路径仍是
"现取全部 active 知识现场比对"；ES 路径使用持久化双路检索索引。

**向量模型挂了不影响核心功能**：`knowledge.propose`（写入时算向量）和
`knowledge.search`（查询时把关键词也变成向量）两条路径的向量计算都包了
try/except，模型下载失败、加载出错、运行时崩溃，都会静默退化成只用 BM25，
不会让"提交知识"或者"搜索"这两个最基本的功能连带挂掉。知识对象连同向量
一起存了 `embedding_model` 字段——只有跟当前配置的模型名字（`embedding.
MODEL_NAME`）一致的向量才会参与比较，换模型之后旧向量不会被拿来跟新模型
算出来的查询向量硬比（维度、语义空间都可能对不上）。目前换模型之后旧向量
只是被跳过，没有自动重新计算的机制，这是已知的功能缺口，等真的换模型的
时候再处理。

`SearchResponse` 带一个 `retrieval_mode` 字段（`"hybrid"` 或
`"bm25_only"`），如实反映**这一次**搜索向量路径是不是真的参与了排序——
模型挂了、或者候选知识里没有一条能比的向量（都用旧模型算的、或者当时算
失败了），都会是 `"bm25_only"`，调用方能看出这次结果缺没缺语义检索这条
证据，不用去猜。

**目前已知但还不算问题的限制**：`embedding_model` 只存了模型名字
（`"BAAI/bge-small-zh-v1.5"`），没有存具体的模型版本号/文件哈希/向量维度
——理论上如果 Hugging Face 上同名模型的产物变了，旧向量可能被误认成还是
"当前模型"算出来的。阶段0/1 单人使用、模型没换过，这个风险目前不成立，
等真要接入团队/多人协作、模型有变动风险的时候再补。

**另一个如实记录、暂不处理的已知特性**：`search/hybrid.py` 里 RRF 融合用
的常数（`_RRF_K = 60`）是信息检索领域给大语料库（几千上万篇文档）场景定
的经验值，故意压平排名差距、避免对单一排序过度敏感。库里知识条数还很少
（个位数到几十条）的时候，这个常数会把"真正相关"和"完全不相关"的融合
分数压得几乎认不出区别（实测差距在小数点后三位），**但排序本身仍然是对
的**——排序是唯一被测试断言覆盖、承诺过的行为，"分数能直观反映相关程度
强弱"这件事目前不成立，别指望靠 `score` 的绝对数值判断"够不够相关"，只
能拿它比"谁排在谁前面"。等语料量真的大起来、这个常数造成的实际问题浮现
了再调，现在不提前调（调多少合适也没有标准答案，得等真数据）。

## 时效校验

`knowledge.propose` 支持传 `effective_at`（生效时间）/`expire_at`（失效
时间），都是可选的。`knowledge.search` 会把状态是 `active` 但"还没到
生效时间"或者"已经过了失效时间"的知识排除在结果之外——`status=active`
只代表"审核通过了"，不代表"现在就该被当真"。不传这两个字段就跟以前一样，
永久有效。传的时间不带时区信息也不会报错，会被当成 UTC 处理
（`knowledge/service.py::_ensure_utc`）。`expire_at` 不晚于 `effective_at`
会被拒绝（`InvalidTimeRangeError`，HTTP 层对应 422）——不然会写进一条
"生效时间在后、失效时间在前"的知识，状态永远是 active 但永远搜不到，
自己都发现不了。

## 交付契约

对应原方案 §9。生命周期只有两个状态：`draft`（起草中，能反复改）→
`frozen`（冻结，`contract_service.update()` 会直接拒绝改动，报
`ContractStateError`）。没有第三个状态——这一轮不做"冻结后创建新版本
替换旧版本"的流程，`ContractStatus` 枚举也没留 `SUPERSEDED` 这种没有
代码路径产生的死值。

冻结（`freeze()`）只有 `Human` 能做（跟 `knowledge.approve` 一样的身份
限制，不是 MCP 工具，走 HTTP `POST /contracts/{id}/freeze`），而且会做
结构校验，不通过就拒绝冻结（`ContractValidationError`，HTTP 层对应
422）：

- 至少要有一条验收标准（`acceptance_criteria` 不能为空）
- 每条验收标准的 `precondition`（前置条件）、`action`（操作）、
  `input`（输入）、`expected_result`（二值化预期结果）都不能是空字符串
  ——对应原方案 §9.2 的原话。草稿期允许留空，`freeze()` 才强制非空。
- `ac_id`、`tc_id` 各自不能重复
- 每条验收标准至少关联一条测试用例，且引用的 `tc_id` 必须真的存在
- `knowledge_refs` 引用的 `knowledge_id` 必须存在，且必须是当前"真的生效"
  （状态 active、且在 `effective_at`/`expire_at` 有效期内，复用
  `knowledge_service.is_currently_valid()`，跟 `knowledge.search` 用的
  是同一个判断）——不能引用一条还在待审核、或者已经过期/还没生效的知识
  当依据。
- 涉及生产数据/不可逆操作的验收标准（`touches_production_or_
  irreversible=True`），`risks` 字段必须写清楚回滚方案，不能为空。
- `open_questions` 必须清空——带着没想清楚的模糊点不能往下走，调研业内
  需求准入模板（GitHub spec-kit 的 "[NEEDS CLARIFICATION]" 机制）之后
  加的规则，改动小、价值明确，不是从一开始就有的。

**故意不做的**：不检查验收标准写得"够不够具体"——那种判断需要理解文字
语义，用规则去猜容易带来"以为拦住了真问题、其实只是判断逻辑不准"这类
新风险，这个交给人审，不是这一轮的范围。冻结失败会记一条
`contract.freeze.rejected` 审计事件（带失败原因分类，不带契约全文）。

`create()`/`update()` 也会对 title/goal/scope/out_of_scope/每条 AC 的
四个必填字段/测试用例描述/risks/open_questions 跑一遍敏感信息筛查（复用
`knowledge/sensitive.py`），命中就拒绝，跟 `knowledge.propose` 同一套
逻辑——不能靠"这是契约不是知识"绕过这层检查。

**知识快照**：`knowledge_refs` 是草稿期"打算引用哪些知识"的列表，会变；
`knowledge_snapshots` 是 `freeze()` 成功那一刻，系统自动读取每条被引用
知识当时的 `version`/`content_hash` 生成的快照，冻结之后不会再变，即使
被引用的知识后来又改了、归档了，快照记的还是冻结当时的样子。已知缺口：
知识对象本身还没有"替代关系"机制，所以没法在快照生成后持续监测"这条
知识是不是已经被别的取代了"，等那边补了这边才有意义跟进。

`contract.get` 是唯一超出原方案 §11 工具表范围的新增——AI 起草完契约
需要能读回自己写的东西才能继续迭代（`update()` 只支持整份覆盖式更新，
不看一眼当前内容没法改），原表格没列这个工具，这里补充说明理由。跟
`knowledge.search` 一样，`contract.get` 也要求 `caller`、也会记一条
`contract.get` 审计事件——读操作同样要可追溯，不能只有写操作有身份边界。
调试用的 HTTP 读接口因此也从 `GET /contracts/{id}` 改成
`POST /contracts/{id}/get`（带 `caller`），原因和 `knowledge.search` 用
POST 而不是 GET 一样：GET 没有请求体，没法带结构化的 `caller`。

`contract_service.update()` 的乐观锁（`expected_version`）真正生效的
地方在 `contract_store.update()` 内部的 `WHERE contract_id = ? AND
version = ?`——那条 SQL 语句本身就是"检查版本+写入"合一的原子操作。
上层 `contract_service.update()` 里还有一次基于读到的旧数据做的 Python
级别版本检查，那次只是给非并发场景一个更快、更清楚的报错，不是真正的
保护，真正的保护在 store 层那条 SQL（两个调用几乎同时基于同一个旧版本
写入时，后写的那个会在 store 层原子性地失败，不会静默覆盖）。

## Harness 的两个校验细节

- **manual_evidence 类型的验收标准**：设计上就是"自动跑不出结论，需要
  人亲自看"。`record_acceptance()` 里，这类 AC 只有当调用方是 Human 时
  `passed=True` 才算数，Agent 提交的一律当没解决处理。未解决的 AC 如果
  **全部**是这个类型（没有真正需要重新开发的失败），运行会停在
  `HarnessStatus.WAITING_FOR_HUMAN`，不消耗修复轮次——跟真的需要改代码
  的失败（走 `REPAIRING`）是两条不同的路径，人推进的时候不用重新过一遍
  入门禁，直接再调用一次 `record_acceptance()` 就行。
- **单轮验收结果的完整性**：`record_acceptance()` 提交的 `results` 里，
  `ac_id` 不能重复（同一条 AC 同一批里既报失败又报通过是自相矛盾的
  证据）、必须全部是契约里存在的 AC（引用未知的 `ac_id` 会被拒绝，不会
  被静默记进历史）。`acceptance_results` 本身跨轮次累积，不覆盖——每条
  记录都带 `round_number` 标记是第几轮产生的，能回溯任意一轮具体提交过
  什么证据，不止有 `repair_rounds[].failure_summary` 那句粗略归因。
- **豁免的 `expires_at`**：必须带时区信息、必须晚于创建时刻，否则拒绝
  创建（`InvalidWaiverError`）——不带时区的时间会在后续跟 UTC 时间比较
  时直接报错，已经过去的时间会造出一个一创建就永远无效的豁免对象。

## `contract/`、`harness/` 的模块拆分

`contract/service.py` 和 `harness/service.py` 原本各自是一个装了全部
逻辑的大文件，陆续加东西后都超过了项目 250 行/文件的上限，拆成了：

- `contract/`：`_shared.py`（公共小工具+跨模块异常）、`update_service.py`
  （`update()`）、`freeze_service.py`（`freeze()`+结构校验）、
  `waiver_service.py`（豁免）、`service.py`（薄的重新导出入口，含
  `create()`/`get()`）。
- `harness/`：`_shared.py`、`acceptance_service.py`（`record_acceptance()`
  ——这个文件里最复杂、增长最快的一块）、`service.py`（薄的重新导出
  入口，含 `start()`/`record_entry_gate()`/`deliver()`/`get()`）。

两边的公开调用方式都没变——外部代码继续
`from govplatform.contract import service as contract_service` /
`from govplatform.harness import service as harness_service`，然后
`contract_service.create/update/freeze/...`，不需要知道内部拆成了几个
文件。

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
