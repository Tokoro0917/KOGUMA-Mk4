/*
 * log.h
 * ログ: 走っているあいだの機体の状態を記録し、あとで PC へ出す。ToraNeko.Mk3 の App/sys/log.h から(2026-11-28)
 * 何をどれだけ取るかは docs/log.md。
 *
 * ■ 使い方(ToraNeko と同じ)
 *   1. 走り始める前に log_start(間隔 [ms]) を呼ぶ
 *   2. 4kHz の処理から、毎回 log_record(今の値) を呼ぶ(ctrl/control.c)。間隔ごとに 1 行だけ残す
 *   3. 走り終わったら log_stop() を呼ぶ
 *   4. ログ出力(モード7 No.1、コマンドの get log)で log_print() を呼ぶと、ビューアで読める形で出す
 *
 * ■ ToraNeko との違い
 * - 「直前をいつも残す」: いっぱいになったら、古い行から上書きしていく(ToraNeko はいっぱいで記録をやめた)。
 *   止まった・ぶつかった・フェイルセーフのときに、直前の分が残る
 * - 種類(log_set_kind): run(走行ログ)、tune(調整のログ。4kHz の毎回)、current(電流のログ。20kHz)、
 *   sensor(壁センサの生の値。4kHz)。同じ 256KB(SRAM3)を使うので、1 回にどれか 1 つ。初めは run
 */
#ifndef SYS_LOG_H
#define SYS_LOG_H

#include <stdbool.h>
#include <stdint.h>

/* 何の動作中か(ビューアが区間を色分けする。KOGUMA の LOG_PH_* と同じ番号) */
typedef enum {
  LOG_PHASE_OTHER     = 0,   /* そのほか */
  LOG_PHASE_STRAIGHT  = 1,   /* 直線 */
  LOG_PHASE_DIAG      = 2,   /* 斜めの直線 */
  LOG_PHASE_PRE       = 3,   /* 前距離(ターンの前の直進) */
  LOG_PHASE_TURN      = 4,   /* スラロームのターン */
  LOG_PHASE_POST      = 5,   /* 後距離(ターンの後の直進) */
  LOG_PHASE_PRE_DIAG  = 6,   /* 斜めからの前距離 */
  LOG_PHASE_POST_DIAG = 7,   /* 斜めへの後距離 */
  LOG_PHASE_PIVOT     = 8,   /* その場旋回 */
  LOG_PHASE_STOP      = 9,   /* 止まる */
  LOG_PHASE_ALIGN     = 10,  /* 壁合わせ */
} log_phase_t;

/* ログの種類(docs/log.md の 1 章) */
typedef enum {
  LOG_KIND_RUN = 0,      /* 走行ログ(log_start の間隔ごと) */
  LOG_KIND_TUNE,         /* 調整のログ(4kHz の毎回。列は run と同じ) */
  LOG_KIND_CURRENT,      /* 電流のログ(20kHz の毎回) */
  LOG_KIND_SENSOR,       /* 壁センサの生の値(4kHz の毎回) */
} log_kind_t;

/* 異常の印(flags の列。1 つずつ別の数で、足し合わせる) */
#define LOG_FLAG_ENCODER_ERROR 1   /* この周期にエンコーダの読み取りのエラーが増えた */
#define LOG_FLAG_CURRENT_LIMIT 2   /* 電流の目標が上限で頭打ちになった */
#define LOG_FLAG_MOTOR_FAULT   4   /* MP6551 が異常を知らせている */

/* 記録する値(1 行ぶん)。記録する側(ctrl/control.c)が、今の値を入れて log_record() に渡す。列は docs/log.md の 2 章 */
typedef struct {
  float distance_mm;         /* x: 走った距離 [mm](合計でよい。ログには記録を始めてからの距離を残す) */
  float speed_mm_s;          /* v: 速度 [mm/s] */
  float speed_target_mm_s;   /* v_target: 目標の速度 [mm/s] */
  float accel_mm_s2;         /* a: 前後の加速度(IMU)[mm/s²] */
  float accel_target_mm_s2;  /* a_target: 軌道の加速度 [mm/s²] */
  float speed_left_mm_s;     /* v_L: 左の車輪の速度 [mm/s] */
  float speed_right_mm_s;    /* v_R: 右の車輪の速度 [mm/s] */
  float omega_deg_s;         /* w: 角速度 [deg/s] */
  float omega_target_deg_s;  /* w_target: 目標の角速度 [deg/s] */
  float angle_deg;           /* angle: 角度 [deg](制御を始めたときを 0°) */
  float angle_target_deg;    /* angle_target: 目標の向き [deg](ctrl/control.c の「目標の向き」) */
  float current_target_left_mA;   /* i_L_target */
  float current_target_right_mA;  /* i_R_target */
  float current_left_mA;     /* i_L: 測った電流 [mA] */
  float current_right_mA;    /* i_R */
  float duty_left;           /* duty_L(−1〜1) */
  float duty_right;          /* duty_R */
  float battery_v;           /* batt: 電池の電圧 [V] */
  int sensor_fl;             /* s_FL・s_L・s_R・s_FR: 壁センサの値(点灯 − 消灯) */
  int sensor_l;
  int sensor_r;
  int sensor_fr;
  float wall_dist_left_mm;   /* dist_L: 左の壁までの距離 [mm](前壁合わせのあいだは左前から求めた前の壁までの距離) */
  float wall_dist_right_mm;  /* dist_R */
  float wall_dist_front_mm;  /* dist_F: 前の壁までの距離 [mm] */
  float wall_error;          /* wall_err: 横壁制御の誤差 */
  float wall_out_deg_s;      /* wall_out: 横壁制御の出力(P + D)[deg/s] */
  float fan_current_mA;      /* fan_i: ファンの電流 [mA] */
  int wall_used;             /* wall: 横壁制御に使った壁(1 左、2 右、3 両方、0 なし) */
  log_phase_t phase;         /* phase: 何の動作中か */
  int flags;                 /* flags: 異常の印(LOG_FLAG_*) */
} log_values_t;

void log_set_kind(log_kind_t kind);
log_kind_t log_get_kind(void);
const char *log_get_kind_name(log_kind_t kind);
bool log_set_kind_by_name(const char *name);

void log_start(int interval_ms);
void log_record(log_values_t values);
void log_record_fast(void);
void log_record_current(void);
void log_stop(void);
bool log_has_data(void);
bool log_is_full(void);
int log_get_count(void);
void log_print(void);

#endif /* SYS_LOG_H */
