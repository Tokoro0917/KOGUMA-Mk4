/*
 * encoder.h
 * タイヤの回転の読み取り(MT6835 × 2、SPI2)。ToraNeko.Mk3 の App/drv/encoder.h から(AS5047P を MT6835 に替えた)
 *
 * MT6835 は、タイヤの軸の端に付けた磁石の向き(角度)を 0〜2097151(21 ビット)の数で返す。
 * 磁石はタイヤの軸に付いているので、タイヤ 1 回転 = 2097152。
 * 回った量(total)は、細かすぎると数が大きくなりすぎるので、1 回転 = 65536 カウントに直して数える
 * (1 カウント = 24mm × π ÷ 65536 ≒ 0.0012mm。int32_t で約 2.4km まで数えられる)。
 *
 * 4kHz の処理(0.25ms)ごとに encoder_update() で角度を読み、前の回からの差を足していく。
 * 0.25ms のあいだにタイヤが半回転以上回ることはない(約 150m/s 未満)ので、
 * 差が半回転より大きく見えたら、0 と最大の境目をまたいだと考えて直す。
 */
#ifndef DRV_ENCODER_H
#define DRV_ENCODER_H

#include <stdbool.h>
#include <stdint.h>

#define ENCODER_COUNT_PER_REV 65536    /* タイヤ 1 回転のカウント数(total の数え方) */
#define ENCODER_RAW_PER_REV 2097152    /* MT6835 が返す角度の 1 回転(2 の 21 乗) */

void encoder_init(void);
void encoder_update(void);

/* 電源を入れてから、左・右のタイヤが回った量 [カウント](1 回転 = 65536)。
 * 機体が前に進む向きに回すと増え、後ろに進む向きに回すと減る。モード選択(sys/ui.c)でも使う */
int32_t encoder_get_left_total(void);
int32_t encoder_get_right_total(void);

/* 今の角度(0〜2097151)。読んだままの角度。動作確認用 */
uint32_t encoder_get_left_angle(void);
uint32_t encoder_get_right_angle(void);

/* 読み取りのエラー(CRC が合わない・MT6835 の警告)の回数(電源を入れてから)と、最後の警告(STATUS の 3 ビット) */
uint32_t encoder_get_left_error_count(void);
uint32_t encoder_get_right_error_count(void);
uint8_t encoder_get_last_status(void);

/* 校正(sys/encoder_cal.c)のために使うもの。encoder_set_paused(true) のあいだは encoder_update() が読まないので、
 * そのあいだにレジスタを読み書きする */
void encoder_set_paused(bool paused);
void encoder_set_cal_pin(bool on);
bool encoder_read_register(bool right, uint16_t address, uint8_t *value);
void encoder_write_register(bool right, uint16_t address, uint8_t value);

#endif /* DRV_ENCODER_H */
