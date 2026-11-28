/*
 * encoder_cal.c
 * エンコーダの校正(モード6 No.5。MODES.md)。MK4 で作り直した(2026-11-28)
 *
 * ToraNeko(AS5047P)は、角度の歪みを自分で測って表(config/encoder_correction.h)を作っていた。
 * MK4 の MT6835 には、決まった速さで回しながら CAL_EN を H にすると、自分で歪みを直す仕組み
 * (User Auto-Calibration。データシート Rev1.3 の 9.2)があるので、それを使う。
 *
 * ■ 手順(タイヤを浮かせてから始める)
 *   1. 左右のタイヤを電圧で回し、タイヤの速さを約 300rpm(377mm/s)にそろえる(2 秒)。
 *      MT6835 の決まりでは、回す速さの範囲を先にレジスタ AUTOCAL_FREQ(番地 0x00E の 6〜4 ビット)に書く。
 *      ここでは 4 番(200〜400rpm)にする
 *   2. エンコーダを読むのを止め(校正のあいだは SPI で話さないほうがよい)、AUTOCAL_FREQ を書く
 *   3. CAL_EN を H にして、そのままの電圧で 15 秒回す(64 回転以上。300rpm なら 12.8 秒)
 *   4. 結果をレジスタ 0x113 の 7〜6 ビットで読む: 3 = うまくいった、2 = 失敗、1 = まだ校正中、0 = 校正していない
 *   5. CAL_EN を L に戻して止める。うまくいったら 6 秒以上待ってから電源を切る(MT6835 の決まり。
 *      電源を入れ直すまで、ほかの操作はできない)。LED とシリアルで知らせる
 * 校正の結果は MT6835 の中に残る(電源を切っても消えない)。
 */
#include "sys/encoder_cal.h"

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

#include "ctrl/current_ctrl.h"
#include "ctrl/odometry.h"
#include "drv/encoder.h"
#include "drv/timebase.h"
#include "sys/ui.h"

#define TARGET_SPEED_MM_S 377.0f     /* 回す速さ(300rpm × タイヤ 1 周 75.4mm ÷ 60 秒) */
#define START_VOLTAGE_V 0.5f         /* 最初にかける電圧 [V] */
#define VOLTAGE_GAIN_V_PER_MM_S 0.0005f  /* 速さのずれ 1mm/s あたりに、電圧を直す量 [V](10ms ごと) */
#define VOLTAGE_MAX_V 3.0f
#define SPIN_UP_MS 2000              /* 速さをそろえる時間 [ms] */
#define CALIBRATION_MS 15000         /* 校正のあいだ回す時間 [ms] */
#define AFTER_SUCCESS_WAIT_MS 7000   /* うまくいったあと、電源を切るまで待つ時間 [ms](6 秒以上) */
#define STEP_MS 10                   /* 速さを見る間隔 [ms] */
#define REG_AUTOCAL 0x00E            /* AUTOCAL_FREQ がある番地 */
#define REG_CAL_STATUS 0x113         /* 校正の結果がある番地 */
#define AUTOCAL_FREQ_300RPM 4        /* 200〜400rpm */

/* value を low〜high に収める */
static float clamp(float value, float low, float high)
{
  if (value < low) {
    return low;
  }
  if (value > high) {
    return high;
  }
  return value;
}

/* 左右のタイヤが TARGET_SPEED_MM_S で回るように電圧を合わせながら、wait_ms 回す。最後の電圧を left_v・right_v に返す */
static void spin_at_target(uint32_t wait_ms, float *left_v, float *right_v)
{
  uint32_t start_ms = timebase_get_ms();
  while (timebase_get_ms() - start_ms < wait_ms) {
    float left_error = TARGET_SPEED_MM_S - odometry_get_left_speed_mm_s();
    float right_error = TARGET_SPEED_MM_S - odometry_get_right_speed_mm_s();
    *left_v = clamp(*left_v + left_error * VOLTAGE_GAIN_V_PER_MM_S, 0.0f, VOLTAGE_MAX_V);
    *right_v = clamp(*right_v + right_error * VOLTAGE_GAIN_V_PER_MM_S, 0.0f, VOLTAGE_MAX_V);
    current_ctrl_set_voltage(*left_v, *right_v);
    ui_wait_ms(STEP_MS);
  }
}

/* AUTOCAL_FREQ(番地 0x00E の 6〜4 ビット)を 300rpm 用にする。ほかのビット(7 ビット目と 3〜0 ビット)は変えない。
 * ビット演算を使わず、かけ算・割り算で書いた: 7 ビット目 = 値 ÷ 128、3〜0 ビット = 値 ÷ 16 の余り */
static void write_autocal_freq(bool right)
{
  uint8_t value = 0;
  encoder_read_register(right, REG_AUTOCAL, &value);
  int top_bit = value / 128;
  int low_bits = value - (value / 16) * 16;
  uint8_t new_value = (uint8_t)(top_bit * 128 + AUTOCAL_FREQ_300RPM * 16 + low_bits);
  encoder_write_register(right, REG_AUTOCAL, new_value);
}

/* 校正の結果(0〜3)を読む。0x113 の 7〜6 ビット = 値 ÷ 64 */
static int read_cal_status(bool right)
{
  uint8_t value = 0;
  encoder_read_register(right, REG_CAL_STATUS, &value);
  return value / 64;
}

/* 結果の数を言葉にする */
static const char *status_name(int status)
{
  if (status == 3) {
    return "OK";
  }
  if (status == 2) {
    return "FAILED";
  }
  if (status == 1) {
    return "RUNNING";
  }
  return "NOT_STARTED";
}

/* エンコーダを校正する(先頭のコメントの手順)。タイヤを浮かせてから呼ぶ */
void encoder_cal_run(void)
{
  float left_v = START_VOLTAGE_V;
  float right_v = START_VOLTAGE_V;
  printf("ENCODER_CAL start (wheels must be off the floor)\r\n");

  /* 1. 速さをそろえる */
  spin_at_target(SPIN_UP_MS, &left_v, &right_v);
  printf("ENCODER_CAL speed L %.0f R %.0f mm/s, voltage L %.2f R %.2f V\r\n",
         odometry_get_left_speed_mm_s(), odometry_get_right_speed_mm_s(), left_v, right_v);

  /* 2. 読むのを止めて、速さの範囲を書く */
  encoder_set_paused(true);
  write_autocal_freq(false);
  write_autocal_freq(true);

  /* 3. CAL_EN を H にして、同じ電圧で回し続ける(エンコーダを読まないので、速さは合わせない) */
  encoder_set_cal_pin(true);
  ui_wait_ms(CALIBRATION_MS);

  /* 4. 結果を読む */
  int left_status = read_cal_status(false);
  int right_status = read_cal_status(true);

  /* 5. 止める */
  encoder_set_cal_pin(false);
  current_ctrl_stop();
  printf("ENCODER_CAL result L %s R %s\r\n", status_name(left_status), status_name(right_status));
  if (left_status == 3 && right_status == 3) {
    ui_wait_ms(AFTER_SUCCESS_WAIT_MS);
    printf("ENCODER_CAL done. Turn the power off and on\r\n");
    ui_signal_ok();
  } else {
    encoder_set_paused(false);
    ui_signal_error();
  }
}
