/*
 * at_lines.c — `@` で始まる行の処理(docs/ble.md の 4.3)
 *
 * STM32 から:
 *   @quiet on   … 電波を止める(アドバタイズを止め、つながっていれば切る)
 *   @quiet off  … 電波を戻す
 *   @link?      … 今つながっているかを聞く → `@link up` か `@link down` を返す(STM32 が再起動したあと用)
 * PC から:
 *   @reset      … STM32 の NRST を 10ms L にする
 *   @flash      … STM32 をブートローダの書き込みの待ちに入れる
 *   @name <名前> … アドバタイズの名前を変えて Flash に残す
 *   PC には `#OK @…` か `#ERR …` を返す
 * この行は相手(STM32・PC)には渡さない。
 */
#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>

#include "koguma_ble.h"

LOG_MODULE_REGISTER(at_lines, LOG_LEVEL_INF);

#define AT_LINE_MAX 64   /* @ の行の長さの上限(名前は 29 文字まで) */

/* 行の終わりの改行(\r・\n)を除いて、command に写す */
static void copy_without_newline(char *command, const char *line)
{
	size_t length = strlen(line);

	if (length > AT_LINE_MAX) {
		length = AT_LINE_MAX;
	}
	memcpy(command, line, length);
	command[length] = '\0';
	while (length > 0 && (command[length - 1] == '\n' || command[length - 1] == '\r')) {
		length = length - 1;
		command[length] = '\0';
	}
}

/* PC に 1 行返す(つながっていれば) */
static void reply_to_pc(const char *text)
{
	ble_link_queue_to_pc((const uint8_t *)text, strlen(text));
}

void at_line_from_stm32(const char *line)
{
	char command[AT_LINE_MAX + 1];

	copy_without_newline(command, line);
	if (strcmp(command, "@quiet on") == 0) {
		ble_link_set_quiet(true);
	} else if (strcmp(command, "@quiet off") == 0) {
		ble_link_set_quiet(false);
	} else if (strcmp(command, "@link?") == 0) {
		if (ble_link_is_connected()) {
			stm32_uart_send_own_line("@link up\n");
		} else {
			stm32_uart_send_own_line("@link down\n");
		}
	} else {
		LOG_WRN("STM32 からの知らない行: %s", command);
	}
}

void at_line_from_pc(const char *line)
{
	char command[AT_LINE_MAX + 1];

	copy_without_newline(command, line);
	if (strcmp(command, "@reset") == 0) {
		stm32_reset();
		reply_to_pc("#OK @reset\n");
	} else if (strcmp(command, "@flash") == 0) {
		stm32_enter_bootloader();
		reply_to_pc("#OK @flash\n");
	} else if (strncmp(command, "@name ", 6) == 0) {
		ble_link_set_name(command + 6);   /* "@name " の 6 文字のあとが名前 */
		reply_to_pc("#OK @name\n");
	} else {
		LOG_WRN("PC からの知らない行: %s", command);
		reply_to_pc("#ERR unknown @ command\n");
	}
}
