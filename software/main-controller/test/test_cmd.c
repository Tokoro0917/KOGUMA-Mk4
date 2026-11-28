/*
 * test_cmd.c
 * コマンド(App/sys/cmd.c)と、コマンドで変える値の表・保存(App/sys/params.c)の PC のテスト。MK4 で足したもの(2026-11-28)
 *
 * 受信バッファ(drv/uart.c)の代わりに文字列を渡し、printf で出た返事をファイルに受けて調べる。Flash は配列。
 *   [1] status・知らないコマンド
 *   [2] set・get params・範囲の外・知らない名前
 *   [3] save と読み込み(Flash に書いて、電源を入れ直したことにして読む。壊れた保存は読まない)
 *   [4] run(モードの頼み、名前=値 はその 1 回だけ、走っているときは busy)
 *   [5] log の種類・log div
 *   [6] @link up・down、fw begin(止まっていればブートローダへ、走っていれば busy)
 */
#define _POSIX_C_SOURCE 200809L  /* fileno・dup を使うため(test_output.c と同じ) */

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include "drv/boot.h"
#include "drv/buzzer.h"
#include "drv/current.h"
#include "drv/flash_memory.h"
#include "drv/uart.h"
#include "ctrl/current_ctrl.h"
#include "maze/maze_map.h"
#include "sys/cmd.h"
#include "sys/failsafe.h"
#include "sys/goal.h"
#include "sys/log.h"
#include "sys/mode.h"
#include "sys/output.h"
#include "sys/params.h"

static int s_fail_count = 0;

static void check(bool ok, const char *message)
{
  if (!ok) {
    s_fail_count = s_fail_count + 1;
    printf("  失敗: %s\n", message);
  }
}

/* ---- 仮の受信バッファ ---- */
static const char *s_input = "";
static int s_input_pos = 0;

bool uart_read_char(uint8_t *ch)
{
  if (s_input[s_input_pos] == '\0') {
    return false;
  }
  *ch = (uint8_t)s_input[s_input_pos];
  s_input_pos = s_input_pos + 1;
  return true;
}

/* ---- 仮の Flash(配列) ---- */
static uint32_t s_flash[3][FLASH_AREA_WORD_COUNT];

bool flash_memory_erase(flash_area_t area)
{
  for (int i = 0; i < FLASH_AREA_WORD_COUNT; i++) {
    s_flash[area][i] = FLASH_ERASED_WORD;
  }
  return true;
}

bool flash_memory_write_word(flash_area_t area, int index, uint32_t value)
{
  if (index < 0 || index >= FLASH_AREA_WORD_COUNT || s_flash[area][index] != FLASH_ERASED_WORD) {
    return false;  /* 消したあとにしか書けない */
  }
  s_flash[area][index] = value;
  return true;
}

uint32_t flash_memory_read_word(flash_area_t area, int index)
{
  return s_flash[area][index];
}

/* ---- そのほかの仮のもの ---- */
static int s_boot_count = 0;
static bool s_mute = false;
static float s_limit_mA = 0.0f;
static int s_log_print_count = 0;
static log_kind_t s_log_kind = LOG_KIND_RUN;
static bool s_failsafe_cleared = false;

void boot_enter_bootloader(void) { s_boot_count = s_boot_count + 1; }
void buzzer_set_mute(bool mute) { s_mute = mute; }
void current_ctrl_set_limit_mA(float limit_mA) { s_limit_mA = limit_mA; }
float current_get_battery_v(void) { return 11.82f; }
bool maze_map_is_visited(int x, int y) { (void)x; (void)y; return false; }
bool failsafe_is_stopped(void) { return false; }
void failsafe_clear(void) { s_failsafe_cleared = true; }
failsafe_reason_t failsafe_get_reason(void) { return FAILSAFE_REASON_NONE; }
const char *failsafe_get_reason_name(failsafe_reason_t reason) { (void)reason; return "none"; }
int goal_get_x(void) { return 7; }
int goal_get_y(void) { return 7; }
int log_get_count(void) { return 0; }
bool log_has_data(void) { return false; }
void log_print(void) { s_log_print_count = s_log_print_count + 1; }
bool log_set_kind_by_name(const char *name)
{
  if (strcmp(name, "current") == 0) {
    s_log_kind = LOG_KIND_CURRENT;
    return true;
  }
  if (strcmp(name, "run") == 0) {
    s_log_kind = LOG_KIND_RUN;
    return true;
  }
  return false;
}
int mode_get_mode(void) { return 0; }
int mode_get_number(void) { return 0; }
bool mode_has_action(int mode, int number) { return mode >= 0 && mode <= 7 && number >= 1 && number <= 15; }
void output_maze(int goal_x, int goal_y) { (void)goal_x; (void)goal_y; }

/* ---- 返事を受ける ---- */
#define REPLY_MAX 8192
static char s_reply[REPLY_MAX];

/* input を受けたことにして、cmd_poll() が出した返事を s_reply に入れる */
static void send(const char *input)
{
  s_input = input;
  s_input_pos = 0;
  fflush(stdout);
  FILE *file = tmpfile();
  int saved = dup(fileno(stdout));
  dup2(fileno(file), fileno(stdout));
  cmd_poll();
  fflush(stdout);
  dup2(saved, fileno(stdout));
  close(saved);
  rewind(file);
  size_t length = fread(s_reply, 1, REPLY_MAX - 1, file);
  s_reply[length] = '\0';
  fclose(file);
}

/* 返事に text が入っていれば true */
static bool reply_has(const char *text)
{
  return strstr(s_reply, text) != NULL;
}

static void test_status(void)
{
  printf("[1] status・知らないコマンド\n");
  send("status\n");
  check(reply_has("#STATUS state=idle batt=11.82 maze=16x16"), "status に #STATUS state=idle batt=11.82 maze=16x16 … を返す");
  send("hello\r\n");
  check(reply_has("#ERR unknown command: hello"), "知らないコマンドには #ERR unknown command");
  send("sta");
  check(s_reply[0] == '\0', "改行が来るまでは返事をしない");
  send("tus\n");
  check(reply_has("#STATUS"), "途中で切れて届いても、1 行にまとめて読む");
}

static void test_set(void)
{
  printf("[2] set・get params\n");
  params_init();
  send("set current.limit_mA 2500\n");
  check(reply_has("#OK set current.limit_mA"), "set に #OK set 名前");
  check(params_get(PARAM_CURRENT_LIMIT_MA) == 2500.0f && s_limit_mA == 2500.0f, "値が変わり、電流の制御に渡る");
  send("set current.limit_mA 9000\n");
  check(reply_has("#ERR range current.limit_mA") && params_get(PARAM_CURRENT_LIMIT_MA) == 2500.0f, "範囲の外は断り、値は変えない");
  send("set nothing 1\n");
  check(reply_has("#ERR unknown name: nothing"), "知らない名前は断る");
  send("set buzzer.mute 1\n");
  check(s_mute, "buzzer.mute 1 でブザーを鳴らさない");
  send("get params\n");
  check(reply_has("current.limit_mA=2500") && reply_has("#OK get params"), "get params で 名前=値 と #OK get params");
}

static void test_save(void)
{
  printf("[3] save と読み込み\n");
  flash_memory_erase(FLASH_AREA_PARAMS);
  params_init();
  check(!params_load(), "保存したことがなければ読まない");
  send("set current.limit_mA 1234\nsave\n");
  check(reply_has("#OK save"), "save に #OK save");
  params_init();  /* 電源を入れ直したことにする */
  check(params_get(PARAM_CURRENT_LIMIT_MA) == 3000.0f, "(確かめ)入れ直すと初めの値");
  check(params_load() && params_get(PARAM_CURRENT_LIMIT_MA) == 1234.0f, "Flash から 1234 が読める");
  s_flash[FLASH_AREA_PARAMS][3] = s_flash[FLASH_AREA_PARAMS][3] + 1;  /* 1 つ目の値を壊す */
  params_init();
  check(!params_load() && params_get(PARAM_CURRENT_LIMIT_MA) == 3000.0f, "壊れた保存は読まない(初めの値のまま)");
}

static void test_run(void)
{
  printf("[4] run\n");
  params_init();
  int mode = -1;
  int number = -1;
  send("run 3 2 current.limit_mA=4000\n");
  check(reply_has("#OK run 3 2"), "run 3 2 に #OK run 3 2");
  check(cmd_take_run_request(&mode, &number) && mode == 3 && number == 2, "モード3 No.2 を頼む");
  check(!cmd_take_run_request(&mode, &number), "頼みは 1 回で消える");
  check(params_get(PARAM_CURRENT_LIMIT_MA) == 4000.0f, "名前=値 が入る");
  params_restore();
  check(params_get(PARAM_CURRENT_LIMIT_MA) == 3000.0f, "走り終わったら(params_restore)元の値に戻る");
  send("run turn_test 5\n");
  check(cmd_take_run_request(&mode, &number) && mode == 3 && number == 5, "run turn_test 5 はモード3 No.5");
  send("run explore\n");
  check(cmd_take_run_request(&mode, &number) && mode == 0 && number == 1, "run explore はモード0 No.1");
  send("run 3 2 nothing=1\n");
  check(reply_has("#ERR bad value: nothing") && !cmd_take_run_request(&mode, &number), "知らない名前=値 なら走らない");
  send("run 9 9\n");
  check(reply_has("#ERR unknown run"), "ないモードは断る");
  cmd_set_running(true);
  send("run 3 2\n");
  check(reply_has("#ERR busy"), "走っているあいだは busy");
  cmd_set_running(false);
}

static void test_log(void)
{
  printf("[5] log\n");
  params_init();
  send("log current\n");
  check(reply_has("#OK log current") && s_log_kind == LOG_KIND_CURRENT, "log current で、次に取るログを電流のログにする");
  send("log xyz\n");
  check(reply_has("#ERR usage"), "知らない種類は断る");
  send("log div 4\n");
  check(reply_has("#OK log div") && params_get(PARAM_LOG_DIV_MS) == 4.0f, "log div 4 で、走行ログを 4ms ごとにする");
  send("get log\n");
  check(reply_has("#ERR no log") && s_log_print_count == 0, "ログがなければ #ERR no log");
}

static void test_link_and_fw(void)
{
  printf("[6] @link・fw begin・stop・clear\n");
  send("@link up\n");
  check(cmd_is_link_up() && s_reply[0] == '\0', "@link up でつながったことにする(返事はしない)");
  send("@link down\n");
  check(!cmd_is_link_up(), "@link down で切れたことにする");
  cmd_set_running(true);
  send("fw begin 1000 1234abcd\n");
  check(reply_has("#ERR busy") && s_boot_count == 0, "走っているあいだは、ブートローダへ移らない");
  cmd_set_running(false);
  send("fw begin 1000 1234abcd\n");
  check(reply_has("#REBOOT bootloader") && s_boot_count == 1, "止まっていれば #REBOOT bootloader を返して、ブートローダへ移る");
  send("stop\n");
  check(reply_has("#OK stop"), "stop に #OK stop(止めるのは drv/uart.c と sys/scheduler.c)");
  send("clear\n");
  check(reply_has("#OK clear") && s_failsafe_cleared, "clear でフェイルセーフを解く");
}

int main(void)
{
  test_status();
  test_set();
  test_save();
  test_run();
  test_log();
  test_link_and_fw();
  if (s_fail_count == 0) {
    printf("すべて成功\n");
    return 0;
  }
  printf("失敗 %d 件\n", s_fail_count);
  return 1;
}
