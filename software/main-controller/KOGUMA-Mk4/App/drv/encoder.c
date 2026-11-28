/*
 * encoder.c
 * タイヤの回転の読み取り(MT6835 × 2、SPI2。磁石はタイヤの軸に付いている)
 * ToraNeko.Mk3 の App/drv/encoder.c から。AS5047P を MT6835 に替えた(2026-11-28)。数え方(total)・向きの合わせ方は同じ
 *
 * ■ MT6835 との通信(SPI、モード 3。データシート Rev1.3 の 7.6)
 * CS を Low にしたあと、MCU が「命令(4 ビット)+ 番地(12 ビット)」の 2 バイトを送り、続けてデータを読み書きする。
 *   命令 0011 = 読む、0110 = 書く、1010 = 角度をまとめて読む(バースト)
 * 角度は「まとめて読む」で、番地 0x003〜0x006 の 4 バイトを続けて受け取る(6 バイトのやり取り)。
 * CS を Low にした瞬間の角度が中にとっておかれるので、4 バイトとも同じ瞬間の値になる。
 *   0x003: 角度の上の 8 ビット(ANGLE[20:13])
 *   0x004: 角度のまん中の 8 ビット(ANGLE[12:5])
 *   0x005: 上の 5 ビットが角度の下の 5 ビット(ANGLE[4:0])、下の 3 ビットが警告(STATUS: 回りすぎ・磁石が弱い・電圧が低い)
 *   0x006: CRC(上の 3 バイト = 24 ビットの確かめの数)
 * 角度 = 0x003 × 8192 + 0x004 × 32 + 0x005 ÷ 8(÷ 8 の切り捨てで、下の 3 ビットの警告を落とす)。
 * ビット演算(<< や &)を使わず、かけ算・割り算で書いた。
 *
 * ■ 左右と向き
 * 左右のタイヤは向かい合わせなので、機体が前に進むとき、片方の角度は増え、もう片方は減る。
 * 前に進むと total が増えるように、ENCODER_*_SIGN で向きを合わせる(実機で確かめる。今は ToraNeko と同じ仮の値)。
 *
 * ■ 歪み
 * ToraNeko は角度の歪みを表で直していた。MT6835 には自分で直す仕組み(User Auto-Calibration)があるので、
 * 表は使わない。校正は sys/encoder_cal.c(モード6 No.5)。
 *
 * ■ 割り込み
 * encoder_update() は 4kHz の処理の割り込み(sys/scheduler.c)から呼ぶ。読んだ値は volatile の変数に入れ、
 * メインの処理は get の関数で読む。HAL_SPI_TransmitReceive は、6 バイトを送り終わるまで待つ(15MHz で約 4µs)。
 */
#include "drv/encoder.h"

#include <stdio.h>

#include "main.h"
#include "spi.h"

/* 前に進むと角度が増えるなら 1、減るなら -1(仮。実機で、前に転がして total が増えるかを確かめる) */
#define ENCODER_LEFT_SIGN  -1  /* 左 */
#define ENCODER_RIGHT_SIGN 1   /* 右 */

#define COMMAND_READ  0x30     /* 命令 0011(読む)を、1 バイト目の上の 4 ビットに置いた数(0011 0000) */
#define COMMAND_WRITE 0x60     /* 命令 0110(書く) */
#define COMMAND_BURST 0xA0     /* 命令 1010(角度をまとめて読む) */
#define ANGLE_ADDRESS 0x03     /* 角度の最初の番地 */
#define RAW_TO_TOTAL  32       /* 21 ビットの角度を、1 回転 65536 の数え方にするときに割る数(2097152 ÷ 65536) */
#define HALF_REV_RAW  1048576  /* 半回転(21 ビットの角度で) */
#define SPI_TIMEOUT_MS 1       /* SPI のやり取りを待つ上限 [ms] */

/* 割り込みの中で書き換える値(volatile の理由は sys/scheduler.c の先頭のコメント) */
static volatile uint32_t s_left_angle = 0;   /* 読んだままの角度(21 ビット) */
static volatile uint32_t s_right_angle = 0;
static volatile int32_t s_left_total = 0;    /* 回った量(1 回転 65536) */
static volatile int32_t s_right_total = 0;
static volatile int32_t s_left_rest = 0;     /* 1 回転 65536 に直すときに割り切れなかった分(21 ビットの数。次の回に足す) */
static volatile int32_t s_right_rest = 0;
static volatile uint32_t s_left_error_count = 0;
static volatile uint32_t s_right_error_count = 0;
static volatile uint8_t s_last_status = 0;
static volatile bool s_paused = false;       /* true のあいだは encoder_update() が読まない(校正のとき) */

/* 左(right = false)・右(right = true)の CS を Low(話す)・High(話さない)にする */
static void set_cs(bool right, bool talk)
{
  GPIO_PinState state = GPIO_PIN_SET;
  if (talk) {
    state = GPIO_PIN_RESET;
  }
  if (right) {
    HAL_GPIO_WritePin(ENC_R_CS_GPIO_Port, ENC_R_CS_Pin, state);
  } else {
    HAL_GPIO_WritePin(ENC_L_CS_GPIO_Port, ENC_L_CS_Pin, state);
  }
}

/* CRC(MT6835 の決まり: 多項式 X^8 + X^2 + X + 1、上のビットから。初めの値は 0)を計算する。
 * ここだけはビット演算を使う(CRC は「1 ビットずつ、ずらしながら排他的論理和(^)をとる」計算なので、ほかの書き方がない)。
 *   1. 1 バイトずつ、今の CRC と排他的論理和(^)をとる
 *   2. 8 回くり返す: いちばん上のビット(0x80)が 1 なら、左に 1 つずらして 0x07(多項式の下の 8 ビット)と ^、0 ならずらすだけ */
static uint8_t crc8(const uint8_t data[], int length)
{
  uint8_t crc = 0;
  for (int i = 0; i < length; i++) {
    crc = crc ^ data[i];
    for (int bit = 0; bit < 8; bit++) {
      if ((crc & 0x80) != 0) {
        crc = (uint8_t)((crc << 1) ^ 0x07);
      } else {
        crc = (uint8_t)(crc << 1);
      }
    }
  }
  return crc;
}

/* 角度をまとめて読む。CRC が合って、警告がなければ true(角度を *angle に入れる) */
static bool read_angle(bool right, uint32_t *angle)
{
  uint8_t send[6] = {COMMAND_BURST, ANGLE_ADDRESS, 0, 0, 0, 0};
  uint8_t receive[6] = {0, 0, 0, 0, 0, 0};

  set_cs(right, true);
  HAL_StatusTypeDef result = HAL_SPI_TransmitReceive(&hspi2, send, receive, 6, SPI_TIMEOUT_MS);
  set_cs(right, false);
  if (result != HAL_OK) {
    return false;
  }

  /* receive[2]〜[5] が番地 0x003〜0x006 の中身(最初の 2 バイトは、命令を送っているあいだに受けた意味のない値) */
  uint8_t status = receive[4] - (receive[4] / 8) * 8;  /* 0x005 の下の 3 ビット(8 で割った余り) */
  if (crc8(&receive[2], 3) != receive[5]) {
    return false;
  }
  if (status != 0) {
    s_last_status = status;
    return false;
  }
  *angle = receive[2] * 8192 + receive[3] * 32 + receive[4] / 8;
  return true;
}

/* 前の角度から今の角度への変化(21 ビットの数)。0 と最大の境目をまたいだときは、近い向きに直す */
static int32_t angle_change(uint32_t last_angle, uint32_t now_angle)
{
  int32_t change = (int32_t)now_angle - (int32_t)last_angle;
  if (change > HALF_REV_RAW) {
    change = change - ENCODER_RAW_PER_REV;
  }
  if (change < -HALF_REV_RAW) {
    change = change + ENCODER_RAW_PER_REV;
  }
  return change;
}

/* 21 ビットの変化 change_raw を、割り切れなかった分 *rest と合わせて、1 回転 65536 の数え方の変化にする。
 * 割り切れなかった分は *rest に残して次の回に足す(細かい動きを捨てないため) */
static int32_t to_total_count(int32_t change_raw, volatile int32_t *rest)
{
  int32_t sum = change_raw + *rest;
  int32_t count = sum / RAW_TO_TOTAL;      /* C の割り算は 0 の向きに切り捨てる */
  *rest = sum - count * RAW_TO_TOTAL;
  return count;
}

/* 起動時に 1 回だけ呼ぶ。今の角度を読んで、ここを 0 として数え始める */
void encoder_init(void)
{
  /* SPI2 を先に動かしておく。HAL は最初のやり取りのときに SPI を動かし始めるので、それまでクロックの線の
   * 高さが決まっておらず、最初のやり取りがずれることがある(ToraNeko の IMU で 2026-10-22 に起きた) */
  __HAL_SPI_ENABLE(&hspi2);
  uint32_t angle = 0;
  if (read_angle(false, &angle)) {
    s_left_angle = angle;
    printf("Encoder L OK (angle %lu)\r\n", angle);
  } else {
    printf("Encoder L NG (status %u)\r\n", s_last_status);
  }
  if (read_angle(true, &angle)) {
    s_right_angle = angle;
    printf("Encoder R OK (angle %lu)\r\n", angle);
  } else {
    printf("Encoder R NG (status %u)\r\n", s_last_status);
  }
  s_left_total = 0;
  s_right_total = 0;
}

/* 4kHz の処理ごとに呼ぶ。左右の角度を読み、前の回からの変化を回った量に足す。エラーのときは、その回は足さない */
void encoder_update(void)
{
  if (s_paused) {
    return;
  }
  uint32_t angle = 0;
  if (read_angle(false, &angle)) {
    int32_t change = ENCODER_LEFT_SIGN * angle_change(s_left_angle, angle);
    s_left_total = s_left_total + to_total_count(change, &s_left_rest);
    s_left_angle = angle;
  } else {
    s_left_error_count = s_left_error_count + 1;
  }
  if (read_angle(true, &angle)) {
    int32_t change = ENCODER_RIGHT_SIGN * angle_change(s_right_angle, angle);
    s_right_total = s_right_total + to_total_count(change, &s_right_rest);
    s_right_angle = angle;
  } else {
    s_right_error_count = s_right_error_count + 1;
  }
}

/* 電源を入れてから、左のタイヤが回った量 [カウント](前に進む向きが +) */
int32_t encoder_get_left_total(void)
{
  return s_left_total;
}

/* 電源を入れてから、右のタイヤが回った量 [カウント](前に進む向きが +) */
int32_t encoder_get_right_total(void)
{
  return s_right_total;
}

/* 左の今の角度(0〜2097151。読んだまま) */
uint32_t encoder_get_left_angle(void)
{
  return s_left_angle;
}

/* 右の今の角度(0〜2097151。読んだまま) */
uint32_t encoder_get_right_angle(void)
{
  return s_right_angle;
}

uint32_t encoder_get_left_error_count(void)
{
  return s_left_error_count;
}

uint32_t encoder_get_right_error_count(void)
{
  return s_right_error_count;
}

/* 最後に見た警告(1 = 回りすぎ、2 = 磁石が弱い、4 = 電圧が低い。足し合わせた数) */
uint8_t encoder_get_last_status(void)
{
  return s_last_status;
}

/* true のあいだは、4kHz の処理で角度を読まない(校正でレジスタを読み書きするとき) */
void encoder_set_paused(bool paused)
{
  s_paused = paused;
}

/* 校正のピン CAL_EN(左右共通)を H(on)・L にする */
void encoder_set_cal_pin(bool on)
{
  GPIO_PinState state = GPIO_PIN_RESET;
  if (on) {
    state = GPIO_PIN_SET;
  }
  HAL_GPIO_WritePin(ENC_CAL_GPIO_Port, ENC_CAL_Pin, state);
}

/* レジスタを 1 つ読む(番地は 0x000〜0x0FF のものだけ使う。1 バイト目の下の 4 ビット = 番地の上の 4 ビットは 0)。
 * encoder_set_paused(true) のあいだに呼ぶ */
bool encoder_read_register(bool right, uint16_t address, uint8_t *value)
{
  uint8_t send[3] = {COMMAND_READ + address / 256, (uint8_t)(address - (address / 256) * 256), 0};
  uint8_t receive[3] = {0, 0, 0};
  set_cs(right, true);
  HAL_StatusTypeDef result = HAL_SPI_TransmitReceive(&hspi2, send, receive, 3, SPI_TIMEOUT_MS);
  set_cs(right, false);
  *value = receive[2];
  if (result != HAL_OK) {
    return false;
  }
  return true;
}

/* レジスタを 1 つ書く(電源を切ると元に戻る。EEPROM には書かない)。encoder_set_paused(true) のあいだに呼ぶ */
void encoder_write_register(bool right, uint16_t address, uint8_t value)
{
  uint8_t send[3] = {COMMAND_WRITE + address / 256, (uint8_t)(address - (address / 256) * 256), value};
  uint8_t receive[3] = {0, 0, 0};
  set_cs(right, true);
  HAL_SPI_TransmitReceive(&hspi2, send, receive, 3, SPI_TIMEOUT_MS);
  set_cs(right, false);
}
