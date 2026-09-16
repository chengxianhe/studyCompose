# Compose 多模块脚手架模板

从 `studyCompose` 项目里原样抠出来的、和具体业务无关的部分：build-logic 约定插件、
`:domain :data :core:common :core:logging :core:designsystem :core:ui :feature:home :konsistTest`
模块骨架、detekt/Spotless/Konsist/Dependency Guard 配置、hooks、CI、流程文档。
不含 `:app`——新项目的 `:app` 用 Android Studio 建，这里教的是"建好之后怎么接上"。

依据：`docs/compose-ai-bootstrap-final.md`、`docs/compose-design-system-and-ai-constraints.md`
（这两份文档本身没有收进模板，是搭这套东西时的规格来源，原项目 `docs/` 下还留着）。

## 用法

1. 用 Android Studio 建一个新项目（Empty Activity / Compose），拿到一个带 `:app` 的空项目
2. 把这个 `template/` 目录下**除了这份 README**的所有文件复制到新项目根目录（会跟 Android
   Studio 生成的 `settings.gradle.kts`/`build.gradle.kts`/`gradle/` 等文件冲突，直接覆盖）
3. 在新项目根目录跑：
   ```bash
   ./rename.sh com.你的.包名 你的项目前缀
   ```
   比如 `./rename.sh com.acme.myapp acmeMyapp`。这一步把包名和 build-logic 插件 ID 前缀
   （`studycompose`）都换成你的值，同时把 `com/study/cc` 目录结构搬到新包名对应的路径。
4. 手动把 `:app` 接上：
   - `settings.gradle.kts` 里加 `include(":app")`
   - `app/build.gradle.kts` 参照原项目的写法：应用 `<你的前缀>.android.application`、
     `<你的前缀>.android.application.compose`、`<你的前缀>.hilt`、`<你的前缀>.android.lint`，
     再 `implementation(project(":domain"))` 等把其它模块全部依赖上
5. `git init`（如果还没有），跑一遍自检：
   ```bash
   ./gradlew projects
   ./gradlew :app:assembleDebug
   ./gradlew :konsistTest:test detekt lint test
   ```
6. `CLAUDE.md` 里的设计系统 token 数值是本项目的示例值，落地前对照你自己的设计稿走一遍
   `compose-ai-bootstrap-final.md`/`compose-design-system-and-ai-constraints.md` 确认要不要改

## 目录说明

| 路径 | 内容 |
|---|---|
| `build-logic/` | 9个约定插件：`android.application[.compose]`、`android.library[.compose]`、`android.feature`、`android.room`、`jvm.library`、`hilt`、`android.lint` |
| `domain/` `data/` `core/*` `feature/home/` | 按依赖规则接好约定插件的模块骨架，`core/logging`、`core/designsystem`、`core/ui` 里有真实的 Logger/token/三态组件实现 |
| `konsistTest/` | 19条架构规则的 Konsist 测试（分层依赖/命名位置/结构/设计系统/数据库） |
| `config/detekt/detekt.yml` | 阈值配置 |
| `.claude/` | SessionStart 注入 LESSONS/patterns，PreToolUse 拦超过250行的写入 |
| `.github/workflows/ci.yml` | hard/soft/advisory 三级门禁 |
| `CLAUDE.md` `TASKS.md` `docs/` | AI 协作约束和流程模板 |

## 已知限制

- Jacoco 覆盖率报告目前只对纯 `kotlin("jvm")` 模块（`domain`、`konsistTest`）有效——Android
  模块要接真实覆盖率需要 AGP 的变体级 Jacoco 配置，模板里没做（等真的有业务代码、有覆盖率
  可看的时候再按需接）
- Dependency Guard 只 guard 了 `:app` 的 `releaseRuntimeClasspath`，接上 `:app` 后要自己跑
  一次 `./gradlew :app:dependencyGuardBaseline` 生成基线并提交
