/*
 * current_ctrl.c
 * 電流の制御(20kHz)。MK4 で足したもの(2026-11-28。docs/control.md の 4 章「電流」)
 *
 * ■ 流れ(20kHz ごと。sys/scheduler.c の 20kHz の処理から current_ctrl_update() が呼ばれる)
 *   1. 測った電流が CURRENT_TRIP_MA を CURRENT_TRIP_TICKS 回(1ms)続けて超えたら、すぐ止める(守り)
 *   2. 電流で回すとき: 1 つのタイヤごとに
 *        かけたい電圧 = R × 目標の電流(巻線の抵抗の分)
 *                     + Ke × モーターの角速度(逆起電力の分。タイヤの速さから求める)
 *                     + PI(目標の電流 − 測った電流)(ずれを直す分)
 *      電圧で回すとき: 決めた電圧
 *   3. duty = かけたい電圧 ÷ 電池の電圧(電池の電圧が下がっても、同じ電圧になる)。−DUTY_MAX〜DUTY_MAX に収める
 *   4. duty を TIM1 に書く(drv/motor.c)
 *
 * ■ 積分(I の項)
 * 巻線は温まると抵抗が増える(60°C 上がると約 1.23 倍)ので、R だけでは電流が足りなくなる。そのずれを積分で埋める。
 * duty が上限に張り付いているあいだは積分を増やさない(張り付きから戻るときに行きすぎないため)。
 *
 * ■ 係数(CURRENT_KP・CURRENT_KI)
 * インダクタンスがまだ測れていない(docs/control.md の 5 章)ので、控えめの仮の値。モード4 の電流のステップの応答で決める。
 *
 * ■ 割り込み
 * current_ctrl_set_*() は 4kHz の処理(ctrl/control.c)やメインの処理から呼ぶ。20kHz の処理はこれより優先度が高く、
 * 途中で割り込むことがある。左右の目標を書いているあいだに割り込まれても、片方が 50µs 古いだけなので困らない。
 * 動かし方(s_mode)は、値を全部書いてから最後に変える。
 */
#include "ctrl/current_ctrl.h"

#include "config/robot_params.h"
#include "drv/current.h"
#include "drv/motor.h"

#define PI_VALUE 3.14159265f
#define CURRENT_KP 0.0004f       /* 比例: 電流のずれ 1mA あたりの電圧 [V/mA](0.4 V/A。仮) */
#define CURRENT_KI 2.0f          /* 積分: ずれ 1mA が 1 秒続いたときの電圧 [V/(mA・s)](2000 V/(A・s)。仮) */
#define INTEGRAL_LIMIT_V 2.0f    /* 積分の分の電圧の上限 [V] */
#define DUTY_MAX 0.95f           /* duty の上限(drv/motor.c と同じ) */
#define BATTERY_MIN_V 5.0f       /* 電池の電圧がこれより低く読めたら回さない(まだ測れていない、など) */

/* タイヤの速さ [mm/s] をモーターの軸の角速度 [rad/s] にする倍率(÷ タイヤの半径 [mm] × ギア比) */
#define WHEEL_MM_S_TO_MOTOR_RAD_S (GEAR_RATIO / (TIRE_DIAMETER_MM / 2.0f))

/* 1 つのタイヤの状態 */
typedef struct {
  float target_mA;      /* 目標の電流 */
  float voltage_v;      /* 電圧で回すときの電圧 */
  float wheel_mm_s;     /* タイヤの速さ */
  float integral_v;     /* 積分の分の電圧 */
  float duty;           /* 最後に出した duty */
  int over_ticks;       /* 電流が CURRENT_TRIP_MA を続けて超えた回数 */
} wheel_state_t;

/* 割り込みの中で書き換える(volatile の理由は sys/scheduler.c の先頭のコメント) */
static volatile wheel_state_t s_left;
static volatile wheel_state_t s_right;
static volatile current_ctrl_mode_t s_mode = CURRENT_CTRL_OFF;
static volatile float s_limit_mA = CURRENT_LIMIT_MA;
static volatile bool s_tripped = false;   /* 守りで止めたら true(current_ctrl_stop() で戻る) */

/* value を −limit〜limit に収める */
static float clamp(float value, float limit)
{
  if (value > limit) {
    return limit;
  }
  if (value < -limit) {
    return -limit;
  }
  return value;
}

/* 1 つのタイヤの、電流で回すときのかけたい電圧 [V] を決める(積分も進める) */
static float current_mode_voltage(volatile wheel_state_t *wheel, float measured_mA, float battery_v)
{
  float target_mA = clamp(wheel->target_mA, s_limit_mA);
  float error_mA = target_mA - measured_mA;
  float motor_rad_s = wheel->wheel_mm_s * WHEEL_MM_S_TO_MOTOR_RAD_S;
  float feedforward_v = MOTOR_RESISTANCE_OHM * target_mA / 1000.0f + MOTOR_KE_V_PER_RAD_S * motor_rad_s;
  float voltage_v = feedforward_v + error_mA * CURRENT_KP + wheel->integral_v;

  /* duty が上限に張り付いていなければ、積分を進める */
  float max_v = battery_v * DUTY_MAX;
  if (voltage_v < max_v && voltage_v > -max_v) {
    wheel->integral_v = clamp(wheel->integral_v + error_mA * CURRENT_KI * CURRENT_CTRL_PERIOD_S, INTEGRAL_LIMIT_V);
  }
  return voltage_v;
}

/* 1 つのタイヤの duty を決める */
static float wheel_duty(volatile wheel_state_t *wheel, float measured_mA, float battery_v)
{
  float voltage_v = 0.0f;
  if (s_mode == CURRENT_CTRL_CURRENT) {
    voltage_v = current_mode_voltage(wheel, measured_mA, battery_v);
  } else if (s_mode == CURRENT_CTRL_VOLTAGE) {
    voltage_v = wheel->voltage_v;
  }
  float duty = clamp(voltage_v / battery_v, DUTY_MAX);
  wheel->duty = duty;
  return duty;
}

/* 測った電流が大きすぎる状態が続いたら true(1 つのタイヤ) */
static bool check_trip(volatile wheel_state_t *wheel, float measured_mA)
{
  if (measured_mA > CURRENT_TRIP_MA || measured_mA < -CURRENT_TRIP_MA) {
    wheel->over_ticks = wheel->over_ticks + 1;
  } else {
    wheel->over_ticks = 0;
  }
  if (wheel->over_ticks >= CURRENT_TRIP_TICKS) {
    return true;
  }
  return false;
}

/* duty を 0 にして、MP6551 をスリープにする */
static void output_off(void)
{
  motor_stop();
  motor_enable(false);
  s_left.duty = 0.0f;
  s_right.duty = 0.0f;
}

/* 20kHz の処理から呼ぶ(割り込みの中。電流を読んだあと) */
void current_ctrl_update(void)
{
  float left_mA = current_get_left_mA();
  float right_mA = current_get_right_mA();
  bool left_trip = check_trip(&s_left, left_mA);
  bool right_trip = check_trip(&s_right, right_mA);
  if (left_trip || right_trip) {
    s_tripped = true;
    s_mode = CURRENT_CTRL_OFF;
  }

  float battery_v = current_get_battery_v();
  if (s_mode == CURRENT_CTRL_OFF || battery_v < BATTERY_MIN_V) {
    output_off();
    return;
  }
  float left_duty = wheel_duty(&s_left, left_mA, battery_v);
  float right_duty = wheel_duty(&s_right, right_mA, battery_v);
  motor_set_duty(left_duty, right_duty);
}

/* 積分を 0 にする */
static void reset_integral(void)
{
  s_left.integral_v = 0.0f;
  s_right.integral_v = 0.0f;
}

/* 左右の電流の目標 [mA] を決めて、電流で回す(+ が機体の前に進む向き) */
void current_ctrl_set_target_mA(float left_mA, float right_mA)
{
  s_left.target_mA = left_mA;
  s_right.target_mA = right_mA;
  if (s_mode != CURRENT_CTRL_CURRENT && !s_tripped) {
    reset_integral();
    motor_enable(true);
    s_mode = CURRENT_CTRL_CURRENT;
  }
}

/* 左右にかける電圧 [V] を決めて、電圧で回す(電流の制御はしない。守りは効く) */
void current_ctrl_set_voltage(float left_v, float right_v)
{
  s_left.voltage_v = left_v;
  s_right.voltage_v = right_v;
  if (s_mode != CURRENT_CTRL_VOLTAGE && !s_tripped) {
    motor_enable(true);
    s_mode = CURRENT_CTRL_VOLTAGE;
  }
}

/* 止める(duty 0、MP6551 はスリープ)。守りで止めた印も消す */
void current_ctrl_stop(void)
{
  s_mode = CURRENT_CTRL_OFF;
  s_left.target_mA = 0.0f;
  s_right.target_mA = 0.0f;
  s_left.voltage_v = 0.0f;
  s_right.voltage_v = 0.0f;
  reset_integral();
  s_tripped = false;
  output_off();
}

/* 電流の目標の上限 [mA] を決める(CURRENT_LIMIT_MAX_MA より大きくはしない) */
void current_ctrl_set_limit_mA(float limit_mA)
{
  if (limit_mA > CURRENT_LIMIT_MAX_MA) {
    limit_mA = CURRENT_LIMIT_MAX_MA;
  }
  if (limit_mA < 0.0f) {
    limit_mA = 0.0f;
  }
  s_limit_mA = limit_mA;
}

current_ctrl_mode_t current_ctrl_get_mode(void)
{
  return s_mode;
}

/* 守り(電流が大きすぎた)で止めたら true */
bool current_ctrl_is_tripped(void)
{
  return s_tripped;
}

float current_ctrl_get_left_target_mA(void)
{
  return s_left.target_mA;
}

float current_ctrl_get_right_target_mA(void)
{
  return s_right.target_mA;
}

float current_ctrl_get_left_duty(void)
{
  return s_left.duty;
}

float current_ctrl_get_right_duty(void)
{
  return s_right.duty;
}

/* 左右のタイヤの速さ [mm/s] を入れる(4kHz の処理から) */
void current_ctrl_set_wheel_speed(float left_mm_s, float right_mm_s)
{
  s_left.wheel_mm_s = left_mm_s;
  s_right.wheel_mm_s = right_mm_s;
}
