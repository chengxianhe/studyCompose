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
| 新建 feature 模块 | `feature/home/` | 模块结构、`studycompose.android.feature` 约定插件已经带好 domain/core/Hilt 依赖 |
| 页面三态 | `core/ui/src/main/kotlin/com/study/cc/core/ui/state/` | `LoadingState`/`EmptyState`/`ErrorState` 用法 |
| 新建 UseCase | `domain/src/main/kotlin/com/study/cc/domain/usecase/GetResearchSignalsUseCase.kt` | 参照 NiA `GetFollowableTopicsUseCase` 的 `operator fun invoke()` 写法；**跟 NiA 不同**：Repository 接口必须放在 `domain/.../repository/`（不是 NiA 的 `core.data.repository`），因为本项目 Konsist 断言 domain 不允许出现任何 `.data.` import；UseCase 不用 `@Inject constructor`（domain 不接 DI 框架依赖），改由 `data/.../di/ResearchSignalUseCaseModule.kt` 用 `@Provides` 提供实例 |
| 简单 Repository（非离线优先） | `domain/src/main/kotlin/com/study/cc/domain/repository/ResearchSignalRepository.kt` + `data/src/main/kotlin/com/study/cc/data/repository/InMemoryResearchSignalRepository.kt` | 接口在 domain、实现在 data，Hilt `@Binds` 绑定参照 `core/logging/LoggingModule.kt` 的写法；这个例子是内存假数据源（"A股事件驱动研究雷达"后端还没做出来之前的占位），不是真离线优先同步，下面那行仍然待补 |
| 离线优先 Repository | （待补，参照 NiA `core/data` 下 `OfflineFirstXxxRepository` + `changeListSync` 的写法；接口位置仍要按上面那条改放 domain） | |
| 分页列表 | （待补，参照 NiA 的 Paging3 用法） | |
| 表单校验 | `domain/.../usecase/ValidateStockCodeUseCase.kt` + `feature/stocklookup/`（`StockLookupViewModel` / `StockLookupScreen`）+ `core/designsystem/.../component/AppTextField.kt` | **NiA 没有表单校验样板，这份是按本项目 UDF 规则自拟，不是照搬**：规则放 domain UseCase，返回 sealed 结果（Valid/Empty/InvalidFormat/UnsupportedMarket），ViewModel 只把结果映射成 `UiState.error` 枚举，文案在 Screen 里 `stringResource` 解析；输入中不报"空"错，点提交才报；输入变化清掉上次的 `resolved`。UseCase 由 `data/.../di/StockCodeValidationModule.kt` 提供。尚未接进 app 导航（app 目前无导航，只有 Preview） |

没有对应样板（项目内和 NiA 都没有）时，按 `CLAUDE.md`「开工前必读」的要求告诉我，
一起定一个新的，不要假装样板存在或凑一个不合适的参照。
