## 当前任务
（当前无进行中的任务；下一条等用户定义）

## 待办
（暂无）

## 已完成
更早的条目已归档（原文未改）：
- Android：T-002 ~ T-006 → `docs/tasks/completed-android.md`
- platform/：T-P0 ~ T-P8 → `docs/tasks/completed-platform.md`

新任务完成后先记在这里；本文件接近 250 行时，再把较早的条目搬进上面的归档文件。

- [x] T-009 补 patterns「表单校验」样板（2026-10-28）
      范围：只做表单校验一行，载体是已有的 `ResolveSecurityIdUseCase`（股票代码输入）；不碰离线优先 / 分页。
      产出：`ValidateStockCodeUseCase`（+单测）、`StockCodeValidationModule`、`AppTextField`、
      新模块 `:feature:stocklookup`（ViewModel/Screen/Preview/strings/单测）、patterns 索引更新。
      未做：`:app` 不 include 该模块、不改 MainActivity（app 无导航，用户决定只接 Preview）。
      局限：`AppTextField` 因 detekt LongParameterList（阈值 6）没有 keyboardOptions 参数，数字键盘未启用。
      验收证据：`./gradlew :konsistTest:test detekt lint test spotlessCheck :app:dependencyGuard` 退出码 0，
      依赖未变。

- [x] T-008 代码质量基线度量（2026-10-21）
      范围：用 SlopCodeBench（arXiv 2603.24755）的指标给仓库量一次基线；只度量，不改 Android 代码，
      不改 CLAUDE.md / Konsist / detekt / lint 配置，不引入依赖。
      产出：`tools/quality-baseline/`（measure.py、detekt-metrics.yml、test_measure.py、README.md）、
      `docs/metrics/baseline-2026-10-21.md`。
      结果：8 个检查点上侵蚀（CC>10 的复杂度质量占比）全为 0，最大 CC 3→10，克隆行占比（近似）6%→2.8%。
      局限：detekt 门禁已把 CC 限制在 12，指标本身没有变大的空间，不能据此证明门禁有效；克隆指标是近似，
      与论文不可比；单人单项目。详见报告。
      验收证据：6 个单元测试通过；`./gradlew :konsistTest:test detekt lint test spotlessCheck
      :app:dependencyGuard` 退出码 0；历史度量用的临时 worktree 已清理。
- [x] T-007 补英文 README（2026-10-21，提交 28f7caa）
      范围：新建 `README.en.md`（与中文版对应，不加中文版没有的说法）；`README.md` 顶部加一句话定位和
      英文版链接。另：`LICENSE` 版权人改为 `chengxianhe`（提交 7ceb529）。不动代码。
