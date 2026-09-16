# 参照写法索引

实现前先在这里找场景，按索引打开指向的真实代码，照那个结构写。
样板指向真实代码路径，不贴代码片段——这样样板不会过期。

| 场景 | 参照文件 | 要点 |
|---|---|---|
| 新建 feature 模块 | `feature/home/` | 模块结构、`studycompose.android.feature` 约定插件已经带好 domain/core/Hilt 依赖 |
| 页面三态 | `core/ui/src/main/kotlin/com/study/cc/core/ui/state/` | `LoadingState`/`EmptyState`/`ErrorState` 用法 |
| 新建 UseCase | （待补，还没有真实实现） | |
| 离线优先 Repository | （待补，还没有真实实现） | |
| 分页列表 | （待补） | |
| 表单校验 | （待补） | |

没有对应样板时，按 `CLAUDE.md`「开工前必读」的要求告诉我，一起定一个新的，
不要假装样板存在或凑一个不合适的参照。
