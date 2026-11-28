/*
 * log.c
 * ログ: 走っているあいだの機体の状態を記録し、あとで PC へ出す。ToraNeko.Mk3 の App/sys/log.c から(2026-11-28)
 * 何を取るか・列の中身は docs/log.md。
 *
 * ■ 持ち方(ToraNeko・KOGUMA と同じ考え)
 * RAM を減らすため、走った距離のほかは、単位を決めた 2 バイトの整数(int16)にして持つ
 * (例: 角速度は 0.1 deg/s 単位。12.34 deg/s なら 123)。出すときに元の単位に戻す。
 *
 * ■ 置き場所と、直前をいつも残す(MK4)
 * 4 つの種類(run・tune・current・sensor)は、同じ 256KB の場所 s_area(SRAM3)を使う。1 回にどれか 1 つ。
 * 1 行の大きさは種類で違うので、s_area をバイトの並びとして持ち、行の番号 × 1 行の大きさ の所に memcpy で写す
 * (memcpy は「決めたバイト数を、そのまま写す」関数)。
 * いっぱいになったら、いちばん古い行から上書きしていく(輪のように使う)。
 *   - s_write_row: 次に書く行の番号。最後(s_capacity)まで来たら 0 に戻す
 *   - s_count    : 書いた行の数(s_capacity まで)
 *   - 出すときは、いちばん古い行(まだ一周していなければ 0、一周していれば s_write_row)から順に出す
 *
 * ■ 割り込みとの受け渡し(ToraNeko と同じ)
 * log_record() は 4kHz の処理、log_record_current() は 20kHz の処理の割り込みの中から呼ぶ。
 * log_start()・log_stop()・log_print() は普通の処理から呼ぶ。両方から読み書きする変数には volatile を付ける。
 *   - log_start() は、ほかの変数を全部書いてから、最後に s_recording を true にする
 *   - log_print() は、log_stop() のあと(記録していないとき)に呼ぶ
 *
 * ■ 出力の形(ビューア software/viewer/viewer.html で読める。KOGUMA・ToraNeko と同じ形に kind を足した)
 *   #BEGIN LOG kind=種類 dt=間隔[s] n=行数 div=間隔[ms] full=一周したか(1/0)
 *   列名の行
 *   値の行(CSV)
 *   #END LOG
 */
#include "sys/log.h"

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "config/memory_place.h"
#include "config/robot_params.h"
#include "ctrl/current_ctrl.h"
#include "ctrl/odometry.h"
#include "drv/current.h"
#include "drv/imu.h"
#include "drv/uart.h"
#include "drv/wall.h"
#include "sys/params.h"

#define LOG_AREA_BYTES (256 * 1024)  /* ログの場所の大きさ [バイト] */

/* 値を int16 にするときに掛ける数 */
#define SCALE_SPEED 1.0f    /* 速度: 1 mm/s */
#define SCALE_ACCEL 0.1f    /* 加速度: 10 mm/s²(±327000 mm/s² まで入る) */
#define SCALE_OMEGA 10.0f   /* 角速度: 0.1 deg/s、角度: 0.1 deg */
#define SCALE_DIST  10.0f   /* 壁までの距離: 0.1 mm */
#define SCALE_ERROR 10.0f   /* 横壁制御の誤差: 0.1 */
#define SCALE_DUTY  1000.0f /* duty: 0.1 %(±1000) */
#define SCALE_BATT  1000.0f /* 電池: 1 mV */

/* 1 行の長さの上限 [文字]。出す前に、UART の送信待ちバッファにこれだけの空きができるのを待つ */
#define LINE_LENGTH_MAX 300

/* run・tune の 1 行(64 バイト。列は docs/log.md の 2 章) */
typedef struct {
  float distance_mm;       /* x: 記録を始めてから走った距離 [mm] */
  int16_t speed;           /* v [1 mm/s] */
  int16_t speed_target;    /* v_target [1 mm/s] */
  int16_t accel;           /* a [10 mm/s²] */
  int16_t accel_target;    /* a_target [10 mm/s²] */
  int16_t speed_left;      /* v_L [1 mm/s] */
  int16_t speed_right;     /* v_R [1 mm/s] */
  int16_t omega;           /* w [0.1 deg/s] */
  int16_t omega_target;    /* w_target [0.1 deg/s] */
  int16_t angle;           /* angle [0.1 deg] */
  int16_t angle_target;    /* angle_target [0.1 deg] */
  int16_t current_target_left;   /* i_L_target [mA] */
  int16_t current_target_right;  /* i_R_target [mA] */
  int16_t current_left;    /* i_L [mA] */
  int16_t current_right;   /* i_R [mA] */
  int16_t duty_left;       /* duty_L [0.1 %] */
  int16_t duty_right;      /* duty_R [0.1 %] */
  int16_t battery;         /* batt [mV] */
  int16_t sensor_fl;       /* s_FL */
  int16_t sensor_l;        /* s_L */
  int16_t sensor_r;        /* s_R */
  int16_t sensor_fr;       /* s_FR */
  int16_t dist_left;       /* dist_L [0.1 mm] */
  int16_t dist_right;      /* dist_R [0.1 mm] */
  int16_t dist_front;      /* dist_F [0.1 mm] */
  int16_t wall_error;      /* wall_err [0.1] */
  int16_t wall_out;        /* wall_out [0.1 deg/s] */
  int16_t fan_current;     /* fan_i [mA] */
  int8_t wall_used;        /* wall */
  int8_t phase;            /* phase */
  int8_t flags;            /* flags */
} run_row_t;

/* current の 1 行(18 バイト。docs/log.md の 3 章) */
typedef struct {
  int16_t current_target_left;   /* i_L_target [mA] */
  int16_t current_left;          /* i_L [mA] */
  int16_t current_target_right;  /* i_R_target [mA] */
  int16_t current_right;         /* i_R [mA] */
  int16_t duty_left;             /* duty_L [0.1 %] */
  int16_t duty_right;            /* duty_R [0.1 %] */
  int16_t battery;               /* batt [mV] */
  int16_t speed_left;            /* v_L [1 mm/s] */
  int16_t speed_right;           /* v_R [1 mm/s] */
} current_row_t;

/* sensor の 1 行(28 バイト。docs/log.md の 4 章) */
typedef struct {
  int16_t off[4];          /* 消灯: FL・L・R・FR */
  int16_t on_fl;           /* 組A を点けたときの FL */
  int16_t on_r;            /* 組A を点けたときの R */
  int16_t on_l;            /* 組B を点けたときの L */
  int16_t on_fr;           /* 組B を点けたときの FR */
  int16_t extra[4];        /* 順番 3: FL・L・R・FR */
  int16_t distance;        /* x [0.1 mm](記録を始めてから) */
  int16_t angle;           /* angle [0.1 deg] */
} sensor_row_t;

static uint8_t s_area[LOG_AREA_BYTES] SRAM3_DATA;

/* 割り込み(log_record など)と普通の処理の両方から使う変数 */
static volatile bool s_recording = false;         /* 記録中か */
static volatile log_kind_t s_kind = LOG_KIND_RUN; /* 次に取る(今取っている)種類 */
static volatile log_kind_t s_recorded_kind = LOG_KIND_RUN;  /* 記録してある種類 */
static volatile int s_row_bytes = sizeof(run_row_t);        /* 1 行の大きさ [バイト] */
static volatile int s_capacity = LOG_AREA_BYTES / sizeof(run_row_t);  /* 入る行の数 */
static volatile int s_write_row = 0;              /* 次に書く行の番号 */
static volatile int s_count = 0;                  /* 書いた行の数 */
static volatile int s_interval_ms = 1;            /* 何 ms ごとに 1 行残すか(run だけ) */
static volatile int s_periods_per_row = 4;        /* 何回の 4kHz の処理ごとに 1 行残すか */
static volatile int s_period_count = 0;           /* 前に残してから、何回呼ばれたか */
static volatile float s_start_distance_mm = 0.0f; /* 記録を始めたときの距離 [mm] */
static volatile bool s_first_row = true;          /* 次が最初の行か */

/* 次に取るログの種類を決める(記録していないときに呼ぶ。docs/log.md の 6 章の log <種類>) */
void log_set_kind(log_kind_t kind)
{
  s_kind = kind;
}

/* 次に取るログの種類 */
log_kind_t log_get_kind(void)
{
  return s_kind;
}

/* 種類の名前(出力の kind=) */
const char *log_get_kind_name(log_kind_t kind)
{
  if (kind == LOG_KIND_TUNE) {
    return "tune";
  }
  if (kind == LOG_KIND_CURRENT) {
    return "current";
  }
  if (kind == LOG_KIND_SENSOR) {
    return "sensor";
  }
  return "run";
}

/* 名前で種類を決める(コマンドの log <種類>)。知らない名前なら false */
bool log_set_kind_by_name(const char *name)
{
  if (strcmp(name, "run") == 0) {
    log_set_kind(LOG_KIND_RUN);
  } else if (strcmp(name, "tune") == 0) {
    log_set_kind(LOG_KIND_TUNE);
  } else if (strcmp(name, "current") == 0) {
    log_set_kind(LOG_KIND_CURRENT);
  } else if (strcmp(name, "sensor") == 0) {
    log_set_kind(LOG_KIND_SENSOR);
  } else {
    return false;
  }
  return true;
}

/* 種類 kind の 1 行の大きさ [バイト] */
static int row_bytes_of(log_kind_t kind)
{
  if (kind == LOG_KIND_CURRENT) {
    return sizeof(current_row_t);
  }
  if (kind == LOG_KIND_SENSOR) {
    return sizeof(sensor_row_t);
  }
  return sizeof(run_row_t);
}

/* 記録を始める。run なら interval_ms [ms] ごとに 1 行残す(コマンドの log div で決めた間隔があれば、そちら)(4kHz の処理の何回ぶんかに直す。1ms = 4 回)。
 * tune・current・sensor は毎回残す(interval_ms は使わない)。前のログは消える */
void log_start(int interval_ms)
{
  s_recording = false;

  /* コマンドの log div <ms> で間隔を決めてあれば、それを使う(sys/params.c の log.div_ms。0 なら走り方ごとの間隔) */
  int div_ms = (int)params_get(PARAM_LOG_DIV_MS);
  if (div_ms >= 1) {
    interval_ms = div_ms;
  }
  if (interval_ms < 1) {
    interval_ms = 1;
  }
  int periods = interval_ms * CTRL_FREQ_HZ / 1000;
  if (periods < 1) {
    periods = 1;
  }
  if (s_kind != LOG_KIND_RUN) {
    periods = 1;
  }
  s_interval_ms = interval_ms;
  s_periods_per_row = periods;
  s_period_count = periods - 1;  /* 最初に呼ばれたときに 1 行目を残す */
  s_recorded_kind = s_kind;
  s_row_bytes = row_bytes_of(s_kind);
  s_capacity = LOG_AREA_BYTES / s_row_bytes;
  s_write_row = 0;
  s_count = 0;
  s_first_row = true;

  s_recording = true;  /* 最後に記録中にする */
}

/* value × scale を四捨五入して、2 バイトの整数にする。入りきらない値は、入る値の端にそろえる */
static int16_t to_int16(float value, float scale)
{
  float scaled = value * scale;
  if (scaled > 32767.0f) {
    scaled = 32767.0f;
  }
  if (scaled < -32767.0f) {
    scaled = -32767.0f;
  }
  /* (int16_t) は、小数を切り捨てて整数にする。0.5 を足して(負なら引いて)から切り捨てると四捨五入になる */
  if (scaled >= 0.0f) {
    return (int16_t)(scaled + 0.5f);
  }
  return (int16_t)(scaled - 0.5f);
}

/* 1 行ぶんのデータ(row_bytes バイト)を、次の行の場所に写して、次へ進める(いっぱいなら古い行の上に書く) */
static void store_row(const void *row, int row_bytes)
{
  memcpy(&s_area[s_write_row * row_bytes], row, row_bytes);
  s_write_row = s_write_row + 1;
  if (s_write_row >= s_capacity) {
    s_write_row = 0;
  }
  if (s_count < s_capacity) {
    s_count = s_count + 1;
  }
}

/* run・tune の今の値を記録する。4kHz の処理から毎回呼ぶ(ctrl/control.c)。間隔の回数に 1 回だけ、1 行残す */
void log_record(log_values_t values)
{
  if (!s_recording) {
    return;
  }
  if (s_recorded_kind != LOG_KIND_RUN && s_recorded_kind != LOG_KIND_TUNE) {
    return;
  }

  /* 間隔の回数に 1 回だけ残す */
  s_period_count = s_period_count + 1;
  if (s_period_count < s_periods_per_row) {
    return;
  }
  s_period_count = 0;

  if (s_first_row) {
    s_start_distance_mm = values.distance_mm;
    s_first_row = false;
  }
  run_row_t row;
  row.distance_mm = values.distance_mm - s_start_distance_mm;
  row.speed = to_int16(values.speed_mm_s, SCALE_SPEED);
  row.speed_target = to_int16(values.speed_target_mm_s, SCALE_SPEED);
  row.accel = to_int16(values.accel_mm_s2, SCALE_ACCEL);
  row.accel_target = to_int16(values.accel_target_mm_s2, SCALE_ACCEL);
  row.speed_left = to_int16(values.speed_left_mm_s, SCALE_SPEED);
  row.speed_right = to_int16(values.speed_right_mm_s, SCALE_SPEED);
  row.omega = to_int16(values.omega_deg_s, SCALE_OMEGA);
  row.omega_target = to_int16(values.omega_target_deg_s, SCALE_OMEGA);
  row.angle = to_int16(values.angle_deg, SCALE_OMEGA);
  row.angle_target = to_int16(values.angle_target_deg, SCALE_OMEGA);
  row.current_target_left = to_int16(values.current_target_left_mA, 1.0f);
  row.current_target_right = to_int16(values.current_target_right_mA, 1.0f);
  row.current_left = to_int16(values.current_left_mA, 1.0f);
  row.current_right = to_int16(values.current_right_mA, 1.0f);
  row.duty_left = to_int16(values.duty_left, SCALE_DUTY);
  row.duty_right = to_int16(values.duty_right, SCALE_DUTY);
  row.battery = to_int16(values.battery_v, SCALE_BATT);
  row.sensor_fl = to_int16((float)values.sensor_fl, 1.0f);
  row.sensor_l = to_int16((float)values.sensor_l, 1.0f);
  row.sensor_r = to_int16((float)values.sensor_r, 1.0f);
  row.sensor_fr = to_int16((float)values.sensor_fr, 1.0f);
  row.dist_left = to_int16(values.wall_dist_left_mm, SCALE_DIST);
  row.dist_right = to_int16(values.wall_dist_right_mm, SCALE_DIST);
  row.dist_front = to_int16(values.wall_dist_front_mm, SCALE_DIST);
  row.wall_error = to_int16(values.wall_error, SCALE_ERROR);
  row.wall_out = to_int16(values.wall_out_deg_s, SCALE_OMEGA);
  row.fan_current = to_int16(values.fan_current_mA, 1.0f);
  row.wall_used = (int8_t)values.wall_used;
  row.phase = (int8_t)values.phase;
  row.flags = (int8_t)values.flags;
  store_row(&row, sizeof(run_row_t));
}

/* sensor の値を記録する。4kHz の処理から毎回呼ぶ(sys/scheduler.c)。sensor を取っているときだけ */
void log_record_fast(void)
{
  if (!s_recording || s_recorded_kind != LOG_KIND_SENSOR) {
    return;
  }
  if (s_first_row) {
    s_start_distance_mm = odometry_get_distance_mm();
    s_first_row = false;
  }
  sensor_row_t row;
  /* 受光の番号は 1 = FL、2 = R、3 = L、4 = FR(drv/wall.h)。列は FL・L・R・FR の順に並べる */
  row.off[0] = wall_get_dark(1);
  row.off[1] = wall_get_dark(3);
  row.off[2] = wall_get_dark(2);
  row.off[3] = wall_get_dark(4);
  row.on_fl = wall_get_lit_a(1);
  row.on_r = wall_get_lit_a(2);
  row.on_l = wall_get_lit_b(3);
  row.on_fr = wall_get_lit_b(4);
  row.extra[0] = wall_get_extra(1);
  row.extra[1] = wall_get_extra(3);
  row.extra[2] = wall_get_extra(2);
  row.extra[3] = wall_get_extra(4);
  row.distance = to_int16(odometry_get_distance_mm() - s_start_distance_mm, SCALE_DIST);
  row.angle = to_int16(imu_get_angle_deg(), SCALE_OMEGA);
  store_row(&row, sizeof(sensor_row_t));
}

/* current の値を記録する。20kHz の処理から毎回呼ぶ(sys/scheduler.c)。current を取っているときだけ */
void log_record_current(void)
{
  if (!s_recording || s_recorded_kind != LOG_KIND_CURRENT) {
    return;
  }
  current_row_t row;
  row.current_target_left = to_int16(current_ctrl_get_left_target_mA(), 1.0f);
  row.current_left = to_int16(current_get_left_mA(), 1.0f);
  row.current_target_right = to_int16(current_ctrl_get_right_target_mA(), 1.0f);
  row.current_right = to_int16(current_get_right_mA(), 1.0f);
  row.duty_left = to_int16(current_ctrl_get_left_duty(), SCALE_DUTY);
  row.duty_right = to_int16(current_ctrl_get_right_duty(), SCALE_DUTY);
  row.battery = to_int16(current_get_battery_v(), SCALE_BATT);
  row.speed_left = to_int16(odometry_get_left_speed_mm_s(), SCALE_SPEED);
  row.speed_right = to_int16(odometry_get_right_speed_mm_s(), SCALE_SPEED);
  store_row(&row, sizeof(current_row_t));
}

/* 記録をやめる(記録した行は残る) */
void log_stop(void)
{
  s_recording = false;
}

/* 記録した行があるか */
bool log_has_data(void)
{
  if (s_count > 0) {
    return true;
  }
  return false;
}

/* 一周して、古い行を上書きしたか(直前の s_count 行だけが残っている) */
bool log_is_full(void)
{
  if (s_count >= s_capacity) {
    return true;
  }
  return false;
}

/* 記録した行数 */
int log_get_count(void)
{
  return s_count;
}

/* 古いほうから i 番目(0 から)の行の、場所の行の番号 */
static int stored_row_of(int i)
{
  int oldest = 0;
  if (s_count >= s_capacity) {
    oldest = s_write_row;  /* 一周していれば、次に書く所がいちばん古い */
  }
  int row = oldest + i;
  if (row >= s_capacity) {
    row = row - s_capacity;
  }
  return row;
}

/* run・tune の 1 行を、元の単位に戻して出す。time_s はその行の時刻 [s] */
static void print_run_row(int i, float time_s)
{
  run_row_t row;
  memcpy(&row, &s_area[stored_row_of(i) * sizeof(run_row_t)], sizeof(run_row_t));
  printf("%.4f,%.1f,%d,%d,%.0f,%.0f,%d,%d,%.1f,%.1f,%.1f,%.1f,%d,%d,%d,%d,%.1f,%.1f,%.3f,%d,%d,%d,%d,%.1f,%.1f,%.1f,%.1f,%.1f,%d,%d,%d,%d\r\n",
         time_s, row.distance_mm, row.speed, row.speed_target,
         row.accel / SCALE_ACCEL, row.accel_target / SCALE_ACCEL,
         row.speed_left, row.speed_right,
         row.omega / SCALE_OMEGA, row.omega_target / SCALE_OMEGA,
         row.angle / SCALE_OMEGA, row.angle_target / SCALE_OMEGA,
         row.current_target_left, row.current_target_right, row.current_left, row.current_right,
         row.duty_left / 10.0f, row.duty_right / 10.0f,  /* 0.1 % → % */
         row.battery / SCALE_BATT,
         row.sensor_fl, row.sensor_l, row.sensor_r, row.sensor_fr,
         row.dist_left / SCALE_DIST, row.dist_right / SCALE_DIST, row.dist_front / SCALE_DIST,
         row.wall_error / SCALE_ERROR, row.wall_out / SCALE_OMEGA,
         row.fan_current, row.wall_used, row.phase, row.flags);
}

/* current の 1 行を出す */
static void print_current_row(int i, float time_s)
{
  current_row_t row;
  memcpy(&row, &s_area[stored_row_of(i) * sizeof(current_row_t)], sizeof(current_row_t));
  printf("%.5f,%d,%d,%d,%d,%.1f,%.1f,%.3f,%d,%d\r\n",
         time_s, row.current_target_left, row.current_left, row.current_target_right, row.current_right,
         row.duty_left / 10.0f, row.duty_right / 10.0f, row.battery / SCALE_BATT,
         row.speed_left, row.speed_right);
}

/* sensor の 1 行を出す */
static void print_sensor_row(int i, float time_s)
{
  sensor_row_t row;
  memcpy(&row, &s_area[stored_row_of(i) * sizeof(sensor_row_t)], sizeof(sensor_row_t));
  printf("%.5f,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%.1f,%.1f\r\n",
         time_s, row.off[0], row.off[1], row.off[2], row.off[3],
         row.on_fl, row.on_r, row.on_l, row.on_fr,
         row.extra[0], row.extra[1], row.extra[2], row.extra[3],
         row.distance / SCALE_DIST, row.angle / SCALE_OMEGA);
}

/* 1 行の間隔 [s] */
static float row_interval_s(void)
{
  if (s_recorded_kind == LOG_KIND_RUN) {
    return s_interval_ms / 1000.0f;
  }
  if (s_recorded_kind == LOG_KIND_CURRENT) {
    return CURRENT_CTRL_PERIOD_S;
  }
  return CTRL_PERIOD_S;
}

/* 列の名前の行を出す */
static void print_header(void)
{
  if (s_recorded_kind == LOG_KIND_CURRENT) {
    printf("t,i_L_target,i_L,i_R_target,i_R,duty_L,duty_R,batt,v_L,v_R\r\n");
  } else if (s_recorded_kind == LOG_KIND_SENSOR) {
    printf("t,off_FL,off_L,off_R,off_FR,on_FL,on_R,on_L,on_FR,x3_FL,x3_L,x3_R,x3_FR,x,angle\r\n");
  } else {
    printf("t,x,v,v_target,a,a_target,v_L,v_R,w,w_target,angle,angle_target,i_L_target,i_R_target,i_L,i_R,"
           "duty_L,duty_R,batt,s_FL,s_L,s_R,s_FR,dist_L,dist_R,dist_F,wall_err,wall_out,fan_i,wall,phase,flags\r\n");
  }
}

/* 記録したログを、ビューアで読める形で出す(記録していないときに呼ぶ)。
 * 1 行ずつ、UART の送信待ちバッファに空きができるのを待ってから出す(一杯になって文字を捨てないように) */
void log_print(void)
{
  int count = s_count;
  int full = 0;
  if (log_is_full()) {
    full = 1;
  }
  float interval_s = row_interval_s();
  int div = 1;  /* 何 ms ごとに 1 行か(ToraNeko と同じ div=。run だけ。ほかは毎回なので 1) */
  if (s_recorded_kind == LOG_KIND_RUN) {
    div = s_interval_ms;
  }

  uart_wait_free(LINE_LENGTH_MAX);
  printf("\r\n#BEGIN LOG kind=%s dt=%.5f n=%d div=%d full=%d\r\n",
         log_get_kind_name(s_recorded_kind), interval_s, count, div, full);
  uart_wait_free(LINE_LENGTH_MAX);
  print_header();

  for (int i = 0; i < count; i++) {
    uart_wait_free(LINE_LENGTH_MAX);
    if (s_recorded_kind == LOG_KIND_CURRENT) {
      print_current_row(i, i * interval_s);
    } else if (s_recorded_kind == LOG_KIND_SENSOR) {
      print_sensor_row(i, i * interval_s);
    } else {
      print_run_row(i, i * interval_s);
    }
  }

  uart_wait_free(LINE_LENGTH_MAX);
  printf("#END LOG\r\n");
}
