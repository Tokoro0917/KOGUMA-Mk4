/*
 * mk4_encoder.c
 * MK4 のエンコーダ(MT6835 × 2、SPI2 + DMA、10kHz)。
 * 流れ: 20kHz の処理が偶数回目に encoder_start_left() → 左の DMA の終わりで encoder_left_done()
 *       (左の CS を High、右の CS を Low にして右を読む)→ 右の DMA の終わりで encoder_process()。
 * MT6835 の読み方: 命令 0xA003(続けて読む、番地 0x003 から)のあと、角度の 3 バイト(21 ビットの角度 +
 * 状態の 3 ビット)と CRC の 1 バイトが返る(MT6835 のデータシートの SPI の章)。
 * ToraNeko の drv/encoder.c の angle_change と同じやり方で、境目をまたいだ変化を直す。
 */
#include "drv/encoder.h"

#include <stdbool.h>

#include "bench_mark.h"
#include "mk4_hw.h"

#define FRAME_LENGTH 6              /* 命令 2 バイト + 角度 3 バイト + CRC 1 バイト */
#define HALF_REV_COUNT 1048576      /* 半回転のカウント数 */
#define ENCODER_PERIOD_S (1.0f / 10000.0f)
#define TIRE_DIAMETER_MM 24.0f
#define GEAR_RATIO 5.46f
#define MM_PER_COUNT (TIRE_DIAMETER_MM * 3.14159265f / ENCODER_COUNT_PER_REV)
#define RAD_PER_COUNT (2.0f * 3.14159265f / ENCODER_COUNT_PER_REV)
#define SPEED_FILTER_RATIO 0.3f     /* 速度のゆれを減らす割合(仮) */
#define ENCODER_LEFT_SIGN -1
#define ENCODER_RIGHT_SIGN 1

DMA_BUF uint8_t g_encoder_left_rx[8];
DMA_BUF uint8_t g_encoder_right_rx[8];

static volatile int32_t s_left_angle = 0;
static volatile int32_t s_right_angle = 0;
static volatile int32_t s_left_total = 0;
static volatile int32_t s_right_total = 0;
static volatile float s_left_speed_mm_s = 0.0f;
static volatile float s_right_speed_mm_s = 0.0f;
static volatile float s_left_motor_omega_rad_s = 0.0f;
static volatile float s_right_motor_omega_rad_s = 0.0f;
static volatile uint32_t s_error_count = 0;

void encoder_start_left(void)
{
  hw_pin_low(ENC_L_CS_PORT, ENC_L_CS_PIN);
  hw_spi2_start(g_encoder_left_rx, FRAME_LENGTH);
}

void encoder_left_done(void)
{
  hw_spi2_finish();
  hw_pin_high(ENC_L_CS_PORT, ENC_L_CS_PIN);
  hw_pin_low(ENC_R_CS_PORT, ENC_R_CS_PIN);
  hw_spi2_start(g_encoder_right_rx, FRAME_LENGTH);
}

/* MT6835 の CRC(多項式 x^8 + x^2 + x + 1、初めの値 0)。角度の 3 バイトから計算する。
 * ビットの計算を避けられない所: 1 バイトずつ、上のビットから 8 回、「いちばん上が 1 なら多項式を引く(XOR)」をくり返す */
static uint8_t crc8(const uint8_t data[], int length)
{
  uint8_t crc = 0;
  for (int i = 0; i < length; i++) {
    crc = crc ^ data[i];
    for (int bit = 0; bit < 8; bit++) {
      if ((crc & 0x80u) != 0u) {
        crc = (uint8_t)((crc << 1) ^ 0x07u);
      } else {
        crc = (uint8_t)(crc << 1);
      }
    }
  }
  return crc;
}

/* 受け取ったフレームから 21 ビットの角度を取り出す。CRC が合わないか、状態が悪ければ false */
static bool frame_to_angle(const uint8_t frame[], int32_t *angle)
{
  if (crc8(&frame[2], 3) != frame[5]) {
    return false;
  }
  if ((frame[4] & 0x02u) != 0u) {
    return false;  /* 磁石が弱い(STATUS の Bit1) */
  }
  /* 上の 8 ビット × 8192 + 中の 8 ビット × 32 + 下のバイトの上 5 ビット */
  *angle = frame[2] * 8192 + frame[3] * 32 + frame[4] / 8;
  return true;
}

/* 前の角度から今の角度への変化。境目をまたいだら近い向きに直す(ToraNeko の drv/encoder.c と同じ) */
static int32_t angle_change(int32_t last_angle, int32_t now_angle)
{
  int32_t change = now_angle - last_angle;
  if (change > HALF_REV_COUNT) {
    change = change - ENCODER_COUNT_PER_REV;
  }
  if (change < -HALF_REV_COUNT) {
    change = change + ENCODER_COUNT_PER_REV;
  }
  return change;
}

/* 右の DMA の終わりで呼ぶ。左右の角度から、回った量・車輪の速さ・モーターの角速度を求める */
void encoder_process(void)
{
  hw_spi2_finish();
  hw_pin_high(ENC_R_CS_PORT, ENC_R_CS_PIN);

  int32_t angle = 0;
  if (frame_to_angle(g_encoder_left_rx, &angle)) {
    int32_t change = ENCODER_LEFT_SIGN * angle_change(s_left_angle, angle);
    s_left_angle = angle;
    s_left_total = s_left_total + change;
    float speed_mm_s = change * MM_PER_COUNT / ENCODER_PERIOD_S;
    s_left_speed_mm_s = s_left_speed_mm_s + (speed_mm_s - s_left_speed_mm_s) * SPEED_FILTER_RATIO;
    s_left_motor_omega_rad_s = change * RAD_PER_COUNT / ENCODER_PERIOD_S * GEAR_RATIO;
  } else {
    s_error_count = s_error_count + 1;
  }
  if (frame_to_angle(g_encoder_right_rx, &angle)) {
    int32_t change = ENCODER_RIGHT_SIGN * angle_change(s_right_angle, angle);
    s_right_angle = angle;
    s_right_total = s_right_total + change;
    float speed_mm_s = change * MM_PER_COUNT / ENCODER_PERIOD_S;
    s_right_speed_mm_s = s_right_speed_mm_s + (speed_mm_s - s_right_speed_mm_s) * SPEED_FILTER_RATIO;
    s_right_motor_omega_rad_s = change * RAD_PER_COUNT / ENCODER_PERIOD_S * GEAR_RATIO;
  } else {
    s_error_count = s_error_count + 1;
  }
}

int32_t encoder_get_left_total(void)
{
  return s_left_total;
}

int32_t encoder_get_right_total(void)
{
  return s_right_total;
}

float encoder_get_left_motor_omega_rad_s(void)
{
  return s_left_motor_omega_rad_s;
}

float encoder_get_right_motor_omega_rad_s(void)
{
  return s_right_motor_omega_rad_s;
}

float encoder_get_left_speed_mm_s(void)
{
  return s_left_speed_mm_s;
}

float encoder_get_right_speed_mm_s(void)
{
  return s_right_speed_mm_s;
}

uint32_t encoder_get_error_count(void)
{
  return s_error_count;
}

/* ベンチ用: 1.5m/s で進んでいるときの、次のフレームを作る(CRC も正しく付ける) */
static void make_frame(uint8_t frame[], int32_t angle)
{
  frame[0] = 0;
  frame[1] = 0;
  frame[2] = (uint8_t)(angle / 8192);
  frame[3] = (uint8_t)((angle / 32) % 256);
  frame[4] = (uint8_t)((angle % 32) * 8);
  frame[5] = crc8(&frame[2], 3);
}

void encoder_bench_next(float speed_mm_s)
{
  /* 0.1ms に進むカウント(1.5m/s なら約 4170) */
  int32_t step = (int32_t)(speed_mm_s * ENCODER_PERIOD_S / MM_PER_COUNT);
  int32_t left = s_left_angle - step;
  if (left < 0) {
    left = left + ENCODER_COUNT_PER_REV;
  }
  int32_t right = s_right_angle + step;
  if (right >= ENCODER_COUNT_PER_REV) {
    right = right - ENCODER_COUNT_PER_REV;
  }
  make_frame(g_encoder_left_rx, left);
  make_frame(g_encoder_right_rx, right);
}
