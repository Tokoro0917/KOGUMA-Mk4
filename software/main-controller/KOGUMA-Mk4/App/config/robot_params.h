/*
 * robot_params.h
 * 機体の定数(制御周期、タイヤ径、ギア比、トレッド幅、モーターの定数など)
 * ToraNeko.Mk3 の App/config/robot_params.h から。値は KOGUMA MK4 のタイヤ 24mm の機体(t24)のもの(2026-11-28)
 *
 * 数値の出どころ: docs/control.md(モデル)、docs/spec.md(機体・モーター)。
 * 「実機で合わせる」と書いた値は、まだ計算の値。
 * (main のブランチの機体はタイヤ 15mm・ギア比 3.15 だが、作るのは t24 なので、ここは t24 にした)
 */
#ifndef CONFIG_ROBOT_PARAMS_H
#define CONFIG_ROBOT_PARAMS_H

/* 制御周期 [Hz](docs/software.md の 4 章)。速度・角度の制御とログの記録は 1 秒にこの回数呼ばれる。
 * 壁センサの 1 巡(20kHz の処理の 5 回)と同じ */
#define CTRL_FREQ_HZ 4000
/* 制御周期 [s](1 ÷ 4000 = 0.00025 秒 = 0.25ms) */
#define CTRL_PERIOD_S (1.0f / CTRL_FREQ_HZ)

/* 電流の制御の周期 [Hz](TIM1 の PWM 4 周期ごと。ADC2 の変換が終わるたび) */
#define CURRENT_CTRL_FREQ_HZ 20000
#define CURRENT_CTRL_PERIOD_S (1.0f / CURRENT_CTRL_FREQ_HZ)

/* 電池の下限の電圧 [V]。電源を入れたときにこれより低ければ、何もせずに知らせる(MODES.md)。
 * 3 セルのリポで、1 セル 3.7V(仮。ToraNeko は 2 セルで 1 セル 3.75V) */
#define BATTERY_LOW_V 11.1f

/* タイヤの直径 [mm]。長い直進(モード6 No.6)で、ものさしの距離に合わせて直す(ToraNeko の robot_params.h の
 * 「新しい直径 = 今の直径 × ものさしの距離 ÷ encoder の距離」) */
#define TIRE_DIAMETER_MM 24.0f

/* トレッド幅 [mm](左右のタイヤのまん中どうしの間隔。docs/control.md の先頭、t24) */
#define TREAD_MM 58.1f

/* 機体の重さ [g](電池を含む。docs/control.md の先頭、t24) */
#define ROBOT_MASS_G 60.1f

/* 有効質量 [g](機体 60.1g + ロータと車輪の回る慣性を質量に直した 10.1g。docs/control.md の先頭) */
#define EFFECTIVE_MASS_G 70.2f

/* 慣性モーメント [g・cm²](機体。ロータの分は入れていない。docs/control.md の先頭、t24) */
#define INERTIA_G_CM2 293.0f

/* ギア比(71T ÷ 13T。モーター 5.46 回転でタイヤ 1 回転) */
#define GEAR_RATIO 5.46f

/* モーター(NFP-D8620)の定数(docs/control.md の 3 章。実機で測って直す: モード4) */
#define MOTOR_KT_NM_PER_A 0.00147f        /* トルク定数 [N・m/A] */
#define MOTOR_KE_V_PER_RAD_S 0.00151f     /* 逆起電力の定数 [V/(rad/s)](モーターの軸の角速度で) */
#define MOTOR_RESISTANCE_OHM 1.03f        /* 巻線 1Ω + ドライバ 0.03Ω */

/* モーターの向き: + の duty で機体が前に進む向きに回るなら 1、後ろなら -1(仮。実機で確かめる)。
 * 左右のモーターは向かい合わせなので、ふつうは片方が -1 になる。電流(drv/current.c)にも同じ向きを使う */
#define MOTOR_LEFT_SIGN  1
#define MOTOR_RIGHT_SIGN -1

/* 電流の上限 [mA](docs/control.md の 4 章)。ふだんは 3A、ターンの入りなどで 5A(MP6551 の上限)まで上げられる */
#define CURRENT_LIMIT_MA 3000.0f
#define CURRENT_LIMIT_MAX_MA 5000.0f
/* これを超えた電流が CURRENT_TRIP_TICKS 回(20kHz の処理。20 回 = 1ms)続いたら、すぐ止める(docs/software.md の 7 章) */
#define CURRENT_TRIP_MA 6000.0f
#define CURRENT_TRIP_TICKS 20

#endif /* CONFIG_ROBOT_PARAMS_H */
