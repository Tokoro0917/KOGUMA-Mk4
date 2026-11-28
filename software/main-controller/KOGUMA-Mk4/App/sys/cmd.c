/*
 * cmd.c
 * PC・BLE から届いた行(コマンド)を読んで処理する。MK4 で足したもの(2026-11-28)
 * 行の決まりは docs/ble.md の 4 章(PC → 機体、nRF52832 の @ の行)と docs/log.md の 6 章。
 *
 * ■ 読み方
 * drv/uart.c の受信バッファから 1 文字ずつ取り出し、改行(\n か \r)が来たら 1 行として処理する。
 * 返事は # で始まる 1 行(#OK …・#ERR …・#STATUS …)。PC の道具(tools/mouse.py・fw.py、ビューア)はこれを待つ。
 *
 * ■ コマンド
 *   status                    #STATUS を返す
 *   get maze                  迷路を送る(sys/output.c)
 *   get log                   ログを送る(sys/log.c。RAM にある最後の 1 つ)
 *   get params                値を全部送る(sys/params.c)
 *   set <名前> <値>           値を変える(RAM。save までは Flash に書かない)
 *   save                      値を Flash に書く
 *   log <種類>                次に取るログ(run・tune・current・sensor)
 *   log div <ms>              走行ログの間隔 [ms](0 で、走り方ごとの間隔に戻す)
 *   run <モード> <No.> [名前=値 …]   モードを走らせる(手をかざして離すと始まる)。名前=値 はその 1 回だけ
 *   run explore / run fast <No.> / run turn_test <No.>   モード 0 No.1・モード 1・モード 3 の別の書き方
 *   stop                      すぐ止まる(走っているあいだも。止めるのは drv/uart.c と sys/scheduler.c)
 *   clear                     フェイルセーフを解く(スイッチを押すのと同じ。機体に手が届かないとき)
 *   fw begin <長さ> <crc>     プログラムの書き込み: ブートローダへ移る(止まっているときだけ)
 * nRF52832 から来る行: @link up・@link down(PC とつながった・切れた。状態の LED 0 に出す)
 */
#include "sys/cmd.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "drv/boot.h"
#include "drv/current.h"
#include "drv/uart.h"
#include "maze/maze_map.h"
#include "sys/failsafe.h"
#include "sys/goal.h"
#include "sys/log.h"
#include "sys/mode.h"
#include "sys/output.h"
#include "sys/params.h"

#define LINE_MAX 300   /* 1 行の長さの上限 [文字](これより長い行は、後ろを捨てる) */
#define WORD_MAX 12    /* 1 行の言葉の数の上限 */

static char s_line[LINE_MAX + 1];  /* 受けている途中の行(最後に '\0' を置くので 1 つ多い) */
static int s_line_length = 0;
static bool s_link_up = false;      /* PC と BLE でつながっているか(@link up から @link down まで) */
static bool s_running = false;      /* 走っているか(sys/mode.c が知らせる) */
static bool s_run_requested = false;
static int s_run_mode = 0;
static int s_run_number = 0;

/* 起動時に 1 回呼ぶ。nRF52832 に、今 PC とつながっているかを聞く(STM32 が再起動したときのため。docs/ble.md の 4.3) */
void cmd_init(void)
{
  s_line_length = 0;
  printf("@link?\r\n");
}

/* 行 line を、空白で区切った言葉に分ける。words[] にそれぞれの先頭を入れ、言葉の数を返す。
 * 区切りの空白は '\0' に書き換える(line の中身が変わる) */
static int split_words(char line[], char *words[])
{
  int count = 0;
  int i = 0;
  while (line[i] != '\0' && count < WORD_MAX) {
    while (line[i] == ' ') {
      i = i + 1;
    }
    if (line[i] == '\0') {
      break;
    }
    words[count] = &line[i];
    count = count + 1;
    while (line[i] != ' ' && line[i] != '\0') {
      i = i + 1;
    }
    if (line[i] == ' ') {
      line[i] = '\0';
      i = i + 1;
    }
  }
  return count;
}

/* #STATUS の行を出す(状態・電池・迷路・ログ・止めたわけ・つながり) */
void cmd_print_status(void)
{
  const char *state = "idle";
  if (failsafe_is_stopped()) {
    state = "failsafe";
  } else if (s_running) {
    state = "running";
  }
  int explored = 0;
  if (maze_map_is_visited(0, 1) || maze_map_is_visited(1, 0)) {
    explored = 1;  /* スタートのとなりに入ったことがあれば、探索したことがある */
  }
  int link = 0;
  if (s_link_up) {
    link = 1;
  }
  printf("#STATUS state=%s batt=%.2f maze=%dx%d explored=%d log=%d fs=%s mode=%d.%d link=%d\r\n",
         state, current_get_battery_v(), MAZE_SIZE, MAZE_SIZE, explored, log_get_count(),
         failsafe_get_reason_name(failsafe_get_reason()), mode_get_mode(), mode_get_number(), link);
}

/* set <名前> <値> */
static void command_set(char *words[], int count)
{
  if (count < 3) {
    printf("#ERR usage: set <name> <value>\r\n");
    return;
  }
  int index = params_find(words[1]);
  if (index < 0) {
    printf("#ERR unknown name: %s\r\n", words[1]);
    return;
  }
  if (!params_set_by_index(index, strtof(words[2], NULL))) {
    printf("#ERR range %s\r\n", words[1]);
    return;
  }
  params_apply();
  printf("#OK set %s\r\n", words[1]);
}

/* 言葉 word の中の '=' が何文字目か(0 から数える)。なければ -1 */
static int find_equal(const char *word)
{
  for (int i = 0; word[i] != '\0'; i++) {
    if (word[i] == '=') {
      return i;
    }
  }
  return -1;
}

/* 名前=値 の言葉を、その 1 回だけの値として入れる。うまくいかなければ false(#ERR を出す) */
static bool apply_temporary_values(char *words[], int first, int count)
{
  for (int i = first; i < count; i++) {
    char *word = words[i];
    int equal = find_equal(word);  /* '=' が何文字目か(なければ -1) */
    if (equal < 0) {
      printf("#ERR not name=value: %s\r\n", word);
      return false;
    }
    word[equal] = '\0';  /* '=' を '\0' にして、名前と値を分ける(名前は word、値は word[equal + 1] から) */
    int index = params_find(word);
    if (index < 0 || !params_set_by_index(index, strtof(&word[equal + 1], NULL))) {
      printf("#ERR bad value: %s\r\n", words[i]);
      return false;
    }
  }
  params_apply();
  return true;
}

/* run の種類の名前・数から、モードと No. を決める。何番目の言葉から 名前=値 か(first_value)も返す。わからなければ false */
static bool parse_run_target(char *words[], int count, int *mode, int *number, int *first_value)
{
  if (count >= 2 && strcmp(words[1], "explore") == 0) {
    *mode = 0;
    *number = 1;
    *first_value = 2;
    return true;
  }
  if (count >= 3 && strcmp(words[1], "fast") == 0) {
    *mode = 1;
    *number = atoi(words[2]);
    *first_value = 3;
    return true;
  }
  if (count >= 3 && strcmp(words[1], "turn_test") == 0) {
    *mode = 3;
    *number = atoi(words[2]);
    *first_value = 3;
    return true;
  }
  if (count >= 3 && words[1][0] >= '0' && words[1][0] <= '9') {
    *mode = atoi(words[1]);
    *number = atoi(words[2]);
    *first_value = 3;
    return true;
  }
  return false;
}

/* run … */
static void command_run(char *words[], int count)
{
  int mode = 0;
  int number = 0;
  int first_value = 0;
  if (s_running) {
    printf("#ERR busy\r\n");
    return;
  }
  if (!parse_run_target(words, count, &mode, &number, &first_value) || !mode_has_action(mode, number)) {
    printf("#ERR unknown run\r\n");
    return;
  }
  params_backup();
  if (!apply_temporary_values(words, first_value, count)) {
    params_restore();
    return;
  }
  s_run_mode = mode;
  s_run_number = number;
  s_run_requested = true;
  printf("#OK run %d %d\r\n", mode, number);
}

/* log <種類>・log div <ms> */
static void command_log(char *words[], int count)
{
  if (count >= 3 && strcmp(words[1], "div") == 0) {
    int index = params_find("log.div_ms");
    if (!params_set_by_index(index, strtof(words[2], NULL))) {
      printf("#ERR range log div\r\n");
      return;
    }
    printf("#OK log div\r\n");
    return;
  }
  if (count >= 2 && log_set_kind_by_name(words[1])) {
    printf("#OK log %s\r\n", words[1]);
    return;
  }
  printf("#ERR usage: log run|tune|current|sensor, log div <ms>\r\n");
}

/* get … */
static void command_get(char *words[], int count)
{
  if (count >= 2 && strcmp(words[1], "maze") == 0) {
    output_maze(goal_get_x(), goal_get_y());
  } else if (count >= 2 && strcmp(words[1], "log") == 0) {
    if (log_has_data()) {
      log_print();
    } else {
      printf("#ERR no log\r\n");
    }
  } else if (count >= 2 && strcmp(words[1], "params") == 0) {
    params_print_all();
    printf("#OK get params\r\n");
  } else {
    printf("#ERR usage: get maze|log|params\r\n");
  }
}

/* fw begin <長さ> <crc>: 止まっていれば、ブートローダへ移る(戻らない)。
 * PC の道具(tools/fw.py)は # で始まる返事を待ち、#OK fw begin でも #ERR でもなければ #BOOT ready を待つ */
static void command_fw(char *words[], int count)
{
  if (count < 2 || strcmp(words[1], "begin") != 0) {
    return;  /* ブートローダ向けのほかの行(fw <位置> …、fw end)は、走るプログラムでは使わない */
  }
  if (s_running) {
    printf("#ERR busy\r\n");
    return;
  }
  printf("#REBOOT bootloader\r\n");
  boot_enter_bootloader();
}

/* nRF52832 から来た @ の行 */
static void handle_bridge_line(const char *line)
{
  if (strcmp(line, "@link up") == 0) {
    s_link_up = true;
  } else if (strcmp(line, "@link down") == 0) {
    s_link_up = false;
  }
}

/* 1 行を処理する */
static void handle_line(char line[])
{
  if (line[0] == '@') {
    handle_bridge_line(line);
    return;
  }
  char *words[WORD_MAX];
  int count = split_words(line, words);
  if (count == 0) {
    return;
  }
  if (strcmp(words[0], "status") == 0) {
    cmd_print_status();
  } else if (strcmp(words[0], "get") == 0) {
    command_get(words, count);
  } else if (strcmp(words[0], "set") == 0) {
    command_set(words, count);
  } else if (strcmp(words[0], "save") == 0) {
    if (params_save()) {
      printf("#OK save\r\n");
    } else {
      printf("#ERR save\r\n");
    }
  } else if (strcmp(words[0], "log") == 0) {
    command_log(words, count);
  } else if (strcmp(words[0], "run") == 0) {
    command_run(words, count);
  } else if (strcmp(words[0], "stop") == 0) {
    printf("#OK stop\r\n");
  } else if (strcmp(words[0], "clear") == 0) {
    failsafe_clear();
    printf("#OK clear\r\n");
  } else if (strcmp(words[0], "fw") == 0) {
    command_fw(words, count);
  } else {
    printf("#ERR unknown command: %s\r\n", words[0]);
  }
}

/* 受信バッファにたまった文字を読み、1 行そろったら処理する。待っているあいだにくり返し呼ぶ */
void cmd_poll(void)
{
  uint8_t ch = 0;
  while (uart_read_char(&ch)) {
    if (ch == '\n' || ch == '\r') {
      s_line[s_line_length] = '\0';
      if (s_line_length > 0) {
        handle_line(s_line);
      }
      s_line_length = 0;
    } else if (s_line_length < LINE_MAX) {
      s_line[s_line_length] = (char)ch;
      s_line_length = s_line_length + 1;
    }
  }
}

/* run で頼まれたモードがあれば、mode・number に入れて true(頼みは消す) */
bool cmd_take_run_request(int *mode, int *number)
{
  if (!s_run_requested) {
    return false;
  }
  s_run_requested = false;
  *mode = s_run_mode;
  *number = s_run_number;
  return true;
}

/* PC と BLE でつながっているか */
bool cmd_is_link_up(void)
{
  return s_link_up;
}

/* 走っている(true)・止まっている(false)を知らせる(sys/mode.c から) */
void cmd_set_running(bool running)
{
  s_running = running;
}
