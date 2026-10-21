# quality-baseline

用 SlopCodeBench（arXiv 2603.24755）的指标给本仓库量代码质量基线。只度量，不参与 CI，不改任何
Android 代码或门禁配置。

## 怎么跑

```bash
# 量当前工作区
python3 tools/quality-baseline/measure.py .

# 量若干历史提交（每个提交用临时 git worktree，跑完自动清理；需要 ANDROID_HOME 或能找到 SDK）
ANDROID_HOME=<sdk 路径> python3 tools/quality-baseline/measure.py --history 53634cc a2f9c09 HEAD

# 单元测试
cd tools/quality-baseline && python3 -m unittest test_measure
```

原理：用 Gradle init script 临时把各模块的 detekt 配置换成 `detekt-metrics.yml`（把
`CyclomaticComplexMethod` / `LongMethod` 阈值压到 1，让每个函数都出现在报告里），再从 detekt 的
XML 报告里汇总。不改 `config/detekt/detekt.yml`，也不改 `build.gradle.kts`。

## 度量范围

`app/ feature/ core/ domain/ data/` 下的 `src/main`；排除测试、`*Preview.kt`、`build/`、
`build-logic/`、`konsistTest/`，以及根 `build.gradle.kts` 里 detekt 已排除的文件
（`ui/theme/`、`MainActivity.kt` 等）。

## 指标

| 指标 | 定义 | 与论文的关系 |
|---|---|---|
| `erosion` | CC > 10 的函数的"复杂度质量"占总质量的比例，单函数质量 = CC × √SLOC | 与论文定义一致 |
| `max_cc` / `functions_cc_gt_10` / `functions` / `total_function_sloc` | 原始量 | 论文称原始量（LOC、最大 CC）预测成本更强 |
| `clone_ratio_approx` | 规范化后重复出现的连续 6 行窗口覆盖的行数 ÷ 代码行数 | **近似，不可与论文数字比**：论文用 137 条 AST-grep 规则 + 结构克隆，规则集未公开 |

## 已知局限

- CC 与 SLOC 由 detekt 计算（`LongMethod` 报的行数作为 SLOC），口径以 detekt 为准。
- 本仓库的 detekt 门禁已把 CC 限制在 12 以内（`config/detekt/detekt.yml`），`erosion` 的上限
  被门禁压住，数值偏低是预期；没有"无门禁"的对照组，不能据此证明门禁有效。
- 克隆指标按行窗口匹配，会把 Compose 里天然相似的布局代码也算进去，也会漏掉改了名字的克隆。
- 样本是单人单项目，只能当"迹象"。
