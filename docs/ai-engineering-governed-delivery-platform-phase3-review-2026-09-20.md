# 阶段3 Harness 交叉审查修复记录（2026-09-20）

`docs/ai-engineering-governed-delivery-platform-baseline.md` 已经超过
250 行的单文件上限（Edit 工具会被 hook 拦住），这轮修复记录单独开一个
文件，§7.4 提到的"实现完成"之后紧接着发生的事。

## 背景

阶段3骨架（`harness/` 模块 + `contract/` 的 `Waiver`）写完、59 个测试
全绿之后，收到一轮交叉审查（跟之前每一轮一样的格式），3 条 P0 + 3 条
P1。逐条核实（不是照单全收，是先重新读实际代码确认审查说的是不是真的）
后全部认同——都在代码里实打实验证了，不是审查方猜的。修完后 65 个测试
（新增 6 个）、mypy strict/ruff/pytest 全绿。

## 逐条核实与修复

**P0-1：`harness.start` 之前是 Agent 也能调，还注册成了 MCP 工具。**
跟 baseline 文档 §7.1 自己写的"AI 不能自己...启动一轮 Harness 循环"
直接冲突——写代码时把"契约冻结=人已经授权"和"现在要不要真的跑一次=
人点火"这两件事混成一件事了，是实现时对自己写的设计理解错误，不是
文档没说清楚。改成 Human-only，`mcp_server/server.py` 里的
`harness.start` 工具整个删掉，只留 HTTP 出口（跟 `contract.freeze`/
`knowledge.approve` 一个模式）。

**P0-2：`record_acceptance()` 没管 `verification_type`，Agent 能自己把
`manual_evidence` 类型的 AC 判过。** 这条最要命——`manual_evidence`
这个类型当初就是为了实现"遇到没法自动验证的场景，停下来问你"这个
明确选定的行为（`AskUserQuestion` 选的"停下来问你（推荐）"），但代码
里从来没把这个决定接进去，Agent 提交 `passed=True` 系统照单全收。
改成：`manual_evidence` 类型的 AC，只有调用方是 Human 时 `passed=True`
才算数；Agent 提交的对这类 AC 一律当未解决处理（不报错，正常走进
修复轮次——Agent 提交一批结果里混着几条自己判不了的 manual_evidence
是正常情况，不该让整次调用失败）。

**P0-3：`acceptance_results` 每轮覆盖，多轮验收的具体证据丢了。** 只剩
`repair_rounds[].failure_summary` 那句粗略归因，追溯不到某一轮具体谁
提交了什么证据，跟"全过程可追溯"的原则不符。改成跨轮次累积（新增
`AcceptanceResult.round_number` 字段标轮次由服务端盖章），不再覆盖。

**P1-4：乐观锁不是真原子的。** `contract_store.update()` 原来的 SQL 是
`WHERE contract_id = ?`，没有 `AND version = ?`；`contract_service.
update()` 里"读一次版本、Python 里判断、再写"这几步之间有时间窗口，
两个几乎同时的并发写入都可能通过 Python 检查，后写的会静默覆盖先写的
——这在我们的多 Agent 场景下（Claude Code 和 Codex 各自独立的 MCP
server 进程，同时打同一个 SQLite 文件）不是纯理论问题。改成
`contract_store.update()` 支持可选的 `expected_version` 参数，带上时
SQL 本身就是 `WHERE contract_id = ? AND version = ?`，检查和写入是
同一条语句、同一个事务，`rowcount == 0` 判定为冲突。Python 层原来那个
检查保留（给非并发场景一个更快、更清楚的报错），但真正生效的保护在
store 层这条 SQL。

**P1-5：豁免能在契约草稿期申请。** `request_waiver()` 没查契约状态，
而草稿期 AC 内容还能被 `update()` 改，人批的豁免对应哪个版本的 AC
说不清楚。加上 `contract.status != FROZEN` 就拒绝的检查。

**P1-6：`VerificationCase.description`（TC 描述）从来没进敏感信息
筛查。** `_sensitive_reason_in_contract()` 只扫了 title/goal/scope/AC
字段/risks/open_questions，漏了 TC 描述这个自由文本字段。补上。

## 涉及文件

- `platform/src/govplatform/harness/service.py`（P0-1/P0-2/P0-3）
- `platform/src/govplatform/harness/models.py`（P0-3，`AcceptanceResult.
  round_number`）
- `platform/src/govplatform/mcp_server/server.py`（P0-1，删掉
  `harness.start` 工具）
- `platform/src/govplatform/contract/store.py`（P1-4，`update()` 加
  `expected_version` 参数）
- `platform/src/govplatform/contract/service.py`（P1-4/P1-5/P1-6）
- 测试：`test_harness_lifecycle.py`/`test_harness_repair_and_
  escalation.py`/`test_waivers.py`/`test_contract_lifecycle.py`/
  `test_contract_sensitive_and_audit.py` 都加了对应用例，新增 6 个，
  总数从 59 到 65。

## 没做的（第一轮）

- baseline 文档 §7 本身没改（写不进去，超行数上限），这份文件是补充
  记录，不是替代——下次有空拆分 baseline 文档时应该把 §7 整节挪出来。
- 没有重新审视 `freeze()` 里 `contract_store.update()` 那次调用是否
  也有类似的并发窗口（两个人几乎同时冻结同一份契约）——这轮只修了
  审查具体指出的 `update()` 路径，`freeze()` 是 Human-only 且概率极低，
  按"只修被指出的具体缺口"的一贯原则先不动，需要的话是独立话题。

## 第二轮（同一天，紧接着第一轮修完之后）

第一轮修完、又加了个 `open_questions` 非空禁止冻结的规则（业内调研
GitHub spec-kit "[NEEDS CLARIFICATION]" 机制来的，见对话记录）之后，
收到第二轮交叉审查，1 条 P0 + 2 条 P1，逐条核实全部属实，修完后
70 个测试（新增 4 个）、mypy strict/ruff/pytest 全绿。

**P0：manual_evidence 未解决时会进 REPAIRING，无意义消耗修复轮次。**
第一轮修的是"Agent 不能自己把 manual_evidence 判过"，但没管"判不过之后
去哪"——统一走跟真实失败一样的 REPAIRING 路径，代码没有任何问题也会
被计入修复轮次，3 次之后甚至会被 ESCALATED，纯粹因为没有人去确认。
改法：`HarnessStatus` 加一个 `WAITING_FOR_HUMAN`，`record_acceptance()`
里把"未解决"拆成 `needs_repair_ids`（真的需要重新开发）和
`needs_human_ids`（全是 manual_evidence，代码没问题）——只要
`needs_repair_ids` 非空还是走 REPAIRING/ESCALATED；`needs_repair_ids`
空但 `needs_human_ids` 非空，进 `WAITING_FOR_HUMAN`，不消耗轮次。
`record_acceptance()` 的状态守卫也要跟着放开：从 `WAITING_FOR_HUMAN`
能直接再调用它（人确认或者豁免生效后），不用重新过一遍入门禁。

**P1：豁免的 expires_at 没校验，可能是过去的时间或者没带时区。**
`is_ac_waived()` 拿 `expires_at` 跟 UTC 时间比较，传进来 naive datetime
会直接抛 TypeError，不是清楚的拒绝原因；传过去的时间会造出一个一创建
就永远无效的豁免。`request_waiver()` 加两条校验：必须带时区信息、必须
晚于当前时间，新增 `InvalidWaiverError`。

**P1：单轮验收结果里同一条 AC 出现多次、或者引用不存在的 AC，没有校验。**
`passed_ac_ids` 之前是从 `results` 直接构建集合——同一个 `ac_id` 同一批
里既报 `passed=False` 又报 `passed=True`，只要有一条为真就会被计入"通过"，
悄悄取了对自己有利的结论；引用契约里没有的 `ac_id` 也不会报错，白白
存进审计历史。加了两条前置校验：`results` 里 `ac_id` 不能重复、必须
全部在契约的 AC 集合里，否则直接拒绝整批（`HarnessStateError`），不猜
哪条数的。

**顺带的结构性工作**：改 `harness/service.py` 时同样撞上了 250 行/文件
上限（跟第一轮改 `contract/service.py`一样），把 `record_acceptance()`
拆去了新文件 `harness/acceptance_service.py`，公共小工具挪进
`harness/_shared.py`，`service.py` 变成薄的重新导出层——外部调用方
（`api/routes/`、`mcp_server/`、测试）不用改任何 import。

涉及文件：`harness/models.py`（新状态）、`harness/_shared.py`（新）、
`harness/acceptance_service.py`（新，装 `record_acceptance()`）、
`harness/service.py`（瘦身+重新导出）、`contract/waiver_service.py`
（`InvalidWaiverError` + 两条校验）、`contract/service.py`（重新导出
`InvalidWaiverError`）、`api/routes/contract.py`（新异常的 HTTP 映射）、
测试：`test_harness_lifecycle.py`（改 1 个、加 3 个）、`test_waivers.py`
（改 1 个、加 1 个）。
