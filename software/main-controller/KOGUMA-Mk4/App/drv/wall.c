/*
 * wall.c
 * 壁センサの AD 値の読み取り(ADC1 の injected の 4 本)と、発光の順番。
 * ToraNeko.Mk3 の App/drv/wall.c から(2026-11-28)。ToraNeko は TIM3 と DMA の連鎖で 4 回測っていたが、
 * MK4 は TIM1(モーターの PWM)の 20kHz で ADC1 を起動し、20kHz の処理で順番を進める(docs/software.md の 4.3)
 *
 * ■ 流れ(20kHz ごと)
 *   1. TIM1 の TRGO で、ADC1(壁センサ)と ADC2(電流)が同時に変換を始める
 *   2. ADC2 の割り込みで sys/scheduler.c が wall_read_adc() を呼ぶ。ADC1 も同じ時間で終わっているので、
 *      4 本の結果を読み、今の順番(s_phase)の値として残す
 *   3. 順番を 1 つ進めて、次の順番の発光を点ける・消す。次の変換(50µs あと)まで点いているので、
 *      受光のアンプ(約 7µs で落ち着く)は十分に間に合う
 * 1 つの組が点いているのは 5 回に 1 回(50µs)なので、発光の平均の電流は小さい。
 *
 * ■ ピン
 *   組A: WALL_LED_FL_R(PB4)→ 左前と右の発光(NJU6080 の PWM の端子)
 *   組B: WALL_LED_L_FR(PB5)→ 左と右前の発光
 *   受光: FL = PC0(IN10)、L = PC1(IN11)、R = PC2(IN12)、FR = PC3(IN13)。ADC1 の injected の順番 1〜4
 */
#include "drv/wall.h"

#include "adc.h"
#include "drv/current.h"
#include "main.h"

#define PHASE_COUNT 5  /* 順番の数(20kHz の 5 回 = 4kHz で 1 巡) */

/* 受光の値(添字 0〜3 = 受光の番号 1〜4: FL・R・L・FR)。割り込みの中で書き換えるので volatile */
static volatile uint16_t s_dark[WALL_SENSOR_COUNT];
static volatile uint16_t s_lit_a[WALL_SENSOR_COUNT];
static volatile uint16_t s_lit_b[WALL_SENSOR_COUNT];
static volatile uint16_t s_extra[WALL_SENSOR_COUNT];
static volatile int s_phase = 0;              /* 今終わった変換の順番(0〜4) */
static volatile uint32_t s_cycle_count = 0;   /* 1 巡した回数 */

/* 組A(左前と右)を点ける・消す */
static void set_led_a(bool on)
{
  if (on) {
    HAL_GPIO_WritePin(WALL_LED_FL_R_GPIO_Port, WALL_LED_FL_R_Pin, GPIO_PIN_SET);
  } else {
    HAL_GPIO_WritePin(WALL_LED_FL_R_GPIO_Port, WALL_LED_FL_R_Pin, GPIO_PIN_RESET);
  }
}

/* 組B(左と右前)を点ける・消す */
static void set_led_b(bool on)
{
  if (on) {
    HAL_GPIO_WritePin(WALL_LED_L_FR_GPIO_Port, WALL_LED_L_FR_Pin, GPIO_PIN_SET);
  } else {
    HAL_GPIO_WritePin(WALL_LED_L_FR_GPIO_Port, WALL_LED_L_FR_Pin, GPIO_PIN_RESET);
  }
}

/* 起動時に 1 回だけ呼ぶ。ADC1 を校正して、injected の変換(TIM1 の TRGO で始まる)を待つようにする。
 * TIM1 を動かす前(motor_init() の前)に呼ぶ。ADC1 の割り込みは使わない(ADC2 の割り込みの中で読む) */
void wall_init(void)
{
  set_led_a(false);
  set_led_b(false);
  s_phase = 0;
  HAL_ADCEx_Calibration_Start(&hadc1, ADC_SINGLE_ENDED);
  HAL_ADCEx_InjectedStart(&hadc1);
}

/* 4 本の結果を values(添字 0〜3 = 受光の番号 1〜4)に写す。
 * ADC1 の順番 1〜4 は FL・L・R・FR なので、受光の番号(FL・R・L・FR)に並べ替える */
static void copy_sensors(volatile uint16_t values[])
{
  values[0] = LL_ADC_INJ_ReadConversionData12(ADC1, LL_ADC_INJ_RANK_1);  /* 1: FL */
  values[1] = LL_ADC_INJ_ReadConversionData12(ADC1, LL_ADC_INJ_RANK_3);  /* 2: R */
  values[2] = LL_ADC_INJ_ReadConversionData12(ADC1, LL_ADC_INJ_RANK_2);  /* 3: L */
  values[3] = LL_ADC_INJ_ReadConversionData12(ADC1, LL_ADC_INJ_RANK_4);  /* 4: FR */
}

/* 20kHz の処理から呼ぶ(割り込みの中)。今の順番の値を読み、順番を進めて次の発光にする。
 * 組B(順番 2)を読み終えたとき true を返す(sys/scheduler.c がそこで 4kHz の処理を起こす) */
bool wall_read_adc(void)
{
  bool cycle_done = false;
  LL_ADC_ClearFlag_JEOS(ADC1);

  if (s_phase == 0) {
    copy_sensors(s_dark);
  } else if (s_phase == 1) {
    copy_sensors(s_lit_a);
  } else if (s_phase == 2) {
    copy_sensors(s_lit_b);
    cycle_done = true;
    s_cycle_count = s_cycle_count + 1;
  } else if (s_phase == 3) {
    copy_sensors(s_extra);
  }

  /* 次の順番へ。次の変換のあいだの発光にする(順番 1 は組A、順番 2 は組B、ほかは消す) */
  int next_phase = s_phase + 1;
  if (next_phase >= PHASE_COUNT) {
    next_phase = 0;
  }
  set_led_a(next_phase == 1);
  set_led_b(next_phase == 2);
  s_phase = next_phase;
  return cycle_done;
}

/* num(1〜4)が範囲の中なら、配列の添字(0〜3)にする。範囲の外なら -1 */
static int to_index(int num)
{
  if (num < 1 || num > WALL_SENSOR_COUNT) {
    return -1;
  }
  return num - 1;
}

/* 受光 num の、組A を点けたときの値 */
uint16_t wall_get_lit_a(int num)
{
  int index = to_index(num);
  if (index < 0) {
    return 0;
  }
  return s_lit_a[index];
}

/* 受光 num の、組B を点けたときの値 */
uint16_t wall_get_lit_b(int num)
{
  int index = to_index(num);
  if (index < 0) {
    return 0;
  }
  return s_lit_b[index];
}

/* 受光 num の、全部消したときの値 */
uint16_t wall_get_dark(int num)
{
  int index = to_index(num);
  if (index < 0) {
    return 0;
  }
  return s_dark[index];
}

/* 受光 num の、順番 3(点けないで、組B のすぐあと)の値 */
uint16_t wall_get_extra(int num)
{
  int index = to_index(num);
  if (index < 0) {
    return 0;
  }
  return s_extra[index];
}

/* 受光 num の、組A を点けたときの値 − 消したときの値 */
int32_t wall_get_a_minus_dark(int num)
{
  int32_t lit = wall_get_lit_a(num);
  int32_t dark = wall_get_dark(num);
  return lit - dark;
}

/* 受光 num の、組B を点けたときの値 − 消したときの値 */
int32_t wall_get_b_minus_dark(int num)
{
  int32_t lit = wall_get_lit_b(num);
  int32_t dark = wall_get_dark(num);
  return lit - dark;
}

/* 電池の電圧 [V](ToraNeko の名前を残した) */
float wall_get_battery_v(void)
{
  return current_get_battery_v();
}

/* 1 巡した回数 */
uint32_t wall_get_cycle_count(void)
{
  return s_cycle_count;
}
