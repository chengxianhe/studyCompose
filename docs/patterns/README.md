# 参照写法索引

实现前先在这里找场景，按索引打开指向的真实代码，照那个结构写。
样板指向真实代码路径，不贴代码片段——这样样板不会过期。

"待补"的场景：项目内还没有真实代码，先去查 Google 官方的
[Now in Android](https://github.com/android/nowinandroid)（Compose + 多模块 + Hilt +
offline-first 的官方样板项目，本项目 build-logic 的约定插件设计就是照它搭的）对应写法作外部
参照，写完后把代码路径补进下表，转成项目内部样板。NiA 是通用参考不代表照抄，明显不适用时停
下来问。

| 场景 | 参照文件 | 要点 |
|---|---|---|
| 平台任务接续与证据门禁 | `platform/src/govplatform/delivery/context.py`、`submission.py`、`report.py`；底层 `harness/evidence_guard.py`；测试 `platform/tests/test_execution_loop.py` | T-025 会话内 prepare/verify/submit/status；准入不可覆盖、各入口统一校验、人工批准保留；正式部署与人工审查状态见任务记录 |
| 新建 feature 模块 | `feature/home/` | 模块结构、`studycompose.android.feature` 约定插件已经带好 domain/core/Hilt 依赖 |
| 页面三态 | `core/ui/src/main/kotlin/com/study/cc/core/ui/state/` | `LoadingState`/`EmptyState`/`ErrorState` 用法 |
| 底部多 Tab 导航（每个 Tab 独立返回栈） | `app/src/main/java/com/study/cc/navigation/`（`NavigationState` / `Navigator` / `AppNavHost`） | 参照官方 nav3-recipes 的 multiple-backstacks；**与官方示例不同**：`toDecoratedEntries` 只返回当前 Tab 的条目，所以任何 Tab 根页面按返回键都直接退出应用（官方示例是先回到起始 Tab）。导航与路由放 `app`，feature 只暴露 `XxxRoute`。用 Navigation 3 的 **1.0.1**，不是 1.2.0：1.1.x/1.2.0 要求 compileSdk 37 / AGP 9.1+（1.1.x 还会把整个应用的 Compose 抬到 1.10+） |
| 新建 UseCase | `domain/src/main/kotlin/com/study/cc/domain/usecase/ObserveLibrarySyncStateUseCase.kt`、`RefreshMediaLibraryUseCase.kt`；注入见 `data/src/main/kotlin/com/study/cc/data/di/MediaLibraryUseCaseModule.kt` | `operator fun invoke()`；Repository 接口在 domain；UseCase 无 Android/Hilt 依赖，data 的 `@Provides` 负责组装 |
| 简单 Repository（非离线优先） | （待补；接口在 domain、实现在 data，Hilt `@Binds` 绑定参照 `core/logging/LoggingModule.kt` 的写法） | 旧样板已随股票相关代码移除（T-010） |
| 离线优先 Repository | `domain/src/main/kotlin/com/study/cc/domain/repository/MediaLibraryRepository.kt`、`data/src/main/kotlin/com/study/cc/data/repository/MediaLibraryRepositoryImpl.kt`、`data/src/main/kotlin/com/study/cc/data/sync/` | T-012 的 MediaStore → Room 单向同步样板（非联网双向同步）；功能测试与 API 31 真机已有记录，百万真实 schema、部分授权与增量真机验证待 T-012b，不能当已验收的性能样板 |
| 按日照片网格（固定五列） | `feature/library/src/main/kotlin/com/study/cc/feature/library/` 中的 `PhotoDayGrid.kt`、`PhotoDayViewport.kt`、`PhotoDayLoads.kt`、`PhotoDayViewModel.kt`；查询见 `data/src/main/kotlin/com/study/cc/data/store/PhotoTimelineDao.kt` | 小型日期摘要驱动粘性头/滑块，按可见日查询；离开视口取消、失败可重试。T-014 自动检查通过、待人工审查；RAW 缩略图与完整权限旅程未验收，不作为百万图片性能样板 |
| 分页列表 | 当前相册方案不引入 Paging 3，按日查询；不为补样板另加分页功能 | 如未来任务需要分页，另行确认范围和参考实现 |
| 表单校验 | （待补；NiA 没有表单校验样板，需按本项目 UDF 规则自拟。可复用 `core/designsystem/.../component/AppTextField.kt`） | 旧样板（`ValidateStockCodeUseCase` + `feature/stocklookup/`）已移除，见 git 提交 795060d |

没有对应样板（项目内和 NiA 都没有）时，按 `CLAUDE.md`「开工前必读」的要求告诉我，
一起定一个新的，不要假装样板存在或凑一个不合适的参照。
