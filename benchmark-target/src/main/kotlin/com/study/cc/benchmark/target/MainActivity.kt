package com.study.cc.benchmark.target

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.Surface
import com.study.cc.benchmark.target.probe.BenchMode
import com.study.cc.benchmark.target.probe.DEFAULT_SCALE
import com.study.cc.benchmark.target.probe.EXTRA_MODE
import com.study.cc.benchmark.target.probe.EXTRA_SCALE
import com.study.cc.benchmark.target.ui.BenchmarkScreen
import com.study.cc.core.designsystem.theme.AppTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val mode = BenchMode.from(intent.getStringExtra(EXTRA_MODE))
        val scale = intent.getIntExtra(EXTRA_SCALE, DEFAULT_SCALE)
        setContent {
            AppTheme {
                // 数据准备好、首屏内容出现后才算「完全绘制」，StartupTimingMetric 的 TTFD 以此为准
                // 没有 Surface 时深色主题下文字是白色、窗口底色是浅色，界面会像是空白
                Surface {
                    BenchmarkScreen(mode = mode, scale = scale, onReady = ::reportFullyDrawn)
                }
            }
        }
    }
}
