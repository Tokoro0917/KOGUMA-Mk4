/* USER CODE BEGIN Header */
/* usart.h — usart の初期化(CubeMX が作る形と同じ。中身は ../Src/usart.c) */
/* USER CODE END Header */
#ifndef __USART_H__
#define __USART_H__

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"

/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

extern UART_HandleTypeDef huart1;  /* PC(STLINK の仮想 COM ポート)と BLE(HY0020) */

void MX_USART1_UART_Init(void);

/* USER CODE BEGIN Prototypes */

/* USER CODE END Prototypes */

#ifdef __cplusplus
}
#endif

#endif
