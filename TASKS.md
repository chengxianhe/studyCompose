## 当前任务
（当前无进行中的任务；下一条等用户定义）

## 待办
本地相册管理（草案，2026-10-28 与用户讨论后定，尚未开工；开工前每条都要先进 plan mode 确认范围）。

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
  100 万条下冷启动到首屏内容 ≤ 2 s（实测中位数 0.87 s，但有未解释的离群值）、内存峰值与总量基本无关（匿名 RSS 约 76 MB）、
  网格滚动无明显掉帧（帧 CPU P99 约 5.5 ms）、同步未完成时可先展示已有部分；年 / 月 / 日摘要不得在首屏路径上同步全量聚合。
- 新增依赖（Room、Coil 等）随引入它的任务一起提交，提交信息列出新增的库并按流程刷新 dependencyGuard 基线。
- 设计系统缺 token（缩略图间距、日期头、网格圆角等）时停下来问，不内联、不借用。

### 已确认的决定（2026-10-28 用户）
1. 钻取：年 → 点月，进入该年的月；月 → 点日，跳转到「日」流中**该年该月该日**的位置。
2. 「相册」第一版只读系统相册（MediaStore bucket）；用户自建相册放后续。
3. 修图第一版：占位 Tab + domain 接口，不接 MNN；主线完成后再做最小版，最后接 MNN。
4. 导航库用 **Navigation 3**（目录里是 `1.0.0-alpha03`，alpha 风险在 T-013 开工前评估并记录）。
5. 不做应用内回收站；回忆不为 2 月 29 日做特殊规则（按「月-日」字面匹配，平年不带出 2 月 29 日的照片）。

### 任务
- [ ] T-012 权限 + MediaStore → Room 同步
      范围：`READ_MEDIA_IMAGES` 及 Android 14 部分照片访问（`READ_MEDIA_VISUAL_USER_SELECTED`）处理；
      首次全量同步 + 基于修改时间/`generation` 的增量同步；`ContentObserver` 监听并防抖；
      Room 初始 schema（含 bucket、`taken_at` 索引，schema JSON 导出入版本控制）；
      Repository 接口在 domain、实现在 data。同步过程不阻塞 UI，未完成时可先出已有部分。
      验收：100 万条全量同步耗时与内存记入基线；批量增删下增量同步正确；部分授权时界面提示数据不完整；
      自检命令全绿。
      依赖：T-011。patterns「离线优先 Repository」行在本任务补真实样板；完成后用真实 schema 重跑 T-011 基线，
      并查清首屏内容时间的离群值；摘要（年 / 月 / 日数量与封面）持久化并增量维护。
- [ ] T-013 App 骨架：4 Tab 底部导航 + 各 Tab 独立返回栈
      范围：`app` 模块内的底部导航与路由；4 个 Tab 先挂占位页；feature 只暴露 Route 与回调。
      使用 Navigation 3（alpha，见已确认第 4 条）。
      验收：Tab 切换保留各自返回栈；跨 feature 无直接依赖；自检命令全绿。
      依赖：无（可与 T-012 并行）。
- [ ] T-014 照片·日流 + 日期滑块 + 未知日期桶
      范围：`feature:library` 新建；定义 scope 抽象（先实现 `All`）；日期流按设备时区分日，每天一个
      粘性日期头，「未知日期」桶固定在最底；日期滑块按桶下标跳转；Coil 加载缩略图并限制缓存；
      分桶规则放 domain 并单测（设备时区、跨零点、缺失时间）。
      验收：进入任一天只查该天数据；100 万条下滚动达预算；分桶边界单测通过；自检命令全绿。
      依赖：T-012、T-013。
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
更早的条目已归档（原文未改）：
- Android：T-002 ~ T-006 → `docs/tasks/completed-android.md`
- platform/：T-P0 ~ T-P8 → `docs/tasks/completed-platform.md`

新任务完成后先记在这里；本文件接近 250 行时，再把较早的条目搬进上面的归档文件。

- [x] T-011 压测基础设施与性能预算（2026-10-28，带已知缺口）
      范围：`:benchmark-target`（合成数据 + 原型 Room schema + 占位网格）、`:benchmark`（Macrobenchmark 五组度量）、
      `studycompose.android.test` 约定插件、`benchmark/README.md`、`docs/metrics/photo-baseline-2026-10-28.md`。
      结果（华为 CLS-AL30，100 万条）：首屏内容中位数 0.87 s、占位网格滚动帧 CPU P50 2.1 ms / P99 5.5 ms、
      匿名 RSS 峰值 76 MB、首次灌入 23.0 s；年汇总 0.55 s、日桶列表 0.33 s，需持久化摘要，不能每次启动同步算。
      已知缺口：首屏内容时间有未解释的离群值（最大 24.9 s）；冷启动测试在不同档位随机失败过；
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
