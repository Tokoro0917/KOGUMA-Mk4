/* boot_flash.h — 走るプログラムの Flash を消す・書く・確かめる、走るプログラムへ移る */
#ifndef BOOT_FLASH_H
#define BOOT_FLASH_H

#include <stdint.h>

/* 走るプログラムが正しそうか(1 = 正しそう) */
int boot_flash_app_is_valid(void);

/* 走るプログラムの領域を、length バイトが入るだけ消す(先頭から)。0 = できた、-1 = 失敗 */
int boot_flash_erase_app(uint32_t length);

/* 走るプログラムの offset から length バイトを書く(先頭の 1KB は RAM にためる)。0 = できた、-1 = 失敗 */
int boot_flash_write(uint32_t offset, const uint8_t *data, uint32_t length, uint32_t image_length);

/* 書いた image_length バイトの CRC32(先頭の 1KB は RAM、残りは Flash から) */
uint32_t boot_flash_crc(uint32_t image_length);

/* RAM にためた先頭の 1KB を Flash に書く(CRC が合ったあと)。0 = できた */
int boot_flash_write_first_block(uint32_t image_length);

/* 走るプログラムへ移る(戻らない) */
void boot_flash_jump_to_app(void);

#endif
