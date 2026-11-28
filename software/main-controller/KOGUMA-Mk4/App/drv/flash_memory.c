/*
 * flash_memory.c
 * Flash の保存場所を消す・書く・読む。ToraNeko.Mk3 の App/drv/flash_memory.c から(2026-11-28。STM32H562 に合わせた)
 * 保存場所と H562 の Flash の性質は flash_memory.h の先頭。
 *
 * ■ 書き方(H562)
 * 1 語を 16 バイトの組に入れる: 組の先頭の 4 バイトに語を、残りの 12 バイトに 0xFF を入れて、16 バイトを 1 回で書く
 * (HAL_FLASH_Program の FLASH_TYPEPROGRAM_QUADWORD)。index 番目の語の番地 = 保存場所の先頭 + index × 16。
 *
 * ■ 書いたあとに読むとき
 * 命令のキャッシュ(ICACHE)は Flash の中身を覚えている。書いた・消したあとは、古い中身を読まないように
 * キャッシュを捨てる(HAL_ICACHE_Invalidate。docs/firmware_memory.md の 5 章)。
 */
#include "drv/flash_memory.h"

#include "main.h"

#define BANK2_START_ADDRESS 0x08080000U  /* バンク 2 の先頭 */
#define AREA_SECTOR_COUNT   4            /* 1 つの保存場所のセクタの数(32KB ÷ 8KB) */
#define SLOT_BYTES          16           /* 1 語に使う大きさ(書く単位) */

/* 保存場所 area の、バンク 2 の中のセクタの番号(0〜63)。GOAL = 0〜3、MAZE = 4〜7、PARAMS = 8〜11 */
static uint32_t area_first_sector(flash_area_t area)
{
  if (area == FLASH_AREA_MAZE) {
    return 4;
  }
  if (area == FLASH_AREA_PARAMS) {
    return 8;
  }
  return 0;
}

/* 保存場所 area の先頭の番地 */
static uint32_t area_address(flash_area_t area)
{
  return BANK2_START_ADDRESS + area_first_sector(area) * 0x2000U;  /* 1 セクタ = 8KB = 0x2000 */
}

/* 前の操作で残ったエラーの印を消す(残っていると、次の操作が失敗することがある) */
static void clear_error_flags(void)
{
  __HAL_FLASH_CLEAR_FLAG(FLASH_FLAG_ALL_ERRORS);
}

/* 保存場所 area(32KB、セクタ 4 つ)を消す。どの語も 0xFFFFFFFF になる。うまくいったら true。
 * 約 8ms かかる。バンク 2 なので CPU は止まらないが、走っているときは呼ばない(ToraNeko と同じ決まり) */
bool flash_memory_erase(flash_area_t area)
{
  FLASH_EraseInitTypeDef erase;
  erase.TypeErase = FLASH_TYPEERASE_SECTORS;  /* セクタを消す */
  erase.Banks = FLASH_BANK_2;
  erase.Sector = area_first_sector(area);
  erase.NbSectors = AREA_SECTOR_COUNT;
  uint32_t error_sector = 0;                  /* 失敗したときに、そのセクタの番号が入る(使わない) */

  HAL_FLASH_Unlock();
  clear_error_flags();
  HAL_StatusTypeDef status = HAL_FLASHEx_Erase(&erase, &error_sector);
  HAL_FLASH_Lock();
  HAL_ICACHE_Invalidate();

  return status == HAL_OK;
}

/* 保存場所 area の index 番目の語(0 から数える)に value を書く。うまくいったら true。
 * 書けるのは、消したあとの語だけ */
bool flash_memory_write_word(flash_area_t area, int index, uint32_t value)
{
  if (index < 0 || index >= FLASH_AREA_WORD_COUNT) {
    return false;  /* 保存場所の外 */
  }
  uint32_t address = area_address(area) + index * SLOT_BYTES;
  /* 16 バイト = 4 語。先頭に書きたい語、残りは消したままの値 */
  uint32_t slot[4] = {value, FLASH_ERASED_WORD, FLASH_ERASED_WORD, FLASH_ERASED_WORD};

  HAL_FLASH_Unlock();
  clear_error_flags();
  /* HAL_FLASH_Program の 3 つ目は「書く中身がある RAM の番地」を数として渡す決まりなので、配列の番地を uint32_t にして渡す */
  HAL_StatusTypeDef status = HAL_FLASH_Program(FLASH_TYPEPROGRAM_QUADWORD, address, (uint32_t)slot);
  HAL_FLASH_Lock();
  HAL_ICACHE_Invalidate();

  return status == HAL_OK;
}

/* 保存場所 area の index 番目の語を読む。保存場所の外なら、消したあとの値を返す */
uint32_t flash_memory_read_word(flash_area_t area, int index)
{
  if (index < 0 || index >= FLASH_AREA_WORD_COUNT) {
    return FLASH_ERASED_WORD;
  }
  /* Flash は、RAM と同じように番地を指定して読める。index 番目の組の先頭の番地を「uint32_t の場所」とみなして読む */
  const volatile uint32_t *word = (const volatile uint32_t *)(area_address(area) + index * SLOT_BYTES);
  return *word;
}
