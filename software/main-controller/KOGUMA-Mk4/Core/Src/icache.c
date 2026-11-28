/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    icache.c
  * @brief   命令のキャッシュ(ICACHE、8KB)を入れる(../../CUBEMX_SETUP.md の 2 章)
  ******************************************************************************
  * 240MHz では Flash を読むのに 5 回の待ちが入るので、命令のキャッシュで隠す。
  * データのキャッシュは内蔵の RAM にはないので、DMA とキャッシュの食い違いは起きない(docs/firmware_memory.md)。
  ******************************************************************************
  */
/* USER CODE END Header */

#include "icache.h"

/* USER CODE BEGIN 0 */

/* USER CODE END 0 */

/* ICACHE を 2-way で入れる */
void MX_ICACHE_Init(void)
{
  if (HAL_ICACHE_ConfigAssociativityMode(ICACHE_2WAYS) != HAL_OK) {
    Error_Handler();
  }
  if (HAL_ICACHE_Enable() != HAL_OK) {
    Error_Handler();
  }
}

/* USER CODE BEGIN 1 */

/* USER CODE END 1 */
