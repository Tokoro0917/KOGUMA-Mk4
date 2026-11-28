/*
 * current.h
 * モーターの電流(INA241A3 × 2)・CMS(MP6551 の電流の出力 × 2)・電池の電圧の読み取り(ADC2)。MK4 で足したもの
 */
#ifndef DRV_CURRENT_H
#define DRV_CURRENT_H

#include <stdbool.h>
#include <stdint.h>

void current_init(void);
void current_read_adc(void);
void current_start_zero_measure(void);
bool current_is_zero_ready(void);

/* 左右のモーターの電流 [mA](機体が前に進む向きに回す電流が +。その回の ADC の値) */
float current_get_left_mA(void);
float current_get_right_mA(void);

/* 左右の MP6551 の CMS(下の FET の電流の和 ≒ 電池から出る電流の目安)[mA] */
float current_get_left_cms_mA(void);
float current_get_right_cms_mA(void);

/* 電池の電圧 [V](ゆれを減らしたもの)。ToraNeko の wall_get_battery_v() の代わり */
float current_get_battery_v(void);

/* ADC の生の値(0〜4095。動作確認用) */
uint16_t current_get_left_raw(void);
uint16_t current_get_right_raw(void);

#endif /* DRV_CURRENT_H */
