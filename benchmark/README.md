# 相册性能基线（T-011）

用合成数据验证「Room 只存轻量元数据 + SQL 聚合」在 100 万张下的表现。
被测应用是 `:benchmark-target`（独立 applicationId，不影响 `:app`），度量代码在本模块。

## 它测什么

| 测试 | 度量 | 指标 |
|---|---|---|
| `ColdStartBenchmark` | 冷启动到首屏内容 | `timeToFullDisplayMs` |
| `ScrollBenchmark` | 占位网格连续 fling | `frameDurationCpuMs`、`frameOverrunMs` |
| `MemoryBenchmark` | 网格滚动 vs 全量读入 `LongArray` 的内存峰值 | `memoryRssAnonMaxKb` 等 |
| `QueryTimingBenchmark` | 年 / 月 / 日汇总、日桶、某天 id、历史上的今天、strftime 对照、增量 upsert、LongArray 反例 | 各 trace 段耗时 |
| `SeedBenchmark` | 先删库再全量灌入 | `bench.seed` 耗时 |

规模默认 10 万 / 50 万 / 100 万三档。库文件按规模缓存在被测应用里，`SeedBenchmark` 之外不会重复生成。

## 怎么跑

需要一台连着 adb 的真机（模拟器的数字没有意义）。**会在设备上安装两个 APK，并写入数十到百 MB 数据库。**

```
# 全部规模
./gradlew :benchmark:connectedBenchmarkAndroidTest

# 只跑部分规模
./gradlew :benchmark:connectedBenchmarkAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.scales=100000,1000000

# 只跑某一个类
./gradlew :benchmark:connectedBenchmarkAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.class=com.study.cc.benchmark.QueryTimingBenchmark
```

结果 JSON 在 `benchmark/build/outputs/connected_android_test_additional_output/` 下。
标准自检命令（`./gradlew :konsistTest:test detekt lint test spotlessCheck :app:dependencyGuard`）不包含这些设备测试。

## 约定

- 常量与 `:benchmark-target` 的 `BenchMode` / `strings.xml` 对应（见 `BenchmarkTarget.kt`），改动时两边同步。
- 占位网格不加载缩略图：只度量「数据路径 + 布局」。解码开销留给 T-014 用真实图片测。
- 原型 schema 与 T-012 的真实 schema 不共享代码；T-012 完成后须用真实 schema 重跑。
- 基线数字只代表所用设备，换设备要重测。
