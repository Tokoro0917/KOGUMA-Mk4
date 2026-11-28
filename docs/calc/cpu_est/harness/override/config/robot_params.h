/*
 * robot_params.h(ベンチ用の差し替え)
 * ToraNeko の config/robot_params.h を写し、MK4(タイヤ 24mm の機体)の値と 4kHz の制御周期にしたもの。
 * 1 回の計算の量は周期によらない(定数が変わるだけ)。
 */
#ifndef CONFIG_ROBOT_PARAMS_H
#define CONFIG_ROBOT_PARAMS_H

#define CTRL_FREQ_HZ 4000                    /* MK4 の制御周期 [Hz](docs/control.md の4章) */
#define CTRL_PERIOD_S (1.0f / CTRL_FREQ_HZ)
#define BATTERY_LOW_V 10.5f
#define TIRE_DIAMETER_MM 24.0f               /* t24 の機体 */
#define TREAD_MM 58.1f

#endif
