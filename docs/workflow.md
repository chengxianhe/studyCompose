# 执行与验收流程

当前规则以 `AGENTS.md`（链接到 `CLAUDE.md`）为准；历史 bootstrap 文档和 `template/` 是参考快照。
本流程不要求 Claude Code 订阅，不依赖 `.claude/` hooks 自动生效。

## 一次任务

1. 读项目约定、当前任务、接续记录、LESSONS 与真实代码样板。记录 HEAD 和已有改动。
2. 提出改动文件、职责、验收方式；用户确认后执行。明确授权持续有效，不重复确认同一个方案。
3. 实现过程中运行针对性测试；完整交付前运行统一入口。失败修实现；门禁本身缺陷另行确认修复。
4. 整理差异与自动检查证据交用户人工审查；代码与知识都不由 Agent 自批。
5. 核实发现，修复后验证与复审；更新任务证据及接续记录。未验证项不可记为通过。
6. 用户授权后才提交/推送；格式化与逻辑改动按项目约定分开，避免夹带接手时的未完成工作。

## 知识与契约接入

正常新任务在步骤 1 搜索有效知识并读取全文/来源，记录引用 ID、版本；空结果按项目文件继续。
步骤 2 用 `contract.create` 建草稿：goal/scope/out_of_scope、结构化 AC、对应 TC、风险、
待澄清问题、有效 knowledge_refs。任务文件记 contract_id；不得引用未批准条目。
用户在本机审核页阅读后冻结，并单独启动运行；Agent 查询运行后在任务文件记 run_id。
范围已在会话中批准时不重复询问方案，但平台的人工状态转换仍由用户执行，不能冒充 Human。
MCP 不可用则明确采用文件记录，注明原因；恢复后不把旧工作伪造为已执行的 Harness 历史。

执行者实际运行统一自检，将 exit code、源码指纹、日志路径写入 `harness.record_entry_gate`。
自动化 AC 可记录真实测试结果；人工审查项由用户确认。按 AC 写 `harness.record_acceptance`，
证据中标明实际验证者和结果，不把执行者的自检写成独立验收。
底层门禁统一核对 prepare 准入、仓库/模式、当前源码和真实日志；自动 AC 的语义结论仍由执行者提供，
**不能把日志存在当成所有业务 AC 已通过，也不能保证审查独立性**。
失败按状态机最多修复 3 轮；人工证据只能由用户确认，待人工项不能自证或标记任务完成。
通过后由用户确认 deliver；会话持续执行不等于关闭会话后仍有后台调度器。

步骤 5 必须评估可复用知识：先搜索去重，再 propose 来源、范围、规则及验证证据；
任务文件记 proposal ID/status，或“无新增可复用知识”与理由。待审核不算已生效。
审核、备份恢复、旧候选清单见 `docs/knowledge/README.md`。

## 验证入口

| 命令 | 范围 |
|---|---|
| `bash scripts/verify.sh android` | 工作流脚本测试、Konsist、detekt、lint、单测、Spotless、APK 依赖基线、debug APK 构建 |
| `bash scripts/verify.sh platform` | 工作流脚本测试、MCP JSON、uv 锁定安装、ruff、mypy strict、pytest、MCP import |
| `bash scripts/verify.sh all` | 以上两端；公共验证脚本/CI/工作流调整时使用 |
| `bash scripts/verify.sh workflow` | 只检查脚本自身，不能声明应用验收通过 |

每次运行在 `.verification/` 保存 HEAD、status、前后指纹、完整日志和退出码。该目录不进 Git；
CI 上传为 artifact。任务记录保留摘要，发布/长期复现需要的测试报告另存到 `docs/metrics/`。
工作区在运行中变化则此次证据不能代表最终版本；重新运行。不会复用旧 success stamp。
Gradle 增量结果须如实标明；怀疑缓存、复现争议时再强制重跑，不能把 UP-TO-DATE 描述为重新执行。
`assembleDebug` 验证打包与依赖注入，但不代表 UI、真实权限、设备性能已验收。

CI 的 Android `hard` 与 Platform CI 的 `hard` 都不允许失败；platform 格式检查暂保留独立软检查。
远端是否阻止合并还取决于分支规则。需在仓库设置核实必需检查，不能用本地 YAML 代替已启用证明。
Platform CI 仅在相关路径变更时运行，不应把可能不产生的检查无条件设为所有 PR 的必需项。

## 自动验证与证据入库

任务由用户冻结并启动后，记录 run_id；先按下面的会话闭环执行 prepare，再运行验证并记录门禁：

```bash
uv run --project platform python -m govplatform.delivery verify \
  --repo /absolute/path/to/studyCompose --mode platform \
  --run-id RUN_ID --session-id CURRENT_SESSION
```

`--mode` 按任务选 android/platform/all。该命令实际执行 `scripts/verify.sh`，保留退出码，
核对 mode、HEAD、检查前后及当前指纹、日志、退出码后，以 Agent 身份记录门禁结果。
非零退出码只记录失败；不自动把 AC 标通过、不代填人工证据、不自动批准或启动任务。
验证失败时自动修实现后重跑；验收失败按既有最多三轮修复机制处理，不用改门禁来变绿。

已有本次验证证据可用 `import --evidence /absolute/path/to/.verification/platform.XXXXXX`
替代 verify；只读检查用 `inspect`，无需 run-id/session-id。导入不能引用不完整/其他模式/
其他源码版本的日志；旧脚本未生成 mode.txt 时须重跑，不手工补写元数据冒充新验证。
结果摘要保存源码指纹、日志路径及 SHA-256。它防止误用，不抵抗同机调用者故意伪造证据。

门禁通过后，执行者按真实测试结果记录自动 AC；用户在任务页填写人工 AC。
补审只沿用同一轮的已有自动结果和真实人工结论，失败轮次不能沿用到修复后的新轮次。
用户明确不通过进入修复，未填写继续待定；记录作者由服务端设置，调用方不能冒充人工证据作者。
同一契约只允许一条活动运行；用户取消/确认交付或运行升级终结后可开新一轮。

## 会话内最小闭环（T-025）

这组命令协调已经人工启动的运行；编码、判断失败原因和修复仍由当前会话的 Agent 执行。
它不会后台启动模型、自动领取任务或代替人工操作。命令从仓库根目录执行。

1. 人工冻结、启动后，执行准入。没有 `--evidence` 时实际运行统一自检；也可传当前有效证据目录。

   ```bash
   uv run --project platform python -m govplatform.delivery prepare \
     --repo "$PWD" --mode platform --run-id RUN_ID --session-id SESSION_ID
   ```

   准入要求检查通过，记录当前 HEAD、源码指纹、既有 WIP 和包含未跟踪文件的快照，绑定仓库及验证模式。
   同一运行重复 prepare 返回原基线，不覆盖；老任务只建立当前接续基线，不补造历史。
   准入材料写进 `.verification/session-*`，索引写入现有审计日志。清理该目录会使证据失效。

2. 在已确认范围内实现、针对性验证和修复。交付前运行上述 `delivery verify`，
   失败保留真实退出码；通过进入 accepting。模式按 android/platform/all 的现有规则选择。
   不能为绕开检查更改绑定模式；HEAD 改变时需重新确认基线，首版不自动迁移运行。

3. 执行者把全部非人工 AC 的实际结果写成 JSON 数组，放在 `.verification/` 内，避免改变源码指纹：

   ```json
   [{"ac_id":"AC-1","passed":true,"evidence_summary":"实际测试命令、结果及对应日志位置"}]
   ```

   示例不是可以直接提交的验收结论；逐项填写，不能用整包检查通过推断业务通过。
   提交实际验证目录及未验证项：

   ```bash
   uv run --project platform python -m govplatform.delivery submit \
     --run-id RUN_ID --session-id SESSION_ID --evidence .verification/platform.ACTUAL \
     --results .verification/ac-results.json --limitations '实际已知风险与未验证项'
   ```

   submit 不接受人工 AC；缺项/重复项拒绝。验证失败不记录 AC 通过；自动 AC 失败进入既有修复流程。
   通过且只剩人工项时进入 waiting_for_human；没有人工 AC 的契约可进入 passed，最终 deliver 仍仅限用户。
   审查包包含契约、准入引用、相对准入的实际差异、完整当前快照、日志哈希、AC 说明、风险和结果状态。
   准入前的 WIP 与本次新增差异分开呈现；包生成不等于状态推进成功，必须核对 outcome.json/实际运行。

4. 中断或换会话后，用 status 读取运行、原基线及最近生成的审查包，不重建任务：

   ```bash
   uv run --project platform python -m govplatform.delivery status \
     --run-id RUN_ID --session-id SESSION_ID
   ```

   人工不通过后，当前会话修复并重新 verify/submit；上一轮已通过的证据目录不得复用。
   人工通过与最终交付时也会核对源码/日志是否仍匹配；变更后旧批准不能继续交付。
   若已 passed 后又改代码，首版需由用户取消并创建新运行；不自动撤销人工结论。

CLI、HTTP、MCP 共享底层证据门禁；HTTP/MCP 的 summary 须为 VerificationEvidence JSON，不能传“ok”。
更新代码后，旧 MCP 与人工审核服务进程须重启才能加载新规则；不把文件已修改当成服务已启用。
真实设备/性能证据仍按任务 AC 单独提供，这些命令不测性能，也不证明图片体验达标。
准入只接收通过的基线；既有失败的豁免、后台调度与无人值守恢复不在首版范围。

## 人工审查

2026-11-04 用户将审查改为人工。当前默认代码最终审查和知识入库均由用户决定，
不再自动启动模型审查；未来若明确要求模型辅助，模型意见仍不能代替人工批准。

交给用户的材料：已批准目标与 AC、任务起点、既有 WIP、本次改动文件与完整 diff、
源码指纹、实际测试命令/退出码/日志、验证缺口。未跟踪文件也必须包含在审查材料中。
实现者核实反馈后修复并重跑受影响检查，再提交新差异；没有人工结论时记“待人工审查”。
本机页面提供知识批准、契约冻结、运行启动和交付按钮；Agent 不代点、不自报 Human。

## 接续与任务状态

每项任务只保留一份 `docs/tasks/<task-id>.md`，`TASKS.md` 链接它。包括：
已批准范围、已实现/未验证、最后检查命令与结果、审查记录、阻塞项、下一步。
结束长会话、任务切换、验证失败或范围变更时更新，不逐条抄聊天记录。
标记完成必须满足该任务的明确验收；拆出的验收任务写清依赖和仍未达成的产品目标。

T-014 负责日流功能及行为测试；T-012b 在功能可运行后验证真实 schema、百万元数据和缩略图路径。
现有占位格基线只能当参考。真实图片场景的预算、数据分布、设备与冷热缓存必须明确，
不能把占位格的 5.5 ms / 76 MB 原样宣称为真实图片页已经达标。
