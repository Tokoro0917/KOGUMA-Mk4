/*
 * current.c
 * モーターの電流・CMS・電池の電圧の読み取り(ADC2)。MK4 で足したもの(2026-11-28)
 *
 * ■ 読み方(Core/Src/adc.c の先頭)
 * ADC2 は、TIM1 の TRGO(20kHz)で injected の 4 本(左の電流・右の電流・左の CMS・右の CMS)を変換する。
 * 終わると ADC2 の割り込みが来て、sys/scheduler.c が current_read_adc() を呼ぶ。
 * 電池は regular の 1 本で、current_read_adc() の最後に次の変換をソフトで起動し、次の回(50µs あと)に読む。
 * 結果は LL の関数(stm32h5xx_ll_adc.h。レジスタを 1 つ読むだけの小さな関数)で読む。
 *
 * ■ 値の直し方(docs/spec.md の「モーターの電流」)
 * ADC は 12 ビット、3.3V で 4096。1 カウント = 3300 ÷ 4096 = 0.806mV。
 *   電流: INA241A3(ゲイン 50)× 5mΩ = 0.25V/A。0A で 1.65V(約 2048)。1 カウント = 0.806 ÷ 0.25 = 3.22mA
 *   CMS : MP6551 の CM を 4.7kΩ × 2 で受ける。0.235V/A(+の向き)、0A で 1.65V。1 カウント ≒ 3.43mA
 *   電池: 47kΩ と 10kΩ の分圧。電池の電圧 = ADC の電圧 × 57 ÷ 10
 * 0A の値は、起動したとき(モーターを止めているとき)に 0.1 秒測って決める(current_start_zero_measure())。
 *
 * ■ 向き
 * INA241A3 は OUT1 → モーターの向きを + として測る(仮。実機で、前に回したときに + になるかを確かめる)。
 * モーターの向き(config/robot_params.h の MOTOR_*_SIGN)をかけて、機体が前に進む向きの電流を + にする。
 */
#include "drv/current.h"

#include "adc.h"
#include "config/robot_params.h"
#include "main.h"

#define ADC_MV_PER_COUNT (3300.0f / 4096.0f)  /* 1 カウントの電圧 [mV] */
#define CURRENT_MV_PER_A 250.0f               /* INA241A3 の出力 [mV/A] */
#define CMS_MV_PER_A 235.0f                   /* CMS の出力 [mV/A](+ の向き) */
#define ZERO_DEFAULT_COUNT 2048.0f            /* 0A の値を測る前に使う値(1.65V) */
#define BATTERY_DIVIDER (57.0f / 10.0f)       /* 分圧を戻す倍率 */
#define BATTERY_FILTER_RATIO 0.01f            /* 電池の電圧のゆれを減らす割合(1 回で新しい値に 1% 近づける。約 5ms で落ち着く) */
#define ZERO_SAMPLE_COUNT 2000                /* 0A の値を測る回数(20kHz で 0.1 秒) */

/* 割り込みの中で書き換える値(volatile の理由は sys/scheduler.c の先頭のコメント) */
static volatile uint16_t s_left_raw = 2048;
static volatile uint16_t s_right_raw = 2048;
static volatile uint16_t s_left_cms_raw = 2048;
static volatile uint16_t s_right_cms_raw = 2048;
static volatile float s_left_zero = ZERO_DEFAULT_COUNT;     /* 0A のときの値 [カウント] */
static volatile float s_right_zero = ZERO_DEFAULT_COUNT;
static volatile float s_left_cms_zero = ZERO_DEFAULT_COUNT;
static volatile float s_right_cms_zero = ZERO_DEFAULT_COUNT;
static volatile float s_battery_v = 0.0f;
static volatile bool s_battery_first = true;   /* まだ電池を 1 回も読んでいない */
static volatile int s_zero_count = 0;          /* 0A の値を測った回数(ZERO_SAMPLE_COUNT になったら終わり) */
static volatile float s_zero_sum[4];           /* 0A の値を測るときの足し合わせ(左・右・左 CMS・右 CMS) */
static volatile bool s_zero_ready = false;

/* 起動時に 1 回だけ呼ぶ。ADC2 を校正して、injected の変換(TIM1 の TRGO で始まる)を待つようにする。
 * TIM1 を動かす前(motor_init() の前)に呼ぶ */
void current_init(void)
{
  HAL_ADCEx_Calibration_Start(&hadc2, ADC_SINGLE_ENDED);
  HAL_ADCEx_InjectedStart_IT(&hadc2);  /* 4 本が終わったら割り込み(EOCSelection が SEQ_CONV なので、4 本の終わりに 1 回) */
  HAL_ADC_Start(&hadc2);               /* 電池(regular)の最初の変換 */
}

/* 0A の値を測り直す(モーターを止めているときに呼ぶ。約 0.1 秒で終わる) */
void current_start_zero_measure(void)
{
  s_zero_ready = false;
  s_zero_sum[0] = 0.0f;
  s_zero_sum[1] = 0.0f;
  s_zero_sum[2] = 0.0f;
  s_zero_sum[3] = 0.0f;
  s_zero_count = 0;
}

/* 0A の値を測り終えたら true */
bool current_is_zero_ready(void)
{
  return s_zero_ready;
}

/* 0A の値を測っているあいだ、1 回分を足す。ZERO_SAMPLE_COUNT 回たまったら平均を 0A の値にする */
static void add_zero_sample(void)
{
  if (s_zero_ready) {
    return;
  }
  s_zero_sum[0] = s_zero_sum[0] + s_left_raw;
  s_zero_sum[1] = s_zero_sum[1] + s_right_raw;
  s_zero_sum[2] = s_zero_sum[2] + s_left_cms_raw;
  s_zero_sum[3] = s_zero_sum[3] + s_right_cms_raw;
  s_zero_count = s_zero_count + 1;
  if (s_zero_count >= ZERO_SAMPLE_COUNT) {
    s_left_zero = s_zero_sum[0] / ZERO_SAMPLE_COUNT;
    s_right_zero = s_zero_sum[1] / ZERO_SAMPLE_COUNT;
    s_left_cms_zero = s_zero_sum[2] / ZERO_SAMPLE_COUNT;
    s_right_cms_zero = s_zero_sum[3] / ZERO_SAMPLE_COUNT;
    s_zero_ready = true;
  }
}

/* 電池の電圧を読んで、ゆれを減らす。次の変換を始める */
static void read_battery(void)
{
  float battery_v = LL_ADC_REG_ReadConversionData12(ADC2) * ADC_MV_PER_COUNT / 1000.0f * BATTERY_DIVIDER;
  if (s_battery_first) {
    s_battery_v = battery_v;
    s_battery_first = false;
  } else {
    s_battery_v = s_battery_v + (battery_v - s_battery_v) * BATTERY_FILTER_RATIO;
  }
  LL_ADC_REG_StartConversion(ADC2);
}

/* 20kHz の処理の最初に呼ぶ(ADC2 の割り込みの中、sys/scheduler.c)。injected の 4 本と電池を読む */
void current_read_adc(void)
{
  s_left_raw = LL_ADC_INJ_ReadConversionData12(ADC2, LL_ADC_INJ_RANK_1);
  s_right_raw = LL_ADC_INJ_ReadConversionData12(ADC2, LL_ADC_INJ_RANK_2);
  s_left_cms_raw = LL_ADC_INJ_ReadConversionData12(ADC2, LL_ADC_INJ_RANK_3);
  s_right_cms_raw = LL_ADC_INJ_ReadConversionData12(ADC2, LL_ADC_INJ_RANK_4);
  add_zero_sample();
  read_battery();
}

/* 左のモーターの電流 [mA] */
float current_get_left_mA(void)
{
  float mV = (s_left_raw - s_left_zero) * ADC_MV_PER_COUNT;
  return MOTOR_LEFT_SIGN * mV / CURRENT_MV_PER_A * 1000.0f;
}

/* 右のモーターの電流 [mA] */
float current_get_right_mA(void)
{
  float mV = (s_right_raw - s_right_zero) * ADC_MV_PER_COUNT;
  return MOTOR_RIGHT_SIGN * mV / CURRENT_MV_PER_A * 1000.0f;
}

/* 左の CMS [mA](向きはない。電池から出る向きが +) */
float current_get_left_cms_mA(void)
{
  return (s_left_cms_raw - s_left_cms_zero) * ADC_MV_PER_COUNT / CMS_MV_PER_A * 1000.0f;
}

/* 右の CMS [mA] */
float current_get_right_cms_mA(void)
{
  return (s_right_cms_raw - s_right_cms_zero) * ADC_MV_PER_COUNT / CMS_MV_PER_A * 1000.0f;
}

/* 電池の電圧 [V] */
float current_get_battery_v(void)
{
  return s_battery_v;
}

uint16_t current_get_left_raw(void)
{
  return s_left_raw;
}

uint16_t current_get_right_raw(void)
{
  return s_right_raw;
}
