/* USER CODE BEGIN Header */
/* adc.h — adc の初期化(CubeMX が作る形と同じ。中身は ../Src/adc.c) */
/* USER CODE END Header */
#ifndef __ADC_H__
#define __ADC_H__

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"

/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

extern ADC_HandleTypeDef hadc1;   /* 壁センサ 4 本(injected)とファンの電流(regular) */
extern ADC_HandleTypeDef hadc2;   /* モーターの電流 4 本(injected)と電池(regular) */

void MX_ADC1_Init(void);
void MX_ADC2_Init(void);

/* USER CODE BEGIN Prototypes */

/* USER CODE END Prototypes */

#ifdef __cplusplus
}
#endif

#endif
