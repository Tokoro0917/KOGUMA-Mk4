/*
 * scheduler.h
 * 20kHz の処理(電流の制御・壁センサ)と 4kHz の処理(速度・角度の制御)を呼ぶ。
 * ToraNeko.Mk3 の App/sys/scheduler.h から(ToraNeko は 2kHz の処理 1 つ)
 */
#ifndef SYS_SCHEDULER_H
#define SYS_SCHEDULER_H

#include <stdbool.h>
#include <stdint.h>

/* 割り込みの記録(scheduler_take_stats で取り出す)。ToraNeko と同じ形で、20kHz の分を足した */
typedef struct {
  uint32_t tick_count;         /* 前に取り出してから、4kHz の処理が来た回数 */
  uint32_t busy_max_us;        /* 4kHz の処理 1 回にかかった時間の最大 [µs] */
  uint32_t period_min_us;      /* 4kHz の処理の間隔の最小 [µs](250 のはず) */
  uint32_t period_max_us;      /* 4kHz の処理の間隔の最大 [µs] */
  uint32_t fast_count;         /* 20kHz の処理が来た回数 */
  uint32_t fast_busy_max_us;   /* 20kHz の処理 1 回にかかった時間の最大 [µs] */
} scheduler_stats_t;

void scheduler_start(void);
void scheduler_take_stats(scheduler_stats_t *stats);

/* 割り込みの入口(Core/Src/stm32h5xx_it.c から呼ばれる) */
void scheduler_on_adc_done(void);
void scheduler_on_control_tick(void);

/* 20kHz・4kHz の処理が動いているか(フェイルセーフ・ウォッチドッグ用。前に呼んでから 1 回でも来ていれば true) */
bool scheduler_check_alive(void);

#endif /* SYS_SCHEDULER_H */
