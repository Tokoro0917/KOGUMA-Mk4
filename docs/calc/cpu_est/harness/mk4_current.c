/*
 * mk4_current.c
 * MK4 の 20kHz の処理(docs/software.md の 4.4 の 1〜8、docs/control.md の4章)。
 * ADC2 の DMA の終わりの割り込みから current_isr() が呼ばれる。
 *   1. 電流を mA に直す(左右の電流・CMS・電池)
 *   2. 電流の守り(目標を上限で頭打ち、5A を 1ms 超えたら止める、電池の電流の見張り、回生の制限)
 *   3. 電流の制御: duty = (R × 目標 + Ke × モーターの角速度) / 電池の電圧 + PI(目標 − 測った電流)、duty の上限
 *   4. duty を TIM1 の 4 つの比較の値に書く
 *   5. 壁センサの順番を進める(mk4_wall.c)
 *   6. 偶数回目に、エンコーダの読み取り(SPI2 の DMA)を始める(10kHz)
 *   7. 5 回に 1 回、4kHz の処理を起こす
 *   8. 処理時間を記録する(ToraNeko の sys/scheduler.c と同じ)
 */
#include <stdbool.h>
#include <stdint.h>

#include "bench_mark.h"
#include "drv/encoder.h"
#include "mk4_hw.h"

bool wall_step(void);
float wall_get_fan_mA(void);
extern volatile float g_battery_v;

#define ADC2_COUNT 5            /* MOT_L_I・MOT_R_I・MOT_L_CMS・MOT_R_CMS・BATT */
#define CURRENT_PERIOD_S (1.0f / 20000.0f)
#define MA_PER_COUNT 4.03f      /* INA241A3(20V/V)、5mΩ、3.3V/65536 ... の仮の値 */
#define CMS_MA_PER_COUNT 1.2f   /* 仮の値 */
#define BATTERY_V_PER_COUNT (3.3f / 65535.0f * 5.0f)
#define MOTOR_R_OHM 1.03f       /* 巻線 1Ω + ドライバ 0.03Ω(docs/control.md の3章) */
#define MOTOR_KE_V_S 0.00151f   /* 逆起電力 1.51mV/(rad/s) */
#define CURRENT_KP_V_PER_A 0.8f
#define CURRENT_KI_V_PER_A_S 2000.0f
#define INTEGRAL_LIMIT_V 2.0f
#define CURRENT_LIMIT_MA 5000.0f       /* 片側の上限 */
#define OVER_CURRENT_MA 5000.0f        /* これを 1ms(20 回)続けて超えたら止める */
#define OVER_CURRENT_COUNT 20
#define BATTERY_CURRENT_LIMIT_MA 7500.0f
#define REGEN_LIMIT_MA 1500.0f
#define REGEN_VOLTAGE_V 13.5f
#define DUTY_MAX 0.95f
#define PWM_COMPARE_MAX 1250    /* TIM1 の ARR(センターアラインド) */

DMA_BUF uint16_t g_adc2_buffer[ADC2_COUNT];  /* ADC2 の DMA が書く所 */

/* 4kHz の処理が書き、20kHz の処理が読む */
volatile float g_target_left_mA = 0.0f;
volatile float g_target_right_mA = 0.0f;

/* 20kHz の処理が書く(ログと 4kHz の処理が読む) */
volatile float g_left_mA = 0.0f;
volatile float g_right_mA = 0.0f;
volatile float g_left_cms_mA = 0.0f;
volatile float g_right_cms_mA = 0.0f;
volatile float g_left_duty = 0.0f;
volatile float g_right_duty = 0.0f;
volatile float g_battery_mA = 0.0f;
volatile uint32_t g_current_tick_count = 0;
volatile bool g_current_stopped = false;

static int s_zero_left = 32768;          /* 0A のときの ADC の値(起動時に測る) */
static int s_zero_right = 32768;
static float s_integral_left_v = 0.0f;
static float s_integral_right_v = 0.0f;
static float s_limit_mA = CURRENT_LIMIT_MA;
static int s_over_current_count = 0;
static int s_encoder_parity = 0;         /* 0 と 1 をくり返す(偶数回目にエンコーダを読む) */

static volatile uint32_t s_busy_max_us = 0;
static volatile uint32_t s_period_min_us = 0xFFFFFFFF;
static volatile uint32_t s_period_max_us = 0;
static volatile uint32_t s_last_start_us = 0;
static volatile bool s_has_last_start = false;

/* value を -limit〜limit にする */
static float limit_value(float value, float limit)
{
  if (value > limit) {
    return limit;
  }
  if (value < -limit) {
    return -limit;
  }
  return value;
}

/* 1. 電流を mA に直す */
static void convert_adc(void)
{
  g_left_mA = (g_adc2_buffer[0] - s_zero_left) * MA_PER_COUNT;
  g_right_mA = (g_adc2_buffer[1] - s_zero_right) * MA_PER_COUNT;
  g_left_cms_mA = g_adc2_buffer[2] * CMS_MA_PER_COUNT;
  g_right_cms_mA = g_adc2_buffer[3] * CMS_MA_PER_COUNT;
  g_battery_v = g_adc2_buffer[4] * BATTERY_V_PER_COUNT;
}

/* 2. 電流の守り。止めたら true */
static bool check_over_current(void)
{
  if (g_left_mA > OVER_CURRENT_MA || g_left_mA < -OVER_CURRENT_MA
      || g_right_mA > OVER_CURRENT_MA || g_right_mA < -OVER_CURRENT_MA) {
    s_over_current_count = s_over_current_count + 1;
  } else {
    s_over_current_count = 0;
  }
  if (s_over_current_count >= OVER_CURRENT_COUNT) {
    g_current_stopped = true;
    hw_pin_low(MOTOR_EN_PORT, MOTOR_EN_PIN);
  }
  return g_current_stopped;
}

/* 電池の電流 ≒ Σ(duty × モーターの電流)+ ファンの電流 が上限を超えないように、片側の上限を下げる */
static void update_current_limit(void)
{
  g_battery_mA = g_left_duty * g_left_mA + g_right_duty * g_right_mA + wall_get_fan_mA();
  if (g_battery_mA > BATTERY_CURRENT_LIMIT_MA) {
    s_limit_mA = CURRENT_LIMIT_MA * BATTERY_CURRENT_LIMIT_MA / g_battery_mA;
  } else {
    s_limit_mA = CURRENT_LIMIT_MA;
  }
}

/* 回生の制限: 電池へ戻る電流(duty × 目標)が大きすぎないように、目標を小さくする */
static float limit_regen(float target_mA, float duty)
{
  float regen_limit_mA = REGEN_LIMIT_MA;
  if (g_battery_v > REGEN_VOLTAGE_V) {
    regen_limit_mA = REGEN_LIMIT_MA * 0.5f;
  }
  float battery_side_mA = duty * target_mA;
  if (battery_side_mA < -regen_limit_mA) {
    if (duty > 0.01f || duty < -0.01f) {
      return -regen_limit_mA / duty;
    }
  }
  return target_mA;
}

/* 3. 1 つのモーターの電流の制御。duty(-DUTY_MAX〜DUTY_MAX)を返す */
static float control_one_motor(float target_mA, float measured_mA, float omega_rad_s, float last_duty, float *integral_v)
{
  target_mA = limit_value(target_mA, s_limit_mA);
  target_mA = limit_regen(target_mA, last_duty);
  float target_A = target_mA * 0.001f;
  float error_A = (target_mA - measured_mA) * 0.001f;
  float back_emf_v = MOTOR_KE_V_S * omega_rad_s;

  *integral_v = *integral_v + CURRENT_KI_V_PER_A_S * error_A * CURRENT_PERIOD_S;
  *integral_v = limit_value(*integral_v, INTEGRAL_LIMIT_V);

  float voltage_v = MOTOR_R_OHM * target_A + back_emf_v + CURRENT_KP_V_PER_A * error_A + *integral_v;
  float duty = voltage_v / g_battery_v;

  /* duty の上限: 上限の電流より多く流れない duty(ADC が読めなくても効く守り) */
  float limit_A = s_limit_mA * 0.001f;
  float duty_high = (MOTOR_R_OHM * limit_A + back_emf_v) / g_battery_v;
  float duty_low = (-MOTOR_R_OHM * limit_A + back_emf_v) / g_battery_v;
  if (duty > duty_high) {
    duty = duty_high;
  }
  if (duty < duty_low) {
    duty = duty_low;
  }
  return limit_value(duty, DUTY_MAX);
}

/* duty を、IN1・IN2 の比較の値にする(+ なら IN1 側を PWM。ToraNeko の drv/motor.c と同じ形) */
static void duty_to_compare(float duty, uint32_t *in1, uint32_t *in2)
{
  if (duty >= 0.0f) {
    int count = duty * PWM_COMPARE_MAX + 0.5f;
    *in1 = PWM_COMPARE_MAX - count;
    *in2 = PWM_COMPARE_MAX;
  } else {
    int count = -duty * PWM_COMPARE_MAX + 0.5f;
    *in1 = PWM_COMPARE_MAX;
    *in2 = PWM_COMPARE_MAX - count;
  }
}

/* 8. 間隔を記録する(ToraNeko の sys/scheduler.c の record_period と同じ) */
static void record_period(uint32_t start_us)
{
  if (s_has_last_start) {
    uint32_t period_us = start_us - s_last_start_us;
    if (period_us < s_period_min_us) {
      s_period_min_us = period_us;
    }
    if (period_us > s_period_max_us) {
      s_period_max_us = period_us;
    }
  }
  s_last_start_us = start_us;
  s_has_last_start = true;
}

/* 20kHz の処理(流れは先頭のコメント) */
void current_isr(void)
{
  uint32_t start_us = hw_get_us();
  record_period(start_us);

  convert_adc();
  uint32_t left_in1 = PWM_COMPARE_MAX;
  uint32_t left_in2 = PWM_COMPARE_MAX;
  uint32_t right_in1 = PWM_COMPARE_MAX;
  uint32_t right_in2 = PWM_COMPARE_MAX;
  if (!check_over_current()) {
    update_current_limit();
    float left_duty = control_one_motor(g_target_left_mA, g_left_mA, encoder_get_left_motor_omega_rad_s(),
                                        g_left_duty, &s_integral_left_v);
    float right_duty = control_one_motor(g_target_right_mA, g_right_mA, encoder_get_right_motor_omega_rad_s(),
                                         g_right_duty, &s_integral_right_v);
    g_left_duty = left_duty;
    g_right_duty = right_duty;
    duty_to_compare(left_duty, &left_in1, &left_in2);
    duty_to_compare(right_duty, &right_in1, &right_in2);
  }
  hw_set_motor_compare(left_in1, left_in2, right_in1, right_in2);

  bool wake_control = wall_step();

  if (s_encoder_parity == 0) {
    encoder_start_left();
    s_encoder_parity = 1;
  } else {
    s_encoder_parity = 0;
  }
  if (wake_control) {
    hw_wake_control_task();
  }

  g_current_tick_count = g_current_tick_count + 1;
  uint32_t busy_us = hw_get_us() - start_us;
  if (busy_us > s_busy_max_us) {
    s_busy_max_us = busy_us;
  }
}

/* ベンチ用: 走っているときの値にする */
void current_bench_set(void)
{
  g_adc2_buffer[0] = 32768 + 300;   /* 約 1.2A */
  g_adc2_buffer[1] = 32768 + 250;
  g_adc2_buffer[2] = 400;
  g_adc2_buffer[3] = 380;
  g_adc2_buffer[4] = 44000;         /* 約 11.1V */
  g_target_left_mA = 1300.0f;
  g_target_right_mA = 1100.0f;
  g_left_duty = 0.3f;
  g_right_duty = 0.28f;
}
