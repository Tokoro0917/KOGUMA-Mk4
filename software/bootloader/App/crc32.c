/*
 * crc32.c — CRC32(zlib・Python の zlib.crc32 と同じ計算)。書き込んだプログラムが正しいかを確かめる
 *
 * CRC はビットごとの計算(XOR とずらし)でしか書けないので、ここだけビット演算を使う。
 * 速さは要らない(448KB でも 1 秒かからない)ので、表を使わず 1 ビットずつ計算する。
 */
#include "crc32.h"

/* 続きから計算する: 最初は crc = 0 で呼び、返った値を次に渡す */
uint32_t crc32_update(uint32_t crc, const uint8_t *data, uint32_t length)
{
	crc = ~crc;   /* zlib の決まり: 始めと終わりで全部のビットを反転する */
	for (uint32_t i = 0; i < length; i++) {
		crc = crc ^ data[i];
		for (int bit = 0; bit < 8; bit++) {
			/* いちばん下のビットが 1 なら、ずらしてから決まった数(0xEDB88320)と XOR。0 ならずらすだけ */
			if ((crc & 1U) != 0U) {
				crc = (crc >> 1) ^ 0xEDB88320U;
			} else {
				crc = crc >> 1;
			}
		}
	}
	return ~crc;
}
