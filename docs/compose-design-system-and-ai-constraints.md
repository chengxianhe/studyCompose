# 设计系统规范与 AI 约束方案

> 解决的问题：AI 自己发明颜色、间距、字号、组件高度，硬编码文案，
> 导致视觉不一致、无法主题化、无法国际化。
>
> 核心原则：**唯一真相源（single source of truth）+ 编译期/测试期强制**。
> 光写规范没用，必须让违规变成红色失败。

---

## 一、为什么必须做这个

AI 写 `Color(0xFF3366FF)` 的成本是零，查 `MaterialTheme.colorScheme.primary` 需要先知道
有哪些 token、叫什么、语义对不对。它永远会选前者，除非前者写不出来。

这类问题的特点：
- 编译器不报错
- 单元测试测不出来
- code review 时单看一行 `16.dp` 完全正常
- 等你发现时已经散落在几百个文件里

所以只能靠**规则前置拦截**。

---

## 二、Token 三层结构

```
① 基础层 Primitive     原始值，不带语义     Blue500 = Color(0xFF3366FF)
       ↓ 只能被 ② 引用
② 语义层 Semantic      按用途命名           colorScheme.primary / Spacing.lg
       ↓ 业务代码只能用这一层
③ 组件层 Component     组件专属常量         Sizes.topBarHeight
```

**规则：业务代码（feature 模块）只允许引用 ② 和 ③，绝对不能碰 ①。**

基础层只在 `:core:designsystem` 内部使用。这样换主题、做暗色模式、改品牌色时只改一个文件。

---

## 三、具体 token 定义

放在 `:core:designsystem` 下，这是唯一真相源。

### 3.1 颜色

```kotlin
// core/designsystem/theme/Color.kt

// ① 基础层 —— internal，外部无法访问
internal val Blue50  = Color(0xFFE6F1FB)
internal val Blue500 = Color(0xFF3366FF)
internal val Blue900 = Color(0xFF042C53)
internal val Neutral0   = Color(0xFFFFFFFF)
internal val Neutral900 = Color(0xFF1A1A1A)
// ...

// ② 语义层 —— Material3 colorScheme
internal val LightColors = lightColorScheme(
    primary = Blue500,
    onPrimary = Neutral0,
    surface = Neutral0,
    onSurface = Neutral900,
    error = Red500,
    // ...
)
internal val DarkColors = darkColorScheme(/* ... */)
```

**业务代码只能这样用：**
```kotlin
Text(color = MaterialTheme.colorScheme.onSurface)
Surface(color = MaterialTheme.colorScheme.surfaceVariant)
```

**Material3 不够用时**，扩展语义色（不要直接暴露基础色）：
```kotlin
@Immutable
data class ExtendedColors(
    val success: Color,
    val onSuccess: Color,
    val warning: Color,
    val brandGradientStart: Color,
)

val LocalExtendedColors = staticCompositionLocalOf { ExtendedColors(...) }

// 使用：AppTheme.extendedColors.success
```

### 3.2 间距

**只允许 8 的倍数（4 可作为半步）**，杜绝 13dp、19dp 这种值。

```kotlin
// core/designsystem/theme/Spacing.kt
object Spacing {
    val none = 0.dp
    val xxs  = 2.dp
    val xs   = 4.dp
    val sm   = 8.dp
    val md   = 12.dp
    val lg   = 16.dp    // 默认页面内边距
    val xl   = 24.dp
    val xxl  = 32.dp
    val xxxl = 48.dp
}
```

### 3.3 字号

全部走 Typography，禁止内联 `fontSize`。

```kotlin
// core/designsystem/theme/Type.kt
internal val AppTypography = Typography(
    displayLarge   = TextStyle(fontSize = 32.sp, lineHeight = 40.sp, fontWeight = FontWeight.Normal),
    headlineMedium = TextStyle(fontSize = 24.sp, lineHeight = 32.sp, fontWeight = FontWeight.Medium),
    titleLarge     = TextStyle(fontSize = 20.sp, lineHeight = 28.sp, fontWeight = FontWeight.Medium),
    titleMedium    = TextStyle(fontSize = 16.sp, lineHeight = 24.sp, fontWeight = FontWeight.Medium),
    bodyLarge      = TextStyle(fontSize = 16.sp, lineHeight = 24.sp),
    bodyMedium     = TextStyle(fontSize = 14.sp, lineHeight = 20.sp),
    labelMedium    = TextStyle(fontSize = 12.sp, lineHeight = 16.sp),
)
```

**使用：** `Text(style = MaterialTheme.typography.bodyMedium)`

⚠️ 字号用 `sp` 不用 `dp`，否则用户系统字体放大会失效（无障碍要求）。

### 3.4 组件尺寸标准

这是你说的"title 高度、bottom 高度"这类。**集中声明，业务代码引用。**

```kotlin
// core/designsystem/theme/Sizes.kt
object Sizes {
    // 导航
    val topBarHeight        = 64.dp
    val topBarHeightLarge   = 112.dp
    val bottomBarHeight     = 80.dp
    val tabHeight           = 48.dp

    // 触控
    val minTouchTarget      = 48.dp   // 无障碍最小点击区，不可小于此值
    val buttonHeight        = 48.dp
    val buttonHeightSmall   = 36.dp
    val fabSize             = 56.dp

    // 列表
    val listItemSingleLine  = 56.dp
    val listItemTwoLine     = 72.dp
    val listItemThreeLine   = 88.dp

    // 图标与头像
    val iconSm = 16.dp
    val iconMd = 24.dp    // 默认
    val iconLg = 32.dp
    val avatarSm = 32.dp
    val avatarMd = 40.dp
    val avatarLg = 56.dp

    // 分隔线
    val dividerThickness = 1.dp
}

object Radius {
    val none = 0.dp
    val sm   = 4.dp
    val md   = 8.dp
    val lg   = 12.dp    // 卡片默认
    val xl   = 16.dp
    val full = 999.dp   // 胶囊
}

object Elevation {
    val none = 0.dp
    val low  = 1.dp
    val mid  = 3.dp
    val high = 6.dp
}
```

> 上面的数值是基于 Material3 的建议基线。**定稿前对照 M3 官方规范和你的设计稿确认一次**，
> 确认后就写死在这里，之后所有地方引用它，不再各处硬编码。

---

## 四、基础组件清单

`:core:designsystem` 必须先把这些封装好，否则 AI 会每个页面自己搓一个。

| 组件 | 说明 |
|---|---|
| `AppButton` / `AppOutlinedButton` / `AppTextButton` | 统一高度、圆角、loading 态、disabled 态 |
| `AppTopBar` | 标题、返回、右侧 action 插槽 |
| `AppBottomBar` | |
| `AppCard` | 统一圆角、elevation、内边距 |
| `AppTextField` | 统一错误态、计数、清除按钮 |
| `AppDialog` / `AppBottomSheet` | |
| `AppSnackbar` | 配合 UiState 里的 userMessage |
| **`LoadingState`** | 全屏 loading / 局部 loading |
| **`EmptyState`** | 空数据占位（图 + 文案 + 可选按钮） |
| **`ErrorState`** | 错误占位（含重试按钮） |
| `AppAsyncImage` | Coil 封装，统一占位图和失败图 |
| `AppDivider` / `AppChip` / `AppBadge` | |

加粗那三个是最容易被忽略、又最容易被 AI 各写各的。**页面三态（加载/空/错误）必须统一封装**，
否则你会看到十种不同的 loading 样式。

---

## 五、国际化

即使现在只做中文，**也必须从第一天就禁止硬编码字符串**。后期补的成本是十倍。

```kotlin
// ❌ 禁止
Text("提交订单")

// ✅ 必须
Text(stringResource(R.string.order_submit))
```

**strings.xml 命名约定：**
```
<模块>_<场景>_<语义>
order_detail_title
order_submit_button
common_retry
common_loading
error_network_timeout
```

**其他要求：**
- 带参数用占位符，不要字符串拼接：`<string name="cart_count">共 %1$d 件商品</string>`
- 复数用 `plurals`，不要 if-else
- 日期、货币、数字格式化走系统 API，不要手写
- 布局用 `start`/`end` 而不是 `left`/`right`（为 RTL 语言留余地）

---

## 六、AI 的决策树（写进 CLAUDE.md）

这是最核心的部分——**告诉 AI 拿不到值的时候该干什么**。

```
需要一个颜色 / 间距 / 字号 / 尺寸？
│
├─ 1. 先在 :core:designsystem 里找现成 token
│      颜色 → MaterialTheme.colorScheme / AppTheme.extendedColors
│      间距 → Spacing.*
│      字号 → MaterialTheme.typography.*
│      尺寸 → Sizes.* / Radius.* / Elevation.*
│
├─ 2. 找到语义匹配的 → 直接用，结束
│
├─ 3. 找到数值接近但语义不对的
│      → 用语义对的那个，不要因为数值凑巧就借用
│      （比如别把 Spacing.lg 当成 Sizes.iconMd 用，都是 16dp 但含义不同）
│
└─ 4. 确实没有对应 token
       → 【停下来告诉我】，不要自己内联一个值
       → 由我决定：是新增 token，还是改用现有的
```

**新增 token 的流程（需要人确认）：**
1. 在 `:core:designsystem` 对应文件里新增，命名走语义不走数值
   （`Spacing.xxl` 不叫 `Spacing.dp32`）
2. 如果是颜色，同时补暗色模式的值
3. 提交时单独一个 commit，便于 review

---

## 七、强制规则（关键）

上面全是规范，**不强制等于没有**。下面是让违规变红的方法。

### 7.1 Konsist 规则

```kotlin
class DesignSystemTest {

    private val featureScope = Konsist.scopeFromProject()
        .files.filter { it.path.contains("/feature/") }

    @Test
    fun `feature 模块禁止硬编码颜色`() {
        featureScope.forEach { file ->
            assertFalse(
                file.text.contains(Regex("""Color\(0x[0-9A-Fa-f]{8}\)""")),
                "${file.name} 存在硬编码颜色，请使用 MaterialTheme.colorScheme 或新增 token"
            )
        }
    }

    @Test
    fun `feature 模块禁止内联 dp 数值`() {
        // 允许 0.dp 和 1.dp（分隔线），其余必须走 Spacing/Sizes/Radius
        featureScope.forEach { file ->
            val matches = Regex("""(?<![\w.])(\d+)\.dp""").findAll(file.text)
                .map { it.groupValues[1].toInt() }
                .filter { it != 0 && it != 1 }
                .toList()
            assertTrue(matches.isEmpty(), "${file.name} 存在内联 dp: $matches")
        }
    }

    @Test
    fun `禁止内联 sp 字号`() {
        featureScope.forEach { file ->
            assertFalse(
                file.text.contains(Regex("""fontSize\s*=\s*\d+\.sp""")),
                "${file.name} 存在内联 fontSize，请使用 MaterialTheme.typography"
            )
        }
    }

    @Test
    fun `禁止硬编码中文字符串`() {
        featureScope.forEach { file ->
            assertFalse(
                file.text.contains(Regex(""""[^"]*[\u4e00-\u9fa5]+[^"]*"""")),
                "${file.name} 存在硬编码中文，请使用 stringResource"
            )
        }
    }

    @Test
    fun `feature 模块禁止 import 基础色`() {
        featureScope.forEach { file ->
            assertFalse(
                file.imports.any { it.name.contains("designsystem.theme.Blue") },
                "${file.name} 直接引用了基础色，只能用语义层"
            )
        }
    }
}
```

> 注意第一条和第四条会误伤 Preview 代码和测试代码，
> 记得在 scope 里排除 `*Preview.kt` 和 `androidTest/` `test/` 目录。

### 7.2 detekt

```yaml
style:
  MagicNumber:
    active: true
    ignoreNumbers: ['-1', '0', '1', '2']
    ignoreAnnotated: ['Preview', 'Composable']   # 按需调整
  ForbiddenImport:
    active: true
    imports:
      - value: 'androidx.compose.material.*'     # 禁 M2，只用 M3
        reason: '本项目统一使用 Material3'
```

### 7.3 Android Lint

内置规则直接开：
- `HardcodedText` —— XML 里的硬编码文案
- `MissingTranslation` / `ExtraTranslation` —— 多语言时
- `SmallSp` —— 字号过小
- `ContentDescription` —— 无障碍

```kotlin
lint {
    abortOnError = true
    warningsAsErrors = true
    disable += setOf(/* 确实不需要的 */)
}
```

### 7.4 Roborazzi 截图测试（P2）

最后一道防线：视觉回归。AI 改了样式导致 UI 变形，前面的规则都拦不住，
截图 diff 能拦住。团队大了或 UI 稳定后再上。

---

## 八、CLAUDE.md 片段（直接抄）

```markdown
## 设计系统（硬约束）

所有视觉常量的唯一来源是 :core:designsystem，业务代码禁止内联任何视觉数值。

### 禁止
- `Color(0xFF...)` —— 用 MaterialTheme.colorScheme 或 AppTheme.extendedColors
- 内联 dp 数值（0.dp 和 1.dp 除外）—— 用 Spacing / Sizes / Radius / Elevation
- 内联 `fontSize = X.sp` —— 用 MaterialTheme.typography
- 硬编码字符串 —— 用 stringResource(R.string.xxx)
- import androidx.compose.material.* —— 本项目只用 Material3
- 自己写 loading / 空态 / 错误态 —— 用 LoadingState / EmptyState / ErrorState
- 自己搓按钮、卡片、输入框 —— 用 AppButton / AppCard / AppTextField

### 找不到合适 token 时
不要内联一个值，也不要"数值接近就借用"。
停下来告诉我缺什么、用在哪，由我决定新增 token 还是改用现有的。

### 新增 token
命名走语义不走数值（Spacing.xxl，不是 Spacing.dp32）。
颜色必须同时提供暗色模式值。

### 自检
./gradlew :konsistTest:test detekt lint
设计系统相关的断言在 DesignSystemTest 中，失败必须修实现，禁止改断言。
```

---

## 九、落地顺序

1. **先建 token 文件**（Color / Spacing / Type / Sizes / Radius）—— 半小时
2. **再建基础组件**，尤其是三态组件 —— 半天
3. **然后上 Konsist 规则**，故意写违规代码验证会红 —— 一小时
4. **最后写进 CLAUDE.md** —— 十分钟

顺序不能反。先有 token 和组件，规则才有意义——
否则 AI 被拦住之后无处可去，只会反复问你或者想办法绕过。

---

## 十、一个容易踩的坑

规则太严会让 AI 卡死在琐事上。建议给两个口子：

- **Preview 和测试代码豁免**：`@Preview` 里写死值无所谓
- **`:core:designsystem` 模块本身豁免**：它就是定义这些值的地方

Konsist 的 scope 一定要精确限定在 `feature/` 和 `data/`，别全局扫。
