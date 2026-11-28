/*
 * cmd.h
 * PC・BLE から届いた行(コマンド)を読んで処理する(docs/ble.md の 4 章、docs/log.md の 6 章)。MK4 で足したもの
 *
 * cmd_poll() を、待っているあいだ(sys/ui.c の ui_wait_ms())にくり返し呼ぶ。
 * run <種類> は、その場では走らず、モードを選んでいるところ(sys/mode.c)が cmd_take_run_request() で受け取る。
 */
#ifndef SYS_CMD_H
#define SYS_CMD_H

#include <stdbool.h>

void cmd_init(void);
void cmd_poll(void);
void cmd_print_status(void);
bool cmd_take_run_request(int *mode, int *number);
bool cmd_is_link_up(void);
void cmd_set_running(bool running);

#endif /* SYS_CMD_H */
