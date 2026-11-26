/*
 * bench.c
 * ベンチの main。MK4 の割り込みの処理を、本物と同じ順番(50µs ごとの時刻の並び)で呼び、
 * 1 回ずつ区間の印(bench_mark.h)を付ける。QEMU のプラグインが、区間ごとの命令とメモリの読み書きを記録する。
 *
 * 区間の番号(analysis/cycle_model.py と同じ)
 *   1  空(印だけ。印の分を引くため)
 *   10 20kHz の処理(ADC2 の DMA の割り込み、LL: 印を消す + current_isr)
 *   11 エンコーダ 左の DMA の終わり(LL: 印を消す、CS、右を始める)
 *   12 エンコーダ 右の DMA の終わり(LL)+ 角度・速度の計算(encoder_process)
 *   13 IMU の INT1(LL: 印を消す、CS、SPI3 を始める)
 *   14 IMU の DMA の終わり(LL)+ 値の計算(imu_process)
 *   15 4kHz の割り込みの入口(TIM6 の番号。LL: 何もしないで control_task を呼ぶだけ。中身は 40〜)
 *   40 4kHz の処理 直進・加速中(壁の補正あり)
 *   41 4kHz の処理 直進・一定の速さ(壁の補正あり)
 *   42 4kHz の処理 直進・減速中(壁の補正あり、sqrtf)
 *   43 4kHz の処理 スラローム(ターン)
 *   44 4kHz の処理 止まって前壁合わせ
 *   50〜 HAL の割り込みの道すじ(hal_paths.c)
 *   60 LL でエンコーダの読み取りを始める分(encoder_start_left)
 */
#include <stdbool.h>
#include <stdint.h>

#include "bench_mark.h"
#include "ctrl/control.h"
#include "ctrl/trajectory.h"
#include "mk4_hw.h"
#include "sys/failsafe.h"
#include "sys/log.h"

void current_isr(void);
void current_bench_set(void);
void encoder_left_done(void);
void encoder_start_left(void);
void encoder_process(void);
void encoder_bench_next(float speed_mm_s);
void imu_start_read(void);
void imu_process(void);
void imu_bench_set(float omega_dps);
void control_task(void);
void control_bench_reset_log(void);
void wall_bench_adc(int step, bool walls);
void hal_paths_run(void);

__attribute__((section(".mark"))) volatile uint32_t g_mark[256];

static int s_tick = 0;        /* 50µs ごとの時刻 */
static int s_wall_step = 0;   /* 壁センサの順番(mk4_wall.c と同じに進める) */
static bool s_aligning = false;  /* 前壁合わせ中か(ベンチが覚えておく) */

/* 20kHz の割り込み(LL の書き方): DMA の印を消して、20kHz の処理を呼ぶ */
static void adc2_dma_irq_ll(void)
{
  hw_clear_adc2_dma_flag();
  current_isr();
}

/* 4kHz の割り込み(TIM6 の番号を借りる)。中身の区間の番号は、軌道の状態で分ける */
static int control_region_id(void)
{
  if (s_aligning) {
    return 44;
  }
  if (trajectory_get_kind() == TRAJECTORY_SLALOM) {
    return 43;
  }
  float accel = trajectory_get_accel_mm_s2();
  if (accel > 0.0f) {
    return 40;
  }
  if (accel < 0.0f) {
    return 42;
  }
  return 41;
}

/* 50µs を 1 回進める。本物の割り込みの順番: 20kHz → (偶数回目) エンコーダ 2 回の DMA → (約 3 回に 1 回) IMU →
 * (5 回に 1 回) 4kHz の処理 */
static void run_one_tick(float speed_mm_s, float omega_dps, bool walls)
{
  /* トレースを小さくするため、20kHz・エンコーダ・IMU は 80 回のうち 10 回(続いた 10 回)だけ記録する。
   * 10 回続ければ、偶数・奇数と壁センサの順番 0〜4 の組み合わせが全部入る */
  bool mark = false;
  if ((s_tick / 10) % 8 == 0) {
    mark = true;
  }
  wall_bench_adc(s_wall_step, walls);
  if (mark) {
    BENCH_BEGIN(10);
  }
  adc2_dma_irq_ll();
  if (mark) {
    BENCH_END(10);
  }
  bool control_now = false;
  if (s_wall_step == 2) {
    control_now = true;
  }
  s_wall_step = s_wall_step + 1;
  if (s_wall_step >= 5) {
    s_wall_step = 0;
  }

  if ((s_tick % 2) == 0) {
    encoder_bench_next(speed_mm_s);
    if (mark) {
      BENCH_BEGIN(11);
    }
    encoder_left_done();
    if (mark) {
      BENCH_END(11);
      BENCH_BEGIN(12);
    }
    encoder_process();
    if (mark) {
      BENCH_END(12);
    }
  }
  if ((s_tick % 3) == 0) {
    imu_bench_set(omega_dps);
    if (mark) {
      BENCH_BEGIN(13);
    }
    imu_start_read();
    if (mark) {
      BENCH_END(13);
      BENCH_BEGIN(14);
    }
    imu_process();
    if (mark) {
      BENCH_END(14);
    }
  }
  if (control_now) {
    int id = control_region_id();
    BENCH_BEGIN(id);
    control_task();
    BENCH_END(id);
  }
  s_tick = s_tick + 1;
}

int main(void)
{
  hw_bench_init();
  current_bench_set();
  imu_bench_set(0.0f);

  BENCH_BEGIN(1);
  BENCH_END(1);

  /* 60: LL でエンコーダの読み取りを始める分だけ(HAL の道すじと入れかえる計算に使う) */
  for (int i = 0; i < 4; i++) {
    BENCH_BEGIN(60);
    encoder_start_left();
    BENCH_END(60);
  }

  /* 直進: 0 → 2000mm/s(10000mm/s²)、3 区画ぶん、終わりの速さ 300mm/s。壁の補正あり、ログは 1ms ごと */
  log_start(1);
  control_start();
  control_set_wall_control(true);
  trajectory_start_straight(270.0f, 2000.0f, 300.0f, 10000.0f);
  int guard = 0;
  while (!trajectory_is_done() && guard < 20000) {
    run_one_tick(trajectory_get_speed_mm_s(), 0.0f, true);
    guard = guard + 1;
  }
  /* スラローム 90 度(300mm/s、最高 1000deg/s、20000deg/s²) */
  control_bench_reset_log();
  trajectory_start_slalom(90.0f, 300.0f, 1000.0f, 20000.0f);
  guard = 0;
  while (!trajectory_is_done() && guard < 20000) {
    run_one_tick(trajectory_get_speed_mm_s(), trajectory_get_omega_deg_s(), false);
    guard = guard + 1;
  }
  /* 止まって前壁合わせ(200 回) */
  trajectory_start_straight(30.0f, 300.0f, 0.0f, 10000.0f);
  guard = 0;
  while (!trajectory_is_done() && guard < 20000) {
    run_one_tick(trajectory_get_speed_mm_s(), 0.0f, true);
    guard = guard + 1;
  }
  control_set_front_align(true);
  s_aligning = true;
  for (int i = 0; i < 200; i++) {
    run_one_tick(0.0f, 0.0f, true);
  }
  control_set_front_align(false);
  s_aligning = false;

  if (failsafe_is_stopped()) {
    bench_puts("WARNING: failsafe stopped during bench\n");
  }
  if (!control_is_running()) {
    bench_puts("WARNING: control not running at end\n");
  }

  hal_paths_run();
  bench_puts("bench done\n");
  return 0;
}
