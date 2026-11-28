/*
 * led.h
 * LED の点灯・消灯(ToraNeko.Mk3 の App/drv/led.h から。MK4 の LED を足した)
 *
 * ■ 表示 LED(LED1〜LED7。ToraNeko と同じ番号と並び。docs/software.md の 6.2)
 *   LED1 = No. の 8(LED_NUM3)、LED2 = No. の 4(LED_NUM2)、
 *   LED3 = モードの 4(LED_MODE2)、LED4 = モードの 2(LED_MODE1)、LED5 = モードの 1(LED_MODE0)、
 *   LED6 = No. の 2(LED_NUM1)、LED7 = No. の 1(LED_NUM0)
 * ■ MK4 で足した LED(2026-11-27 の基板)
 *   壁の表示 FL・L・R・FR(D110〜D113)、状態の LED 0・1(D114・D115)、前の LED(D98)
 */
#ifndef DRV_LED_H
#define DRV_LED_H

#include <stdbool.h>
#include <stdint.h>

#define LED_COUNT 7  /* 表示 LED の個数 */

void led_init(void);
void led_set(uint8_t num, bool on);
void led_all_off(void);

/* 壁の表示 LED(壁センサがその側の壁を見ていれば点ける) */
void led_set_wall(bool front_left, bool left, bool right, bool front_right);

/* 状態の LED 0(D114。BLE の状態)・1(D115。機体の状態)、前の LED(D98) */
void led_set_status0(bool on);
void led_set_status1(bool on);
void led_set_front(bool on);

#endif /* DRV_LED_H */
