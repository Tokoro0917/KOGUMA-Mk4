/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    gpio.c
  * @brief   ふつうの入出力のピンの設定(CubeMX の GPIO の画面と同じ。../../CUBEMX_SETUP.md の 2 章)
  ******************************************************************************
  * タイマー・ADC・SPI・UART のピンは、それぞれの初期化(stm32h5xx_hal_msp.c)で設定する。
  * - LED・壁センサの発光・MOT_EN は L で始める(消灯・モーターは止まったまま)
  * - エンコーダ・IMU の CS は H で始める(選ばない。L で始めると、電源を入れた直後に選ばれた状態になる)
  ******************************************************************************
  */
/* USER CODE END Header */

#include "gpio.h"

/* USER CODE BEGIN 0 */

/* USER CODE END 0 */

/* 出力のピンを 1 つ設定する(初めの出力を先に決めてから出力にする) */
static void output_pin(GPIO_TypeDef *port, uint16_t pin, GPIO_PinState first_state, uint32_t speed)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};

  HAL_GPIO_WritePin(port, pin, first_state);
  GPIO_InitStruct.Pin = pin;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = speed;
  HAL_GPIO_Init(port, &GPIO_InitStruct);
}

/* 入力のピンを 1 つ設定する(プルは外付けの抵抗があるので、中のものは使わない) */
static void input_pin(GPIO_TypeDef *port, uint16_t pin)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};

  GPIO_InitStruct.Pin = pin;
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(port, &GPIO_InitStruct);
}

/* ふつうの入出力のピンを設定する */
void MX_GPIO_Init(void)
{
  /* ピンの時計を入れる(入れないと、ピンの設定を書いても効かない) */
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();
  __HAL_RCC_GPIOE_CLK_ENABLE();
  __HAL_RCC_GPIOH_CLK_ENABLE();

  /* モードの LED(4・2・1) */
  output_pin(LED_MODE0_GPIO_Port, LED_MODE0_Pin, GPIO_PIN_RESET, GPIO_SPEED_FREQ_LOW);
  output_pin(LED_MODE1_GPIO_Port, LED_MODE1_Pin, GPIO_PIN_RESET, GPIO_SPEED_FREQ_LOW);
  output_pin(LED_MODE2_GPIO_Port, LED_MODE2_Pin, GPIO_PIN_RESET, GPIO_SPEED_FREQ_LOW);
  /* No. の LED(8・4・2・1) */
  output_pin(LED_NUM0_GPIO_Port, LED_NUM0_Pin, GPIO_PIN_RESET, GPIO_SPEED_FREQ_LOW);
  output_pin(LED_NUM1_GPIO_Port, LED_NUM1_Pin, GPIO_PIN_RESET, GPIO_SPEED_FREQ_LOW);
  output_pin(LED_NUM2_GPIO_Port, LED_NUM2_Pin, GPIO_PIN_RESET, GPIO_SPEED_FREQ_LOW);
  output_pin(LED_NUM3_GPIO_Port, LED_NUM3_Pin, GPIO_PIN_RESET, GPIO_SPEED_FREQ_LOW);
  /* 壁の表示 LED(PC13 は 2MHz までのピンなので Low) */
  output_pin(LED_WALL_FL_GPIO_Port, LED_WALL_FL_Pin, GPIO_PIN_RESET, GPIO_SPEED_FREQ_LOW);
  output_pin(LED_WALL_L_GPIO_Port, LED_WALL_L_Pin, GPIO_PIN_RESET, GPIO_SPEED_FREQ_LOW);
  output_pin(LED_WALL_R_GPIO_Port, LED_WALL_R_Pin, GPIO_PIN_RESET, GPIO_SPEED_FREQ_LOW);
  output_pin(LED_WALL_FR_GPIO_Port, LED_WALL_FR_Pin, GPIO_PIN_RESET, GPIO_SPEED_FREQ_LOW);
  /* 状態の LED・前の LED */
  output_pin(LED_STATUS0_GPIO_Port, LED_STATUS0_Pin, GPIO_PIN_RESET, GPIO_SPEED_FREQ_LOW);
  output_pin(LED_STATUS1_GPIO_Port, LED_STATUS1_Pin, GPIO_PIN_RESET, GPIO_SPEED_FREQ_LOW);
  output_pin(LED_FRONT_GPIO_Port, LED_FRONT_Pin, GPIO_PIN_RESET, GPIO_SPEED_FREQ_LOW);
  /* 壁センサの発光(消灯で始める。点けたり消したりを速くするので High) */
  output_pin(WALL_LED_FL_R_GPIO_Port, WALL_LED_FL_R_Pin, GPIO_PIN_RESET, GPIO_SPEED_FREQ_HIGH);
  output_pin(WALL_LED_L_FR_GPIO_Port, WALL_LED_L_FR_Pin, GPIO_PIN_RESET, GPIO_SPEED_FREQ_HIGH);
  /* モータードライバ(L でスリープ。モーターは止まったまま) */
  output_pin(MOT_EN_GPIO_Port, MOT_EN_Pin, GPIO_PIN_RESET, GPIO_SPEED_FREQ_LOW);
  /* エンコーダ・IMU の CS(H = 選ばない) */
  output_pin(ENC_L_CS_GPIO_Port, ENC_L_CS_Pin, GPIO_PIN_SET, GPIO_SPEED_FREQ_HIGH);
  output_pin(ENC_R_CS_GPIO_Port, ENC_R_CS_Pin, GPIO_PIN_SET, GPIO_SPEED_FREQ_HIGH);
  output_pin(IMU_CS_GPIO_Port, IMU_CS_Pin, GPIO_PIN_SET, GPIO_SPEED_FREQ_HIGH);
  /* エンコーダの校正(ふだんは L。PC15 は 2MHz までのピン) */
  output_pin(ENC_CAL_GPIO_Port, ENC_CAL_Pin, GPIO_PIN_RESET, GPIO_SPEED_FREQ_LOW);
  /* 使わないピン PB3(浮かせないように L を出す) */
  output_pin(SPARE_PB3_GPIO_Port, SPARE_PB3_Pin, GPIO_PIN_RESET, GPIO_SPEED_FREQ_LOW);

  /* 入力: スイッチ SW2(押すと L)、モータードライバの異常(L で異常)、IMU の INT1。
   * IMU の INT1 は、今は割り込みにしない(4kHz の処理の中で読む。drv/imu.c) */
  input_pin(SW_GPIO_Port, SW_Pin);
  input_pin(MOT_nFAULT_GPIO_Port, MOT_nFAULT_Pin);
  input_pin(IMU_INT_GPIO_Port, IMU_INT_Pin);
}

/* USER CODE BEGIN 2 */

/* USER CODE END 2 */
