# 一个成熟 Android 工程需要具备什么

> 按领域分类，每项标注优先级：
> **P0** = 第一天就该有，后补代价极高
> **P1** = 有真实用户前补上
> **P2** = 团队变大 / 规模上来后补
> **P3** = 按需

---

## 一、构建工程

| 项 | 优先级 | 说明 |
|---|---|---|
| Gradle Version Catalog | P0 | `gradle/libs.versions.toml`，依赖版本集中管理 |
| **build-logic 约定插件** | P0 | included build，把构建配置抽成 `xxx.android.library` 这类插件。多模块项目不做这个，build.gradle.kts 会失控 |
| Kotlin DSL | P0 | 别用 Groovy |
| KSP 而非 kapt | P0 | 编译快一个量级 |
| Product Flavors | P1 | demo/prod、内网/线上，NiA 就是这么分的 |
| R8 混淆 + 资源压缩 | P1 | `minifyEnabled` + `shrinkResources`，配好 keep 规则 |
| 签名配置外置 | P0 | keystore 密码走环境变量/CI secret，**绝不进仓库** |
| Gradle 构建缓存 / 配置缓存 | P1 | `org.gradle.caching=true`、`configuration-cache=true` |
| Remote Build Cache | P2 | 团队 3 人以上收益明显 |
| Dependency Guard | P1 | 锁定依赖树，防止传递依赖悄悄变化引入风险 |
| 依赖漏洞扫描 | P2 | OWASP dependency-check / Snyk |

---

## 二、架构与模块化

| 项 | 优先级 | 说明 |
|---|---|---|
| 三层分层（UI / Domain / Data） | P0 | Google 官方架构指南，不是 MVVM 这个标签 |
| 单向数据流 UDF | P0 | ViewModel 产出 state，不发一次性事件 |
| **domain 为纯 Kotlin 模块** | P0 | 编译期隔离平台代码，将来跨平台的基础 |
| feature 模块化 | P0 | 一个业务一个模块 |
| feature api/impl 拆分 | P2 | NiA 的做法，编译图更瘦，团队大了才值 |
| DI（Hilt） | P0 | 模块间解耦的前提 |
| Navigation 3 | P0 | 导航栈变成可观察 state |
| Adaptive UI（大屏/折叠屏） | P1 | Material3 Adaptive + WindowSizeClass |
| 统一 Result / Error 模型 | P0 | 错误处理散落是后期最难重构的债之一 |

---

## 三、代码质量与护栏

| 项 | 优先级 | 说明 |
|---|---|---|
| Spotless + ktlint | P0 | 格式统一，消除无意义 diff |
| detekt | P0 | 复杂度、文件长度、坏味道。**AI 协作场景必备** |
| **Konsist 架构测试** | P0 | 分层依赖、命名、结构断言。AI 场景下这是最有效的护栏 |
| Android Lint | P1 | 内置规则先开严，`lintOptions { abortOnError true }` |
| 自定义 Lint 规则 | P2 | NiA 自己写了一套，团队大了才值得投入 |
| CI 强制门禁 | P0 | 上面所有检查必须在 CI 上跑，本地能跳过就等于没有 |
| PR 模板 + review 清单 | P1 | AI 生成的代码要当外部贡献者的 PR 对待 |

---

## 四、测试体系

| 项 | 优先级 | 说明 |
|---|---|---|
| 单元测试（JUnit + Truth） | P0 | 比例约 70% |
| Turbine | P0 | 测 Flow 必备 |
| coroutines-test | P0 | |
| **test double 而非 mock** | P1 | NiA 的理念：用 Hilt 替换真实实现为简化版，比 mock 具体调用更不易碎 |
| Robolectric | P1 | JVM 上跑 Android 代码，比 instrumentation 快得多 |
| Compose UI Test | P1 | |
| **Roborazzi 截图回归测试** | P2 | UI 改动的视觉 diff，防止 AI 顺手改坏样式 |
| 无障碍自动检查 | P2 | roborazzi-accessibility-check |
| Jacoco 覆盖率 | P2 | 别追求高数字，用来发现完全没测的模块 |
| E2E / 冒烟用例 | P1 | 发版前必跑的关键路径 |

---

## 五、可观测性（线上问题怎么发现和定位）

这块是最容易被新项目漏掉的，也是上线后最痛的。分五件事，别混为一谈：

### 5.1 崩溃 / ANR 监控 —— P1

| 方案 | 适用 |
|---|---|
| **Bugly**（腾讯） | 国内首选。Android/iOS/鸿蒙/小程序/Unity 全覆盖，ANR 深度分析、Native Crash 定位、AI 辅助归因。注意专业版可能收费 |
| **Sentry 自建** | 开源可私有化。前后端已用 Sentry 时统一技术栈划算 |
| **友盟+** | 接入最轻，适合快速起步；深度诊断弱 |
| Firebase Crashlytics | 出海场景；国内不可靠 |

### 5.2 本地日志 + 回捞 —— 接口 P0，实现 P1

**为什么单独算一块**：崩溃堆栈只有最后一刻现场，很多线上问题根本不崩溃。要还原"用户点了什么导致白屏"，只能靠日志。

完整链路四段：

1. **写入层**
   - **Xlog**（腾讯 mars，微信同款）：mmap + 压缩 + 加密，高性能、不丢日志、不卡顿
   - **Logan**（美团）：同样 mmap + 加密，理念是关键日志不采样（网络日志会完整记 Headers、原始 URL）
   - 坑：Logan 开源的**只有存储 SDK**，回捞接口和后端要自己实现
   - 建议：先只接 Xlog，用自己的接口封装，便于以后替换

2. **触发回捞**
   - 推送下发指令（携带 userId + 时间范围）
   - 或启动/前后台切换时拉配置接口查是否有回捞任务（更稳，不依赖推送到达率）
   - 用户主动反馈时触发（最常用，成本最低）

3. **上传**
   - 分片、断点续传、仅 WiFi、失败重试、大小上限、去重

4. **后端解码与检索**
   - xlog 是加密压缩的，要先解码
   - ⚠️ 体积警告：10MB 的 xlog 解码后可达 ~100MB 纯文本，普通编辑器打不开，需要 klogg 这类流式查看工具
   - 规模上来后接 ELK / Loki

**必须做的两件事**：
- **脱敏在写入层完成**（手机号、身份证、token、精确位置、完整地址），落盘即采集，上传时再过滤已经晚了
- **分级 + 体积控制**：本地滚动保留 7 天、按级别分文件、Release 默认 INFO 以上、DEBUG 靠远程开关临时打开

### 5.3 性能 APM —— P2
- **Matrix**（微信开源）：卡顿、内存泄漏、IO、帧率、电量，国内最完整
- androidx.metrics（JankStats）：帧率
- 启动耗时埋点

### 5.4 业务埋点 —— P1
- 神策 / GrowingIO / 友盟 U-App，或自建（本质是上报接口 + 数仓，最容易自建的一块）
- 关键：**埋点规范先定，字段命名统一**，否则后期数据没法用

### 5.5 推送 —— P1（如果需要）
- 国内必须做厂商通道聚合（小米/华为/OPPO/vivo/荣耀），否则 App 被杀就收不到
- 极光、个推等聚合服务，或自己接各家原生 SDK

---

## 六、发布与运维

| 项 | 优先级 | 说明 |
|---|---|---|
| CI（PR 触发全量检查） | P0 | GitHub Actions / GitLab CI，跑 lint + detekt + konsist + test + build |
| CD（自动打包分发） | P1 | 蒲公英 / fir.im / Firebase App Distribution |
| 版本号自动化 | P1 | 从 git tag 生成，别手改 |
| **多渠道打包** | P1 | 国内应用商店多，用 Walle（美团）或 VasDolly（腾讯）做 V2 签名快速渠道包 |
| 灰度发布 | P1 | 各应用商店的分阶段发布 + 自己的开关 |
| **远程配置 / 功能开关** | P0 | 出事能关功能，是线上止损的最后手段。可自建（一个 JSON 接口即可） |
| 热修复 | P2 | Tinker（微信）/ Robust（美团）。维护成本高，慎上 |
| 强更 / 版本管理 | P1 | 服务端下发最低支持版本 |
| 符号表 / mapping 归档 | P0 | 混淆后不存 mapping = 崩溃堆栈永远看不懂 |

---

## 七、性能工程

| 项 | 优先级 | 说明 |
|---|---|---|
| Baseline Profile | P1 | 启动和滚动性能提升明显，NiA 标配 |
| Macrobenchmark | P2 | 量化启动耗时、帧率 |
| ProfileInstaller | P1 | 配合 Baseline Profile |
| Compose Runtime Tracing | P2 | 排查重组问题 |
| **包体积监控** | P1 | CI 上记录每次 APK/AAB 大小，超阈值告警。不监控就会一路膨胀 |
| 启动优化 | P1 | 异步初始化、延迟加载、Startup 库 |

---

## 八、安全与合规（国内尤其重要）

| 项 | 优先级 | 说明 |
|---|---|---|
| **隐私合规** | P0 | 隐私政策、首次启动弹窗、**同意前不得采集任何信息**（含 SDK 初始化）。违规直接下架 |
| 个人信息清单 | P0 | 上架必填，SDK 采集了什么要说清楚 |
| 网络安全配置 | P0 | `networkSecurityConfig`，禁明文、证书校验 |
| 敏感数据加密存储 | P0 | 别把 token 明文丢 SharedPreferences |
| 代码混淆 + 资源混淆 | P1 | R8 + AndResGuard |
| 加固 | P2 | 360/腾讯乐固等，看业务敏感度 |
| 应用签名保护 | P1 | 防二次打包校验 |
| 三方 SDK 审计 | P1 | 每个 SDK 采集什么必须清楚，合规责任在你 |

---

## 九、适配与体验

| 项 | 优先级 | 说明 |
|---|---|---|
| Edge-to-edge | P0 | Android 15+ 强制，有官方 Skill 可用 |
| 深色模式 | P1 | |
| 多语言 / i18n | P3 | 只做国内可跳过，但字符串统一进 strings.xml 是 P0 习惯 |
| 无障碍 | P2 | contentDescription、触控区域 |
| 大屏 / 折叠屏 | P1 | |
| 国产 ROM 适配 | P1 | 权限、后台保活、推送、通知，各家行为不一致 |

---

## 十、协作与文档

| 项 | 优先级 | 说明 |
|---|---|---|
| README（如何跑起来） | P0 | 新人/新机器 30 分钟内能跑通 |
| **CLAUDE.md / AGENTS.md** | P0 | AI 协作的架构约束，软链同一份 |
| TASKS.md 或 issue 看板 | P0 | 任务拆分的载体 |
| ADR（架构决策记录） | P2 | 为什么选了 A 不选 B，半年后自己都会忘 |
| CHANGELOG | P1 | |
| 分支策略 | P0 | trunk-based 或 git flow，定了就别改 |
| Commit 规范 | P1 | Conventional Commits，能自动生成 changelog |

---

## 十一、AI 协作基建（2026 新增）

| 项 | 优先级 | 说明 |
|---|---|---|
| **Android CLI + Android Skills** | P0 | Google 官方，2026-04 发布，05 月 I/O 上 1.0 稳定。SKILL.md 形式，覆盖 Nav3 迁移、edge-to-edge、adaptive UI、CameraX、Compose Styles。官方数据：token 降 70%，速度快 3 倍。支持 Claude Code / Codex / Cursor 等几十种 agent。`android skills install <skill>`，homebrew 可装 |
| CLAUDE.md 架构约束 | P0 | 见第十节 |
| 可验证的护栏（Konsist/detekt/test） | P0 | AI 只对"会失败的东西"负责 |
| plan mode 先出方案 | P0 | 绝大部分跑偏发生在没审计划就动手 |
| 交叉审查（另一个 agent 审） | P1 | 角色不对称，做的和审的不是同一个 |
| 小步 commit | P0 | AI 协作的回滚点 |
| 每任务开新会话 | P0 | 防上下文稀释导致"忘记架构" |

---

## 落地顺序建议

**第 0 周（骨架）**
Version Catalog → build-logic 约定插件 → 模块结构 → Hilt → Nav3 → Spotless/detekt/Konsist → CI 门禁 → CLAUDE.md/TASKS.md → Android CLI + Skills → **core:logging 接口层**（实现可以先是 Log 转发）→ 远程配置接口 → 签名与 mapping 归档

**上线前**
崩溃监控 → 日志落盘实现 + 回捞链路 → 埋点 → 隐私合规全套 → R8/混淆 → 多渠道打包 → 灰度机制 → 包体积监控

**有用户后**
APM → Baseline Profile → 性能基线 → 数据看板

**团队变大后**
feature api/impl 拆分 → 截图测试 → 自定义 Lint → Remote Build Cache → ADR

---

## 三条判断原则

**接口先行，实现后补。** 日志、埋点、远程配置、错误模型这几样，接口必须第一天定好，因为调用点会散布全代码库；实现可以先用最笨的版本。反过来，崩溃平台、APM 这些是"接进来"的，晚接没有额外成本。

**能编译期拦的，不要留到运行期。** Gradle 模块依赖 > Konsist 断言 > 文档约定。这个顺序在 AI 协作场景下的差距比人类协作大得多。

**没有验证过的护栏等于没有护栏。** 每加一条规则，故意写一行违规代码确认它会红。这一步跳过的话，你以为有保护，实际裸奔。
