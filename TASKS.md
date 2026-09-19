## 当前任务
- [ ] T-001 <一句话>
      规格：specs/xxx.md
      验收：<具体到可验证>
      范围：<只允许改哪些目录>
      不做：<明确排除>

## 待办

## 已完成
- [x] T-P0 `platform/` 阶段0/1：受控知识库原型（2026-09-18）
      规格：`docs/ai-engineering-governed-delivery-platform.md`（原方案）+
      `docs/ai-engineering-governed-delivery-platform-baseline.md`（阶段0
      决策与验收状态，含逐项勾选）
      验收：知识写入→人工审核→`knowledge.search` 检索到，带来源/版本/
      权威级别；Claude Code 与 Codex 均以各自 Agent 身份验证可调用；
      mypy strict/ruff/pytest 全绿（完成时19个测试，当前总数见最新一条）
      范围：仅 `platform/` 目录 + 根目录 `.mcp.json`/`.github/workflows/
      platform-ci.yml`，不涉及 Android 侧代码
      不做：交付契约（阶段2）、Harness 三轮修复（阶段3）、cross-encoder
      重排、多空间隔离——均为有意延后，理由见 baseline 文档 §6
- [x] T-P1 `platform/` 深化：BM25 + 本地向量语义检索混合（2026-09-18）
      规格：同上 baseline 文档 §6 "2026-09-18 更新"
      验收：语义相关但无字面关键词重合的查询能命中知识（见
      `tests/test_hybrid_search.py`）；向量模型失败时写入/搜索均能退化
      为 BM25-only 不报错（见 `tests/test_embedding_resilience.py`）
      范围：仅 `platform/` 目录
      不做：向量数据库、持久化索引、自动重嵌入
- [x] T-P2 `platform/` 两轮交叉审查修复 + 时效校验（2026-09-18）
      规格：同上 baseline 文档 §6，同一天的两轮交叉审查记录
      验收：向量模型失败时 propose/search 均不报错（含 search 内部查询词
      编码也要容错，第一版只顾了写入路径）；换模型后的旧向量不参与比较；
      SQLite 迁移只吞"列已存在"这一种错误；`effective_at`/`expire_at`
      支持且顺序无效会被拒绝；`SearchResponse.retrieval_mode` 如实反映
      这次搜索有没有用上向量检索；mypy strict/ruff/pytest 全绿（26 个
      测试，此数字同样只是完成时快照）
      范围：仅 `platform/` 目录
      不做：模型版本号/哈希、旧向量自动重嵌入——阶段0/1单人场景不成立
- [x] T-P3 `platform/` 阶段2：交付契约 AC-*/TC-*（2026-09-18）
      规格：`docs/ai-engineering-governed-delivery-platform.md` §9 +
      baseline 文档 §6 "阶段2 落地"
      验收：契约起草→草稿期可改→冻结（Human-only）→冻结后拒绝再改；
      冻结时校验 AC 非空/AC-TC 引用完整/ac_id-tc_id 不重复/knowledge_refs
      存在，任一不满足拒绝冻结并写审计事件；MCP 三个工具
      （create/update/get）+ HTTP 冻结接口都跑通；mypy strict/ruff/
      pytest 全绿（38 个测试，完成时快照）
      范围：仅 `platform/` 目录
      不做：Harness（阶段3，拿冻结契约驱动开发/三轮修复/准出门禁）、
      契约版本替换流程（SUPERSEDED 状态）、内容质量校验——均为有意延后
- [x] T-P4 `platform/` 阶段2 交叉审查修复：AC 结构拆分/知识快照/get 审计
      （2026-09-18）
      规格：同上 baseline 文档 §6，同一天第二轮交叉审查记录
      验收：AcceptanceCriterion 拆成 precondition/action/input/
      expected_result 四个必填字段（冻结时校验非空）；knowledge_refs 必须
      当前生效（active + 在有效期内）才能冻结，冻结时固化
      knowledge_snapshots（version+content_hash）；contract.get 要求
      caller 并记审计；契约正文复用敏感信息筛查；mypy strict/ruff/pytest
      全绿（42 个测试，完成时快照）
      范围：仅 `platform/` 目录
      不做：契约版本替换、内容质量校验——同上一条理由
