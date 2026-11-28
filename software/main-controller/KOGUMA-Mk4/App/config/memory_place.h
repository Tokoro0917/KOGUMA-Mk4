/*
 * memory_place.h
 * 大きい配列を置く RAM の場所の印(docs/firmware_memory.md の 3 章)
 *
 * SRAM3_DATA を付けた配列は、SRAM3(0x20050000〜、320KB)に置く(リンカの設定 STM32H562RGVX_FLASH.ld の .sram3)。
 * ふつうの変数・スタック(SRAM1・SRAM2)と分けて、ログ(256KB)などの大きいものをここに置く。
 * SRAM3 は起動したときに 0 にならない(NOLOAD)ので、使う前に自分で 0 にするか、書いてから読む。
 * 例: static uint8_t s_area[1024] SRAM3_DATA;
 */
#ifndef CONFIG_MEMORY_PLACE_H
#define CONFIG_MEMORY_PLACE_H

/* __attribute__((section(".sram3"))) は「この変数を .sram3 という区画に置いて」と gcc に頼む書き方 */
#define SRAM3_DATA __attribute__((section(".sram3")))

#endif /* CONFIG_MEMORY_PLACE_H */
