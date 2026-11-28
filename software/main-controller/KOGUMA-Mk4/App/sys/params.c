/*
 * params.c
 * コマンドで変えられる値の表と、Flash への保存。MK4 で足したもの(2026-11-28。docs/software.md の 8.3)
 *
 * ■ 表(s_params)
 * 1 行 = 名前(コマンドで使う。英数字と . _)、初めの値、下限、上限、説明。値は全部 float で持つ(0・1 の切り替えも)。
 * set で範囲の外の値を入れようとしたら、変えずに断る(sys/cmd.c が #ERR range を返す)。
 *
 * ■ Flash の形(drv/flash_memory.c の FLASH_AREA_PARAMS)
 *   [0] 目印 PARAMS_MARK
 *   [1] 書いた値の数 n
 *   [2]〜 値ごとに 2 語: 名前から作った数(name_number())、値(float の 4 バイトをそのまま)
 *   [2 + 2n] 確かめの数(それより前の語を全部足したもの。sys/flash.c と同じ考え)
 * 名前で照らし合わせるので、表に値を足したり並べ替えたりしても、前に保存した値はそのまま読める
 * (表にない名前は読み飛ばし、Flash にない値は初めの値のまま)。
 *
 * ■ その 1 回だけ変える(コマンドの run <種類> 名前=値 …。docs/ble.md の 5 章)
 * params_backup() で今の値を写しておき、走り終わったら params_restore() で戻す。
 */
#include "sys/params.h"

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "ctrl/current_ctrl.h"
#include "drv/buzzer.h"
#include "drv/flash_memory.h"

#define PARAMS_MARK 0x50524D31  /* 保存した目印("PRM1" の文字コード) */

/* 表の 1 行 */
typedef struct {
  const char *name;        /* 名前 */
  float default_value;     /* 初めの値 */
  float min_value;         /* 下限 */
  float max_value;         /* 上限 */
  const char *description; /* 説明(get params で出す) */
} param_entry_t;

/* 表(並びは params.h の param_id_t と同じ) */
static const param_entry_t s_params[PARAM_COUNT] = {
  {"buzzer.mute", 0.0f, 0.0f, 1.0f, "1 = no sound"},
  {"current.limit_mA", 3000.0f, 0.0f, 5000.0f, "motor current limit [mA]"},
  {"log.div_ms", 0.0f, 0.0f, 100.0f, "run log interval [ms] (0 = default of each run)"},
  {"link.auto_send", 1.0f, 0.0f, 1.0f, "1 = send log after each run when BLE is connected"},
};

static float s_values[PARAM_COUNT];   /* 今の値 */
static float s_backup[PARAM_COUNT];   /* params_backup() で写した値 */

/* 初めの値にする(起動時に 1 回、params_load() の前に呼ぶ) */
void params_init(void)
{
  for (int i = 0; i < PARAM_COUNT; i++) {
    s_values[i] = s_params[i].default_value;
  }
}

/* 名前から、照らし合わせに使う数を作る(1 文字ずつ、前の数 × 31 + 文字の番号。uint32_t に入りきらない分は捨てる) */
static uint32_t name_number(const char *name)
{
  uint32_t number = 0;
  for (int i = 0; name[i] != '\0'; i++) {
    number = number * 31 + (uint8_t)name[i];
  }
  return number;
}

/* float の 4 バイトを、そのまま uint32_t にする(Flash に書くため。memcpy は 4 バイトをそのまま写す) */
static uint32_t float_to_word(float value)
{
  uint32_t word = 0;
  memcpy(&word, &value, sizeof(word));
  return word;
}

static float word_to_float(uint32_t word)
{
  float value = 0.0f;
  memcpy(&value, &word, sizeof(value));
  return value;
}

/* Flash から読む。保存したことがあり、確かめの数が合えば true(合わなければ、今の値のまま) */
bool params_load(void)
{
  if (flash_memory_read_word(FLASH_AREA_PARAMS, 0) != PARAMS_MARK) {
    return false;
  }
  uint32_t count = flash_memory_read_word(FLASH_AREA_PARAMS, 1);
  if (count > 500) {
    return false;  /* 壊れている */
  }
  /* まず確かめの数を調べる */
  uint32_t sum = PARAMS_MARK + count;
  for (uint32_t i = 0; i < count * 2; i++) {
    sum = sum + flash_memory_read_word(FLASH_AREA_PARAMS, 2 + i);
  }
  if (sum != flash_memory_read_word(FLASH_AREA_PARAMS, 2 + count * 2)) {
    return false;
  }
  /* 名前が合う値だけ、範囲の中なら入れる */
  for (uint32_t i = 0; i < count; i++) {
    uint32_t number = flash_memory_read_word(FLASH_AREA_PARAMS, 2 + i * 2);
    float value = word_to_float(flash_memory_read_word(FLASH_AREA_PARAMS, 3 + i * 2));
    for (int index = 0; index < PARAM_COUNT; index++) {
      if (name_number(s_params[index].name) == number) {
        params_set_by_index(index, value);
      }
    }
  }
  return true;
}

/* 今の値を Flash に書く(止まっているときに呼ぶ)。うまくいったら true */
bool params_save(void)
{
  if (!flash_memory_erase(FLASH_AREA_PARAMS)) {
    return false;
  }
  bool ok = true;
  uint32_t sum = 0;
  int index_in_flash = 0;
  uint32_t words[2] = {PARAMS_MARK, PARAM_COUNT};
  for (int i = 0; i < 2; i++) {
    ok = ok && flash_memory_write_word(FLASH_AREA_PARAMS, index_in_flash, words[i]);
    sum = sum + words[i];
    index_in_flash = index_in_flash + 1;
  }
  for (int index = 0; index < PARAM_COUNT; index++) {
    uint32_t number = name_number(s_params[index].name);
    uint32_t value_word = float_to_word(s_values[index]);
    ok = ok && flash_memory_write_word(FLASH_AREA_PARAMS, index_in_flash, number);
    ok = ok && flash_memory_write_word(FLASH_AREA_PARAMS, index_in_flash + 1, value_word);
    sum = sum + number + value_word;
    index_in_flash = index_in_flash + 2;
  }
  ok = ok && flash_memory_write_word(FLASH_AREA_PARAMS, index_in_flash, sum);
  return ok;
}

/* 値を、それを使う所に渡す(起動したとき、set・読み込みのあとに呼ぶ) */
void params_apply(void)
{
  buzzer_set_mute(s_values[PARAM_BUZZER_MUTE] > 0.5f);
  current_ctrl_set_limit_mA(s_values[PARAM_CURRENT_LIMIT_MA]);
}

/* 番号 id の今の値 */
float params_get(param_id_t id)
{
  return s_values[id];
}

/* 名前 name の、表の何番目か。なければ -1 */
int params_find(const char *name)
{
  for (int index = 0; index < PARAM_COUNT; index++) {
    if (strcmp(s_params[index].name, name) == 0) {
      return index;
    }
  }
  return -1;
}

/* 表の index 番目の名前(index が範囲の外なら "") */
const char *params_get_name(int index)
{
  if (index < 0 || index >= PARAM_COUNT) {
    return "";
  }
  return s_params[index].name;
}

/* 表の index 番目の今の値 */
float params_get_by_index(int index)
{
  if (index < 0 || index >= PARAM_COUNT) {
    return 0.0f;
  }
  return s_values[index];
}

/* 表の index 番目の値を value にする。範囲の外なら変えずに false */
bool params_set_by_index(int index, float value)
{
  if (index < 0 || index >= PARAM_COUNT) {
    return false;
  }
  if (value < s_params[index].min_value || value > s_params[index].max_value) {
    return false;
  }
  s_values[index] = value;
  return true;
}

/* 全部の値を「名前=値 (下限〜上限) 説明」の形で出す(コマンドの get params) */
void params_print_all(void)
{
  for (int index = 0; index < PARAM_COUNT; index++) {
    printf("%s=%g (%g..%g) %s\r\n", s_params[index].name, s_values[index],
           s_params[index].min_value, s_params[index].max_value, s_params[index].description);
  }
}

/* 今の値を写しておく(その 1 回だけ変える前に) */
void params_backup(void)
{
  for (int i = 0; i < PARAM_COUNT; i++) {
    s_backup[i] = s_values[i];
  }
}

/* params_backup() で写した値に戻す */
void params_restore(void)
{
  for (int i = 0; i < PARAM_COUNT; i++) {
    s_values[i] = s_backup[i];
  }
  params_apply();
}
