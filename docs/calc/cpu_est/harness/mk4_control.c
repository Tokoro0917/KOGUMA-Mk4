/*
 * mk4_control.c
 * MK4 の 4kHz の処理(docs/software.md の 4.5、docs/control.md)。TIM6 の割り込みの番号を借りて、
 * 20kHz の処理が 5 回に 1 回起こす。中身は ToraNeko の sys/scheduler.c の run_control() に MK4 の分を足したもの:
 *   1. odometry_update()      ToraNeko の ctrl/odometry.c(そのまま)
 *   2. 速度の推定             MK4: エンコーダの速さと IMU の加速度の相補フィルタ(docs/control.md の2章)
 *   3. 自己位置               MK4: x, y, θ を足していく。軌道の目標の位置との差(軌道追従の準備、3章)
 *   4. control_update()       ToraNeko の ctrl/control.c(そのまま): 軌道 → 速度・角度の PI + FF → 壁の補正
 *                             → motor_set_voltage()(MK4 では電流の目標にする、下)→ ログ → ずれの見張り
 *   5. モーターの温度の見張り(I²t)、電池の電流の分け方
 *   6. フェイルセーフ(nFAULT、20kHz・10kHz・IMU の処理が動いているか、エラーの数)
 *   7. MK4 で足すログの列(1kHz に間引く)
 *   8. ウォッチドッグ、処理時間の記録
 */
#include <math.h>
#include <stdbool.h>
#include <stdint.h>

#include "bench_mark.h"
#include "config/robot_params.h"
#include "ctrl/control.h"
#include "ctrl/odometry.h"
#include "ctrl/trajectory.h"
#include "drv/encoder.h"
#include "drv/imu.h"
#include "mk4_hw.h"
#include "sys/failsafe.h"

extern volatile float g_target_left_mA;
extern volatile float g_target_right_mA;
extern volatile float g_left_mA;
extern volatile float g_right_mA;
extern volatile float g_left_duty;
extern volatile float g_right_duty;
extern volatile float g_battery_v;
extern volatile float g_battery_mA;
extern volatile uint32_t g_current_tick_count;
uint32_t imu_get_sample_count(void);

#define DEG_TO_RAD (3.14159265f / 180.0f)
#define MA_PER_OUTPUT 1000.0f          /* ToraNeko の「電圧」の出口を、電流の目標 [mA] として読む(ゲインは合わせ直す) */
#define TARGET_LIMIT_MA 5000.0f
#define SPEED_FILTER_K 0.05f           /* 相補フィルタの K(仮) */
#define I2T_TIME_CONSTANT_S 2.0f
#define I2T_LIMIT_A2 9.0f              /* 3A の 2 乗 */
#define TRACKING_GAIN_X 0.0f           /* 軌道追従のゲイン(最初は 0、docs/control.md の4章) */
#define TRACKING_GAIN_Y 0.0f
#define LOG_DIVIDE 4                   /* 4kHz を 1kHz に間引く */
#define MK4_LOG_ROW_MAX 4000

/* MK4 で足すログの列(1 行) */
typedef struct {
  int16_t current_target_left;
  int16_t current_target_right;
  int16_t current_left;
  int16_t current_right;
  int16_t duty_left;
  int16_t duty_right;
  int16_t battery_mA;
  int16_t speed_estimate;
  int16_t accel_x;
  int16_t wheel_left;
  int16_t wheel_right;
  int16_t pose_x;
  int16_t pose_y;
  int16_t encoder_errors;
  int16_t isr_busy;
  int16_t reserved;
} mk4_log_row_t;

AXI_BUF static mk4_log_row_t s_mk4_rows[MK4_LOG_ROW_MAX];

static float s_speed_estimate_mm_s = 0.0f;
static float s_x_mm = 0.0f;
static float s_y_mm = 0.0f;
static float s_target_x_mm = 0.0f;
static float s_target_y_mm = 0.0f;
static float s_target_theta_deg = 0.0f;
static float s_tracking_v_mm_s = 0.0f;
static float s_tracking_omega_deg_s = 0.0f;
static float s_i2t_left_a2 = 0.0f;
static float s_i2t_right_a2 = 0.0f;
static float s_target_limit_mA = TARGET_LIMIT_MA;
static uint32_t s_last_current_count = 0;
static uint32_t s_last_imu_count = 0;
static int s_stuck_count = 0;
static int s_log_count = 0;
static int s_log_row = 0;
static uint32_t s_busy_max_us = 0;

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

/* ToraNeko の ctrl/control.c が呼ぶ。MK4 では、出口を左右の電流の目標にする */
void motor_set_voltage(float left_v, float right_v)
{
  g_target_left_mA = limit_value(left_v * MA_PER_OUTPUT, s_target_limit_mA);
  g_target_right_mA = limit_value(right_v * MA_PER_OUTPUT, s_target_limit_mA);
}

void motor_stop(void)
{
  g_target_left_mA = 0.0f;
  g_target_right_mA = 0.0f;
}

void fan_stop(void)
{
}

void uart_wait_free(int length)
{
  (void)length;
}

/* 2. 速度の推定(相補フィルタ): 予測 = 前の速度 + 加速度 × Δt、速度 = 予測 + K × (エンコーダの速さ − 予測) */
static void update_speed_estimate(void)
{
  float accel_mm_s2 = imu_get_accel_x_mps2() * 1000.0f;
  float predicted = s_speed_estimate_mm_s + accel_mm_s2 * CTRL_PERIOD_S;
  float encoder_speed = (encoder_get_left_speed_mm_s() + encoder_get_right_speed_mm_s()) / 2.0f;
  s_speed_estimate_mm_s = predicted + SPEED_FILTER_K * (encoder_speed - predicted);
}

/* 3. 自己位置と、軌道の目標の位置。差を「進む向き」と「横」に分ける(軌道追従のゲインは最初 0) */
static void update_pose(void)
{
  float theta_rad = imu_get_angle_deg() * DEG_TO_RAD;
  float cos_theta = cosf(theta_rad);
  float sin_theta = sinf(theta_rad);
  s_x_mm = s_x_mm + s_speed_estimate_mm_s * cos_theta * CTRL_PERIOD_S;
  s_y_mm = s_y_mm + s_speed_estimate_mm_s * sin_theta * CTRL_PERIOD_S;

  s_target_theta_deg = s_target_theta_deg + trajectory_get_omega_deg_s() * CTRL_PERIOD_S;
  float target_theta_rad = s_target_theta_deg * DEG_TO_RAD;
  float target_speed = trajectory_get_speed_mm_s();
  s_target_x_mm = s_target_x_mm + target_speed * cosf(target_theta_rad) * CTRL_PERIOD_S;
  s_target_y_mm = s_target_y_mm + target_speed * sinf(target_theta_rad) * CTRL_PERIOD_S;

  float dx = s_target_x_mm - s_x_mm;
  float dy = s_target_y_mm - s_y_mm;
  float along_mm = cos_theta * dx + sin_theta * dy;
  float side_mm = -sin_theta * dx + cos_theta * dy;
  s_tracking_v_mm_s = along_mm * TRACKING_GAIN_X;
  s_tracking_omega_deg_s = side_mm * TRACKING_GAIN_Y;
}

/* 5. モーターの温度の見張り: 電流の 2 乗を時定数のあるフィルタで足す。超えそうなら上限を 3A に下げる */
static void update_i2t(void)
{
  float left_A = g_left_mA * 0.001f;
  float right_A = g_right_mA * 0.001f;
  float ratio = CTRL_PERIOD_S / I2T_TIME_CONSTANT_S;
  s_i2t_left_a2 = s_i2t_left_a2 + (left_A * left_A - s_i2t_left_a2) * ratio;
  s_i2t_right_a2 = s_i2t_right_a2 + (right_A * right_A - s_i2t_right_a2) * ratio;
  if (s_i2t_left_a2 > I2T_LIMIT_A2 || s_i2t_right_a2 > I2T_LIMIT_A2) {
    s_target_limit_mA = 3000.0f;
  } else {
    s_target_limit_mA = TARGET_LIMIT_MA;
  }
}

/* 6. フェイルセーフ: nFAULT、20kHz の処理と IMU が進んでいるか、エンコーダのエラーの数 */
static void check_failsafe(void)
{
  bool stop = false;
  if (!hw_pin_read(NFAULT_PORT, NFAULT_PIN)) {
    stop = true;
  }
  uint32_t current_count = g_current_tick_count;
  uint32_t imu_count = imu_get_sample_count();
  if (current_count == s_last_current_count || imu_count == s_last_imu_count) {
    s_stuck_count = s_stuck_count + 1;
  } else {
    s_stuck_count = 0;
  }
  s_last_current_count = current_count;
  s_last_imu_count = imu_count;
  if (s_stuck_count > 4) {
    stop = true;
  }
  if (encoder_get_error_count() > 100) {
    stop = true;
  }
  if (stop && !failsafe_is_stopped()) {
    failsafe_stop();
  }
}

/* value × scale を四捨五入して int16 にする(ToraNeko の sys/log.c の to_int16 と同じ) */
static int16_t to_int16(float value, float scale)
{
  float scaled = value * scale;
  if (scaled > 32767.0f) {
    scaled = 32767.0f;
  }
  if (scaled < -32767.0f) {
    scaled = -32767.0f;
  }
  if (scaled >= 0.0f) {
    return (int16_t)(scaled + 0.5f);
  }
  return (int16_t)(scaled - 0.5f);
}

/* 7. MK4 で足すログの列を、4 回に 1 回(1kHz)残す */
static void record_mk4_log(void)
{
  s_log_count = s_log_count + 1;
  if (s_log_count < LOG_DIVIDE) {
    return;
  }
  s_log_count = 0;
  if (s_log_row >= MK4_LOG_ROW_MAX) {
    return;
  }
  int row = s_log_row;
  s_mk4_rows[row].current_target_left = to_int16(g_target_left_mA, 1.0f);
  s_mk4_rows[row].current_target_right = to_int16(g_target_right_mA, 1.0f);
  s_mk4_rows[row].current_left = to_int16(g_left_mA, 1.0f);
  s_mk4_rows[row].current_right = to_int16(g_right_mA, 1.0f);
  s_mk4_rows[row].duty_left = to_int16(g_left_duty, 10000.0f);
  s_mk4_rows[row].duty_right = to_int16(g_right_duty, 10000.0f);
  s_mk4_rows[row].battery_mA = to_int16(g_battery_mA, 1.0f);
  s_mk4_rows[row].speed_estimate = to_int16(s_speed_estimate_mm_s, 1.0f);
  s_mk4_rows[row].accel_x = to_int16(imu_get_accel_x_mps2(), 100.0f);
  s_mk4_rows[row].wheel_left = to_int16(encoder_get_left_speed_mm_s(), 1.0f);
  s_mk4_rows[row].wheel_right = to_int16(encoder_get_right_speed_mm_s(), 1.0f);
  s_mk4_rows[row].pose_x = to_int16(s_x_mm, 1.0f);
  s_mk4_rows[row].pose_y = to_int16(s_y_mm, 10.0f);
  s_mk4_rows[row].encoder_errors = (int16_t)encoder_get_error_count();
  s_mk4_rows[row].isr_busy = (int16_t)s_busy_max_us;
  s_mk4_rows[row].reserved = 0;
  s_log_row = row + 1;
}

/* 4kHz の処理(流れは先頭のコメント) */
void control_task(void)
{
  uint32_t start_us = hw_get_us();
  odometry_update();
  update_speed_estimate();
  update_pose();
  control_update();
  update_i2t();
  check_failsafe();
  record_mk4_log();
  hw_refresh_watchdog();
  uint32_t busy_us = hw_get_us() - start_us;
  if (busy_us > s_busy_max_us) {
    s_busy_max_us = busy_us;
  }
}

/* ベンチ用: ログの位置を 0 に戻す(いっぱいにならないように) */
void control_bench_reset_log(void)
{
  s_log_row = 0;
}

float control_bench_tracking(void)
{
  return s_tracking_v_mm_s + s_tracking_omega_deg_s;
}
