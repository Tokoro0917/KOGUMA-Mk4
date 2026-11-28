/*
 * uart.h
 * PC・BLE との通信(USART1。ToraNeko.Mk3 の App/drv/uart.h から。受けるのを足した)
 *
 * printf で書いた文字もここから送られる。受けた文字は uart_read_char() で 1 文字ずつ取り出す(sys/cmd.c)。
 */
#ifndef DRV_UART_H
#define DRV_UART_H

#include <stdbool.h>
#include <stdint.h>

void uart_init(void);
void uart_write(const uint8_t *data, uint32_t len);
void uart_wait_free(uint32_t count);
uint32_t uart_get_dropped_count(void);

bool uart_read_char(uint8_t *ch);
uint32_t uart_get_rx_dropped_count(void);
uint32_t uart_get_rx_error_count(void);
bool uart_take_stop_request(void);

#endif /* DRV_UART_H */
