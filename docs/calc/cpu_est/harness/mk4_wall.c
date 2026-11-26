/*
 * mk4_wall.c
 * MK4 の壁センサの順番(docs/software.md の 4.3)。20kHz の処理から 1 回ずつ呼ばれ、5 回で 1 巡(4kHz)。
 *   順番 0: 消灯の値(FL・L・R・FR)とファンの電流を受け取る → 組A(FL と R)を点ける
 *   順番 1: 組A の値(FL・R)を受け取る → 組A を消し、組B(L と FR)を点ける
 *   順番 2: 組B の値(L・FR)を受け取る → 組B を消す → 4kHz の処理を起こす
 *   順番 3・4: 空き
 * 値の取り出し方(wall_get_a_minus_dark など)は ToraNeko の drv/wall.c と同じ名前にして、
 * ToraNeko の ctrl/wall_ctrl.c がそのまま使えるようにした。
 */
#include "drv/wall.h"

#include <stdbool.h>

#include "bench_mark.h"
#include "mk4_hw.h"

#define ADC1_COUNT 5          /* FL・L・R・FR・ファンの電流 */
#define ADC1_FL 0
#define ADC1_L 1
#define ADC1_R 2
#define ADC1_FR 3
#define ADC1_FAN 4
#define FAN_MA_PER_COUNT 0.8f  /* 仮の値 */

DMA_BUF uint16_t g_adc1_buffer[ADC1_COUNT];  /* ADC1 の DMA が書く所 */

static volatile uint16_t s_lit_a[WALL_SENSOR_COUNT + 1];
static volatile uint16_t s_lit_b[WALL_SENSOR_COUNT + 1];
static volatile uint16_t s_dark[WALL_SENSOR_COUNT + 1];
static volatile float s_fan_mA = 0.0f;
static int s_step = 0;                    /* 今の順番(0〜4) */
volatile float g_battery_v = 11.1f;       /* 20kHz の処理が書く(mk4_current.c) */

/* 順番を 1 つ進める。4kHz の処理を起こす回(組B を読み終えた回)なら true */
bool wall_step(void)
{
  bool wake_control = false;
  if (s_step == 0) {
    s_dark[1] = g_adc1_buffer[ADC1_FL];
    s_dark[2] = g_adc1_buffer[ADC1_R];
    s_dark[3] = g_adc1_buffer[ADC1_L];
    s_dark[4] = g_adc1_buffer[ADC1_FR];
    s_fan_mA = g_adc1_buffer[ADC1_FAN] * FAN_MA_PER_COUNT;
    hw_pin_high(WALL_LED_A_PORT, WALL_LED_A_PIN);
  } else if (s_step == 1) {
    s_lit_a[1] = g_adc1_buffer[ADC1_FL];
    s_lit_a[2] = g_adc1_buffer[ADC1_R];
    hw_pin_low(WALL_LED_A_PORT, WALL_LED_A_PIN);
    hw_pin_high(WALL_LED_B_PORT, WALL_LED_B_PIN);
  } else if (s_step == 2) {
    s_lit_b[3] = g_adc1_buffer[ADC1_L];
    s_lit_b[4] = g_adc1_buffer[ADC1_FR];
    hw_pin_low(WALL_LED_B_PORT, WALL_LED_B_PIN);
    wake_control = true;
  }
  s_step = s_step + 1;
  if (s_step >= 5) {
    s_step = 0;
  }
  return wake_control;
}

float wall_get_fan_mA(void)
{
  return s_fan_mA;
}

/* ここから下は ToraNeko の drv/wall.c と同じ */
uint16_t wall_get_lit_a(int num)
{
  return s_lit_a[num];
}

uint16_t wall_get_lit_b(int num)
{
  return s_lit_b[num];
}

uint16_t wall_get_dark(int num)
{
  return s_dark[num];
}

int32_t wall_get_a_minus_dark(int num)
{
  int32_t value = s_lit_a[num];
  value = value - s_dark[num];
  return value;
}

int32_t wall_get_b_minus_dark(int num)
{
  int32_t value = s_lit_b[num];
  value = value - s_dark[num];
  return value;
}

float wall_get_battery_v(void)
{
  return g_battery_v;
}

/* ベンチ用: 次の 20kHz の処理で ADC1 の DMA が書いてある値を入れる。walls なら区画のまん中で両側に壁 */
void wall_bench_adc(int step, bool walls)
{
  int left = 200;
  int right = 150;
  int front_left = 330;
  int front_right = 520;
  if (walls) {
    left = 1457;
    right = 1148;
  }
  int dark = 100;
  g_adc1_buffer[ADC1_FAN] = 900;
  if (step == 0) {
    g_adc1_buffer[ADC1_FL] = (uint16_t)dark;
    g_adc1_buffer[ADC1_L] = (uint16_t)dark;
    g_adc1_buffer[ADC1_R] = (uint16_t)dark;
    g_adc1_buffer[ADC1_FR] = (uint16_t)dark;
  } else if (step == 1) {
    g_adc1_buffer[ADC1_FL] = (uint16_t)(dark + front_left);
    g_adc1_buffer[ADC1_R] = (uint16_t)(dark + right);
  } else if (step == 2) {
    g_adc1_buffer[ADC1_L] = (uint16_t)(dark + left);
    g_adc1_buffer[ADC1_FR] = (uint16_t)(dark + front_right);
  }
}
