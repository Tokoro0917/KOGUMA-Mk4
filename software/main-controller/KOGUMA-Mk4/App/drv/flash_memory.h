/*
 * flash_memory.h
 * Flash の保存場所を消す・書く・読む(HAL の Flash の関数を使うのはここだけ)
 * ToraNeko.Mk3 の App/drv/flash_memory.h から(2026-11-28。STM32H562 の Flash に合わせた)
 *
 * 何をどの順番で書くか(迷路やゴールの形)は sys/flash.c・sys/params.c が決める。ここは、決められた場所に
 * 4 バイトの数(語)を 1 つずつ書く・読むだけ(ToraNeko と同じ使い方)。
 *
 * ■ 保存場所(docs/spec.md の「内蔵Flashの使い方」。プログラムと分けて、バンク 2 = 0x08080000〜 を使う)
 *   FLASH_AREA_GOAL    0x08080000〜(32KB = セクタ 4 つ): ゴールの位置・感度の倍率・壁制御の目標
 *   FLASH_AREA_MAZE    0x08088000〜(32KB): 迷路
 *   FLASH_AREA_PARAMS  0x08090000〜(32KB): コマンドで変えた値(sys/params.c)
 * バンク 2 を消している・書いているあいだも、CPU はバンク 1 のプログラムを読み続けられる(止まらない)。
 *
 * ■ H562 の Flash の性質(ToraNeko の F411 と違う所)
 *   - 消すのは 8KB のセクタ単位(1 セクタ 約 2ms)。消すと、どの語も 0xFFFFFFFF になる
 *   - 書くのは 16 バイト(4 語)単位。一度書いた 16 バイトは、消すまで書き直せない(確かめの符号 ECC が付くため)
 *   そこで、1 語を 16 バイトの 1 つの組に入れる(残りの 12 バイトは 0xFF のまま)。場所は 4 倍使うが、
 *   ToraNeko と同じく「1 語ずつ、好きな順番で書ける」
 */
#ifndef DRV_FLASH_MEMORY_H
#define DRV_FLASH_MEMORY_H

#include <stdbool.h>
#include <stdint.h>

/* 保存場所 */
typedef enum {
  FLASH_AREA_GOAL = 0,    /* ゴールの位置など */
  FLASH_AREA_MAZE = 1,    /* 迷路 */
  FLASH_AREA_PARAMS = 2,  /* コマンドで変えた値 */
} flash_area_t;

/* 1 つの保存場所に入る語(4 バイト)の数(32KB ÷ 1 語あたり 16 バイト) */
#define FLASH_AREA_WORD_COUNT 2048

/* 消したあとの語の値 */
#define FLASH_ERASED_WORD 0xFFFFFFFF

bool flash_memory_erase(flash_area_t area);
bool flash_memory_write_word(flash_area_t area, int index, uint32_t value);
uint32_t flash_memory_read_word(flash_area_t area, int index);

#endif /* DRV_FLASH_MEMORY_H */
