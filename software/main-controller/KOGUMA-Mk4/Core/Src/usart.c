/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    usart.c
  * @brief   USART1(PC と BLE。PB6 TX・PB7 RX)の設定(../../CUBEMX_SETUP.md の 7 章)
  ******************************************************************************
  * 115200bps、8 ビット、パリティなし、ストップ 1。送る・受けるの両方。
  * 2026-11-28: DMA は使わない。受けるのは 1 文字ごとの割り込み、送るのは「送り口が空いた」の割り込み(drv/uart.c)。
  * 割り込みの優先度は 5(20kHz・4kHz の処理より低い)。
  * PB7 は基板の R101 4.7kΩ で引き上げてあるので、中のプルアップは使わない。
  ******************************************************************************
  */
/* USER CODE END Header */

#include "usart.h"

/* USER CODE BEGIN 0 */

/* USER CODE END 0 */

UART_HandleTypeDef huart1;

/* USART1 を設定する */
void MX_USART1_UART_Init(void)
{
  huart1.Instance = USART1;
  huart1.Init.BaudRate = 115200;
  huart1.Init.WordLength = UART_WORDLENGTH_8B;
  huart1.Init.StopBits = UART_STOPBITS_1;
  huart1.Init.Parity = UART_PARITY_NONE;
  huart1.Init.Mode = UART_MODE_TX_RX;
  huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart1.Init.OverSampling = UART_OVERSAMPLING_16;
  huart1.Init.OneBitSampling = UART_ONE_BIT_SAMPLE_DISABLE;
  huart1.Init.ClockPrescaler = UART_PRESCALER_DIV1;
  huart1.AdvancedInit.AdvFeatureInit = UART_ADVFEATURE_NO_INIT;
  if (HAL_UART_Init(&huart1) != HAL_OK) {
    Error_Handler();
  }
  /* FIFO は使わない(1 文字ずつ割り込みで受ける。drv/uart.c の書き方が素直になる) */
  if (HAL_UARTEx_DisableFifoMode(&huart1) != HAL_OK) {
    Error_Handler();
  }
}

/* USART1 の時計・ピン・割り込みを設定する(HAL_UART_Init から呼ばれる) */
void HAL_UART_MspInit(UART_HandleTypeDef *uartHandle)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};

  if (uartHandle->Instance == USART1) {
    __HAL_RCC_USART1_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    GPIO_InitStruct.Pin = UART_TX_Pin;
    GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF7_USART1;
    HAL_GPIO_Init(UART_TX_GPIO_Port, &GPIO_InitStruct);
    GPIO_InitStruct.Pin = UART_RX_Pin;
    HAL_GPIO_Init(UART_RX_GPIO_Port, &GPIO_InitStruct);
    HAL_NVIC_SetPriority(USART1_IRQn, 5, 0);
    HAL_NVIC_EnableIRQ(USART1_IRQn);
  }
}

/* USER CODE BEGIN 1 */

/* USER CODE END 1 */
