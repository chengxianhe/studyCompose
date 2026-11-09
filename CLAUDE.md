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

## 知识库（govplatform，MCP 工具）
本项目配了一个独立的知识治理原型（`platform/`，见
`docs/ai-engineering-governed-delivery-platform-baseline.md`），通过 MCP 暴露
`knowledge.search` / `knowledge.propose` / `knowledge.list` / `knowledge.get`。
使用与人工审核入口见 `docs/knowledge/README.md`；目录/全文可包含待审条目，不等于生效规则。

- 遇到不确定的架构/业务规则、或者这条规则 `CLAUDE.md` 里没写清楚时，先用
  `knowledge.search` 查一下有没有人已经记录过，别自己猜
- 发现了值得记住的新规则/决策，用 `knowledge.propose` 提交一条。提交后状态是
  "待审核"，我确认过才会生效、才能被搜到——提交完不代表马上能用，别当场假设它已生效
- 每项任务收尾都评估知识沉淀：先搜索去重，提交有来源和验证证据的提案，在任务记录写 ID/状态；
  没有新经验则明确记“无新增可复用知识”及理由，不为凑数入库。
- 相关工具不在当前会话的工具列表里（没连上 MCP、或者没被信任）时，跳过工具步骤，
  按现有规则（`docs/patterns/`、`docs/LESSONS.md`、问我）处理，不要因为工具不可用卡住
- 正常新任务关联 `contract.create/get/update` 与 `harness.*`，流程见 `docs/workflow.md`。
  只有用户能批准知识、冻结契约、启动运行、确认交付；Agent 不得自报 Human 或代点审核按钮。

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
统一入口（从仓库根目录执行）：

    bash scripts/verify.sh android

包含 `:konsistTest:test detekt lint test spotlessCheck :app:dependencyGuard assembleDebug`。
`platform/` 改动执行 `bash scripts/verify.sh platform`；跨两端、验证脚本或公共工作流改动执行 `all`。
`workflow` 只验证脚本行为，不能代替 Android / platform 验收。文档改动至少执行 `git diff --check HEAD`。
入口会保存 HEAD、工作区指纹、完整日志与退出码到 `.verification/`，不缓存“已通过”。
执行期间源码变化会让结果失效；CI 使用同一入口。真机/性能验证仍按任务单独执行。

全部通过才算完成。

- `spotlessCheck` 失败：运行 `./gradlew spotlessApply`，格式化改动单独提交，不夹带逻辑
  改动。ktlint 的行宽已与 detekt 对齐为 120，两者不会互相矛盾。
- `:app:dependencyGuard` 失败：说明最终打进 APK 的依赖变了。逐项确认差异都是有意引入后，
  运行 `./gradlew :app:dependencyGuardBaseline`，基线文件随引入依赖的那次提交一起提交，
  提交信息列出新增的库；不要为了变绿而盲目刷新基线。

**架构测试失败时必须修实现，禁止修改 Konsist 断言、detekt 配置或 lint 抑制来变绿。
如果你认为某条规则本身有问题，停下来告诉我，由我决定是否调整。**

## 工作方式
- 会话开始先读本文件、`TASKS.md`、当前任务链接的接续记录、`docs/LESSONS.md` 和 `docs/patterns/README.md`
- 编码前列出改动文件、职责与验收方式，等我确认；已明确批准的方案继续执行，不反复询问。
  有 Plan mode 时使用；没有时在对话中给出只读方案，不能假称已切换模式
- 一次只做 `TASKS.md` 中「当前任务」那一条
- 不顺手重构无关代码，不顺手加没要求的功能
- 不确定的设计决策停下来问，不要自己拍板
- 接手先记录 HEAD、工作区改动与已有未跟踪文件；不把先前改动当成本轮产出，不擅自覆盖或提交
- 当前任务在 `docs/tasks/` 保留一份接续记录：已确认范围、进度、检查证据、未验证项和下一步
- 每个 Kotlin 文件最多 250 行由 Konsist 检查；Claude 编辑 hook 仅是便利提醒，不是 Codex 的自动门禁
- 技能必须匹配本项目；其他项目的业务事件、模块名、固定生命周期策略不能作为本项目硬规则
- 真机操作先确认本轮设备授权；每次输入前核对前台应用，用户切走后停止输入
- 默认不提交、不推送；用户授权提交后按约定拆分，推送需有明确授权

## 协作偏好（2026-11-06 用户确认记录）
- 用户只需描述目标、困扰或期望效果；Agent 负责主动发现可行方案、遗漏场景、约束与风险，
  不要求用户先列出完整方案或掌握提示词技巧。
  提问前先查相关代码、已确认决定和有效知识；优先澄清最影响结果的未决取舍，不重复问已有答案。
- 讨论阶段主动探索并筛选：简单问题直接给建议；存在关键取舍时，通常精选两三个有实质区别的
  方案，说明用户体验、成本与后续影响，并明确推荐。数量不是硬上限，不为凑数制造选项。
  目标和路径已明确时不强制头脑风暴；方案可在对话中简述，不为小改动另建规格或计划文档。
  仍遵守编码前确认；已批准的方案直接继续。
- 用户决定重要取舍；方案确认后收敛执行，区分本次必须解决的问题与后续改进。
  额外发现记录为建议或待办，不自动扩大实现范围；改变范围的决策按现有确认规则处理。
- 节省 token 优先减少重复读取、无效重试和冗长输出；日志保留完整证据、按需读取。
  不削减发现问题与提出好方案的思考，不跳过规定的测试、门禁或人工审查。
  完成开工必读后，先用索引或搜索定位，再读当前场景的代码、文档和技能；同会话未变内容不反复全文加载，
  出现修改或证据过期时重新核对。稳定、重复的操作优先复用已有脚本，不为单次需求另搭框架。
- 模型调配按任务难度评估：日常工作可从中档推理起步，复杂难点再提高；这是调配建议，
  不代表已修改模型配置，也不默认启动多 Agent 或模型审查。成本以任务交付、耗时和返工一起衡量。
- 独立任务宜使用独立会话，通过简短接续记录保留决定、证据和未完成项，避免携带无关历史。
  用户不必反复重述已经确认的偏好；纯讨论不自动转成实现任务。
  接续只记录影响后续工作的决定及理由、证据链接、未验证项和下一步；引用原始资料，不抄日志与聊天。
  社区方法按具体问题少量吸收，不整套套用，不额外增加固定审查轮次或多 Agent 流程。

## 人工审查与自动验证
2026-11-04 用户要求审查交给人工。默认由用户审查知识入库与代码交付，暂停自动模型审查；
若用户后续明确限定范围或要求模型辅助，再按该次授权执行。
实现者负责计划、编码、运行自检、整理差异与证据，以及逐条核实并修复人工意见。
自动测试通过只能记为“自动检查通过，待人工审查”，不得替用户宣布已验收或批准知识。

审查材料包含任务范围、基线与既有 WIP、本次文件清单、实际 diff、检查日志/退出码、
源码指纹、已知风险与未验证项。用 `python3 scripts/workspace_fingerprint.py` 固定审查快照；
人工审查后若代码再变，复验受影响路径并重新交付差异，不沿用旧批准。
知识批准、契约冻结、运行启动与最终交付仍由用户操作。细则见 `docs/workflow.md`。
