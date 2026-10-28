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
| 新建 UseCase | （待补，参照 NiA `GetFollowableTopicsUseCase` 的 `operator fun invoke()` 写法；**与 NiA 不同**：Repository 接口放 `domain/.../repository/`，不是 NiA 的 `core.data.repository`，因为 Konsist 断言 domain 不允许出现任何 `.data.` import；UseCase 不用 `@Inject constructor`，改由 data 层 `di/` 下的 `@Provides` 提供实例） | 旧样板已随股票相关代码移除（T-010），可在 git 历史 795060d 之前查看 |
| 简单 Repository（非离线优先） | （待补；接口在 domain、实现在 data，Hilt `@Binds` 绑定参照 `core/logging/LoggingModule.kt` 的写法） | 旧样板已随股票相关代码移除（T-010） |
| 离线优先 Repository | （待补，参照 NiA `core/data` 下 `OfflineFirstXxxRepository` + `changeListSync` 的写法；接口位置仍要按上面那条改放 domain） | |
| 分页列表 | （待补，参照 NiA 的 Paging3 用法） | |
| 表单校验 | （待补；NiA 没有表单校验样板，需按本项目 UDF 规则自拟。可复用 `core/designsystem/.../component/AppTextField.kt`） | 旧样板（`ValidateStockCodeUseCase` + `feature/stocklookup/`）已移除，见 git 提交 795060d |

没有对应样板（项目内和 NiA 都没有）时，按 `CLAUDE.md`「开工前必读」的要求告诉我，
一起定一个新的，不要假装样板存在或凑一个不合适的参照。
