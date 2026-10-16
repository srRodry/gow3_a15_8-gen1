package com.gow3.android.data

import com.gow3.android.R

/**
 * 一个可编辑的启动参数：其 gow3.ini 键、显示标签、分组以及 Android 运行时
 * 实际消费的取值域。`defaultValue` 是键缺失时 UI 显示的值。
 *
 * 显示标签、分组与说明使用字符串资源 id（labelRes / groupRes / descriptionRes），
 * 由 UI 层通过 Context 解析，数据层保持纯 JVM 结构、不依赖 Android。
 */
internal data class LaunchParam(
    val key: String,
    val labelRes: Int,
    val groupRes: Int,
    val options: List<LaunchOption>,
    val defaultValue: String,
    val descriptionRes: Int? = null,
)

internal data class LaunchOption(val value: String, val labelRes: Int)

/**
 * launcher 编辑的启动参数，由 Android 运行时消费的 gow3.ini 键支撑。
 * 默认值与取值域遵循 `SettingsDialog.java` 的常量（UPSCALER_VALUES/FPS_VALUES …）
 * 以及 `gpu/shim/gow3_graphics.h` / `gpu/shim/gow3_settings.cpp` 中的运行时解析器；
 * 当两者不一致时（fps_limit：Java 前端提供 40/45，但 `ParseFpsLimit` 把它们映射为 0）
 * 以运行时取值域为准，确保每个选项都实际生效。
 *
 * SM8475 性能基线默认值为 render_resolution=480p、fps_limit=30、engine_fps=60；
 * display_mode 已从可编辑项移除，固定 fullscreen。这些默认值
 * MUST 与 `tools/android/config/gow3-default.ini`（首启落盘为 gow3.ini 的基准）
 * 保持一致，避免 UI 展示默认与实际运行默认漂移。
 */
internal object LaunchParams {
    val all: List<LaunchParam> = listOf(
        LaunchParam(
            key = "upscaler", labelRes = R.string.param_upscaler, groupRes = R.string.param_group_display,
            options = listOf(
                LaunchOption("off", R.string.param_option_off_720p),
                LaunchOption("fsr3", R.string.param_option_fsr31),
            ),
            defaultValue = "fsr3",
            descriptionRes = R.string.param_desc_upscaler,
        ),
        LaunchParam(
            key = "render_resolution", labelRes = R.string.param_resolution, groupRes = R.string.param_group_display,
            options = listOf(
                LaunchOption("native", R.string.param_option_native),
                LaunchOption("480p", R.string.param_option_480p),
                LaunchOption("720p", R.string.param_option_720p),
                LaunchOption("800p", R.string.param_option_800p),
                LaunchOption("1440p", R.string.param_option_1440p),
                LaunchOption("1800p", R.string.param_option_1800p),
                LaunchOption("4K", R.string.param_option_4k),
            ),
            // SM8475 baseline: 480p game target; FSR 3.1 Performance preset halves it internally.
            // 与 tools/android/config/gow3-default.ini 保持一致。
            defaultValue = "480p",
        ),
        LaunchParam(
            key = "fps_limit", labelRes = R.string.param_fps_limit, groupRes = R.string.param_group_performance,
            options = listOf(
                LaunchOption("30", R.string.param_option_30),
                LaunchOption("60", R.string.param_option_60),
                LaunchOption("120", R.string.param_option_120),
                LaunchOption("240", R.string.param_option_240),
                LaunchOption("0", R.string.param_option_unlimited),
            ),
            // First SM8475 validation targets sustained 30 FPS; raise only after frametime is stable.
            // 与 tools/android/config/gow3-default.ini 保持一致。
            defaultValue = "30",
        ),
        LaunchParam(
            key = "engine_fps", labelRes = R.string.param_engine_fps, groupRes = R.string.param_group_performance,
            options = listOf(
                LaunchOption("60", R.string.param_option_engine_60),
                LaunchOption("120", R.string.param_option_120),
                LaunchOption("240", R.string.param_option_240),
            ),
            // 移动端优化默认值：游戏原生引擎速度，最稳定、最省电。
            // 与 tools/android/config/gow3-default.ini 保持一致。
            defaultValue = "60",
            descriptionRes = R.string.param_desc_engine_fps,
        ),
        LaunchParam(
            key = "vsync", labelRes = R.string.param_vsync, groupRes = R.string.param_group_performance,
            options = listOf(
                LaunchOption("0", R.string.param_option_off),
                LaunchOption("1", R.string.param_option_on),
            ),
            defaultValue = "0",
            descriptionRes = R.string.param_desc_vsync,
        ),
        LaunchParam(
            key = "frames_queued", labelRes = R.string.param_frames_queued, groupRes = R.string.param_group_performance,
            options = listOf(
                LaunchOption("1", R.string.param_option_frames_1),
                LaunchOption("2", R.string.param_option_frames_2),
                LaunchOption("0", R.string.param_option_unlimited),
            ),
            defaultValue = "1",
            descriptionRes = R.string.param_desc_frames_queued,
        ),
        LaunchParam(
            key = "skip_network_choice", labelRes = R.string.param_offline_start, groupRes = R.string.param_group_startup,
            options = listOf(
                LaunchOption("0", R.string.param_option_off),
                LaunchOption("1", R.string.param_option_on),
            ),
            defaultValue = "1",
        ),
        LaunchParam(
            key = "skip_intro", labelRes = R.string.param_skip_intros, groupRes = R.string.param_group_startup,
            options = listOf(
                LaunchOption("0", R.string.param_option_off),
                LaunchOption("1", R.string.param_option_on),
            ),
            defaultValue = "1",
        ),
        LaunchParam(
            key = "debug_camera", labelRes = R.string.param_free_camera, groupRes = R.string.param_group_startup,
            options = listOf(
                LaunchOption("0", R.string.param_option_off),
                LaunchOption("1", R.string.param_option_on),
            ),
            defaultValue = "0",
            descriptionRes = R.string.param_desc_free_camera,
        ),
    )

    /** 参数的当前原始值；缺失或为空时返回其默认值。 */
    fun valueOf(ini: Map<String, String>, param: LaunchParam): String {
        val v = ini[param.key]?.trim()
        return if (v.isNullOrEmpty()) param.defaultValue else v
    }

    /** 当前值对应的选项；未知值返回 null（由 UI 层回退到原始值）。 */
    fun selectedOption(ini: Map<String, String>, param: LaunchParam): LaunchOption? {
        val v = valueOf(ini, param)
        return param.options.firstOrNull { it.value == v }
    }
}
