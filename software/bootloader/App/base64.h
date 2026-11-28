/* base64.h — base64 の文字列をバイトに戻す */
#ifndef BASE64_H
#define BASE64_H

#include <stdint.h>

/* text(text_length 文字)を戻して out に書く。戻したバイト数を返す。おかしな文字・入りきらないときは -1 */
int base64_decode(const char *text, uint32_t text_length, uint8_t *out, uint32_t out_max);

#endif
