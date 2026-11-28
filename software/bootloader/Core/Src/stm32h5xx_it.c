/*
 * stm32h5xx_it.c — ブートローダの割り込み: SysTick(HAL の 1ms)と USART1(1 文字受けた)
 * ほかの割り込みは使わない(startup の Default_Handler のまま)。
 */
#include "stm32h5xx_hal.h"

extern UART_HandleTypeDef huart1;   /* boot_uart.c */

/* 1ms ごと: HAL の時刻(HAL_GetTick)を進める */
void SysTick_Handler(void)
{
	HAL_IncTick();
}

/* USART1: HAL に任せる(1 文字受けたら HAL_UART_RxCpltCallback が呼ばれる) */
void USART1_IRQHandler(void)
{
	HAL_UART_IRQHandler(&huart1);
}

/* 困ったとき(ふつうは来ない): 止まる */
void HardFault_Handler(void)
{
	while (1) {
	}
}
