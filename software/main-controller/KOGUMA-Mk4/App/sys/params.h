/*
 * params.h
 * コマンドで変えられる値の表と、Flash への保存(docs/software.md の 8.3、docs/ble.md の 4.2)。MK4 で足したもの
 *
 * 初めの値は表(params.c の s_params)に書いてある。BLE・UART の set <名前> <値> で RAM の値を変え、
 * save で Flash に書く。電源を入れたときに Flash から読む(params_load())。
 * 新しい値を足すときは、下の param_id_t に 1 つ足し、params.c の表に 1 行足す(名前・初めの値・下限・上限・説明)。
 */
#ifndef SYS_PARAMS_H
#define SYS_PARAMS_H

#include <stdbool.h>

/* 値の番号(params.c の表と同じ順) */
typedef enum {
  PARAM_BUZZER_MUTE = 0,      /* ブザーを鳴らさない(1)・鳴らす(0) */
  PARAM_CURRENT_LIMIT_MA,     /* 電流の目標の上限 [mA] */
  PARAM_LOG_DIV_MS,           /* 走行ログの間隔 [ms](0 なら、走り方ごとに決めた間隔) */
  PARAM_LINK_AUTO_SEND,       /* BLE でつながっていれば、走り終わりにログを送る(1)・送らない(0) */
  PARAM_COUNT                 /* 値の数(いちばん最後に置く) */
} param_id_t;

void params_init(void);
bool params_load(void);
bool params_save(void);
void params_apply(void);

float params_get(param_id_t id);
int params_find(const char *name);
const char *params_get_name(int index);
float params_get_by_index(int index);
bool params_set_by_index(int index, float value);
void params_print_all(void);

void params_backup(void);
void params_restore(void);

#endif /* SYS_PARAMS_H */
