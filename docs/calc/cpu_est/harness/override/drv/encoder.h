/*
 * encoder.h(ベンチ用の差し替え)
 * MK4 のエンコーダ(MT6835、21 ビット、車軸)。関数の名前は ToraNeko の drv/encoder.h と同じにして、
 * ToraNeko の ctrl/odometry.c がそのまま使えるようにする。
 */
#ifndef DRV_ENCODER_H
#define DRV_ENCODER_H

#include <stdint.h>

#define ENCODER_COUNT_PER_REV 2097152  /* 2 の 21 乗 */

int32_t encoder_get_left_total(void);
int32_t encoder_get_right_total(void);
void encoder_process(void);
void encoder_start_left(void);
void encoder_left_done(void);
float encoder_get_left_motor_omega_rad_s(void);
float encoder_get_right_motor_omega_rad_s(void);
float encoder_get_left_speed_mm_s(void);
float encoder_get_right_speed_mm_s(void);
uint32_t encoder_get_error_count(void);

#endif
