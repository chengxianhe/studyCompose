plugins {
    alias(libs.plugins.kotlin.jvm)
}

dependencies {
    testImplementation(libs.junit)
    testImplementation(libs.konsist)
}

// Konsist 在运行时扫描整个项目的源码文件，而不仅仅是本模块声明的输入，
// Gradle 的增量构建无法感知这一点，必须禁用 up-to-date 缓存，否则其他模块改了代码这里会被误判成"没变化"而跳过。
tasks.test {
    outputs.upToDateWhen { false }
}
