/*
 * base64.c — base64 の文字列をバイトに戻す(fw の行の中身。PC の tools/fw.py が base64 にして送る)
 *
 * base64 は 4 文字で 3 バイト(1 文字が 64 通り = 6 ビット)。最後の '=' は足りない分の詰め物。
 * ビット演算の代わりに、掛け算・割り算で書いた(64 = 6 ビット、256 = 8 ビット)。
 */
#include "base64.h"

/* 1 文字を 0〜63 の数にする。base64 の文字でなければ -1 */
static int char_value(char c)
{
	if (c >= 'A' && c <= 'Z') {
		return c - 'A';
	}
	if (c >= 'a' && c <= 'z') {
		return c - 'a' + 26;
	}
	if (c >= '0' && c <= '9') {
		return c - '0' + 52;
	}
	if (c == '+') {
		return 62;
	}
	if (c == '/') {
		return 63;
	}
	return -1;
}

int base64_decode(const char *text, uint32_t text_length, uint8_t *out, uint32_t out_max)
{
	uint32_t out_length = 0;

	if (text_length % 4U != 0U) {
		return -1;   /* 4 文字ずつのはず */
	}
	for (uint32_t i = 0; i < text_length; i = i + 4U) {
		int values[4];
		int pad = 0;   /* '=' の数(最後の 4 文字だけ) */

		for (int k = 0; k < 4; k++) {
			char c = text[i + (uint32_t)k];

			if (c == '=') {
				values[k] = 0;
				pad = pad + 1;
			} else {
				values[k] = char_value(c);
				if (values[k] < 0) {
					return -1;
				}
			}
		}
		/* 4 文字(6 ビット × 4 = 24 ビット)を 1 つの数にして、3 バイト(8 ビット × 3)に分ける */
		uint32_t n = (uint32_t)values[0] * 262144U + (uint32_t)values[1] * 4096U + (uint32_t)values[2] * 64U + (uint32_t)values[3];
		uint8_t bytes[3];

		bytes[0] = (uint8_t)(n / 65536U);
		bytes[1] = (uint8_t)((n / 256U) % 256U);
		bytes[2] = (uint8_t)(n % 256U);
		for (int k = 0; k < 3 - pad; k++) {
			if (out_length >= out_max) {
				return -1;
			}
			out[out_length] = bytes[k];
			out_length = out_length + 1U;
		}
	}
	return (int)out_length;
}
