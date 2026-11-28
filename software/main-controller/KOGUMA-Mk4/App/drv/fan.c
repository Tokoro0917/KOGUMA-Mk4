/*
 * fan.c
 * 吸引ファン(モーター NFP-D8620。TIM16 CH1 の PWM、PB8。N チャネル MOSFET で、電池からローサイドで回す)と、ファンの電流
 * ToraNeko.Mk3 の App/drv/fan.c から(2026-11-28)。ファンの電流の読み取りを足した
 *
 * ■ PWM
 * TIM16 は 240MHz で 0〜2999 を数える(80kHz。モーターの TIM1 と同じ周期。Core/Src/tim.c)。
 * 比べる数(CCR)より小さいあいだ High を出し、そのあいだ MOSFET が ON になってファンに電池の電圧がかかる。
 * CCR を 0 にすると止まり、3000 にすると、ずっと ON になる。
 *
 * ■ 電圧で決める(ToraNeko と同じ)
 * ファンには電池の電圧がそのままかかるので、「かけたい電圧 ÷ 電池の電圧」の割合だけ ON にする。
 * 電池の電圧は走っているあいだに下がるので、4kHz の処理ごとに fan_update() で割合を計算し直す(sys/scheduler.c)。
 *
 * ■ 上限(docs/control.md の 4 章「吸引ファンの電圧の上限」、docs/spec.md「ファンの羽根の強さ」)
 * 回しすぎると羽根が遠心力で壊れるので、ふだんは 7.4V(モーターの定格、約 40,000rpm)より高い電圧はかけない。
 * 最短走行のときだけ fan_allow_high_voltage(true) で 8.5V(案、約 45,000rpm)まで上げられる。
 *
 * ■ ファンの電流
 * ADC1 の regular の 1 本(FAN_ISENSE、PB0)。20kHz の処理で読み、次の変換を始める。
 * シャントの電圧を RC で平均したものなので、さらに 20 回(1ms)足して平均する(12 ビットで 1A ≒ 12 カウントと粗いため)。
 * シャントは 10mΩ(仮。docs/spec.md の「ファンの電流の計測」。回路図で確かめる)。
 */
#include "drv/fan.h"

#include <stdbool.h>

#include "adc.h"
#include "drv/current.h"
#include "main.h"
#include "tim.h"

#define FAN_PWM_PERIOD    3000   /* TIM16 が 1 周で数える数(ARR 2999 + 1) */
#define FAN_LIMIT_V       7.4f   /* ふだんの上限 [V](モーターの定格) */
#define FAN_HIGH_LIMIT_V  8.5f   /* 最短走行のときの上限 [V](案) */
#define FAN_BATTERY_MIN_V 5.0f   /* 電池の電圧がこれより低く読めたら回さない(まだ測れていない、など) */
#define FAN_SHUNT_MOHM    10.0f  /* ファンの電流を測るシャント [mΩ](仮) */
#define ADC_MV_PER_COUNT  (3300.0f / 4096.0f)
#define FAN_AVERAGE_COUNT 20     /* ファンの電流を平均する回数(20kHz で 1ms) */

/* かけたい電圧 [V]。メインの処理で書き、割り込み(fan_update())で読むので volatile */
static volatile float s_target_v = 0.0f;
static volatile bool s_allow_high = false;
static volatile uint32_t s_current_sum = 0;   /* ファンの電流の足し合わせ [カウント] */
static volatile int s_current_count = 0;
static volatile float s_current_mA = 0.0f;    /* 平均したファンの電流 [mA] */

/* 起動時に 1 回だけ呼ぶ。止めた状態(CCR 0)にしてから、PWM を出し始める。motor_init() のすぐあとに呼ぶ */
void fan_init(void)
{
  s_target_v = 0.0f;
  __HAL_TIM_SET_COMPARE(&htim16, TIM_CHANNEL_1, 0);
  HAL_TIM_PWM_Start(&htim16, TIM_CHANNEL_1);
  HAL_ADC_Start(&hadc1);  /* ファンの電流(regular)の最初の変換 */
}

/* 今の上限の電圧 [V] */
static float limit_v(void)
{
  if (s_allow_high) {
    return FAN_HIGH_LIMIT_V;
  }
  return FAN_LIMIT_V;
}

/* ファンにかける電圧を決める [V]。0 で止まる。上限より高くはしない */
void fan_set_voltage(float voltage_v)
{
  if (voltage_v < 0.0f) {
    voltage_v = 0.0f;
  }
  if (voltage_v > limit_v()) {
    voltage_v = limit_v();
  }
  s_target_v = voltage_v;
  fan_update();
}

/* 上限を 8.5V にする(true。最短走行のときだけ)・7.4V に戻す(false) */
void fan_allow_high_voltage(bool on)
{
  s_allow_high = on;
  if (!on && s_target_v > FAN_LIMIT_V) {
    s_target_v = FAN_LIMIT_V;
  }
}

/* ファンを止める */
void fan_stop(void)
{
  s_target_v = 0.0f;
  __HAL_TIM_SET_COMPARE(&htim16, TIM_CHANNEL_1, 0);
}

/* 今かけたい電圧 [V](0 なら止まっている) */
float fan_get_voltage(void)
{
  return s_target_v;
}

/* 今の電池の電圧で、ON にする割合を計算し直す。4kHz の処理ごとに呼ぶ(sys/scheduler.c) */
void fan_update(void)
{
  float battery_v = current_get_battery_v();
  if (s_target_v <= 0.0f || battery_v < FAN_BATTERY_MIN_V) {
    __HAL_TIM_SET_COMPARE(&htim16, TIM_CHANNEL_1, 0);
    return;
  }
  int on_count = s_target_v / battery_v * FAN_PWM_PERIOD + 0.5f;  /* 0.5 を足して、四捨五入する */
  if (on_count > FAN_PWM_PERIOD) {
    on_count = FAN_PWM_PERIOD;
  }
  __HAL_TIM_SET_COMPARE(&htim16, TIM_CHANNEL_1, on_count);
}

/* 20kHz の処理から呼ぶ(割り込みの中)。ファンの電流を読んで足し、次の変換を始める。20 回たまったら平均する */
void fan_read_adc(void)
{
  s_current_sum = s_current_sum + LL_ADC_REG_ReadConversionData12(ADC1);
  s_current_count = s_current_count + 1;
  if (s_current_count >= FAN_AVERAGE_COUNT) {
    float average_count = (float)s_current_sum / FAN_AVERAGE_COUNT;
    s_current_mA = average_count * ADC_MV_PER_COUNT / FAN_SHUNT_MOHM * 1000.0f;
    s_current_sum = 0;
    s_current_count = 0;
  }
  LL_ADC_REG_StartConversion(ADC1);
}

/* ファンの電流 [mA](1ms の平均) */
float fan_get_current_mA(void)
{
  return s_current_mA;
}
