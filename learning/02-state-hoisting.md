# 第二课：状态提升（State Hoisting）

对应示例代码：`app/src/main/java/com/example/studycompose/MainActivity.kt`。

## 1. 改造前的问题

最初的 `CounterScreen` 同时做三件事：

```text
保存 count
修改 count
显示 count
```

这对于小练习没有问题，但组件不能方便地复用。例如，调用方无法让它显示服务器给出的数字，也很难在单元测试中控制点击后的行为。

## 2. 改造后的职责

```text
CounterPage（有状态）
├─ 保存 count
├─ 定义 onIncrement / onReset 如何修改 count
└─ 把 count 与事件传给 CounterScreen

CounterScreen（无状态）
├─ 显示 count
├─ 点击时调用 onIncrement
└─ 点击时调用 onReset
```

代码关系：

```kotlin
@Composable
fun CounterPage() {
    var count by rememberSaveable { mutableIntStateOf(0) }

    CounterScreen(
        count = count,
        onIncrement = { count += 1 },
        onReset = { count = 0 },
    )
}
```

```kotlin
@Composable
fun CounterScreen(
    count: Int,
    onIncrement: () -> Unit,
    onReset: () -> Unit,
) {
    Text("当前数量：$count")
    Button(onClick = onIncrement) { Text("加一") }
    Button(onClick = onReset) { Text("重置") }
}
```

## 3. 什么是状态提升

状态提升就是把状态从组件内部移到它的调用方。

```text
提升前：CounterScreen 自己拥有 count
提升后：CounterPage 拥有 count，CounterScreen 只接收 count
```

“提升到哪里”为止？提升到所有需要读取或修改该状态的组件的最近共同父级。

## 4. 单向数据流

```text
数据：CounterPage  ── count ──→  CounterScreen
事件：CounterScreen ── onIncrement / onReset ──→ CounterPage
```

事件不会由子组件直接修改父组件的变量。子组件只表达“用户想加一”；拥有状态的上层决定如何处理这个请求，再把新状态向下传回。

```text
点击加一
→ CounterScreen 调用 onIncrement
→ CounterPage 修改 count
→ Compose 重组
→ CounterScreen 收到新的 count
```

## 5. 好处

- 复用：同一个 `CounterScreen` 能显示任意数字。
- 测试：可直接传入 `count = 2` 和假的回调，不依赖 Activity。
- 可替换：状态未来可从 `rememberSaveable` 换成 ViewModel、StateFlow 或网络数据，UI 组件不必重写。
- 可维护：状态修改集中在上层，减少多个子组件同时改同一份数据的风险。

## 6. 与 Flutter 的对应

这是 Flutter 常见的“父组件持有 State，子组件接收参数和 callback”模式：

```dart
CounterView(
  count: count,
  onIncrement: () => setState(() => count++),
)
```

## 7. 复习问题

1. 为什么 `CounterScreen` 不应直接写 `count++`？
2. `onIncrement` 是数据还是事件？
3. 用户点击按钮后，数据和事件分别朝哪个方向流动？
4. 将来把状态换成 ViewModel 时，哪个组件更可能需要改变？
