/*
 * main.c — HY0020(nRF52832)のプログラムの入口: 起動の順番だけ
 *
 * 1. STM32 との UART を動かす(stm32_uart.c)
 * 2. BLE を動かし、アドバタイズを始める(ble_link.c)
 * 3. STM32 に「まだつながっていない」(`@link down`)を知らせる
 * あとはスレッドと BLE の知らせで動くので、main はここで終わる。
 */
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>

#include "koguma_ble.h"

LOG_MODULE_REGISTER(main, LOG_LEVEL_INF);

int main(void)
{
	LOG_INF("KOGUMA MK4 BLE(HY0020)起動");
	if (stm32_uart_start() != 0) {
		return 0;
	}
	if (ble_link_start() != 0) {
		return 0;
	}
	stm32_uart_send_own_line("@link down\n");
	return 0;
}
