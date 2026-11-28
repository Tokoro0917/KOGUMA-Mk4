/* crc32.h — CRC32(zlib と同じ) */
#ifndef CRC32_H
#define CRC32_H

#include <stdint.h>

/* 続きから計算する: 最初は crc = 0 で呼び、返った値を次に渡す */
uint32_t crc32_update(uint32_t crc, const uint8_t *data, uint32_t length);

#endif
