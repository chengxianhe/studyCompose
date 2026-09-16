# 项目约定

## 架构
Google 官方架构指南分层（UI / Domain / Data）+ 单向数据流（UDF）。
多模块 Gradle，依赖方向单向不可逆：

    app → feature/* → domain ← data
    feature/* → core/*

模块结构与依赖规则见 `docs/compose-ai-bootstrap-final.md`，机器断言在 `:konsistTest`。

### 硬性规则（违反即 bug，不接受"先这样后面再改"）
- feature 禁止 import data 包下任何内容，实现类由 app 通过 Hilt 注入
- feature 之间禁止互相依赖
- domain 是纯 Kotlin 模块（`kotlin("jvm")`），禁止 android.* / androidx.*
- DTO 不得越过 data 层边界，必须在 data 层映射成 domain 实体
- ViewModel 不得直接调 Retrofit / Room，必须经过 UseCase
- ViewModel 对外只暴露 StateFlow；不用 Channel / SharedFlow 发一次性事件，
  把事件表达成 state（如 UiState.userMessage: String?），UI 消费后回调清除
- 纯 UI 状态（展开/收起、Tab 选中）用 remember 留在 Composable，不进 ViewModel
- 禁止直接用 android.util.Log，统一走 core:logging 的 Logger（core:logging 内部实现豁免）
- 禁止 fallbackToDestructiveMigration，schema 变更必须写 Migration，
  `room { schemaDirectory(...) }` 导出的 schema JSON 要进版本控制

## 新增逻辑时的默认动作
**默认新建 UseCase / 新建文件。往已有类加方法是例外，需要理由。**

在往任何已有类添加方法之前，必须先报告：
- 该类当前行数、public 方法数
- 该类当前职责的一句话概括
- 新逻辑为什么属于这个职责而不是一个新职责

说不清就新建。

## 开工前必读
实现新功能前，先读 `docs/patterns/README.md` 找对应场景，
按索引打开它指向的真实代码，照那个结构写。

`docs/patterns/README.md` 里标"待补"的场景（项目内还没有真实代码可参照时）：
去查 Google 官方的 Now in Android（github.com/android/nowinandroid）对应写法作为外部参照——
它是 Compose + 多模块 + Hilt + offline-first 这套架构的官方样板项目，本项目的 build-logic
约定插件设计就是照它的思路搭的。参照它写完之后，把这份代码补进 `docs/patterns/README.md`
对应行，之后同类场景直接用项目内部这份，不用每次都去查外部项目。

Now in Android 是通用参考，不代表和本项目业务场景100%贴合，明显不适用的地方停下来问，
不要照抄了事。找不到合适参照（项目内和 NiA 都没有）时告诉我，一起定一个新的
（不要假装样板存在）。

## 设计系统（硬约束）
视觉常量唯一来源是 `:core:designsystem`（`com.study.cc.core.designsystem.theme` 下的
Color / Spacing / Type / Sizes / Radius / Elevation），业务代码禁止内联任何视觉数值。

禁止：
- `Color(0xFF...)` → `MaterialTheme.colorScheme` / `AppTheme.extendedColors`
- 内联 dp（0.dp、1.dp 除外）→ `Spacing` / `Sizes` / `Radius` / `Elevation`
- `fontSize = X.sp` → `MaterialTheme.typography`
- 硬编码字符串（含中文）→ `stringResource(R.string.xxx)`
- `import androidx.compose.material.*` → 本项目只用 Material3
- 自己写 loading / 空态 / 错误态 → 用 `core:ui` 的 `LoadingState` / `EmptyState` / `ErrorState`
- 自己搓按钮、卡片、输入框 → 按需在 `:core:designsystem` 建 `AppButton` / `AppCard` / `AppTextField`
  这类组件后再复用，不要每个页面各写一套

以上除设计系统内联规则外，还都有 Konsist 断言（scope 限定 `feature/` 和 `data/`，
排除 `*Preview.kt` 和测试目录，`:core:designsystem` 本身天然豁免）。

### 找不到合适 token 时
不要内联一个值，也不要"数值接近就借用"
（`Spacing.lg` 和 `Sizes.iconMd` 都是 16dp 但语义不同，别混用）。
停下来告诉我缺什么、用在哪，由我决定新增 token 还是改用现有的。

### 新增 token 的流程
1. 在 `:core:designsystem` 对应文件里新增，命名走语义不走数值（`Spacing.xxl`，不是 `Spacing.dp32`）
2. 如果是颜色，同时补暗色模式的值
3. 提交时单独一个 commit，便于 review

## 日志规范
- 统一用 `core:logging` 的 `Logger` 接口（`LogcatLogger` 已通过 Hilt 绑定为默认实现）
- 禁止记录：手机号、身份证、token、密码、完整地址、精确位置
- 记录对象用脱敏摘要，禁止 `toString` 整个 data class
- 关键路径（网络、状态机跳转、支付、登录）必须记录且不采样
- tag 用类名

## 国际化
所有用户可见文案进 `strings.xml`。命名 `<模块>_<场景>_<语义>`
（例：`order_detail_title`、`common_retry`）。
带参数用占位符不要拼接；复数用 `plurals`；布局用 `start`/`end` 不用 `left`/`right`。

## 自检要求（每次改完必须执行）
    ./gradlew :konsistTest:test detekt lint test

全部通过才算完成。

**架构测试失败时必须修实现，禁止修改 Konsist 断言、detekt 配置或 lint 抑制来变绿。
如果你认为某条规则本身有问题，停下来告诉我，由我决定是否调整。**

## 工作方式
- 编码前先进 plan mode，列出改动文件和职责，等我确认
- 一次只做 `TASKS.md` 中「当前任务」那一条
- 不顺手重构无关代码，不顺手加没要求的功能
- 不确定的设计决策停下来问，不要自己拍板

## 交叉审查（配了 codex MCP 后启用，目前尚未配置，先占位）
任务完成且本地全绿后，调用 codex 审查，传入：本次 git diff、
本文件的架构与设计系统章节、`TASKS.md` 中该任务的验收标准。
要求它只输出分级问题清单，不改文件。
收到后逐条评估：认同的修复，不认同的说明理由交我判断。
