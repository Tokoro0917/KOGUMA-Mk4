/*
 * current_ctrl.h
 * 電流の制御(20kHz)。MK4 で足したもの(docs/control.md の 4 章)
 *
 * 速度・角度の制御(ctrl/control.c、4kHz)が「左右の電流の目標」を決め、ここが 20kHz で duty に直す。
 * 決めた電圧をそのままかける(電圧で回す)こともできる(エンコーダの校正・モーターの同定に使う)。
 */
#ifndef CTRL_CURRENT_CTRL_H
#define CTRL_CURRENT_CTRL_H

#include <stdbool.h>
#include <stdint.h>

/* 今の動かし方 */
typedef enum {
  CURRENT_CTRL_OFF = 0,  /* 止めている(duty 0、MP6551 はスリープ) */
  CURRENT_CTRL_CURRENT,  /* 電流の目標に合わせる */
  CURRENT_CTRL_VOLTAGE,  /* 決めた電圧をかける */
} current_ctrl_mode_t;

void current_ctrl_update(void);

void current_ctrl_set_target_mA(float left_mA, float right_mA);
void current_ctrl_set_voltage(float left_v, float right_v);
void current_ctrl_stop(void);
void current_ctrl_set_limit_mA(float limit_mA);

current_ctrl_mode_t current_ctrl_get_mode(void);
bool current_ctrl_is_tripped(void);

/* ログ用: 最後の目標の電流 [mA]、最後に出した duty(−1〜1) */
float current_ctrl_get_left_target_mA(void);
float current_ctrl_get_right_target_mA(void);
float current_ctrl_get_left_duty(void);
float current_ctrl_get_right_duty(void);

/* 左右のタイヤの速さ [mm/s](4kHz の処理が ctrl/odometry.c の値を入れる。逆起電力の分を足すのに使う) */
void current_ctrl_set_wheel_speed(float left_mm_s, float right_mm_s);

#endif /* CTRL_CURRENT_CTRL_H */
