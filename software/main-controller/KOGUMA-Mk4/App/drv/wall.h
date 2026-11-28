/*
 * wall.h
 * 壁センサ(受光 4 つ、発光 2 組)の AD 値の読み取り。ToraNeko.Mk3 の App/drv/wall.h から(読み方を MK4 に変えた)
 *
 * 20kHz の処理(sys/scheduler.c)で、5 つの順番を 1 つずつ進める(4kHz で 1 巡。docs/software.md の 4.3)。
 *   順番 0: 発光なし          → 4 つの受光の「消灯」の値(まわりの光の分)
 *   順番 1: 組A(FL と R)を点ける → 組A を点けたときの値
 *   順番 2: 組B(L と FR)を点ける → 組B を点けたときの値。読んだら 4kHz の処理を起こす
 *   順番 3・4: 発光なし        → 順番 3 の値を「x3」として残す(光のもれ・残りを見る。ログの sensor)
 * 受光の番号は ToraNeko と同じ: 1 = 左前(FL)、2 = 右(R)、3 = 左(L)、4 = 右前(FR)
 * (組A を点けて 1・2 を、組B を点けて 3・4 を使う)。
 * 結果は、次に測り終えるまで get の関数で読める。
 */
#ifndef DRV_WALL_H
#define DRV_WALL_H

#include <stdbool.h>
#include <stdint.h>

#define WALL_SENSOR_COUNT 4  /* 受光の数 */

void wall_init(void);
bool wall_read_adc(void);

/* 受光 num(1〜4)の AD 値(0〜4095)。組A を点けたとき・組B を点けたとき・全部消したとき・順番 3 */
uint16_t wall_get_lit_a(int num);
uint16_t wall_get_lit_b(int num);
uint16_t wall_get_dark(int num);
uint16_t wall_get_extra(int num);

/* 受光 num(1〜4)の、点けたときの値 − 全部消したときの値(LED の光の分だけ。まわりの光は引かれる) */
int32_t wall_get_a_minus_dark(int num);
int32_t wall_get_b_minus_dark(int num);

/* 電池の電圧 [V]。ToraNeko の名前を残した(中身は drv/current.c の current_get_battery_v()) */
float wall_get_battery_v(void);

/* 何回 1 巡したか(電源を入れてから。動作確認用) */
uint32_t wall_get_cycle_count(void);

#endif /* DRV_WALL_H */
