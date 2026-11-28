/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    tim.c
  * @brief   タイマーの設定(../../CUBEMX_SETUP.md の 4 章)
  ******************************************************************************
  * タイマーの時計は全部 240MHz(APB1・APB2 の分周 /1)。
  * - TIM1 : モーターの PWM。センターアラインド(0 → 1500 → 0 で 1 周期 = 2 × 1500 ÷ 240MHz = 12.5µs = 80kHz)。
  *          Repetition Counter 7(山と谷を 1 つずつ数えるので、8 つ = PWM 4 周期ごと = 20kHz)で更新し、
  *          そのとき TRGO を出して ADC1・ADC2 の injected の変換を起動する(drv/current.c・drv/wall.c)
  * - TIM5 : 1MHz で数える 32 ビットの時計(µs。ToraNeko と同じ)
  * - TIM16: 吸引ファンの PWM(3000 カウント = 80kHz。TIM1 と同じ周期)
  * - TIM17: ブザー(1MHz で数え、ARR で音の高さを決める)
  ******************************************************************************
  */
/* USER CODE END Header */

#include "tim.h"

/* USER CODE BEGIN 0 */

/* USER CODE END 0 */

TIM_HandleTypeDef htim1;
TIM_HandleTypeDef htim5;
TIM_HandleTypeDef htim16;
TIM_HandleTypeDef htim17;

/* PWM のチャンネル 1 つの初めの設定(PWM モード 1、duty 0 で始める) */
static void pwm_channel_config(TIM_HandleTypeDef *htim, uint32_t channel)
{
  TIM_OC_InitTypeDef sConfigOC = {0};

  sConfigOC.OCMode = TIM_OCMODE_PWM1;
  sConfigOC.Pulse = 0;
  sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
  sConfigOC.OCNPolarity = TIM_OCNPOLARITY_HIGH;
  sConfigOC.OCFastMode = TIM_OCFAST_DISABLE;
  sConfigOC.OCIdleState = TIM_OCIDLESTATE_RESET;
  sConfigOC.OCNIdleState = TIM_OCNIDLESTATE_RESET;
  if (HAL_TIM_PWM_ConfigChannel(htim, &sConfigOC, channel) != HAL_OK) {
    Error_Handler();
  }
}

/* ブレーキ・デッドタイムは使わない(TIM1・TIM16・TIM17 は「出力を出す」の印 MOE を立てると PWM が出る) */
static void break_dead_time_off(TIM_HandleTypeDef *htim)
{
  TIM_BreakDeadTimeConfigTypeDef sBreakDeadTimeConfig = {0};

  sBreakDeadTimeConfig.OffStateRunMode = TIM_OSSR_DISABLE;
  sBreakDeadTimeConfig.OffStateIDLEMode = TIM_OSSI_DISABLE;
  sBreakDeadTimeConfig.LockLevel = TIM_LOCKLEVEL_OFF;
  sBreakDeadTimeConfig.DeadTime = 0;
  sBreakDeadTimeConfig.BreakState = TIM_BREAK_DISABLE;
  sBreakDeadTimeConfig.BreakPolarity = TIM_BREAKPOLARITY_HIGH;
  sBreakDeadTimeConfig.BreakFilter = 0;
  sBreakDeadTimeConfig.BreakAFMode = TIM_BREAK_AFMODE_INPUT;
  sBreakDeadTimeConfig.Break2State = TIM_BREAK2_DISABLE;
  sBreakDeadTimeConfig.Break2Polarity = TIM_BREAK2POLARITY_HIGH;
  sBreakDeadTimeConfig.Break2Filter = 0;
  sBreakDeadTimeConfig.Break2AFMode = TIM_BREAK_AFMODE_INPUT;
  sBreakDeadTimeConfig.AutomaticOutput = TIM_AUTOMATICOUTPUT_DISABLE;
  if (HAL_TIMEx_ConfigBreakDeadTime(htim, &sBreakDeadTimeConfig) != HAL_OK) {
    Error_Handler();
  }
}

/* TIM1: モーターの PWM(CH1〜CH4 = 左 IN1・左 IN2・右 IN1・右 IN2) */
void MX_TIM1_Init(void)
{
  TIM_MasterConfigTypeDef sMasterConfig = {0};

  htim1.Instance = TIM1;
  htim1.Init.Prescaler = 0;
  htim1.Init.CounterMode = TIM_COUNTERMODE_CENTERALIGNED1;
  htim1.Init.Period = 1500;
  htim1.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim1.Init.RepetitionCounter = 7;
  htim1.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_ENABLE;
  if (HAL_TIM_PWM_Init(&htim1) != HAL_OK) {
    Error_Handler();
  }
  /* 更新のたび(20kHz)に TRGO を出す → ADC1・ADC2 の injected の変換が始まる */
  sMasterConfig.MasterOutputTrigger = TIM_TRGO_UPDATE;
  sMasterConfig.MasterOutputTrigger2 = TIM_TRGO2_RESET;
  sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim1, &sMasterConfig) != HAL_OK) {
    Error_Handler();
  }
  pwm_channel_config(&htim1, TIM_CHANNEL_1);
  pwm_channel_config(&htim1, TIM_CHANNEL_2);
  pwm_channel_config(&htim1, TIM_CHANNEL_3);
  pwm_channel_config(&htim1, TIM_CHANNEL_4);
  break_dead_time_off(&htim1);
  HAL_TIM_MspPostInit(&htim1);
}

/* TIM5: 1MHz で数え続ける(µs の時計。32 ビットなので約 71 分で 0 に戻る) */
void MX_TIM5_Init(void)
{
  htim5.Instance = TIM5;
  htim5.Init.Prescaler = 240 - 1;
  htim5.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim5.Init.Period = 0xFFFFFFFF;
  htim5.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim5.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_Base_Init(&htim5) != HAL_OK) {
    Error_Handler();
  }
}

/* TIM16: 吸引ファンの PWM(CH1 = PB8) */
void MX_TIM16_Init(void)
{
  htim16.Instance = TIM16;
  htim16.Init.Prescaler = 0;
  htim16.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim16.Init.Period = 3000 - 1;
  htim16.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim16.Init.RepetitionCounter = 0;
  htim16.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_ENABLE;
  if (HAL_TIM_PWM_Init(&htim16) != HAL_OK) {
    Error_Handler();
  }
  pwm_channel_config(&htim16, TIM_CHANNEL_1);
  break_dead_time_off(&htim16);
  HAL_TIM_MspPostInit(&htim16);
}

/* TIM17: ブザー(CH1 = PB9)。1MHz で数える。ARR + 1 が 1 周期の µs(500 なら 2kHz) */
void MX_TIM17_Init(void)
{
  htim17.Instance = TIM17;
  htim17.Init.Prescaler = 240 - 1;
  htim17.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim17.Init.Period = 500 - 1;
  htim17.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim17.Init.RepetitionCounter = 0;
  htim17.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_ENABLE;
  if (HAL_TIM_PWM_Init(&htim17) != HAL_OK) {
    Error_Handler();
  }
  pwm_channel_config(&htim17, TIM_CHANNEL_1);
  break_dead_time_off(&htim17);
  HAL_TIM_MspPostInit(&htim17);
}

/* PWM のタイマーの時計を入れる(HAL_TIM_PWM_Init から呼ばれる) */
void HAL_TIM_PWM_MspInit(TIM_HandleTypeDef *tim_pwmHandle)
{
  if (tim_pwmHandle->Instance == TIM1) {
    __HAL_RCC_TIM1_CLK_ENABLE();
  } else if (tim_pwmHandle->Instance == TIM16) {
    __HAL_RCC_TIM16_CLK_ENABLE();
  } else if (tim_pwmHandle->Instance == TIM17) {
    __HAL_RCC_TIM17_CLK_ENABLE();
  }
}

/* 数えるだけのタイマーの時計を入れる(HAL_TIM_Base_Init から呼ばれる) */
void HAL_TIM_Base_MspInit(TIM_HandleTypeDef *tim_baseHandle)
{
  if (tim_baseHandle->Instance == TIM5) {
    __HAL_RCC_TIM5_CLK_ENABLE();
  }
}

/* 出力のピン 1 本を、タイマーの出力(AF)にする */
static void timer_pin(GPIO_TypeDef *port, uint16_t pin, uint8_t alternate)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};

  GPIO_InitStruct.Pin = pin;
  GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
  GPIO_InitStruct.Alternate = alternate;
  HAL_GPIO_Init(port, &GPIO_InitStruct);
}

/* タイマーの出力のピンを設定する(AF の番号は ST のピンのデータ STM32_open_pin_data で確かめた) */
void HAL_TIM_MspPostInit(TIM_HandleTypeDef *timHandle)
{
  if (timHandle->Instance == TIM1) {
    __HAL_RCC_GPIOA_CLK_ENABLE();
    timer_pin(MOT_L_IN1_GPIO_Port, MOT_L_IN1_Pin, GPIO_AF1_TIM1);
    timer_pin(MOT_L_IN2_GPIO_Port, MOT_L_IN2_Pin, GPIO_AF1_TIM1);
    timer_pin(MOT_R_IN1_GPIO_Port, MOT_R_IN1_Pin, GPIO_AF1_TIM1);
    timer_pin(MOT_R_IN2_GPIO_Port, MOT_R_IN2_Pin, GPIO_AF1_TIM1);
  } else if (timHandle->Instance == TIM16) {
    __HAL_RCC_GPIOB_CLK_ENABLE();
    timer_pin(FAN_PWM_GPIO_Port, FAN_PWM_Pin, GPIO_AF1_TIM16);
  } else if (timHandle->Instance == TIM17) {
    __HAL_RCC_GPIOB_CLK_ENABLE();
    timer_pin(BUZZER_GPIO_Port, BUZZER_Pin, GPIO_AF1_TIM17);
  }
}

/* USER CODE BEGIN 1 */

/* USER CODE END 1 */
