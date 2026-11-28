/*
 * boot_flash.c — 走るプログラムの Flash を消す・書く・確かめる、走るプログラムへ移る
 *
 * 書き込みの途中で切れても、こわれたプログラムに飛ばないようにする工夫(docs/ble.md の 6.2 の 3):
 *   1. fw begin で、走るプログラムの領域を先に全部消す(先頭のベクタテーブルも消えるので「正しくない」になる)
 *   2. 先頭の 1KB(ベクタテーブルを含む)は RAM にためておき、Flash には書かない
 *   3. fw end で全体の CRC32 が合ったときだけ、最後に先頭の 1KB を書く
 *   → 途中で切れたときは先頭が消えたままなので、ブートローダは「正しくない」と見て書き込みを待つ
 *
 * H562 の Flash は、16 バイト(128 ビット)ずつ書く。一度書いた 16 バイトは、消さないと書き直せない(ECC のため)。
 * 同じ行が送り直されたときのために、Flash に同じ中身がすでにあれば書かずに進む。
 */
#include <string.h>
#include "stm32h5xx_hal.h"
#include "boot_config.h"
#include "boot_flash.h"
#include "crc32.h"

static uint8_t first_block[FIRST_BLOCK_SIZE];   /* 先頭の 1KB(最後に書く) */

/* 走るプログラムが正しそうか: スタックの初めの値が RAM の中、リセットの関数の番地が走るプログラムの中で、
 * Thumb の命令の印(番地の一番下が 1)がある。消えたままなら、どちらも 0xFFFFFFFF でだめになる */
int boot_flash_app_is_valid(void)
{
	uint32_t stack_top = *(volatile uint32_t *)APP_BASE;
	uint32_t reset_handler = *(volatile uint32_t *)(APP_BASE + 4U);

	if (stack_top < RAM_START || stack_top > RAM_END) {
		return 0;
	}
	if (reset_handler < APP_BASE || reset_handler >= APP_BASE + APP_MAX_SIZE) {
		return 0;
	}
	if (reset_handler % 2U != 1U) {
		return 0;
	}
	return 1;
}

int boot_flash_erase_app(uint32_t length)
{
	FLASH_EraseInitTypeDef erase = {0};
	uint32_t sector_error = 0;
	/* 消すセクタの数(length を 8KB で割って切り上げ) */
	uint32_t sectors = (length + SECTOR_SIZE - 1U) / SECTOR_SIZE;

	memset(first_block, 0xFF, sizeof(first_block));
	erase.TypeErase = FLASH_TYPEERASE_SECTORS;
	erase.Banks = FLASH_BANK_1;
	erase.Sector = APP_FIRST_SECTOR;
	erase.NbSectors = sectors;
	HAL_FLASH_Unlock();
	HAL_StatusTypeDef status = HAL_FLASHEx_Erase(&erase, &sector_error);

	HAL_FLASH_Lock();
	if (status != HAL_OK) {
		return -1;
	}
	return 0;
}

/* 16 バイトを Flash の address に書く。すでに同じ中身なら書かない。消えていない別の中身があれば -1 */
static int program_unit(uint32_t address, const uint8_t *data)
{
	const uint8_t *now = (const uint8_t *)address;
	int same = 1;
	int erased = 1;

	for (uint32_t i = 0; i < PROGRAM_UNIT; i++) {
		if (now[i] != data[i]) {
			same = 0;
		}
		if (now[i] != 0xFFU) {
			erased = 0;
		}
	}
	if (same) {
		return 0;    /* 送り直された行: もう書いてある */
	}
	if (!erased) {
		return -1;   /* 消えていない所に別の中身は書けない */
	}
	/* HAL_FLASH_Program の 3 つ目は、書く中身の番地(16 バイトの配列の先頭)を数で渡す決まり */
	uint32_t words[4];

	memcpy(words, data, PROGRAM_UNIT);   /* 4 バイトそろえの配列に写す */
	HAL_FLASH_Unlock();
	HAL_StatusTypeDef status = HAL_FLASH_Program(FLASH_TYPEPROGRAM_QUADWORD, address, (uint32_t)words);

	HAL_FLASH_Lock();
	if (status != HAL_OK) {
		return -1;
	}
	return 0;
}

int boot_flash_write(uint32_t offset, const uint8_t *data, uint32_t length, uint32_t image_length)
{
	if (offset % PROGRAM_UNIT != 0U) {
		return -1;   /* 16 バイトの区切りから始まるはず */
	}
	if (offset + length > image_length || image_length > APP_MAX_SIZE) {
		return -1;
	}
	if (length % PROGRAM_UNIT != 0U && offset + length != image_length) {
		return -1;   /* 16 バイトの倍数でないのは、最後の行だけ */
	}
	uint32_t i = 0;

	/* 先頭の 1KB の分は RAM にためる */
	while (i < length && offset + i < FIRST_BLOCK_SIZE) {
		first_block[offset + i] = data[i];
		i = i + 1U;
	}
	/* 残りを 16 バイトずつ Flash に書く。最後の半端は 0xFF で埋める */
	while (i < length) {
		uint8_t unit[PROGRAM_UNIT];
		uint32_t n = length - i;

		if (n > PROGRAM_UNIT) {
			n = PROGRAM_UNIT;
		}
		memset(unit, 0xFF, sizeof(unit));
		memcpy(unit, data + i, n);
		if (program_unit(APP_BASE + offset + i, unit) != 0) {
			return -1;
		}
		i = i + PROGRAM_UNIT;
	}
	return 0;
}

uint32_t boot_flash_crc(uint32_t image_length)
{
	uint32_t first = image_length;

	if (first > FIRST_BLOCK_SIZE) {
		first = FIRST_BLOCK_SIZE;
	}
	uint32_t crc = crc32_update(0, first_block, first);   /* 先頭は RAM から */

	if (image_length > FIRST_BLOCK_SIZE) {
		crc = crc32_update(crc, (const uint8_t *)(APP_BASE + FIRST_BLOCK_SIZE), image_length - FIRST_BLOCK_SIZE);   /* 残りは Flash から */
	}
	return crc;
}

int boot_flash_write_first_block(uint32_t image_length)
{
	uint32_t first = image_length;

	if (first > FIRST_BLOCK_SIZE) {
		first = FIRST_BLOCK_SIZE;
	}
	for (uint32_t i = 0; i < first; i = i + PROGRAM_UNIT) {
		if (program_unit(APP_BASE + i, first_block + i) != 0) {
			return -1;
		}
	}
	return 0;
}

/* 走るプログラムへ移る。手順:
 *   1. 割り込みを止め、使った周辺(SysTick・USART1)と時計の設定を、リセットのあとと同じにもどす
 *   2. NVIC の割り込みを全部止めて、待っている割り込みも消す
 *   3. ベクタテーブルの番地(VTOR)を走るプログラムの先頭にする
 *   4. スタックの初めの値を走るプログラムのものにして、リセットの関数へ飛ぶ(もう戻ってこない) */
void boot_flash_jump_to_app(void)
{
	uint32_t stack_top = *(volatile uint32_t *)APP_BASE;
	uint32_t reset_handler = *(volatile uint32_t *)(APP_BASE + 4U);
	void (*app_reset)(void) = (void (*)(void))reset_handler;   /* 番地を関数として呼ぶ(ここだけ関数ポインタを使う) */

	__disable_irq();
	SysTick->CTRL = 0;
	HAL_RCC_DeInit();
	HAL_DeInit();
	for (int i = 0; i < 8; i++) {
		NVIC->ICER[i] = 0xFFFFFFFFU;   /* 割り込みを止める(32 個ずつ) */
		NVIC->ICPR[i] = 0xFFFFFFFFU;   /* 待っている割り込みを消す */
	}
	SCB->VTOR = APP_BASE;
	__DSB();
	__ISB();
	__set_MSP(stack_top);
	__enable_irq();   /* リセットのあとと同じ(割り込みを受けられる)にしておく。NVIC は全部止めてある */
	app_reset();
	while (1) {
	}
}
