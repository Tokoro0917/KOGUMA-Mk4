/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : ピンの名前(CubeMX の User Label と同じ形)と、main.c の宣言
  ******************************************************************************
  * KOGUMA MK4(STM32H562RGV6)。2026-11-28 に Claude が手で書いた(CubeMX を使える環境がなかったため)。
  * CubeMX が作るファイルと同じ形にしてあるので、あとで CubeMX で .ioc を作って生成し直しても、
  * USER CODE 欄と App/ はそのまま残る。ピンは docs/pinmap.md、設定は ../CUBEMX_SETUP.md。
  ******************************************************************************
  */
/* USER CODE END Header */

#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

#include "stm32h5xx_hal.h"

/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

void Error_Handler(void);

/* ピンの名前(docs/pinmap.md の割り当て表) */
#define LED_WALL_FR_Pin GPIO_PIN_13
#define LED_WALL_FR_GPIO_Port GPIOC
#define SW_Pin GPIO_PIN_14
#define SW_GPIO_Port GPIOC
#define ENC_CAL_Pin GPIO_PIN_15
#define ENC_CAL_GPIO_Port GPIOC
#define WALL_FL_Pin GPIO_PIN_0
#define WALL_FL_GPIO_Port GPIOC
#define WALL_L_Pin GPIO_PIN_1
#define WALL_L_GPIO_Port GPIOC
#define WALL_R_Pin GPIO_PIN_2
#define WALL_R_GPIO_Port GPIOC
#define WALL_FR_Pin GPIO_PIN_3
#define WALL_FR_GPIO_Port GPIOC
#define LED_WALL_FL_Pin GPIO_PIN_0
#define LED_WALL_FL_GPIO_Port GPIOA
#define LED_WALL_L_Pin GPIO_PIN_1
#define LED_WALL_L_GPIO_Port GPIOA
#define LED_WALL_R_Pin GPIO_PIN_2
#define LED_WALL_R_GPIO_Port GPIOA
#define MOT_R_CMS_Pin GPIO_PIN_3
#define MOT_R_CMS_GPIO_Port GPIOA
#define MOT_R_I_Pin GPIO_PIN_4
#define MOT_R_I_GPIO_Port GPIOA
#define IMU_SCK_Pin GPIO_PIN_5
#define IMU_SCK_GPIO_Port GPIOA
#define IMU_MISO_Pin GPIO_PIN_6
#define IMU_MISO_GPIO_Port GPIOA
#define IMU_MOSI_Pin GPIO_PIN_7
#define IMU_MOSI_GPIO_Port GPIOA
#define MOT_L_I_Pin GPIO_PIN_4
#define MOT_L_I_GPIO_Port GPIOC
#define MOT_L_CMS_Pin GPIO_PIN_5
#define MOT_L_CMS_GPIO_Port GPIOC
#define FAN_ISENSE_Pin GPIO_PIN_0
#define FAN_ISENSE_GPIO_Port GPIOB
#define BATT_Pin GPIO_PIN_1
#define BATT_GPIO_Port GPIOB
#define MOT_EN_Pin GPIO_PIN_2
#define MOT_EN_GPIO_Port GPIOB
#define IMU_CS_Pin GPIO_PIN_10
#define IMU_CS_GPIO_Port GPIOB
#define IMU_INT_Pin GPIO_PIN_11
#define IMU_INT_GPIO_Port GPIOB
#define LED_NUM2_Pin GPIO_PIN_12
#define LED_NUM2_GPIO_Port GPIOB
#define LED_NUM3_Pin GPIO_PIN_13
#define LED_NUM3_GPIO_Port GPIOB
#define ENC_MISO_Pin GPIO_PIN_14
#define ENC_MISO_GPIO_Port GPIOB
#define ENC_MOSI_Pin GPIO_PIN_15
#define ENC_MOSI_GPIO_Port GPIOB
#define LED_NUM1_Pin GPIO_PIN_11
#define LED_NUM1_GPIO_Port GPIOD
#define LED_NUM0_Pin GPIO_PIN_12
#define LED_NUM0_GPIO_Port GPIOD
#define ENC_L_CS_Pin GPIO_PIN_6
#define ENC_L_CS_GPIO_Port GPIOC
#define ENC_R_CS_Pin GPIO_PIN_7
#define ENC_R_CS_GPIO_Port GPIOC
#define LED_MODE0_Pin GPIO_PIN_8
#define LED_MODE0_GPIO_Port GPIOC
#define MOT_nFAULT_Pin GPIO_PIN_9
#define MOT_nFAULT_GPIO_Port GPIOC
#define MOT_L_IN1_Pin GPIO_PIN_8
#define MOT_L_IN1_GPIO_Port GPIOA
#define MOT_L_IN2_Pin GPIO_PIN_9
#define MOT_L_IN2_GPIO_Port GPIOA
#define MOT_R_IN1_Pin GPIO_PIN_10
#define MOT_R_IN1_GPIO_Port GPIOA
#define MOT_R_IN2_Pin GPIO_PIN_11
#define MOT_R_IN2_GPIO_Port GPIOA
#define ENC_SCK_Pin GPIO_PIN_12
#define ENC_SCK_GPIO_Port GPIOA
#define LED_MODE1_Pin GPIO_PIN_15
#define LED_MODE1_GPIO_Port GPIOA
#define LED_MODE2_Pin GPIO_PIN_10
#define LED_MODE2_GPIO_Port GPIOC
#define LED_STATUS0_Pin GPIO_PIN_11
#define LED_STATUS0_GPIO_Port GPIOC
#define LED_STATUS1_Pin GPIO_PIN_12
#define LED_STATUS1_GPIO_Port GPIOC
#define WALL_LED_FL_R_Pin GPIO_PIN_4
#define WALL_LED_FL_R_GPIO_Port GPIOB
#define WALL_LED_L_FR_Pin GPIO_PIN_5
#define WALL_LED_L_FR_GPIO_Port GPIOB
#define UART_TX_Pin GPIO_PIN_6
#define UART_TX_GPIO_Port GPIOB
#define UART_RX_Pin GPIO_PIN_7
#define UART_RX_GPIO_Port GPIOB
#define FAN_PWM_Pin GPIO_PIN_8
#define FAN_PWM_GPIO_Port GPIOB
#define BUZZER_Pin GPIO_PIN_9
#define BUZZER_GPIO_Port GPIOB
#define LED_FRONT_Pin GPIO_PIN_0
#define LED_FRONT_GPIO_Port GPIOE
#define SPARE_PB3_Pin GPIO_PIN_3
#define SPARE_PB3_GPIO_Port GPIOB

/* USER CODE BEGIN Private defines */

/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
