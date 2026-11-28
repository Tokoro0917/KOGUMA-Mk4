/*
 * fan.h
 * 吸引ファン(中身は fan.c)。かける電圧 [V] で決める(電池の電圧が変わっても同じになるようにする)。
 * ToraNeko.Mk3 の App/drv/fan.h から。上限の切り替えとファンの電流を足した
 */
#ifndef DRV_FAN_H
#define DRV_FAN_H

#include <stdbool.h>

void fan_init(void);
void fan_set_voltage(float voltage_v);
void fan_allow_high_voltage(bool on);
void fan_stop(void);
float fan_get_voltage(void);
void fan_update(void);
void fan_read_adc(void);
float fan_get_current_mA(void);

#endif /* DRV_FAN_H */
