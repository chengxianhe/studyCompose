## 当前任务
（当前无进行中的任务；下一条等用户定义）

## 待办
（暂无）

## 已完成
- [x] T-006 首页信号卡片带实时报价（2026-10-20）
      范围：每张 ResearchSignal 卡片显示现价与今日涨跌幅（带正负号的数字，**不上色**）。
      不改 `:data`（除 StockUseCaseModule 增加一个 @Provides）；不动
      InMemoryResearchSignalRepository 的占位数据；不新增设计系统 token / 组件。
      规格：
      ① `:domain` 新建 `ResolveSecurityIdUseCase`（仅一个 public fun，输入 6 位 stockCode
        字符串，输出 `SecurityId?`）：6 开头→SSE，0/3 开头→SZSE，其余（含北交所 4/8/9、
        非 6 位数字、空串）→null。带单元测试覆盖上述全部分支。
      ② `StockUseCaseModule` 增加对应 @Provides。
      ③ `HomeUiState` 增加 `quotes: Map<String, Quote> = emptyMap()`，key 为 signal.id。
      ④ `HomeViewModel` 注入 GetQuoteUseCase、ResolveSecurityIdUseCase；信号列表到达后并发
        为每个信号取一次报价，单个失败（任何非 CancellationException 异常）只是 Map 里缺这一项，
        不改 hasError；CancellationException 必须重新抛出；`onRefreshClick`/`onRetryClick`
        之后重新取报价；新一轮取报价要取消上一轮未完成的（不得串用过期结果）。
      ⑤ `HomeScreen` 的 SignalCard 在有报价时多显示一行（现价 + 带正负号涨跌幅），无报价
        时与现在完全一致。文案进 strings.xml，无内联视觉数值。
      ⑥ 测试：全部成功、部分失败、全部失败、不可解析代码（北交所）、刷新后报价重取、
        取消不被吞。
      验收：`./gradlew :konsistTest:test detekt lint test spotlessCheck :app:dependencyGuard
      :app:assembleDebug` 全绿（--rerun-tasks）；不得修改 Konsist/detekt/lint 配置；
      不得新增 @Suppress。
      已知局限：占位信号代码为 600001/600002，真机上多半走"无行情"路径；本任务无真机联网验证。
      验收证据（2026-10-20）：--rerun-tasks 全量自检含 assembleDebug 全绿，测试 79 个 0 失败；
      11 个变异体 9 个被杀，2 个存活（均为冗余防御：最终写入前的 version 校验、
      onRetryClick 里多余的 quoteJob.cancel，上游已有取消保证，行为等价）
      后续修复（e1c70c4）：刷新时行情行闪烁已修——重新取报价不再先清空 quotes，新结果到达后
      整体替换（刷新时取失败的股票其旧报价随之消失，不显示过期价）；onRetryClick 仍会清空。
      遗留：①未做 Codex 只读复审；②无真机联网验证，占位代码 600001/600002 多半走无行情路径；
      ③涨跌幅未上色（项目暂无涨跌色 token）

- [x] T-005 软门禁清零：更新 dependencyGuard 依赖基线、统一 spotless 格式，
      并把这两项纳入自检清单（2026-10-19）
      规格：2026-10-19 验收 T-004 时核实——`./gradlew :app:dependencyGuard`
      失败，差异仅为 `hilt-navigation-compose` 带入的 9 项（T-002/T-003
      提交 e34ec0f 引入后未更新基线）；`./gradlew spotlessCheck` 对
      domain/data/feature:home 里一批文件失败（含 T-002/T-003 已提交的旧
      文件，不只是 T-004 新文件）。这两项不在 CLAUDE.md 自检清单里，所以
      之前"自检全绿"并不覆盖它们
      发现（T-004 验收时）：spotless 的 ktlint 没有配置行宽上限，会把
      `fun x(...): T =` 与后面的表达式并成一行；detekt 的 MaxLineLength 是 120。
      已提交的旧代码折行写法满足 detekt、违反 spotless——两个门禁互相矛盾。
      所以 `spotlessApply` 之前必须先对齐：在 spotless 的 ktlint 配置里设
      `max_line_length=120`（只是让 ktlint 与 detekt 一致，不放宽任何检查），
      否则格式化会让 detekt 变红。当前 spotless 违规共 12 个文件：T-004 的 5 个
      （见 T-004「遗留」）+ 已提交旧文件 7 个（ResearchSignalUseCaseModule、
      HomeScreen、HomeViewModel、GetHomeSummaryUseCaseTest、
      GetResearchSignalsUseCaseTest、RefreshResearchSignalsUseCaseTest、
      HomeViewModelTest）
      验收：分两个独立提交——
      ① 依赖基线：确认差异全部是有意引入后，运行
      `./gradlew :app:dependencyGuardBaseline`，提交只含
      `app/dependencies/releaseRuntimeClasspath.txt`，提交信息列出新增的库；
      ② 格式统一：运行 `spotlessApply`，提交只含格式变化，不夹带任何逻辑
      改动（用 `git diff -w` 抽查；格式化后 `./gradlew :konsistTest:test
      detekt lint test` 仍全绿）；
      两个提交之后 `./gradlew dependencyGuard spotlessCheck` 全绿
      后续：把 `dependencyGuard`、`spotlessCheck` 加进 CLAUDE.md 自检清单——
      这是修改项目约定，等用户确认后单独提交，不并入上面两个
      范围：`app/dependencies/`、spotless 报告里列出的源文件
      不做：不改 detekt/Konsist/lint 配置；不借格式化顺手重构；基线只在
      逐项确认差异是有意引入后才更新，不为变绿而盲目刷新
      前置：T-004 先提交，避免格式化与 T-004 未提交文件互相踩；T-004 里
      有意引入的 `desugar_jdk_libs` 是 `coreLibraryDesugaring` 配置，预计不
      影响 `releaseRuntimeClasspath`，该任务开始时实际验证
      完成情况：按计划分提交，另有一处必要的偏差——
      ① `8395e29` 依赖基线：`:app:dependencyGuardBaseline`，差异恰为 9 行新增、0 行删除，
      提交只含 `app/dependencies/releaseRuntimeClasspath.txt`；
      ② `5fa9232` 先对齐行宽（偏差：计划里是两个提交，这里多出这个）：spotless 的 ktlint
      设 `max_line_length=120`，与 detekt 一致，ktlint 变严而非放宽；不先做这步，格式化会让
      detekt 变红；
      ③ `430582c` 格式统一：13 个文件，逐个把改前改后去掉空白/尾逗号/import 顺序后比较，
      13 个全部相同（纯格式），测试数不变；
      ④ CLAUDE.md 自检清单加入 `spotlessCheck`、`:app:dependencyGuard`（单独提交）。
      验证：`./gradlew :konsistTest:test detekt lint test :app:assembleDebug spotlessCheck
      :app:dependencyGuard` 全部通过（domain 10、data 29、Konsist 21、home 5，失败 0），
      这是项目第一次所有门禁同时为绿
      未做/留意：CLAUDE.md「交叉审查（Codex）」一节仍写着"没有直接调用 Codex 的工具"，
      已与实际流程不符，但改它涉及分工约定，留给用户决定；`:app:assembleDebug` 目前不在
      自检清单里，但它能发现 Hilt 依赖图错误（T-004 验收时靠它），建议用户考虑加入
- [x] T-004 A股行情数据 V1（2026-10-19）：在 `:data` 用腾讯财经接口取"证券搜索 / 单股报价 /
      日K线"三项（只做数据层，无 UI）
      规格：`~/Downloads/stock-data-api-development-guide.md` §3、§8.1、§10
      + 本次会话 2026-10-19 对腾讯三个接口的实测样本（文档自称未实测，
      腾讯报价/日K/搜索的字段顺序与单位已用真实响应核对，见下）
      实测结论（写进解析器和测试的依据）：报价 `qt.gtimg.cn` 为 GBK 文本、
      `~` 分隔、`[3]`现价 `[4]`昨收 `[5]`开 `[30]`时间 `[33]`高 `[34]`低；
      日K `newfqkline` 为 JSON，行顺序 日期/开/收/高/低/量(手)/`{}`/换手率/
      成交额(万元)，第 7 个元素是空对象（数组混合类型）；搜索 `smartbox`
      返回 `\uXXXX` 转义字符串；不带浏览器 User-Agent 也可访问
      验收：`./gradlew :konsistTest:test detekt lint test` 全绿；
      `:app:assembleDebug` 编译通过；解析器单元测试用保存的真实响应做
      fixture（报价 fixture 保留 GBK 原始字节），覆盖：正常解析、数组混合
      类型、搜索 unicode 转义、空响应/字段缺失/格式错位 → 明确报
      SchemaChanged 而不是静默错位；UseCase 与 Repository 映射有测试；
      报价带 `source`/`sourceTime`/`fetchedAt`；日K带 `source`/`fetchedAt`，
      数据时间以末根K线日期为准（K线接口本身没有独立时间戳）；量单位固定为"手"、
      金额单位固定为"元"并在命名中体现；日志走 `core:logging`
      范围：`domain/` `data/`，外加 `TASKS.md`、`docs/patterns/README.md`
      （完成后补一行"第三方非 JSON 数据源适配器"真实样板路径）
      不做：UI/首页接线；东方财富/新浪/同花顺（同花顺文档里没有接口信息）；
      分钟线/分时；多源降级、缓存、限流退避；`stale` 判定（需要交易日历）；
      北交所/ETF/指数的单位与复权核验（只验证了沪深个股）；自家后端；
      应用内联网冒烟测试；数据源授权与合规评估——这些是非官方前端接口，
      对外发布前必须换成有授权的数据源（承接 T-003 登记的合规风险）
      完成情况：Codex 实现，Claude 验收（准入门禁 → 自己强制全量重跑 → 对抗
      验证 → 跨源对照 → Codex 只读独立复审，复审 10 条逐条核实，成立的全部
      修复）。证据：`./gradlew :konsistTest:test detekt lint test
      :app:assembleDebug --rerun-tasks` 533/533 任务实际执行并成功；测试
      domain 10、data 29（debug/release 各）、Konsist 21、home 5，失败 0；
      24 个故意植入的 bug 全部被测试抓住；3 只股票×近 10 个交易日与东方财富
      跨源对照 33 项一致（报价成交额为整数元，容差 <1 元）；合并后的 manifest
      含 `android.permission.INTERNET`；dependencyGuard 差异仅为 T-002 遗留
      的 9 行，T-004 未新增任何一行
      用户决定：接受核心库脱糖（minSdk 24 使用 `java.time` 所需），版本放进
      `gradle/libs.versions.toml`（`desugar-jdk-libs`），`app`/`data` 启用
      实现要点：INTERNET 声明在 `data` 库 manifest（由 manifest 合并带入
      app）；K 线回退到 `day` 键时标 `Adjustment.UNKNOWN` 而非 QFQ；搜索只
      保留 `GP-A*`（B 股 `GP-B` 被排除，科创板 `GP-A-KCB` 保留）；
      `SecurityId` 要求 6 位数字；成功与失败都记日志（不含搜索词和响应体）
      已知未验证：应用内真机联网（没有 UI 接线）；ETF/指数/北交所；除权日前后、
      停牌、涨跌停日；上游频率限制；同花顺；数据源授权与合规（对外发布前必须
      换成有授权的数据源）
      遗留：`StockUseCaseModule`、`TencentUrls`、`StockDataException`、
      `GetDailyBarsUseCase`、`StockFixtures` 共 5 个文件为满足 detekt 的 120
      列上限而折行，与 spotless 的 ktlint（无行宽上限）冲突，留给 T-005
- [x] T-003a T-003 的 Codex 交叉审查修复（2026-10-19）
      规格：Codex 只读审查报告（本次会话），逐条对照代码核实后修复
      验收：`./gradlew :konsistTest:test detekt lint test` 全绿（含 3 个
      domain + 5 个 HomeViewModel 测试，完成时快照）；ViewModel 测试
      真正覆盖 loading→数据、loading→error、重试恢复订阅、连点防重入、
      刷新失败；`ResearchSignal` 加稳定 `id` 作列表 key；正收益占比改
      `Double`（方案文档示例 68.1%）；数据流报错后"重试"会重新订阅；
      刷新防重入、不吞 `CancellationException`；错误改 `hasError` +
      本地化文案，不再透传原始异常文字；空信号时仍显示每日汇总；
      `collectAsStateWithLifecycle`（新增 `lifecycle-runtime-compose`
      依赖）
      范围：`domain/` `data/` `feature/home/`、`gradle/libs.versions.toml`、
      `AndroidFeatureConventionPlugin.kt`
      不做：`SignalCard` 卡片容器——`:core:designsystem` 里没有 `AppCard`，
      按设计系统规则停下来等用户决定；ViewModel 上游订阅随页面生命周期
      暂停（`stateIn(WhileSubscribed)`）——内存假数据源下无影响，接真数据源
      时再做；失败路径未接 `Logger`
- [x] T-003 用真实业务替换 Home 测试脚手架：A股事件驱动研究雷达首页
      （假数据版）（2026-09-21）
      规格：`~/Downloads/a_share_event_news_radar_v1.md`（用户提供的产品
      方案）§26"首页"
      验收：删掉 T-002 的 `HomeItem`/`HomeItemRepository` 等测试用占位
      代码，换成 `ResearchSignal`/`DailySummary` 真实领域模型；
      `./gradlew :konsistTest:test detekt lint test` 全绿；
      `:app:assembleDebug` 编译通过；模拟器装包启动后首页展示汇总数字 +
      事件候选卡列表，点刷新不崩溃；新增单元测试通过
      范围：`domain/` `data/` `feature/home/`（`app/`/`build-logic/`/
      `gradle/libs.versions.toml` 里 T-002 加的 Hilt 基础设施原样保留未动）
      不做：接真后端（财联社/东财/巨潮抓取 + FastAPI，方案文档还没做）、
      事件详情页/股票详情页（需要导航，字段更多，留给下一个任务）、真实
      抓取与合规评估（方案文档 §5 数据源 ToS 风险、§20 证券投资咨询合规，
      这两条在对外发布前必须单独过一遍，这次只搭 UI 骨架不涉及）
- [x] T-002 首个真实 Home 列表页：UseCase/Repository 落地 + Hilt 首次真正跑通
      （2026-09-21）
      规格：本次会话对话记录 + `docs/patterns/README.md`"新建 UseCase"/
      "简单 Repository（非离线优先）"两行（参照 Now in Android
      `GetFollowableTopicsUseCase`/`TopicsRepository`，按本项目 Konsist
      规则把 Repository 接口挪进 domain）
      验收：`./gradlew :konsistTest:test detekt lint test` 全绿；
      `:app:assembleDebug` 编译通过；模拟器装包启动后首页正常展示列表，
      点刷新按钮不崩溃、logcat 无异常；domain/feature 新增 6 个单元测试
      通过（Turbine 覆盖 loading→数据/loading→error 两条路径）
      （此数字是 T-002 完成时快照；这批脚手架测试已在 T-003 删除，
      当前测试数见 T-003a）
      范围：`domain/` `data/` `feature/home/` `app/`
      （`MainActivity`/`AndroidManifest`/新增 `StudyComposeApplication`）
      `gradle/libs.versions.toml`、
      `build-logic/convention/.../AndroidFeatureConventionPlugin.kt`
      （新增 `hilt-navigation-compose` 依赖）
      不做：Room/Retrofit 真实网络与离线优先同步、导航、下拉手势刷新、
      删除 `MainActivity` 里原有的 CounterScreen 计数器 demo 代码；点刷新
      后的瞬时 loading 态没能在真机截图上稳定复现（600ms 窗口比 CLI 截图
      往返耗时短），改用单元测试覆盖这条路径
- [x] T-P0 `platform/` 阶段0/1：受控知识库原型（2026-09-18）
      规格：`docs/ai-engineering-governed-delivery-platform.md`（原方案）+
      `docs/ai-engineering-governed-delivery-platform-baseline.md`（阶段0
      决策与验收状态，含逐项勾选）
      验收：知识写入→人工审核→`knowledge.search` 检索到，带来源/版本/
      权威级别；Claude Code 与 Codex 均以各自 Agent 身份验证可调用；
      mypy strict/ruff/pytest 全绿（完成时19个测试，当前总数见最新一条）
      范围：仅 `platform/` 目录 + 根目录 `.mcp.json`/`.github/workflows/
      platform-ci.yml`，不涉及 Android 侧代码
      不做：交付契约（阶段2）、Harness 三轮修复（阶段3）、cross-encoder
      重排、多空间隔离——均为有意延后，理由见 baseline 文档 §6
- [x] T-P1 `platform/` 深化：BM25 + 本地向量语义检索混合（2026-09-18）
      规格：同上 baseline 文档 §6 "2026-09-18 更新"
      验收：语义相关但无字面关键词重合的查询能命中知识（见
      `tests/test_hybrid_search.py`）；向量模型失败时写入/搜索均能退化
      为 BM25-only 不报错（见 `tests/test_embedding_resilience.py`）
      范围：仅 `platform/` 目录
      不做：向量数据库、持久化索引、自动重嵌入
- [x] T-P2 `platform/` 两轮交叉审查修复 + 时效校验（2026-09-18）
      规格：同上 baseline 文档 §6，同一天的两轮交叉审查记录
      验收：向量模型失败时 propose/search 均不报错（含 search 内部查询词
      编码也要容错，第一版只顾了写入路径）；换模型后的旧向量不参与比较；
      SQLite 迁移只吞"列已存在"这一种错误；`effective_at`/`expire_at`
      支持且顺序无效会被拒绝；`SearchResponse.retrieval_mode` 如实反映
      这次搜索有没有用上向量检索；mypy strict/ruff/pytest 全绿（26 个
      测试，此数字同样只是完成时快照）
      范围：仅 `platform/` 目录
      不做：模型版本号/哈希、旧向量自动重嵌入——阶段0/1单人场景不成立
- [x] T-P3 `platform/` 阶段2：交付契约 AC-*/TC-*（2026-09-18）
      规格：`docs/ai-engineering-governed-delivery-platform.md` §9 +
      baseline 文档 §6 "阶段2 落地"
      验收：契约起草→草稿期可改→冻结（Human-only）→冻结后拒绝再改；
      冻结时校验 AC 非空/AC-TC 引用完整/ac_id-tc_id 不重复/knowledge_refs
      存在，任一不满足拒绝冻结并写审计事件；MCP 三个工具
      （create/update/get）+ HTTP 冻结接口都跑通；mypy strict/ruff/
      pytest 全绿（38 个测试，完成时快照）
      范围：仅 `platform/` 目录
      不做：Harness（阶段3，拿冻结契约驱动开发/三轮修复/准出门禁）、
      契约版本替换流程（SUPERSEDED 状态）、内容质量校验——均为有意延后
- [x] T-P4 `platform/` 阶段2 交叉审查修复：AC 结构拆分/知识快照/get 审计
      （2026-09-18）
      规格：同上 baseline 文档 §6，同一天第二轮交叉审查记录
      验收：AcceptanceCriterion 拆成 precondition/action/input/
      expected_result 四个必填字段（冻结时校验非空）；knowledge_refs 必须
      当前生效（active + 在有效期内）才能冻结，冻结时固化
      knowledge_snapshots（version+content_hash）；contract.get 要求
      caller 并记审计；契约正文复用敏感信息筛查；mypy strict/ruff/pytest
      全绿（42 个测试，完成时快照）
      范围：仅 `platform/` 目录
      不做：契约版本替换、内容质量校验——同上一条理由
- [x] T-P5 `platform/` 修两个真漏洞：知识下线机制、契约并发编辑保护
      （2026-09-19）
      规格：同上 baseline 文档 §6，用户自己复盘发现（不是交叉审查）
      验收：knowledge_service.deprecate()（Human-only，要求 reason）把
      active 知识转 deprecated，search() 自动搜不到；contract_service.
      update() 要求 expected_version 做乐观锁，版本对不上拒绝
      （ContractConflictError，HTTP 409），成功后版本号加一；mypy
      strict/ruff/pytest 全绿（48 个测试，完成时快照）
      范围：仅 `platform/` 目录
      不做：知识"取消下线"（撤销的撤销）、freeze() 的并发保护（本轮只
      解决 update() 被识别出来的那个具体缺口）
- [x] T-P6 `platform/` 阶段3：Harness 状态追踪 + 豁免机制（2026-09-20）
      规格：baseline 文档 §7（三道门禁+豁免机制设计，含调研 Google/
      Microsoft/国内大厂/Anthropic 自己公开实践的结论）
      验收：`harness/` 模块记录完整状态机（开发→入门禁→验收→修复
      最多3轮→通过/升级）；豁免独立对象、Human-only、必填理由/风险/
      到期时间、到期 fail closed；涉及生产数据/不可逆操作的 AC 不允许
      豁免，契约冻结时要求写回滚方案；`harness.deliver` 只有 Human 能做；
      用构造场景手工跑通完整流程；mypy strict/ruff/pytest 全绿（59 个
      测试，完成时快照）
      范围：仅 `platform/` 目录
      不做：真的用 `Agent` 工具跑一次 studyCompose 真实功能——这是下一
      个独立任务，需要先选定功能、走需求准入门禁、起草冻结契约
- [x] T-P7 `platform/` 阶段3交叉审查修复：Harness 三个 P0 + 契约两个
      P1（2026-09-20）
      规格：`docs/ai-engineering-governed-delivery-platform-phase3-review-
      2026-09-20.md`（baseline 文档已超 250 行上限，这轮记录单开文件）
      验收：harness.start 改 Human-only 且从 MCP 工具里删掉；
      manual_evidence 类型 AC 只有 Human 调用才能判 passed，Agent 提交
      的一律当未解决；acceptance_results 跨轮次累积不再覆盖；契约乐观锁
      改成 `WHERE ... AND version = ?` 原子写入；豁免要求契约必须已冻结；
      TC 描述补进敏感信息筛查；mypy strict/ruff/pytest 全绿（65 个测试，
      完成时快照）
      范围：仅 `platform/` 目录
      不做：freeze() 自身的并发窗口（概率极低、Human-only，本轮只修
      审查具体指出的缺口）
- [x] T-P8 `platform/` 需求准入门禁调研 + 阶段3二轮交叉审查修复
      （2026-09-20）
      规格：`docs/ai-engineering-governed-delivery-platform-phase3-review-
      2026-09-20.md`"第二轮"一节（调研 Definition of Ready/GitHub
      spec-kit 等业内需求准入模板的结论也记在这轮对话里）
      验收：`open_questions` 非空禁止冻结（抄 spec-kit 的
      "[NEEDS CLARIFICATION]" 机制）；`HarnessStatus` 加
      `WAITING_FOR_HUMAN`，manual_evidence 未解决时不再无意义消耗修复
      轮次；豁免 `expires_at` 必须带时区且晚于当前时间
      （`InvalidWaiverError`）；单轮验收结果拒绝重复/未知 ac_id；
      `contract/service.py`、`harness/service.py` 两个都因超 250 行/
      文件上限拆分成多文件，外部调用方 import 不变；mypy strict/ruff/
      pytest 全绿（70 个测试，完成时快照）
      范围：仅 `platform/` 目录
      不做：真实任务试跑——仍然是下一个独立任务
