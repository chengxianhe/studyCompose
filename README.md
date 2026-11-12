# studyCompose

中文 | [English](README.en.md)

一个正在开发的本地相册应用，也是 AI 辅助 Android 开发的工程实践项目。
应用采用 Jetpack Compose 多模块架构，以机器检查约束代码分层、设计系统和依赖；
独立的 Python 平台负责知识审核、任务契约与验证证据，最终审查和交付由用户确认。

## 当前功能

### Android 相册

| 功能 | 当前状态 |
|---|---|
| 媒体权限与同步 | 从系统 MediaStore 读取图片和视频，轻量元数据同步到 Room；支持增量、删除对账和时区变化重算 |
| 照片日流 | 固定五列网格、粘性日期头、日期滑块跳转；按设备时区分日，未知日期桶置底 |
| 按需加载 | 根据可见日期查询当天数据，支持请求取消、失败重试与缓存淘汰；Coil 加载缩略图并限制缓存 |
| 四 Tab 导航 | Navigation 3 管理独立返回栈；照片已接入日流，相册、回忆、修图目前为占位页 |
| 后续功能 | 年/月钻取、相册内容、历史上的今天、大图查看、收藏、删除/移动和修图尚未实现 |

日流自动检查已通过，部分真机场景已验证，**T-014 仍待补充设备验证和人工审查**。
RAW（如 CR3/RAF）缩略图、完整权限旅程、返回与未知桶等场景仍有验证缺口。
百万张规模是目标，真实 schema、图片与滚动性能验收由 T-012b 承接，尚未完成。
详见 [当前任务](TASKS.md) 和 [T-014 接续记录](docs/tasks/t-014.md)。

### 知识与任务交付平台

`platform/` 是独立的本机 Python 原型，不参与 Gradle 构建，Android 应用运行不依赖它。

- **知识治理**：提案、目录与全文查看、人工审核/废弃、BM25 与本地向量混合检索，以及备份恢复。
- **本地检索与来源图谱**：固定模型修订与摘要、结构分块/父子关联、ES 混合召回和本地重排；来源、依赖/替代关系及影响查询。
- **宿主主动补证**：内部资料不足时继续选择澄清、外查或授权检查，保留原问、来源和停止原因；工具指引与记录校验不等于独立语义裁判或后台 Agent。
- **任务契约**：结构化验收标准和测试用例、版本校验、人工冻结与运行启动。
- **执行与证据**：会话内的 `prepare / verify / submit / status` 命令连接源码快照、统一检查和验收记录。
- **人工入口**：本机网页提供知识审核、任务确认、人工验收与最终交付；Agent 不代替用户批准。
- **MCP 工具**：`knowledge.list/get/search/propose`、`contract.create/get/update`、
  `harness.record_entry_gate/record_acceptance/get`，配置见 [.mcp.json](.mcp.json)。
  来源与图谱另提供 `graph.source_register/propose/get/list/explain/impact`。

[T-025](docs/tasks/t-025.md) 的真实会话闭环已于 2026-11-06 经用户确认交付；
T-023、T-014 的待审项仍分别保留。平台没有关闭会话后持续开发的后台调度器；
身份声明和证据校验面向本机受信任进程，不提供防伪身份保证。
详见 [平台 README](platform/README.md)、[知识操作](docs/knowledge/README.md) 和 [工作流](docs/workflow.md)。
通用能力的目标、分层及尚未实现的部分见 [架构 v0.2](docs/knowledge/architecture-v0.2.md)
和 [能力路线图](docs/knowledge/capability-roadmap.md)。微信与小看板属于应用适配，核心不依赖它们。

## 快速开始

以下命令均从仓库根目录运行。

### Android 应用

准备 JDK 17（与 CI 一致）、Android SDK 36 和 Python 3。在 Android Studio 中打开仓库，
或在本机 `local.properties` 配置 SDK 路径。应用最低支持 Android 7.0（API 24）。

```bash
# 完整检查并构建 debug APK
bash scripts/verify.sh android
```

APK 位于 `app/build/outputs/apk/debug/app-debug.apk`。可通过 Android Studio 安装运行；
照片页面需要用户授予相应媒体读取权限。

### 本机审核页

平台需要 Python 3.11+ 和 `uv`。

```bash
uv sync --project platform --locked
uv run --project platform python -m govplatform.review
```

打开 <http://127.0.0.1:8765/>，任务入口为 <http://127.0.0.1:8765/tasks>。
Android 应用与审核页可分别使用；MCP 接入方式见 [平台 README](platform/README.md)。

## 验证与交付

```bash
bash scripts/verify.sh android   # 架构、静态检查、单测、格式、依赖基线与 APK
bash scripts/verify.sh platform  # ruff、mypy、pytest 与 MCP 导入
bash scripts/verify.sh all       # 两端完整检查，含工作流脚本测试
```

统一入口保存 HEAD、前后源码指纹、完整日志与退出码到本机 `.verification/`。
源码在检查期间变化会使结果失效；检查证据和平台运行数据库不提交到 Git。

2026-11-09 的提交版本 `d4f5f5b` 已通过 `all`：工作流 9 个测试、Android 完整门禁、
平台 120 个测试通过。这是该版本的自动检查记录，不代替真机、性能或人工验收。
2026-11-12 的 T-031 候选快照通过平台完整门禁：192 项测试，无跳过，含真实本机 ES 与 stdio MCP；
新增 24 项补证记录测试，六类宿主案例中四类为真实工具观察、两类为明确回放。
T-026～T-031 的实现、未验证项与人工状态见各任务接续，不能用测试通过替代人工交付。
CI 使用相同入口；远端合并阻断仍需分支规则配合，Jacoco/APK 体积为报告项。

## 工程结构

```text
app/                  应用入口、四 Tab 导航与依赖组装
feature/library/      照片日流；后续相册/回忆共用的功能模块
feature/home/         保留的权限与同步状态页面
domain/               纯 Kotlin 实体、Repository 接口与 UseCase
data/                 MediaStore、Room、同步与 Repository 实现
core/                 设计系统、通用 UI、日志与公共能力
build-logic/          Gradle 约定插件
konsistTest/          架构与设计规范的机器断言
benchmark*/           性能测试与基准目标应用
platform/             独立知识与任务交付平台
scripts/              统一验证入口与源码指纹工具
docs/                 任务接续、架构、证据与工作流说明
template/             可复用脚手架参考
```

依赖方向为 `app → feature → domain ← data`；feature 可依赖 core，禁止 feature 互相依赖或直接访问 data。
UI 使用单向数据流，ViewModel 经 UseCase 访问业务逻辑，对外暴露 StateFlow；
视觉 token 统一来自设计系统，用户文案使用字符串资源。

开发前阅读 [AGENTS.md](AGENTS.md)（指向 [CLAUDE.md](CLAUDE.md)）和
[真实代码样板索引](docs/patterns/README.md)。自动检查由执行者完成，代码最终审查由用户负责，
当前不默认启动独立模型审查。架构背景见 [工程搭建说明](docs/compose-ai-bootstrap-final.md)，
历史记录中的旧流程以当前项目约定为准。

## 维护与协议

个人项目，由 `chengxianhe` 维护，以 Codex 为主要开发助手，保留 Claude 配置兼容。
问题和建议欢迎提交 issue。[MIT License](LICENSE)。
