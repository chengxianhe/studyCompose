# studyCompose

中文 | [English](README.en.md)

一个关于「让 AI 辅助的 Android 开发始终受架构约束」的个人参考项目：架构规则用机器断言
（Konsist、detekt、lint、Dependency Guard）强制执行，而不是只写在文档里。

具体是一个 Jetpack Compose 多模块 Android 工程脚手架，外加一个独立的
「受治理 AI 知识平台」原型（`platform/`）。两部分完全隔离，`platform/`
不进 Gradle 构建，Android 那边的架构规则也不约束 `platform/`。

## 这个仓库有什么

```
app/ feature/* core/* domain/* data/*   Android app，官方架构分层 + UDF
build-logic/                            Gradle 约定插件
konsistTest/                            架构规则的机器断言
docs/                                   架构/流程/AI协作方案文档
template/                               从这个工程提炼出的可复用脚手架，另起新工程用
platform/                               独立 Python 服务：知识治理原型（见下）
CLAUDE.md / AGENTS.md                   AI 协作硬规则（后者是前者的符号链接）
```

## 怎么用

### Android 部分

```bash
bash scripts/verify.sh android  # 完整门禁 + debug APK 构建
```

- 工作流与独立模型回归见 [docs/workflow.md](docs/workflow.md)，当前任务见 `TASKS.md`。
- 开工前先读 `AGENTS.md`（链接到 `CLAUDE.md`）——架构分层、设计系统 token、日志规范这些硬规则都在这里，
  违反了 CI 会红。
- 具体场景该怎么写，先查 `docs/patterns/README.md` 找对应索引再动手。
- 想了解这套脚手架是怎么从零搭起来的，看 `docs/compose-ai-bootstrap-final.md`；
  要另起一个新的 Compose 多模块工程，直接用 `template/` 目录，不用从这个仓库里现拆。

### `platform/`（AI 知识治理原型）

```bash
bash scripts/verify.sh platform
```

- 通过 MCP 暴露 `knowledge.search` / `knowledge.propose` 两个工具，配置写在仓库根目录
  的 `.mcp.json` 里——用 Claude Code 或 Codex 打开这个仓库时会提示是否信任，信任后
  这两个工具就能直接在对话里用。
- 具体用法、已知的信任边界、已经实现的检测能力，看 `platform/README.md`。
- 设计背景和取舍，看 `docs/ai-engineering-governed-delivery-platform.md`（完整方案）
  和 `docs/ai-engineering-governed-delivery-platform-baseline.md`（阶段0落地决策+
  验收状态）。

## 现在是什么状态，别高估

- Android 侧：Konsist、detekt、lint、单测、Spotless、Dependency Guard 与 debug APK 构建全部必过；
  Jacoco/APK 体积仅报告。远端合并阻断还需配置分支规则，不能仅凭 YAML 宣称已强制。
- `platform/` 侧：知识审核检索、交付契约、Harness 状态追踪已在 T-P0～T-P8 实现；
  这仍是原型，真实任务全流程验收尚未完成，见 `docs/tasks/completed-platform.md`。
- 当前业务为本地相册；进度、既有未提交实现和未验收性能目标以 `TASKS.md` 及任务接续记录为准。

## 维护计划

两条不同的升级路径，分别对应 Android 代码规则和知识库本身：

**Android 侧的"踩坑 → 规则"升级路径**（`docs/LESSONS.md` 定义，已经在跑）：

```
一次性错误   → 当场改掉，不记录
重复 2 次    → 记进 docs/LESSONS.md，AI 会提示可以写进知识库了
重复 3 次    → 提炼成 CLAUDE.md 硬规则
可机器检测   → 升级成 Konsist / detekt / hook 断言，然后从 LESSONS.md 删除
```

**`platform/` 侧的路线图**（细节见 baseline 文档 §6）：

- 当前：阶段0～3 的原型能力已有归档；下一步按用户明确任务验证真实使用，不自行扩建治理系统。
- 已知但暂不处理的技术债：审计日志 90 天保留目标还没有清理任务（数据量小，
  不着急）；现在只支持单个工程独享一份知识库，多个工程共享需要先补上"空间"
  隔离概念（原方案 §5，阶段0故意没做），不是简单改改配置就行。

## 维护者

目前是个人项目，`chengxianhe` 一个人维护，以 Codex 为主要开发助手；Claude 配置保留兼容。
发现问题或者有想法，直接开 issue。

## 协议

[MIT License](LICENSE)——随便用、改、商用都行，保留版权声明就好。
