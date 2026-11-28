/* USER CODE BEGIN Header */
/* spi.h — spi の初期化(CubeMX が作る形と同じ。中身は ../Src/spi.c) */
/* USER CODE END Header */
#ifndef __SPI_H__
#define __SPI_H__

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"

/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

extern SPI_HandleTypeDef hspi1;   /* IMU(LSM6DSR) */
extern SPI_HandleTypeDef hspi2;   /* エンコーダ(MT6835 × 2) */

void MX_SPI1_Init(void);
void MX_SPI2_Init(void);

/* USER CODE BEGIN Prototypes */

/* USER CODE END Prototypes */

#ifdef __cplusplus
}
#endif

#endif
