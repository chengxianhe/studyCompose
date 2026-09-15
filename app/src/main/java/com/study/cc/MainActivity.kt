// 声明本文件属于哪个包；包名决定其他 Kotlin 文件如何引用这里的类和函数。
package com.study.cc

// Android Activity 创建时会传入 Bundle，用来恢复之前保存的界面状态。
import android.os.Bundle
// ComponentActivity 是支持 AndroidX、生命周期和 Compose 的 Activity 基类。
import androidx.activity.ComponentActivity
// setContent 用 Compose 的 UI 内容替代传统 XML 的 setContentView。
import androidx.activity.compose.setContent
// 让 App 内容可以绘制到状态栏、导航栏区域，适合现代沉浸式界面。
import androidx.activity.enableEdgeToEdge
// Arrangement 用于控制 Column 中子项在主轴（垂直方向）的排列方式。
import androidx.compose.foundation.layout.Arrangement
// Column 是从上到下摆放子项的 Compose 布局，类似 XML 的垂直 LinearLayout。
import androidx.compose.foundation.layout.Column
// fillMaxSize 让组件占据父容器可用的最大宽高。
import androidx.compose.foundation.layout.fillMaxSize
// padding 为组件四周留出间距，也用于避开 Scaffold 提供的系统栏区域。
import androidx.compose.foundation.layout.padding
// Button 是 Material 3 的可点击按钮组件，自带触摸反馈和无障碍语义。
import androidx.compose.material3.Button
// BottomAppBar 是 Scaffold 的底部栏插槽常用组件。
import androidx.compose.material3.BottomAppBar
// 此版本的 TopAppBar 仍标记为实验 API；OptIn 表示我们明确接受它的 API 可能变化。
import androidx.compose.material3.ExperimentalMaterial3Api
// FloatingActionButton 是浮在内容右下方、用于最主要动作的圆形按钮。
import androidx.compose.material3.FloatingActionButton
// MaterialTheme 提供统一的颜色、字体和形状规范，避免把视觉样式硬编码在组件中。
import androidx.compose.material3.MaterialTheme
// Scaffold 是 Material 页面骨架，负责协调内容与系统栏、顶部栏等区域。
import androidx.compose.material3.Scaffold
// Text 用来声明一段要显示的文本；状态变化时它会自动显示最新值。
import androidx.compose.material3.Text
// TopAppBar 是 Scaffold 的顶部栏插槽常用组件。
import androidx.compose.material3.TopAppBar
// Composable 标记一个“描述 UI 的函数”，只有它才能调用其他 Compose UI。
import androidx.compose.runtime.Composable
// getValue 让 State 可以用 `by` 语法直接读取，而不必写 `.value`。
import androidx.compose.runtime.getValue
// mutableIntStateOf 创建专用于 Int 的可观察状态，避免通用装箱，适合计数器。
import androidx.compose.runtime.mutableIntStateOf
// remember 缓存重组期间复用的对象；这里用它保持事件回调对象稳定。
import androidx.compose.runtime.remember
// rememberSaveable 保存简单 UI 状态，并支持 Activity 重建后的状态恢复。
import androidx.compose.runtime.saveable.rememberSaveable
// setValue 让 State 可以用 `by` 语法直接赋值，而不必写 `.value = ...`。
import androidx.compose.runtime.setValue
// Alignment 定义交叉轴对齐方式，例如让 Column 的内容水平居中。
import androidx.compose.ui.Alignment
// Modifier 是 Compose 的“属性链”，可追加尺寸、间距、点击等 UI 行为。
import androidx.compose.ui.Modifier
// Preview 让 Android Studio 无需运行 App 就能在编辑器中预览 Composable。
import androidx.compose.ui.tooling.preview.Preview
// dp 是与屏幕密度无关的尺寸单位，保证不同设备上的视觉间距更一致。
import androidx.compose.ui.unit.dp
// 导入创建项目时生成的主题，统一整个 App 的 Material 配色和字体。
import com.study.cc.ui.theme.StudyComposeTheme

// MainActivity 是应用启动后展示本页面的 Android 入口。
class MainActivity : ComponentActivity() {
    // onCreate 是 Activity 首次创建时的生命周期回调，相当于页面初始化入口。
    override fun onCreate(savedInstanceState: Bundle?) {
        // 先让父类完成必要的 Android 生命周期初始化；这是覆写回调时的固定写法。
        super.onCreate(savedInstanceState)
        // 启用边到边显示；后续 Scaffold 会把安全区域的内边距提供给内容。
        enableEdgeToEdge()

        // 从这里开始声明 Activity 要显示的 Compose UI，而不是加载 XML 布局文件。
        setContent {
            // 把整页放进项目主题中，子组件可通过 MaterialTheme 读取统一样式。
            StudyComposeTheme {
                // CounterPage 持有页面状态；它再把状态和事件交给纯展示用的 CounterScreen。
                CounterPage()
            }
        }
    }
}

// CounterPage 是“有状态”的上层：它拥有 count，并定义状态可以怎样变化。
@Composable
fun CounterPage() {
    // 页面状态仍保存在 Composition 中；后续学习 ViewModel 时会把它移到页面外。
    var count by rememberSaveable { mutableIntStateOf(0) }
    // 记住事件 Lambda，避免每次重组都创建新的回调对象。
    val onIncrement: () -> Unit = remember { { count += 1 } }
    // 重置回调同样稳定，并且只允许这里修改 count。
    val onReset = remember { { count = 0 } }

    // 状态向下传递，用户事件向上传递；这就是单向数据流。
    CounterScreen(
        count = count,
        onIncrement = onIncrement,
        onReset = onReset,
    )
}

// TopAppBar 在当前依赖版本属于实验 API；这行表明我们有意识地使用它。
@OptIn(ExperimentalMaterial3Api::class)
// CounterScreen 是“无状态”的展示组件：它只接收数据和事件，不保存或直接修改 count。
@Composable
fun CounterScreen(
    // 由调用方提供当前数据；因此该组件可显示 0、10 或任何其他数字。
    count: Int,
    // 点击“加一”时只发出事件请求，具体怎样修改状态由调用方决定。
    onIncrement: () -> Unit,
    // 点击“重置”时同理；这使展示组件不依赖具体状态存储方式。
    onReset: () -> Unit,
    // modifier 仍让调用方决定该组件的位置和尺寸。
    modifier: Modifier = Modifier,
) {

    // Scaffold 把“页面公共框架”从中间的业务内容中分离出来。
    Scaffold(
        // Scaffold 自己占满页面；modifier 仍保留，方便别的页面或预览进一步定制它。
        modifier = modifier.fillMaxSize(),
        // topBar 是一个插槽（slot）：Scaffold 不关心具体顶部 UI，只负责把它放在顶部。
        topBar = {
            // 这里把 Material 3 的 TopAppBar 填进 topBar 插槽。
            TopAppBar(title = { Text("Scaffold 计数器") })
        },
        // bottomBar 是第二个插槽，适合放底部导航、状态信息或操作栏。
        bottomBar = {
            // 这里用 BottomAppBar 显示当前状态，证明它和中间内容读取的是同一个 count。
            BottomAppBar {
                Text(
                    // count 改变时，底部文字也会自动重组为最新数量。
                    text = "底部状态：当前数量为 $count",
                    // 加水平内边距，使文字不会紧贴底部栏边缘。
                    modifier = Modifier.padding(horizontal = 16.dp),
                )
            }
        },
        // floatingActionButton 是第三个插槽，Scaffold 会把它定位在内容右下方。
        floatingActionButton = {
            // 把最常用的“加一”事件交给调用方处理；CounterScreen 不直接写状态。
            FloatingActionButton(onClick = onIncrement) {
                Text("＋")
            }
        },
    ) { innerPadding ->
        // 这是 Scaffold 的“主体内容”插槽；innerPadding 是它为顶部、底部栏预留的安全空间。
        Column(
            // 先应用 innerPadding 防止内容和栏重叠，再添加页面自己的水平间距。
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(horizontal = 24.dp),
            // 让 Column 中的子项在水平方向居中。
            horizontalAlignment = Alignment.CenterHorizontally,
            // 子项之间间隔 16dp，并把整组内容在主体区域的垂直方向居中。
            verticalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterVertically),
        ) {
            // 文本读取 count；每当 count 更新，Compose 会仅重新计算需要这份状态的 UI。
            Text(
                // Kotlin 字符串模板把当前 count 插入显示内容，无需手动刷新 TextView。
                text = "当前数量：$count",
                // 使用主题中的大标题排版，便于全局统一字号并支持主题调整。
                style = MaterialTheme.typography.headlineMedium,
            )

            // 普通按钮也发出相同的加一事件；它和 FAB 只是放置位置不同。
            Button(onClick = onIncrement) {
                Text("中间的加一按钮")
            }

            // 第二个按钮负责把状态恢复为初始值。
            Button(
                // 点击时请求调用方重置状态；调用方传回新 count 后 UI 会自动更新。
                onClick = onReset,
                // count 为 0 时禁用按钮，避免用户执行没有意义的重置操作。
                enabled = count > 0,
            ) {
                // 用文字描述按钮的动作，Material 组件会自动处理禁用态的视觉效果。
                Text("重置")
            }
        }
    }
}

// 标记下面函数为 Android Studio 预览入口；showBackground 让预览有背景便于观察。
@Preview(showBackground = true)
// 预览函数同样必须是 Composable，才能调用 CounterScreen。
@Composable
fun CounterScreenPreview() {
    // 预览也包在同一主题中，使预览和真机上的样式保持一致。
    StudyComposeTheme {
        // 预览直接传入假数据与空事件，不需要真实状态容器或 Activity。
        CounterScreen(
            count = 2,
            onIncrement = {},
            onReset = {},
        )
    }
}
