/* USER CODE BEGIN Header */
/* tim.h — tim の初期化(CubeMX が作る形と同じ。中身は ../Src/tim.c) */
/* USER CODE END Header */
#ifndef __TIM_H__
#define __TIM_H__

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"

/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

extern TIM_HandleTypeDef htim1;   /* モーターの PWM(80kHz、センターアラインド)。20kHz ごとに ADC を起動する */
extern TIM_HandleTypeDef htim5;   /* µs を数える(1MHz、32 ビット) */
extern TIM_HandleTypeDef htim16;  /* 吸引ファンの PWM(80kHz) */
extern TIM_HandleTypeDef htim17;  /* ブザー(1MHz で数え、ARR で音の高さ) */

void MX_TIM1_Init(void);
void MX_TIM5_Init(void);
void MX_TIM16_Init(void);
void MX_TIM17_Init(void);
void HAL_TIM_MspPostInit(TIM_HandleTypeDef *htim);

/* USER CODE BEGIN Prototypes */

/* USER CODE END Prototypes */

#ifdef __cplusplus
}
#endif

#endif
