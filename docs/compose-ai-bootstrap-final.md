# Compose 新工程 · AI 协作完整搭建包

> 最终整合版。前面几份文件的内容都收在这里，按落地顺序组织。
> 用法：按第 0 节的顺序做，中间的大段内容是贴给 Claude Code 或直接建文件用的。

---

## 0. 总览

### 四层结构

```
规格层   specs/*.md              契约，你拍板
任务层   TASKS.md                拆分，你来做
知识层   docs/patterns/ LESSONS  参照写法与踩过的坑
约束层   CLAUDE.md + token       AI 执行时的边界
验证层   Konsist/detekt/hooks    机器仲裁，分三级门禁
```

前两层是流程，后三层是工程。AI 只在约束层和验证层里活动。

### 落地顺序（照做，别跳）

| 步骤 | 内容 | 耗时 |
|---|---|---|
| 1 | 装 Android CLI + Skills | 30 分钟 |
| 2 | 贴引导 prompt，分三批搭骨架 | 2-3 小时 |
| 3 | 建 designsystem token 和基础组件 | 半天 |
| 4 | 上 Konsist 全套规则 | 1 小时 |
| 5 | **故意写违规代码，验证每条规则都会红** | 30 分钟 |
| 6 | 配 hooks、建文档骨架 | 1 小时 |
| 7 | 配 CI 三级门禁 | 1 小时 |
| 8 | 提交基线 commit，开始做第一个功能 | — |

第 5 步是全场最重要的一步，**没验证过的护栏等于没有护栏**。

---

## 1. 装 Android CLI 与 Skills

Google 2026-04 发布、05 月 I/O 上 1.0 稳定，官方支持 Claude Code 和 Codex。
SKILL.md 形式，覆盖 Navigation 3 迁移、edge-to-edge、adaptive UI、CameraX、Compose Styles。
官方数据：token 用量降低 70% 以上，任务速度提升 3 倍。

```bash
brew install android-cli          # 或 apt-get / winget，见官方文档
android skills install <skill>    # 按需安装
android skills list               # 查看已装
android skills update             # 定期更新
```

文档：d.android.com/tools/agents

**它和 Konsist 的分工**：Skills 管"怎么写对"（喂最佳实践），Konsist 管"写错了拦住"（断言）。互补，都要。

---

## 2. 引导 Prompt（贴进 Claude Code）

在空目录 `git init` 后启动 `claude`，信任目录，然后贴入下面内容。

````
这是一个空目录，从零搭建 Android 项目骨架。严格按要求执行，
不要自行增加需求外的功能，不要生成示例业务代码。

开始前先问我包名。

## 技术栈
Kotlin + Jetpack Compose + Material3
Gradle Kotlin DSL + Version Catalog + build-logic 约定插件
Hilt / Coroutines+Flow / Navigation 3
Retrofit + OkHttp + kotlinx.serialization
Room（含 room-gradle-plugin）+ Proto DataStore
Coil / WorkManager / kotlinx-datetime
测试：JUnit + Truth + Turbine + Robolectric + coroutines-test
质量：Spotless+ktlint / detekt / Konsist / Dependency Guard

## 模块结构（严格按此，不增不减）

:app                    application。只做 DI 装配、导航图、Application 类
:domain                 【kotlin("jvm") 纯 Kotlin 模块，不是 android library】
                        实体、Repository 接口、UseCase。禁止任何 Android 依赖
:data                   android library。Repository 实现、Retrofit service、
                        Room dao、DTO 与映射、同步逻辑
:core:common            Result 包装、扩展函数、DispatcherProvider
:core:logging           日志接口层（Logger interface + 实现先用 android.util.Log 转发）
:core:designsystem      Theme / Color / Type / Spacing / Sizes / Radius / 基础组件
:core:ui                跨 feature 复用的 UI 组件、UiState 基类、三态组件
:feature:home           示例 feature，只建空结构和一个占位 Screen
:konsistTest            纯 Kotlin 测试模块，只放架构与规范测试

## 依赖规则（写进各模块 build.gradle.kts，硬约束）

- :domain 不依赖任何模块（它是 jvm 模块，Android API 天然不可用）
- :data 依赖 :domain、:core:common、:core:logging
- :feature:* 依赖 :domain、:core:common、:core:logging、:core:designsystem、:core:ui
- :feature:* 【禁止】依赖 :data —— 实现类由 :app 通过 Hilt 注入
- :feature:* 之间【禁止】互相依赖
- :core:designsystem 不依赖 :domain
- :app 依赖所有模块

## build-logic（included build，重点）

创建 build-logic 目录作为 included build，定义以下约定插件，
各模块只 apply 插件，不重复写配置：

  myapp.android.application
  myapp.android.application.compose
  myapp.android.library
  myapp.android.library.compose
  myapp.android.feature          （feature 模块专用，含标准依赖集）
  myapp.android.room
  myapp.jvm.library              （domain 用）
  myapp.hilt
  myapp.android.lint

## 数据层架构：离线优先

Repository 实现遵循 offline-first：
- UI 只从本地数据库读取（Flow）
- 网络只负责往本地数据库写
- 同步由 WorkManager 触发，失败不影响已有数据展示
- Repository 接口返回 domain 模型的 Flow，不返回 Response/Call

## Room 迁移（硬约束）

- 禁止使用 fallbackToDestructiveMigration()（会清空用户数据）
- 每次 schema 变更必须写 Migration 并导出 schema JSON 进版本控制
- 配置 room { schemaDirectory("$projectDir/schemas") }

## 需要生成的文件

1. settings.gradle.kts（含 includeBuild("build-logic")）
2. gradle/libs.versions.toml
3. build-logic 下的全部约定插件
4. 各模块 build.gradle.kts（按依赖规则，多一个依赖都不要加）
5. config/detekt/detekt.yml
6. konsistTest 下的架构测试（规则清单见下）
7. core:designsystem 下的 token 文件（Color/Type/Spacing/Sizes/Radius/Elevation）
8. core:ui 下的三态组件（LoadingState / EmptyState / ErrorState）
9. core:logging 的 Logger 接口与默认实现
10. CLAUDE.md（内容我会单独给你）
11. TASKS.md、.gitignore、docs/ 目录骨架

## detekt 阈值
LargeClass 250 / LongMethod 40 / TooManyFunctions 12
LongParameterList 6 / ComplexMethod 12 / build.maxIssues 0
ForbiddenImport: androidx.compose.material.*（只用 M3）

## Konsist 规则清单

分层：
1. assertArchitecture：domain.dependsOnNothing()，data.dependsOn(domain)，
   feature.dependsOn(domain)
2. feature 包禁止 import com.<pkg>.data.*
3. feature 包之间禁止互相 import
4. domain 包禁止出现 android.* / androidx.* import
5. 任何模块禁止 import android.util.Log（必须走 core:logging）

命名与位置：
6. 继承 ViewModel 的类必须以 ViewModel 结尾
7. UseCase 后缀的类必须在 ..domain.usecase..，且只有一个 public 方法
8. Repository 接口在 ..domain.repository..，实现在 ..data.repository.. 且以 Impl 结尾
9. Dto 后缀的类必须在 ..data.. 包下
10. Composable 函数名必须大写开头

结构：
11. ViewModel 的 public 属性只能是 StateFlow（禁止 SharedFlow / Channel / Mutable*）
12. Repository 接口方法返回类型不得是 Response / Call
13. 单个文件不超过 250 行
14. ViewModel public 方法不超过 8 个

设计系统（scope 限定 feature/ 与 data/，排除 *Preview.kt 和测试目录）：
15. 禁止 Color(0x........) 硬编码
16. 禁止内联 dp 数值（0.dp、1.dp 除外）
17. 禁止 fontSize = X.sp 内联
18. 禁止硬编码中文字符串（必须 stringResource）

数据库：
19. 禁止调用 fallbackToDestructiveMigration

## 执行方式

先进 plan mode，列出要创建的文件清单和各自职责，我确认后再写。
分三批，每批停下来等我确认：
  批次1 = settings/version catalog/build-logic/模块骨架
  批次2 = detekt + Konsist + core:designsystem token + 三态组件 + core:logging
  批次3 = CLAUDE.md / TASKS.md / docs 骨架 / .gitignore
````

---

## 3. CLAUDE.md 完整版

生成后用这份覆盖。`ln -s CLAUDE.md AGENTS.md` 让 Codex 共用。

````markdown
# 项目约定

## 架构
Google 官方架构指南分层（UI / Domain / Data）+ 单向数据流（UDF）。
多模块 Gradle，依赖方向单向不可逆：

    app → feature/* → domain ← data
    feature/* → core/*

### 硬性规则（违反即 bug，不接受"先这样后面再改"）
- feature 禁止 import data 包下任何内容，实现类由 app 通过 Hilt 注入
- feature 之间禁止互相依赖
- domain 是纯 Kotlin 模块，禁止 android.* / androidx.*
- DTO 不得越过 data 层边界，必须在 data 层映射成 domain 实体
- ViewModel 不得直接调 Retrofit / Room，必须经过 UseCase
- ViewModel 对外只暴露 StateFlow；不用 Channel / SharedFlow 发一次性事件，
  把事件表达成 state（如 UiState.userMessage: String?），UI 消费后回调清除
- 纯 UI 状态（展开/收起、Tab 选中）用 remember 留在 Composable，不进 ViewModel
- 禁止直接用 android.util.Log，统一走 core:logging 的 Logger
- 禁止 fallbackToDestructiveMigration，schema 变更必须写 Migration

## 新增逻辑时的默认动作
**默认新建 UseCase / 新建文件。往已有类加方法是例外，需要理由。**

在往任何已有类添加方法之前，必须先报告：
- 该类当前行数、public 方法数
- 该类当前职责的一句话概括
- 新逻辑为什么属于这个职责而不是一个新职责

说不清就新建。

## 开工前必读
实现新功能前，先读 docs/patterns/README.md 找对应场景，
按索引打开它指向的真实代码，照那个结构写。
找不到对应样板时告诉我，一起定一个新的。

## 设计系统（硬约束）
视觉常量唯一来源是 :core:designsystem，业务代码禁止内联任何视觉数值。

禁止：
- Color(0xFF...) → MaterialTheme.colorScheme / AppTheme.extendedColors
- 内联 dp（0.dp、1.dp 除外）→ Spacing / Sizes / Radius / Elevation
- fontSize = X.sp → MaterialTheme.typography
- 硬编码字符串 → stringResource(R.string.xxx)
- import androidx.compose.material.* → 只用 Material3
- 自己写 loading/空态/错误态 → 用 LoadingState / EmptyState / ErrorState
- 自己搓按钮/卡片/输入框 → 用 AppButton / AppCard / AppTextField

找不到合适 token 时：不要内联，也不要"数值接近就借用"
（Spacing.lg 和 Sizes.iconMd 都是 16dp 但语义不同）。
停下来告诉我缺什么、用在哪，由我决定新增还是改用现有的。

新增 token 命名走语义不走数值（Spacing.xxl，不是 Spacing.dp32）。
颜色必须同时给暗色模式值。

## 日志规范
- 统一用 core:logging 的 Logger 接口
- 禁止记录：手机号、身份证、token、密码、完整地址、精确位置
- 记录对象用脱敏摘要，禁止 toString 整个 data class
- 关键路径（网络、状态机跳转、支付、登录）必须记录且不采样
- tag 用类名

## 国际化
所有用户可见文案进 strings.xml。命名 <模块>_<场景>_<语义>。
带参数用占位符不要拼接；复数用 plurals；布局用 start/end 不用 left/right。

## 自检要求（每次改完必须执行）
    ./gradlew :konsistTest:test detekt lint test

全部通过才算完成。

**架构测试失败时必须修实现，禁止修改 Konsist 断言、detekt 配置或 lint 抑制来变绿。
如果你认为某条规则本身有问题，停下来告诉我，由我决定是否调整。**

## 工作方式
- 编码前先进 plan mode，列出改动文件和职责，等我确认
- 一次只做 TASKS.md 中「当前任务」那一条
- 不顺手重构无关代码，不顺手加没要求的功能
- 不确定的设计决策停下来问，不要自己拍板

## 交叉审查（配了 codex MCP 后启用）
任务完成且本地全绿后，调用 codex 审查，传入：本次 git diff、
本文件的架构与设计系统章节、TASKS.md 中该任务的验收标准。
要求它只输出分级问题清单，不改文件。
收到后逐条评估：认同的修复，不认同的说明理由交我判断。
````

---

## 4. Hooks 配置

`.claude/settings.json`。结构是「事件名 → matcher → command」三层。

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          { "type": "command", "command": "cat docs/LESSONS.md docs/patterns/README.md 2>/dev/null" }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": ".claude/hooks/check-file-size.sh" }
        ]
      }
    ]
  }
}
```

`.claude/hooks/check-file-size.sh`：

```bash
#!/usr/bin/env bash
# 目标文件超过 250 行则拒绝写入。退出码 2 = 阻止工具调用，stderr 回喂给模型。
path=$(jq -r '.tool_input.file_path // empty')
[ -z "$path" ] || [ ! -f "$path" ] && exit 0
lines=$(wc -l < "$path")
if [ "$lines" -gt 250 ]; then
  echo "文件 $path 已有 $lines 行，超过 250 行上限。请先拆分，或把新逻辑放进新文件。" >&2
  exit 2
fi
exit 0
```

```bash
chmod +x .claude/hooks/check-file-size.sh
```

> SessionStart 注入的文本要写成**陈述句**（"本仓库使用 X"），
> 不要写成命令句——带外部系统指令口吻的文本会触发提示词注入防御，
> 导致 Claude 把文本呈现给你而不是当作上下文。

三层递进：hook 拦在写入前 → detekt 拦在构建 → Konsist 拦在测试。

---

## 5. 流程与知识模板

### specs/<feature>.md

```markdown
# <功能名>

## 要解决什么问题
（一段话，从用户视角）

## 验收标准
- [ ] 可验证的条件 1（不要写"体验好"这类）
- [ ] 可验证的条件 2

## 数据与接口
- 涉及的 domain 模型：
- Repository 接口签名：
- 服务端接口：

## 明确不做
- （防止 AI 顺手扩展）

## 开放问题
- （由我拍板后填答案，不要让 AI 自己决定）
```

### TASKS.md

```markdown
## 当前任务
- [ ] T-001 <一句话>
      规格：specs/xxx.md
      验收：<具体到可验证>
      范围：<只允许改哪些目录>
      不做：<明确排除>

## 待办
## 已完成
```

### docs/patterns/README.md

```markdown
# 参照写法索引

实现前先在这里找场景，按索引打开指向的真实代码，照那个结构写。
样板指向真实代码路径，不贴代码片段——这样样板不会过期。

| 场景 | 参照文件 | 要点 |
|---|---|---|
| 新建 feature 模块 | feature/home/ | 模块结构、Hilt 装配、导航注册 |
| 新建 UseCase | domain/usecase/GetXxxUseCase.kt | 单一 public 方法、operator invoke |
| 离线优先 Repository | data/repository/XxxRepositoryImpl.kt | 本地读、网络写、Flow 返回 |
| 分页列表 | （待补） | |
| 表单校验 | （待补） | |
| 页面三态 | core/ui/state/ | LoadingState/EmptyState/ErrorState 用法 |
```

### docs/LESSONS.md

```markdown
# 踩过的坑

保持极简。能升级成机器断言的，升级后就从这里删掉。

升级路径：
  一次性错误   → 当场改掉，不记录
  重复 2 次    → 记在这里
  重复 3 次    → 提炼成 CLAUDE.md 规则
  可机器检测   → 升级成 Konsist / detekt / hook 断言，然后从这里删除

---

- [示例] [2026-09-15] Room 用了 fallbackToDestructiveMigration 会清空用户数据。
  → 已升级为 Konsist 断言，本条可删。
```

**收集仪式**：每修完一个 bug 问自己一句"这个会不会再犯"。会就记一条，三十秒。
不要让 AI 自动判断什么值得记，噪音太大。

---

## 6. CI 三级质量门禁

```yaml
# .github/workflows/ci.yml
name: CI
on: [pull_request, push]

jobs:
  hard:                      # hard-mandatory：失败即阻断，不可绕过
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with: { distribution: temurin, java-version: '17' }
      - uses: gradle/actions/setup-gradle@v4
      - run: ./gradlew assembleDebug
      - run: ./gradlew test
      - run: ./gradlew :konsistTest:test
      - run: ./gradlew lint

  soft:                      # soft-mandatory：失败标记但不阻断合并
    runs-on: ubuntu-latest
    continue-on-error: true
    steps:
      - uses: actions/checkout@v4
      - run: ./gradlew detekt spotlessCheck
      - run: ./gradlew dependencyGuard

  advisory:                  # advisory：只报告
    runs-on: ubuntu-latest
    continue-on-error: true
    steps:
      - uses: actions/checkout@v4
      - run: ./gradlew jacocoTestReport
      - name: APK 体积
        run: ./gradlew assembleRelease && ls -lh app/build/outputs/apk/release/
```

**别把所有规则都设成 hard**。全 hard 会让 AI 卡在琐事上反复折腾；全 soft 等于没有。
现阶段 hard 就放：编译 + 测试 + Konsist + lint。

---

## 7. 验证护栏（第 5 步，别跳过）

骨架搭完后逐条验证。**必须看到红色失败**，绿的说明规则写错了。

```kotlin
// 1. 在 feature/home 下加一行
import com.yourpkg.data.repository.UserRepositoryImpl
// 跑 ./gradlew :konsistTest:test → 必须红

// 2. 在某个 Composable 里
Color(0xFF3366FF)          // → 必须红
Modifier.padding(13.dp)    // → 必须红
Text("提交订单")            // → 必须红
Text(fontSize = 15.sp)     // → 必须红

// 3. 在 domain 模块里
import android.content.Context   // → 必须编译失败（jvm 模块）

// 4. 随便找个文件塞到 300 行 → 写入时 hook 必须拒绝

// 5. Room 里写 fallbackToDestructiveMigration() → 必须红
```

全部验证通过后 commit，这是你的基线。

---

## 8. 日常循环

```
① 你：写 specs/<feature>.md，拆成 TASKS.md 里的小任务
② 你：一次只放一条进去
③ CC：plan mode 出方案（Shift+Tab），不写代码
④ 你：扫一眼方案 —— 全流程性价比最高的一分钟
⑤ CC：实现（先读 docs/patterns 对应样板）
⑥ 机器：./gradlew :konsistTest:test detekt lint test，红了 CC 自己修
⑦ Codex：交叉审查（git diff + 规格 + 架构章节，只列问题不改）
⑧ CC：修复认同的问题
⑨ 你：git commit
⑩ 复盘三十秒：有没有值得进 LESSONS.md 的
⑪ 开新会话，下一条任务
```

三条纪律：
- **一任务一 commit**（回滚点）
- **一任务一新会话**（防上下文稀释导致"忘记架构"）
- **两个 agent 不同时写文件**（串行，或 git worktree 隔离）

Codex 接法先用手工（`git diff > /tmp/review.diff` 再贴给 codex），
跑顺一周摸清它的审查质量，再考虑 `claude mcp add --transport stdio --scope project codex -- codex mcp-server`。

---

## 9. 上线前补（现在不用做）

崩溃监控（Bugly / Sentry 自建）· 日志落盘实现（Xlog）与回捞链路 ·
埋点 · 隐私合规全套（同意前不得采集任何信息，含 SDK 初始化）·
R8 混淆 + mapping 归档 · 多渠道打包（Walle / VasDolly）· 灰度 ·
远程配置与功能开关 · 包体积监控 · Baseline Profile

**但 core:logging 的接口层、远程配置的接口、错误模型现在就要定好**——
它们的调用点会散布全代码库，晚了改不动。

---

## 10. 三条判断原则

**接口先行，实现后补。** 日志、埋点、远程配置、错误模型的接口第一天定好，
实现可以先用最笨的版本。崩溃平台、APM 这些是"接进来"的，晚接没有额外成本。

**能编译期拦的不要留到运行期。** Gradle 模块依赖 > hook 拦截 > Konsist 断言 >
detekt > 文档约定。这个顺序在 AI 协作下的差距比人类协作大得多。

**知识库要保持很小。** 凡是能变成机器断言的就不要留在文档里。
LESSONS.md 大到读不完就等于没有。
