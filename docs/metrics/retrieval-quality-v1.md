# 本地检索质量基线 v1

2026-11-11；公开合成资料，标注状态 **draft，待人工审查**。本报告是一次小样本测量，不是质量验收通过或普遍能力提升的证明。

本次 11 篇合成资料、16 个查询，比较 SQLite 现有混合检索与 ES 混合召回＋本地重排。13 例可回答、3 例无答案；旧项目仍适用的知识保留，过期和废弃资料排除。

## 主要结果

ES 链路在这组样本中把相关资料排得更靠前，但误拒答了一例英文查询；不能概括为全面优于 SQLite。没有调整阈值、删除失败案例或修改相关标签。

| 指标 | SQLite 混合检索 | ES＋本地重排 |
|---|---:|---:|
| 可回答样本评分覆盖 | 13/13 | 13/13 |
| 平均 Recall@5 | 1.0000 | 0.9231 |
| 平均 MRR@10 | 0.9038 | 0.9231 |
| 无答案样本的检索闸门代理指标（固定原问） | 未提供闸门，0/3 评分 | 3/3 返回 insufficient，0 次放行 |
| 后端失败/降级 | 0 | 0 |
| 过期/废弃资料泄漏 | 0 | 0 |
| 单例平均查询耗时 | 3.66 ms | 561.46 ms |
| 合成资料/索引准备耗时 | 206.21 ms | 1257.77 ms |
| 一次未计分预热 | 2.92 ms | 2058.65 ms |

SQLite 没有相关性闸门，仍会返回候选片段；unavailable 不等于正确拒答。ES 执行了额外的远程本机查询和重排，两者功能不同；耗时只代表本机这一次运行，没有控制机器并发负载，不是严格性能比较。

这里的“无答案”标注表示资料不能提供问题要求的答案，不等于没有同主题文档。
`relevant` 是可提供所需答案的资料标签；`relevance_grade` 则是检索相关性闸门。
JSON 中的 `no_answer_correct` 记录该闸门在固定原问上的代理结果，未独立检查证据覆盖或最终回答，
不能解释为生成答案正确率，也不能用 pass 推断已经足以回答。

## 分组结果

| 分组 | 数量 | SQLite Recall@5 / MRR@10 | ES Recall@5 / MRR@10 |
|---|---:|---:|---:|
| 中文可回答 | 6 | 1.0000 / 1.0000 | 1.0000 / 1.0000 |
| 英文可回答 | 4 | 1.0000 / 0.6875 | 0.7500 / 0.7500 |
| 知识更新 | 3 | 1.0000 / 1.0000 | 1.0000 / 1.0000 |

## 逐例结果

资料 ID 与完整正文见[案例集](../../platform/evals/retrieval-v1.json)，本表中的第一名为父知识 ID；排名先去重。

| 案例 | 查询 | 标注相关资料 | SQLite 第一名 | ES 第一名／终态 |
|---|---|---|---|---|
| q01 | 新项目 v2 应调用哪个接口？ | api-current | api-current | api-current |
| q02 | 付款前要谁批准，能口头同意吗？ | payment-current | payment-current | payment-current |
| q03 | 断网前后怎样检查知识检索模型是否完整？ | offline-models | offline-models | offline-models |
| q04 | 短语怎么匹配一段很长的中文，BM25 应该怎样分词？ | chinese-tokens | chinese-tokens | chinese-tokens |
| q05 | 申请费用报销要附上什么凭证？ | expenses | expenses | expenses |
| q06 | 恢复数据时如何避免覆盖正在使用的数据库？ | backup | backup | backup |
| q07 | How many days after payment may employees submit reimbursement receipts? | expenses-en, expenses | expenses-en | expenses-en |
| q08 | How should local retrieval models be checked without an internet connection? | offline-models | expenses-en | insufficient |
| q09 | How do I restore a database safely without overwriting the live file? | backup | expenses-en | backup |
| q10 | Which API should a new version 2 project call? | api-current | api-current | api-current |
| q11 | 还没升级的 v1 旧项目应该继续调用哪个 API？ | api-legacy | api-legacy | api-legacy |
| q12 | 现在差旅每天餐饮补助额度是多少？ | travel-current | travel-current | travel-current |
| q13 | 旧口头付款批准流程被撤销后，现在需要怎样审批？ | payment-current | payment-current | payment-current |
| q14 | 如何烘焙巧克力蛋糕，需要多少面粉？ | 无答案 | expenses | insufficient |
| q15 | 提交报销申请的网站具体 URL 是什么？ | 无答案 | expenses | insufficient |
| q16 | API v3 每秒的具体限流数字是多少？ | 无答案 | api-current | insufficient |

## 已发现的缺口与下一步

- q08 的英文问题对应中文 offline-models 资料，ES 返回 insufficient，属于可回答问题的误拒答。当前报告没有保存召回、重排各阶段的全部分数，不能直接归因于某一个模型或阈值。下一轮应先观测候选与分数，再做独立对照，不能直接降低阈值。
- 英文样本只有 4 例，不能据此证明跨语言检索达标。旧版与新版的例子主要验证过滤和排序，不证明自动判断知识过期、冲突裁决或来源监测。
- 三个无答案案例在固定原问上均被闸门拦截，证据仍然很有限；部分资料直接说明缺少某些信息，后续需补充更多自然且含歧义的人工案例。
- 公开样本可用于冒烟回归；如果后续用于调优，则不能再称作未见保留集。没有统计显著性结论；UUID 与并列排序、机器负载可能带来运行差异。

## 可复现性与人工审查

执行命令见[平台说明](../../platform/README.md#小型检索质量基线t-029)。原始结构化报告见[JSON](retrieval-quality-v1.json)。

- 数据 SHA-256：`0eb9a4b7593a165a3a1cf36896a24145c91dd9ebde8604c29ecff2692a0e98f3`。
- 评测/检索相关代码与依赖指纹：`5213a523e7cf1f9bb4f11c84c83b6b94851aef9df5d8e48a0eee35c875207054`。
- embedding：`BAAI/bge-small-zh-v1.5`，修订 `46fbe35fd4374a00fee7de77dfddaeb6dd6a2c59`。
- reranker：`BAAI/bge-reranker-base`，修订 `2cfc18c9415c912f9d8155881c133215df768a70`。
- 查询 limit=10、attempt=2，模型离线使用；没有执行自动查询改写，没有调用生成 LLM。模型 token 费用不适用，宿主会话 token 没有采集，不能记成零。
- 合成人工批准只在新建临时数据库中完成；独立评测索引已清理，生产知识与批准状态未改变。

人工审查请核对：标注是否与合成资料一致；q08 的失败是否被清晰保留；无答案“未评分”是否与成功拒答区分；本轮交付范围是否仅是可复现基线。代码测试通过不代替这些判断。

## 后续诊断补充

原始固定查询结果与 JSON 保持不变。阶段诊断确认 q08 的目标资料已被召回且重排第一，
但得分低于现有相关性阈值；一种中文同义问法也被拦截，不能只归因于语言。

随后预设改写计划、保持模型和阈值不变，对全部 16 例执行最多两次改写：
q08 一次改写后找回目标资料，得分约 0.651；q15 一次改写后也通过相关性闸门，
得分约 0.815，但资料未包含所需报销网址。q14、q16 最终仍返回不足。
这组观察说明相关性得分不能单独承担答案充分性判断；没有执行最终答案生成，
不能据此声称生成模型已经编造网址。

诊断是对已知公开样本的会话预设对照，非盲测，也非平台自主改写验收。
下一步应保留原问约束、逐项核对原文证据，并分别评测相关性与答案充分性。
本机完整计划、原始结果与解释见
[改写对照记录](../../.verification/t029-runtime-quality-20261111/q08-rewrite-comparison.md)。
