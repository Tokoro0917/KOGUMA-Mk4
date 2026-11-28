/*
 * motor.c
 * 走行モーターの出力(MP6551 × 2、TIM1 の PWM)。ToraNeko.Mk3 の App/drv/motor.c から(2026-11-28)
 *
 * ■ PWM(Core/Src/tim.c)
 * TIM1 はセンターアラインドで 0 → 1500 → 0 と数える(80kHz)。比べる数(CCR)より小さいあいだ High を出す(PWM1 モード)。
 * CCR = duty × 1500。0 ならずっと Low、1500 ならずっと High。
 *
 * ■ MP6551 への出し方(docs/pinmap.md の「割り当ての考え方」。ToraNeko・KOGUMA とは違う)
 *   前に回す(duty が +): IN1 に PWM、IN2 は Low
 *   後ろに回す(duty が −): IN1 は Low、IN2 に PWM
 * PWM の Low のあいだは、どちらの向きも両側の出力が L になり、下側の FET で電流がゆっくり減る。
 * こうすると、電流の測り方(INA241A3)がどちらの向きでも同じになる。
 * ToraNeko は「片方を High のままにして、もう片方の Low の時間で回す」(ブレーキの側で減る)だった。
 *
 * ■ MOT_EN(PB2)
 * L のあいだ、MP6551 はスリープ(出力はどちらも切れる)。走る前に motor_enable(true) で H にする。
 *
 * ■ 向き
 * どちら向きが「機体が前に進む向き」かは、モーターの配線で決まる。config/robot_params.h の MOTOR_*_SIGN で合わせる。
 *
 * ■ 割り込み
 * motor_set_duty() は 20kHz の処理(ctrl/current_ctrl.c)から呼ぶ。__HAL_TIM_SET_COMPARE はレジスタ(CCR)に
 * 書くだけの命令なので速い。TIM1 は ARR・CCR の「次の周期から使う」設定(preload)なので、周期の途中で変わらない。
 */
#include "drv/motor.h"

#include "config/robot_params.h"
#include "main.h"
#include "tim.h"

#define PWM_PERIOD 1500        /* TIM1 の ARR(センターアラインドの山の数) */
#define DUTY_MAX   0.95f       /* duty の上限(MP6551 の上の FET のゲートを動かす電気をためる時間を残すため) */

/* 起動時に 1 回だけ呼ぶ。duty 0 にしてから PWM を出し始める(TIM1 の更新で ADC も起動し始める)。
 * TIM16(吸引ファン)も同じ時に動かし始めると、壁センサを読む位置が、車輪とファンの PWM のいつも同じ所になる
 * (drv/fan.c の fan_init() をこのすぐあとに呼ぶ) */
void motor_init(void)
{
  motor_enable(false);
  motor_stop();
  HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
  HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_2);
  HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_3);
  HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_4);
}

/* duty(0〜1)を、CCR の数(0〜1500)にする。上限を超えないようにする */
static uint32_t duty_to_count(float duty)
{
  if (duty > DUTY_MAX) {
    duty = DUTY_MAX;
  }
  if (duty < 0.0f) {
    duty = 0.0f;
  }
  return (uint32_t)(duty * PWM_PERIOD + 0.5f);  /* 0.5 を足して、四捨五入する */
}

/* 1 つのモーターの 2 本の入力に出す。duty が + なら IN1 側、− なら IN2 側を PWM する */
static void set_one_motor(uint32_t in1_channel, uint32_t in2_channel, float duty)
{
  if (duty >= 0.0f) {
    __HAL_TIM_SET_COMPARE(&htim1, in1_channel, duty_to_count(duty));
    __HAL_TIM_SET_COMPARE(&htim1, in2_channel, 0);
  } else {
    __HAL_TIM_SET_COMPARE(&htim1, in1_channel, 0);
    __HAL_TIM_SET_COMPARE(&htim1, in2_channel, duty_to_count(-duty));
  }
}

/* 左右のモーターの duty(−1〜1)を出す。+ が機体の前に進む向き */
void motor_set_duty(float left_duty, float right_duty)
{
  set_one_motor(TIM_CHANNEL_1, TIM_CHANNEL_2, MOTOR_LEFT_SIGN * left_duty);
  set_one_motor(TIM_CHANNEL_3, TIM_CHANNEL_4, MOTOR_RIGHT_SIGN * right_duty);
}

/* duty を 0 にする(4 本とも Low。下側の FET で電流が減る) */
void motor_stop(void)
{
  __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, 0);
  __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_2, 0);
  __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_3, 0);
  __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_4, 0);
}

/* MP6551 を動かす(true)・スリープにする(false) */
void motor_enable(bool on)
{
  if (on) {
    HAL_GPIO_WritePin(MOT_EN_GPIO_Port, MOT_EN_Pin, GPIO_PIN_SET);
  } else {
    HAL_GPIO_WritePin(MOT_EN_GPIO_Port, MOT_EN_Pin, GPIO_PIN_RESET);
  }
}

/* MP6551 が異常(過電流・過熱など)を知らせていれば true(nFAULT が L) */
bool motor_is_fault(void)
{
  if (HAL_GPIO_ReadPin(MOT_nFAULT_GPIO_Port, MOT_nFAULT_Pin) == GPIO_PIN_RESET) {
    return true;
  }
  return false;
}
