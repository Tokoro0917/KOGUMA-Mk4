/*
 * motor.h
 * 走行モーターの出力(MP6551 × 2、TIM1 の PWM 80kHz)。ToraNeko.Mk3 の App/drv/motor.h から
 *
 * MK4 では、モーターにかける電圧は ctrl/current_ctrl.c が電流の制御で決め、ここは duty を出すだけ。
 * ほかのファイルからモーターを止めるときは current_ctrl_stop()(ctrl/current_ctrl.h)を使う
 * (ここの motor_stop() だけを呼ぶと、次の 20kHz の処理で電流の制御がまた duty を書くため)。
 */
#ifndef DRV_MOTOR_H
#define DRV_MOTOR_H

#include <stdbool.h>

void motor_init(void);
void motor_set_duty(float left_duty, float right_duty);
void motor_stop(void);
void motor_enable(bool on);
bool motor_is_fault(void);

#endif /* DRV_MOTOR_H */
