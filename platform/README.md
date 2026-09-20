# govplatform（受控知识与交付契约原型）

对应 `../docs/ai-engineering-governed-delivery-platform.md`（完整方案）和
`../docs/ai-engineering-governed-delivery-platform-baseline.md`（阶段决策
记录与验收状态）。这是"AI 工程受控交付平台"里已经落地的部分——知识治理
（阶段0/1）+ 交付契约（阶段2）+ Harness 状态追踪（阶段3）。跟
studyCompose 的 Android app 完全隔离，通过 MCP 接入 Claude Code / Codex。

## 能做什么

### 1. 知识治理——提交、审核、检索

- **提交**（`knowledge.propose`）：AI 或你自己提交一条知识（规则、决策、
  踩坑记录……），落地状态是"待审核"，还搜不到。入库前会拦截疑似敏感信息
  （手机号/身份证号/token/密码类赋值）。
- **审核**（HTTP `POST /knowledge/{id}/approve`）：**只有你能做**，AI
  没有这个权限。通过后状态变"生效"，才能被搜到。
- **下线**（HTTP `POST /knowledge/{id}/deprecate`）：**只有你能做**，
  要求填 `reason`。批错了、过时了，把一条"生效中"的知识转成"已废弃"，
  转完 `search()` 自动搜不到它（跟"待审核"一个道理，只查 `active` 状态）。
  没有"取消下线"——下线错了就重新提交一条新的，不做撤销的撤销。
- **检索**（`knowledge.search`）：BM25 关键词匹配 + 本地向量语义检索
  混合，搜"耦合"能找到正文写"依赖"的知识（关键词对不上但意思相关）。
  结果带来源、版本、权威级别，还能看出这次搜索有没有真的用上语义那条路
  （`retrieval_mode`）。
- **时效校验**：知识可以设生效时间/失效时间，过期或者还没生效的知识
  即使状态是"生效"也不会被搜到。

### 2. 交付契约——把"什么算做完"写成可验证的东西

- **起草**（`contract.create`/`contract.update`）：验收标准
  （AC-*）必须拆成前置条件、操作、输入、预期结果、验证方式这几个具体
  字段，不能是一句"体验良好"；每条验收标准至少关联一条测试用例（TC-*）。
  `update()` 要求传 `expected_version`（乐观锁）——跟数据库里当前版本
  对不上就拒绝更新，防止两个 Agent（或者你和 Agent）并发改同一份草稿时
  后写的悄悄覆盖先写的；每次改动成功，版本号加一。
- **冻结**（HTTP `POST /contracts/{id}/freeze`）：**只有你能做**。冻结前
  会校验验收标准的结构是否完整、引用的知识是否存在且当前有效，任何一条
  不满足就拒绝冻结并说明原因。冻结后不能再改。
- **知识快照**：契约可以引用知识库里的条目作为依据，冻结那一刻系统会把
  被引用知识当时的版本和内容指纹固化下来，以后知识再怎么变，这份快照
  不变。

### 3. Harness——自动跑"开发→验收→修复"，人只在两头参与

对应原方案 §10，设计决策见 baseline 文档 §7。**`govplatform` 只是账本，
不是引擎**——它负责记录状态，真正驱动开发/验收子任务的是外部的驱动方
（Claude Code 会话），详见下面"Harness 架构限制"。

- **开始一次运行**（`harness.start`）：冻结的契约才能开始，不需要额外的
  人工"开始"确认——冻结本身就是授权信号。
- **入门禁**（`harness.record_entry_gate`）：构建/静态检查/测试有没有过。
  没过打回开发，不进入验收，不消耗修复轮次。
- **独立验收**（`harness.record_acceptance`）：逐条核对契约里的 AC，
  全部通过（或者有未过期的豁免覆盖）才算过。没通过的，只要还没到 3 轮
  修复上限就自动进入下一轮修复；到了上限还没过，直接**升级**（终态，
  不会开出第 4 轮，继续只能针对同一份契约重新开始一次新的运行）。
- **豁免**（HTTP `POST /contracts/{id}/waivers`，**只有你能做**）：契约
  某条 AC 通不过、但你判断可以接受风险时用——必填理由、风险、到期时间，
  不允许永久豁免，到期自动失效（fail closed，不自动续期）。涉及生产数据
  /不可逆操作的 AC（`touches_production_or_irreversible=True`）**不允许
  豁免**，必须真通过；契约里只要有一条 AC 标了这个，冻结时就要求 `risks`
  字段写清楚回滚方案。这套设计调研过 SOC2/DevSecOps 领域的共识和 Google/
  Microsoft/国内大厂/Anthropic 自己的公开实践，不是拍脑袋定的，细节见
  baseline 文档 §7.3。
- **交付**（HTTP `POST /harness-runs/{id}/deliver`，**只有你能做**）：
  运行状态必须是"全部通过"才能标记交付。Harness 自己能自动跑到"全部
  通过"，但不能自己点"交付"——这是"最终交付你来审"这条原则的落地点。

**Harness 架构限制，如实说清楚**：`govplatform` 的身份模型只区分"是谁"
（Human/Agent(kind)），**没法从系统层面强制"验收必须独立于开发"**——
`harness.record_acceptance` 这个调用，理论上开发用的同一个 Agent 身份
也能调、自己给自己判定通过。这个独立性完全靠驱动方（Claude Code 会话）
编排时真的开两个隔离的子任务（一个跑开发、一个从零开始只看契约+代码
diff+测试结果去验收，不看开发过程）来保证，`govplatform` 拦不住有人
（或者某次实现）作弊自证。

### 4. 身份与审计——谁做了什么，全程留痕

- 每一次操作都要声明"我是谁"——人（你）还是 AI（区分 Claude Code /
  Codex，各自带会话标识），不允许混用身份。
- 知识提交、审核、检索、契约起草、冻结……每个动作都记一条审计事件，包括
  被拒绝的操作（敏感信息被拦、结构校验没过）也记，只带失败原因分类，不
  带正文。

## 做不到什么（如实列出，不是等你踩坑才发现）

- **审计数据只写不读。** 每个动作都记了审计，但没有任何工具能查询这张
  表——想知道"这条知识是谁批的"只能直接打开 SQLite 文件手写 SQL。
- **还没有在真实开发中被使用过。** 所有验证目前都是构造出来的场景（demo
  脚本、单元测试），不是真实发生的问题被这套系统挡住或者帮上忙。
- **身份是自报的，不是密码学验证的。** 只适合本机受信任进程，不能防冒充，
  见下文"已知的信任边界"。
- **单机 SQLite，没有备份。** 数据库文件只存在这台电脑上，不在版本控制
  里，换电脑或者硬盘坏了知识和契约都没了。
- **语义检索的分数在小语料库下压得很扁**，只能看排序前后，不能看数值
  判断"够不够相关"；换向量模型后旧数据也不会自动重新计算。
- **"验收独立于开发"这条原则，系统层面没法强制**——只能靠驱动方老老实实
  编排出两个隔离的子任务，`govplatform` 拦不住有人在实现里偷懒自证。
  详见上面"Harness"一节"架构限制"。
- **Harness 目前还没跑过真实任务**——状态机本身（开发→入门禁→验收→
  修复→交付/升级、豁免机制）已经用构造场景验证过，但还没有真的用
  `Agent` 工具开隔离子任务去跑一次 studyCompose 的真实功能。这是下一步，
  不在这轮范围内。

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

# MCP server（stdio），Claude Code / Codex 通过根目录 .mcp.json 接入
uv run python -m govplatform.mcp_server.server
```

## 目录结构

见 `src/govplatform/`：

- `identity/` —— Human/Agent 身份模型，`resolve_principal()` 做白名单
  校验。
- `knowledge/` —— 知识对象、生命周期（propose/approve/get）、敏感信息
  筛查（`sensitive.py`）。
- `embedding.py` —— 本地向量模型的加载与调用，`knowledge/` 和 `search/`
  都依赖它，两者互相不依赖。
- `search/` —— `index.py` 是 BM25，`hybrid.py` 是 BM25+向量的 RRF 融合，
  `service.py` 是对外入口。
- `contract/` —— 交付契约的模型/存储/生命周期 + 豁免（`Waiver`），架构
  上照抄 `knowledge/` 的模式，`freeze()` 时会调 `knowledge_service.get()`
  校验 `knowledge_refs`，是唯一一处跨模块依赖。
- `harness/` —— Harness 运行状态追踪（模型/存储/生命周期），只记录状态、
  不驱动真正的开发/验收，`record_acceptance()` 时会调
  `contract_service.get_without_audit()`/`is_ac_waived()`，是它对
  `contract/` 的唯一依赖。
- `audit/` —— 审计事件的写入（目前没有对应的查询工具，见上文限制）。
- `db/` —— SQLite schema 和连接管理。
- `mcp_server/` —— MCP 工具出口（`knowledge.*`、`contract.*`、
  `harness.*`）。
- `api/` —— 调试用 HTTP 薄层，每个路由都只是薄适配层，业务逻辑全在
  对应的 `*/service.py`。

## 详细设计参考

以下是每块能力的实现细节、取舍理由和已知的技术缺口，写代码/改代码之前
先看这里，避免重复踩过的坑。

### 检索：BM25 + 向量语义混合

`knowledge.search` 同时跑两路排序再融合：

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

模型文件首次使用时会从 Hugging Face 自动下载（几十到一百多 MB，需要联网
一次），之后离线可用，缓存在 `~/.cache/huggingface`（或 `fastembed` 自己
的默认缓存目录）。向量检索目前也是"现取全部 active 知识现场比对"，不是
持久化索引，跟 BM25 的策略保持一致——语料量真的大到线性扫描明显变慢，
再考虑引入向量数据库。

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

### 时效校验

`knowledge.propose` 支持传 `effective_at`（生效时间）/`expire_at`（失效
时间），都是可选的。`knowledge.search` 会把状态是 `active` 但"还没到
生效时间"或者"已经过了失效时间"的知识排除在结果之外——`status=active`
只代表"审核通过了"，不代表"现在就该被当真"。不传这两个字段就跟以前一样，
永久有效。传的时间不带时区信息也不会报错，会被当成 UTC 处理
（`knowledge/service.py::_ensure_utc`）。`expire_at` 不晚于 `effective_at`
会被拒绝（`InvalidTimeRangeError`，HTTP 层对应 422）——不然会写进一条
"生效时间在后、失效时间在前"的知识，状态永远是 active 但永远搜不到，
自己都发现不了。

### 交付契约

对应原方案 §9。生命周期只有两个状态：`draft`（起草中，能反复改）→
`frozen`（冻结，`contract/service.py::update()` 会直接拒绝改动，报
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

**故意不做的**：不检查验收标准写得"够不够具体"——那种判断需要理解文字
语义，用规则去猜容易带来"以为拦住了真问题、其实只是判断逻辑不准"这类
新风险，这个交给人审，不是这一轮的范围。冻结失败会记一条
`contract.freeze.rejected` 审计事件（带失败原因分类，不带契约全文）。

`create()`/`update()` 也会对 title/goal/scope/out_of_scope/每条 AC 的
四个必填字段/risks/open_questions 跑一遍敏感信息筛查（复用
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

### 已知的信任边界

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
