/*
 * led.c
 * LED の点灯・消灯(ToraNeko.Mk3 の App/drv/led.c から。MK4 のピンにして、壁の表示・状態・前の LED を足した)
 *
 * ピン名(LED_NUM3_GPIO_Port、LED_NUM3_Pin など)は Core/Inc/main.h にある。番号と並びは drv/led.h の先頭。
 */
#include "drv/led.h"

#include "main.h"

/* true なら点ける(H)、false なら消す(L)の、ピンに書く値にする */
static GPIO_PinState pin_state(bool on)
{
  if (on) {
    return GPIO_PIN_SET;
  }
  return GPIO_PIN_RESET;
}

/* 起動時に呼ぶ。全部消しておく */
void led_init(void)
{
  led_all_off();
  led_set_wall(false, false, false, false);
  led_set_status0(false);
  led_set_status1(false);
  led_set_front(false);
}

/* 表示 LED を 1 個点ける／消す。num は 1〜7(drv/led.h の先頭の並び)。on が true なら点灯 */
void led_set(uint8_t num, bool on)
{
  GPIO_PinState state = pin_state(on);

  if (num == 1) {
    HAL_GPIO_WritePin(LED_NUM3_GPIO_Port, LED_NUM3_Pin, state);
  } else if (num == 2) {
    HAL_GPIO_WritePin(LED_NUM2_GPIO_Port, LED_NUM2_Pin, state);
  } else if (num == 3) {
    HAL_GPIO_WritePin(LED_MODE2_GPIO_Port, LED_MODE2_Pin, state);
  } else if (num == 4) {
    HAL_GPIO_WritePin(LED_MODE1_GPIO_Port, LED_MODE1_Pin, state);
  } else if (num == 5) {
    HAL_GPIO_WritePin(LED_MODE0_GPIO_Port, LED_MODE0_Pin, state);
  } else if (num == 6) {
    HAL_GPIO_WritePin(LED_NUM1_GPIO_Port, LED_NUM1_Pin, state);
  } else if (num == 7) {
    HAL_GPIO_WritePin(LED_NUM0_GPIO_Port, LED_NUM0_Pin, state);
  }
  /* 1〜7 以外は何もしない */
}

/* 表示 LED を全部消す */
void led_all_off(void)
{
  for (uint8_t num = 1; num <= LED_COUNT; num++) {
    led_set(num, false);
  }
}

/* 壁の表示 LED を点ける／消す(左前・左・右・右前) */
void led_set_wall(bool front_left, bool left, bool right, bool front_right)
{
  HAL_GPIO_WritePin(LED_WALL_FL_GPIO_Port, LED_WALL_FL_Pin, pin_state(front_left));
  HAL_GPIO_WritePin(LED_WALL_L_GPIO_Port, LED_WALL_L_Pin, pin_state(left));
  HAL_GPIO_WritePin(LED_WALL_R_GPIO_Port, LED_WALL_R_Pin, pin_state(right));
  HAL_GPIO_WritePin(LED_WALL_FR_GPIO_Port, LED_WALL_FR_Pin, pin_state(front_right));
}

/* 状態の LED 0(D114、前の LED の左) */
void led_set_status0(bool on)
{
  HAL_GPIO_WritePin(LED_STATUS0_GPIO_Port, LED_STATUS0_Pin, pin_state(on));
}

/* 状態の LED 1(D115、前の LED の右) */
void led_set_status1(bool on)
{
  HAL_GPIO_WritePin(LED_STATUS1_GPIO_Port, LED_STATUS1_Pin, pin_state(on));
}

/* 前の LED(D98) */
void led_set_front(bool on)
{
  HAL_GPIO_WritePin(LED_FRONT_GPIO_Port, LED_FRONT_Pin, pin_state(on));
}
