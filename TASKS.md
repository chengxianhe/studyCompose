## 当前任务
- [ ] T-014 照片·日流 + 日期滑块 + 未知日期桶
      范围：`feature:library` 新建；定义 scope 抽象（先实现 `All`）；日期流按设备时区分日，每天一个
      粘性日期头，「未知日期」桶固定在最底；日期滑块按桶下标跳转；Coil 加载缩略图并限制缓存；
      分桶规则放 domain 并单测（设备时区、跨零点、缺失时间）。
      功能验收：进入任一天只查该天数据；分桶边界与跳转/未知桶行为验证通过；自检命令全绿。
      百万条真实图片性能验收由 T-012b 承接，完成本任务不代表规模目标已通过。
      接续：`docs/tasks/t-014.md`（五列网格与完整自检通过；设备验证部分通过，待补场景与人工审查）。
      依赖：T-012、T-013。
      正式运行 `d9a19f8aad144fb5acf1a88bb03e7504` 已由用户启动；继续自动检查与待授权的设备补验。

## 待接续
暂无；T-014 已恢复为当前任务。

## 待人工验收
- [ ] T-023 人工验收入口与自动证据归档
      用户已授权持续完善，目标是高度自动化；保留人工批准边界。
      范围与验收：`docs/tasks/t-023.md`。105 个平台测试通过，真实运行等待人工 AC-4；之后继续 T-014。
      2026-11-05 用户授权继续 T-014；此处保留 T-023 待审状态，不代为交付。

## 待办
本地相册管理（2026-10-28 讨论后确定；部分任务已实现，新任务开工前确认方案）。

### UI 结构（用户定）
底部 4 个 Tab：**照片 | 相册 | 回忆 | 修图**。
- 照片：分段「年 | 月 | 日」。
  - 年：年份列表，点年进入该年的月；月的封面 = 当月拍摄时间最晚的一张。
  - 月：点月进入该月「有照片的日」；日的封面 = 当日拍摄时间最晚的一张。
  - 日：全部照片的日期流 + 日期滑块。
- 相册：全是相册；点进相册后，内部结构与「照片」一致（年 / 月 / 日）。
- 回忆：历史上的今天，日期流 + 日期滑块（滑块按「N 年前」分段）。
- 修图：为接入阿里端侧 AI（MNN）做准备。

### 全局约定
- 目标规模 **100 万张**；数据源是系统 MediaStore（只读系统相册，不自建私有库）。
- 按日分类用**设备时区**；没有拍摄时间的（`DATE_TAKEN` 缺失、回退 `DATE_MODIFIED` 也无效）进
  **「未知日期」桶**。
- 不分页（不引入 Paging 3）；UI 从不持有全量数据：Room 存 `id + 拍摄日期 + 类型 + 相册(bucket)` 的轻量
  元数据；年 / 月 / 日的数量与封面用 SQL 聚合（封面取组内 `taken_at` 最大的一张，`taken_at` 需建索引）；
  进入某一天时只查那一天。
- **照片 / 相册 / 回忆是同一套 UI，只是数据范围（scope）不同**：`All` / `Album(bucketId)` / `OnThisDay`。
  因 feature 之间禁止互相依赖，这三个 Tab 放进同一个 `feature:library` 模块共用时间线组件。
- 模块划分（默认方案，T-013 前确认）：`feature:library`（照片、相册、回忆）、`feature:viewer`（大图）、
  `feature:editor`（修图）。**导航与 4 个 Tab 的多返回栈放 `app`**，feature 只暴露 Route 与回调；
  跨页面只传 `String` id / 查询条件，**绝不传照片列表**（大图页自己按条件从 Room 取相邻照片）。
- 实体不含 Android 类型（Uri 用 `String`/id 表示）；一次性事件走 `UiState` 字段。
- 位置等 EXIF 敏感信息不进日志；列表里不读 EXIF，只在详情页按需读。
- 性能预算（T-011 实测后修订，数字见 `docs/metrics/photo-baseline-2026-10-28.md`，限于华为 CLS-AL30 一台设备）：
  100 万条下冷启动到首屏内容 ≤ 2 s（实测中位数 1.03 s）、内存峰值与总量基本无关（匿名 RSS 约 76 MB）、
  网格滚动无明显掉帧（帧 CPU P99 约 5.5 ms）、同步未完成时可先展示已有部分；年 / 月 / 日摘要不得在首屏路径上同步全量聚合。
- 新增依赖（Room、Coil 等）随引入它的任务一起提交，提交信息列出新增的库并按流程刷新 dependencyGuard 基线。
- 设计系统缺 token（缩略图间距、日期头、网格圆角等）时停下来问，不内联、不借用。

### 已确认的决定（2026-10-28 用户）
1. 钻取：年 → 点月，进入该年的月；月 → 点日，跳转到「日」流中**该年该月该日**的位置。
2. 「相册」第一版只读系统相册（MediaStore bucket）；用户自建相册放后续。
3. 修图第一版：占位 Tab + domain 接口，不接 MNN；主线完成后再做最小版，最后接 MNN。
4. 导航库用 **Navigation 3**；T-013 已采用 `1.0.1`，原因见 patterns 的导航样板。
5. 不做应用内回收站；回忆不为 2 月 29 日做特殊规则（按「月-日」字面匹配，平年不带出 2 月 29 日的照片）。

### 任务
- [ ] T-012b 真实 schema 基线重跑与真机验证补齐（从 T-012 拆出，排在界面之后）
      范围：`:benchmark-target` 依赖 `:data`，用合成 `MediaSource` 跑真实同步引擎，删掉原型实体 / DAO / 数据库 / 灌库器；
      新增 `SyncBenchmark`（全量同步、1000 条增量、删除对账）；查询改读真实 `day_summary`；三档规模在华为 CLS-AL30 上分多次短运行，
      灌库放在 `setupBlock`；产出 `docs/metrics/photo-baseline-real-schema-*.md` 并与原型基线对比；更新性能预算；
      `docs/patterns/README.md`「离线优先 Repository」行补真实样板。
      真实日流性能：接入 T-014 UI 与 Coil，明确可解析图片数据集、冷热缓存、连续滚动/远距跳转/未知桶场景；
      原型 5.5 ms / 76 MB 仅作参考，记录真实结果并确认适用预算后才能宣称百万规模目标达标。
      真机验证补齐：API 34（部分授权）分支、`ContentObserver` 触发的增量同步（拍一张 / 删一张）；API 33 分支只能靠单测。
      验收：100 万条全量同步耗时与内存记入基线；摘要持久化后首屏内容时间不劣于原型基线（否则如实记录并停下商量）；自检命令全绿。
      依赖：T-012、T-014（先有界面，再做性能验证）。
- [ ] T-015 照片·年 / 月钻取
      范围：年列表 → 月（封面 = 当月最晚一张）→ 有照片的日（封面 = 当日最晚一张）；数量与封面来自
      Room 聚合，不在内存里分组；点某一天跳转到「日」流中该年该月该日的位置。
      验收：100 万条下三级切换无明显卡顿；封面不现算；自检命令全绿。
      依赖：T-014。
- [ ] T-016 相册
      范围：系统相册（MediaStore bucket）列表；点进相册复用时间线（scope = `Album`），结构与「照片」一致。
      验收：相册内年 / 月 / 日与「照片」行为一致；新增 / 删除照片后相册计数同步；自检命令全绿。
      依赖：T-015。
- [ ] T-017 回忆（历史上的今天）
      范围：scope = `OnThisDay`；`GetOnThisDayUseCase` 把「今天」作为参数传入（或注入 Clock）以便单测；
      按「N 年前的今天」分段的日期流 + 滑块；2 月 29 日不做特殊规则（按「月-日」字面匹配）。
      验收：闰年 / 平年 / 无数据用例单测通过；自检命令全绿。
      依赖：T-014。
- [ ] T-018 大图查看 + 收藏
      范围：`feature:viewer`；`HorizontalPager` 左右滑动、缩放手势、按需读 EXIF；入参只含「查询条件 +
      当前照片 id」；收藏状态存 Room（含 Migration）。
      验收：大图内存可控（降采样）；收藏随同步不丢；自检命令全绿。
      依赖：T-014。
- [ ] T-019 删除 / 移动
      范围：Android 11+ 经 `MediaStore.createDeleteRequest` 系统确认；确认结果表达成 `UiState` 字段；
      不做应用内回收站。
      验收：删除后 Room 与 MediaStore 一致；用户取消确认不改数据；自检命令全绿。
      依赖：T-014。
- [ ] T-020 修图 Tab（占位版）
      范围：`feature:editor` 新建；domain 定义 `ImageProcessor` 接口；Tab 内放占位页与入口说明；
      不引入 MNN、不加 native 库。只做占位版，最小版与 MNN 接入属于后续。
      验收：模块边界与 Konsist 断言通过；自检命令全绿。
      依赖：T-013。

后续（未排期）：修图最小版（裁剪 / 旋转 / 亮度对比度，另存为新文件，不覆盖原图）、MNN 接入
（推理引擎放 data 层，domain 只留接口；需评估 APK 体积、`dependencyGuard`、机型兼容与 Hexagon 降级路径）、
自建相册 / 标签、重复图检测（感知哈希）、端侧 AI 打标签 / 以图搜图。

## 已完成
- [x] T-025 会话内执行到待审的最小闭环（2026-11-06 用户验收并确认交付）
      正式运行 `541944bad33342ccba0a7a4af70304e6` 状态 delivered；全量检查退出 0，平台 120 测试通过。
      范围、审查包、交付指纹及保留限制见 `docs/tasks/t-025.md`。
- [x] T-022 知识可用性与任务闭环接入（2026-11-05，用户确认审核完毕）
      产出：知识目录/全文、本机人工审核、备份恢复、契约入口与知识沉淀流程。
      验证：平台 88 测试及隔离双端门禁通过；21 条知识已由用户批准，MCP hybrid 检索命中。
      证据：`docs/tasks/t-022.md`。未提交/未推送；T-014 既有 detekt 失败继续在当前任务处理。

更早的条目已归档（原文未改）：
- Android：T-002 ~ T-006 → `docs/tasks/completed-android.md`
- platform/：T-P0 ~ T-P8 → `docs/tasks/completed-platform.md`

新任务完成后先记在这里；本文件接近 250 行时，再把较早的条目搬进上面的归档文件。

- [x] T-021 Codex 主力工作流迁移（2026-11-04，隔离基线验收）
      产出：统一自检/CI 硬门禁、Astra high 独立回归、任务接续、中文检查 lexer 与技能隔离。
      验证：脚本 9 测试、Konsist 26 测试；HEAD + 本次变更的隔离副本双端自检退出 0，platform 70 测试通过。
      主工作区仍有 T-014 既有 detekt 失败，未提交/未推送；远端 main 未启用强制规则。
      详细证据与审查范围：`docs/tasks/t-021.md`。

- [x] T-013 App 骨架：4 Tab 底部导航 + 各 Tab 独立返回栈（2026-10-29）
      产出：`app` 内用 Navigation 3 1.0.1 管理照片、相册、回忆、修图四个独立返回栈；各 Tab 根页返回直接退出；
      照片接现有 `HomeRoute`，其他 Tab 先用占位页；导航样板补入 `docs/patterns/README.md`。
      验证：导航单测 6 个通过；`./gradlew :konsistTest:test detekt lint test spotlessCheck :app:dependencyGuard` 退出码 0。
      华为 ELE-AL00 真机：四个 Tab 可切换，修图切回照片后首页状态可见；四个根页返回均退出应用；
      横屏后仍停留在回忆；后台进程被杀后从桌面入口恢复仍停留在回忆；截图未见系统栏遮挡。
      各 Tab 的二级返回栈目前只有单测覆盖，待后续任务加入二级页面后再做真机验证。
- [x] T-012 权限 + MediaStore → Room 同步（2026-10-28，底座完成；基线重跑拆为 T-012b）
      产出：domain（`PhotoAccess`、`SyncStatus`、`LibrarySyncState`、`MediaLibraryRepository` 与观察 / 刷新两个 UseCase）；
      data（Room schema `media_item` / `day_summary` / `dirty_day` / `sync_state` 并导出 schema，MediaStore 源按单游标读图片 + 视频，
      全量归并对账 / 增量 / 删除对账 / 时区变化重算，日摘要在整轮同步后统一重算，ContentObserver 防抖，权限归一）；
      app 清单声明媒体权限；`feature:home` 的最小权限与同步状态面板。提交 958c38f、747b609。
      验证：domain 2 个、data 17 个（含 Robolectric + 内存 Room）、feature:home 5 个单测通过；自检命令退出码 0。
      真机（华为 CLS-AL30，API 31）：同步出 1408 项，与 MediaStore 命令行统计的 1343 张图片 + 65 个视频一致。
      未完成（见 T-012b）：100 万条基线重跑、API 34 部分授权分支与 ContentObserver 增量的真机验证。
      历史问题：中文检查曾跨字符串误报中文注释；修复与验证跟踪于 T-021，不再把避免中文注释当业务规则。
- [x] T-011 压测基础设施与性能预算（2026-10-28，带已知缺口）
      范围：`:benchmark-target`（合成数据 + 原型 Room schema + 占位网格）、`:benchmark`（Macrobenchmark 五组度量）、
      `studycompose.android.test` 约定插件、`benchmark/README.md`、`docs/metrics/photo-baseline-2026-10-28.md`。
      结果（华为 CLS-AL30，100 万条）：首屏内容中位数 1.03 s、占位网格滚动帧 CPU P50 2.1 ms / P99 5.5 ms、
      匿名 RSS 峰值 76 MB、首次灌入 23.0 s；年汇总 0.55 s、日桶列表 0.33 s，需持久化摘要，不能每次启动同步算。
      已知缺口：冷启动测试曾在不同档位随机失败（修复后一次完整运行三档通过）；内存 / 查询 / 滚动未在修复后重跑；
      只测了一台设备，且是合成数据 / 占位格；原型 schema 不是 T-012 最终 schema，T-012 须重跑。
      验收证据：`./gradlew :konsistTest:test detekt lint test spotlessCheck :app:dependencyGuard` 退出码 0，
      `:app:dependencyGuard` 基线未变；设备上的 Macrobenchmark 不在标准自检命令内，结果见基线文档。
- [x] T-010 移除股票相关代码（2026-10-28）
      范围：产品转向图片类，删除 domain/data 中全部股票（行情、事件雷达、代码校验）代码与测试、
      `feature:stocklookup`、`docs/signal-rule-acceptance-draft.md`；`feature:home` 保留为占位页。
      保留：`AppTextField`、`data` 的网络依赖（build.gradle 未动）、`platform/`、历史任务归档。
      patterns 索引三行（UseCase / 简单 Repository / 表单校验）改回「待补」。
- [x] T-009 补 patterns「表单校验」样板（2026-10-28）
      范围：只做表单校验一行，载体是已有的 `ResolveSecurityIdUseCase`（股票代码输入）；不碰离线优先 / 分页。
      产出：`ValidateStockCodeUseCase`（+单测）、`StockCodeValidationModule`、`AppTextField`、
      新模块 `:feature:stocklookup`（ViewModel/Screen/Preview/strings/单测）、patterns 索引更新。
      未做：`:app` 不 include 该模块、不改 MainActivity（app 无导航，用户决定只接 Preview）。
      局限：`AppTextField` 因 detekt LongParameterList（阈值 6）没有 keyboardOptions 参数，数字键盘未启用。
      验收证据：`./gradlew :konsistTest:test detekt lint test spotlessCheck :app:dependencyGuard` 退出码 0，
      依赖未变。

- [x] T-008 代码质量基线度量（2026-10-21）
      范围：用 SlopCodeBench（arXiv 2603.24755）的指标给仓库量一次基线；只度量，不改 Android 代码，
      不改 CLAUDE.md / Konsist / detekt / lint 配置，不引入依赖。
      产出：`tools/quality-baseline/`（measure.py、detekt-metrics.yml、test_measure.py、README.md）、
      `docs/metrics/baseline-2026-10-21.md`。
      结果：8 个检查点上侵蚀（CC>10 的复杂度质量占比）全为 0，最大 CC 3→10，克隆行占比（近似）6%→2.8%。
      局限：detekt 门禁已把 CC 限制在 12，指标本身没有变大的空间，不能据此证明门禁有效；克隆指标是近似，
      与论文不可比；单人单项目。详见报告。
      验收证据：6 个单元测试通过；`./gradlew :konsistTest:test detekt lint test spotlessCheck
      :app:dependencyGuard` 退出码 0；历史度量用的临时 worktree 已清理。
- [x] T-007 补英文 README（2026-10-21，提交 28f7caa）
      范围：新建 `README.en.md`（与中文版对应，不加中文版没有的说法）；`README.md` 顶部加一句话定位和
      英文版链接。另：`LICENSE` 版权人改为 `chengxianhe`（提交 7ceb529）。不动代码。
