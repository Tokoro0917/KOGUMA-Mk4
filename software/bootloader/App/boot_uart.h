/* boot_uart.h — ブートローダの UART(USART1、115200) */
#ifndef BOOT_UART_H
#define BOOT_UART_H

#include <stdint.h>

/* USART1 を動かし、受けるのを始める */
void boot_uart_init(void);

/* USART1 を止める(走るプログラムへ移る前) */
void boot_uart_deinit(void);

/* 受けた文字を 1 つ取る。あれば 1、なければ 0 */
int boot_uart_get_byte(uint8_t *byte);

/* 文字列を送る(送り終わるまで待つ) */
void boot_uart_send(const char *text);

#endif
