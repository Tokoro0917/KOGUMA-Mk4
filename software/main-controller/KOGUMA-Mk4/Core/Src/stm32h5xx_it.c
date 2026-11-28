/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    stm32h5xx_it.c
  * @brief   割り込みの入口(CubeMX が作る形と同じ)。中身は App の関数を呼ぶだけ
  ******************************************************************************
  * | 割り込み | 優先度 | 呼ぶもの |
  * |---|---|---|
  * | ADC2(injected の変換が終わった、20kHz) | 0 | scheduler_on_adc_done()(sys/scheduler.c) |
  * | TIM6(4kHz の処理。20kHz の処理が 5 回に 1 回起こす。TIM6 自体は動かさない) | 2 | scheduler_on_control_tick() |
  * | USART1 | 5 | HAL_UART_IRQHandler → drv/uart.c のコールバック |
  * | SysTick(1ms) | 15 | HAL_IncTick(HAL_GetTick を進める) |
  ******************************************************************************
  */
/* USER CODE END Header */

#include "main.h"
#include "stm32h5xx_it.h"

/* USER CODE BEGIN Includes */
#include "sys/scheduler.h"
/* USER CODE END Includes */

extern UART_HandleTypeDef huart1;

/* USER CODE BEGIN 0 */

/* USER CODE END 0 */

/******************************************************************************/
/*           Cortex Processor Interruption and Exception Handlers          */
/******************************************************************************/

void NMI_Handler(void)
{
  /* USER CODE BEGIN NonMaskableInt_IRQn 0 */

  /* USER CODE END NonMaskableInt_IRQn 0 */
  while (1) {
  }
}

/* 困ったとき(ない番地を読んだ、0 で割ったなど)。止まる。デバッガで見ると、どこで起きたか分かる */
void HardFault_Handler(void)
{
  /* USER CODE BEGIN HardFault_IRQn 0 */

  /* USER CODE END HardFault_IRQn 0 */
  while (1) {
  }
}

void MemManage_Handler(void)
{
  while (1) {
  }
}

void BusFault_Handler(void)
{
  while (1) {
  }
}

void UsageFault_Handler(void)
{
  while (1) {
  }
}

void SVC_Handler(void)
{
}

void DebugMon_Handler(void)
{
}

void PendSV_Handler(void)
{
}

/* 1ms ごと */
void SysTick_Handler(void)
{
  /* USER CODE BEGIN SysTick_IRQn 0 */

  /* USER CODE END SysTick_IRQn 0 */
  HAL_IncTick();
  /* USER CODE BEGIN SysTick_IRQn 1 */

  /* USER CODE END SysTick_IRQn 1 */
}

/******************************************************************************/
/* STM32H5xx Peripheral Interrupt Handlers                                    */
/******************************************************************************/

/* ADC2: injected の 4 本の変換が終わった(20kHz)。
 * 速くするため HAL_ADC_IRQHandler は通さず、sys/scheduler.c がレジスタを直接読んで、印(JEOS)を消す
 * (docs/calc/cpu_est/README.md: HAL を通すと 1 回に数 µs 余計にかかる) */
void ADC2_IRQHandler(void)
{
  /* USER CODE BEGIN ADC2_IRQn 0 */
  scheduler_on_adc_done();
  /* USER CODE END ADC2_IRQn 0 */
}

/* TIM6: 4kHz の処理(20kHz の処理が NVIC_SetPendingIRQ(TIM6_IRQn) で起こす) */
void TIM6_IRQHandler(void)
{
  /* USER CODE BEGIN TIM6_IRQn 0 */
  scheduler_on_control_tick();
  /* USER CODE END TIM6_IRQn 0 */
}

/* USART1: 1 文字受けた・送り口が空いた(HAL が調べて、drv/uart.c のコールバックを呼ぶ) */
void USART1_IRQHandler(void)
{
  /* USER CODE BEGIN USART1_IRQn 0 */

  /* USER CODE END USART1_IRQn 0 */
  HAL_UART_IRQHandler(&huart1);
  /* USER CODE BEGIN USART1_IRQn 1 */

  /* USER CODE END USART1_IRQn 1 */
}

/* USER CODE BEGIN 1 */

/* USER CODE END 1 */
