/*
 * boot_lines.c — 書き込みの待ちで受ける行の処理(docs/ble.md の 6.3)
 *
 *   fw begin <長さ> <crc>   … 書き込みを始める。走るプログラムの領域を消して「#OK fw begin」
 *   fw <位置> <base64>      … 位置(バイト)から中身を書く。先頭から途切れずに 4KB 書けるごとに「#OK fw <ここまでの位置>」。
 *                             行が飛んだ(前の行が届かなかった)ときは書かずに「#ERR fw gap <ここまでの位置>」(1 回だけ)
 *   fw end                  … 全体の CRC32 を確かめ、合えば先頭を書いて「#OK fw end」→ 走るプログラムへ
 *   status                  … 「#BOOT ready」を返す(ブートローダにいることを知らせる)
 * うまくいかないときは「#ERR fw …」を返す。PC の tools/fw.py は返事を見て送り直す。
 */
#include <string.h>
#include "boot_config.h"
#include "boot_flash.h"
#include "boot_lines.h"
#include "boot_uart.h"
#include "base64.h"

static uint32_t image_length = 0;    /* fw begin で受けた長さ(0 = まだ始めていない) */
static uint32_t image_crc = 0;       /* fw begin で受けた CRC32 */
static uint32_t written_until = 0;   /* 先頭から途切れずに書けた所(次に来るはずの位置) */
static uint32_t acked_until = 0;     /* 「#OK fw <位置>」をどこまで返したか */
static uint32_t gap_reported = 0xFFFFFFFFU;   /* 「#ERR fw gap」をどの位置で返したか(同じ位置では 1 回だけ返す) */
static int finished = 0;             /* fw end で書き終わった(走るプログラムへ移る) */

/* 10 進の数を読む。読み終わった所を *end に返す(printf・strtoul を使わないのは、C のライブラリを小さくするため) */
static uint32_t read_decimal(const char *text, const char **end)
{
	uint32_t value = 0;

	while (*text == ' ') {
		text = text + 1;
	}
	while (*text >= '0' && *text <= '9') {
		value = value * 10U + (uint32_t)(*text - '0');
		text = text + 1;
	}
	*end = text;
	return value;
}

/* 16 進の数を読む(CRC。例: 1a2b3c4d) */
static uint32_t read_hex(const char *text)
{
	uint32_t value = 0;

	while (*text == ' ') {
		text = text + 1;
	}
	while (1) {
		uint32_t digit;

		if (*text >= '0' && *text <= '9') {
			digit = (uint32_t)(*text - '0');
		} else if (*text >= 'a' && *text <= 'f') {
			digit = (uint32_t)(*text - 'a') + 10U;
		} else if (*text >= 'A' && *text <= 'F') {
			digit = (uint32_t)(*text - 'A') + 10U;
		} else {
			break;
		}
		value = value * 16U + digit;
		text = text + 1;
	}
	return value;
}

/* 数を 10 進(base = 10)か 16 進 8 けた(base = 16)の文字にして、text の後ろに足す */
static void append_number(char *text, uint32_t value, uint32_t base)
{
	static const char digits[] = "0123456789abcdef";
	char reversed[12];
	int count = 0;

	do {
		reversed[count] = digits[value % base];
		value = value / base;
		count = count + 1;
	} while (value > 0U || (base == 16U && count < 8));
	size_t length = strlen(text);

	while (count > 0) {
		count = count - 1;
		text[length] = reversed[count];
		length = length + 1U;
	}
	text[length] = '\0';
}

/* 返事を送る(数を 1 つ入れた行) */
static void reply_with_number(const char *head, uint32_t number)
{
	char text[48];

	strcpy(text, head);
	append_number(text, number, 10U);
	strcat(text, "\n");
	boot_uart_send(text);
}

/* fw begin <長さ> <crc> */
static void command_begin(const char *args)
{
	const char *end = NULL;
	uint32_t length = read_decimal(args, &end);
	uint32_t crc = read_hex(end);   /* CRC は 16 進(例: 1a2b3c4d) */

	if (length == 0U || length > APP_MAX_SIZE) {
		boot_uart_send("#ERR fw length\n");
		return;
	}
	if (boot_flash_erase_app(length) != 0) {
		boot_uart_send("#ERR fw erase\n");
		return;
	}
	image_length = length;
	image_crc = crc;
	written_until = 0;
	acked_until = 0;
	gap_reported = 0xFFFFFFFFU;
	boot_uart_send("#OK fw begin\n");
}

/* fw <位置> <base64> */
static void command_data(const char *args)
{
	static uint8_t data[300];   /* 1 行の中身(PC は 192 バイトずつ送る) */
	const char *text = NULL;
	uint32_t offset = read_decimal(args, &text);

	if (image_length == 0U) {
		boot_uart_send("#ERR fw not begun\n");
		return;
	}
	while (*text == ' ') {
		text = text + 1;
	}
	int length = base64_decode(text, (uint32_t)strlen(text), data, sizeof(data));

	if (length <= 0) {
		reply_with_number("#ERR fw base64 ", offset);
		return;
	}
	if (offset > written_until) {
		/* 前の行が届いていない(飛んだ)。書かずに、どこまで書けているかを知らせる(PC はそこから送り直す) */
		if (gap_reported != written_until) {
			gap_reported = written_until;
			reply_with_number("#ERR fw gap ", written_until);
		}
		return;
	}
	if (boot_flash_write(offset, data, (uint32_t)length, image_length) != 0) {
		reply_with_number("#ERR fw write ", offset);
		return;
	}
	/* 途切れずに書けた所を進める(送り直された前の行なら、進まない) */
	uint32_t end = offset + (uint32_t)length;

	if (end > written_until) {
		written_until = end;
	}
	/* 4KB の区切りを越えたら、または最後まで書いたら、ここまで書けたと返す */
	if (written_until / ACK_EVERY_BYTES > acked_until / ACK_EVERY_BYTES || (written_until == image_length && acked_until != image_length)) {
		acked_until = written_until;
		reply_with_number("#OK fw ", written_until);
	}
}

/* fw end */
static void command_end(void)
{
	if (image_length == 0U) {
		boot_uart_send("#ERR fw not begun\n");
		return;
	}
	uint32_t crc = boot_flash_crc(image_length);

	if (crc != image_crc) {
		char text[64] = "#ERR fw crc ";

		append_number(text, crc, 16U);
		strcat(text, "\n");
		boot_uart_send(text);
		return;
	}
	if (boot_flash_write_first_block(image_length) != 0 || !boot_flash_app_is_valid()) {
		boot_uart_send("#ERR fw first block\n");
		return;
	}
	boot_uart_send("#OK fw end\n");
	finished = 1;
}

void boot_lines_handle(char *line)
{
	/* 行の終わりの改行(\r・\n)を除く */
	size_t length = strlen(line);

	while (length > 0U && (line[length - 1U] == '\n' || line[length - 1U] == '\r')) {
		length = length - 1U;
		line[length] = '\0';
	}
	if (strncmp(line, "fw begin ", 9) == 0) {
		command_begin(line + 9);
	} else if (strcmp(line, "fw end") == 0) {
		command_end();
	} else if (strncmp(line, "fw ", 3) == 0) {
		command_data(line + 3);
	} else if (strcmp(line, "status") == 0) {
		boot_uart_send("#BOOT ready\n");
	} else if (length > 0U) {
		boot_uart_send("#ERR boot: fw begin・fw・fw end・status だけ\n");
	}
}

int boot_lines_finished(void)
{
	return finished;
}
