# 第一课：Compose 页面、状态与刷新链路

对应示例代码：`app/src/main/java/com/example/studycompose/MainActivity.kt`。

## 1. 声明式 UI

Compose 的核心模型是：

```text
UI = f(State)
```

不是手动找到控件并修改它，而是根据当前状态重新描述界面应该是什么样子。

```kotlin
Text("当前数量：$count")
```

当 `count` 变化时，这段 UI 会在重组后显示新值。

## 2. 从 Activity 进入 Compose

```kotlin
setContent {
    StudyComposeTheme {
        CounterScreen()
    }
}
```

- `setContent` 用 Compose UI 替代传统 XML 的 `setContentView`。
- `StudyComposeTheme` 提供统一的 Material 3 颜色、字体和形状。
- `CounterScreen` 是本页可复用的 Composable。

`@Composable`、`Scaffold`、`Column`、`Text`、`Button` 都不是 Kotlin 关键字；它们是 Compose 的函数或注解。Kotlin 关键字包括 `class`、`fun`、`var`、`override` 等。

## 3. 边到边显示与 Scaffold

```kotlin
enableEdgeToEdge()
```

这行让页面背景可以延伸到状态栏和导航栏区域。它通常应在 `setContent` 前调用。

`Scaffold` 是 Material 3 提供的页面骨架。它将公共布局和具体页面内容分离：

```text
Scaffold
├─ topBar：顶部栏
├─ content：中间主体
├─ bottomBar：底部栏
└─ floatingActionButton：右下角主要操作
```

```kotlin
Scaffold(
    topBar = { TopAppBar(title = { Text("标题") }) },
    bottomBar = { BottomAppBar { /* 底部内容 */ } },
    floatingActionButton = { FloatingActionButton(onClick = {}) { Text("＋") } },
) { innerPadding ->
    Column(Modifier.padding(innerPadding)) {
        // 页面主体
    }
}
```

`Scaffold` 不知道业务状态是什么，只负责测量和安置各个插槽。`innerPadding` 是它计算出的安全间距；页面必须主动应用它，避免主体被顶部栏、底部栏或系统栏遮住。

Flutter 的对应结构是：

```dart
Scaffold(
  appBar: ...,
  body: ...,
  bottomNavigationBar: ...,
  floatingActionButton: ...,
)
```

## 4. Modifier 与 padding

```kotlin
Modifier
    .fillMaxSize()
    .padding(innerPadding)
    .padding(horizontal = 24.dp)
```

`Modifier` 是不可变的规则链；每次调用都会返回一条包含旧规则和新规则的新链，而不是修改旧对象。

这两个 `padding` 职责不同：

```text
padding(innerPadding)       → Scaffold 给出的安全留白
padding(horizontal = 24.dp) → 页面设计的左右视觉留白
```

对于 `padding`，对应方向通常会叠加。例如两个四周 `8.dp` 的 padding，效果约为四周 `16.dp`。

但并非所有 Modifier 都会“相加”：

| Modifier 类型 | 多次调用的大致结果 |
| --- | --- |
| `padding` | 布局留白叠加 |
| `background`、`clickable` | 都会加入链，顺序影响范围或行为 |
| `size` | 属于约束，不会简单相加 |

## 5. 可观察状态

```kotlin
var count by rememberSaveable { mutableIntStateOf(0) }
```

- `mutableIntStateOf(0)`：一个可观察的 `Int` 状态容器。
- `rememberSaveable`：在重组和常见配置变更（如旋转）后恢复简单状态。
- `by`：Kotlin 属性委托，可直接写 `count++`，不必写 `count.value++`。

普通局部变量不行：

```kotlin
var count = 0
```

它既不会通知 Compose，也会在 `CounterScreen` 重组时重新初始化。

## 6. 点击后 UI 如何更新

```text
用户点击 Button
  ↓
onClick { count++ }
  ↓
Snapshot State 的 setter 写入新值
  ↓
Runtime 找到读取过 count 的重组区域
  ↓
Recomposer 标记这些区域需要更新
  ↓
下一次显示帧到来时执行重组
  ↓
Composition → Layout → Drawing
  ↓
屏幕显示新数字
```

例如下列三个位置都读取了 `count`：

```kotlin
Text("当前数量：$count")
Text("底部状态：当前数量为 $count")
enabled = count > 0
```

因此 `count` 从 0 变成 1 后，它们都会获得新值；没有读取 `count` 的 UI 则有机会被跳过。

## 7. Compose Runtime、Snapshot 与 Recomposer

```text
Compose Runtime
├─ Composition：记录 UI 描述与调用位置
├─ remember：保存重组期间需要复用的对象
├─ Snapshot State：记录状态读取与状态写入
└─ Recomposer：把“状态失效”安排到合适的一帧执行
```

首次执行 `Text("$count")` 时，Runtime 会记录“此重组区域读取了 `count`”。

`count++` 并不会直接同步调用 `CounterScreen()`。状态变更先进入 Snapshot 系统；Runtime 据此标记依赖区域失效，Recomposer 再登记一次未来帧任务。多次快速更新会合并：下一帧通常直接读取最新状态。

## 8. VSYNC、Choreographer 与绘制

```text
显示硬件 / 系统：按当前刷新率产生 VSYNC 节拍
Choreographer：接收节拍，并在下一帧安排 App 的工作
Recomposer：有待处理重组时，请求在下一帧执行
Compose UI：组合、测量、放置、绘制
GPU / SurfaceFlinger：提交并合成最终画面
```

Recomposer 不制造 VSYNC，也不是依靠固定定时器轮询状态。它只是登记“下一帧我有工作”。没有变化时，显示器仍持续刷新，但 App 可以继续显示上一帧的内容，不生成新的 UI 帧。

Compose 的三阶段：

```text
Composition：有什么 UI
Layout：每个节点多大、放在哪里
Drawing：把背景、文字、图形绘制到 Canvas
```

## 9. 与传统 View 的对比

```text
传统 View：
数据变化 → 手动修改 TextView / Button → invalidate 或 requestLayout → 下一帧绘制

Compose：
State 变化 → Runtime 自动找到依赖 UI → Recomposer → 下一帧重组、布局、绘制
```

两者最后都走 Android 的帧调度、RenderThread、GPU 和 SurfaceFlinger；差别主要在 UI 层如何追踪状态依赖和生成更新。

## 10. 复习问题

1. `Scaffold` 为什么把 `innerPadding` 交给 content，而不是自动忽略它？
2. 两个 `padding` 为什么不会互相重置？
3. 为什么普通 `var count = 0` 不能驱动 UI 更新？
4. `count++` 是直接绘制屏幕，还是安排下一帧重组？
5. VSYNC、Choreographer、Recomposer 三者分别负责什么？

下一课：状态提升（State Hoisting），把 `count` 从 `CounterScreen` 中移到调用方，让组件更可复用、可测试。
