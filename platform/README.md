# govplatform（阶段0/1/2 原型）

对应 `../docs/ai-engineering-governed-delivery-platform.md` 和
`../docs/ai-engineering-governed-delivery-platform-baseline.md`。这是受控
交付平台的原型，目前覆盖两块：**知识治理**（提交知识 → 人工审核通过 →
通过 `knowledge.search` 检索到，带来源/版本/权威级别）和**交付契约**
（起草验收标准 → 人工冻结 → 冻结后不能悄悄改）。

## 范围

- 知识治理（阶段0/1）：`knowledge.search`（只读）、`knowledge.propose`
  （写，落地为 `in_review`）两个 MCP 工具，审核走 HTTP
  `POST /knowledge/{id}/approve`。检索是 BM25 + 向量语义检索的混合方案，
  还做了时效校验，见下面"检索"一节。
- 交付契约（阶段2）：`contract.create`/`contract.update`/`contract.get`
  三个 MCP 工具，冻结走 HTTP `POST /contracts/{id}/freeze`。见下面
  "交付契约"一节。
- `harness.*`、`evidence.query`、cross-encoder 重排、Harness 状态机
  （拿冻结的契约驱动开发、三轮修复、准出门禁）都不在这几轮范围内，属于
  原方案 §13 阶段3-4——这几轮做的是"契约本身怎么被治理"，不是"拿契约
  做什么"。

## 检索：BM25 + 向量语义混合

`knowledge.search` 同时跑两路排序再融合：

- **BM25**（`search/index.py`）：关键词精确匹配，负责类名/接口名/错误码
  这类必须字面命中的场景。
- **向量语义检索**（`embedding.py` + `search/hybrid.py`）：用本地模型
  `BAAI/bge-small-zh-v1.5`（通过 [`fastembed`](https://github.com/qdrant/fastembed)
  加载，ONNX Runtime 跑，不需要装完整的 PyTorch）把知识正文变成向量，
  提交知识时算好存进 SQLite（`knowledge_objects.embedding` 列），搜索时
  现场把查询词也变成向量、算余弦相似度。负责"关键词对不上但意思相关"的
  场景，比如搜"耦合"能找到正文写"依赖"的知识。
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
  ——对应原方案 §9.2 的原话，这几项之前被我图省事塞进一个 `description`
  字段，是漏了结构，不是新加的严格度。草稿期允许留空，`freeze()` 才强制
  非空。
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
`knowledge/`（知识对象 + 生命周期）、`embedding.py`（本地向量模型的加载
与调用，`knowledge/` 和 `search/` 都依赖它，不互相依赖）、`search/`
（`index.py` 是 BM25，`hybrid.py` 是 BM25+向量的 RRF 融合，`service.py`
是对外入口）、`contract/`（交付契约的模型/存储/生命周期，架构上照抄
`knowledge/` 的模式，`freeze()` 时会调 `knowledge_service.get()` 校验
`knowledge_refs`，是唯一一处跨模块依赖）、`audit/`（审计事件）、`db/`
（SQLite）、`mcp_server/`（MCP 工具出口）、`api/`（调试用 HTTP 薄层，
每个路由都只是薄适配层，业务逻辑全在对应的 `*/service.py`）。
